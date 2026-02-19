#!/usr/bin/env python3
"""Run mega_evaluate.py in bounded resume batches with timeout and progress tracking."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEGA_EVAL_JSONL = PROJECT_ROOT / "gold_data" / "mega" / "mega_eval.jsonl"
MEGA_MATCHED_JSONL = PROJECT_ROOT / "gold_data" / "mega" / "mega_matched.jsonl"
MEGA_PDFS_DIR = PROJECT_ROOT / "gold_data" / "mega" / "pdfs"


def _canonical_study_key(study_id: str) -> str:
    text = unicodedata.normalize("NFKD", str(study_id))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return text


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _parse_rerun_statuses(value: str) -> Set[str]:
    return {s.strip() for s in str(value).split(",") if s.strip()}


def _latest_status_by_study_key(path: Path) -> Dict[str, str]:
    latest: Dict[str, str] = {}
    if not path.exists():
        return latest
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
            key = _canonical_study_key(str(study_id))
            if not key:
                continue
            latest[key] = str(row.get("status") or "")
    return latest


def _count_rerun_candidates(path: Path, rerun_statuses: Set[str]) -> int:
    if not rerun_statuses:
        return 0
    latest = _latest_status_by_study_key(path)
    return sum(1 for status in latest.values() if status in rerun_statuses)


def _run_round(
    step_batch: int,
    timeout_sec: int,
    fast_mode: bool,
    diag_jsonl: Optional[Path],
    diag_parser_probe: bool,
    per_study_timeout_sec: int,
    rerun_statuses: str,
    ocr_threshold: float,
    extract_tables: bool,
    enable_advanced: bool,
    aggressive_ocr_correction: bool,
) -> Dict:
    command = [
        sys.executable,
        "scripts/mega_evaluate.py",
        "--batch",
        str(step_batch),
        "--resume",
    ]
    command.append("--fast-mode" if fast_mode else "--no-fast-mode")
    if diag_jsonl:
        command.extend(["--diag-jsonl", str(diag_jsonl)])
    if diag_parser_probe:
        command.append("--diag-parser-probe")
    if per_study_timeout_sec > 0:
        command.extend(["--per-study-timeout-sec", str(per_study_timeout_sec)])
    if rerun_statuses.strip():
        command.extend(["--rerun-statuses", rerun_statuses.strip()])
    command.extend(["--ocr-threshold", str(ocr_threshold)])
    command.append("--extract-tables" if extract_tables else "--no-extract-tables")
    command.append("--enable-advanced" if enable_advanced else "--no-enable-advanced")
    command.append(
        "--aggressive-ocr-correction"
        if aggressive_ocr_correction
        else "--no-aggressive-ocr-correction"
    )
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        elapsed = time.time() - started
        return {
            "command": command,
            "returncode": completed.returncode,
            "elapsed_sec": round(elapsed, 2),
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        elapsed = time.time() - started
        return {
            "command": command,
            "returncode": None,
            "elapsed_sec": round(elapsed, 2),
            "stdout_tail": (exc.stdout or "")[-2000:],
            "stderr_tail": (exc.stderr or "")[-2000:],
            "timed_out": True,
        }


def _next_pending_study_id() -> Optional[str]:
    if not MEGA_MATCHED_JSONL.exists():
        return None

    evaluated_keys = set()
    if MEGA_EVAL_JSONL.exists():
        for line in MEGA_EVAL_JSONL.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            study_id = row.get("study_id")
            if study_id:
                evaluated_keys.add(_canonical_study_key(str(study_id)))

    for line in MEGA_MATCHED_JSONL.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        pmcid = row.get("pmcid")
        study_id = row.get("study_id")
        if not pmcid or not study_id:
            continue
        safe_name = str(study_id).replace(" ", "_").replace("/", "_")
        pdf_path = MEGA_PDFS_DIR / f"{safe_name}_{pmcid}.pdf"
        if not pdf_path.exists():
            continue
        if _canonical_study_key(str(study_id)) in evaluated_keys:
            continue
        return str(study_id)

    return None


def _append_timeout_placeholder(study_id: str, reason: str) -> None:
    row = {
        "study_id": study_id,
        "status": "timeout_skipped_by_batch_runner",
        "error": reason,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    MEGA_EVAL_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with MEGA_EVAL_JSONL.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-rows", type=int, default=1254)
    parser.add_argument("--step-batch", type=int, default=25)
    parser.add_argument("--round-timeout-sec", type=int, default=900)
    parser.add_argument("--max-rounds", type=int, default=20)
    parser.add_argument(
        "--report-json",
        type=Path,
        default=Path("output/mega_batched_run_report.json"),
    )
    parser.add_argument(
        "--fast-mode",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run mega_evaluate.py in fast mode (reduced expensive extraction branches).",
    )
    parser.add_argument(
        "--auto-skip-stuck",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "When a round times out with no new rows, append a timeout placeholder for the next "
            "pending study to unblock progress."
        ),
    )
    parser.add_argument(
        "--diag-jsonl",
        type=Path,
        default=None,
        help="Optional diagnostics JSONL passed through to mega_evaluate.py",
    )
    parser.add_argument(
        "--diag-parser-probe",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable parser timing probe in mega_evaluate.py",
    )
    parser.add_argument(
        "--per-study-timeout-sec",
        type=int,
        default=0,
        help="Pass through per-study extraction timeout to mega_evaluate.py (0 disables).",
    )
    parser.add_argument(
        "--rerun-statuses",
        type=str,
        default="",
        help="Comma-separated statuses to rerun in mega_evaluate (e.g., timeout_skipped_by_batch_runner).",
    )
    parser.add_argument(
        "--max-stall-rounds",
        type=int,
        default=1,
        help=(
            "When rerun statuses are enabled, stop after this many consecutive successful "
            "rounds with no rerun-candidate reduction."
        ),
    )
    parser.add_argument(
        "--ocr-threshold",
        type=float,
        default=100.0,
        help="Pass through OCR threshold to mega_evaluate.py",
    )
    parser.add_argument(
        "--extract-tables",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Pass through table extraction toggle to mega_evaluate.py",
    )
    parser.add_argument(
        "--enable-advanced",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Pass through advanced extraction toggle to mega_evaluate.py",
    )
    parser.add_argument(
        "--aggressive-ocr-correction",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Pass through OCR correction aggressiveness to mega_evaluate.py",
    )
    args = parser.parse_args()

    if args.target_rows <= 0:
        raise ValueError("--target-rows must be > 0")
    if args.step_batch <= 0:
        raise ValueError("--step-batch must be > 0")
    if args.round_timeout_sec <= 0:
        raise ValueError("--round-timeout-sec must be > 0")
    if args.max_rounds <= 0:
        raise ValueError("--max-rounds must be > 0")
    if args.per_study_timeout_sec < 0:
        raise ValueError("--per-study-timeout-sec must be >= 0")
    if args.max_stall_rounds <= 0:
        raise ValueError("--max-stall-rounds must be > 0")
    if args.ocr_threshold <= 0:
        raise ValueError("--ocr-threshold must be > 0")

    rerun_status_set = _parse_rerun_statuses(args.rerun_statuses)
    rounds: List[Dict] = []
    start_rows = _count_jsonl_rows(MEGA_EVAL_JSONL)
    current_rows = start_rows
    start_rerun_candidates = _count_rerun_candidates(MEGA_EVAL_JSONL, rerun_status_set)
    current_rerun_candidates = start_rerun_candidates
    stall_rounds = 0
    interrupted = False

    for round_idx in range(1, args.max_rounds + 1):
        if not rerun_status_set and current_rows >= args.target_rows:
            break
        if rerun_status_set and current_rerun_candidates <= 0:
            break

        before_rows = current_rows
        before_rerun_candidates = current_rerun_candidates
        try:
            result = _run_round(
                step_batch=args.step_batch,
                timeout_sec=args.round_timeout_sec,
                fast_mode=args.fast_mode,
                diag_jsonl=args.diag_jsonl,
                diag_parser_probe=args.diag_parser_probe,
                per_study_timeout_sec=args.per_study_timeout_sec,
                rerun_statuses=args.rerun_statuses,
                ocr_threshold=args.ocr_threshold,
                extract_tables=bool(args.extract_tables),
                enable_advanced=bool(args.enable_advanced),
                aggressive_ocr_correction=bool(args.aggressive_ocr_correction),
            )
        except KeyboardInterrupt:
            interrupted = True
            print("Interrupted during round execution; writing partial report.", flush=True)
            break
        after_rows = _count_jsonl_rows(MEGA_EVAL_JSONL)
        after_rerun_candidates = _count_rerun_candidates(MEGA_EVAL_JSONL, rerun_status_set)
        current_rows = after_rows
        current_rerun_candidates = after_rerun_candidates
        row_delta = after_rows - before_rows
        rerun_delta = after_rerun_candidates - before_rerun_candidates

        round_record = {
            "round": round_idx,
            "before_rows": before_rows,
            "after_rows": after_rows,
            "row_delta": row_delta,
            "before_rerun_candidates": before_rerun_candidates,
            "after_rerun_candidates": after_rerun_candidates,
            "rerun_candidate_delta": rerun_delta,
            **result,
        }
        rounds.append(round_record)

        status = "timeout" if result["timed_out"] else f"rc={result['returncode']}"
        if rerun_status_set:
            print(
                f"[round {round_idx}] {status} "
                f"rerun-candidates: {before_rerun_candidates} -> {after_rerun_candidates} "
                f"(delta {rerun_delta}) rows: {before_rows} -> {after_rows} (delta {row_delta}) "
                f"elapsed={result['elapsed_sec']}s",
                flush=True,
            )
        else:
            print(
                f"[round {round_idx}] {status} "
                f"rows: {before_rows} -> {after_rows} (delta {row_delta}) "
                f"elapsed={result['elapsed_sec']}s",
                flush=True,
            )

        if (
            not rerun_status_set
            and result["timed_out"]
            and row_delta == 0
            and args.auto_skip_stuck
        ):
            stuck_study_id = _next_pending_study_id()
            if stuck_study_id:
                _append_timeout_placeholder(
                    study_id=stuck_study_id,
                    reason=f"batch_timeout_{args.round_timeout_sec}s",
                )
                after_skip_rows = _count_jsonl_rows(MEGA_EVAL_JSONL)
                skip_delta = after_skip_rows - current_rows
                current_rows = after_skip_rows
                round_record["auto_skipped_study_id"] = stuck_study_id
                round_record["rows_after_auto_skip"] = after_skip_rows
                round_record["auto_skip_row_delta"] = skip_delta
                print(
                    f"[round {round_idx}] auto-skip inserted for {stuck_study_id}; "
                    f"rows now {after_skip_rows} (+{skip_delta})",
                    flush=True,
                )

        if rerun_status_set:
            if after_rerun_candidates <= 0:
                print("All rerun-status candidates have been re-evaluated.", flush=True)
                break
            if rerun_delta < 0:
                stall_rounds = 0
            elif row_delta <= 0 and not result["timed_out"] and result["returncode"] == 0:
                stall_rounds += 1
                print(
                    f"No rerun-status reduction in this round "
                    f"(stall {stall_rounds}/{args.max_stall_rounds}).",
                    flush=True,
                )
                if stall_rounds >= args.max_stall_rounds:
                    print("Reached rerun stall limit; stopping early.", flush=True)
                    break
        else:
            if row_delta <= 0 and not result["timed_out"] and result["returncode"] == 0:
                print("No new rows appended; stopping early.", flush=True)
                break

    report = {
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_rows": args.target_rows,
        "step_batch": args.step_batch,
        "round_timeout_sec": args.round_timeout_sec,
        "max_rounds": args.max_rounds,
        "fast_mode": args.fast_mode,
        "diag_jsonl": str(args.diag_jsonl) if args.diag_jsonl else None,
        "diag_parser_probe": args.diag_parser_probe,
        "per_study_timeout_sec": args.per_study_timeout_sec,
        "rerun_statuses": args.rerun_statuses,
        "rerun_statuses_parsed": sorted(rerun_status_set),
        "max_stall_rounds": args.max_stall_rounds,
        "ocr_threshold": args.ocr_threshold,
        "extract_tables": bool(args.extract_tables),
        "enable_advanced": bool(args.enable_advanced),
        "aggressive_ocr_correction": bool(args.aggressive_ocr_correction),
        "start_rows": start_rows,
        "end_rows": current_rows,
        "total_added": current_rows - start_rows,
        "start_rerun_candidates": start_rerun_candidates,
        "end_rerun_candidates": current_rerun_candidates,
        "stall_rounds_at_end": stall_rounds,
        "interrupted": interrupted,
        "rounds": rounds,
    }

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    with args.report_json.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print(f"Wrote report: {args.report_json}", flush=True)
    return 130 if interrupted else 0


if __name__ == "__main__":
    raise SystemExit(main())
