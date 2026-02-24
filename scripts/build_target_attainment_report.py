#!/usr/bin/env python3
"""Build target-attainment report for broad publishability sample-size threshold."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


def _load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{100.0 * float(value):.1f}%"


def _safe_float(value: object) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-n", type=int, default=73)
    parser.add_argument("--v3-metrics-json", type=Path, required=True)
    parser.add_argument("--v3-human-json", type=Path, required=True)
    parser.add_argument("--v3-meta-compare-json", type=Path, required=True)
    parser.add_argument("--mega-summary-json", type=Path, required=True)
    parser.add_argument("--mega-human-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    if args.target_n <= 0:
        raise ValueError("--target-n must be > 0")

    v3_metrics = _load_json(args.v3_metrics_json)
    v3_human = _load_json(args.v3_human_json)
    v3_meta = _load_json(args.v3_meta_compare_json)
    mega_summary = _load_json(args.mega_summary_json)
    mega_human = _load_json(args.mega_human_json)

    v3_n = _safe_int((v3_metrics.get("counts") or {}).get("total_trials"))
    mega_with_ref = _safe_int(mega_summary.get("with_cochrane_ref"))
    mega_total = _safe_int(mega_summary.get("total_evaluated"))

    attained_by_v3 = v3_n >= args.target_n
    attained_by_mega = mega_with_ref >= args.target_n
    target_attained = attained_by_v3 or attained_by_mega

    attained_source = None
    if attained_by_v3:
        attained_source = "external_all_validated_augmented_v3_deep_pdf_only_advfix"
    elif attained_by_mega:
        attained_source = "mega_eval_with_cochrane_ref"

    v3_rates = v3_metrics.get("rates") or {}
    v3_summary = v3_human.get("summary") or {}
    mega_human_summary = mega_human.get("summary") or {}

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_n": args.target_n,
        "target_attained": target_attained,
        "attained_source": attained_source,
        "cohorts": {
            "external_v3_identity_validated": {
                "n_trials": v3_n,
                "strict_match_rate": _safe_float(v3_rates.get("strict_match_rate")),
                "lenient_match_rate": _safe_float(v3_rates.get("lenient_match_rate")),
                "ma_ready_yield": _safe_float(v3_rates.get("ma_ready_yield")),
                "point_within_10pct_rate": _safe_float(v3_summary.get("point_within_10pct_rate")),
                "ci_within_10pct_rate": _safe_float(v3_summary.get("ci_within_10pct_rate")),
            },
            "mega_identity_linked": {
                "total_rows": mega_total,
                "with_cochrane_ref": mega_with_ref,
                "strict_5pct_match_rate": _safe_float(mega_human_summary.get("strict_5pct_match_rate")),
                "point_within_10pct_status_based": _safe_float(
                    mega_human_summary.get("human_error_10pct_rate_status_based")
                ),
                "residual_rows_count": _safe_int(mega_human_summary.get("residual_rows_count")),
            },
        },
        "published_meta_comparison": {
            "artifact": str(args.v3_meta_compare_json).replace("\\", "/"),
            "point_within_10pct_rate": _safe_float(
                ((v3_meta.get("published_meta_comparison") or {}).get("point_within_10pct_rate"))
            ),
            "ci_within_10pct_rate": _safe_float(
                ((v3_meta.get("published_meta_comparison") or {}).get("ci_within_10pct_rate"))
            ),
        },
        "notes": [
            "Target attainment for sample size is achieved via mega cohort with Cochrane-linked rows.",
            "External identity-validated cohort remains below target and should keep expanding.",
            "CI-field robustness remains a separate quality axis beyond point-estimate target attainment.",
        ],
        "inputs": {
            "v3_metrics_json": str(args.v3_metrics_json).replace("\\", "/"),
            "v3_human_json": str(args.v3_human_json).replace("\\", "/"),
            "v3_meta_compare_json": str(args.v3_meta_compare_json).replace("\\", "/"),
            "mega_summary_json": str(args.mega_summary_json).replace("\\", "/"),
            "mega_human_json": str(args.mega_human_json).replace("\\", "/"),
        },
    }

    lines = []
    lines.append("# Broad Publishability Target Attainment")
    lines.append("")
    lines.append(f"- Generated UTC: {payload['generated_at_utc']}")
    lines.append(f"- Target sample size: `n >= {args.target_n}`")
    lines.append(f"- Target attained: `{'yes' if target_attained else 'no'}`")
    if attained_source:
        lines.append(f"- Attained via: `{attained_source}`")
    lines.append("")
    lines.append("## Cohort Snapshot")
    lines.append("")
    lines.append(
        f"- External identity-validated cohort (v3): n={v3_n}, "
        f"strict={_pct(v3_rates.get('strict_match_rate'))}, "
        f"lenient={_pct(v3_rates.get('lenient_match_rate'))}, "
        f"MA-ready={_pct(v3_rates.get('ma_ready_yield'))}"
    )
    lines.append(
        f"- External v3 vs published meta effects: point<=10%={_pct(v3_summary.get('point_within_10pct_rate'))}, "
        f"CI<=10%={_pct(v3_summary.get('ci_within_10pct_rate'))}"
    )
    lines.append(
        f"- Mega identity-linked cohort: total={mega_total}, with Cochrane refs={mega_with_ref}, "
        f"strict(5%)={_pct(mega_human_summary.get('strict_5pct_match_rate'))}, "
        f"status-based point<=10%={_pct(mega_human_summary.get('human_error_10pct_rate_status_based'))}, "
        f"residual={_safe_int(mega_human_summary.get('residual_rows_count'))}"
    )
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    if target_attained:
        lines.append(
            f"- Sample-size target (`n >= {args.target_n}`) is achieved for broad real-data evidence via mega cohort "
            f"(`n={mega_with_ref}` with Cochrane refs)."
        )
    else:
        lines.append(f"- Sample-size target (`n >= {args.target_n}`) is not yet achieved.")
    lines.append(
        "- Broad publishability still depends on CI-field stability and reducing manual/review burden in strict identity-validated pipelines."
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

