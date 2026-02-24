#!/usr/bin/env python3
"""Evaluate cardiology linked benchmark with adjudicated or dual-annotator labels."""

from __future__ import annotations

import argparse
import json
import math
import random
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


def _load_latest_rows(path: Path) -> Dict[str, Dict]:
    latest: Dict[str, Dict] = {}
    for row in _load_jsonl(path):
        rel = str(row.get("pdf_relpath") or "").replace("\\", "/")
        if rel:
            latest[rel] = row
    return latest


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


def _rel_err(extracted: float, expected: float, zero_abs_tolerance: float) -> float:
    if abs(expected) < 1e-12:
        return abs(extracted - expected) / max(zero_abs_tolerance, 1e-12)
    return abs(extracted - expected) / abs(expected)


def _bootstrap_rate(
    values: Sequence[bool],
    *,
    n_bootstrap: int,
    rng_seed: int,
) -> Optional[Dict[str, float]]:
    if not values:
        return None
    n = len(values)
    ints = [1 if v else 0 for v in values]
    rng = random.Random(rng_seed)
    fractions: List[float] = []
    for _ in range(n_bootstrap):
        hits = 0
        for _ in range(n):
            hits += ints[rng.randrange(n)]
        fractions.append(hits / n)
    fractions.sort()
    low_idx = int(0.025 * (n_bootstrap - 1))
    high_idx = int(0.975 * (n_bootstrap - 1))
    return {
        "point": sum(ints) / n,
        "ci_low_95": fractions[low_idx],
        "ci_high_95": fractions[high_idx],
    }


def _ece(values: Sequence[Tuple[float, int]], n_bins: int) -> Optional[float]:
    if not values:
        return None
    bins: List[List[Tuple[float, int]]] = [[] for _ in range(n_bins)]
    for prob, label in values:
        idx = min(n_bins - 1, max(0, int(math.floor(prob * n_bins))))
        bins[idx].append((prob, label))

    total = len(values)
    score = 0.0
    for bucket in bins:
        if not bucket:
            continue
        mean_prob = sum(item[0] for item in bucket) / len(bucket)
        mean_acc = sum(item[1] for item in bucket) / len(bucket)
        score += (len(bucket) / total) * abs(mean_prob - mean_acc)
    return score


def _normalize_annotation(row: Dict) -> Dict:
    block = None
    for key in ("gold", "adjudicated_gold", "annotation"):
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

    if included is None:
        included = point is not None
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


def _consensus_from_pair(
    a: Dict,
    b: Dict,
    *,
    point_tol: float,
    ci_tol: float,
    zero_abs_tolerance: float,
) -> Tuple[Optional[Dict], Dict]:
    a_inc = a.get("included")
    b_inc = b.get("included")
    agreement = {
        "included_match": (a_inc == b_inc) if (a_inc is not None and b_inc is not None) else None,
        "type_match": None,
        "point_within_5pct": None,
        "point_within_10pct": None,
        "ci_within_10pct": None,
    }

    if a_inc is False and b_inc is False:
        return (
            {
                "included": False,
                "effect_type": None,
                "point_estimate": None,
                "ci_lower": None,
                "ci_upper": None,
                "p_value": None,
                "source_text": "",
                "page_number": None,
                "notes": "consensus_excluded",
            },
            agreement,
        )

    if a_inc is not True or b_inc is not True:
        return None, agreement

    a_point = _to_float(a.get("point_estimate"))
    b_point = _to_float(b.get("point_estimate"))
    if a_point is None or b_point is None:
        return None, agreement
    point_rel = _rel_err(a_point, b_point, zero_abs_tolerance)
    agreement["point_within_5pct"] = point_rel <= 0.05
    agreement["point_within_10pct"] = point_rel <= 0.10
    if point_rel > point_tol:
        return None, agreement

    a_type = _normalize_effect_type(a.get("effect_type"))
    b_type = _normalize_effect_type(b.get("effect_type"))
    type_match = (a_type == b_type) if (a_type and b_type) else True
    agreement["type_match"] = type_match
    if not type_match:
        return None, agreement

    a_ci_low = _to_float(a.get("ci_lower"))
    a_ci_high = _to_float(a.get("ci_upper"))
    b_ci_low = _to_float(b.get("ci_lower"))
    b_ci_high = _to_float(b.get("ci_upper"))

    if (a_ci_low is None) != (b_ci_low is None) or (a_ci_high is None) != (b_ci_high is None):
        return None, agreement

    if a_ci_low is not None and a_ci_high is not None and b_ci_low is not None and b_ci_high is not None:
        ci_low_rel = _rel_err(a_ci_low, b_ci_low, zero_abs_tolerance)
        ci_high_rel = _rel_err(a_ci_high, b_ci_high, zero_abs_tolerance)
        ci_rel = max(ci_low_rel, ci_high_rel)
        agreement["ci_within_10pct"] = ci_rel <= 0.10
        if ci_rel > ci_tol:
            return None, agreement
        ci_low = (a_ci_low + b_ci_low) / 2.0
        ci_high = (a_ci_high + b_ci_high) / 2.0
    else:
        ci_low = None
        ci_high = None

    consensus = {
        "included": True,
        "effect_type": a_type or b_type,
        "point_estimate": (a_point + b_point) / 2.0,
        "ci_lower": ci_low,
        "ci_upper": ci_high,
        "p_value": None,
        "source_text": str(a.get("source_text") or b.get("source_text") or ""),
        "page_number": a.get("page_number") if a.get("page_number") is not None else b.get("page_number"),
        "notes": "consensus_from_dual_annotators",
    }
    return consensus, agreement


