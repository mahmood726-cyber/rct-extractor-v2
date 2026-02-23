#!/usr/bin/env python3
"""Compute real-RCT extraction metrics from gold and result files."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

STRICT_DISTANCE_THRESHOLD = 0.05
LENIENT_DISTANCE_THRESHOLD = 0.2

RATIO_TYPES = {"HR", "OR", "RR", "IRR", "GMR", "NNT", "NNH"}
DIFF_TYPES = {"MD", "SMD", "ARD", "ARR", "RRR", "RD", "WMD"}


def _load_jsonl(path: Path) -> List[Dict]:
    items: List[Dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                items.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL line {line_number}: {exc}") from exc
    return items


def _normalize_effect_type(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip().upper()
    if not value:
        return None
    alias_map = {
        "RISK RATIO": "RR",
        "ODDS RATIO": "OR",
        "HAZARD RATIO": "HR",
        "MEAN DIFFERENCE": "MD",
        "STD MEAN DIFFERENCE": "SMD",
        "STANDARDIZED MEAN DIFFERENCE": "SMD",
    }
    return alias_map.get(value, value)


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _target_reference(gold_record: Dict) -> Dict[str, Optional[object]]:
    """Choose the primary numeric reference for match scoring."""
    gold = gold_record.get("gold") or {}
    gold_point = _to_float(gold.get("point_estimate"))
    if gold_point is not None:
        return {
            "value": gold_point,
            "effect_type": _normalize_effect_type(gold.get("effect_type")),
            "ci_lower": _to_float(gold.get("ci_lower")),
            "ci_upper": _to_float(gold.get("ci_upper")),
            "source": "gold",
        }

    return {
        "value": _to_float(gold_record.get("cochrane_effect")),
        "effect_type": None,
        "ci_lower": _to_float(gold_record.get("cochrane_ci_lower")),
        "ci_upper": _to_float(gold_record.get("cochrane_ci_upper")),
        "source": "cochrane",
    }


def _expected_effect_types(gold_record: Dict) -> Set[str]:
    gold_type = _normalize_effect_type(gold_record.get("gold", {}).get("effect_type"))
    if gold_type:
        return {gold_type}

    # Fall back to broad families when an exact gold effect type is unavailable.
    if str(gold_record.get("cochrane_outcome_type", "")).lower() == "continuous":
        return {"MD", "SMD", "WMD"}
    return RATIO_TYPES | DIFF_TYPES


def _is_ma_ready(best_match: Dict) -> bool:
    has_effect = best_match.get("effect_size") is not None
    has_ci = best_match.get("ci_lower") is not None and best_match.get("ci_upper") is not None
    has_se = best_match.get("standard_error") is not None
    has_source = bool(best_match.get("source_text"))
    has_page = best_match.get("page_number") is not None
    return has_effect and (has_ci or has_se) and has_source and has_page


def _is_ratio_measure(
    extracted_type: Optional[str],
    target_type: Optional[str],
    outcome_type: Optional[str],
) -> bool:
    if extracted_type in DIFF_TYPES or target_type in DIFF_TYPES:
        return False
    if extracted_type in RATIO_TYPES or target_type in RATIO_TYPES:
        return True
    return str(outcome_type or "").lower() != "continuous"


def _match_distance(
    extracted_value: float,
    target_value: float,
    extracted_type: Optional[str],
    target_type: Optional[str],
    outcome_type: Optional[str],
) -> float:
    if _is_ratio_measure(extracted_type, target_type, outcome_type) and extracted_value > 0 and target_value > 0:
        return abs(math.log(extracted_value) - math.log(target_value))
    # For difference-based measures, scale by target magnitude so units do not dominate distance.
    scale = max(abs(target_value), 1.0)
    return abs(extracted_value - target_value) / scale


def _load_split_ids(split_manifest: Optional[Path], split: str) -> Optional[Set[str]]:
    if split_manifest is None:
        return None

    with split_manifest.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    trial_ids = manifest.get("trial_ids", {})
    if split == "all":
        selected = set(trial_ids.get("train", []))
        selected.update(trial_ids.get("validation", []))
        selected.update(trial_ids.get("test", []))
        return selected

    if split not in trial_ids:
        raise ValueError(f"Split '{split}' not found in manifest {split_manifest}")
    return set(trial_ids[split])


def compute_metrics(gold_records: List[Dict], result_records: List[Dict], selected_ids: Optional[Set[str]]) -> Dict:
    gold_by_id = {record["study_id"]: record for record in gold_records if record.get("study_id")}
    result_by_id = {record["study_id"]: record for record in result_records if record.get("study_id")}

    trial_ids = set(gold_by_id.keys())
    if selected_ids is not None:
        trial_ids &= selected_ids
    trial_ids = set(sorted(trial_ids))

    totals = {
        "total_trials": len(trial_ids),
        "trials_with_extractions": 0,
        "matchable_trials": 0,
        "strict_matches": 0,
        "lenient_matches": 0,
        "effect_type_total": 0,
        "effect_type_correct": 0,
        "ci_total": 0,
        "ci_complete": 0,
        "ma_ready_trials": 0,
        "computed_trials": 0,
    }

    for study_id in trial_ids:
        gold = gold_by_id[study_id]
        result = result_by_id.get(study_id)
        if not result:
            continue

        best_match = result.get("best_match") or {}
        extracted_value = _to_float(best_match.get("effect_size"))
        if extracted_value is None:
            continue

        totals["trials_with_extractions"] += 1

        extracted_type = _normalize_effect_type(best_match.get("type"))
        target = _target_reference(gold)
        target_value = target["value"]
        if target_value is not None:
            totals["matchable_trials"] += 1
            distance = _match_distance(
                extracted_value=extracted_value,
                target_value=target_value,
                extracted_type=extracted_type,
                target_type=target["effect_type"],
                outcome_type=gold.get("cochrane_outcome_type"),
            )
            if distance < STRICT_DISTANCE_THRESHOLD:
                totals["strict_matches"] += 1
                totals["lenient_matches"] += 1
            elif distance < LENIENT_DISTANCE_THRESHOLD:
                totals["lenient_matches"] += 1

        expected_types = _expected_effect_types(gold)
        if expected_types:
            totals["effect_type_total"] += 1
            if extracted_type in expected_types:
                totals["effect_type_correct"] += 1

        totals["ci_total"] += 1
        if best_match.get("ci_lower") is not None and best_match.get("ci_upper") is not None:
            totals["ci_complete"] += 1

        if _is_ma_ready(best_match):
            totals["ma_ready_trials"] += 1

        source_text = str(best_match.get("source_text", ""))
        if source_text.startswith("[COMPUTED from raw data]"):
            totals["computed_trials"] += 1

    def _rate(numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator > 0 else 0.0

    metrics = {
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": totals,
        "rates": {
            "extraction_coverage": _rate(totals["trials_with_extractions"], totals["total_trials"]),
            "strict_match_rate": _rate(totals["strict_matches"], totals["total_trials"]),
            "lenient_match_rate": _rate(totals["lenient_matches"], totals["total_trials"]),
            "effect_type_accuracy": _rate(totals["effect_type_correct"], totals["effect_type_total"]),
            "ci_completeness": _rate(totals["ci_complete"], totals["ci_total"]),
            "ma_ready_yield": _rate(totals["ma_ready_trials"], totals["total_trials"]),
            "computed_effect_share": _rate(totals["computed_trials"], totals["total_trials"]),
        },
    }
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=Path("gold_data/gold_50.jsonl"), help="Gold JSONL file.")
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("gold_data/baseline_results.json"),
        help="Extractor baseline results JSON file.",
    )
    parser.add_argument(
        "--split-manifest",
        type=Path,
        default=None,
        help="Optional split manifest from scripts/freeze_eval_split.py.",
    )
    parser.add_argument(
        "--split",
        choices=["train", "validation", "test", "all"],
        default="all",
        help="Which split to evaluate when --split-manifest is provided.",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional output JSON path.")
    args = parser.parse_args()

    if not args.gold.exists():
        raise FileNotFoundError(f"Gold dataset not found: {args.gold}")
    if not args.results.exists():
        raise FileNotFoundError(f"Results file not found: {args.results}")

    gold_records = [record for record in _load_jsonl(args.gold) if not record.get("excluded")]
    with args.results.open("r", encoding="utf-8") as handle:
        result_records = json.load(handle)

    selected_ids = _load_split_ids(args.split_manifest, args.split)
    metrics = compute_metrics(gold_records, result_records, selected_ids)

    print("Real-RCT Evaluation Metrics")
    print("===========================")
    print(f"Trials: {metrics['counts']['total_trials']}")
    for key, value in metrics["rates"].items():
        print(f"{key:>24}: {value:.3%}")

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(metrics, handle, indent=2, ensure_ascii=False)
        print(f"\nWrote metrics JSON: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
