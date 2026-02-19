#!/usr/bin/env python3
"""Probe timeout-prone mega studies with stage-isolated timeouts."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _run_parse_worker(pdf_path: str, queue: mp.Queue) -> None:
    started = time.perf_counter()
    try:
        from src.pdf.pdf_parser import PDFParser

        parser = PDFParser()
        parsed = parser.parse(pdf_path)
        payload = {
            "ok": True,
            "timed_out": False,
            "elapsed_sec": round(time.perf_counter() - started, 4),
            "num_pages": parsed.num_pages,
            "extraction_method": parsed.extraction_method,
            "is_born_digital": parsed.is_born_digital,
            "total_characters": sum(len(p.full_text or "") for p in parsed.pages),
            "error": None,
        }
    except Exception as e:
        payload = {
            "ok": False,
            "timed_out": False,
            "elapsed_sec": round(time.perf_counter() - started, 4),
            "num_pages": None,
            "extraction_method": None,
            "is_born_digital": None,
            "total_characters": None,
            "error": str(e),
        }
    queue.put(payload)


def _run_extract_worker(pdf_path: str, fast_mode: bool, queue: mp.Queue) -> None:
    started = time.perf_counter()
    try:
        from src.core.pdf_extraction_pipeline import PDFExtractionPipeline

        if fast_mode:
            pipeline = PDFExtractionPipeline(
                extract_diagnostics=False,
                extract_tables=False,
                enable_advanced=False,
                enable_llm=False,
            )
        else:
            pipeline = PDFExtractionPipeline()
        result = pipeline.extract_from_pdf(pdf_path)
        payload = {
            "ok": True,
            "timed_out": False,
            "elapsed_sec": round(time.perf_counter() - started, 4),
            "num_pages": getattr(result, "num_pages", None),
            "extraction_method": getattr(result, "extraction_method", None),
            "is_born_digital": getattr(result, "is_born_digital", None),
            "total_characters": getattr(result, "total_characters", None),
            "effect_count": len(getattr(result, "effect_estimates", []) or []),
            "warning_count": len(getattr(result, "warnings", []) or []),
            "error_count": len(getattr(result, "errors", []) or []),
            "error": None,
        }
    except Exception as e:
        payload = {
            "ok": False,
            "timed_out": False,
            "elapsed_sec": round(time.perf_counter() - started, 4),
            "num_pages": None,
            "extraction_method": None,
            "is_born_digital": None,
            "total_characters": None,
            "effect_count": None,
            "warning_count": None,
            "error_count": None,
            "error": str(e),
        }
    queue.put(payload)


def _run_with_timeout(
    worker,
    worker_args: Tuple[Any, ...],
    timeout_sec: int,
) -> Dict[str, Any]:
    queue: mp.Queue = mp.Queue()
    process = mp.Process(target=worker, args=(*worker_args, queue))
    started = time.perf_counter()
    process.start()
    process.join(timeout=timeout_sec)

    if process.is_alive():
        process.terminate()
        process.join(timeout=5)
        return {
            "ok": False,
            "timed_out": True,
            "elapsed_sec": round(time.perf_counter() - started, 4),
            "error": f"timeout_{timeout_sec}s",
        }

    if not queue.empty():
        return queue.get()

    return {
        "ok": False,
        "timed_out": False,
        "elapsed_sec": round(time.perf_counter() - started, 4),
        "error": "worker_returned_no_payload",
    }


def _load_shortlist(path: Path) -> List[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    studies = payload.get("shortlist", [])
    if not isinstance(studies, list):
        return []
    return studies


def _probe_one(
    row: dict,
    parse_timeout_sec: int,
    extract_timeout_sec: int,
    fast_mode: bool,
) -> Dict[str, Any]:
    pdf_path = Path(str(row.get("pdf_path") or ""))
    pdf_exists = pdf_path.exists()
    pdf_size = pdf_path.stat().st_size if pdf_exists else None

    out = {
        "study_id": row.get("study_id"),
        "pmcid": row.get("pmcid"),
        "pdf_path": str(pdf_path) if str(pdf_path) else None,
        "pdf_exists": pdf_exists,
        "pdf_size_bytes": pdf_size,
        "round": row.get("round"),
        "comparisons_count": row.get("comparisons_count"),
        "fast_mode": fast_mode,
        "parse": None,
        "extract": None,
        "suspected_hang_stage": None,
    }

    if not pdf_exists:
        out["parse"] = {"ok": False, "timed_out": False, "error": "pdf_missing"}
        out["extract"] = {"ok": False, "timed_out": False, "error": "pdf_missing"}
        return out

    parse_result = _run_with_timeout(
        _run_parse_worker,
        (str(pdf_path),),
        timeout_sec=parse_timeout_sec,
    )
    out["parse"] = parse_result
    if parse_result.get("timed_out"):
        out["suspected_hang_stage"] = "parse"
        out["extract"] = {
            "ok": False,
            "timed_out": False,
            "error": "skipped_due_to_parse_timeout",
        }
        return out

    extract_result = _run_with_timeout(
        _run_extract_worker,
        (str(pdf_path), fast_mode),
        timeout_sec=extract_timeout_sec,
    )
    out["extract"] = extract_result
    if extract_result.get("timed_out"):
        out["suspected_hang_stage"] = "extract"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shortlist-json",
        type=Path,
        default=Path("output/mega_timeout_shortlist_500.json"),
    )
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--parse-timeout-sec", type=int, default=20)
    parser.add_argument("--extract-timeout-sec", type=int, default=45)
    parser.add_argument(
        "--fast-mode",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("output/mega_timeout_probe_500.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("output/mega_timeout_probe_500.md"),
    )
    args = parser.parse_args()

    if not args.shortlist_json.exists():
        raise FileNotFoundError(f"Missing shortlist: {args.shortlist_json}")
    if args.top_n <= 0:
        raise ValueError("--top-n must be > 0")

    studies = _load_shortlist(args.shortlist_json)[: args.top_n]
    if not studies:
        raise RuntimeError("No studies found in shortlist payload.")

    records: List[Dict[str, Any]] = []
    for idx, row in enumerate(studies, start=1):
        print(f"[{idx}/{len(studies)}] probing {row.get('study_id')}")
        records.append(
            _probe_one(
                row=row,
                parse_timeout_sec=args.parse_timeout_sec,
                extract_timeout_sec=args.extract_timeout_sec,
                fast_mode=args.fast_mode,
            )
        )

    parse_timeouts = sum(1 for r in records if (r.get("parse") or {}).get("timed_out"))
    extract_timeouts = sum(1 for r in records if (r.get("extract") or {}).get("timed_out"))
    parse_ok = sum(1 for r in records if (r.get("parse") or {}).get("ok"))
    extract_ok = sum(1 for r in records if (r.get("extract") or {}).get("ok"))
    parse_elapsed = [
        float((r.get("parse") or {}).get("elapsed_sec"))
        for r in records
        if isinstance((r.get("parse") or {}).get("elapsed_sec"), (int, float))
    ]
    extract_elapsed = [
        float((r.get("extract") or {}).get("elapsed_sec"))
        for r in records
        if isinstance((r.get("extract") or {}).get("elapsed_sec"), (int, float))
    ]

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "shortlist_json": str(args.shortlist_json),
        "top_n": args.top_n,
        "parse_timeout_sec": args.parse_timeout_sec,
        "extract_timeout_sec": args.extract_timeout_sec,
        "fast_mode": args.fast_mode,
        "n_records": len(records),
        "parse_ok": parse_ok,
        "parse_timeouts": parse_timeouts,
        "extract_ok": extract_ok,
        "extract_timeouts": extract_timeouts,
        "parse_elapsed_sec_median": round(sorted(parse_elapsed)[len(parse_elapsed) // 2], 4) if parse_elapsed else None,
        "extract_elapsed_sec_median": round(sorted(extract_elapsed)[len(extract_elapsed) // 2], 4) if extract_elapsed else None,
        "records": records,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines: List[str] = []
    lines.append("# Mega Timeout Stage Probe")
    lines.append("")
    lines.append(f"- Generated UTC: {summary['generated_at_utc']}")
    lines.append(f"- Source shortlist: `{args.shortlist_json}`")
    lines.append(f"- Probed studies: {summary['n_records']}")
    lines.append(f"- Parse ok/timeouts: {summary['parse_ok']}/{summary['parse_timeouts']}")
    lines.append(f"- Extract ok/timeouts: {summary['extract_ok']}/{summary['extract_timeouts']}")
    lines.append(
        f"- Parse/Extract timeouts configured: {summary['parse_timeout_sec']}s / {summary['extract_timeout_sec']}s"
    )
    lines.append("")
    lines.append("| Study ID | Parse | Parse sec | Extract | Extract sec | Suspected Hang |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for rec in records:
        parse = rec.get("parse") or {}
        extract = rec.get("extract") or {}
        lines.append(
            f"| {rec.get('study_id')} | "
            f"{'ok' if parse.get('ok') else ('timeout' if parse.get('timed_out') else 'fail')} | "
            f"{parse.get('elapsed_sec', '')} | "
            f"{'ok' if extract.get('ok') else ('timeout' if extract.get('timed_out') else 'fail')} | "
            f"{extract.get('elapsed_sec', '')} | "
            f"{rec.get('suspected_hang_stage') or ''} |"
        )
    lines.append("")

    args.output_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote JSON: {args.output_json}")
    print(f"Wrote MD: {args.output_md}")
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
