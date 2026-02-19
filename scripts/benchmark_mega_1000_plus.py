#!/usr/bin/env python3
"""Consolidated 1000+ PDF benchmark across mega corpus and real-RCT production."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def _load_json(path: Path) -> Dict:
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


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


@dataclass
class MegaEvalStats:
    name: str
    total: int
    with_reference: int
    matches_assisted: int
    matches_strict: int
    extracted_no_match: int
    no_extraction: int
    error: int
    no_reference: int

    @property
    def extraction_coverage(self) -> float:
        if self.with_reference <= 0:
            return 0.0
        return (self.matches_assisted + self.extracted_no_match) / self.with_reference

    @property
    def assisted_match_rate(self) -> float:
        if self.with_reference <= 0:
            return 0.0
        return self.matches_assisted / self.with_reference

    @property
    def strict_match_rate(self) -> float:
        if self.with_reference <= 0:
            return 0.0
        return self.matches_strict / self.with_reference


def _compute_mega_eval_stats(path: Path, name: str, strict_rel_threshold: float) -> MegaEvalStats:
    rows = _load_jsonl(path)
    status_counts = Counter(str(row.get("status") or "unknown") for row in rows)

    matches_strict = 0
    for row in rows:
        if row.get("status") != "match":
            continue
        match = row.get("match")
        method = str(row.get("match_method") or "")
        if isinstance(match, dict):
            rel = match.get("rel_distance")
            if not method:
                method = str(match.get("method") or "")
        else:
            rel = None

        strict_by_distance = False
        if rel is not None:
            try:
                rel_value = float(rel)
            except (TypeError, ValueError):
                rel_value = None
            strict_by_distance = rel_value is not None and rel_value <= strict_rel_threshold

        strict_by_method = "5pct" in method.lower()
        if strict_by_distance or strict_by_method:
            matches_strict += 1

    total = len(rows)
    no_reference = int(status_counts.get("no_cochrane_ref", 0))
    error = int(status_counts.get("error", 0))
    with_reference = total - no_reference - error

    return MegaEvalStats(
        name=name,
        total=total,
        with_reference=with_reference,
        matches_assisted=int(status_counts.get("match", 0)),
        matches_strict=matches_strict,
        extracted_no_match=int(status_counts.get("extracted_no_match", 0)),
        no_extraction=int(status_counts.get("no_extraction", 0)),
        error=error,
        no_reference=no_reference,
    )


def _build_markdown(
    output_path: Path,
    report: Dict,
    versions: List[MegaEvalStats],
) -> None:
    real = report["real_rct"]
    lines = [
        "# Mega 1000+ Benchmark",
        "",
        f"- Generated UTC: {report['computed_at_utc']}",
        f"- Mega corpus PDFs: {report['mega_pdf_count']}",
        f"- Strict criterion: relative error <= {report['strict_rel_threshold']:.2f}",
        "",
        "## Mega Corpus (1290 studies)",
        "",
        "| Version | Coverage | Strict Match | Assisted Match | No Extraction |",
        "|---|---:|---:|---:|---:|",
    ]

    for stats in versions:
        no_extract_rate = stats.no_extraction / stats.with_reference if stats.with_reference > 0 else 0.0
        lines.append(
            f"| {stats.name} "
            f"| {_pct(stats.extraction_coverage)} "
            f"| {_pct(stats.strict_match_rate)} "
            f"| {_pct(stats.assisted_match_rate)} "
            f"| {_pct(no_extract_rate)} |"
        )

    lines.extend(
        [
            "",
            "## Real-RCT Production (37-study frozen gold)",
            "",
            "| Metric | Baseline | Current | Delta |",
            "|---|---:|---:|---:|",
            f"| Extraction coverage | {_pct(real['baseline']['extraction_coverage'])} | {_pct(real['current']['extraction_coverage'])} | {_pct(real['current']['extraction_coverage'] - real['baseline']['extraction_coverage'])} |",
            f"| Strict match rate | {_pct(real['baseline']['strict_match_rate'])} | {_pct(real['current']['strict_match_rate'])} | {_pct(real['current']['strict_match_rate'] - real['baseline']['strict_match_rate'])} |",
            f"| CI completeness | {_pct(real['baseline']['ci_completeness'])} | {_pct(real['current']['ci_completeness'])} | {_pct(real['current']['ci_completeness'] - real['baseline']['ci_completeness'])} |",
            f"| MA-ready yield | {_pct(real['baseline']['ma_ready_yield'])} | {_pct(real['current']['ma_ready_yield'])} | {_pct(real['current']['ma_ready_yield'] - real['baseline']['ma_ready_yield'])} |",
            "",
            "## Notes",
            "",
            "- Mega strict match uses rel_distance <= 5% from merged match records.",
            "- Mega assisted match uses status == match from merged evaluations.",
            "- Mega and Real-RCT cohorts are different and should be compared by trend, not absolute parity.",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mega-pdfs-dir", type=Path, default=Path("gold_data/mega/pdfs"))
    parser.add_argument("--v10-merged", type=Path, default=Path("gold_data/mega/mega_eval_v10_merged.jsonl"))
    parser.add_argument("--v10-1-merged", type=Path, default=Path("gold_data/mega/mega_eval_v10_1_merged.jsonl"))
    parser.add_argument("--v10-2-merged", type=Path, default=Path("gold_data/mega/mega_eval_v10_2_merged.jsonl"))
    parser.add_argument(
        "--real-baseline-metrics",
        type=Path,
        default=Path("data/baselines/real_rct_metrics_baseline.json"),
    )
    parser.add_argument(
        "--real-current-metrics",
        type=Path,
        default=Path("output/real_rct_metrics_upgraded_v3.json"),
    )
    parser.add_argument("--strict-rel-threshold", type=float, default=0.05)
    parser.add_argument("--output-json", type=Path, default=Path("output/mega_1000_plus_benchmark.json"))
    parser.add_argument("--output-md", type=Path, default=Path("output/mega_1000_plus_benchmark.md"))
    args = parser.parse_args()

    for path in (
        args.v10_merged,
        args.v10_1_merged,
        args.v10_2_merged,
        args.real_baseline_metrics,
        args.real_current_metrics,
    ):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")
    if not args.mega_pdfs_dir.exists():
        raise FileNotFoundError(f"Mega PDFs directory not found: {args.mega_pdfs_dir}")
    if args.strict_rel_threshold < 0:
        raise ValueError("--strict-rel-threshold must be >= 0")

    v10 = _compute_mega_eval_stats(args.v10_merged, "v10_merged", args.strict_rel_threshold)
    v10_1 = _compute_mega_eval_stats(args.v10_1_merged, "v10_1_merged", args.strict_rel_threshold)
    v10_2 = _compute_mega_eval_stats(args.v10_2_merged, "v10_2_merged", args.strict_rel_threshold)
    versions = [v10, v10_1, v10_2]

    baseline_metrics = _load_json(args.real_baseline_metrics)
    current_metrics = _load_json(args.real_current_metrics)

    report = {
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "strict_rel_threshold": args.strict_rel_threshold,
        "mega_pdf_count": len(list(args.mega_pdfs_dir.glob("*.pdf"))),
        "mega_versions": {
            stats.name: {
                "total": stats.total,
                "with_reference": stats.with_reference,
                "counts": {
                    "match": stats.matches_assisted,
                    "strict_match": stats.matches_strict,
                    "extracted_no_match": stats.extracted_no_match,
                    "no_extraction": stats.no_extraction,
                    "no_reference": stats.no_reference,
                    "error": stats.error,
                },
                "rates": {
                    "extraction_coverage": stats.extraction_coverage,
                    "strict_match_rate": stats.strict_match_rate,
                    "assisted_match_rate": stats.assisted_match_rate,
                    "no_extraction_rate": (stats.no_extraction / stats.with_reference) if stats.with_reference else 0.0,
                },
            }
            for stats in versions
        },
        "real_rct": {
            "baseline": {
                "extraction_coverage": float(baseline_metrics["rates"]["extraction_coverage"]),
                "strict_match_rate": float(baseline_metrics["rates"]["strict_match_rate"]),
                "ci_completeness": float(baseline_metrics["rates"]["ci_completeness"]),
                "ma_ready_yield": float(baseline_metrics["rates"]["ma_ready_yield"]),
            },
            "current": {
                "extraction_coverage": float(current_metrics["rates"]["extraction_coverage"]),
                "strict_match_rate": float(current_metrics["rates"]["strict_match_rate"]),
                "ci_completeness": float(current_metrics["rates"]["ci_completeness"]),
                "ma_ready_yield": float(current_metrics["rates"]["ma_ready_yield"]),
            },
        },
        "inputs": {
            "v10_merged": str(args.v10_merged),
            "v10_1_merged": str(args.v10_1_merged),
            "v10_2_merged": str(args.v10_2_merged),
            "real_baseline_metrics": str(args.real_baseline_metrics),
            "real_current_metrics": str(args.real_current_metrics),
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    _build_markdown(args.output_md, report, versions)

    print("Mega 1000+ benchmark complete")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
