#!/usr/bin/env python3
"""Build unresolved-only adjudication packet from dual annotator files."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


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


def _normalize_annotation(row: Optional[Dict]) -> Optional[Dict]:
    if not isinstance(row, dict):
        return None
    block = None
    for key in ("annotation", "gold", "adjudicated_gold"):
        value = row.get(key)
        if isinstance(value, dict):
            block = value
            break
    block = block or {}

    included = _to_bool(block.get("included"))
    point = _to_float(block.get("point_estimate"))
    ci_low = _to_float(block.get("ci_lower"))
    ci_high = _to_float(block.get("ci_upper"))
    effect_type = _normalize_effect_type(block.get("effect_type") or block.get("type"))
    return {
        "included": included,
        "effect_type": effect_type,
        "point_estimate": point,
        "ci_lower": ci_low,
        "ci_upper": ci_high,
        "p_value": _to_float(block.get("p_value")),
        "page_number": _to_int(block.get("page_number")),
        "source_text": str(block.get("source_text") or ""),
        "notes": str(block.get("notes") or ""),
    }


def _rel_err(extracted: float, expected: float, zero_abs_tolerance: float) -> float:
    if abs(expected) < 1e-12:
        return abs(extracted - expected) / max(zero_abs_tolerance, 1e-12)
    return abs(extracted - expected) / abs(expected)


def _consensus_or_reasons(
    a: Optional[Dict],
    b: Optional[Dict],
    *,
    point_tol: float,
    ci_tol: float,
    zero_abs_tolerance: float,
) -> Tuple[Optional[Dict], List[str], Dict[str, Optional[bool]]]:
    reasons: List[str] = []
    agreement = {
        "included_match": None,
        "type_match": None,
        "point_within_10pct": None,
        "ci_within_10pct": None,
    }

    if a is None:
        reasons.append("missing_annotator_a_row")
    if b is None:
        reasons.append("missing_annotator_b_row")
    if reasons:
        return None, reasons, agreement

    a_inc = a.get("included")
    b_inc = b.get("included")
    if a_inc is not None and b_inc is not None:
        agreement["included_match"] = bool(a_inc == b_inc)

    if a_inc is False and b_inc is False:
        consensus = {
            "included": False,
            "effect_type": None,
            "point_estimate": None,
            "ci_lower": None,
            "ci_upper": None,
            "p_value": None,
            "source_text": "",
            "page_number": None,
            "notes": "consensus_excluded",
        }
        return consensus, [], agreement

    if a_inc is None or b_inc is None:
        reasons.append("missing_included_label")
        return None, reasons, agreement

    if bool(a_inc) != bool(b_inc):
        reasons.append("included_disagreement")
        return None, reasons, agreement

    # Both included
    a_point = _to_float(a.get("point_estimate"))
    b_point = _to_float(b.get("point_estimate"))
    if a_point is None or b_point is None:
        reasons.append("missing_point_estimate")
        return None, reasons, agreement

    point_rel = _rel_err(a_point, b_point, zero_abs_tolerance)
    agreement["point_within_10pct"] = bool(point_rel <= 0.10)
    if point_rel > point_tol:
        reasons.append("point_disagreement")

    a_type = _normalize_effect_type(a.get("effect_type"))
    b_type = _normalize_effect_type(b.get("effect_type"))
    if a_type is not None and b_type is not None:
        agreement["type_match"] = bool(a_type == b_type)
    if a_type and b_type and a_type != b_type:
        reasons.append("effect_type_mismatch")

    a_ci_low = _to_float(a.get("ci_lower"))
    a_ci_high = _to_float(a.get("ci_upper"))
    b_ci_low = _to_float(b.get("ci_lower"))
    b_ci_high = _to_float(b.get("ci_upper"))
    a_has_ci = a_ci_low is not None and a_ci_high is not None
    b_has_ci = b_ci_low is not None and b_ci_high is not None

    if a_has_ci != b_has_ci:
        reasons.append("ci_presence_mismatch")
    elif a_has_ci and b_has_ci:
        ci_rel = max(
            _rel_err(a_ci_low, b_ci_low, zero_abs_tolerance),
            _rel_err(a_ci_high, b_ci_high, zero_abs_tolerance),
        )
        agreement["ci_within_10pct"] = bool(ci_rel <= 0.10)
        if ci_rel > ci_tol:
            reasons.append("ci_disagreement")

    if reasons:
        return None, reasons, agreement

    consensus = {
        "included": True,
        "effect_type": a_type or b_type,
        "point_estimate": (a_point + b_point) / 2.0,
        "ci_lower": (a_ci_low + b_ci_low) / 2.0 if a_has_ci and b_has_ci else None,
        "ci_upper": (a_ci_high + b_ci_high) / 2.0 if a_has_ci and b_has_ci else None,
        "p_value": None,
        "source_text": str(a.get("source_text") or b.get("source_text") or ""),
        "page_number": a.get("page_number") if a.get("page_number") is not None else b.get("page_number"),
        "notes": "consensus_from_dual_annotators",
    }
    return consensus, [], agreement


def _adjudication_route(reasons: Sequence[str], model_seed: Optional[Dict]) -> str:
    reason_set = set(reasons)
    if "missing_annotator_a_row" in reason_set or "missing_annotator_b_row" in reason_set:
        return "complete_missing_annotator_row"
    if "missing_included_label" in reason_set:
        return "complete_included_label"
    if "missing_point_estimate" in reason_set:
        return "fill_point_estimate_if_included"
    confidence = _to_float((model_seed or {}).get("model_snapshot_best", {}).get("calibrated_confidence"))
    if confidence is not None and confidence >= 0.9:
        return "manual_adjudication_with_model_seed_reference"
    return "manual_adjudication_required"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=Path("data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1"),
    )
    parser.add_argument("--annotator-a-jsonl", type=Path, default=None)
    parser.add_argument("--annotator-b-jsonl", type=Path, default=None)
    parser.add_argument("--model-seed-jsonl", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--consensus-point-tol", type=float, default=0.10)
    parser.add_argument("--consensus-ci-tol", type=float, default=0.15)
    parser.add_argument("--zero-abs-tolerance", type=float, default=0.02)
    args = parser.parse_args()

    benchmark_dir = args.benchmark_dir
    if not benchmark_dir.exists():
        raise FileNotFoundError(f"--benchmark-dir not found: {benchmark_dir}")

    annotator_a_path = args.annotator_a_jsonl or benchmark_dir / "blinded_template_annotator_a.jsonl"
    annotator_b_path = args.annotator_b_jsonl or benchmark_dir / "blinded_template_annotator_b.jsonl"
    model_seed_path = args.model_seed_jsonl or benchmark_dir / "model_seed_adjudicator_only.jsonl"
    cohort_path = benchmark_dir / "benchmark_cohort.jsonl"

    for path in (annotator_a_path, annotator_b_path, model_seed_path, cohort_path):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    out_dir = args.output_dir or (benchmark_dir / "adjudication_unresolved")
    unresolved_path = out_dir / "unresolved_packet.jsonl"
    consensus_path = out_dir / "consensus_auto.jsonl"
    summary_path = out_dir / "summary.json"
    ids_path = out_dir / "unresolved_benchmark_ids.txt"

    cohort_rows = _load_jsonl(cohort_path)
    a_rows = _load_jsonl(annotator_a_path)
    b_rows = _load_jsonl(annotator_b_path)
    model_seed_rows = _load_jsonl(model_seed_path)

    cohort_by_id = {str(row.get("benchmark_id") or ""): row for row in cohort_rows if row.get("benchmark_id")}
    a_by_id = {str(row.get("benchmark_id") or ""): row for row in a_rows if row.get("benchmark_id")}
    b_by_id = {str(row.get("benchmark_id") or ""): row for row in b_rows if row.get("benchmark_id")}
    model_by_id = {str(row.get("benchmark_id") or ""): row for row in model_seed_rows if row.get("benchmark_id")}

    benchmark_ids = sorted(set(cohort_by_id) | set(a_by_id) | set(b_by_id))

    unresolved_rows: List[Dict] = []
    consensus_rows: List[Dict] = []
    reason_counts: Counter = Counter()
    included_match_flags: List[bool] = []
    type_match_flags: List[bool] = []
    point10_flags: List[bool] = []
    ci10_flags: List[bool] = []

    for bid in benchmark_ids:
        base = cohort_by_id.get(bid) or {}
        a_norm = _normalize_annotation(a_by_id.get(bid))
        b_norm = _normalize_annotation(b_by_id.get(bid))
        model_seed = model_by_id.get(bid)

        consensus, reasons, agreement = _consensus_or_reasons(
            a_norm,
            b_norm,
            point_tol=float(args.consensus_point_tol),
            ci_tol=float(args.consensus_ci_tol),
            zero_abs_tolerance=float(args.zero_abs_tolerance),
        )
        if agreement["included_match"] is not None:
            included_match_flags.append(bool(agreement["included_match"]))
        if agreement["type_match"] is not None:
            type_match_flags.append(bool(agreement["type_match"]))
        if agreement["point_within_10pct"] is not None:
            point10_flags.append(bool(agreement["point_within_10pct"]))
        if agreement["ci_within_10pct"] is not None:
            ci10_flags.append(bool(agreement["ci_within_10pct"]))

        if consensus is not None:
            consensus_rows.append(
                {
                    "benchmark_id": bid,
                    "study_id": base.get("study_id"),
                    "pdf_relpath": base.get("pdf_relpath"),
                    "pmcid": base.get("pmcid"),
                    "pmid": base.get("pmid"),
                    "gold": consensus,
                    "consensus_notes": "auto_consensus",
                }
            )
            continue

        for reason in reasons:
            reason_counts[reason] += 1
        unresolved_rows.append(
            {
                "benchmark_id": bid,
                "study_id": base.get("study_id"),
                "pdf_relpath": base.get("pdf_relpath"),
                "pdf_abs_path": base.get("pdf_abs_path"),
                "pmcid": base.get("pmcid"),
                "pmid": base.get("pmid"),
                "status_snapshot": base.get("status_snapshot"),
                "linked_meta_matches_total": base.get("linked_meta_matches_total"),
                "linked_meta_pmids": base.get("linked_meta_pmids"),
                "disagreement_reasons": list(reasons),
                "agreement_flags": agreement,
                "annotator_a": a_norm,
                "annotator_b": b_norm,
                "model_seed": model_seed.get("model_snapshot_best") if isinstance(model_seed, dict) else None,
                "recommended_adjudication_route": _adjudication_route(reasons, model_seed),
            }
        )

    unresolved_rows.sort(key=lambda row: str(row.get("benchmark_id") or ""))
    consensus_rows.sort(key=lambda row: str(row.get("benchmark_id") or ""))

    _write_jsonl(unresolved_path, unresolved_rows)
    _write_jsonl(consensus_path, consensus_rows)
    ids_path.parent.mkdir(parents=True, exist_ok=True)
    ids_path.write_text(
        "\n".join(str(row.get("benchmark_id") or "") for row in unresolved_rows) + ("\n" if unresolved_rows else ""),
        encoding="utf-8",
    )

    summary = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "benchmark_dir": str(benchmark_dir).replace("\\", "/"),
            "annotator_a_jsonl": str(annotator_a_path).replace("\\", "/"),
            "annotator_b_jsonl": str(annotator_b_path).replace("\\", "/"),
            "model_seed_jsonl": str(model_seed_path).replace("\\", "/"),
            "consensus_point_tol": float(args.consensus_point_tol),
            "consensus_ci_tol": float(args.consensus_ci_tol),
            "zero_abs_tolerance": float(args.zero_abs_tolerance),
        },
        "counts": {
            "benchmark_rows_total": len(benchmark_ids),
            "consensus_auto_rows": len(consensus_rows),
            "unresolved_rows": len(unresolved_rows),
            "reason_counts": dict(sorted(reason_counts.items())),
        },
        "agreement": {
            "included_match_rate": (sum(included_match_flags) / len(included_match_flags)) if included_match_flags else None,
            "type_match_rate": (sum(type_match_flags) / len(type_match_flags)) if type_match_flags else None,
            "point_within_10pct_rate": (sum(point10_flags) / len(point10_flags)) if point10_flags else None,
            "ci_within_10pct_rate": (sum(ci10_flags) / len(ci10_flags)) if ci10_flags else None,
        },
        "paths": {
            "unresolved_packet_jsonl": str(unresolved_path).replace("\\", "/"),
            "consensus_auto_jsonl": str(consensus_path).replace("\\", "/"),
            "unresolved_ids_txt": str(ids_path).replace("\\", "/"),
            "summary_json": str(summary_path).replace("\\", "/"),
        },
    }
    _write_json(summary_path, summary)

    print(f"Wrote: {unresolved_path}")
    print(f"Wrote: {consensus_path}")
    print(f"Wrote: {ids_path}")
    print(f"Wrote: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
