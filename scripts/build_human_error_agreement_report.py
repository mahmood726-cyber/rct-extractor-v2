#!/usr/bin/env python3
"""Build agreement report under a human-extraction error tolerance envelope."""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


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


def _to_float(value: object) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _rel_err(extracted: float, expected: float, zero_abs_tolerance: float) -> float:
    if abs(expected) < 1e-12:
        return abs(extracted - expected) / max(zero_abs_tolerance, 1e-12)
    return abs(extracted - expected) / abs(expected)


def _format_pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{100.0 * value:.1f}%"


def _cohort_gold_point(row: Dict) -> Optional[float]:
    gold = row.get("gold") or {}
    point = _to_float(gold.get("point_estimate"))
    if point is not None:
        return point
    return _to_float(row.get("cochrane_effect"))


def _cohort_gold_ci(row: Dict) -> Tuple[Optional[float], Optional[float]]:
    gold = row.get("gold") or {}
    ci_low = _to_float(gold.get("ci_lower"))
    ci_high = _to_float(gold.get("ci_upper"))
    if ci_low is not None and ci_high is not None:
        return ci_low, ci_high
    return _to_float(row.get("cochrane_ci_lower")), _to_float(row.get("cochrane_ci_upper"))


def _cohort_gold_type(row: Dict) -> Optional[str]:
    gold = row.get("gold") or {}
    value = str(gold.get("effect_type") or "").strip().upper()
    return value or None


def _result_best(row: Dict) -> Dict:
    return row.get("best_match") or {}


def _bootstrap_rate(
    values: Sequence[bool],
    *,
    n_bootstrap: int,
    rng_seed: int,
) -> Optional[Dict[str, float]]:
    if not values:
        return None
    rng = random.Random(rng_seed)
    n = len(values)
    fractions: List[float] = []
    int_values = [1 if v else 0 for v in values]
    for _ in range(n_bootstrap):
        hits = 0
        for _ in range(n):
            hits += int_values[rng.randrange(n)]
        fractions.append(hits / n)
    fractions.sort()
    low_idx = int(0.025 * (n_bootstrap - 1))
    high_idx = int(0.975 * (n_bootstrap - 1))
    return {
        "point": sum(int_values) / n,
        "ci_low_95": fractions[low_idx],
        "ci_high_95": fractions[high_idx],
    }


