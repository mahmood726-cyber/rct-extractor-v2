#!/usr/bin/env python3
"""Run extractor across a local PDF corpus with resume + timeout safeguards."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from _path_utils import default_corpus_dir
except ImportError:
    from scripts._path_utils import default_corpus_dir


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INLINE_SCRIPT = r"""
import json
import sys
import traceback

from src.core.pdf_extraction_pipeline import PDFExtractionPipeline
from src.core.enhanced_extractor_v3 import to_dict

pdf_path = sys.argv[1]
opts = json.loads(sys.argv[2])

try:
    pipeline = PDFExtractionPipeline(
        extract_diagnostics=False,
        run_rct_classification=False,
        score_primary_outcomes=False,
        include_page_audit=False,
        compute_raw_effects=bool(opts.get("compute_raw_effects", True)),
        extract_tables=bool(opts.get("extract_tables", True)),
        enable_advanced=bool(opts.get("enable_advanced", False)),
        enable_llm=False,
        ocr_threshold=float(opts.get("ocr_threshold", 100.0)),
        aggressive_ocr_correction=bool(opts.get("aggressive_ocr_correction", True)),
    )
    result = pipeline.extract_from_pdf(pdf_path)
    payload = {
        "ok": True,
        "effects": [to_dict(e) for e in (result.effect_estimates or [])],
        "meta": {
            "num_pages": getattr(result, "num_pages", None),
            "extraction_method": getattr(result, "extraction_method", None),
            "is_born_digital": getattr(result, "is_born_digital", None),
            "total_characters": getattr(result, "total_characters", None),
            "warning_count": len(getattr(result, "warnings", []) or []),
            "error_count": len(getattr(result, "errors", []) or []),
            "pipeline_errors": list(getattr(result, "errors", []) or []),
            "pipeline_warnings": list(getattr(result, "warnings", []) or []),
        },
    }
except Exception as exc:
    payload = {
        "ok": False,
        "error": str(exc),
        "traceback_tail": traceback.format_exc(limit=6)[-1200:],
    }

