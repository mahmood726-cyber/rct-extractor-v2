#!/usr/bin/env python3
"""Build human-error-envelope agreement report for mega real-data eval artifacts."""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence


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


def _rel_error(extracted: float, expected: float, zero_abs_tolerance: float) -> float:
    if abs(expected) < 1e-12:
        return abs(extracted - expected) / max(zero_abs_tolerance, 1e-12)
    return abs(extracted - expected) / abs(expected)


def _bootstrap_rate(values: Sequence[bool], *, n_bootstrap: int, seed: int) -> Optional[Dict[str, float]]:
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    int_values = [1 if v else 0 for v in values]
    samples: List[float] = []
    for _ in range(n_bootstrap):
        hit = 0
        for _ in range(n):
            hit += int_values[rng.randrange(n)]
        samples.append(hit / n)
    samples.sort()
    low_idx = int(0.025 * (n_bootstrap - 1))
    high_idx = int(0.975 * (n_bootstrap - 1))
    return {
        "point": sum(int_values) / n,
        "ci_low_95": samples[low_idx],
        "ci_high_95": samples[high_idx],
    }


def _fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{100.0 * value:.1f}%"


def _best_direct_rel_error(row: Dict, zero_abs_tolerance: float) -> Optional[float]:
    extracted_values = [
        _to_float(item.get("point_estimate"))
        for item in (row.get("extracted") or [])
    ]
    extracted_values = [v for v in extracted_values if v is not None]
    cochrane_values = [
        _to_float(item.get("effect"))
        for item in (row.get("cochrane") or [])
    ]
    cochrane_values = [v for v in cochrane_values if v is not None]
    if not extracted_values or not cochrane_values:
        return None
    best: Optional[float] = None
    for ext in extracted_values:
        for ref in cochrane_values:
            err = _rel_error(ext, ref, zero_abs_tolerance)
            if best is None or err < best:
                best = err
    return best


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mega-eval-jsonl",
        type=Path,
        default=Path("gold_data/mega/mega_eval.jsonl"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        required=True,
    )
    parser.add_argument("--n-bootstrap", type=int, default=20000)
    parser.add_argument("--rng-seed", type=int, default=20260224)
    parser.add_argument("--zero-abs-tolerance", type=float, default=0.02)
    args = parser.parse_args()

    if args.n_bootstrap <= 0:
        raise ValueError("--n-bootstrap must be > 0")

    rows = _load_jsonl(args.mega_eval_jsonl)
    with_ref = [row for row in rows if (row.get("cochrane") or [])]
    with_pmcid = [row for row in rows if row.get("pmcid")]

    within_5_status: List[bool] = []
    within_10_status: List[bool] = []
    residual_rows: List[Dict] = []

    for row in with_ref:
        status = str(row.get("status") or "")
        is_match = status == "match"
        within_5_status.append(is_match)
        within_10_status.append(is_match)

        best_direct = _best_direct_rel_error(row, args.zero_abs_tolerance)

        if is_match:
            continue
        residual_rows.append(
            {
                "study_id": row.get("study_id"),
                "status": status,
                "pmcid": row.get("pmcid"),
                "n_extracted": row.get("n_extracted"),
                "n_cochrane": row.get("n_cochrane"),
                "best_direct_rel_error": best_direct,
            }
        )

    residual_rows.sort(
        key=lambda item: (
            float("inf") if item["best_direct_rel_error"] is None else item["best_direct_rel_error"],
            str(item.get("study_id") or ""),
        )
    )

    strict_5_rate = sum(1 for flag in within_5_status if flag) / len(within_5_status) if within_5_status else None
    envelope_10_status_rate = (
        sum(1 for flag in within_10_status if flag) / len(within_10_status) if within_10_status else None
    )
    bootstrap_10 = _bootstrap_rate(
        within_10_status,
        n_bootstrap=args.n_bootstrap,
        seed=args.rng_seed,
    )

    summary = {
        "total_rows": len(rows),
        "rows_with_pmcid": len(with_pmcid),
        "rows_with_cochrane_ref": len(with_ref),
        "strict_5pct_match_rate": strict_5_rate,
        "human_error_10pct_rate_status_based": envelope_10_status_rate,
        "human_error_10pct_bootstrap_95ci": bootstrap_10,
        "residual_rows_count": len(residual_rows),
    }

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "mega_eval_jsonl": str(args.mega_eval_jsonl).replace("\\", "/"),
            "n_bootstrap": args.n_bootstrap,
            "rng_seed": args.rng_seed,
            "zero_abs_tolerance": args.zero_abs_tolerance,
        },
        "summary": summary,
        "residual_rows": residual_rows,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines: List[str] = []
    lines.append("# Mega Real-Data Human-Error Agreement Report")
    lines.append("")
    lines.append(f"- Generated UTC: {payload['generated_at_utc']}")
    lines.append(f"- Input: `{payload['inputs']['mega_eval_jsonl']}`")
    lines.append("- Human-error envelope target: `10%` relative point-estimate error")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total rows: {summary['total_rows']}")
    lines.append(f"- Rows with PMCID: {summary['rows_with_pmcid']}")
    lines.append(f"- Rows with Cochrane reference: {summary['rows_with_cochrane_ref']}")
    lines.append(f"- Strict match rate (5% criterion from eval status): {_fmt_pct(summary['strict_5pct_match_rate'])}")
    lines.append(
        "- 10% envelope agreement (status-based, conservative): "
        f"{_fmt_pct(summary['human_error_10pct_rate_status_based'])}"
    )
    if bootstrap_10:
        lines.append(
            "- 10% envelope bootstrap 95% CI (status-based): "
            f"{_fmt_pct(bootstrap_10['point'])} "
            f"({_fmt_pct(bootstrap_10['ci_low_95'])} to {_fmt_pct(bootstrap_10['ci_high_95'])})"
        )
    lines.append(f"- Residual non-match rows: {summary['residual_rows_count']}")
    lines.append("")
    lines.append("## Residual Rows")
    lines.append("")
    lines.append("| Study ID | Status | PMCID | n_extracted | n_cochrane | Best Direct Rel Error |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: |")
    for row in residual_rows:
        err = row.get("best_direct_rel_error")
        lines.append(
            f"| {row.get('study_id') or ''} | {row.get('status') or ''} | {row.get('pmcid') or ''} | "
            f"{row.get('n_extracted') or 0} | {row.get('n_cochrane') or 0} | "
            f"{(f'{err:.6f}' if isinstance(err, (int, float)) else 'n/a')} |"
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "- This artifact provides broad-N real-data agreement evidence for point estimates; "
        "CI-field reliability should be evaluated separately."
    )

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
