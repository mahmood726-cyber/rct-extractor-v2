#!/usr/bin/env python3
"""Run the full real-RCT freeze/upgrade/evaluate/gate/contract pipeline."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run(command: List[str]) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    env = os.environ.copy()
    if command and Path(command[0]).name.lower().startswith("python"):
        env["PYTHONUNBUFFERED"] = "1"
    subprocess.run(command, cwd=PROJECT_ROOT, check=True, env=env)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-input", type=Path, default=Path("gold_data/gold_50.jsonl"))
    parser.add_argument("--frozen-dir", type=Path, default=Path("data/frozen_eval_v1"))
    parser.add_argument("--seed-results", type=Path, default=Path("gold_data/baseline_results.json"))
    parser.add_argument("--pdf-dir", type=Path, default=Path("test_pdfs/gold_standard"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--split", choices=["train", "validation", "test", "all"], default="all")
    parser.add_argument("--max-drop", type=float, default=0.02)
    parser.add_argument("--upgraded-results", type=Path, default=Path("output/real_rct_results_upgraded_v3.json"))
    parser.add_argument("--baseline-metrics", type=Path, default=Path("data/baselines/real_rct_metrics_baseline.json"))
    parser.add_argument("--current-metrics", type=Path, default=Path("output/real_rct_metrics_upgraded_v3.json"))
    parser.add_argument("--gate-report", type=Path, default=Path("output/real_rct_gate_report_upgraded_v3.json"))
    parser.add_argument("--ma-records", type=Path, default=Path("output/ma_records_upgraded_v3.jsonl"))
    parser.add_argument(
        "--ma-records-validated",
        type=Path,
        default=Path("output/ma_records_upgraded_v3.validated.jsonl"),
    )
    parser.add_argument(
        "--rerun-missing",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Whether to rerun missing studies through full PDF extraction during upgrade.",
    )
    parser.add_argument(
        "--rerun-missing-uncertainty",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Rerun studies that have effect values but are missing CI/SE.",
    )
    parser.add_argument(
        "--enable-advanced",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable advanced extraction while upgrading unresolved studies.",
    )
    parser.add_argument(
        "--backfill-pages",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Backfill page numbers from PDF text during upgrade.",
    )
    parser.add_argument(
        "--backfill-uncertainty-from-page",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Backfill CI/SE from page context when a selected match lacks uncertainty.",
    )
    parser.add_argument(
        "--focus-statuses",
        type=str,
        default=None,
        help="Optional status focus for upgrade (comma-separated, e.g. no_extractions,no_match).",
    )
    parser.add_argument(
        "--study-ids",
        type=str,
        default=None,
        help="Optional study_id filter for targeted rerun (comma-separated).",
    )
    parser.add_argument(
        "--max-reruns",
        type=int,
        default=None,
        help="Optional cap on reruns for this invocation.",
    )
    parser.add_argument(
        "--resume-from-output",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reuse existing upgrade output file as seed for incremental reruns.",
    )
    parser.add_argument(
        "--per-study-timeout-sec",
        type=float,
        default=None,
        help="Optional timeout passed to upgrade script per rerun study.",
    )
    parser.add_argument(
        "--uncertainty-distance-tolerance",
        type=float,
        default=0.05,
        help="Distance tolerance for preferring rerun candidates that add CI/SE.",
    )
    parser.add_argument(
        "--uncertainty-backfill-max-distance",
        type=int,
        default=320,
        help="Max character distance for uncertainty backfill around source/effect anchors.",
    )
    parser.add_argument(
        "--skip-freeze",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Skip freeze step and reuse existing frozen split.",
    )
    args = parser.parse_args()

    frozen_gold = args.frozen_dir / "frozen_gold.jsonl"
    split_manifest = args.frozen_dir / "split_manifest.json"

    if not args.skip_freeze:
        _run(
            [
                sys.executable,
                "scripts/freeze_eval_split.py",
                "--input",
                str(args.gold_input),
                "--output-dir",
                str(args.frozen_dir),
                "--seed",
                str(args.seed),
            ]
        )

    _run(
        [
            sys.executable,
            "scripts/evaluate_real_rct_metrics.py",
            "--gold",
            str(frozen_gold),
            "--results",
            str(args.seed_results),
            "--split-manifest",
            str(split_manifest),
            "--split",
            args.split,
            "--output",
            str(args.baseline_metrics),
        ]
    )

    upgrade_cmd = [
        sys.executable,
        "scripts/upgrade_real_rct_results.py",
        "--gold",
        str(frozen_gold),
        "--seed-results",
        str(args.seed_results),
        "--pdf-dir",
        str(args.pdf_dir),
        "--output",
        str(args.upgraded_results),
    ]
    if args.rerun_missing:
        upgrade_cmd.append("--rerun-missing")
    else:
        upgrade_cmd.append("--no-rerun-missing")
    if args.rerun_missing_uncertainty:
        upgrade_cmd.append("--rerun-missing-uncertainty")
    else:
        upgrade_cmd.append("--no-rerun-missing-uncertainty")
    if args.enable_advanced:
        upgrade_cmd.append("--enable-advanced")
    else:
        upgrade_cmd.append("--no-enable-advanced")
    if args.backfill_pages:
        upgrade_cmd.append("--backfill-pages")
    else:
        upgrade_cmd.append("--no-backfill-pages")
    if args.backfill_uncertainty_from_page:
        upgrade_cmd.append("--backfill-uncertainty-from-page")
    else:
        upgrade_cmd.append("--no-backfill-uncertainty-from-page")
    if args.focus_statuses:
        upgrade_cmd.extend(["--focus-statuses", args.focus_statuses])
    if args.study_ids:
        upgrade_cmd.extend(["--study-ids", args.study_ids])
    if args.max_reruns is not None:
        upgrade_cmd.extend(["--max-reruns", str(args.max_reruns)])
    if args.resume_from_output:
        upgrade_cmd.append("--resume-from-output")
    else:
        upgrade_cmd.append("--no-resume-from-output")
    if args.per_study_timeout_sec is not None:
        upgrade_cmd.extend(["--per-study-timeout-sec", str(args.per_study_timeout_sec)])
    upgrade_cmd.extend(["--uncertainty-distance-tolerance", str(args.uncertainty_distance_tolerance)])
    upgrade_cmd.extend(["--uncertainty-backfill-max-distance", str(args.uncertainty_backfill_max_distance)])
    _run(upgrade_cmd)

    _run(
        [
            sys.executable,
            "scripts/evaluate_real_rct_metrics.py",
            "--gold",
            str(frozen_gold),
            "--results",
            str(args.upgraded_results),
            "--split-manifest",
            str(split_manifest),
            "--split",
            args.split,
            "--output",
            str(args.current_metrics),
        ]
    )

    _run(
        [
            sys.executable,
            "scripts/check_regression_gate.py",
            "--baseline",
            str(args.baseline_metrics),
            "--current",
            str(args.current_metrics),
            "--max-drop",
            str(args.max_drop),
            "--report",
            str(args.gate_report),
        ]
    )

    _run(
        [
            sys.executable,
            "scripts/build_ma_records_from_results.py",
            "--gold",
            str(frozen_gold),
            "--results",
            str(args.upgraded_results),
            "--output-jsonl",
            str(args.ma_records),
        ]
    )

    _run(
        [
            sys.executable,
            "scripts/validate_ma_contract.py",
            str(args.ma_records),
            "--output-jsonl",
            str(args.ma_records_validated),
        ]
    )

    print("\nReal-RCT gate pipeline completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
