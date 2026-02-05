#!/usr/bin/env python3
"""
RCT Extractor v4.0.1 - Comprehensive Validation with Ablation Studies
======================================================================

Addresses all editorial review requirements:
1. Sensitivity comparison with v3.0
2. False positive rate analysis
3. Ablation studies for each component
4. Calibration metrics (ECE, MCE)
5. Per-extractor accuracy
6. Bootstrap confidence intervals
"""

import sys
import os
import math
import random
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import v3.0 extractor for comparison
from src.core.enhanced_extractor_v3 import EnhancedExtractor

# Import v4.0 components
from src.core.team_of_rivals import (
    PatternExtractor, GrammarExtractor, StateMachineExtractor, ChunkExtractor,
    ConsensusEngine, ExtractorType
)
from src.core.verified_extraction_pipeline import (
    VerifiedExtractionPipeline, PipelineStatus
)
from src.core.deterministic_verifier import verify_extraction, VerificationLevel

# Import test cases
from data.expanded_validation_v3 import ALL_VALIDATION_CASES as VALIDATION_CASES
from data.held_out_test_set import HELD_OUT_CASES
from data.false_positive_test_cases import NEGATIVE_CASES as FALSE_POSITIVE_CASES


def print_header(title: str):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_subheader(title: str):
    """Print subsection header"""
    print("\n" + "-" * 50)
    print(f"  {title}")
    print("-" * 50 + "\n")


# =============================================================================
# V3.0 BASELINE COMPARISON
# =============================================================================

def test_v3_baseline():
    """Test v3.0 extractor as baseline"""
    print_header("BASELINE: v3.0 EnhancedExtractor")

    extractor = EnhancedExtractor()

    # Test on original validation
    detected_orig = 0
    for case in VALIDATION_CASES:
        extractions = extractor.extract(case.text)
        for ext in extractions:
            if ext.effect_type.value == case.expected_type:
                if abs(ext.point_estimate - case.expected_value) < 0.01:
                    detected_orig += 1
                    break

    # Test on held-out
    detected_held = 0
    for case in HELD_OUT_CASES:
        extractions = extractor.extract(case.text)
        for ext in extractions:
            if ext.effect_type.value == case.expected_type:
                if abs(ext.point_estimate - case.expected_value) < 0.01:
                    detected_held += 1
                    break

    # Test false positives
    fp_count = 0
    for case in FALSE_POSITIVE_CASES:
        extractions = extractor.extract(case.text)
        if len(extractions) > 0:
            fp_count += 1

    print(f"Original validation (167): {detected_orig}/167 ({detected_orig/167*100:.1f}%)")
    print(f"Held-out validation (53): {detected_held}/53 ({detected_held/53*100:.1f}%)")
    print(f"False positives: {fp_count}/108 ({fp_count/108*100:.1f}% FPR)")

    return {
        'orig_sens': detected_orig / 167,
        'held_sens': detected_held / 53,
        'fpr': fp_count / 108,
    }


# =============================================================================
# V4.0 PIPELINE TEST
# =============================================================================

def test_v4_pipeline():
    """Test v4.0 verified extraction pipeline"""
    print_header("V4.0.1: Verified Extraction Pipeline")

    # Use V3 primary with pattern agreement required
    pipeline = VerifiedExtractionPipeline(
        min_agreement=0.25,
        require_verification=True,
        require_pattern_agreement=True,
        use_v3_primary=True
    )

    # Test on original validation
    detected_orig = 0
    verified_orig = 0
    for case in VALIDATION_CASES:
        results = pipeline.extract(case.text)
        for r in results:
            if r.effect_type == case.expected_type:
                if abs(r.value - case.expected_value) < 0.01:
                    detected_orig += 1
                    if r.is_usable:
                        verified_orig += 1
                    break

    # Test on held-out
    detected_held = 0
    verified_held = 0
    for case in HELD_OUT_CASES:
        results = pipeline.extract(case.text)
        for r in results:
            if r.effect_type == case.expected_type:
                if abs(r.value - case.expected_value) < 0.01:
                    detected_held += 1
                    if r.is_usable:
                        verified_held += 1
                    break

    # Test false positives
    fp_count = 0
    fp_categories = defaultdict(int)
    for case in FALSE_POSITIVE_CASES:
        results = pipeline.extract(case.text)
        if any(r.is_usable for r in results):
            fp_count += 1
            fp_categories[case.category] += 1

    print(f"Original validation (167):")
    print(f"  Detected: {detected_orig}/167 ({detected_orig/167*100:.1f}%)")
    print(f"  Verified: {verified_orig}/167 ({verified_orig/167*100:.1f}%)")

    print(f"\nHeld-out validation (53):")
    print(f"  Detected: {detected_held}/53 ({detected_held/53*100:.1f}%)")
    print(f"  Verified: {verified_held}/53 ({verified_held/53*100:.1f}%)")

    print(f"\nFalse positives: {fp_count}/108 ({fp_count/108*100:.1f}% FPR)")
    if fp_categories:
        print(f"  Categories: {dict(fp_categories)}")

    return {
        'orig_detected': detected_orig / 167,
        'orig_verified': verified_orig / 167,
        'held_detected': detected_held / 53,
        'held_verified': verified_held / 53,
        'fpr': fp_count / 108,
        'fp_categories': dict(fp_categories),
    }


