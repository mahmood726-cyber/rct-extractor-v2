#!/usr/bin/env python3
"""Build adjudication worklist and freeze protocol for cardiology linked benchmark."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


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


def _write_jsonl(path: Path, rows: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _priority_tier(status: str, confidence: Optional[float], has_ci: bool, has_effect: bool) -> int:
    if status == "extracted" and has_effect and confidence is not None and confidence >= 0.90 and has_ci:
        return 1
    if status == "extracted":
        return 2
    if status == "no_extraction":
        return 3
    if status == "timeout":
        return 4
    return 5


def _recommended_route(status: str, confidence: Optional[float], has_ci: bool, has_effect: bool) -> str:
    if status == "extracted" and has_effect and confidence is not None and confidence >= 0.90 and has_ci:
        return "fast_verify_model_seed"
    if status == "extracted" and has_effect:
        return "full_verify_model_seed"
    if status == "timeout":
        return "retry_pdf_then_full_read"
    return "full_read_negative_check"


def _batch_count(total: int, batch_size: int, explicit_batches: Optional[int]) -> int:
    if explicit_batches is not None:
        return max(1, explicit_batches)
    return max(1, int(math.ceil(total / float(batch_size))))


def _build_worklist(
    cohort_rows: Sequence[Dict],
    *,
    seed: int,
) -> List[Dict]:
    enriched: List[Dict] = []
    rng = random.Random(seed)

    for row in cohort_rows:
        status = str(row.get("status_snapshot") or "").strip().lower()
        linked_meta = int(row.get("linked_meta_matches_total") or 0)
        linked_citing = int(row.get("linked_citing_total_considered") or 0)
        best = row.get("model_snapshot_best") if isinstance(row.get("model_snapshot_best"), dict) else {}
        effect = _to_float(best.get("effect_size"))
        ci_low = _to_float(best.get("ci_lower"))
        ci_high = _to_float(best.get("ci_upper"))
        conf = _to_float(best.get("calibrated_confidence"))
        has_ci = ci_low is not None and ci_high is not None
        has_effect = effect is not None
        tier = _priority_tier(status=status, confidence=conf, has_ci=has_ci, has_effect=has_effect)
        route = _recommended_route(status=status, confidence=conf, has_ci=has_ci, has_effect=has_effect)

        enriched.append(
            {
                "benchmark_id": str(row.get("benchmark_id") or ""),
                "study_id": str(row.get("study_id") or ""),
                "pdf_relpath": str(row.get("pdf_relpath") or ""),
                "pmcid": str(row.get("pmcid") or ""),
                "pmid": str(row.get("pmid") or ""),
                "status_snapshot": status,
                "linked_meta_matches_total": linked_meta,
                "linked_citing_total_considered": linked_citing,
                "model_type": str(best.get("type") or "").upper() or None,
                "model_effect_size": effect,
                "model_ci_lower": ci_low,
                "model_ci_upper": ci_high,
                "model_p_value": _to_float(best.get("p_value")),
                "model_calibrated_confidence": conf,
                "model_automation_tier": str(best.get("automation_tier") or "") or None,
                "model_source_text": str(best.get("source_text") or ""),
                "model_page_number": best.get("page_number"),
                "priority_tier": tier,
                "recommended_route": route,
                "_tie_breaker": rng.random(),
            }
        )

    enriched.sort(
        key=lambda item: (
            int(item["priority_tier"]),
            -int(item["linked_meta_matches_total"]),
            -int(item["linked_citing_total_considered"]),
            -float(item["model_calibrated_confidence"] if item["model_calibrated_confidence"] is not None else -1.0),
            float(item["_tie_breaker"]),
            str(item["benchmark_id"]),
        )
    )

    for idx, row in enumerate(enriched, start=1):
        row["queue_rank"] = idx
        row.pop("_tie_breaker", None)
    return enriched


def _assign_batches(worklist: Sequence[Dict], n_batches: int) -> List[Dict]:
    out: List[Dict] = []
    for idx, row in enumerate(worklist):
        batch_idx = (idx % n_batches) + 1
        item = dict(row)
        item["batch_id"] = f"batch_{batch_idx:03d}"
        out.append(item)
    return out


def _counts_by(rows: Sequence[Dict], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        token = str(row.get(key) or "")
        counts[token] = counts.get(token, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: kv[0]))


def _batch_counts(rows: Sequence[Dict]) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = {}
    for row in rows:
        batch_id = str(row.get("batch_id") or "")
        status = str(row.get("status_snapshot") or "")
        out.setdefault(batch_id, {})
        out[batch_id][status] = out[batch_id].get(status, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: kv[0]))


def _write_worklist_csv(path: Path, rows: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "queue_rank",
        "batch_id",
        "priority_tier",
        "recommended_route",
        "benchmark_id",
        "study_id",
        "pdf_relpath",
        "pmcid",
        "pmid",
        "status_snapshot",
        "linked_meta_matches_total",
        "linked_citing_total_considered",
        "model_type",
        "model_effect_size",
        "model_ci_lower",
        "model_ci_upper",
        "model_p_value",
        "model_calibrated_confidence",
        "model_automation_tier",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def _write_protocol_md(path: Path, payload: Dict) -> None:
    rows_total = int(payload.get("counts", {}).get("rows_total", 0))
    n_batches = int(payload.get("counts", {}).get("work_batches", 0))
    point_tol = payload.get("consensus_rules", {}).get("point_tolerance")
    ci_tol = payload.get("consensus_rules", {}).get("ci_tolerance")
    zero_tol = payload.get("consensus_rules", {}).get("zero_abs_tolerance")
    lines: List[str] = []
    lines.append("# Cardiology Benchmark Adjudication Freeze Protocol")
    lines.append("")
    lines.append(f"- Generated UTC: {payload.get('generated_at_utc')}")
    lines.append(f"- Benchmark version: {payload.get('benchmark_version')}")
    lines.append(f"- Rows to adjudicate: {rows_total}")
    lines.append(f"- Work batches: {n_batches}")
    lines.append("")
    lines.append("## Completion Gates")
    lines.append("")
    lines.append("1. Both annotators complete all benchmark rows (`included` non-null for each row).")
    lines.append("2. For `included=true`, `effect_type` and `point_estimate` must be non-null.")
    lines.append("3. For `included=true`, `source_text` must be non-empty.")
    lines.append("4. Unresolved dual-annotator rows must be manually adjudicated into `adjudication_template.jsonl`.")
    lines.append("5. Final adjudicated file must contain exactly one row per benchmark id.")
    lines.append("")
    lines.append("## Consensus Rules")
    lines.append("")
    lines.append(f"- Point tolerance: `{point_tol}` relative error.")
    lines.append(f"- CI tolerance: `{ci_tol}` max relative bound error.")
    lines.append(f"- Zero absolute tolerance: `{zero_tol}`.")
    lines.append("- If both annotators mark excluded, consensus is excluded.")
    lines.append("- If included/included but values differ beyond tolerance, row requires manual adjudication.")
    lines.append("")
    lines.append("## Freeze Commands")
    lines.append("")
    lines.append("- Final freeze (fails if adjudication is incomplete):")
    lines.append("")
    lines.append("```bash")
    lines.append(str(payload.get("freeze_command") or "").strip())
    lines.append("```")
    preview_cmd = str(payload.get("preview_command") or "").strip()
    if preview_cmd:
        lines.append("")
        lines.append("- Preview-only (allows partial gold; not for publication metrics):")
        lines.append("")
        lines.append("```bash")
        lines.append(preview_cmd)
        lines.append("```")
    lines.append("")
    lines.append("## Input Locks")
    lines.append("")
    for entry in payload.get("input_files", []):
        lines.append(
            f"- `{entry.get('path')}` | sha256=`{entry.get('sha256')}` | bytes={entry.get('size_bytes')}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=Path("data/benchmarks/cardiology_meta_linked_v1"),
    )
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--n-batches", type=int, default=None)
    parser.add_argument("--seed", type=int, default=20260225)
    parser.add_argument("--consensus-point-tol", type=float, default=0.10)
    parser.add_argument("--consensus-ci-tol", type=float, default=0.15)
    parser.add_argument("--zero-abs-tolerance", type=float, default=0.02)
    parser.add_argument(
        "--system-results-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/results_linkage_boosted_snapshot.jsonl"),
        help="System results file to score against after adjudication freeze.",
    )
    parser.add_argument(
        "--eval-output-json",
        type=Path,
        default=None,
        help="Optional override for evaluation JSON output path.",
    )
    parser.add_argument(
        "--eval-output-md",
        type=Path,
        default=None,
        help="Optional override for evaluation markdown output path.",
    )
    args = parser.parse_args()

    benchmark_dir = args.benchmark_dir
    if not benchmark_dir.exists():
        raise FileNotFoundError(f"--benchmark-dir not found: {benchmark_dir}")
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be > 0")
    if args.n_batches is not None and args.n_batches <= 0:
        raise ValueError("--n-batches must be > 0 when provided")

    manifest_path = benchmark_dir / "manifest.json"
    cohort_path = benchmark_dir / "benchmark_cohort.jsonl"
    annotator_a_path = benchmark_dir / "blinded_template_annotator_a.jsonl"
    annotator_b_path = benchmark_dir / "blinded_template_annotator_b.jsonl"
    adjudication_path = benchmark_dir / "adjudication_template.jsonl"
    model_seed_path = benchmark_dir / "model_seed_adjudicator_only.jsonl"

    required = [manifest_path, cohort_path, annotator_a_path, annotator_b_path, adjudication_path, model_seed_path]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"Missing required benchmark file: {path}")

    manifest = _load_json(manifest_path)
    cohort_rows = _load_jsonl(cohort_path)
    annotator_a_rows = _load_jsonl(annotator_a_path)
    annotator_b_rows = _load_jsonl(annotator_b_path)
    adjudication_rows = _load_jsonl(adjudication_path)
    model_seed_rows = _load_jsonl(model_seed_path)

    n_rows = len(cohort_rows)
    if not (n_rows == len(annotator_a_rows) == len(annotator_b_rows) == len(adjudication_rows) == len(model_seed_rows)):
        raise ValueError(
            "Benchmark/template row-count mismatch: "
            f"cohort={len(cohort_rows)}, a={len(annotator_a_rows)}, b={len(annotator_b_rows)}, "
            f"adjudication={len(adjudication_rows)}, model_seed={len(model_seed_rows)}"
        )

    worklist = _build_worklist(cohort_rows, seed=int(args.seed))
    n_batches = _batch_count(total=len(worklist), batch_size=int(args.batch_size), explicit_batches=args.n_batches)
    worklist = _assign_batches(worklist, n_batches=n_batches)

    worklist_jsonl = benchmark_dir / "adjudication_worklist.jsonl"
    worklist_csv = benchmark_dir / "adjudication_worklist.csv"
    batches_dir = benchmark_dir / "adjudication_batches"
    protocol_json = benchmark_dir / "adjudication_freeze_protocol.json"
    protocol_md = benchmark_dir / "adjudication_freeze_protocol.md"
    summary_json = benchmark_dir / "adjudication_worklist_summary.json"
    eval_json = args.eval_output_json or Path(
        f"output/cardiology_oa_full_v1_fast/{benchmark_dir.name}_benchmark_eval.json"
    )
    eval_md = args.eval_output_md or Path(
        f"output/cardiology_oa_full_v1_fast/{benchmark_dir.name}_benchmark_eval.md"
    )

    _write_jsonl(worklist_jsonl, worklist)
    _write_worklist_csv(worklist_csv, worklist)

    batch_ids = sorted({str(row.get("batch_id") or "") for row in worklist})
    for batch_id in batch_ids:
        rows = [row for row in worklist if row.get("batch_id") == batch_id]
        _write_jsonl(batches_dir / f"{batch_id}.jsonl", rows)
        ids_txt = "\n".join(str(row.get("benchmark_id") or "") for row in rows) + "\n"
        (batches_dir / f"{batch_id}_benchmark_ids.txt").write_text(ids_txt, encoding="utf-8")

    input_files: List[Dict[str, object]] = []
    for path in required:
        input_files.append(
            {
                "path": str(path).replace("\\", "/"),
                "size_bytes": int(path.stat().st_size),
                "sha256": _sha256(path),
            }
        )

    freeze_command = (
        "python scripts/evaluate_cardiology_linked_benchmark.py "
        f"--benchmark-cohort-jsonl {str((benchmark_dir / 'benchmark_cohort.jsonl')).replace('\\', '/')} "
        f"--system-results-jsonl {str(args.system_results_jsonl).replace('\\', '/')} "
        f"--adjudicated-jsonl {str((benchmark_dir / 'adjudication_template.jsonl')).replace('\\', '/')} "
        f"--output-json {str(eval_json).replace('\\', '/')} "
        f"--output-md {str(eval_md).replace('\\', '/')}"
    )
    preview_command = f"{freeze_command} --allow-partial-gold"

    protocol_payload = {
        "protocol_version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "benchmark_version": str(manifest.get("benchmark_version") or benchmark_dir.name),
        "counts": {
            "rows_total": len(worklist),
            "work_batches": len(batch_ids),
            "batch_size_target": int(args.batch_size),
        },
        "consensus_rules": {
            "point_tolerance": float(args.consensus_point_tol),
            "ci_tolerance": float(args.consensus_ci_tol),
            "zero_abs_tolerance": float(args.zero_abs_tolerance),
        },
        "completion_gates": {
            "require_dual_annotation_all_rows": True,
            "require_included_non_null": True,
            "require_point_and_type_when_included": True,
            "require_source_text_when_included": True,
            "require_manual_adjudication_for_unresolved_consensus": True,
            "require_exact_rows_in_final_adjudicated_jsonl": len(worklist),
        },
        "paths": {
            "benchmark_dir": str(benchmark_dir).replace("\\", "/"),
            "worklist_jsonl": str(worklist_jsonl).replace("\\", "/"),
            "worklist_csv": str(worklist_csv).replace("\\", "/"),
            "batches_dir": str(batches_dir).replace("\\", "/"),
            "system_results_jsonl": str(args.system_results_jsonl).replace("\\", "/"),
            "eval_output_json": str(eval_json).replace("\\", "/"),
            "eval_output_md": str(eval_md).replace("\\", "/"),
            "protocol_md": str(protocol_md).replace("\\", "/"),
            "summary_json": str(summary_json).replace("\\", "/"),
        },
        "freeze_command": freeze_command,
        "preview_command": preview_command,
        "input_files": input_files,
    }
    _write_json(protocol_json, protocol_payload)
    _write_protocol_md(protocol_md, protocol_payload)

    summary_payload = {
        "generated_at_utc": _utc_now(),
        "benchmark_version": protocol_payload["benchmark_version"],
        "counts": {
            "rows_total": len(worklist),
            "batches_total": len(batch_ids),
            "status_counts": _counts_by(worklist, "status_snapshot"),
            "priority_tier_counts": _counts_by(worklist, "priority_tier"),
            "recommended_route_counts": _counts_by(worklist, "recommended_route"),
            "batch_status_counts": _batch_counts(worklist),
        },
        "paths": {
            "worklist_jsonl": str(worklist_jsonl).replace("\\", "/"),
            "worklist_csv": str(worklist_csv).replace("\\", "/"),
            "protocol_json": str(protocol_json).replace("\\", "/"),
            "protocol_md": str(protocol_md).replace("\\", "/"),
        },
    }
    _write_json(summary_json, summary_payload)

    print(f"Wrote: {worklist_jsonl}")
    print(f"Wrote: {worklist_csv}")
    print(f"Wrote: {batches_dir}")
    print(f"Wrote: {protocol_json}")
    print(f"Wrote: {protocol_md}")
    print(f"Wrote: {summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
