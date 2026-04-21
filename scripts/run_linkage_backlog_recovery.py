#!/usr/bin/env python3
"""Targeted recovery pass for meta-linked extraction failures."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from _path_utils import default_corpus_dir
except ImportError:
    from scripts._path_utils import default_corpus_dir

from scripts.extract_pdf_corpus import (
    _extract_one,
    _file_signature,
    _load_latest_rows,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _has_extractable_best(row: Optional[Dict]) -> bool:
    if not isinstance(row, dict):
        return False
    if str(row.get("status") or "") != "extracted":
        return False
    best = row.get("best_match") or {}
    return best.get("effect_size") is not None


def _to_task(input_dir: Path, backlog_row: Dict, baseline_row: Dict) -> Optional[Dict]:
    relpath = str(backlog_row.get("pdf_relpath") or baseline_row.get("pdf_relpath") or "").replace("\\", "/")
    if not relpath:
        return None
    pdf_path = input_dir / relpath
    if not pdf_path.exists() or not pdf_path.is_file():
        return None
    return {
        "study_id": str(backlog_row.get("study_id") or baseline_row.get("study_id") or pdf_path.stem),
        "pdf_relpath": relpath,
        "pdf_path": str(pdf_path.resolve()),
        "pmcid": str(backlog_row.get("pmcid") or baseline_row.get("pmcid") or ""),
        "file_signature": _file_signature(pdf_path),
    }


def _retry_namespace(
    *,
    timeout_sec: float,
    extract_tables: bool,
    enable_advanced: bool,
    compute_raw_effects: bool,
    ocr_threshold: float,
    aggressive_ocr_correction: bool,
    top_extractions: int,
) -> argparse.Namespace:
    ns = argparse.Namespace()
    ns.per_pdf_timeout_sec = float(timeout_sec)
    ns.extract_tables = bool(extract_tables)
    ns.enable_advanced = bool(enable_advanced)
    ns.compute_raw_effects = bool(compute_raw_effects)
    ns.ocr_threshold = float(ocr_threshold)
    ns.aggressive_ocr_correction = bool(aggressive_ocr_correction)
    ns.top_extractions = int(top_extractions)
    return ns


def _build_passes(args: argparse.Namespace) -> List[Dict]:
    return [
        {
            "name": "advanced_tables_raw",
            "timeout_sec": float(args.timeout_pass1_sec),
            "extract_tables": bool(args.pass1_extract_tables),
            "enable_advanced": True,
            "compute_raw_effects": bool(args.compute_raw_effects),
        },
        {
            "name": "advanced_no_tables_raw",
            "timeout_sec": float(args.timeout_pass2_sec),
            "extract_tables": False,
            "enable_advanced": True,
            "compute_raw_effects": bool(args.compute_raw_effects),
        },
        {
            "name": "baseline_no_tables_raw",
            "timeout_sec": float(args.timeout_pass3_sec),
            "extract_tables": False,
            "enable_advanced": False,
            "compute_raw_effects": bool(args.compute_raw_effects),
        },
    ]


def _run_candidate(
    *,
    task: Dict,
    backlog_row: Dict,
    baseline_row: Dict,
    pass_defs: List[Dict],
    args: argparse.Namespace,
) -> Dict:
    baseline_status = str(baseline_row.get("status") or "")
    attempts: List[Dict] = []
    selected_row: Optional[Dict] = None
    selected_pass: Optional[str] = None
    last_row: Optional[Dict] = None

    for pass_def in pass_defs:
        ns = _retry_namespace(
            timeout_sec=float(pass_def["timeout_sec"]),
            extract_tables=bool(pass_def["extract_tables"]),
            enable_advanced=bool(pass_def["enable_advanced"]),
            compute_raw_effects=bool(pass_def["compute_raw_effects"]),
            ocr_threshold=float(args.ocr_threshold),
            aggressive_ocr_correction=bool(args.aggressive_ocr_correction),
            top_extractions=int(args.top_extractions),
        )
        row = _extract_one(task, ns)
        last_row = row
        best = row.get("best_match") or {}
        attempts.append(
            {
                "pass_name": str(pass_def["name"]),
                "timeout_sec": float(pass_def["timeout_sec"]),
                "extract_tables": bool(pass_def["extract_tables"]),
                "enable_advanced": bool(pass_def["enable_advanced"]),
                "compute_raw_effects": bool(pass_def["compute_raw_effects"]),
                "status": str(row.get("status") or ""),
                "n_extractions": int(row.get("n_extractions") or 0),
                "best_type": str(best.get("type") or ""),
                "best_has_ci": bool(best.get("ci_lower") is not None and best.get("ci_upper") is not None),
                "elapsed_sec": (row.get("meta") or {}).get("elapsed_sec"),
                "error": row.get("error"),
            }
        )
        if _has_extractable_best(row):
            selected_row = row
            selected_pass = str(pass_def["name"])
            break

    final_row = selected_row if selected_row is not None else last_row
    final_status = str((final_row or {}).get("status") or "not_attempted")
    improved = (baseline_status != "extracted") and _has_extractable_best(final_row)

    attempt_record = {
        "processed_at_utc": _utc_now(),
        "study_id": task.get("study_id"),
        "pdf_relpath": task.get("pdf_relpath"),
        "pmcid": task.get("pmcid"),
        "pmid": str(backlog_row.get("pmid") or ""),
        "baseline_status": baseline_status,
        "linked_meta_matches_total": int(backlog_row.get("meta_matches_total") or 0),
        "linked_citing_total_considered": int(backlog_row.get("citing_total_considered") or 0),
        "attempts": attempts,
        "selected_pass": selected_pass,
        "final_status": final_status,
        "improved_to_extracted": bool(improved),
    }

    improved_row: Optional[Dict] = None
    if improved and isinstance(final_row, dict):
        improved_row = dict(final_row)
        meta = dict(improved_row.get("meta") or {})
        meta["linkage_recovery"] = {
            "source": "run_linkage_backlog_recovery.py",
            "generated_at_utc": _utc_now(),
            "baseline_status": baseline_status,
            "linked_meta_matches_total": int(backlog_row.get("meta_matches_total") or 0),
            "linked_citing_total_considered": int(backlog_row.get("citing_total_considered") or 0),
            "linked_trial_pmid": str(backlog_row.get("pmid") or ""),
            "selected_pass": selected_pass,
            "attempts": attempts,
        }
        improved_row["meta"] = meta

    return {
        "attempt_record": attempt_record,
        "improved_row": improved_row,
        "selected_pass": selected_pass,
        "final_status": final_status,
        "baseline_status": baseline_status,
        "linked_meta_matches_total": int(backlog_row.get("meta_matches_total") or 0),
    }


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_corpus_dir("cardiology_rcts"),
    )
    parser.add_argument(
        "--backlog-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/linkage_first_backlog.jsonl"),
    )
    parser.add_argument(
        "--baseline-results-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/results.jsonl"),
    )
    parser.add_argument(
        "--output-improved-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/linkage_recovery_improved.jsonl"),
    )
    parser.add_argument(
        "--output-attempts-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/linkage_recovery_attempts.jsonl"),
    )
    parser.add_argument(
        "--output-summary-json",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/linkage_recovery_summary.json"),
    )
    parser.add_argument(
        "--output-summary-md",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/linkage_recovery_summary.md"),
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-pass1-sec", type=float, default=180.0)
    parser.add_argument("--timeout-pass2-sec", type=float, default=120.0)
    parser.add_argument("--timeout-pass3-sec", type=float, default=90.0)
    parser.add_argument(
        "--pass1-extract-tables",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable table extraction in pass1.",
    )
    parser.add_argument(
        "--compute-raw-effects",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable raw-effect fallback in retry passes.",
    )
    parser.add_argument("--ocr-threshold", type=float, default=100.0)
    parser.add_argument(
        "--aggressive-ocr-correction",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--top-extractions", type=int, default=8)
    parser.add_argument("--max-candidates", type=int, default=None)
    parser.add_argument("--progress-every", type=int, default=10)
    args = parser.parse_args()

    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")
    if not args.backlog_jsonl.exists():
        raise FileNotFoundError(f"Backlog JSONL not found: {args.backlog_jsonl}")
    if not args.baseline_results_jsonl.exists():
        raise FileNotFoundError(f"Baseline results JSONL not found: {args.baseline_results_jsonl}")
    if args.workers <= 0:
        raise ValueError("--workers must be > 0")
    if args.progress_every <= 0:
        raise ValueError("--progress-every must be > 0")
    if args.max_candidates is not None and args.max_candidates <= 0:
        raise ValueError("--max-candidates must be > 0 when provided")

    backlog_rows = _load_jsonl(args.backlog_jsonl)
    baseline_latest = _load_latest_rows(args.baseline_results_jsonl)
    pass_defs = _build_passes(args)

    candidates: List[Dict] = []
    skipped = Counter()
    for backlog_row in backlog_rows:
        relpath = str(backlog_row.get("pdf_relpath") or "").replace("\\", "/")
        if not relpath:
            skipped["missing_relpath"] += 1
            continue
        baseline_row = baseline_latest.get(relpath)
        if not isinstance(baseline_row, dict):
            skipped["missing_baseline_row"] += 1
            continue
        if _has_extractable_best(baseline_row):
            skipped["already_extracted"] += 1
            continue
        task = _to_task(args.input_dir, backlog_row, baseline_row)
        if task is None:
            skipped["missing_pdf"] += 1
            continue
        candidates.append(
            {
                "task": task,
                "backlog_row": backlog_row,
                "baseline_row": baseline_row,
            }
        )

    if args.max_candidates is not None:
        candidates = candidates[: int(args.max_candidates)]

    attempts_out: List[Dict] = []
    improved_out: List[Dict] = []
    selected_pass_counts = Counter()
    final_status_counts = Counter()
    baseline_status_counts = Counter()
    improved_baseline_status_counts = Counter()
    recovered_meta_matches_total = 0

    total = len(candidates)
    print(f"Linkage recovery candidates: {total}")
    started = time.perf_counter()
    processed = 0

    if total > 0:
        with ThreadPoolExecutor(max_workers=int(args.workers)) as executor:
            future_map: Dict[Future, Dict] = {}
            iterator = iter(candidates)

            for _ in range(min(int(args.workers), total)):
                item = next(iterator, None)
                if item is None:
                    break
                fut = executor.submit(
                    _run_candidate,
                    task=item["task"],
                    backlog_row=item["backlog_row"],
                    baseline_row=item["baseline_row"],
                    pass_defs=pass_defs,
                    args=args,
                )
                future_map[fut] = item

            while future_map:
                done, _ = wait(set(future_map.keys()), return_when=FIRST_COMPLETED)
                for fut in done:
                    item = future_map.pop(fut)
                    result = fut.result()
                    attempt_record = result["attempt_record"]
                    improved_row = result["improved_row"]

                    attempts_out.append(attempt_record)
                    baseline_status = str(result["baseline_status"] or "")
                    baseline_status_counts[baseline_status] += 1
                    final_status_counts[str(result["final_status"] or "")] += 1
                    if result["selected_pass"]:
                        selected_pass_counts[str(result["selected_pass"])] += 1

                    if isinstance(improved_row, dict):
                        improved_out.append(improved_row)
                        improved_baseline_status_counts[baseline_status] += 1
                        recovered_meta_matches_total += int(result["linked_meta_matches_total"] or 0)

                    processed += 1
                    if processed == 1 or processed % int(args.progress_every) == 0 or processed == total:
                        elapsed = max(time.perf_counter() - started, 1e-6)
                        rate = processed / elapsed
                        eta = (total - processed) / rate if rate > 0 else 0.0
                        print(f"[{processed}/{total}] processed rate={rate:.2f}/s eta={eta/60:.1f}m")

                    nxt = next(iterator, None)
                    if nxt is not None:
                        next_future = executor.submit(
                            _run_candidate,
                            task=nxt["task"],
                            backlog_row=nxt["backlog_row"],
                            baseline_row=nxt["baseline_row"],
                            pass_defs=pass_defs,
                            args=args,
                        )
                        future_map[next_future] = nxt

    attempts_out.sort(key=lambda row: str(row.get("pdf_relpath") or ""))
    improved_out.sort(key=lambda row: str(row.get("pdf_relpath") or ""))

    _write_jsonl(args.output_attempts_jsonl, attempts_out)
    _write_jsonl(args.output_improved_jsonl, improved_out)

    summary = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "input_dir": str(args.input_dir).replace("\\", "/"),
            "backlog_jsonl": str(args.backlog_jsonl).replace("\\", "/"),
            "baseline_results_jsonl": str(args.baseline_results_jsonl).replace("\\", "/"),
            "workers": int(args.workers),
            "max_candidates": args.max_candidates,
            "passes": pass_defs,
        },
        "counts": {
            "backlog_rows_input": len(backlog_rows),
            "candidates_attempted": total,
            "improved_rows": len(improved_out),
            "recovered_meta_matches_total": recovered_meta_matches_total,
            "skipped": dict(sorted(skipped.items())),
        },
        "rates": {
            "improvement_rate_among_attempted": (len(improved_out) / total) if total else 0.0,
        },
        "distributions": {
            "baseline_status_counts_attempted": dict(sorted(baseline_status_counts.items())),
            "improved_from_baseline_status_counts": dict(sorted(improved_baseline_status_counts.items())),
            "selected_pass_counts": dict(sorted(selected_pass_counts.items())),
            "final_status_counts": dict(sorted(final_status_counts.items())),
        },
        "paths": {
            "output_improved_jsonl": str(args.output_improved_jsonl).replace("\\", "/"),
            "output_attempts_jsonl": str(args.output_attempts_jsonl).replace("\\", "/"),
        },
    }
    _write_json(args.output_summary_json, summary)

    lines: List[str] = []
    lines.append("# Linkage Backlog Recovery Summary")
    lines.append("")
    lines.append(f"- Generated UTC: {summary['generated_at_utc']}")
    lines.append(f"- Backlog input rows: {summary['counts']['backlog_rows_input']}")
    lines.append(f"- Candidates attempted: {summary['counts']['candidates_attempted']}")
    lines.append(f"- Improved rows: {summary['counts']['improved_rows']}")
    lines.append(
        f"- Improvement rate among attempted: {_fmt_pct(summary['rates']['improvement_rate_among_attempted'])}"
    )
    lines.append(f"- Recovered linked meta-match count (sum): {summary['counts']['recovered_meta_matches_total']}")
    lines.append("")
    lines.append("## Attempted Baseline Status")
    lines.append("")
    for key, value in sorted((summary["distributions"].get("baseline_status_counts_attempted") or {}).items()):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Improvement By Pass")
    lines.append("")
    for key, value in sorted((summary["distributions"].get("selected_pass_counts") or {}).items()):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Final Status Counts")
    lines.append("")
    for key, value in sorted((summary["distributions"].get("final_status_counts") or {}).items()):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append(f"- Improved JSONL: `{args.output_improved_jsonl}`")
    lines.append(f"- Attempts JSONL: `{args.output_attempts_jsonl}`")
    lines.append("")
    args.output_summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {args.output_improved_jsonl}")
    print(f"Wrote: {args.output_attempts_jsonl}")
    print(f"Wrote: {args.output_summary_json}")
    print(f"Wrote: {args.output_summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
