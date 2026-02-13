#!/usr/bin/env python3
"""
Audit "Extra" Extractions from Positive Controls
=================================================

Analyzes extractions that don't match ground truth to categorize:
1. Valid secondary endpoints (ground truth incomplete)
2. Valid subgroup analyses
3. True false positives (extraction errors)

This addresses the editorial concern about precision measurement artifacts.

Usage:
    python scripts/audit_extra_extractions.py
    python scripts/audit_extra_extractions.py --sample 20
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.external_validation_dataset import ALL_EXTERNAL_VALIDATION_TRIALS

try:
    from src.core.enhanced_extractor_v3 import EnhancedExtractor, EffectType
    HAS_EXTRACTOR = True
except ImportError:
    HAS_EXTRACTOR = False


@dataclass
class ExtraExtraction:
    """An extraction not matching ground truth"""
    trial_name: str
    effect_type: str
    value: float
    ci_lower: Optional[float]
    ci_upper: Optional[float]
    source_snippet: str
    classification: str  # "secondary_endpoint", "subgroup", "sensitivity", "true_fp", "unknown"
    notes: str


def classify_extraction(ext, trial, ground_truth_values) -> str:
    """
    Attempt to classify an extra extraction.

    Heuristics:
    - If value is close to a GT value but different type -> misclassification
    - If source mentions "subgroup" -> subgroup analysis
    - If source mentions secondary/exploratory -> secondary endpoint
    - Otherwise -> needs manual review
    """
    source_lower = ext.source_text.lower()

    # Check for subgroup indicators
    subgroup_terms = ['subgroup', 'subset', 'stratified', 'by age', 'by sex',
                      'in patients with', 'among those']
    if any(term in source_lower for term in subgroup_terms):
        return "subgroup"

    # Check for secondary endpoint indicators
    secondary_terms = ['secondary', 'exploratory', 'post-hoc', 'sensitivity',
                       'per-protocol', 'as-treated']
    if any(term in source_lower for term in secondary_terms):
        return "secondary_endpoint"

    # Check for common secondary outcomes
    secondary_outcomes = ['mortality', 'death', 'hospitalization', 'renal',
                          'stroke', 'mi ', 'myocardial']
    if any(term in source_lower for term in secondary_outcomes):
        # Check if this matches a GT value (would be duplicate) or is different
        for gt_val in ground_truth_values:
            if abs(ext.point_estimate - gt_val) < 0.02:
                return "secondary_endpoint"  # Different CI or slight variation

    # Check for interim/updated analysis
    if 'interim' in source_lower or 'updated' in source_lower:
        return "sensitivity"

    # Check value plausibility - wild values are likely FP
    if ext.point_estimate > 10 or ext.point_estimate < 0.01:
        return "true_fp"

    return "unknown"


def audit_trial(trial) -> List[ExtraExtraction]:
    """Audit extra extractions for a single trial."""
    if not HAS_EXTRACTOR:
        return []

    # Get ground truth
    ground_truth = trial.consensus if trial.consensus else trial.extractor_a
    gt_values = set()
    gt_keys = set()

    for gt in ground_truth:
        gt_values.add(gt.effect_size)
        gt_keys.add((gt.effect_type, round(gt.effect_size, 2)))

    # Extract
    extractor = EnhancedExtractor()
    extractions = extractor.extract(trial.source_text)

    # Find extras
    extras = []
    for ext in extractions:
        ext_type = ext.effect_type.value
        ext_key = (ext_type, round(ext.point_estimate, 2))

        # Check if matches any GT
        is_match = False
        for gt in ground_truth:
            if (ext_type == gt.effect_type and
                abs(ext.point_estimate - gt.effect_size) < 0.02):
                is_match = True
                break

        if not is_match:
            classification = classify_extraction(ext, trial, gt_values)

            extras.append(ExtraExtraction(
                trial_name=trial.trial_name,
                effect_type=ext_type,
                value=ext.point_estimate,
                ci_lower=ext.ci.lower if ext.ci else None,
                ci_upper=ext.ci.upper if ext.ci else None,
                source_snippet=ext.source_text[:100] + "..." if len(ext.source_text) > 100 else ext.source_text,
                classification=classification,
                notes=""
            ))

    return extras


def run_audit(sample_size: Optional[int] = None) -> Dict[str, Any]:
    """Run audit across all trials."""
    all_extras = []

    trials = ALL_EXTERNAL_VALIDATION_TRIALS
    if sample_size and sample_size < len(trials):
        trials = random.sample(list(trials), sample_size)

    for trial in trials:
        extras = audit_trial(trial)
        all_extras.extend(extras)

    # Summarize by classification
    by_class = {}
    for ext in all_extras:
        c = ext.classification
        by_class[c] = by_class.get(c, 0) + 1

    total = len(all_extras)

    return {
        "total_extra_extractions": total,
        "by_classification": by_class,
        "classification_percentages": {
            c: round(count / total * 100, 1) if total > 0 else 0
            for c, count in by_class.items()
        },
        "estimated_true_fp_rate": by_class.get("true_fp", 0) / total if total > 0 else 0,
        "estimated_valid_secondary_rate": (
            by_class.get("secondary_endpoint", 0) +
            by_class.get("subgroup", 0) +
            by_class.get("sensitivity", 0)
        ) / total if total > 0 else 0,
        "details": [asdict(e) for e in all_extras[:50]]  # First 50 for inspection
    }


def print_audit(results: Dict[str, Any]):
    """Print audit results."""
    print("\n" + "=" * 70)
    print("EXTRA EXTRACTION AUDIT")
    print("=" * 70)

    print(f"\nTotal extra extractions: {results['total_extra_extractions']}")

    print("\nBy classification:")
    for c, count in sorted(results['by_classification'].items(), key=lambda x: -x[1]):
        pct = results['classification_percentages'][c]
        print(f"  {c}: {count} ({pct}%)")

    print(f"\nEstimated true FP rate: {results['estimated_true_fp_rate']:.1%}")
    print(f"Estimated valid secondary rate: {results['estimated_valid_secondary_rate']:.1%}")

    print("\n--- Sample Extra Extractions ---")
    for i, ext in enumerate(results['details'][:10], 1):
        print(f"\n{i}. {ext['trial_name']}: {ext['effect_type']} {ext['value']}")
        print(f"   Classification: {ext['classification']}")
        print(f"   Source: {ext['source_snippet'][:80]}...")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Audit extra extractions")
    parser.add_argument("--sample", type=int, help="Sample size (default: all)")
    parser.add_argument("--output", type=Path, help="Output JSON path")

    args = parser.parse_args()

    if not HAS_EXTRACTOR:
        print("Error: Extractor not available")
        sys.exit(1)

    results = run_audit(args.sample)
    print_audit(results)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved to: {args.output}")


if __name__ == "__main__":
    main()
