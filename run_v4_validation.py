#!/usr/bin/env python3
"""
RCT Extractor v4.0 - Verified Extraction Validation
====================================================

Tests the new verified extraction architecture against all test cases:
1. Original validation set (167 cases)
2. Held-out test set (53 cases)
3. False positive test set (108 cases)

Validates:
- Team-of-Rivals consensus
- Deterministic verification
- Proof-Carrying Numbers
- Fail-closed operation
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.team_of_rivals import team_extract, get_verified_extractions, ConsensusEngine
from src.core.deterministic_verifier import verify_extraction, VerificationLevel
from src.core.verified_extraction_pipeline import (
    verified_extract, VerifiedExtractionPipeline, PipelineStatus,
    generate_verification_report
)
from src.core.proof_carrying_numbers import (
    create_verified_extraction, ProofCarryingExtraction
)

# Import test cases
from data.expanded_validation_v3 import ALL_VALIDATION_CASES as VALIDATION_CASES
from data.held_out_test_set import HELD_OUT_CASES
from data.false_positive_test_cases import NEGATIVE_CASES as FALSE_POSITIVE_CASES


def print_header(title: str):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def test_team_of_rivals():
    """Test Team-of-Rivals extraction"""
    print_header("PILLAR 1: Team-of-Rivals Extraction")

    engine = ConsensusEngine()

    # Test on sample cases
    test_texts = [
        "HR 0.72 (95% CI 0.58-0.89)",
        "odds ratio = 2.15, 95% CI: 1.34 to 3.45",
        "The hazard ratio was 0.83 (0.71-0.97, p=0.02)",
        "RR 1.45 [95% CI 1.12-1.87]",
    ]

    total_extractions = 0
    unanimous = 0
    consensus_reached = 0

    for text in test_texts:
        results = engine.extract_with_consensus(text)
        for r in results:
            total_extractions += 1
            if r.is_unanimous:
                unanimous += 1
            if r.agreement_ratio >= 0.5:
                consensus_reached += 1

    print(f"Sample tests: {len(test_texts)}")
    print(f"Total extractions: {total_extractions}")
    print(f"Unanimous agreement: {unanimous} ({unanimous/total_extractions*100:.1f}%)")
    print(f"Consensus reached (>=50%): {consensus_reached} ({consensus_reached/total_extractions*100:.1f}%)")

    return total_extractions, unanimous


def test_deterministic_verification():
    """Test deterministic verification engine"""
    print_header("PILLAR 2: Deterministic Verification")

    test_cases = [
        # (effect_type, value, ci_lower, ci_upper, expected_level)
        ("HR", 0.72, 0.58, 0.89, VerificationLevel.PROVEN),      # Valid
        ("HR", 0.50, 0.60, 0.80, VerificationLevel.VIOLATED),    # Value outside CI
        ("OR", 2.15, 1.34, 3.45, VerificationLevel.PROVEN),      # Valid
        ("OR", 2.15, 3.45, 1.34, VerificationLevel.VIOLATED),    # CI reversed
        ("MD", -2.5, -4.1, -0.9, VerificationLevel.PROVEN),      # Valid negative
        ("RR", 1.45, 1.12, 1.87, VerificationLevel.PROVEN),      # Valid
    ]

    passed = 0
    for effect_type, value, ci_lower, ci_upper, expected in test_cases:
        result = verify_extraction(effect_type, value, ci_lower, ci_upper)

        if result.overall_level == expected:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"

        print(f"  [{status}] {effect_type}={value}, CI=[{ci_lower},{ci_upper}] -> {result.overall_level.value}")

    print(f"\nDeterministic verification: {passed}/{len(test_cases)} passed")
    return passed, len(test_cases)


def test_proof_carrying_numbers():
    """Test Proof-Carrying Numbers"""
    print_header("PILLAR 3: Proof-Carrying Numbers")

    # Create valid PCN
    pcn = create_verified_extraction(
        effect_type="HR",
        value=0.72,
        ci_lower=0.58,
        ci_upper=0.89,
        source_text="HR 0.72 (95% CI 0.58-0.89)",
        extraction_method="test"
    )

    print(f"Created PCN for HR 0.72 (0.58-0.89)")
    print(f"  Is verified: {pcn.is_fully_verified}")
    print(f"  Point estimate verified: {pcn.point_estimate.is_verified}")
    print(f"  Certificate checks passed: {pcn.master_certificate.checks_passed if pcn.master_certificate else 'N/A'}")

    # Test fail-closed
    invalid_pcn = create_verified_extraction(
        effect_type="HR",
        value=0.50,  # Outside CI
        ci_lower=0.60,
        ci_upper=0.80,
        source_text="HR 0.50 (CI 0.60-0.80)",
        extraction_method="test"
    )

    print(f"\nCreated invalid PCN for HR 0.50 (0.60-0.80)")
    print(f"  Is verified: {invalid_pcn.is_fully_verified}")
    print(f"  Needs review: {invalid_pcn.needs_review}")

    # Test render
    try:
        _ = invalid_pcn.point_estimate.render()
        fail_closed = False
    except Exception:
        fail_closed = True

    print(f"  Fail-closed works: {fail_closed}")

    return 1 if pcn.is_fully_verified and fail_closed else 0


def test_validation_cases():
    """Test on original validation cases"""
    print_header("VALIDATION: Original Test Cases (167)")

    pipeline = VerifiedExtractionPipeline(min_agreement=0.25, require_verification=False)

    detected = 0
    verified = 0
    total = len(VALIDATION_CASES)

    for i, case in enumerate(VALIDATION_CASES):
        text = case.text
        expected_type = case.expected_type
        expected_value = case.expected_value

        results = pipeline.extract(text)

        # Check if expected value was found
        found = False
        found_verified = False

        for r in results:
            if r.effect_type == expected_type:
                if abs(r.value - expected_value) < 0.01:
                    found = True
                    if r.is_usable or r.status in [PipelineStatus.VERIFIED, PipelineStatus.CONSENSUS_ONLY]:
                        found_verified = True
                    break

        if found:
            detected += 1
        if found_verified:
            verified += 1

        # Progress
        if (i + 1) % 50 == 0:
            print(f"  Processed {i+1}/{total}...")

    sensitivity = detected / total * 100
    verified_rate = verified / total * 100

    print(f"\nResults:")
    print(f"  Total cases: {total}")
    print(f"  Detected: {detected} ({sensitivity:.1f}%)")
    print(f"  Verified: {verified} ({verified_rate:.1f}%)")

    return detected, verified, total


def test_held_out_cases():
    """Test on held-out test cases"""
    print_header("VALIDATION: Held-Out Test Cases (53)")

    pipeline = VerifiedExtractionPipeline(min_agreement=0.25, require_verification=False)

    detected = 0
    verified = 0
    total = len(HELD_OUT_CASES)

    for case in HELD_OUT_CASES:
        text = case.text
        expected_type = case.expected_type
        expected_value = case.expected_value

        results = pipeline.extract(text)

        found = False
        found_verified = False

        for r in results:
            if r.effect_type == expected_type:
                if abs(r.value - expected_value) < 0.01:
                    found = True
                    if r.is_usable or r.status in [PipelineStatus.VERIFIED, PipelineStatus.CONSENSUS_ONLY]:
                        found_verified = True
                    break

        if found:
            detected += 1
        if found_verified:
            verified += 1

    sensitivity = detected / total * 100
    verified_rate = verified / total * 100

    print(f"Results:")
    print(f"  Total cases: {total}")
    print(f"  Detected: {detected} ({sensitivity:.1f}%)")
    print(f"  Verified: {verified} ({verified_rate:.1f}%)")

    return detected, verified, total


def test_false_positives():
    """Test on false positive cases"""
    print_header("VALIDATION: False Positive Test Cases (108)")

    pipeline = VerifiedExtractionPipeline(min_agreement=0.5, require_verification=True)

    false_positives = 0
    total = len(FALSE_POSITIVE_CASES)

    categories_with_fp = {}

    for case in FALSE_POSITIVE_CASES:
        text = case.text
        category = case.category

        results = pipeline.extract(text)

        # Any extraction is a false positive for these cases
        if any(r.is_usable for r in results):
            false_positives += 1
            if category not in categories_with_fp:
                categories_with_fp[category] = 0
            categories_with_fp[category] += 1

    fpr = false_positives / total * 100

    print(f"Results:")
    print(f"  Total negative cases: {total}")
    print(f"  False positives: {false_positives} ({fpr:.1f}%)")
    print(f"  Specificity: {100 - fpr:.1f}%")

    if categories_with_fp:
        print(f"\n  Categories with FP: {categories_with_fp}")

    return false_positives, total


def test_pipeline_integration():
    """Test full pipeline integration"""
    print_header("INTEGRATION: Full Pipeline Test")

    text = """
    The primary endpoint showed a significant benefit with treatment:
    hazard ratio 0.68 (95% CI 0.54-0.85, p=0.001). Secondary outcomes
    also favored treatment with OR 0.72 (0.58-0.89) and MD -3.2
    (95% CI -5.1 to -1.3). The absolute risk difference was -8.5%
    (-12.1 to -4.9), corresponding to NNT of 12 (8-20).
    """

    results = verified_extract(text, strict=False)

    print(f"Extracted {len(results)} effect estimates:")
    for r in results:
        status = "VERIFIED" if r.is_usable else "UNVERIFIED"
        ci = f"({r.ci_lower}-{r.ci_upper})" if r.ci_lower and r.ci_upper else ""
        print(f"  [{status}] {r.effect_type} = {r.value} {ci}")
        print(f"           Confidence: {r.confidence:.0%}, Status: {r.status.value}")

    # Generate report
    print("\n" + generate_verification_report(results))

    return len(results)


def main():
    """Run all validations"""
    print("\n" + "=" * 70)
    print("  RCT EXTRACTOR v4.0 - VERIFIED EXTRACTION VALIDATION")
    print("=" * 70)

    # Run tests
    tor_total, tor_unanimous = test_team_of_rivals()
    dv_passed, dv_total = test_deterministic_verification()
    pcn_passed = test_proof_carrying_numbers()

    orig_detected, orig_verified, orig_total = test_validation_cases()
    held_detected, held_verified, held_total = test_held_out_cases()
    fp_count, fp_total = test_false_positives()

    integration_count = test_pipeline_integration()

    # Summary
    print_header("FINAL SUMMARY")

    print("Pillar Tests:")
    print(f"  Team-of-Rivals: {tor_unanimous}/{tor_total} unanimous")
    print(f"  Deterministic Verification: {dv_passed}/{dv_total} passed")
    print(f"  Proof-Carrying Numbers: {'PASSED' if pcn_passed else 'FAILED'}")

    print("\nValidation Results:")
    print(f"  Original (167): {orig_detected} detected ({orig_detected/orig_total*100:.1f}%), {orig_verified} verified")
    print(f"  Held-out (53): {held_detected} detected ({held_detected/held_total*100:.1f}%), {held_verified} verified")
    print(f"  False Positives: {fp_count}/{fp_total} FP ({fp_count/fp_total*100:.1f}% FPR)")

    print("\nOverall Metrics:")
    total_positive = orig_total + held_total
    total_detected = orig_detected + held_detected
    total_verified = orig_verified + held_verified

    print(f"  Combined Sensitivity: {total_detected/total_positive*100:.1f}%")
    print(f"  Combined Verified Rate: {total_verified/total_positive*100:.1f}%")
    print(f"  False Positive Rate: {fp_count/fp_total*100:.1f}%")
    print(f"  Specificity: {(fp_total-fp_count)/fp_total*100:.1f}%")

    print("\n" + "=" * 70)
    print("  VALIDATION COMPLETE")
    print("=" * 70 + "\n")

    # Return success if sensitivity > 80% and FPR < 5%
    success = (total_detected/total_positive > 0.80) and (fp_count/fp_total < 0.05)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
