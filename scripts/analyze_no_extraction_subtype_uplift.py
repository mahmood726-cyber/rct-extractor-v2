#!/usr/bin/env python3
"""Analyze no-extraction uplift by subtype between two mega_eval snapshots."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


def _canonical_study_key(study_id: str) -> str:
    text = unicodedata.normalize("NFKD", str(study_id))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return text


def _load_latest_rows(path: Path) -> Dict[str, dict]:
    latest: Dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            study_id = row.get("study_id")
            if not study_id:
                continue
            key = _canonical_study_key(study_id)
            if key:
                latest[key] = row
    return latest


def _derive_subtype(row: dict) -> str:
    cochrane = row.get("cochrane") or []
    data_types = set()
    has_raw = False
    for item in cochrane:
        dt = str(item.get("data_type") or "").strip().lower()
        if dt:
            data_types.add(dt)
        if isinstance(item.get("raw_data"), dict) and item.get("raw_data"):
            has_raw = True

    if not data_types:
        primary = "unknown"
    elif len(data_types) == 1:
        primary = next(iter(data_types))
    else:
        primary = "mixed"

    raw_label = "with_raw" if has_raw else "no_raw"
    return f"{primary}|{raw_label}"


def _pct(num: int, den: int) -> float:
    return (num / den) if den else 0.0


def analyze(before_path: Path, after_path: Path) -> dict:
    before = _load_latest_rows(before_path)
    after = _load_latest_rows(after_path)

    baseline_keys = [
        k for k, row in before.items() if str(row.get("status")) == "no_extraction"
    ]

    by_subtype_total: Counter = Counter()
    by_subtype_resolved: Counter = Counter()
    by_subtype_to_match: Counter = Counter()
    by_subtype_to_extracted: Counter = Counter()
    by_subtype_after_status: Dict[str, Counter] = defaultdict(Counter)

    resolved = 0
    to_match = 0
    to_extracted = 0

    for key in baseline_keys:
        before_row = before[key]
        subtype = _derive_subtype(before_row)
        by_subtype_total[subtype] += 1

        after_row = after.get(key) or {}
        after_status = str(after_row.get("status") or "missing_after")
        by_subtype_after_status[subtype][after_status] += 1

        if after_status != "no_extraction":
            resolved += 1
            by_subtype_resolved[subtype] += 1
            if after_status == "match":
                to_match += 1
                by_subtype_to_match[subtype] += 1
            if after_status in {"match", "extracted_no_match"}:
                to_extracted += 1
                by_subtype_to_extracted[subtype] += 1

    subtype_rows: List[dict] = []
    for subtype, total in sorted(by_subtype_total.items(), key=lambda kv: (-kv[1], kv[0])):
        subtype_rows.append(
            {
                "subtype": subtype,
                "total_before_no_extraction": total,
                "resolved_any": int(by_subtype_resolved[subtype]),
                "resolved_any_rate": _pct(int(by_subtype_resolved[subtype]), total),
                "to_match": int(by_subtype_to_match[subtype]),
                "to_match_rate": _pct(int(by_subtype_to_match[subtype]), total),
                "to_extracted_any": int(by_subtype_to_extracted[subtype]),
                "to_extracted_any_rate": _pct(int(by_subtype_to_extracted[subtype]), total),
                "after_status_counts": dict(by_subtype_after_status[subtype]),
            }
        )

    return {
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "before_eval": str(before_path),
        "after_eval": str(after_path),
        "baseline_no_extraction_total": len(baseline_keys),
        "resolved_any_total": resolved,
        "resolved_any_rate": _pct(resolved, len(baseline_keys)),
        "to_match_total": to_match,
        "to_match_rate": _pct(to_match, len(baseline_keys)),
        "to_extracted_any_total": to_extracted,
        "to_extracted_any_rate": _pct(to_extracted, len(baseline_keys)),
        "subtypes": subtype_rows,
    }


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def to_markdown(report: dict) -> str:
    lines = [
        "# No-Extraction Uplift by Subtype",
        "",
        f"- Generated UTC: {report['computed_at_utc']}",
        f"- Baseline no-extraction pool: {report['baseline_no_extraction_total']}",
        f"- Resolved (any): {report['resolved_any_total']} ({_fmt_pct(report['resolved_any_rate'])})",
        f"- Converted to extracted (match+extracted_no_match): {report['to_extracted_any_total']} ({_fmt_pct(report['to_extracted_any_rate'])})",
        f"- Converted to match: {report['to_match_total']} ({_fmt_pct(report['to_match_rate'])})",
        "",
        "| Subtype | Baseline | Resolved | To Extracted | To Match |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report["subtypes"]:
        lines.append(
            f"| {row['subtype']} "
            f"| {row['total_before_no_extraction']} "
            f"| {row['resolved_any']} ({_fmt_pct(row['resolved_any_rate'])}) "
            f"| {row['to_extracted_any']} ({_fmt_pct(row['to_extracted_any_rate'])}) "
            f"| {row['to_match']} ({_fmt_pct(row['to_match_rate'])}) |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True, help="Baseline mega_eval JSONL snapshot")
    parser.add_argument("--after", type=Path, required=True, help="Post-run mega_eval JSONL snapshot")
    parser.add_argument("--output-json", type=Path, default=Path("output/no_extraction_uplift_by_subtype.json"))
    parser.add_argument("--output-md", type=Path, default=Path("output/no_extraction_uplift_by_subtype.md"))
    args = parser.parse_args()

    if not args.before.exists():
        raise FileNotFoundError(f"Before snapshot not found: {args.before}")
    if not args.after.exists():
        raise FileNotFoundError(f"After snapshot not found: {args.after}")

    report = analyze(before_path=args.before, after_path=args.after)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    args.output_md.write_text(to_markdown(report), encoding="utf-8", newline="\n")

    print(f"Wrote JSON: {args.output_json}")
    print(f"Wrote MD: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
