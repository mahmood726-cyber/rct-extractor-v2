#!/usr/bin/env python3
"""Run strict external no-tune evaluation end-to-end."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run(command: List[str]) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    env = os.environ.copy()
    if command and Path(command[0]).name.lower().startswith("python"):
        env["PYTHONUNBUFFERED"] = "1"
    subprocess.run(command, cwd=PROJECT_ROOT, check=True, env=env)


def _load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_results(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return data


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _write_summary_report(summary: Dict, report_path: Path) -> None:
    metrics = summary.get("metrics", {})
    status_counts = summary.get("status_counts", {})
    protocol = summary.get("protocol", {})
    no_tune_flags = summary.get("no_tune_flags", {})

    lines = [
        "# External No-Tune Evaluation Report",
        "",
        f"- Generated UTC: {summary.get('generated_at_utc')}",
        f"- Frozen trials: {protocol.get('frozen_trials_total')}",
        f"- Journal mix (frozen): {protocol.get('journal_counts_frozen')}",
        "",
        "## Core Metrics",
        "",
        f"- Extraction coverage: {metrics.get('extraction_coverage', 0.0):.6f}",
        f"- Strict match rate: {metrics.get('strict_match_rate', 0.0):.6f}",
        f"- Lenient match rate: {metrics.get('lenient_match_rate', 0.0):.6f}",
        f"- Effect-type accuracy: {metrics.get('effect_type_accuracy', 0.0):.6f}",
        f"- CI completeness: {metrics.get('ci_completeness', 0.0):.6f}",
        f"- MA-ready yield: {metrics.get('ma_ready_yield', 0.0):.6f}",
        "",
        "## Result Status Counts",
        "",
    ]
    for key in sorted(status_counts):
        lines.append(f"- {key}: {status_counts[key]}")
    lines.extend(
        [
            "",
            "## No-Tune Controls",
            "",
            "- `--no-fallback-from-gold`",
            "- `--no-fallback-from-cochrane`",
            "- `--no-fallback-for-distant`",
            "- `--no-allow-assumed-se-fallback`",
            "- `--no-resume-from-output`",
            f"- PubMed abstract fallback: `{'enabled' if no_tune_flags.get('fallback_from_pubmed_abstract') else 'disabled'}`",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/ground_truth/external_validation_ground_truth.jsonl"),
    )
    parser.add_argument(
        "--source",
        choices=["jsonl", "module"],
        default="jsonl",
        help="Ground-truth source for cohort preparation.",
    )
    parser.add_argument("--cohort-dir", type=Path, default=Path("data/external_no_tune_v1"))
    parser.add_argument("--pdf-dir", type=Path, default=Path("test_pdfs/external_no_tune_v1/pdfs"))
    parser.add_argument(
        "--journal-allowlist",
        type=str,
        default="NEJM,Lancet,AJP",
        help="Comma-separated journals to include; empty means no filter.",
    )
    parser.add_argument("--max-trials", type=int, default=None)
    parser.add_argument(
        "--download-missing",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--require-local-pdf",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--request-timeout-sec", type=float, default=80.0)
    parser.add_argument(
        "--validate-pdf-content",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Validate PMCID metadata against expected DOI/PMID during cohort prep.",
    )
    parser.add_argument("--per-study-timeout-sec", type=float, default=180.0)
    parser.add_argument(
        "--enable-advanced",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Pass through to upgrade script.",
    )
    parser.add_argument(
        "--fallback-from-pubmed-abstract",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "For no_extractions/no_match rows, allow PubMed abstract extraction fallback "
            "using trial PMID."
        ),
    )
    parser.add_argument(
        "--pubmed-timeout-sec",
        type=float,
        default=20.0,
    )
    parser.add_argument(
        "--skip-prepare",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument(
        "--prepare-only",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument(
        "--results-output",
        type=Path,
        default=Path("output/external_no_tune_v1_results.json"),
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("output/external_no_tune_v1_metrics.json"),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("output/external_no_tune_v1_summary.json"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("output/external_no_tune_v1_report.md"),
    )
    args = parser.parse_args()

    cohort_dir = args.cohort_dir
    frozen_gold = cohort_dir / "frozen_gold.jsonl"
    seed_results = cohort_dir / "seed_results_empty.json"
    protocol_lock = cohort_dir / "protocol_lock.json"

    if not args.skip_prepare:
        prepare_cmd = [
            sys.executable,
            "scripts/prepare_external_no_tune_eval.py",
            "--input",
            str(args.input),
            "--source",
            args.source,
            "--output-dir",
            str(cohort_dir),
            "--pdf-dir",
            str(args.pdf_dir),
            "--journal-allowlist",
            args.journal_allowlist,
            "--request-timeout-sec",
            str(args.request_timeout_sec),
        ]
        if args.max_trials is not None:
            prepare_cmd.extend(["--max-trials", str(args.max_trials)])
        if args.download_missing:
            prepare_cmd.append("--download-missing")
        else:
            prepare_cmd.append("--no-download-missing")
        if args.require_local_pdf:
            prepare_cmd.append("--require-local-pdf")
        else:
            prepare_cmd.append("--no-require-local-pdf")
        if args.validate_pdf_content:
            prepare_cmd.append("--validate-pdf-content")
        else:
            prepare_cmd.append("--no-validate-pdf-content")
        _run(prepare_cmd)

    if args.prepare_only:
        print("Prepared cohort only; skipping extraction/evaluation.")
        return 0

    if not frozen_gold.exists():
        raise FileNotFoundError(f"Frozen gold file not found: {frozen_gold}")
    if not seed_results.exists():
        raise FileNotFoundError(f"Seed results file not found: {seed_results}")

    upgrade_cmd = [
        sys.executable,
        "scripts/upgrade_real_rct_results.py",
        "--gold",
        str(frozen_gold),
        "--seed-results",
        str(seed_results),
        "--pdf-dir",
        str(args.pdf_dir),
        "--output",
        str(args.results_output),
        "--rerun-missing",
        "--no-rerun-missing-uncertainty",
        "--backfill-pages",
        "--backfill-uncertainty-from-page",
        "--no-fallback-from-gold",
        "--no-fallback-from-cochrane",
        "--no-fallback-for-distant",
        "--no-allow-assumed-se-fallback",
        "--no-resume-from-output",
    ]
    if args.enable_advanced:
        upgrade_cmd.append("--enable-advanced")
    else:
        upgrade_cmd.append("--no-enable-advanced")
    if args.fallback_from_pubmed_abstract:
        upgrade_cmd.append("--fallback-from-pubmed-abstract")
    else:
        upgrade_cmd.append("--no-fallback-from-pubmed-abstract")
    if args.pubmed_timeout_sec is not None:
        upgrade_cmd.extend(["--pubmed-timeout-sec", str(args.pubmed_timeout_sec)])
    if args.per_study_timeout_sec is not None:
        upgrade_cmd.extend(["--per-study-timeout-sec", str(args.per_study_timeout_sec)])
    _run(upgrade_cmd)

    evaluate_cmd = [
        sys.executable,
        "scripts/evaluate_real_rct_metrics.py",
        "--gold",
        str(frozen_gold),
        "--results",
        str(args.results_output),
        "--split",
        "all",
        "--output",
        str(args.metrics_output),
    ]
    _run(evaluate_cmd)

    metrics_payload = _load_json(args.metrics_output)
    results_rows = _load_results(args.results_output)
    protocol_payload = _load_json(protocol_lock) if protocol_lock.exists() else {}
    status_counts = Counter(str(row.get("status") or "unknown") for row in results_rows)

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifacts": {
            "frozen_gold": _rel(frozen_gold),
            "seed_results": _rel(seed_results),
            "results": _rel(args.results_output),
            "metrics": _rel(args.metrics_output),
            "protocol_lock": _rel(protocol_lock) if protocol_lock.exists() else None,
        },
        "no_tune_flags": {
            "fallback_from_gold": False,
            "fallback_from_cochrane": False,
            "fallback_for_distant": False,
            "allow_assumed_se_fallback": False,
            "resume_from_output": False,
            "fallback_from_pubmed_abstract": bool(args.fallback_from_pubmed_abstract),
        },
        "protocol": {
            "source": protocol_payload.get("source"),
            "selected_trials_total": protocol_payload.get("selected_trials_total"),
            "frozen_trials_total": protocol_payload.get("frozen_trials_total"),
            "journal_counts_frozen": protocol_payload.get("journal_counts_frozen", {}),
            "download_stats": protocol_payload.get("download_stats", {}),
            "validate_pdf_content": protocol_payload.get("validate_pdf_content"),
            "validation_stats": protocol_payload.get("validation_stats", {}),
        },
        "counts": metrics_payload.get("counts", {}),
        "metrics": metrics_payload.get("rates", {}),
        "status_counts": dict(sorted(status_counts.items())),
    }

    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    with args.summary_output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    _write_summary_report(summary, args.report_output)

    print("\nExternal no-tune evaluation complete.")
    print(f"Wrote: {args.results_output}")
    print(f"Wrote: {args.metrics_output}")
    print(f"Wrote: {args.summary_output}")
    print(f"Wrote: {args.report_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