print(json.dumps(payload, ensure_ascii=False))
"""


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


def _discover_pdfs(input_dir: Path, recursive: bool) -> List[Path]:
    if recursive:
        paths = list(input_dir.rglob("*.pdf"))
    else:
        paths = list(input_dir.glob("*.pdf"))
    files = [p for p in paths if p.is_file()]
    files.sort(key=lambda p: str(p).lower())
    return files


def _file_signature(path: Path) -> Dict[str, int]:
    stat = path.stat()
    return {
        "size_bytes": int(stat.st_size),
        "mtime_ns": int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))),
    }


def _pmcid_from_path(path: Path) -> Optional[str]:
    match = re.search(r"(PMC\d+)", path.name, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper()


def _normalize_effect(effect: Dict) -> Dict:
    source_text = str(effect.get("source_text") or "").strip()
    warnings_raw = effect.get("warnings")
    if isinstance(warnings_raw, list):
        warnings = [str(item) for item in warnings_raw]
    elif warnings_raw:
        warnings = [str(warnings_raw)]
    else:
        warnings = []

    return {
        "type": str(effect.get("type") or "").upper() or None,
        "effect_size": _to_float(effect.get("effect_size")),
        "ci_lower": _to_float(effect.get("ci_lower")),
        "ci_upper": _to_float(effect.get("ci_upper")),
        "p_value": _to_float(effect.get("p_value")),
        "standard_error": _to_float(effect.get("standard_error")),
        "se_method": str(effect.get("se_method") or "") or None,
        "raw_confidence": _to_float(effect.get("raw_confidence")),
        "calibrated_confidence": _to_float(effect.get("calibrated_confidence")),
        "automation_tier": str(effect.get("automation_tier") or "") or None,
        "source_text": source_text[:400],
        "char_start": _safe_int(effect.get("char_start")),
        "char_end": _safe_int(effect.get("char_end")),
        "warnings": warnings,
        "page_number": _safe_int(effect.get("page_number")),
    }


def _effect_score(effect: Dict) -> Tuple[int, int, int, int, float, int]:
    source_text = str(effect.get("source_text") or "").strip().lower()
    has_ci = effect.get("ci_lower") is not None and effect.get("ci_upper") is not None
    has_uncertainty = has_ci or effect.get("standard_error") is not None
    has_type = bool(effect.get("type"))
    is_lax = source_text.startswith("[lax]")
    is_computed = source_text.startswith("[computed from raw data]")
    confidence = float(effect.get("calibrated_confidence") or 0.0)
    warnings = effect.get("warnings") or []
    warning_penalty = -len(warnings) if isinstance(warnings, list) else -1
    return (
        1 if has_uncertainty else 0,
        1 if has_ci else 0,
        1 if has_type else 0,
        0 if (is_lax or is_computed) else 1,
        confidence,
        warning_penalty,
    )


def _choose_best(effects: Sequence[Dict]) -> Optional[Dict]:
    cleaned = [e for e in effects if e.get("effect_size") is not None]
    if not cleaned:
        return None
    ranked = sorted(cleaned, key=_effect_score, reverse=True)
    best = dict(ranked[0])
    if best.get("page_number") is None:
        best["page_number"] = None
    return best


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
                continue
            rel = str(row.get("pdf_relpath") or "").replace("\\", "/")
            if not rel:
                continue
            latest[rel] = row
    return latest


def _same_signature(row: Dict, signature: Dict[str, int]) -> bool:
    recorded = row.get("file_signature") or {}
    try:
        recorded_size = int(recorded.get("size_bytes"))
        recorded_mtime = int(recorded.get("mtime_ns"))
    except (TypeError, ValueError):
        return False
    return recorded_size == int(signature["size_bytes"]) and recorded_mtime == int(signature["mtime_ns"])


def _shard_filter(items: Sequence[Dict], shard_index: int, num_shards: int) -> List[Dict]:
    if num_shards <= 1:
        return list(items)
    if shard_index < 0 or shard_index >= num_shards:
        raise ValueError("--shard-index must be in [0, --num-shards).")
    return [item for idx, item in enumerate(items) if idx % num_shards == shard_index]


def _parse_payload(stdout_text: str) -> Optional[Dict]:
    lines = [line.strip() for line in stdout_text.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            payload = json.loads(line)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            continue
    return None


def _extract_one(task: Dict, args: argparse.Namespace) -> Dict:
    pdf_path = Path(task["pdf_path"])
    started = time.perf_counter()

    options = {
        "compute_raw_effects": bool(args.compute_raw_effects),
        "extract_tables": bool(args.extract_tables),
        "enable_advanced": bool(args.enable_advanced),
        "ocr_threshold": float(args.ocr_threshold),
        "aggressive_ocr_correction": bool(args.aggressive_ocr_correction),
    }

    command = [
        sys.executable,
        "-c",
        DEFAULT_INLINE_SCRIPT,
        str(pdf_path),
        json.dumps(options, ensure_ascii=False),
    ]

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    result: Dict[str, object] = {
        "study_id": task["study_id"],
        "pdf_relpath": task["pdf_relpath"],
        "pdf_path": task["pdf_path"],
        "pmcid": task["pmcid"],
        "file_signature": task["file_signature"],
        "processed_at_utc": _utc_now(),
        "status": "error",
        "n_extractions": 0,
        "best_match": None,
        "top_extractions": [],
        "meta": {
            "elapsed_sec": None,
            "timed_out": False,
            "return_code": None,
        },
        "error": None,
    }

    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=float(args.per_pdf_timeout_sec),
            env=env,
        )
    except subprocess.TimeoutExpired:
        elapsed = round(time.perf_counter() - started, 3)
        result["status"] = "timeout"
        result["error"] = f"timeout_{int(args.per_pdf_timeout_sec)}s"
        result["meta"] = {
            "elapsed_sec": elapsed,
            "timed_out": True,
            "return_code": None,
            "stdout_tail": "",
            "stderr_tail": "",
        }
        return result
    except Exception as exc:
        elapsed = round(time.perf_counter() - started, 3)
        result["status"] = "error"
        result["error"] = f"subprocess_exception: {exc}"
        result["meta"] = {
            "elapsed_sec": elapsed,
            "timed_out": False,
            "return_code": None,
            "stdout_tail": "",
            "stderr_tail": "",
        }
        return result

    elapsed = round(time.perf_counter() - started, 3)
    stdout_tail = (completed.stdout or "")[-2000:]
    stderr_tail = (completed.stderr or "")[-2000:]

    payload = _parse_payload(completed.stdout or "")
    if completed.returncode != 0:
        result["status"] = "error"
        result["error"] = f"extractor_returncode_{completed.returncode}"
        result["meta"] = {
            "elapsed_sec": elapsed,
            "timed_out": False,
            "return_code": completed.returncode,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
        }
        return result

    if not payload:
        result["status"] = "error"
        result["error"] = "missing_json_payload"
        result["meta"] = {
            "elapsed_sec": elapsed,
            "timed_out": False,
            "return_code": completed.returncode,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
        }
        return result

    if not payload.get("ok"):
        result["status"] = "error"
        result["error"] = str(payload.get("error") or "extractor_failed")
        result["meta"] = {
            "elapsed_sec": elapsed,
            "timed_out": False,
            "return_code": completed.returncode,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
            "extractor_traceback_tail": payload.get("traceback_tail"),
        }
        return result

    raw_effects = payload.get("effects") or []
    effects: List[Dict] = []
    for item in raw_effects:
        if isinstance(item, dict):
            normalized = _normalize_effect(item)
            if normalized.get("effect_size") is not None:
                effects.append(normalized)

    best = _choose_best(effects)
    top = sorted(effects, key=_effect_score, reverse=True)[: int(args.top_extractions)]

    result["status"] = "extracted" if effects else "no_extraction"
    result["n_extractions"] = len(effects)
    result["best_match"] = best
    result["top_extractions"] = top
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    result["meta"] = {
        "elapsed_sec": elapsed,
        "timed_out": False,
        "return_code": completed.returncode,
        "num_pages": _safe_int(meta.get("num_pages")),
        "extraction_method": meta.get("extraction_method"),
        "is_born_digital": meta.get("is_born_digital"),
        "total_characters": _safe_int(meta.get("total_characters")),
        "warning_count": _safe_int(meta.get("warning_count")),
        "error_count": _safe_int(meta.get("error_count")),
        "pipeline_errors": meta.get("pipeline_errors") if isinstance(meta.get("pipeline_errors"), list) else [],
        "pipeline_warnings": meta.get("pipeline_warnings") if isinstance(meta.get("pipeline_warnings"), list) else [],
    }
    return result


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _build_summary(rows: Iterable[Dict], expected_total: int, pending: int) -> Dict:
    row_list = list(rows)
    status_counts = Counter(str(row.get("status") or "unknown") for row in row_list)

    extracted_rows = [row for row in row_list if str(row.get("status")) == "extracted"]
    best_rows = [row for row in row_list if isinstance(row.get("best_match"), dict)]
    with_ci = 0
    with_se = 0
    computed_best = 0
    effect_type_counts: Counter = Counter()
    elapsed_values: List[float] = []

    for row in best_rows:
        best = row.get("best_match") or {}
        if best.get("ci_lower") is not None and best.get("ci_upper") is not None:
            with_ci += 1
        if best.get("standard_error") is not None:
            with_se += 1
        source_text = str(best.get("source_text") or "").strip().lower()
        if source_text.startswith("[computed from raw data]"):
            computed_best += 1
        effect_type = str(best.get("type") or "").upper().strip()
        if effect_type:
            effect_type_counts[effect_type] += 1

    for row in row_list:
        meta = row.get("meta") or {}
        elapsed = _to_float(meta.get("elapsed_sec"))
        if elapsed is not None and elapsed >= 0:
            elapsed_values.append(elapsed)

    elapsed_summary = {
        "count": len(elapsed_values),
        "median_sec": round(float(median(elapsed_values)), 3) if elapsed_values else None,
        "mean_sec": round(sum(elapsed_values) / len(elapsed_values), 3) if elapsed_values else None,
        "max_sec": round(max(elapsed_values), 3) if elapsed_values else None,
    }

    processed_total = len(row_list)
    summary = {
        "generated_at_utc": _utc_now(),
        "expected_total_pdfs": expected_total,
        "processed_total": processed_total,
        "pending_total": pending,
        "status_counts": dict(sorted(status_counts.items())),
        "rates": {
            "processed_fraction": _pct(processed_total, expected_total),
            "extraction_coverage": _pct(len(extracted_rows), processed_total),
            "best_match_rate": _pct(len(best_rows), processed_total),
            "best_match_with_ci_rate": _pct(with_ci, len(best_rows)),
            "best_match_with_se_rate": _pct(with_se, len(best_rows)),
            "computed_best_share": _pct(computed_best, len(best_rows)),
        },
        "counts": {
            "extracted_rows": len(extracted_rows),
            "best_match_rows": len(best_rows),
            "best_match_with_ci": with_ci,
            "best_match_with_se": with_se,
            "computed_best_rows": computed_best,
        },
        "best_effect_type_counts": dict(sorted(effect_type_counts.items())),
        "timing_sec": elapsed_summary,
    }
    return summary


def _write_summary_markdown(path: Path, summary: Dict, args: argparse.Namespace) -> None:
    lines: List[str] = []
    lines.append("# PDF Corpus Extraction Report")
    lines.append("")
    lines.append(f"- Generated UTC: {summary.get('generated_at_utc')}")
    lines.append(f"- Input dir: `{args.input_dir}`")
    lines.append(f"- Expected PDFs in run scope: {summary.get('expected_total_pdfs')}")
    lines.append(f"- Processed PDFs: {summary.get('processed_total')}")
    lines.append(f"- Pending PDFs: {summary.get('pending_total')}")
    lines.append(
        f"- Extraction coverage (status=extracted): {summary.get('rates', {}).get('extraction_coverage', 0.0):.4f}"
    )
    lines.append(f"- Best-match rows: {summary.get('counts', {}).get('best_match_rows', 0)}")
    lines.append(
        f"- Best-match with CI: {summary.get('counts', {}).get('best_match_with_ci', 0)} "
        f"({summary.get('rates', {}).get('best_match_with_ci_rate', 0.0):.4f})"
    )
    lines.append("")
    lines.append("## Status Counts")
    lines.append("")
    for key, value in sorted((summary.get("status_counts") or {}).items()):
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("## Best Effect Type Counts")
    lines.append("")
    effect_counts = summary.get("best_effect_type_counts") or {}
    if effect_counts:
        for key, value in sorted(effect_counts.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")

    timing = summary.get("timing_sec") or {}
    lines.append("")
    lines.append("## Timing")
    lines.append("")
    lines.append(f"- Median sec/PDF: {timing.get('median_sec')}")
    lines.append(f"- Mean sec/PDF: {timing.get('mean_sec')}")
    lines.append(f"- Max sec/PDF: {timing.get('max_sec')}")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _iter_tasks(pdf_paths: Sequence[Path], input_dir: Path) -> List[Dict]:
    tasks: List[Dict] = []
    for path in pdf_paths:
        rel = str(path.relative_to(input_dir)).replace("\\", "/")
        signature = _file_signature(path)
        tasks.append(
            {
                "study_id": path.stem,
                "pdf_relpath": rel,
                "pdf_path": str(path.resolve()),
                "pmcid": _pmcid_from_path(path),
                "file_signature": signature,
            }
        )
    return tasks


def _task_needs_run(task: Dict, latest_rows: Dict[str, Dict], resume: bool) -> bool:
    if not resume:
        return True
    existing = latest_rows.get(task["pdf_relpath"])
    if not existing:
        return True
    return not _same_signature(existing, task["file_signature"])


def _process_tasks(
    tasks: List[Dict],
    args: argparse.Namespace,
    output_jsonl: Path,
) -> int:
    if not tasks:
        return 0

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.resume else "w"
    processed = 0
    started = time.perf_counter()
    total = len(tasks)
    print(f"Running extraction on {total} PDFs with workers={args.workers}")

    with output_jsonl.open(mode, encoding="utf-8", newline="\n") as handle:
        with ThreadPoolExecutor(max_workers=int(args.workers)) as executor:
            future_to_task: Dict[Future, Dict] = {}
            task_iter = iter(tasks)

            for _ in range(min(int(args.workers), total)):
                task = next(task_iter, None)
                if task is None:
                    break
                fut = executor.submit(_extract_one, task, args)
                future_to_task[fut] = task

            while future_to_task:
                done, _ = wait(set(future_to_task.keys()), return_when=FIRST_COMPLETED)
                for fut in done:
                    task = future_to_task.pop(fut)
                    try:
                        row = fut.result()
                    except Exception as exc:
                        row = {
                            "study_id": task["study_id"],
                            "pdf_relpath": task["pdf_relpath"],
                            "pdf_path": task["pdf_path"],
                            "pmcid": task["pmcid"],
                            "file_signature": task["file_signature"],
                            "processed_at_utc": _utc_now(),
                            "status": "error",
                            "n_extractions": 0,
                            "best_match": None,
                            "top_extractions": [],
                            "meta": {
                                "elapsed_sec": None,
                                "timed_out": False,
                                "return_code": None,
                            },
                            "error": f"future_exception: {exc}",
                        }

                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    handle.flush()

                    processed += 1
                    if processed == 1 or processed % int(args.progress_every) == 0 or processed == total:
                        elapsed = max(time.perf_counter() - started, 1e-6)
                        rate = processed / elapsed
                        eta = (total - processed) / rate if rate > 0 else 0.0
                        print(
                            f"[{processed}/{total}] {task['pdf_relpath']} status={row.get('status')} "
                            f"rate={rate:.2f}/s eta={eta/60:.1f}m"
                        )
                    if args.print_errors and row.get("status") in {"error", "timeout"}:
                        print(
                            f"  issue: {task['pdf_relpath']} -> {row.get('status')} "
                            f"error={row.get('error')}"
                        )

                    next_task = next(task_iter, None)
                    if next_task is not None:
                        next_future = executor.submit(_extract_one, next_task, args)
                        future_to_task[next_future] = next_task

    return processed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_corpus_dir("cardiology_rcts"),
        help="Directory containing PDF files.",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1/results.jsonl"),
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=Path("output/cardiology_oa_full_v1/summary.json"),
    )
    parser.add_argument(
        "--summary-md",
        type=Path,
        default=Path("output/cardiology_oa_full_v1/report.md"),
    )
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Recursively discover PDFs.",
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip files already processed with matching file signature.",
    )
    parser.add_argument("--workers", type=int, default=2, help="Concurrent subprocess workers.")
    parser.add_argument("--per-pdf-timeout-sec", type=float, default=150.0)
    parser.add_argument(
        "--extract-tables",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable table extraction in pipeline.",
    )
    parser.add_argument(
        "--enable-advanced",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable advanced extraction path.",
    )
    parser.add_argument(
        "--compute-raw-effects",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable raw-data computed fallback effects.",
    )
    parser.add_argument("--ocr-threshold", type=float, default=100.0)
    parser.add_argument(
        "--aggressive-ocr-correction",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--top-extractions", type=int, default=8)
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--print-errors", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-pdfs", type=int, default=None, help="Optional cap for debugging.")
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    args = parser.parse_args()

    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")
    if not args.input_dir.is_dir():
        raise NotADirectoryError(f"--input-dir is not a directory: {args.input_dir}")
    if args.workers <= 0:
        raise ValueError("--workers must be > 0")
    if args.per_pdf_timeout_sec <= 0:
        raise ValueError("--per-pdf-timeout-sec must be > 0")
    if args.top_extractions <= 0:
        raise ValueError("--top-extractions must be > 0")
    if args.progress_every <= 0:
        raise ValueError("--progress-every must be > 0")
    if args.num_shards <= 0:
        raise ValueError("--num-shards must be > 0")
    if args.shard_index < 0 or args.shard_index >= args.num_shards:
        raise ValueError("--shard-index must satisfy 0 <= shard-index < num-shards")

    pdf_paths = _discover_pdfs(args.input_dir, recursive=bool(args.recursive))
    tasks = _iter_tasks(pdf_paths, args.input_dir)
    tasks = _shard_filter(tasks, shard_index=int(args.shard_index), num_shards=int(args.num_shards))
    if args.max_pdfs is not None:
        if args.max_pdfs <= 0:
            raise ValueError("--max-pdfs must be > 0 when provided")
        tasks = tasks[: int(args.max_pdfs)]

    print(
        f"Discovered {len(pdf_paths)} PDFs; selected {len(tasks)} "
        f"(shard {args.shard_index}/{args.num_shards}, recursive={args.recursive})"
    )
    if not tasks:
        print("No PDFs selected. Nothing to do.")
        return 0

    latest_before = _load_latest_rows(args.output_jsonl) if args.resume else {}
    pending = [task for task in tasks if _task_needs_run(task, latest_before, resume=bool(args.resume))]
    skipped = len(tasks) - len(pending)
    print(f"Resume check: pending={len(pending)} skipped={skipped}")

    processed_now = _process_tasks(tasks=pending, args=args, output_jsonl=args.output_jsonl)

    latest_after = _load_latest_rows(args.output_jsonl)
    selected_rel = {task["pdf_relpath"] for task in tasks}
    selected_rows = [row for rel, row in latest_after.items() if rel in selected_rel]
    pending_after = max(len(tasks) - len(selected_rows), 0)

    summary = _build_summary(selected_rows, expected_total=len(tasks), pending=pending_after)
    summary["run"] = {
        "processed_now": processed_now,
        "resume_skipped": skipped,
        "workers": int(args.workers),
        "timeout_sec": float(args.per_pdf_timeout_sec),
        "shard_index": int(args.shard_index),
        "num_shards": int(args.num_shards),
        "recursive": bool(args.recursive),
        "max_pdfs": int(args.max_pdfs) if args.max_pdfs is not None else None,
    }
    summary["paths"] = {
        "input_dir": str(args.input_dir.resolve()),
        "output_jsonl": str(args.output_jsonl.resolve()),
        "summary_json": str(args.summary_json.resolve()),
        "summary_md": str(args.summary_md.resolve()),
    }

    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    with args.summary_json.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
    _write_summary_markdown(args.summary_md, summary, args)

    print("Corpus extraction complete")
    print(f"Processed this run: {processed_now}")
    print(f"Output JSONL: {args.output_jsonl}")
    print(f"Summary JSON: {args.summary_json}")
    print(f"Summary MD: {args.summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