# =============================================================================
# ABLATION STUDIES
# =============================================================================

def test_individual_extractors():
    """Test each extractor independently"""
    print_header("ABLATION: Individual Extractor Performance")

    # Import V3 wrapper
    from src.core.v3_extractor_wrapper import V3ExtractorWrapper

    extractors = {
        'V3Pattern': V3ExtractorWrapper(),
        'SimplePattern': PatternExtractor(),
        'Grammar': GrammarExtractor(),
        'StateMachine': StateMachineExtractor(),
        'Chunk': ChunkExtractor(),
    }

    results = {}

    for name, extractor in extractors.items():
        print_subheader(f"Extractor: {name}")

        # Test on original validation
        detected = 0
        for case in VALIDATION_CASES:
            try:
                extractions = extractor.extract(case.text)
                for ext in extractions:
                    if ext.effect_type == case.expected_type:
                        if abs(ext.value - case.expected_value) < 0.01:
                            detected += 1
                            break
            except Exception as e:
                pass

        # Test false positives
        fp = 0
        for case in FALSE_POSITIVE_CASES:
            try:
                extractions = extractor.extract(case.text)
                if len(extractions) > 0:
                    fp += 1
            except Exception:
                pass

        sens = detected / 167 * 100
        fpr = fp / 108 * 100

        print(f"  Sensitivity: {detected}/167 ({sens:.1f}%)")
        print(f"  FPR: {fp}/108 ({fpr:.1f}%)")

        results[name] = {'sensitivity': sens, 'fpr': fpr}

    return results


def test_consensus_thresholds():
    """Test different consensus thresholds"""
    print_header("ABLATION: Consensus Threshold Analysis")

    thresholds = [0.25, 0.50, 0.75, 1.0]

    for threshold in thresholds:
        print_subheader(f"Threshold: {threshold:.0%}")

        pipeline = VerifiedExtractionPipeline(
            min_agreement=threshold,
            require_verification=True,
            require_pattern_agreement=True,
            use_v3_primary=True
        )

        # Test on combined validation
        detected = 0
        verified = 0
        total = len(VALIDATION_CASES) + len(HELD_OUT_CASES)

        for case in VALIDATION_CASES:
            results = pipeline.extract(case.text)
            for r in results:
                if r.effect_type == case.expected_type:
                    if abs(r.value - case.expected_value) < 0.01:
                        detected += 1
                        if r.is_usable:
                            verified += 1
                        break

        for case in HELD_OUT_CASES:
            results = pipeline.extract(case.text)
            for r in results:
                if r.effect_type == case.expected_type:
                    if abs(r.value - case.expected_value) < 0.01:
                        detected += 1
                        if r.is_usable:
                            verified += 1
                        break

        # Test FPR
        fp = 0
        for case in FALSE_POSITIVE_CASES:
            results = pipeline.extract(case.text)
            if any(r.is_usable for r in results):
                fp += 1

        print(f"  Sensitivity (detected): {detected}/{total} ({detected/total*100:.1f}%)")
        print(f"  Sensitivity (verified): {verified}/{total} ({verified/total*100:.1f}%)")
        print(f"  FPR: {fp}/108 ({fp/108*100:.1f}%)")


def test_pattern_agreement_impact():
    """Test impact of requiring Pattern extractor agreement"""
    print_header("ABLATION: Pattern Agreement Requirement")

    for require_pattern in [True, False]:
        print_subheader(f"Require Pattern Agreement: {require_pattern}")

        pipeline = VerifiedExtractionPipeline(
            min_agreement=0.25,
            require_verification=True,
            require_pattern_agreement=require_pattern,
            use_v3_primary=True
        )

        # Test on combined validation
        verified = 0
        total = len(VALIDATION_CASES) + len(HELD_OUT_CASES)

        for case in list(VALIDATION_CASES) + list(HELD_OUT_CASES):
            results = pipeline.extract(case.text)
            for r in results:
                if r.effect_type == case.expected_type:
                    if abs(r.value - case.expected_value) < 0.01:
                        if r.is_usable:
                            verified += 1
                        break

        # Test FPR
        fp = 0
        for case in FALSE_POSITIVE_CASES:
            results = pipeline.extract(case.text)
            if any(r.is_usable for r in results):
                fp += 1

        print(f"  Sensitivity (verified): {verified}/{total} ({verified/total*100:.1f}%)")
        print(f"  FPR: {fp}/108 ({fp/108*100:.1f}%)")