def _load_gold(
    *,
    benchmark_rows: Sequence[Dict],
    adjudicated_jsonl: Optional[Path],
    annotator_a_jsonl: Optional[Path],
    annotator_b_jsonl: Optional[Path],
    point_tol: float,
    ci_tol: float,
    zero_abs_tolerance: float,
) -> Tuple[Dict[str, Dict], Dict]:
    benchmark_ids = {str(row.get("benchmark_id") or "") for row in benchmark_rows}

    if adjudicated_jsonl is not None:
        rows = _load_jsonl(adjudicated_jsonl)
        gold_map: Dict[str, Dict] = {}
        for row in rows:
            bid = str(row.get("benchmark_id") or "")
            if not bid or bid not in benchmark_ids:
                continue
            gold_map[bid] = _normalize_annotation(row)
        return gold_map, {"mode": "adjudicated", "rows_loaded": len(gold_map)}

    if annotator_a_jsonl is None or annotator_b_jsonl is None:
        return {}, {"mode": "missing_labels", "rows_loaded": 0}

    a_rows = {str(row.get("benchmark_id") or ""): _normalize_annotation(row) for row in _load_jsonl(annotator_a_jsonl)}
    b_rows = {str(row.get("benchmark_id") or ""): _normalize_annotation(row) for row in _load_jsonl(annotator_b_jsonl)}

    gold_map: Dict[str, Dict] = {}
    overlap = 0
    included_match: List[bool] = []
    type_match: List[bool] = []
    point_5: List[bool] = []
    point_10: List[bool] = []
    ci_10: List[bool] = []
    unresolved_ids: List[str] = []

    for bid in sorted(benchmark_ids):
        a = a_rows.get(bid)
        b = b_rows.get(bid)
        if a is None or b is None:
            continue
        overlap += 1
        consensus, agreement = _consensus_from_pair(
            a,
            b,
            point_tol=point_tol,
            ci_tol=ci_tol,
            zero_abs_tolerance=zero_abs_tolerance,
        )
        if agreement["included_match"] is not None:
            included_match.append(bool(agreement["included_match"]))
        if agreement["type_match"] is not None:
            type_match.append(bool(agreement["type_match"]))
        if agreement["point_within_5pct"] is not None:
            point_5.append(bool(agreement["point_within_5pct"]))
        if agreement["point_within_10pct"] is not None:
            point_10.append(bool(agreement["point_within_10pct"]))
        if agreement["ci_within_10pct"] is not None:
            ci_10.append(bool(agreement["ci_within_10pct"]))

        if consensus is None:
            unresolved_ids.append(bid)
            continue
        gold_map[bid] = consensus

    pair_summary = {
        "mode": "dual_annotator_consensus",
        "rows_overlap": overlap,
        "consensus_rows": len(gold_map),
        "unresolved_rows": len(unresolved_ids),
        "included_match_rate": (sum(included_match) / len(included_match)) if included_match else None,
        "type_match_rate": (sum(type_match) / len(type_match)) if type_match else None,
        "point_within_5pct_rate": (sum(point_5) / len(point_5)) if point_5 else None,
        "point_within_10pct_rate": (sum(point_10) / len(point_10)) if point_10 else None,
        "ci_within_10pct_rate": (sum(ci_10) / len(ci_10)) if ci_10 else None,
        "unresolved_benchmark_ids_preview": unresolved_ids[:50],
    }
    return gold_map, pair_summary


