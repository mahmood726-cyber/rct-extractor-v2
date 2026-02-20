#!/usr/bin/env python3
"""Bootstrap confidence intervals for real-RCT extraction metrics."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Dict, List, Optional

RATIO_TYPES = {"HR", "OR", "RR", "IRR", "GMR", "NNT", "NNH"}
DIFF_TYPES = {"MD", "SMD", "ARD", "ARR", "RRR", "RD", "WMD"}

STRICT_DISTANCE_THRESHOLD = 0.05
LENIENT_DISTANCE_THRESHOLD = 0.2


def _load_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            rows.append(json.loads(stripped))
    return rows


def _normalize_effect_type(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    if not normalized:
        return None
    alias_map = {
        "RISK RATIO": "RR",
        "ODDS RATIO": "OR",
        "HAZARD RATIO": "HR",
        "MEAN DIFFERENCE": "MD",
        "STD MEAN DIFFERENCE": "SMD",
        "STANDARDIZED MEAN DIFFERENCE": "SMD",
    }
    return alias_map.get(normalized, normalized)


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_ratio_measure(extracted_type: Optional[str], target_type: Optional[str], outcome_type: Optional[str]) -> bool:
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
    return abs(extracted_value - target_value)


def _target_reference(gold_record: Dict) -> Dict[str, Optional[float]]:
    gold = gold_record.get("gold") or {}
    gold_point = _to_float(gold.get("point_estimate"))
    if gold_point is not None:
        return {
            "value": gold_point,
            "effect_type": _normalize_effect_type(gold.get("effect_type")),
        }
    return {
        "value": _to_float(gold_record.get("cochrane_effect")),
        "effect_type": None,
    }


def _expected_effect_types(gold_record: Dict) -> set[str]:
    gold_type = _normalize_effect_type((gold_record.get("gold") or {}).get("effect_type"))
    if gold_type:
        return {gold_type}
    if str(gold_record.get("cochrane_outcome_type", "")).lower() == "continuous":
        return {"MD", "SMD", "WMD"}
    return set(RATIO_TYPES | DIFF_TYPES)


def _is_ma_ready(best_match: Dict) -> bool:
    has_effect = best_match.get("effect_size") is not None
    has_ci = best_match.get("ci_lower") is not None and best_match.get("ci_upper") is not None
    has_se = best_match.get("standard_error") is not None
    has_source = bool(best_match.get("source_text"))
    has_page = best_match.get("page_number") is not None
    return has_effect and (has_ci or has_se) and has_source and has_page


def _compute_trial_flags(gold_record: Dict, result_record: Optional[Dict]) -> Dict[str, float]:
    if not result_record:
        return {
            "extracted": 0.0,
            "strict": 0.0,
            "lenient": 0.0,
            "effect_type_total": 0.0,
            "effect_type_correct": 0.0,
            "ci_total": 0.0,
            "ci_complete": 0.0,
            "ma_ready": 0.0,
            "computed": 0.0,
        }

    best_match = result_record.get("best_match") or {}
    extracted_value = _to_float(best_match.get("effect_size"))
    if extracted_value is None:
        return {
            "extracted": 0.0,
            "strict": 0.0,
            "lenient": 0.0,
            "effect_type_total": 0.0,
            "effect_type_correct": 0.0,
            "ci_total": 0.0,
            "ci_complete": 0.0,
            "ma_ready": 0.0,
            "computed": 0.0,
        }

    extracted_type = _normalize_effect_type(best_match.get("type"))
    target = _target_reference(gold_record)
    target_value = target["value"]
    strict = 0.0
    lenient = 0.0
    if target_value is not None:
        distance = _match_distance(
            extracted_value=extracted_value,
            target_value=target_value,
            extracted_type=extracted_type,
            target_type=target["effect_type"],
            outcome_type=gold_record.get("cochrane_outcome_type"),
        )
        if distance < STRICT_DISTANCE_THRESHOLD:
            strict = 1.0
            lenient = 1.0
        elif distance < LENIENT_DISTANCE_THRESHOLD:
            lenient = 1.0

    expected_types = _expected_effect_types(gold_record)
    effect_type_correct = 1.0 if extracted_type in expected_types else 0.0

    ci_complete = 1.0 if (best_match.get("ci_lower") is not None and best_match.get("ci_upper") is not None) else 0.0
    ma_ready = 1.0 if _is_ma_ready(best_match) else 0.0
    computed = 1.0 if str(best_match.get("source_text") or "").startswith("[COMPUTED from raw data]") else 0.0

    return {
        "extracted": 1.0,
        "strict": strict,
        "lenient": lenient,
        "effect_type_total": 1.0,
        "effect_type_correct": effect_type_correct,
        "ci_total": 1.0,
        "ci_complete": ci_complete,
        "ma_ready": ma_ready,
        "computed": computed,
    }


def _aggregate(sample_flags: List[Dict[str, float]]) -> Dict[str, float]:
    total_trials = float(len(sample_flags))
    extracted = sum(item["extracted"] for item in sample_flags)
    strict = sum(item["strict"] for item in sample_flags)
    lenient = sum(item["lenient"] for item in sample_flags)
    effect_type_total = sum(item["effect_type_total"] for item in sample_flags)
    effect_type_correct = sum(item["effect_type_correct"] for item in sample_flags)
    ci_total = sum(item["ci_total"] for item in sample_flags)
    ci_complete = sum(item["ci_complete"] for item in sample_flags)
    ma_ready = sum(item["ma_ready"] for item in sample_flags)
    computed = sum(item["computed"] for item in sample_flags)

    def _rate(numerator: float, denominator: float) -> float:
        return numerator / denominator if denominator > 0 else 0.0

    return {
        "extraction_coverage": _rate(extracted, total_trials),
        "strict_match_rate": _rate(strict, total_trials),
        "lenient_match_rate": _rate(lenient, total_trials),
        "effect_type_accuracy": _rate(effect_type_correct, effect_type_total),
        "ci_completeness": _rate(ci_complete, ci_total),
        "ma_ready_yield": _rate(ma_ready, total_trials),
        "computed_effect_share": _rate(computed, total_trials),
    }


def _percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    if q <= 0:
        return min(values)
    if q >= 1:
        return max(values)
    sorted_values = sorted(values)
    pos = (len(sorted_values) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_values[lo]
    frac = pos - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--n-bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=1729)
    args = parser.parse_args()

    if args.n_bootstrap <= 0:
        raise ValueError("--n-bootstrap must be > 0")

    gold_rows = [row for row in _load_jsonl(args.gold) if not row.get("excluded")]
    result_rows = json.loads(args.results.read_text(encoding="utf-8"))

    gold_by_id = {row["study_id"]: row for row in gold_rows if row.get("study_id")}
    result_by_id = {row["study_id"]: row for row in result_rows if row.get("study_id")}
    trial_ids = sorted(gold_by_id.keys())

    flags_by_id = {
        study_id: _compute_trial_flags(gold_by_id[study_id], result_by_id.get(study_id))
        for study_id in trial_ids
    }
    point_rates = _aggregate([flags_by_id[study_id] for study_id in trial_ids])

    rng = random.Random(args.seed)
    metric_names = list(point_rates.keys())
    samples: Dict[str, List[float]] = {name: [] for name in metric_names}

    for _ in range(args.n_bootstrap):
        sampled_flags = [flags_by_id[rng.choice(trial_ids)] for _ in trial_ids]
        sampled_rates = _aggregate(sampled_flags)
        for metric in metric_names:
            samples[metric].append(sampled_rates[metric])

    output_payload = {
        "gold": str(args.gold),
        "results": str(args.results),
        "n_trials": len(trial_ids),
        "n_bootstrap": args.n_bootstrap,
        "seed": args.seed,
        "metrics": {
            metric: {
                "point": point_rates[metric],
                "ci_low_95": _percentile(samples[metric], 0.025),
                "ci_high_95": _percentile(samples[metric], 0.975),
            }
            for metric in metric_names
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