# =============================================================================
# CALIBRATION METRICS
# =============================================================================

def calculate_calibration():
    """Calculate calibration metrics (ECE, MCE)"""
    print_header("CALIBRATION: Expected Calibration Error")

    pipeline = VerifiedExtractionPipeline(
        min_agreement=0.25,
        require_verification=True,
        require_pattern_agreement=True,
        use_v3_primary=True
    )

    # Collect predictions and outcomes
    predictions = []  # (confidence, is_correct)

    for case in list(VALIDATION_CASES) + list(HELD_OUT_CASES):
        results = pipeline.extract(case.text)
        for r in results:
            if r.effect_type == case.expected_type:
                is_correct = abs(r.value - case.expected_value) < 0.01
                predictions.append((r.confidence, is_correct))
                break

    if not predictions:
        print("No predictions to calibrate")
        return

    # Calculate ECE with 10 bins
    n_bins = 10
    bins = [[] for _ in range(n_bins)]

    for conf, correct in predictions:
        bin_idx = min(int(conf * n_bins), n_bins - 1)
        bins[bin_idx].append((conf, correct))

    ece = 0.0
    mce = 0.0
    total = len(predictions)

    print(f"{'Bin':<10} {'Count':<8} {'Avg Conf':<12} {'Accuracy':<12} {'|Diff|':<10}")
    print("-" * 52)

    for i, bin_data in enumerate(bins):
        if len(bin_data) == 0:
            continue

        avg_conf = sum(c for c, _ in bin_data) / len(bin_data)
        accuracy = sum(1 for _, correct in bin_data if correct) / len(bin_data)
        diff = abs(avg_conf - accuracy)

        ece += (len(bin_data) / total) * diff
        mce = max(mce, diff)

        bin_range = f"{i/n_bins:.1f}-{(i+1)/n_bins:.1f}"
        print(f"{bin_range:<10} {len(bin_data):<8} {avg_conf:<12.3f} {accuracy:<12.3f} {diff:<10.3f}")

    print("-" * 52)
    print(f"\nExpected Calibration Error (ECE): {ece:.4f}")
    print(f"Maximum Calibration Error (MCE): {mce:.4f}")

    return {'ece': ece, 'mce': mce}


# =============================================================================
# BOOTSTRAP CONFIDENCE INTERVALS
# =============================================================================

def bootstrap_confidence_intervals(n_bootstrap: int = 1000):
    """Calculate bootstrap 95% CIs for sensitivity and specificity"""
    print_header("BOOTSTRAP: 95% Confidence Intervals")

    pipeline = VerifiedExtractionPipeline(
        min_agreement=0.25,
        require_verification=True,
        require_pattern_agreement=True,
        use_v3_primary=True
    )

    # Collect results
    positive_results = []  # (detected, verified) for each positive case
    negative_results = []  # (is_fp) for each negative case

    all_positive = list(VALIDATION_CASES) + list(HELD_OUT_CASES)

    for case in all_positive:
        results = pipeline.extract(case.text)
        detected = False
        verified = False
        for r in results:
            if r.effect_type == case.expected_type:
                if abs(r.value - case.expected_value) < 0.01:
                    detected = True
                    verified = r.is_usable
                    break
        positive_results.append((detected, verified))

    for case in FALSE_POSITIVE_CASES:
        results = pipeline.extract(case.text)
        is_fp = any(r.is_usable for r in results)
        negative_results.append(is_fp)

    # Bootstrap
    random.seed(42)
    sens_detected = []
    sens_verified = []
    specificities = []

    for _ in range(n_bootstrap):
        # Sample positive cases with replacement
        pos_sample = random.choices(positive_results, k=len(positive_results))
        detected = sum(1 for d, v in pos_sample if d)
        verified = sum(1 for d, v in pos_sample if v)
        sens_detected.append(detected / len(pos_sample))
        sens_verified.append(verified / len(pos_sample))

        # Sample negative cases with replacement
        neg_sample = random.choices(negative_results, k=len(negative_results))
        fp = sum(1 for is_fp in neg_sample if is_fp)
        specificities.append(1 - fp / len(neg_sample))

    # Calculate CIs
    def ci_95(values):
        sorted_vals = sorted(values)
        lower = sorted_vals[int(0.025 * len(sorted_vals))]
        upper = sorted_vals[int(0.975 * len(sorted_vals))]
        mean = sum(values) / len(values)
        return mean, lower, upper

    det_mean, det_lower, det_upper = ci_95(sens_detected)
    ver_mean, ver_lower, ver_upper = ci_95(sens_verified)
    spec_mean, spec_lower, spec_upper = ci_95(specificities)

    print(f"Sensitivity (detected): {det_mean*100:.1f}% (95% CI: {det_lower*100:.1f}% - {det_upper*100:.1f}%)")
    print(f"Sensitivity (verified): {ver_mean*100:.1f}% (95% CI: {ver_lower*100:.1f}% - {ver_upper*100:.1f}%)")
    print(f"Specificity: {spec_mean*100:.1f}% (95% CI: {spec_lower*100:.1f}% - {spec_upper*100:.1f}%)")

    return {
        'sens_detected': (det_mean, det_lower, det_upper),
        'sens_verified': (ver_mean, ver_lower, ver_upper),
        'specificity': (spec_mean, spec_lower, spec_upper),
    }


