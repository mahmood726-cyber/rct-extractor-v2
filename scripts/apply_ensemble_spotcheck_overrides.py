#!/usr/bin/env python3
"""Apply manual spot-check overrides onto ensemble-prefilled adjudication JSONL."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _write_jsonl(path: Path, rows: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _to_bool(value: object) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"", "none", "null", "na", "n/a"}:
        return None
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _load_spotcheck_csv(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _join_notes(*parts: str) -> str:
    cleaned = [str(p).strip() for p in parts if str(p).strip()]
    return "; ".join(cleaned)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--spotcheck-csv", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any manual override row cannot be matched by benchmark_id.",
    )
    args = parser.parse_args()

    if not args.input_jsonl.exists():
        raise FileNotFoundError(f"--input-jsonl not found: {args.input_jsonl}")
    if not args.spotcheck_csv.exists():
        raise FileNotFoundError(f"--spotcheck-csv not found: {args.spotcheck_csv}")

    rows = _load_jsonl(args.input_jsonl)
    spot_rows = _load_spotcheck_csv(args.spotcheck_csv)
    by_id = {str(r.get("benchmark_id") or ""): r for r in rows if r.get("benchmark_id")}

    applied = 0
    include_true = 0
    include_false = 0
    flip_count = 0
    unchanged_count = 0
    missing_ids: List[str] = []
    applied_rows: List[Dict] = []

    for srow in spot_rows:
        manual_inc = _to_bool(srow.get("manual_check_included"))
        if manual_inc is None:
            continue
        bid = str(srow.get("benchmark_id") or "").strip()
        if not bid or bid not in by_id:
            missing_ids.append(bid or "<missing_benchmark_id>")
            continue

        target = by_id[bid]
        gold = target.get("gold") if isinstance(target.get("gold"), dict) else {}
        gold = dict(gold)

        before_inc = _to_bool(gold.get("included"))
        if before_inc is None:
            before_inc = False

        rank = str(srow.get("spotcheck_rank") or "").strip()
        bucket = str(srow.get("spotcheck_bucket") or "").strip()
        note = str(srow.get("manual_check_notes") or "").strip()
        manual_type = str(srow.get("manual_check_effect_type") or "").strip() or None
        manual_point = _to_float(srow.get("manual_check_point_estimate"))
        manual_ci_low = _to_float(srow.get("manual_check_ci_lower"))
        manual_ci_high = _to_float(srow.get("manual_check_ci_upper"))
        manual_page = _to_int(srow.get("manual_check_page_number"))

        gold["included"] = bool(manual_inc)
        if manual_inc:
            if manual_type is not None:
                gold["effect_type"] = manual_type.upper()
            if manual_point is not None:
                gold["point_estimate"] = manual_point
            if manual_ci_low is not None:
                gold["ci_lower"] = manual_ci_low
            if manual_ci_high is not None:
                gold["ci_upper"] = manual_ci_high
            if manual_page is not None:
                gold["page_number"] = manual_page
            if not str(gold.get("source_text") or "").strip():
                gold["source_text"] = str(srow.get("consensus_source_text") or "")
            gold["notes"] = _join_notes(
                str(gold.get("notes") or ""),
                "manual_spotcheck_confirm_include",
                note,
            )
        else:
            gold["effect_type"] = None
            gold["point_estimate"] = None
            gold["ci_lower"] = None
            gold["ci_upper"] = None
            gold["p_value"] = None
            gold["source_text"] = ""
            gold["page_number"] = None
            gold["notes"] = _join_notes(
                str(gold.get("notes") or ""),
                "manual_spotcheck_override_exclude",
                note,
            )

        target["gold"] = gold
        target["adjudication_notes"] = _join_notes(
            str(target.get("adjudication_notes") or ""),
            f"manual_spotcheck_override:rank={rank}:bucket={bucket}:included={manual_inc}",
        )

        after_inc = bool(manual_inc)
        if bool(before_inc) != after_inc:
            flip_count += 1
        else:
            unchanged_count += 1

        applied += 1
        if after_inc:
            include_true += 1
        else:
            include_false += 1
        applied_rows.append(
            {
                "benchmark_id": bid,
                "spotcheck_rank": rank,
                "pmid": srow.get("pmid"),
                "before_included": bool(before_inc),
                "after_included": after_inc,
                "manual_check_notes": note,
            }
        )

    if args.strict and missing_ids:
        raise ValueError(f"Missing benchmark ids for manual overrides: {missing_ids}")

    _write_jsonl(args.output_jsonl, rows)
    summary = {
        "generated_at_utc": _utc_now(),
        "paths": {
            "input_jsonl": str(args.input_jsonl).replace("\\", "/"),
            "spotcheck_csv": str(args.spotcheck_csv).replace("\\", "/"),
            "output_jsonl": str(args.output_jsonl).replace("\\", "/"),
        },
        "counts": {
            "rows_total": len(rows),
            "spotcheck_rows_total": len(spot_rows),
            "manual_overrides_applied": applied,
            "manual_include_true": include_true,
            "manual_include_false": include_false,
            "manual_flip_count": flip_count,
            "manual_unchanged_count": unchanged_count,
            "missing_override_ids": len(missing_ids),
        },
        "missing_override_ids": missing_ids,
        "applied_rows": applied_rows,
    }
    _write_json(args.summary_json, summary)

    print(f"Wrote: {args.output_jsonl}")
    print(f"Wrote: {args.summary_json}")
    print(
        "Applied manual overrides: "
        f"{applied} (include={include_true}, exclude={include_false}, flips={flip_count})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
