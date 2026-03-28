#!/usr/bin/env python3
"""Prefill adjudication template from model-seed outputs with review tiers."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def _to_bool(value: object) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"", "none", "null", "na", "n/a"}:
        return None
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def _normalize_effect_type(value: object) -> Optional[str]:
    text = str(value or "").strip().upper()
    if not text:
        return None
    alias = {
        "RISK RATIO": "RR",
        "ODDS RATIO": "OR",
        "HAZARD RATIO": "HR",
        "MEAN DIFFERENCE": "MD",
        "STANDARDIZED MEAN DIFFERENCE": "SMD",
    }
    return alias.get(text, text)


def _review_tier(
    *,
    included: bool,
    status_snapshot: str,
    confidence: Optional[float],
    has_ci: bool,
    has_core_fields: bool,
) -> str:
    if included:
        if confidence is not None and confidence >= 0.95 and has_ci:
            return "tier_1_fast_verify_included"
        if confidence is not None and confidence >= 0.80:
            return "tier_2_verify_included"
        return "tier_3_full_review_included"
    if status_snapshot == "extracted" and has_core_fields:
        return "tier_2_verify_extracted_rejected"
    if status_snapshot == "timeout":
        return "tier_3_full_review_timeout"
    return "tier_4_negative_check"


def _review_required(tier: str) -> bool:
    return tier != "tier_4_negative_check"


def _write_review_csv(path: Path, rows: Sequence[Dict]) -> None:
    fieldnames = [
        "benchmark_id",
        "study_id",
        "pmid",
        "pmcid",
        "pdf_relpath",
        "status_snapshot",
        "suggested_included",
        "review_tier",
        "review_required",
        "model_confidence",
        "model_effect_type",
        "model_point_estimate",
        "model_ci_lower",
        "model_ci_upper",
        "reason",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=Path("data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1"),
    )
    parser.add_argument("--adjudication-jsonl", type=Path, default=None)
    parser.add_argument("--model-seed-jsonl", type=Path, default=None)
    parser.add_argument("--output-jsonl", type=Path, default=None)
    parser.add_argument("--review-jsonl", type=Path, default=None)
    parser.add_argument("--review-csv", type=Path, default=None)
    parser.add_argument("--summary-json", type=Path, default=None)
    parser.add_argument("--min-include-confidence", type=float, default=0.80)
    parser.add_argument("--min-source-len", type=int, default=20)
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Overwrite rows that already have non-null gold.included.",
    )
    args = parser.parse_args()

    if args.min_include_confidence < 0 or args.min_include_confidence > 1:
        raise ValueError("--min-include-confidence must be in [0,1]")
    if args.min_source_len < 0:
        raise ValueError("--min-source-len must be >= 0")

    benchmark_dir = args.benchmark_dir
    if not benchmark_dir.exists():
        raise FileNotFoundError(f"--benchmark-dir not found: {benchmark_dir}")

    adjudication_path = args.adjudication_jsonl or (benchmark_dir / "adjudication_template.jsonl")
    model_seed_path = args.model_seed_jsonl or (benchmark_dir / "model_seed_adjudicator_only.jsonl")
    output_path = args.output_jsonl or adjudication_path
    review_jsonl_path = args.review_jsonl or (benchmark_dir / "adjudication_prefill_review_queue.jsonl")
    review_csv_path = args.review_csv or (benchmark_dir / "adjudication_prefill_review_queue.csv")
    summary_path = args.summary_json or (benchmark_dir / "adjudication_prefill_summary.json")

    for path in (adjudication_path, model_seed_path):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    adjudication_rows = _load_jsonl(adjudication_path)
    model_seed_rows = _load_jsonl(model_seed_path)
    model_by_id = {str(row.get("benchmark_id") or ""): row for row in model_seed_rows if row.get("benchmark_id")}

    backup_path = None
    if output_path.resolve() == adjudication_path.resolve():
        backup_path = adjudication_path.with_name(f"{adjudication_path.stem}.prefill_backup_{_utc_stamp()}.jsonl")
        shutil.copyfile(adjudication_path, backup_path)

    updated_rows: List[Dict] = []
    review_rows: List[Dict] = []

    count_preserved = 0
    count_prefilled = 0
    included_true = 0
    included_false = 0
    missing_model = 0
    reason_counts: Dict[str, int] = {}
    tier_counts: Dict[str, int] = {}

    for row in adjudication_rows:
        bid = str(row.get("benchmark_id") or "")
        gold = row.get("gold") if isinstance(row.get("gold"), dict) else {}
        existing_included = _to_bool(gold.get("included"))

        model_row = model_by_id.get(bid) or {}
        status_snapshot = str(model_row.get("status_snapshot") or "").strip().lower()
        best = model_row.get("model_snapshot_best") if isinstance(model_row.get("model_snapshot_best"), dict) else {}
        model_type = _normalize_effect_type(best.get("type"))
        model_point = _to_float(best.get("effect_size"))
        model_ci_low = _to_float(best.get("ci_lower"))
        model_ci_high = _to_float(best.get("ci_upper"))
        model_p = _to_float(best.get("p_value"))
        model_conf = _to_float(best.get("calibrated_confidence"))
        model_source = str(best.get("source_text") or "").strip()
        model_page = _to_int(best.get("page_number"))
        has_ci = model_ci_low is not None and model_ci_high is not None
        has_core = model_type is not None and model_point is not None
        has_source = len(model_source) >= int(args.min_source_len)

        preserve = (existing_included is not None) and (not args.overwrite_existing)
        if preserve:
            count_preserved += 1
            suggested_included = bool(existing_included)
            reason = "preserved_existing_gold"
            out_row = dict(row)
            out_gold = out_row.get("gold") if isinstance(out_row.get("gold"), dict) else {}
            out_source = str(out_gold.get("source_text") or "").strip()
            if suggested_included and not out_source:
                out_gold["source_text"] = model_source
            out_row["gold"] = out_gold
        else:
            count_prefilled += 1
            if not model_row:
                missing_model += 1

            include_candidate = (
                status_snapshot == "extracted"
                and has_core
                and model_conf is not None
                and model_conf >= float(args.min_include_confidence)
                and has_source
            )

            if include_candidate:
                suggested_included = True
                reason = "model_extracted_above_threshold"
                out_gold = {
                    "included": True,
                    "effect_type": model_type,
                    "point_estimate": model_point,
                    "ci_lower": model_ci_low,
                    "ci_upper": model_ci_high,
                    "p_value": model_p,
                    "source_text": model_source,
                    "page_number": model_page,
                    "notes": (
                        "prefill_from_model_seed"
                        f"; confidence={model_conf:.3f}" if model_conf is not None else "prefill_from_model_seed"
                    ),
                }
            else:
                suggested_included = False
                if status_snapshot == "extracted" and has_core:
                    if model_conf is None:
                        reason = "extracted_missing_confidence"
                    elif model_conf < float(args.min_include_confidence):
                        reason = "extracted_below_confidence_threshold"
                    elif not has_source:
                        reason = "extracted_missing_source_text"
                    else:
                        reason = "extracted_rejected_other"
                elif status_snapshot == "timeout":
                    reason = "timeout_no_valid_extraction"
                elif status_snapshot == "no_extraction":
                    reason = "no_extraction"
                else:
                    reason = "not_extracted"
                out_gold = {
                    "included": False,
                    "effect_type": None,
                    "point_estimate": None,
                    "ci_lower": None,
                    "ci_upper": None,
                    "p_value": None,
                    "source_text": "",
                    "page_number": None,
                    "notes": f"prefill_from_model_seed; reason={reason}",
                }

            out_row = dict(row)
            out_row["gold"] = out_gold
            prev_notes = str(out_row.get("adjudication_notes") or "").strip()
            prefix = "prefill_autofill_v1"
            if prev_notes:
                out_row["adjudication_notes"] = f"{prefix}; {prev_notes}"
            else:
                out_row["adjudication_notes"] = prefix

        if suggested_included:
            included_true += 1
        else:
            included_false += 1

        reason_counts[reason] = reason_counts.get(reason, 0) + 1

        tier = _review_tier(
            included=suggested_included,
            status_snapshot=status_snapshot,
            confidence=model_conf,
            has_ci=has_ci,
            has_core_fields=has_core,
        )
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        requires_review = _review_required(tier)

        review_rows.append(
            {
                "benchmark_id": bid,
                "study_id": row.get("study_id"),
                "pmid": row.get("pmid"),
                "pmcid": row.get("pmcid"),
                "pdf_relpath": row.get("pdf_relpath"),
                "status_snapshot": status_snapshot,
                "suggested_included": suggested_included,
                "review_tier": tier,
                "review_required": requires_review,
                "model_confidence": model_conf,
                "model_effect_type": model_type,
                "model_point_estimate": model_point,
                "model_ci_lower": model_ci_low,
                "model_ci_upper": model_ci_high,
                "reason": reason,
            }
        )
        updated_rows.append(out_row)

    review_rows.sort(
        key=lambda r: (
            0 if bool(r.get("review_required")) else 1,
            str(r.get("review_tier") or ""),
            -float(r.get("model_confidence") if r.get("model_confidence") is not None else -1.0),
            str(r.get("benchmark_id") or ""),
        )
    )

    _write_jsonl(output_path, updated_rows)
    _write_jsonl(review_jsonl_path, review_rows)
    _write_review_csv(review_csv_path, review_rows)

    summary = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "benchmark_dir": str(benchmark_dir).replace("\\", "/"),
            "adjudication_jsonl": str(adjudication_path).replace("\\", "/"),
            "model_seed_jsonl": str(model_seed_path).replace("\\", "/"),
            "output_jsonl": str(output_path).replace("\\", "/"),
            "min_include_confidence": float(args.min_include_confidence),
            "min_source_len": int(args.min_source_len),
            "overwrite_existing": bool(args.overwrite_existing),
        },
        "counts": {
            "rows_total": len(updated_rows),
            "rows_preserved_existing": count_preserved,
            "rows_prefilled": count_prefilled,
            "rows_suggested_included_true": included_true,
            "rows_suggested_included_false": included_false,
            "rows_missing_model_seed": missing_model,
            "rows_review_required": sum(1 for r in review_rows if bool(r.get("review_required"))),
            "review_tier_counts": dict(sorted(tier_counts.items())),
            "prefill_reason_counts": dict(sorted(reason_counts.items())),
        },
        "paths": {
            "backup_jsonl": str(backup_path).replace("\\", "/") if backup_path is not None else None,
            "prefilled_adjudication_jsonl": str(output_path).replace("\\", "/"),
            "review_queue_jsonl": str(review_jsonl_path).replace("\\", "/"),
            "review_queue_csv": str(review_csv_path).replace("\\", "/"),
            "summary_json": str(summary_path).replace("\\", "/"),
        },
    }
    _write_json(summary_path, summary)

    print(f"Wrote: {output_path}")
    print(f"Wrote: {review_jsonl_path}")
    print(f"Wrote: {review_csv_path}")
    print(f"Wrote: {summary_path}")
    if backup_path is not None:
        print(f"Wrote: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