def _fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{100.0 * value:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-cohort-jsonl", type=Path, required=True)
    parser.add_argument("--system-results-jsonl", type=Path, required=True)
    parser.add_argument("--adjudicated-jsonl", type=Path, default=None)
    parser.add_argument("--annotator-a-jsonl", type=Path, default=None)
    parser.add_argument("--annotator-b-jsonl", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--output-consensus-jsonl", type=Path, default=None)
    parser.add_argument("--consensus-point-tol", type=float, default=0.10)
    parser.add_argument("--consensus-ci-tol", type=float, default=0.15)
    parser.add_argument("--zero-abs-tolerance", type=float, default=0.02)
    parser.add_argument("--n-bootstrap", type=int, default=10000)
    parser.add_argument("--rng-seed", type=int, default=20260224)
    parser.add_argument("--ece-bins", type=int, default=10)
    args = parser.parse_args()

    if not args.benchmark_cohort_jsonl.exists():
        raise FileNotFoundError(f"Benchmark cohort JSONL not found: {args.benchmark_cohort_jsonl}")
    if not args.system_results_jsonl.exists():
        raise FileNotFoundError(f"System results JSONL not found: {args.system_results_jsonl}")
    if args.adjudicated_jsonl is not None and not args.adjudicated_jsonl.exists():
        raise FileNotFoundError(f"Adjudicated JSONL not found: {args.adjudicated_jsonl}")
    if args.annotator_a_jsonl is not None and not args.annotator_a_jsonl.exists():
        raise FileNotFoundError(f"Annotator A JSONL not found: {args.annotator_a_jsonl}")
    if args.annotator_b_jsonl is not None and not args.annotator_b_jsonl.exists():
        raise FileNotFoundError(f"Annotator B JSONL not found: {args.annotator_b_jsonl}")
    if args.n_bootstrap <= 0:
        raise ValueError("--n-bootstrap must be > 0")
    if args.ece_bins <= 1:
        raise ValueError("--ece-bins must be > 1")

    benchmark_rows = _load_jsonl(args.benchmark_cohort_jsonl)
    bench_by_id = {str(row.get("benchmark_id") or ""): row for row in benchmark_rows if row.get("benchmark_id")}
    system_by_rel = _load_latest_rows(args.system_results_jsonl)

    gold_map, label_summary = _load_gold(
        benchmark_rows=benchmark_rows,
        adjudicated_jsonl=args.adjudicated_jsonl,
        annotator_a_jsonl=args.annotator_a_jsonl,
        annotator_b_jsonl=args.annotator_b_jsonl,
        point_tol=float(args.consensus_point_tol),
        ci_tol=float(args.consensus_ci_tol),
        zero_abs_tolerance=float(args.zero_abs_tolerance),
    )

    if args.output_consensus_jsonl is not None and gold_map:
        out_rows: List[Dict] = []
        for bid, gold in sorted(gold_map.items(), key=lambda item: item[0]):
            base = bench_by_id.get(bid) or {}
            out_rows.append(
                {
                    "benchmark_id": bid,
                    "study_id": base.get("study_id"),
                    "pdf_relpath": base.get("pdf_relpath"),
                    "pmcid": base.get("pmcid"),
                    "pmid": base.get("pmid"),
                    "gold": gold,
                }
            )
        args.output_consensus_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with args.output_consensus_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
            for row in out_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    per_row: List[Dict] = []
    point_1: List[bool] = []
    point_2: List[bool] = []
    point_5: List[bool] = []
    point_10: List[bool] = []
    ci_10: List[bool] = []
    type_match_flags: List[bool] = []
    calibration_pairs: List[Tuple[float, int]] = []

    gold_resolved = 0
    gold_included = 0
    gold_excluded = 0
    extracted_on_gold_included = 0
    extracted_on_gold_excluded = 0
    page_present_count = 0
    source_present_count = 0

    for bid in sorted(bench_by_id):
        bench = bench_by_id[bid]
        gold = gold_map.get(bid)
        if gold is None:
            continue
        gold_resolved += 1
        included = bool(gold.get("included"))
        if included:
            gold_included += 1
        else:
            gold_excluded += 1

        rel = str(bench.get("pdf_relpath") or "").replace("\\", "/")
        system_row = system_by_rel.get(rel) or {}
        status = str(system_row.get("status") or "")
        best = system_row.get("best_match") if isinstance(system_row.get("best_match"), dict) else {}
        extracted = status == "extracted" and _to_float(best.get("effect_size")) is not None

        row_payload = {
            "benchmark_id": bid,
            "study_id": bench.get("study_id"),
            "pdf_relpath": rel,
            "status": status,
            "gold_included": included,
            "extracted": extracted,
            "gold_effect_type": _normalize_effect_type(gold.get("effect_type")),
            "system_effect_type": _normalize_effect_type(best.get("type")),
            "gold_point": _to_float(gold.get("point_estimate")),
            "system_point": _to_float(best.get("effect_size")),
            "gold_ci_low": _to_float(gold.get("ci_lower")),
            "gold_ci_high": _to_float(gold.get("ci_upper")),
            "system_ci_low": _to_float(best.get("ci_lower")),
            "system_ci_high": _to_float(best.get("ci_upper")),
            "point_rel_error": None,
            "ci_rel_error_max": None,
            "within_10pct": None,
            "ci_within_10pct": None,
            "type_match": None,
            "calibrated_confidence": _to_float(best.get("calibrated_confidence")),
            "automation_tier": best.get("automation_tier"),
        }

        if included:
            if extracted:
                extracted_on_gold_included += 1
                if best.get("page_number") is not None:
                    page_present_count += 1
                if str(best.get("source_text") or "").strip():
                    source_present_count += 1
        else:
            if extracted:
                extracted_on_gold_excluded += 1

        if included and extracted:
            gold_point = _to_float(gold.get("point_estimate"))
            system_point = _to_float(best.get("effect_size"))
            if gold_point is not None and system_point is not None:
                point_rel = _rel_err(system_point, gold_point, float(args.zero_abs_tolerance))
                row_payload["point_rel_error"] = point_rel
                f1 = point_rel <= 0.01
                f2 = point_rel <= 0.02
                f5 = point_rel <= 0.05
                f10 = point_rel <= 0.10
                row_payload["within_10pct"] = f10
                point_1.append(f1)
                point_2.append(f2)
                point_5.append(f5)
                point_10.append(f10)
                conf = _to_float(best.get("calibrated_confidence"))
                if conf is not None:
                    prob = min(1.0, max(0.0, conf))
                    calibration_pairs.append((prob, 1 if f10 else 0))

            g_type = _normalize_effect_type(gold.get("effect_type"))
            s_type = _normalize_effect_type(best.get("type"))
            if g_type and s_type:
                tm = g_type == s_type
                row_payload["type_match"] = tm
                type_match_flags.append(tm)

            g_low = _to_float(gold.get("ci_lower"))
            g_high = _to_float(gold.get("ci_upper"))
            s_low = _to_float(best.get("ci_lower"))
            s_high = _to_float(best.get("ci_upper"))
            if g_low is not None and g_high is not None and s_low is not None and s_high is not None:
                ci_rel = max(
                    _rel_err(s_low, g_low, float(args.zero_abs_tolerance)),
                    _rel_err(s_high, g_high, float(args.zero_abs_tolerance)),
                )
                ci_ok = ci_rel <= 0.10
                row_payload["ci_rel_error_max"] = ci_rel
                row_payload["ci_within_10pct"] = ci_ok
                ci_10.append(ci_ok)

        per_row.append(row_payload)

    point_bootstrap = _bootstrap_rate(point_10, n_bootstrap=int(args.n_bootstrap), rng_seed=int(args.rng_seed))
    ci_bootstrap = _bootstrap_rate(ci_10, n_bootstrap=int(args.n_bootstrap), rng_seed=int(args.rng_seed) + 17)

    brier = None
    if calibration_pairs:
        brier = sum((p - y) ** 2 for p, y in calibration_pairs) / len(calibration_pairs)
    ece = _ece(calibration_pairs, n_bins=int(args.ece_bins))

    summary = {
        "benchmark_rows_total": len(bench_by_id),
        "gold_rows_resolved": gold_resolved,
        "gold_rows_unresolved": len(bench_by_id) - gold_resolved,
        "gold_rows_included": gold_included,
        "gold_rows_excluded": gold_excluded,
        "extracted_on_gold_included": extracted_on_gold_included,
        "extracted_on_gold_excluded": extracted_on_gold_excluded,
        "point_comparable_rows": len(point_10),
        "ci_comparable_rows": len(ci_10),
        "type_comparable_rows": len(type_match_flags),
        "calibration_rows": len(calibration_pairs),
        "extraction_coverage_on_gold_included": (extracted_on_gold_included / gold_included) if gold_included else None,
        "false_positive_extraction_rate_on_gold_excluded": (
            extracted_on_gold_excluded / gold_excluded if gold_excluded else None
        ),
        "point_within_1pct_rate": (sum(point_1) / len(point_1)) if point_1 else None,
        "point_within_2pct_rate": (sum(point_2) / len(point_2)) if point_2 else None,
        "point_within_5pct_rate": (sum(point_5) / len(point_5)) if point_5 else None,
        "point_within_10pct_rate": (sum(point_10) / len(point_10)) if point_10 else None,
        "ci_within_10pct_rate": (sum(ci_10) / len(ci_10)) if ci_10 else None,
        "effect_type_match_rate": (sum(type_match_flags) / len(type_match_flags)) if type_match_flags else None,
        "source_presence_on_extracted_gold_included": (
            source_present_count / extracted_on_gold_included if extracted_on_gold_included else None
        ),
        "page_presence_on_extracted_gold_included": (
            page_present_count / extracted_on_gold_included if extracted_on_gold_included else None
        ),
        "point_within_10pct_bootstrap_95ci": point_bootstrap,
        "ci_within_10pct_bootstrap_95ci": ci_bootstrap,
        "calibration_brier_point10": brier,
        "calibration_ece_point10": ece,
    }

    payload = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "benchmark_cohort_jsonl": str(args.benchmark_cohort_jsonl).replace("\\", "/"),
            "system_results_jsonl": str(args.system_results_jsonl).replace("\\", "/"),
            "adjudicated_jsonl": str(args.adjudicated_jsonl).replace("\\", "/")
            if args.adjudicated_jsonl
            else None,
            "annotator_a_jsonl": str(args.annotator_a_jsonl).replace("\\", "/")
            if args.annotator_a_jsonl
            else None,
            "annotator_b_jsonl": str(args.annotator_b_jsonl).replace("\\", "/")
            if args.annotator_b_jsonl
            else None,
            "consensus_point_tol": float(args.consensus_point_tol),
            "consensus_ci_tol": float(args.consensus_ci_tol),
            "zero_abs_tolerance": float(args.zero_abs_tolerance),
            "n_bootstrap": int(args.n_bootstrap),
            "rng_seed": int(args.rng_seed),
            "ece_bins": int(args.ece_bins),
        },
        "label_summary": label_summary,
        "summary": summary,
        "rows": per_row,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines: List[str] = []
    lines.append("# Cardiology Linked Benchmark Evaluation")
    lines.append("")
    lines.append(f"- Generated UTC: {payload['generated_at_utc']}")
    lines.append(f"- Label mode: {label_summary.get('mode')}")
    lines.append(f"- Benchmark rows: {summary['benchmark_rows_total']}")
    lines.append(f"- Gold resolved rows: {summary['gold_rows_resolved']}")
    lines.append(f"- Gold unresolved rows: {summary['gold_rows_unresolved']}")
    lines.append(f"- Gold included rows: {summary['gold_rows_included']}")
    lines.append(f"- Gold excluded rows: {summary['gold_rows_excluded']}")
    lines.append("")
    lines.append("## Core Metrics")
    lines.append("")
    lines.append(f"- Extraction coverage on gold-included: {_fmt_pct(summary['extraction_coverage_on_gold_included'])}")
    lines.append(
        "- False-positive extraction on gold-excluded: "
        f"{_fmt_pct(summary['false_positive_extraction_rate_on_gold_excluded'])}"
    )
    lines.append(f"- Point within 10%: {_fmt_pct(summary['point_within_10pct_rate'])}")
    lines.append(f"- Point within 5%: {_fmt_pct(summary['point_within_5pct_rate'])}")
    lines.append(f"- CI within 10%: {_fmt_pct(summary['ci_within_10pct_rate'])}")
    lines.append(f"- Effect-type match: {_fmt_pct(summary['effect_type_match_rate'])}")
    lines.append(f"- Source presence on extracted gold-included: {_fmt_pct(summary['source_presence_on_extracted_gold_included'])}")
    lines.append(f"- Page presence on extracted gold-included: {_fmt_pct(summary['page_presence_on_extracted_gold_included'])}")
    lines.append("")
    lines.append("## Calibration (Point<=10% Event)")
    lines.append("")
    lines.append(f"- Calibration rows: {summary['calibration_rows']}")
    lines.append(
        f"- Brier score: {(f'{summary['calibration_brier_point10']:.6f}' if summary['calibration_brier_point10'] is not None else 'n/a')}"
    )
    lines.append(
        f"- ECE ({int(args.ece_bins)} bins): {(f'{summary['calibration_ece_point10']:.6f}' if summary['calibration_ece_point10'] is not None else 'n/a')}"
    )
    lines.append("")
    lines.append("## Label Agreement / Consensus")
    lines.append("")
    for key in (
        "rows_loaded",
        "rows_overlap",
        "consensus_rows",
        "unresolved_rows",
        "included_match_rate",
        "type_match_rate",
        "point_within_5pct_rate",
        "point_within_10pct_rate",
        "ci_within_10pct_rate",
    ):
        if key in label_summary:
            value = label_summary.get(key)
            if isinstance(value, float):
                lines.append(f"- {key}: {_fmt_pct(value)}")
            else:
                lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Row Detail (first 100)")
    lines.append("")
    lines.append("| Benchmark ID | Status | Gold Incl | Extracted | Point Err | <=10% | CI Err | CI<=10% | Type Match |")
    lines.append("| --- | --- | --- | --- | ---: | --- | ---: | --- | --- |")
    for row in per_row[:100]:
        point_err = row.get("point_rel_error")
        ci_err = row.get("ci_rel_error_max")
        lines.append(
            f"| {row.get('benchmark_id')} | {row.get('status') or ''} | "
            f"{'yes' if row.get('gold_included') else 'no'} | "
            f"{'yes' if row.get('extracted') else 'no'} | "
            f"{(f'{point_err:.6f}' if point_err is not None else 'n/a')} | "
            f"{('yes' if row.get('within_10pct') else ('no' if row.get('within_10pct') is False else 'n/a'))} | "
            f"{(f'{ci_err:.6f}' if ci_err is not None else 'n/a')} | "
            f"{('yes' if row.get('ci_within_10pct') else ('no' if row.get('ci_within_10pct') is False else 'n/a'))} | "
            f"{('yes' if row.get('type_match') else ('no' if row.get('type_match') is False else 'n/a'))} |"
        )

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_md}")
    if args.output_consensus_jsonl is not None and gold_map:
        print(f"Wrote: {args.output_consensus_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
