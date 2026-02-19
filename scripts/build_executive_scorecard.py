#!/usr/bin/env python3
"""Build a concise executive scorecard for real-RCT extraction progress."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_json_optional(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return dict(default)
    return _load_json(path)


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def _build_scorecard(
    mega_summary: Dict[str, Any],
    timeout_report: Dict[str, Any],
    no_extract_report: Dict[str, Any],
    outside_benchmark: Dict[str, Any],
) -> Dict[str, Any]:
    counts = dict(mega_summary.get("counts") or {})
    total = int(mega_summary.get("total_evaluated") or mega_summary.get("total") or 0)
    with_ref = int(mega_summary.get("with_cochrane_ref") or 0)

    no_extraction = int(counts.get("no_extraction", 0))
    match = int(counts.get("match", 0))
    extracted_no_match = int(counts.get("extracted_no_match", 0))
    timeout_left = int(counts.get("timeout_skipped_by_batch_runner", 0))

    extraction_rate = float(mega_summary.get("extraction_rate") or _safe_div(match + extracted_no_match, with_ref))
    match_rate = float(mega_summary.get("match_rate") or _safe_div(match, with_ref))

    timeout_start = int(timeout_report.get("start_rerun_candidates") or 0)
    timeout_end = int(timeout_report.get("end_rerun_candidates") or 0)
    timeout_cleared = max(0, timeout_start - timeout_end)
    timeout_clear_rate = _safe_div(timeout_cleared, timeout_start) if timeout_start else 0.0

    no_extract_start = int(no_extract_report.get("start_rerun_candidates") or 0)
    no_extract_end = int(no_extract_report.get("end_rerun_candidates") or 0)
    no_extract_reduced = max(0, no_extract_start - no_extract_end)
    no_extract_reduction_rate = _safe_div(no_extract_reduced, no_extract_start) if no_extract_start else 0.0

    full = (outside_benchmark.get("evaluations") or {}).get("full_set") or {}
    system_names = sorted(full.keys())
    current_name = next((n for n in system_names if "upgraded_v4" in n), system_names[0] if system_names else "")
    current_rates = (full.get(current_name) or {}).get("rates") or {}
    baseline_rates = (full.get("baseline_results") or {}).get("rates") or {}
    external_rates = (full.get("external_mega_v10_merged") or {}).get("rates") or {}

    return {
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "mega": {
            "total_evaluated": total,
            "with_cochrane_ref": with_ref,
            "counts": counts,
            "rates": {
                "match_rate": match_rate,
                "extraction_rate": extraction_rate,
                "no_extraction_rate": _safe_div(no_extraction, with_ref),
            },
            "operational": {
                "timeout_placeholders_remaining": timeout_left,
                "duplicate_rows": int(mega_summary.get("duplicate_rows") or 0),
            },
        },
        "campaigns": {
            "timeout_clear": {
                "start": timeout_start,
                "end": timeout_end,
                "cleared": timeout_cleared,
                "clear_rate": timeout_clear_rate,
                "rounds": int(timeout_report.get("rounds") and len(timeout_report["rounds"]) or 0),
            },
            "no_extraction_targeted": {
                "start": no_extract_start,
                "end": no_extract_end,
                "reduced": no_extract_reduced,
                "reduction_rate": no_extract_reduction_rate,
                "rounds": int(no_extract_report.get("rounds") and len(no_extract_report["rounds"]) or 0),
            },
        },
        "frozen_gold_benchmark": {
            "current_system": current_name,
            "current_rates": current_rates,
            "baseline_rates": baseline_rates,
            "external_mega_rates": external_rates,
        },
    }


def _to_markdown(scorecard: Dict[str, Any]) -> str:
    mega = scorecard["mega"]
    camp = scorecard["campaigns"]
    bench = scorecard["frozen_gold_benchmark"]
    counts = mega["counts"]
    rates = mega["rates"]

    lines = [
        "# Real-RCT Executive Scorecard",
        "",
        f"- Generated UTC: {scorecard['computed_at_utc']}",
        "",
        "## Mega vs Cochrane (Current)",
        "",
        f"- Evaluated studies: {mega['total_evaluated']}",
        f"- With Cochrane reference: {mega['with_cochrane_ref']}",
        f"- Match: {counts.get('match', 0)} ({_pct(rates['match_rate'])})",
        f"- Extracted (match+no-match): {counts.get('match', 0) + counts.get('extracted_no_match', 0)} ({_pct(rates['extraction_rate'])})",
        f"- No extraction: {counts.get('no_extraction', 0)} ({_pct(rates['no_extraction_rate'])})",
        f"- Timeout placeholders remaining: {mega['operational']['timeout_placeholders_remaining']}",
        f"- Duplicate rows: {mega['operational']['duplicate_rows']}",
        "",
        "## Campaign Impact",
        "",
        f"- Timeout clearance: {camp['timeout_clear']['start']} -> {camp['timeout_clear']['end']} (cleared {camp['timeout_clear']['cleared']}, {_pct(camp['timeout_clear']['clear_rate'])})",
        f"- No-extraction targeted pass: {camp['no_extraction_targeted']['start']} -> {camp['no_extraction_targeted']['end']} (reduced {camp['no_extraction_targeted']['reduced']}, {_pct(camp['no_extraction_targeted']['reduction_rate'])})",
        "",
        "## Frozen Gold (37-study) Benchmark",
        "",
        f"- Current system: `{bench['current_system']}`",
        f"- Current coverage/strict/MA-ready: {_pct(float(bench['current_rates'].get('extraction_coverage', 0.0)))}, {_pct(float(bench['current_rates'].get('strict_match_rate', 0.0)))}, {_pct(float(bench['current_rates'].get('ma_ready_yield', 0.0)))}",
        f"- Baseline coverage/strict/MA-ready: {_pct(float(bench['baseline_rates'].get('extraction_coverage', 0.0)))}, {_pct(float(bench['baseline_rates'].get('strict_match_rate', 0.0)))}, {_pct(float(bench['baseline_rates'].get('ma_ready_yield', 0.0)))}",
        f"- External mega coverage/strict/MA-ready: {_pct(float(bench['external_mega_rates'].get('extraction_coverage', 0.0)))}, {_pct(float(bench['external_mega_rates'].get('strict_match_rate', 0.0)))}, {_pct(float(bench['external_mega_rates'].get('ma_ready_yield', 0.0)))}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mega-summary", type=Path, default=Path("gold_data/mega/mega_eval_summary.json"))
    parser.add_argument(
        "--timeout-report",
        type=Path,
        default=Path("output/mega_batched_run_report_upsert_clear_timeouts.json"),
    )
    parser.add_argument(
        "--no-extraction-report",
        type=Path,
        default=Path("output/mega_batched_run_report_rerun_no_extraction_targeted_v2.json"),
    )
    parser.add_argument(
        "--outside-benchmark",
        type=Path,
        default=Path("output/outside_solution_benchmark_v4.json"),
    )
    parser.add_argument("--output-json", type=Path, default=Path("output/real_rct_executive_scorecard.json"))
    parser.add_argument("--output-md", type=Path, default=Path("output/real_rct_executive_scorecard.md"))
    args = parser.parse_args()

    mega_summary = _load_json(args.mega_summary)
    timeout_report = _load_json_optional(
        args.timeout_report,
        default={"start_rerun_candidates": 0, "end_rerun_candidates": 0, "rounds": []},
    )
    no_extract_report = _load_json_optional(
        args.no_extraction_report,
        default={"start_rerun_candidates": 0, "end_rerun_candidates": 0, "rounds": []},
    )
    outside_benchmark = _load_json(args.outside_benchmark)

    scorecard = _build_scorecard(
        mega_summary=mega_summary,
        timeout_report=timeout_report,
        no_extract_report=no_extract_report,
        outside_benchmark=outside_benchmark,
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(scorecard, handle, indent=2, ensure_ascii=False)

    args.output_md.write_text(_to_markdown(scorecard), encoding="utf-8", newline="\n")

    print(f"Wrote JSON: {args.output_json}")
    print(f"Wrote MD: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
