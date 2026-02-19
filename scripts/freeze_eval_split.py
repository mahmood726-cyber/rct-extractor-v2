#!/usr/bin/env python3
"""Freeze and split a Cochrane-linked gold dataset at trial level."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def _to_float(value: object):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_reference_effect(record: Dict) -> bool:
    """Return True when a record has any usable numeric reference effect."""
    if _to_float(record.get("cochrane_effect")) is not None:
        return True
    gold = record.get("gold") or {}
    return _to_float(gold.get("point_estimate")) is not None


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_jsonl(path: Path) -> List[Dict]:
    records: List[Dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_number}: {exc}") from exc
    return records


def _write_jsonl(path: Path, records: Iterable[Dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _split_counts(total: int, train_ratio: float, val_ratio: float, test_ratio: float) -> Tuple[int, int, int]:
    if total <= 0:
        return 0, 0, 0
    if total == 1:
        return 1, 0, 0
    if total == 2:
        return 1, 1, 0

    train = int(total * train_ratio)
    val = int(total * val_ratio)
    test = total - train - val

    train = max(train, 1)
    val = max(val, 1)
    test = max(test, 1)

    while train + val + test > total:
        if train >= val and train >= test and train > 1:
            train -= 1
        elif val >= test and val > 1:
            val -= 1
        elif test > 1:
            test -= 1
        else:
            break

    while train + val + test < total:
        train += 1

    return train, val, test


def _normalize_ratios(train: float, val: float, test: float) -> Tuple[float, float, float]:
    total = train + val + test
    if total <= 0:
        raise ValueError("Ratios must sum to a positive value.")
    return train / total, val / total, test / total


def build_frozen_split(
    records: List[Dict],
    seed: int,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
) -> Dict:
    trial_ids = sorted({record["study_id"] for record in records})
    rng = random.Random(seed)
    rng.shuffle(trial_ids)

    train_n, val_n, test_n = _split_counts(len(trial_ids), train_ratio, val_ratio, test_ratio)
    train_ids = sorted(trial_ids[:train_n])
    val_ids = sorted(trial_ids[train_n:train_n + val_n])
    test_ids = sorted(trial_ids[train_n + val_n:train_n + val_n + test_n])

    trial_to_split = {trial_id: "train" for trial_id in train_ids}
    trial_to_split.update({trial_id: "validation" for trial_id in val_ids})
    trial_to_split.update({trial_id: "test" for trial_id in test_ids})

    split_records: Dict[str, List[Dict]] = {"train": [], "validation": [], "test": []}
    for record in records:
        split_name = trial_to_split[record["study_id"]]
        split_records[split_name].append(record)

    split_record_counts = {name: len(split_records[name]) for name in split_records}

    return {
        "trial_ids": {
            "train": train_ids,
            "validation": val_ids,
            "test": test_ids,
        },
        "split_record_counts": split_record_counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("gold_data/gold_50.jsonl"),
        help="Input Cochrane-linked gold JSONL dataset.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/frozen_eval_v1"),
        help="Output directory for frozen dataset and split manifest.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic trial shuffling.")
    parser.add_argument("--train-ratio", type=float, default=0.70, help="Training split ratio.")
    parser.add_argument("--validation-ratio", type=float, default=0.15, help="Validation split ratio.")
    parser.add_argument("--test-ratio", type=float, default=0.15, help="Test split ratio.")
    parser.add_argument(
        "--include-excluded",
        action="store_true",
        help="Include records marked excluded=true in frozen dataset.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input dataset not found: {args.input}")

    train_ratio, val_ratio, test_ratio = _normalize_ratios(
        args.train_ratio,
        args.validation_ratio,
        args.test_ratio,
    )

    raw_records = _load_jsonl(args.input)

    included: List[Dict] = []
    skipped = {
        "excluded_flag": 0,
        "missing_study_id": 0,
        "missing_reference_effect": 0,
    }

    for record in raw_records:
        if not args.include_excluded and record.get("excluded"):
            skipped["excluded_flag"] += 1
            continue
        if not record.get("study_id"):
            skipped["missing_study_id"] += 1
            continue
        if not _has_reference_effect(record):
            skipped["missing_reference_effect"] += 1
            continue
        included.append(record)

    if not included:
        raise ValueError("No records available after filtering; cannot create split.")

    split = build_frozen_split(
        records=included,
        seed=args.seed,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    frozen_path = args.output_dir / "frozen_gold.jsonl"
    manifest_path = args.output_dir / "split_manifest.json"
    protocol_path = args.output_dir / "protocol_lock.json"

    _write_jsonl(frozen_path, included)

    manifest = {
        "protocol_version": "1.0.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "ratios": {
            "train": train_ratio,
            "validation": val_ratio,
            "test": test_ratio,
        },
        "trial_ids": split["trial_ids"],
        "split_record_counts": split["split_record_counts"],
    }

    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)

    frozen_hash = _sha256_file(frozen_path)
    protocol = {
        "protocol_version": "1.0.0",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_dataset": str(args.input).replace("\\", "/"),
        "input_dataset_sha256": _sha256_file(args.input),
        "frozen_dataset": str(frozen_path).replace("\\", "/"),
        "frozen_dataset_sha256": frozen_hash,
        "frozen_dataset_record_count": len(included),
        "frozen_trial_count": len({record["study_id"] for record in included}),
        "split_manifest": str(manifest_path).replace("\\", "/"),
        "split_manifest_sha256": _sha256_file(manifest_path),
        "include_excluded": args.include_excluded,
        "skipped_records": skipped,
    }

    with protocol_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(protocol, handle, indent=2, ensure_ascii=False)

    print(f"Frozen records: {len(included)}")
    print(f"Frozen trials: {protocol['frozen_trial_count']}")
    print(f"Train/validation/test trials: "
          f"{len(split['trial_ids']['train'])}/"
          f"{len(split['trial_ids']['validation'])}/"
          f"{len(split['trial_ids']['test'])}")
    print(f"Wrote: {frozen_path}")
    print(f"Wrote: {manifest_path}")
    print(f"Wrote: {protocol_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