def _bool_text(value: Optional[bool]) -> str:
    if value is None:
        return "n/a"
    return "yes" if value else "no"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-label", type=str, required=True)
    parser.add_argument("--gold-jsonl", type=Path, required=True)
    parser.add_argument("--results-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--n-bootstrap", type=int, default=20000)
    parser.add_argument("--rng-seed", type=int, default=20260224)
    parser.add_argument(
        "--zero-abs-tolerance",
        type=float,
        default=0.02,
        help="Absolute tolerance used when gold point estimate is zero.",
    )
    args = parser.parse_args()

    if args.n_bootstrap <= 0:
        raise ValueError("--n-bootstrap must be > 0")

    gold_rows = _load_jsonl(args.gold_jsonl)
    raw_results = _load_json(args.results_json)
    results_rows = raw_results if isinstance(raw_results, list) else raw_results.get("results", [])
    result_by_id = {str(row.get("study_id")): row for row in results_rows if row.get("study_id")}

    per_study: List[Dict] = []
    within_1: List[bool] = []
    within_2: List[bool] = []
    within_5: List[bool] = []
    within_10: List[bool] = []
    ci_within_10: List[bool] = []
    type_match_flags: List[bool] = []

    for gold_row in gold_rows:
        study_id = str(gold_row.get("study_id") or "")
        if not study_id:
            continue
        result_row = result_by_id.get(study_id)
        best = _result_best(result_row or {})

        expected_point = _cohort_gold_point(gold_row)
        expected_ci_low, expected_ci_high = _cohort_gold_ci(gold_row)
        expected_type = _cohort_gold_type(gold_row)

        extracted_point = _to_float(best.get("effect_size"))
        extracted_ci_low = _to_float(best.get("ci_lower"))
        extracted_ci_high = _to_float(best.get("ci_upper"))
        extracted_type = str(best.get("type") or "").strip().upper() or None

        point_rel_error: Optional[float] = None
        if expected_point is not None and extracted_point is not None:
            point_rel_error = _rel_err(
                extracted=extracted_point,
                expected=expected_point,
                zero_abs_tolerance=args.zero_abs_tolerance,
            )
            within_1_flag = point_rel_error <= 0.01
            within_2_flag = point_rel_error <= 0.02
            within_5_flag = point_rel_error <= 0.05
            within_10_flag = point_rel_error <= 0.10
            within_1.append(within_1_flag)
            within_2.append(within_2_flag)
            within_5.append(within_5_flag)
            within_10.append(within_10_flag)
        else:
            within_1_flag = None
            within_2_flag = None
            within_5_flag = None
            within_10_flag = None

        ci_rel_error_max: Optional[float] = None
        if (
            expected_ci_low is not None
            and expected_ci_high is not None
            and extracted_ci_low is not None
            and extracted_ci_high is not None
        ):
            low_rel = _rel_err(extracted_ci_low, expected_ci_low, args.zero_abs_tolerance)
            high_rel = _rel_err(extracted_ci_high, expected_ci_high, args.zero_abs_tolerance)
            ci_rel_error_max = max(low_rel, high_rel)
            ci_10_flag = ci_rel_error_max <= 0.10
            ci_within_10.append(ci_10_flag)
        else:
            ci_10_flag = None

        type_match: Optional[bool] = None
        if expected_type and extracted_type:
            type_match = expected_type == extracted_type
            type_match_flags.append(type_match)

        per_study.append(
            {
                "study_id": study_id,
                "status": (result_row or {}).get("status"),
                "expected_type": expected_type,
                "extracted_type": extracted_type,
                "type_match": type_match,
                "expected_point": expected_point,
                "extracted_point": extracted_point,
                "point_rel_error": point_rel_error,
                "within_1pct": within_1_flag,
                "within_2pct": within_2_flag,
                "within_5pct": within_5_flag,
                "within_10pct": within_10_flag,
                "expected_ci_low": expected_ci_low,
                "expected_ci_high": expected_ci_high,
                "extracted_ci_low": extracted_ci_low,
                "extracted_ci_high": extracted_ci_high,
                "ci_rel_error_max": ci_rel_error_max,
                "ci_within_10pct": ci_10_flag,
                "automation_tier": best.get("automation_tier"),
                "needs_review": bool(best.get("needs_review")),
                "source_text": best.get("source_text"),
            }
        )

    point_bootstrap = _bootstrap_rate(within_10, n_bootstrap=args.n_bootstrap, rng_seed=args.rng_seed)
    ci_bootstrap = _bootstrap_rate(ci_within_10, n_bootstrap=args.n_bootstrap, rng_seed=args.rng_seed + 7)

    summary = {
        "cohort_label": args.cohort_label,
        "total_gold_trials": len(per_study),
        "results_present_trials": sum(1 for row in per_study if row["status"] is not None),
        "point_comparable_trials": len(within_10),
        "ci_comparable_trials": len(ci_within_10),
        "type_comparable_trials": len(type_match_flags),
        "point_within_1pct_rate": (sum(1 for flag in within_1 if flag) / len(within_1)) if within_1 else None,
        "point_within_2pct_rate": (sum(1 for flag in within_2 if flag) / len(within_2)) if within_2 else None,
        "point_within_5pct_rate": (sum(1 for flag in within_5 if flag) / len(within_5)) if within_5 else None,
        "point_within_10pct_rate": (sum(1 for flag in within_10 if flag) / len(within_10)) if within_10 else None,
        "ci_within_10pct_rate": (sum(1 for flag in ci_within_10 if flag) / len(ci_within_10))
        if ci_within_10
        else None,
        "effect_type_match_rate": (sum(1 for flag in type_match_flags if flag) / len(type_match_flags))
        if type_match_flags
        else None,
        "point_within_10pct_bootstrap_95ci": point_bootstrap,
        "ci_within_10pct_bootstrap_95ci": ci_bootstrap,
        "needs_review_trials": sum(1 for row in per_study if row["needs_review"]),
        "manual_tier_trials": sum(1 for row in per_study if row["automation_tier"] == "manual"),
    }

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "cohort_label": args.cohort_label,
            "gold_jsonl": str(args.gold_jsonl).replace("\\", "/"),
            "results_json": str(args.results_json).replace("\\", "/"),
            "n_bootstrap": args.n_bootstrap,
            "rng_seed": args.rng_seed,
            "zero_abs_tolerance": args.zero_abs_tolerance,
        },
        "summary": summary,
        "studies": sorted(per_study, key=lambda row: row["study_id"]),
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines: List[str] = []
    lines.append(f"# {args.cohort_label} Human-Error Agreement Report")
    lines.append("")
    lines.append(f"- Generated UTC: {payload['generated_at_utc']}")
    lines.append(f"- Gold JSONL: `{payload['inputs']['gold_jsonl']}`")
    lines.append(f"- Results JSON: `{payload['inputs']['results_json']}`")
    lines.append(f"- Human-error tolerance target: `10%` relative error")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total gold trials: {summary['total_gold_trials']}")
    lines.append(f"- Results present: {summary['results_present_trials']}")
    lines.append(f"- Point-comparable trials: {summary['point_comparable_trials']}")
    lines.append(f"- CI-comparable trials: {summary['ci_comparable_trials']}")
    lines.append(f"- Effect-type-comparable trials: {summary['type_comparable_trials']}")
    lines.append(f"- Point agreement within 1%: {_format_pct(summary['point_within_1pct_rate'])}")
    lines.append(f"- Point agreement within 2%: {_format_pct(summary['point_within_2pct_rate'])}")
    lines.append(f"- Point agreement within 5%: {_format_pct(summary['point_within_5pct_rate'])}")
    lines.append(f"- Point agreement within 10%: {_format_pct(summary['point_within_10pct_rate'])}")
    lines.append(f"- CI bound agreement within 10%: {_format_pct(summary['ci_within_10pct_rate'])}")
    lines.append(f"- Effect-type match: {_format_pct(summary['effect_type_match_rate'])}")
    lines.append(f"- Manual-tier trials: {summary['manual_tier_trials']}")
    lines.append(f"- Needs-review trials: {summary['needs_review_trials']}")
    lines.append("")

    point_ci = summary["point_within_10pct_bootstrap_95ci"]
    if point_ci:
        lines.append("## Bootstrap 95% CI")
        lines.append("")
        lines.append(
            "- Point agreement within 10%: "
            f"{_format_pct(point_ci['point'])} "
            f"({_format_pct(point_ci['ci_low_95'])} to {_format_pct(point_ci['ci_high_95'])})"
        )
        ci_ci = summary["ci_within_10pct_bootstrap_95ci"]
        if ci_ci:
            lines.append(
                "- CI agreement within 10%: "
                f"{_format_pct(ci_ci['point'])} "
                f"({_format_pct(ci_ci['ci_low_95'])} to {_format_pct(ci_ci['ci_high_95'])})"
            )
        lines.append("")

    lines.append("## Study Detail")
    lines.append("")
    lines.append("| Study ID | Type Match | Point Err | <=10% | CI Err Max | CI <=10% | Tier | Needs Review |")
    lines.append("| --- | --- | ---: | --- | ---: | --- | --- | --- |")
    for row in payload["studies"]:
        point_err = row["point_rel_error"]
        ci_err = row["ci_rel_error_max"]
        lines.append(
            f"| {row['study_id']} | {_bool_text(row['type_match'])} | "
            f"{(f'{point_err:.6f}' if point_err is not None else 'n/a')} | {_bool_text(row['within_10pct'])} | "
            f"{(f'{ci_err:.6f}' if ci_err is not None else 'n/a')} | {_bool_text(row['ci_within_10pct'])} | "
            f"{row.get('automation_tier') or 'n/a'} | {'yes' if row.get('needs_review') else 'no'} |"
        )

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
