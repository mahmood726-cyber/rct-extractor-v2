#!/usr/bin/env python3
"""Build an explicit comparison report against published meta-analysis effects."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{100.0 * float(value):.1f}%"


def _safe_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-label", type=str, required=True)
    parser.add_argument("--human-error-json", type=Path, required=True)
    parser.add_argument("--results-json", type=Path, required=True)
    parser.add_argument("--ma-records-jsonl", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    human = _load_json(args.human_error_json)
    summary = human.get("summary") or {}
    studies: List[Dict] = human.get("studies") or []
    results: List[Dict] = _load_json(args.results_json)

    point_fail = [row for row in studies if row.get("within_10pct") is False]
    ci_fail = [row for row in studies if row.get("ci_within_10pct") is False]
    status_error = [row for row in studies if str(row.get("status")) == "error"]

    status_counts = Counter(str(row.get("status") or "unknown") for row in results)
    tier_counts = Counter(str(row.get("automation_tier") or "unknown") for row in studies)
    needs_review_count = sum(1 for row in studies if row.get("needs_review"))

    ma_records_total = 0
    if args.ma_records_jsonl is not None and args.ma_records_jsonl.exists():
        ma_records_total = len(_load_jsonl(args.ma_records_jsonl))

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cohort_label": args.cohort_label,
        "inputs": {
            "human_error_json": str(args.human_error_json).replace("\\", "/"),
            "results_json": str(args.results_json).replace("\\", "/"),
            "ma_records_jsonl": (
                str(args.ma_records_jsonl).replace("\\", "/")
                if args.ma_records_jsonl is not None
                else None
            ),
        },
        "published_meta_comparison": {
            "point_comparable_trials": _safe_int(summary.get("point_comparable_trials")),
            "point_within_10pct_rate": summary.get("point_within_10pct_rate"),
            "point_within_10pct_bootstrap_95ci": summary.get("point_within_10pct_bootstrap_95ci"),
            "ci_comparable_trials": _safe_int(summary.get("ci_comparable_trials")),
            "ci_within_10pct_rate": summary.get("ci_within_10pct_rate"),
            "ci_within_10pct_bootstrap_95ci": summary.get("ci_within_10pct_bootstrap_95ci"),
            "effect_type_match_rate": summary.get("effect_type_match_rate"),
        },
        "pipeline_quality": {
            "status_counts": dict(sorted(status_counts.items())),
            "automation_tier_counts": dict(sorted(tier_counts.items())),
            "needs_review_trials": needs_review_count,
            "ma_contract_records_total": ma_records_total,
        },
        "outliers": {
            "point_outside_10pct": [row.get("study_id") for row in point_fail],
            "ci_outside_10pct": [row.get("study_id") for row in ci_fail],
            "error_status": [row.get("study_id") for row in status_error],
        },
    }

    lines: List[str] = []
    lines.append(f"# {args.cohort_label} Published-Meta Comparison")
    lines.append("")
    lines.append(f"- Generated UTC: {payload['generated_at_utc']}")
    lines.append(f"- Human-error envelope: 10% relative tolerance")
    lines.append("")
    lines.append("## Agreement vs Published Meta Effects")
    lines.append("")
    lines.append(
        f"- Point agreement <=10%: {_pct(summary.get('point_within_10pct_rate'))} "
        f"on {_safe_int(summary.get('point_comparable_trials'))} comparable trials"
    )
    point_ci = summary.get("point_within_10pct_bootstrap_95ci") or {}
    if point_ci:
        lines.append(
            f"- Point <=10% bootstrap 95% CI: {_pct(point_ci.get('ci_low_95'))} to {_pct(point_ci.get('ci_high_95'))}"
        )
    lines.append(
        f"- CI-bound agreement <=10%: {_pct(summary.get('ci_within_10pct_rate'))} "
        f"on {_safe_int(summary.get('ci_comparable_trials'))} comparable trials"
    )
    ci_ci = summary.get("ci_within_10pct_bootstrap_95ci") or {}
    if ci_ci:
        lines.append(
            f"- CI <=10% bootstrap 95% CI: {_pct(ci_ci.get('ci_low_95'))} to {_pct(ci_ci.get('ci_high_95'))}"
        )
    lines.append(f"- Effect-type match: {_pct(summary.get('effect_type_match_rate'))}")
    lines.append("")
    lines.append("## MA Contract And Review Burden")
    lines.append("")
    lines.append(f"- Status counts: {dict(sorted(status_counts.items()))}")
    lines.append(f"- Automation tiers: {dict(sorted(tier_counts.items()))}")
    lines.append(f"- Needs-review trials: {needs_review_count}")
    if args.ma_records_jsonl is not None:
        lines.append(f"- MA-contract records emitted: {ma_records_total}")
    lines.append("")
    lines.append("## Outliers")
    lines.append("")
    lines.append(f"- Point outside 10%: {len(point_fail)}")
    lines.append(f"- CI outside 10%: {len(ci_fail)}")
    lines.append(f"- Error status: {len(status_error)}")
    lines.append("")
    lines.append("| Study ID | Status | Point Err | CI Err Max | Needs Review | Tier |")
    lines.append("| --- | --- | ---: | ---: | --- | --- |")
    ranked = sorted(
        studies,
        key=lambda row: (
            0 if row.get("within_10pct") is False else 1,
            0 if row.get("ci_within_10pct") is False else 1,
            str(row.get("study_id") or ""),
        ),
    )
    for row in ranked:
        point_err = row.get("point_rel_error")
        ci_err = row.get("ci_rel_error_max")
        lines.append(
            "| "
            f"{row.get('study_id') or ''} | {row.get('status') or ''} | "
            f"{(f'{float(point_err):.6f}' if point_err is not None else 'n/a')} | "
            f"{(f'{float(ci_err):.6f}' if ci_err is not None else 'n/a')} | "
            f"{'yes' if row.get('needs_review') else 'no'} | {row.get('automation_tier') or 'n/a'} |"
        )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

