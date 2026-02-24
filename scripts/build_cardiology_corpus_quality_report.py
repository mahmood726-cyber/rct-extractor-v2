#!/usr/bin/env python3
"""Build quality metrics/report for cardiology OA corpus extraction outputs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, List, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _load_latest_rows(path: Path) -> Dict[str, Dict]:
    latest: Dict[str, Dict] = {}
    if not path.exists():
        return latest
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                # Ignore any partially-written trailing line.
                continue
            rel = str(row.get("pdf_relpath") or "").replace("\\", "/")
            if not rel:
                continue
            latest[rel] = row
    return latest


def _source_type(source_text: str) -> str:
    text = source_text.strip().lower()
    if text.startswith("[computed from raw data]"):
        return "computed"
    if text.startswith("[lax]"):
        return "lax"
    if text.startswith("[table"):
        return "table"
    if text.startswith("[ocr"):
        return "ocr"
    if text.startswith("[figure"):
        return "figure"
    if text:
        return "text"
    return "missing"


def _rows_iter(latest_rows: Dict[str, Dict]) -> Iterable[Dict]:
    for _, row in sorted(latest_rows.items(), key=lambda item: item[0]):
        yield row


def build_summary(latest_rows: Dict[str, Dict], high_conf_threshold: float) -> Dict:
    rows = list(_rows_iter(latest_rows))
    total = len(rows)
    status_counts = Counter(str(row.get("status") or "unknown") for row in rows)
    extraction_method_counts = Counter(
        str((row.get("meta") or {}).get("extraction_method") or "unknown") for row in rows
    )

    extracted_rows = [row for row in rows if str(row.get("status") or "") == "extracted"]
    best_rows = [row for row in rows if isinstance(row.get("best_match"), dict)]

    with_ci = 0
    with_se = 0
    with_uncertainty = 0
    with_source = 0
    with_page = 0
    high_conf = 0
    high_conf_with_ci = 0
    strict_ma_ready = 0
    relaxed_ma_ready = 0

    effect_type_counts = Counter()
    automation_tier_counts = Counter()
    source_type_counts = Counter()
    born_digital_counts = Counter()

    elapsed_values: List[float] = []

    for row in rows:
        meta = row.get("meta") or {}
        elapsed = _to_float(meta.get("elapsed_sec"))
        if elapsed is not None and elapsed >= 0:
            elapsed_values.append(elapsed)
        born_key = "unknown"
        if meta.get("is_born_digital") is True:
            born_key = "born_digital"
        elif meta.get("is_born_digital") is False:
            born_key = "scanned_or_ocr"
        born_digital_counts[born_key] += 1

    for row in best_rows:
        best = row.get("best_match") or {}
        ci_ready = best.get("ci_lower") is not None and best.get("ci_upper") is not None
        se_ready = best.get("standard_error") is not None
        uncertainty_ready = ci_ready or se_ready

        source_text = str(best.get("source_text") or "").strip()
        source_ready = bool(source_text)
        page_ready = best.get("page_number") is not None
        effect_type = str(best.get("type") or "").upper().strip()
        if effect_type:
            effect_type_counts[effect_type] += 1

        automation_tier = str(best.get("automation_tier") or "unknown")
        automation_tier_counts[automation_tier] += 1

        source_type_counts[_source_type(source_text)] += 1

        conf = _to_float(best.get("calibrated_confidence"))
        is_high_conf = conf is not None and conf >= high_conf_threshold

        if ci_ready:
            with_ci += 1
        if se_ready:
            with_se += 1
        if uncertainty_ready:
            with_uncertainty += 1
        if source_ready:
            with_source += 1
        if page_ready:
            with_page += 1
        if is_high_conf:
            high_conf += 1
            if ci_ready:
                high_conf_with_ci += 1

        if uncertainty_ready and source_ready:
            relaxed_ma_ready += 1
            if page_ready:
                strict_ma_ready += 1

    timing = {
        "n_with_elapsed": len(elapsed_values),
        "median_sec": round(float(median(elapsed_values)), 3) if elapsed_values else None,
        "mean_sec": round(sum(elapsed_values) / len(elapsed_values), 3) if elapsed_values else None,
        "max_sec": round(max(elapsed_values), 3) if elapsed_values else None,
    }

    payload = {
        "generated_at_utc": _utc_now(),
        "counts": {
            "total_rows": total,
            "extracted_rows": len(extracted_rows),
            "best_match_rows": len(best_rows),
            "best_with_ci": with_ci,
            "best_with_se": with_se,
            "best_with_uncertainty": with_uncertainty,
            "best_with_source_text": with_source,
            "best_with_page_number": with_page,
            "high_confidence_best": high_conf,
            "high_confidence_with_ci": high_conf_with_ci,
            "ma_ready_relaxed": relaxed_ma_ready,
            "ma_ready_strict": strict_ma_ready,
        },
        "rates": {
            "extraction_coverage": _pct(len(extracted_rows), total),
            "best_match_rate": _pct(len(best_rows), total),
            "ci_completeness_among_best": _pct(with_ci, len(best_rows)),
            "uncertainty_completeness_among_best": _pct(with_uncertainty, len(best_rows)),
            "source_completeness_among_best": _pct(with_source, len(best_rows)),
            "page_completeness_among_best": _pct(with_page, len(best_rows)),
            "high_confidence_share_among_best": _pct(high_conf, len(best_rows)),
            "high_confidence_ci_share_among_best": _pct(high_conf_with_ci, len(best_rows)),
            "ma_ready_relaxed_rate": _pct(relaxed_ma_ready, total),
            "ma_ready_strict_rate": _pct(strict_ma_ready, total),
        },
        "distributions": {
            "status_counts": dict(sorted(status_counts.items())),
            "extraction_method_counts": dict(sorted(extraction_method_counts.items())),
            "best_effect_type_counts": dict(sorted(effect_type_counts.items())),
            "best_automation_tier_counts": dict(sorted(automation_tier_counts.items())),
            "best_source_type_counts": dict(sorted(source_type_counts.items())),
            "born_digital_counts": dict(sorted(born_digital_counts.items())),
        },
        "timing_sec": timing,
        "parameters": {
            "high_confidence_threshold": high_conf_threshold,
        },
    }
    return payload


def write_markdown(path: Path, summary: Dict, input_jsonl: Path) -> None:
    counts = summary.get("counts") or {}
    rates = summary.get("rates") or {}
    dist = summary.get("distributions") or {}
    timing = summary.get("timing_sec") or {}

    lines: List[str] = []
    lines.append("# Cardiology OA Corpus Quality Report")
    lines.append("")
    lines.append(f"- Generated UTC: {summary.get('generated_at_utc')}")
    lines.append(f"- Input results: `{input_jsonl}`")
    lines.append(f"- Total rows: {counts.get('total_rows', 0)}")
    lines.append(f"- Extraction coverage: {rates.get('extraction_coverage', 0.0):.4f}")
    lines.append(f"- Best-match rate: {rates.get('best_match_rate', 0.0):.4f}")
    lines.append(f"- CI completeness (best matches): {rates.get('ci_completeness_among_best', 0.0):.4f}")
    lines.append(f"- High-confidence best share: {rates.get('high_confidence_share_among_best', 0.0):.4f}")
    lines.append(f"- MA-ready relaxed rate: {rates.get('ma_ready_relaxed_rate', 0.0):.4f}")
    lines.append(f"- MA-ready strict rate: {rates.get('ma_ready_strict_rate', 0.0):.4f}")
    lines.append("")
    lines.append("## Status Counts")
    lines.append("")
    for key, value in sorted((dist.get("status_counts") or {}).items()):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Best-Match Effect Types")
    lines.append("")
    effect_counts = dist.get("best_effect_type_counts") or {}
    if effect_counts:
        for key, value in sorted(effect_counts.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Best-Match Source Types")
    lines.append("")
    for key, value in sorted((dist.get("best_source_type_counts") or {}).items()):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Timing")
    lines.append("")
    lines.append(f"- Median sec/PDF: {timing.get('median_sec')}")
    lines.append(f"- Mean sec/PDF: {timing.get('mean_sec')}")
    lines.append(f"- Max sec/PDF: {timing.get('max_sec')}")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/results.jsonl"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/quality_report.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/quality_report.md"),
    )
    parser.add_argument("--high-conf-threshold", type=float, default=0.9)
    args = parser.parse_args()

    if not args.results_jsonl.exists():
        raise FileNotFoundError(f"Results file not found: {args.results_jsonl}")
    if not (0.0 <= args.high_conf_threshold <= 1.0):
        raise ValueError("--high-conf-threshold must be between 0 and 1")

    latest_rows = _load_latest_rows(args.results_jsonl)
    summary = build_summary(latest_rows, high_conf_threshold=float(args.high_conf_threshold))
    summary["inputs"] = {"results_jsonl": str(args.results_jsonl).replace("\\", "/")}

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(args.output_md, summary, args.results_jsonl)

    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