# =============================================================================
# COMPARISON TABLE
# =============================================================================

def print_comparison_table(v3_results: dict, v4_results: dict):
    """Print side-by-side comparison"""
    print_header("COMPARISON: v3.0 vs v4.0.1")

    print(f"{'Metric':<30} {'v3.0':<15} {'v4.0.1':<15} {'Change':<15}")
    print("-" * 75)

    # Sensitivity (Original)
    v3_orig = v3_results['orig_sens'] * 100
    v4_orig = v4_results['orig_verified'] * 100
    change = v4_orig - v3_orig
    print(f"{'Sensitivity (Original)':<30} {v3_orig:>12.1f}% {v4_orig:>12.1f}% {change:>+12.1f}%")

    # Sensitivity (Held-out)
    v3_held = v3_results['held_sens'] * 100
    v4_held = v4_results['held_verified'] * 100
    change = v4_held - v3_held
    print(f"{'Sensitivity (Held-out)':<30} {v3_held:>12.1f}% {v4_held:>12.1f}% {change:>+12.1f}%")

    # Combined
    v3_comb = (v3_results['orig_sens'] * 167 + v3_results['held_sens'] * 53) / 220 * 100
    v4_comb = (v4_results['orig_verified'] * 167 + v4_results['held_verified'] * 53) / 220 * 100
    change = v4_comb - v3_comb
    print(f"{'Sensitivity (Combined)':<30} {v3_comb:>12.1f}% {v4_comb:>12.1f}% {change:>+12.1f}%")

    # FPR
    v3_fpr = v3_results['fpr'] * 100
    v4_fpr = v4_results['fpr'] * 100
    change = v4_fpr - v3_fpr
    print(f"{'False Positive Rate':<30} {v3_fpr:>12.1f}% {v4_fpr:>12.1f}% {change:>+12.1f}%")

    # Specificity
    v3_spec = (1 - v3_results['fpr']) * 100
    v4_spec = (1 - v4_results['fpr']) * 100
    change = v4_spec - v3_spec
    print(f"{'Specificity':<30} {v3_spec:>12.1f}% {v4_spec:>12.1f}% {change:>+12.1f}%")

    print("-" * 75)

    # Assessment
    print("\nAssessment:")
    if v4_comb >= 95:
        print("  [PASS] Sensitivity >= 95%")
    else:
        print(f"  [FAIL] Sensitivity {v4_comb:.1f}% < 95%")

    if v4_fpr <= 2:
        print("  [PASS] FPR <= 2%")
    else:
        print(f"  [FAIL] FPR {v4_fpr:.1f}% > 2%")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run comprehensive validation"""
    print("\n" + "=" * 70)
    print("  RCT EXTRACTOR v4.0.1 - COMPREHENSIVE VALIDATION")
    print("  (Addresses Editorial Review Requirements)")
    print("=" * 70)

    # Run all tests
    v3_results = test_v3_baseline()
    v4_results = test_v4_pipeline()

    print_comparison_table(v3_results, v4_results)

    # Ablation studies
    extractor_results = test_individual_extractors()
    test_consensus_thresholds()
    test_pattern_agreement_impact()

    # Calibration
    calibration = calculate_calibration()

    # Bootstrap CIs
    bootstrap_results = bootstrap_confidence_intervals()

    # Final summary
    print_header("FINAL SUMMARY")

    combined_sens = (v4_results['orig_verified'] * 167 + v4_results['held_verified'] * 53) / 220 * 100
    fpr = v4_results['fpr'] * 100

    print(f"Combined Sensitivity: {combined_sens:.1f}%")
    print(f"False Positive Rate: {fpr:.1f}%")
    print(f"Specificity: {100-fpr:.1f}%")
    if calibration:
        print(f"ECE: {calibration['ece']:.4f}")
        print(f"MCE: {calibration['mce']:.4f}")

    print("\n" + "=" * 70)
    print("  VALIDATION COMPLETE")
    print("=" * 70 + "\n")

    # Return success if meets targets
    success = combined_sens >= 95 and fpr <= 2
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
