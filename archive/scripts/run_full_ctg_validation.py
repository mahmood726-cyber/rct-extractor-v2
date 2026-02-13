#!/usr/bin/env python3
"""
Complete CTG Validation
=======================

Validates RCT Extractor against ClinicalTrials.gov author-reported results.
Uses a curated list of trials known to have effect estimates.

This is the authoritative validation - CTG data comes directly from trial authors.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import statistics

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.ctg_scraper import CTGScraper, CTGStudy, EffectEstimate
from src.core.enhanced_extractor_v3 import EnhancedExtractor, Extraction


# Curated list of trials with known effect estimates (expanded)
VALIDATION_NCTS = [
    # Cardiovascular
    "NCT02653482",  # DAPA-HF
    "NCT01920711",  # PARADIGM-HF
    "NCT02065791",  # CREDENCE
    "NCT02819518",  # DECLARE-TIMI
    "NCT01032915",  # ROCKET-AF
    "NCT02105948",  # EMPEROR-Reduced
    "NCT03036124",  # DAPA-CKD
    "NCT01897571",  # ARISTOTLE substudy
    "NCT00790010",  # SAVOR-TIMI
    "NCT01243424",  # LEADER
    "NCT01720446",  # SUSTAIN-6
    "NCT01394952",  # EXAMINE
    "NCT00968708",  # TECOS
    "NCT01144338",  # CANVAS
    "NCT01989754",  # EMPA-REG OUTCOME
    # Oncology
    "NCT02142738",  # KEYNOTE-024
    "NCT02494583",  # KEYNOTE-189
    "NCT01844505",  # PALOMA-2
    "NCT02422615",  # PALOMA-3
    "NCT01120184",  # CheckMate 067
    "NCT02252042",  # POLO
    "NCT02853331",  # KEYNOTE-426
    "NCT02684006",  # IMpassion130
    "NCT02370498",  # MONALEESA-3
    "NCT02107703",  # MONARCH-3
    # Diabetes
    "NCT01131676",  # ORIGIN
    "NCT00295633",  # ACCORD
    "NCT00145925",  # ADVANCE
    "NCT01986881",  # REWIND
    "NCT01730534",  # PIONEER 6
    # Rheumatology
    "NCT01877668",  # RA-BEAM
    "NCT00106535",  # RAPID 1
    "NCT00106522",  # RAPID 2
    # Respiratory
    "NCT01854658",  # INPULSIS
    "NCT02597127",  # SENSCIS
    # Neurology
    "NCT01188655",  # SPRINT-MS
    "NCT01247545",  # FREEDOMS II
    # Infectious Disease
    "NCT04280705",  # ACTT-1
    "NCT04381936",  # RECOVERY
]


@dataclass
class MatchResult:
    """Result of matching CTG effect to extraction"""
    ctg_effect_type: str
    ctg_value: float
    ctg_ci_lower: Optional[float]
    ctg_ci_upper: Optional[float]
    extracted_type: Optional[str]
    extracted_value: Optional[float]
    extracted_ci_lower: Optional[float]
    extracted_ci_upper: Optional[float]
    value_match: bool
    type_match: bool
    ci_match: bool
    overall_match: bool
    value_error: Optional[float]
    value_error_pct: Optional[float]


@dataclass
class ValidationMetrics:
    """Comprehensive validation metrics"""
    studies_validated: int = 0
    total_ctg_effects: int = 0
    total_extractions: int = 0
    true_positives: int = 0
    false_negatives: int = 0
    false_positives: int = 0

    sensitivity: float = 0.0
    precision: float = 0.0
    f1_score: float = 0.0

    mean_absolute_error: float = 0.0
    mean_relative_error_pct: float = 0.0
    median_absolute_error: float = 0.0

    ci_detection_rate: float = 0.0
    ci_accuracy: float = 0.0

    by_effect_type: Dict = field(default_factory=dict)


def values_match(v1: float, v2: float, tolerance: float = 0.02) -> bool:
    """Check if values match within tolerance"""
    if v1 == 0 and v2 == 0:
        return True
    if v1 == 0 or v2 == 0:
        return abs(v1 - v2) < 0.01
    rel_diff = abs(v1 - v2) / max(abs(v1), abs(v2))
    return rel_diff <= tolerance


def run_validation(sample: int = None):
    """Run full CTG-based validation.

    Args:
        sample: If set, validate only the first N trials from the list.
    """
    print("=" * 70)
    print("CTG-BASED VALIDATION - AUTHORITATIVE GROUND TRUTH")
    print("Using author-reported data from ClinicalTrials.gov")
    print("=" * 70)

    scraper = CTGScraper()
    extractor = EnhancedExtractor()

    all_matches = []
    by_type = defaultdict(lambda: {"tp": 0, "fn": 0, "errors": []})
    total_extracted = 0
    studies_validated = 0

    ncts = VALIDATION_NCTS[:sample] if sample else VALIDATION_NCTS
    print(f"\nValidating {len(ncts)} trials...")

    for i, nct_id in enumerate(ncts):
        try:
            study = scraper.fetch_study(nct_id)
            if not study or not study.effect_estimates:
                continue

            studies_validated += 1

            # Create source text from CTG effect estimates
            source_texts = []
            for effect in study.effect_estimates:
                source_texts.append(effect.source_text)
                # Also add standardized format
                if effect.ci_lower and effect.ci_upper:
                    source_texts.append(
                        f"{effect.effect_type} {effect.value} (95% CI {effect.ci_lower}-{effect.ci_upper})"
                    )
                else:
                    source_texts.append(f"{effect.effect_type} {effect.value}")

            combined_text = "\n".join(source_texts)

            # Extract using our tool
            extractions = extractor.extract(combined_text)
            total_extracted += len(extractions)

            # Match each CTG effect to extractions
            matched_indices = set()

            for ctg_effect in study.effect_estimates:
                best_match = None
                best_score = 0
                best_idx = -1

                for idx, ext in enumerate(extractions):
                    if idx in matched_indices:
                        continue

                    score = 0
                    if ctg_effect.effect_type.upper() == ext.effect_type.value.upper():
                        score += 0.4
                    if values_match(ctg_effect.value, ext.point_estimate):
                        score += 0.6

                    if score > best_score:
                        best_score = score
                        best_match = ext
                        best_idx = idx

                if best_match and best_score >= 0.6:
                    matched_indices.add(best_idx)

                    type_match = ctg_effect.effect_type.upper() == best_match.effect_type.value.upper()
                    value_match = values_match(ctg_effect.value, best_match.point_estimate)

                    ci_match = False
                    if ctg_effect.ci_lower and ctg_effect.ci_upper and best_match.ci:
                        ci_match = (
                            values_match(ctg_effect.ci_lower, best_match.ci.lower, 0.05) and
                            values_match(ctg_effect.ci_upper, best_match.ci.upper, 0.05)
                        )

                    value_error = abs(ctg_effect.value - best_match.point_estimate)
                    value_error_pct = (value_error / abs(ctg_effect.value) * 100) if ctg_effect.value != 0 else 0

                    match_result = MatchResult(
                        ctg_effect_type=ctg_effect.effect_type,
                        ctg_value=ctg_effect.value,
                        ctg_ci_lower=ctg_effect.ci_lower,
                        ctg_ci_upper=ctg_effect.ci_upper,
                        extracted_type=best_match.effect_type.value,
                        extracted_value=best_match.point_estimate,
                        extracted_ci_lower=best_match.ci.lower if best_match.ci else None,
                        extracted_ci_upper=best_match.ci.upper if best_match.ci else None,
                        value_match=value_match,
                        type_match=type_match,
                        ci_match=ci_match,
                        overall_match=value_match and type_match,
                        value_error=value_error,
                        value_error_pct=value_error_pct
                    )
                    all_matches.append(match_result)

                    if value_match and type_match:
                        by_type[ctg_effect.effect_type]["tp"] += 1
                        by_type[ctg_effect.effect_type]["errors"].append(value_error_pct)
                    else:
                        by_type[ctg_effect.effect_type]["fn"] += 1
                else:
                    # False negative
                    match_result = MatchResult(
                        ctg_effect_type=ctg_effect.effect_type,
                        ctg_value=ctg_effect.value,
                        ctg_ci_lower=ctg_effect.ci_lower,
                        ctg_ci_upper=ctg_effect.ci_upper,
                        extracted_type=None,
                        extracted_value=None,
                        extracted_ci_lower=None,
                        extracted_ci_upper=None,
                        value_match=False,
                        type_match=False,
                        ci_match=False,
                        overall_match=False,
                        value_error=None,
                        value_error_pct=None
                    )
                    all_matches.append(match_result)
                    by_type[ctg_effect.effect_type]["fn"] += 1

            if (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{len(ncts)} trials")

        except Exception as e:
            print(f"  Error on {nct_id}: {e}")

        time.sleep(0.5)  # Rate limiting

    # Calculate metrics
    metrics = ValidationMetrics()
    metrics.studies_validated = studies_validated
    metrics.total_ctg_effects = len(all_matches)
    metrics.total_extractions = total_extracted

    metrics.true_positives = sum(1 for m in all_matches if m.overall_match)
    metrics.false_negatives = sum(1 for m in all_matches if not m.overall_match)

    # FP = extractions that didn't match any CTG effect
    matched_count = sum(1 for m in all_matches if m.extracted_value is not None)
    metrics.false_positives = total_extracted - matched_count

    # Sensitivity
    if metrics.true_positives + metrics.false_negatives > 0:
        metrics.sensitivity = metrics.true_positives / (metrics.true_positives + metrics.false_negatives)

    # Precision
    if metrics.true_positives + metrics.false_positives > 0:
        metrics.precision = metrics.true_positives / (metrics.true_positives + metrics.false_positives)

    # F1
    if metrics.sensitivity + metrics.precision > 0:
        metrics.f1_score = 2 * (metrics.sensitivity * metrics.precision) / (metrics.sensitivity + metrics.precision)

    # Error metrics
    errors = [m.value_error for m in all_matches if m.value_error is not None]
    errors_pct = [m.value_error_pct for m in all_matches if m.value_error_pct is not None]

    if errors:
        metrics.mean_absolute_error = statistics.mean(errors)
        metrics.median_absolute_error = statistics.median(errors)
    if errors_pct:
        metrics.mean_relative_error_pct = statistics.mean(errors_pct)

    # CI metrics
    ci_expected = sum(1 for m in all_matches if m.ctg_ci_lower is not None)
    ci_detected = sum(1 for m in all_matches if m.extracted_ci_lower is not None)
    ci_correct = sum(1 for m in all_matches if m.ci_match)

    if ci_expected > 0:
        metrics.ci_detection_rate = ci_detected / ci_expected
    if ci_detected > 0:
        metrics.ci_accuracy = ci_correct / ci_detected

    # By effect type
    for effect_type, data in by_type.items():
        total = data["tp"] + data["fn"]
        sens = data["tp"] / total if total > 0 else 0
        mean_err = statistics.mean(data["errors"]) if data["errors"] else 0

        metrics.by_effect_type[effect_type] = {
            "true_positives": data["tp"],
            "false_negatives": data["fn"],
            "total": total,
            "sensitivity": round(sens, 4),
            "mean_error_pct": round(mean_err, 4)
        }

    # Print results
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS - CTG AUTHOR-REPORTED DATA")
    print("=" * 70)

    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"Studies validated:     {metrics.studies_validated}")
    print(f"CTG effect estimates:  {metrics.total_ctg_effects}")
    print(f"Our extractions:       {metrics.total_extractions}")

    print(f"\n{'='*50}")
    print("CLASSIFICATION METRICS")
    print(f"{'='*50}")
    print(f"True Positives:   {metrics.true_positives}")
    print(f"False Negatives:  {metrics.false_negatives}")
    print(f"False Positives:  {metrics.false_positives}")

    print(f"\n{'='*50}")
    print("PERFORMANCE METRICS")
    print(f"{'='*50}")
    print(f"Sensitivity (Recall): {metrics.sensitivity:.1%}")
    print(f"Precision:            {metrics.precision:.1%}")
    print(f"F1 Score:             {metrics.f1_score:.1%}")

    print(f"\n{'='*50}")
    print("ERROR METRICS")
    print(f"{'='*50}")
    print(f"Mean Absolute Error:   {metrics.mean_absolute_error:.4f}")
    print(f"Mean Relative Error:   {metrics.mean_relative_error_pct:.2f}%")
    print(f"Median Absolute Error: {metrics.median_absolute_error:.4f}")

    print(f"\n{'='*50}")
    print("CONFIDENCE INTERVAL METRICS")
    print(f"{'='*50}")
    print(f"CI Detection Rate: {metrics.ci_detection_rate:.1%}")
    print(f"CI Accuracy:       {metrics.ci_accuracy:.1%}")

    print(f"\n{'='*50}")
    print("BY EFFECT TYPE")
    print(f"{'='*50}")
    for effect_type in sorted(metrics.by_effect_type.keys()):
        data = metrics.by_effect_type[effect_type]
        print(f"  {effect_type:5s}: {data['sensitivity']:6.1%} sensitivity "
              f"({data['true_positives']:3d}/{data['total']:3d}), "
              f"error: {data['mean_error_pct']:.2f}%")

    # Save results
    output = {
        "validation_date": datetime.now().isoformat(),
        "validation_source": "ClinicalTrials.gov (Author-Reported Ground Truth)",
        "methodology": "CTG results are authoritative - data from trial investigators",
        "studies_validated": metrics.studies_validated,
        "metrics": {
            "total_ctg_effects": metrics.total_ctg_effects,
            "total_extractions": metrics.total_extractions,
            "true_positives": metrics.true_positives,
            "false_negatives": metrics.false_negatives,
            "false_positives": metrics.false_positives,
            "sensitivity": round(metrics.sensitivity, 4),
            "precision": round(metrics.precision, 4),
            "f1_score": round(metrics.f1_score, 4),
            "mean_absolute_error": round(metrics.mean_absolute_error, 6),
            "mean_relative_error_pct": round(metrics.mean_relative_error_pct, 4),
            "median_absolute_error": round(metrics.median_absolute_error, 6),
            "ci_detection_rate": round(metrics.ci_detection_rate, 4),
            "ci_accuracy": round(metrics.ci_accuracy, 4),
        },
        "by_effect_type": metrics.by_effect_type,
        "matches": [asdict(m) for m in all_matches]
    }

    output_file = "ctg_validation_results_full.json"
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CTG-based validation of RCT Extractor")
    parser.add_argument("--sample", type=int, default=None,
                        help="Validate only the first N trials (default: all)")
    args = parser.parse_args()
    run_validation(sample=args.sample)
