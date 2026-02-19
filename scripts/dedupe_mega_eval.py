#!/usr/bin/env python3
"""Deduplicate mega_eval.jsonl by study_id, keeping the strongest result per study."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


STATUS_SCORE: Dict[str, int] = {
    "match": 6,
    "extracted_no_match": 5,
    "no_extraction": 4,
    "no_cochrane_ref": 3,
    "error": 2,
    "timeout_skipped_by_batch_runner": 1,
}


def _score_row(row: dict, line_idx: int) -> Tuple[int, int, int]:
    status = str(row.get("status", ""))
    status_score = STATUS_SCORE.get(status, 0)
    n_extracted = int(row.get("n_extracted", 0) or 0)
    has_match = 1 if row.get("match") else 0
    # Later lines win ties so newest row is preferred when quality is equal.
    return (status_score * 100 + has_match * 10 + n_extracted, line_idx, line_idx)


def dedupe(input_path: Path, output_path: Path) -> Dict[str, int]:
    raw_lines = input_path.read_text(encoding="utf-8", errors="replace").splitlines()

    best_by_id: Dict[str, Tuple[Tuple[int, int, int], int, dict]] = {}
    unparsable = 0
    missing_id = 0

    for idx, line in enumerate(raw_lines):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError:
            unparsable += 1
            continue

        study_id = row.get("study_id")
        if not study_id:
            missing_id += 1
            continue

        study_id = str(study_id)
        candidate = (_score_row(row, idx), idx, row)
        existing = best_by_id.get(study_id)
        if existing is None or candidate[0] > existing[0]:
            best_by_id[study_id] = candidate

    kept = [v for _, v in sorted(best_by_id.items(), key=lambda item: item[1][1])]
    output_lines: List[str] = [json.dumps(v[2], ensure_ascii=False) for v in kept]
    output_path.write_text("\n".join(output_lines) + ("\n" if output_lines else ""), encoding="utf-8")

    input_rows = sum(1 for line in raw_lines if line.strip())
    output_rows = len(output_lines)
    return {
        "input_rows": input_rows,
        "output_rows": output_rows,
        "removed_rows": max(0, input_rows - output_rows),
        "unique_study_ids": len(best_by_id),
        "unparsable_rows": unparsable,
        "missing_study_id_rows": missing_id,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("gold_data/mega/mega_eval.jsonl"),
        help="Input mega_eval JSONL path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input)",
    )
    parser.add_argument(
        "--backup",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="When overwriting input, keep a .bak copy first",
    )
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output or args.input

    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    if output_path == input_path and args.backup:
        backup_path = input_path.with_suffix(input_path.suffix + ".bak")
        shutil.copy2(input_path, backup_path)
        print(f"Backup written: {backup_path}")

    stats = dedupe(input_path=input_path, output_path=output_path)
    print(json.dumps(stats, indent=2))
    print(f"Wrote: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
