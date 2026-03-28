#!/usr/bin/env python3
"""Build a compact adjudication packet for remaining false-negative rows."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover - optional import
    fitz = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_latest_rows(path: Path) -> Dict[str, Dict]:
    latest: Dict[str, Dict] = {}
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            rel = str(row.get("pdf_relpath") or "").replace("\\", "/").strip()
            if not rel:
                continue
            latest[rel] = row
    return latest


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_csv(path: Path, rows: Sequence[Dict]) -> None:
    fieldnames = [
        "spotcheck_rank",
        "spotcheck_bucket",
        "benchmark_id",
        "pmid",
        "pmcid",
        "study_id",
        "pdf_relpath",
        "pdf_abs_path",
        "current_status",
        "consensus_included",
        "consensus_effect_type",
        "consensus_point_estimate",
        "consensus_ci_lower",
        "consensus_ci_upper",
        "validator_exclude_reasons",
        "validator_rct_reason",
        "validator_study_type",
        "validator_trial_signal_count",
        "validator_results_signal_count",
        "validator_non_rct_count",
        "validator_single_arm_count",
        "validator_protocol_count",
        "raw_candidate_effect_type",
        "raw_candidate_point_estimate",
        "raw_candidate_ci_lower",
        "raw_candidate_ci_upper",
        "raw_candidate_confidence",
        "raw_candidate_source_text",
        "manual_check_included",
        "manual_check_effect_type",
        "manual_check_point_estimate",
        "manual_check_ci_lower",
        "manual_check_ci_upper",
        "manual_check_page_number",
        "manual_check_source_text",
        "manual_check_notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})


def _read_pdf_head_text(pdf_path: Path, *, max_pages: int, max_chars: int) -> str:
    if fitz is None:
        return ""
    try:
        doc = fitz.open(str(pdf_path))
    except Exception:
        return ""
    chunks: List[str] = []
    total = 0
    try:
        n = min(int(max_pages), int(doc.page_count))
        for idx in range(n):
            page = doc.load_page(idx)
            text = page.get_text("text")
            chunks.append(text)
            total += len(text)
            if total >= int(max_chars):
                break
    finally:
        doc.close()
    text = "\n".join(chunks)
    if len(text) > int(max_chars):
        text = text[: int(max_chars)]
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-json", type=Path, required=True)
    parser.add_argument("--validated-results-jsonl", type=Path, required=True)
    parser.add_argument("--raw-results-jsonl", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--max-chars", type=int, default=3500)
    args = parser.parse_args()

    for path in (args.eval_json, args.validated_results_jsonl, args.raw_results_jsonl):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")
    if args.max_pages <= 0:
        raise ValueError("--max-pages must be > 0")
    if args.max_chars <= 0:
        raise ValueError("--max-chars must be > 0")

    eval_payload = json.loads(args.eval_json.read_text(encoding="utf-8"))
    eval_rows = eval_payload.get("rows") if isinstance(eval_payload.get("rows"), list) else []

    validated_by_rel = _load_latest_rows(args.validated_results_jsonl)
    raw_by_rel = _load_latest_rows(args.raw_results_jsonl)

    misses: List[Dict] = [
        row
        for row in eval_rows
        if isinstance(row, dict)
        and bool(row.get("gold_included"))
        and not bool(row.get("extracted"))
    ]

    packet_rows: List[Dict] = []
    head_text_rows: List[Dict] = []

    for idx, miss in enumerate(sorted(misses, key=lambda r: str(r.get("benchmark_id") or "")), start=1):
        rel = str(miss.get("pdf_relpath") or "").replace("\\", "/")
        validated = validated_by_rel.get(rel, {})
        raw = raw_by_rel.get(rel, {})

        ai = validated.get("ai_validator") if isinstance(validated.get("ai_validator"), dict) else {}
        validators = ai.get("validators") if isinstance(ai.get("validators"), dict) else {}
        rct_block = validators.get("rct_design") if isinstance(validators.get("rct_design"), dict) else {}
        rct_details = rct_block.get("details") if isinstance(rct_block.get("details"), dict) else {}

        raw_best = raw.get("best_match") if isinstance(raw.get("best_match"), dict) else {}
        pdf_abs = str(validated.get("pdf_path") or raw.get("pdf_path") or "")
        pdf_path = Path(pdf_abs) if pdf_abs else None

        packet = {
            "spotcheck_rank": idx,
            "spotcheck_bucket": "remaining_miss",
            "benchmark_id": miss.get("benchmark_id"),
            "pmid": None,
            "pmcid": None,
            "study_id": miss.get("study_id"),
            "pdf_relpath": rel,
            "pdf_abs_path": pdf_abs.replace("\\", "/") if pdf_abs else "",
            "current_status": validated.get("status"),
            "consensus_included": False,
            "consensus_effect_type": None,
            "consensus_point_estimate": None,
            "consensus_ci_lower": None,
            "consensus_ci_upper": None,
            "validator_exclude_reasons": "; ".join(ai.get("exclude_reasons") or []) if isinstance(ai.get("exclude_reasons"), list) else "",
            "validator_rct_reason": rct_block.get("reason"),
            "validator_study_type": rct_details.get("study_type"),
            "validator_trial_signal_count": rct_details.get("trial_signal_count"),
            "validator_results_signal_count": rct_details.get("results_signal_count"),
            "validator_non_rct_count": rct_details.get("non_rct_count"),
            "validator_single_arm_count": rct_details.get("single_arm_count"),
            "validator_protocol_count": rct_details.get("protocol_count"),
            "raw_candidate_effect_type": raw_best.get("type"),
            "raw_candidate_point_estimate": _to_float(raw_best.get("effect_size")),
            "raw_candidate_ci_lower": _to_float(raw_best.get("ci_lower")),
            "raw_candidate_ci_upper": _to_float(raw_best.get("ci_upper")),
            "raw_candidate_confidence": _to_float(raw_best.get("calibrated_confidence")),
            "raw_candidate_source_text": str(raw_best.get("source_text") or "")[:500],
            "manual_check_included": None,
            "manual_check_effect_type": miss.get("gold_effect_type"),
            "manual_check_point_estimate": _to_float(miss.get("gold_point")),
            "manual_check_ci_lower": _to_float(miss.get("gold_ci_low")),
            "manual_check_ci_upper": _to_float(miss.get("gold_ci_high")),
            "manual_check_page_number": None,
            "manual_check_source_text": "",
            "manual_check_notes": "",
        }
        packet_rows.append(packet)

        head_text = ""
        if pdf_path is not None and pdf_path.exists():
            head_text = _read_pdf_head_text(pdf_path, max_pages=int(args.max_pages), max_chars=int(args.max_chars))
        head_text_rows.append(
            {
                "benchmark_id": packet.get("benchmark_id"),
                "study_id": packet.get("study_id"),
                "pdf_relpath": rel,
                "pdf_abs_path": packet.get("pdf_abs_path"),
                "head_text_excerpt": head_text,
            }
        )

    out_dir = args.output_dir
    csv_path = out_dir / "remaining_miss_sheet.csv"
    jsonl_path = out_dir / "remaining_miss_sheet.jsonl"
    head_text_path = out_dir / "remaining_miss_head_text.jsonl"
    ids_path = out_dir / "remaining_miss_benchmark_ids.txt"
    summary_path = out_dir / "summary.json"
    readme_path = out_dir / "README.md"

    _write_csv(csv_path, packet_rows)
    _write_jsonl(jsonl_path, packet_rows)
    _write_jsonl(head_text_path, head_text_rows)
    ids_path.parent.mkdir(parents=True, exist_ok=True)
    ids_path.write_text(
        "\n".join(str(r.get("benchmark_id") or "") for r in packet_rows if str(r.get("benchmark_id") or "").strip()) + "\n",
        encoding="utf-8",
    )

    summary = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "eval_json": str(args.eval_json).replace("\\", "/"),
            "validated_results_jsonl": str(args.validated_results_jsonl).replace("\\", "/"),
            "raw_results_jsonl": str(args.raw_results_jsonl).replace("\\", "/"),
            "max_pages": int(args.max_pages),
            "max_chars": int(args.max_chars),
        },
        "counts": {
            "remaining_misses": len(packet_rows),
        },
        "paths": {
            "sheet_csv": str(csv_path).replace("\\", "/"),
            "sheet_jsonl": str(jsonl_path).replace("\\", "/"),
            "head_text_jsonl": str(head_text_path).replace("\\", "/"),
            "benchmark_ids_txt": str(ids_path).replace("\\", "/"),
            "summary_json": str(summary_path).replace("\\", "/"),
            "readme_md": str(readme_path).replace("\\", "/"),
        },
    }
    _write_json(summary_path, summary)

    lines = [
        "# Remaining Miss Adjudication Packet",
        "",
        f"- Generated UTC: {summary['generated_at_utc']}",
        f"- Remaining miss rows: {len(packet_rows)}",
        "",
        "## Files",
        "",
        f"- `remaining_miss_sheet.csv`: manual fill sheet (compatible with manual override workflow)",
        f"- `remaining_miss_sheet.jsonl`: same rows as JSONL",
        f"- `remaining_miss_head_text.jsonl`: PDF head-text excerpts",
        f"- `remaining_miss_benchmark_ids.txt`: benchmark ids",
        "",
        "## How To Use",
        "",
        "1. Open each PDF path from `pdf_abs_path` in `remaining_miss_sheet.csv`.",
        "2. Fill `manual_check_*` fields (included/effect/point/CI/page/source/notes).",
        "3. Apply overrides using existing override script if needed.",
    ]
    readme_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {csv_path}")
    print(f"Wrote: {jsonl_path}")
    print(f"Wrote: {head_text_path}")
    print(f"Wrote: {ids_path}")
    print(f"Wrote: {summary_path}")
    print(f"Wrote: {readme_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

