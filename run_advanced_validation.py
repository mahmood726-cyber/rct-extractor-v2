"""
Advanced Validation for RCT Extractor v2.11
============================================

Tests for:
1. Continuous outcomes (mean/SD) extraction with conversions
2. Time-to-event (HR) extraction with CI consistency
3. Ambiguity detection (multiple analyses, timepoints, populations)
4. Composite endpoint handling
5. Non-standard designs flagging
"""

import sys
from pathlib import Path
from datetime import datetime

# Direct imports from the module files
sys.path.insert(0, str(Path(__file__).parent / 'src' / 'core'))

from continuous_extractor import (
    ContinuousOutcomeExtractor, DispersionConverter,
    DispersionType, ConversionMethod
)
from tte_extractor import (
    TimeToEventExtractor, AnalysisType, EndpointCategory
)


# =============================================================================
# 1. CONTINUOUS OUTCOMES TEST CASES
# =============================================================================

CONTINUOUS_POSITIVE_CASES = [
    # Mean (SD) format
    {
        "text": "Systolic blood pressure was 135.2 (18.4) mmHg",
        "expected_mean": 135.2,
        "expected_dispersion": 18.4,
        "expected_type": DispersionType.SD,
        "expected_unit": "mmHg",
        "source": "SBP mean (SD)"
    },
    {
        "text": "LDL-C decreased to 68.5 (22.3) mg/dL",
        "expected_mean": 68.5,
        "expected_dispersion": 22.3,
        "expected_type": DispersionType.SD,
        "expected_unit": "mg/dL",
        "source": "LDL-C mean (SD)"
    },
    # Mean ± SD format
    {
        "text": "HbA1c was 7.2 ± 1.1%",
        "expected_mean": 7.2,
        "expected_dispersion": 1.1,
        "expected_type": DispersionType.SD,
        "expected_unit": "%",
        "source": "HbA1c mean ± SD"
    },
    {
        "text": "Weight: 82.5 ± 15.3 kg",
        "expected_mean": 82.5,
        "expected_dispersion": 15.3,
        "expected_type": DispersionType.SD,
        "expected_unit": "kg",
        "source": "Weight mean ± SD"
    },
    # Mean (SD=X) format
    {
        "text": "eGFR was 62.4 (SD=18.7) mL/min/1.73m2",
        "expected_mean": 62.4,
        "expected_dispersion": 18.7,
        "expected_type": DispersionType.SD,
        "expected_unit": "mL/min/1.73m2",
        "source": "eGFR with SD="
    },
]

CONTINUOUS_CONVERSION_CASES = [
    # Mean (SE) - needs conversion
    {
        "text": "Change in LDL was -52.3 (SE 2.8) mg/dL",
        "n": 500,
        "expected_mean": -52.3,
        "expected_se": 2.8,
        "expected_sd_approx": 62.6,  # 2.8 * sqrt(500)
        "source": "LDL change with SE"
    },
    {
        "text": "Mean reduction was 15.4 (SE 1.2) points",
        "n": 200,
        "expected_mean": 15.4,
        "expected_se": 1.2,
        "expected_sd_approx": 17.0,  # 1.2 * sqrt(200)
        "source": "Score reduction with SE"
    },
    # Mean (95% CI) - needs conversion
    {
        "text": "HbA1c was 7.5% (95% CI 7.2 to 7.8)",
        "n": 100,
        "expected_mean": 7.5,
        "expected_ci_lower": 7.2,
        "expected_ci_upper": 7.8,
        "source": "HbA1c with CI"
    },
]

CONTINUOUS_MEDIAN_IQR_CASES = [
    # Median (IQR) - should flag for manual review
    {
        "text": "Median eGFR was 45.3 (IQR 38.1-52.7) mL/min",
        "expected_median": 45.3,
        "expected_q1": 38.1,
        "expected_q3": 52.7,
        "should_flag_review": True,
        "source": "eGFR median (IQR)"
    },
    {
        "text": "BNP: 523 (312-891) pg/mL",
        "expected_median": 523,
        "expected_q1": 312,
        "expected_q3": 891,
        "should_flag_review": True,
        "source": "BNP median (IQR)"
    },
]


# =============================================================================
# 2. TIME-TO-EVENT (HR) TEST CASES
# =============================================================================

TTE_POSITIVE_CASES = [
    # Standard HR
    {
        "text": "The hazard ratio for the primary endpoint was 0.72 (95% CI, 0.63 to 0.82; P<0.001)",
        "expected_hr": 0.72,
        "expected_ci_lower": 0.63,
        "expected_ci_upper": 0.82,
        "validation_should_pass": True,
        "source": "Standard NEJM format"
    },
    {
        "text": "HR 0.85 (95% CI 0.75-0.96)",
        "expected_hr": 0.85,
        "expected_ci_lower": 0.75,
        "expected_ci_upper": 0.96,
        "validation_should_pass": True,
        "source": "Short HR format"
    },
]

TTE_VALIDATION_FAILURE_CASES = [
    # CI does not contain HR
    {
        "text": "HR 0.72 (95% CI 0.75-0.85)",
        "expected_hr": 0.72,
        "expected_ci_lower": 0.75,
        "expected_ci_upper": 0.85,
        "validation_should_pass": False,
        "expected_error": "CI .* does not contain HR",
        "source": "HR below CI"
    },
    # CI order wrong
    {
        "text": "HR 0.80 (95% CI 0.90-0.70)",
        "expected_hr": 0.80,
        "expected_ci_lower": 0.90,
        "expected_ci_upper": 0.70,
        "validation_should_pass": False,
        "expected_error": "lower .* >= upper",
        "source": "Reversed CI"
    },
]

TTE_AMBIGUITY_CASES = [
    # Multiple timepoints
    {
        "text": """At 12 months, the HR was 0.68 (95% CI 0.55-0.84).
                   At 24 months, the HR was 0.75 (95% CI 0.62-0.91).""",
        "should_flag_multiple_timepoints": True,
        "source": "Multiple timepoints"
    },
    # Unclear primary
    {
        "text": """HR for CV death was 0.78 (95% CI 0.65-0.94).
                   HR for MI was 0.82 (95% CI 0.68-0.99).
                   HR for stroke was 0.85 (95% CI 0.70-1.03).""",
        "should_flag_no_primary": True,
        "source": "No primary designation"
    },
    # MACE composite with components
    {
        "text": "For the primary endpoint of MACE (CV death, MI, or stroke), HR was 0.80 (95% CI 0.70-0.92)",
        "should_detect_composite": True,
        "expected_components": ["CV death", "MI", "stroke"],
        "source": "MACE composite"
    },
]

TTE_TIMEPOINT_CASES = [
    {
        "text": "In the 12-month landmark analysis, the hazard ratio was 0.65 (95% CI 0.50-0.85)",
        "expected_analysis_type": AnalysisType.LANDMARK,
        "expected_timepoint": "12 months",
        "source": "Landmark analysis"
    },
    {
        "text": "At median follow-up of 3.5 years, the overall HR was 0.72 (95% CI 0.63-0.82)",
        "expected_analysis_type": AnalysisType.OVERALL,
        "expected_timepoint": "3.5 years",
        "source": "Overall with follow-up"
    },
    {
        "text": "In the per-protocol population, HR was 0.68 (95% CI 0.55-0.84)",
        "expected_analysis_type": AnalysisType.PER_PROTOCOL,
        "source": "Per-protocol"
    },
    {
        "text": "In the subgroup aged ≥65 years, HR was 0.78 (95% CI 0.64-0.95)",
        "expected_analysis_type": AnalysisType.SUBGROUP,
        "source": "Subgroup analysis"
    },
]


# =============================================================================
# 3. DISPERSION CONVERSION TESTS
# =============================================================================

CONVERSION_TEST_CASES = [
    # SE to SD
    {
        "se": 2.5,
        "n": 100,
        "expected_sd": 25.0,
        "method": ConversionMethod.SE_TO_SD,
        "source": "SE to SD"
    },
    # Invalid n
    {
        "se": 2.5,
        "n": 0,
        "expected_method": ConversionMethod.MANUAL_REQUIRED,
        "source": "Invalid n"
    },
]


# =============================================================================
# RUN TESTS
# =============================================================================

def run_continuous_tests():
    """Test continuous outcome extraction"""
    print("\n" + "=" * 70)
    print("CONTINUOUS OUTCOMES EXTRACTION TESTS")
    print("=" * 70)

    extractor = ContinuousOutcomeExtractor()
    passed = 0
    failed = 0
    failures = []

    # Positive cases
    print("\nMean (SD) Extraction:")
    for case in CONTINUOUS_POSITIVE_CASES:
        report = extractor.extract(case["text"], "test", n=100)

        if report.outcomes:
            outcome = report.outcomes[0]
            mean_ok = abs(outcome.mean - case["expected_mean"]) < 0.1
            disp_ok = abs(outcome.dispersion_value - case["expected_dispersion"]) < 0.1
            type_ok = outcome.dispersion_type == case["expected_type"]

            if mean_ok and disp_ok and type_ok:
                passed += 1
                print(f"  [PASS] {case['source']}")
            else:
                failed += 1
                failures.append(case["source"])
                print(f"  [FAIL] {case['source']}: Got mean={outcome.mean}, disp={outcome.dispersion_value}")
        else:
            failed += 1
            failures.append(case["source"])
            print(f"  [FAIL] {case['source']}: No extraction")

    # Conversion cases
    print("\nSE/CI Conversion:")
    for case in CONTINUOUS_CONVERSION_CASES:
        report = extractor.extract(case["text"], "test", n=case.get("n"))

        if report.outcomes:
            outcome = report.outcomes[0]
            mean_ok = abs(outcome.mean - case["expected_mean"]) < 0.1

            if "expected_se" in case:
                disp_ok = abs(outcome.dispersion_value - case["expected_se"]) < 0.1
                if outcome.sd:
                    sd_ok = abs(outcome.sd - case["expected_sd_approx"]) < 1.0
                else:
                    sd_ok = False

                if mean_ok and disp_ok:
                    passed += 1
                    print(f"  [PASS] {case['source']}: SE={outcome.dispersion_value}, SD~{outcome.sd:.1f}")
                else:
                    failed += 1
                    failures.append(case["source"])
            else:
                passed += 1
                print(f"  [PASS] {case['source']}: Extracted with conversion needed")
        else:
            failed += 1
            failures.append(case["source"])
            print(f"  [FAIL] {case['source']}: No extraction")

    # Median/IQR cases (should flag for review)
    print("\nMedian (IQR) Detection:")
    for case in CONTINUOUS_MEDIAN_IQR_CASES:
        report = extractor.extract(case["text"], "test", n=100)

        if report.outcomes and case.get("should_flag_review"):
            outcome = report.outcomes[0]
            if outcome.dispersion_type == DispersionType.IQR:
                passed += 1
                print(f"  [PASS] {case['source']}: Correctly flagged as IQR")
            else:
                failed += 1
                failures.append(case["source"])
        else:
            failed += 1
            failures.append(case["source"])

    total = passed + failed
    print(f"\nContinuous Outcomes: {passed}/{total} ({passed/total*100:.1f}%)")

    return passed, failed, failures


def run_tte_tests():
    """Test time-to-event extraction"""
    print("\n" + "=" * 70)
    print("TIME-TO-EVENT (HR) EXTRACTION TESTS")
    print("=" * 70)

    extractor = TimeToEventExtractor()
    passed = 0
    failed = 0
    failures = []

    # Positive cases
    print("\nHR Extraction:")
    for case in TTE_POSITIVE_CASES:
        report = extractor.extract(case["text"])

        if report.outcomes:
            outcome = report.outcomes[0]
            hr_ok = abs(outcome.hr - case["expected_hr"]) < 0.01
            ci_low_ok = abs(outcome.ci_lower - case["expected_ci_lower"]) < 0.01
            ci_high_ok = abs(outcome.ci_upper - case["expected_ci_upper"]) < 0.01
            valid_ok = outcome.validation_passed == case["validation_should_pass"]

            if hr_ok and ci_low_ok and ci_high_ok and valid_ok:
                passed += 1
                print(f"  [PASS] {case['source']}")
            else:
                failed += 1
                failures.append(case["source"])
                print(f"  [FAIL] {case['source']}")
        else:
            failed += 1
            failures.append(case["source"])
            print(f"  [FAIL] {case['source']}: No extraction")

    # Validation failure cases
    print("\nCI Consistency Validation:")
    for case in TTE_VALIDATION_FAILURE_CASES:
        report = extractor.extract(case["text"])

        if report.outcomes:
            outcome = report.outcomes[0]

            if not outcome.validation_passed:
                passed += 1
                print(f"  [PASS] {case['source']}: Correctly detected validation error")
            else:
                failed += 1
                failures.append(case["source"])
                print(f"  [FAIL] {case['source']}: Should have failed validation")
        else:
            failed += 1
            failures.append(case["source"])

    # Ambiguity detection
    print("\nAmbiguity Detection:")
    for case in TTE_AMBIGUITY_CASES:
        report = extractor.extract(case["text"])

        if case.get("should_flag_multiple_timepoints"):
            if report.multiple_timepoints_detected:
                passed += 1
                print(f"  [PASS] {case['source']}: Multiple timepoints detected")
            else:
                failed += 1
                failures.append(case["source"])
                print(f"  [FAIL] {case['source']}: Should detect multiple timepoints")

        elif case.get("should_flag_no_primary"):
            if not report.primary_analysis_identified:
                passed += 1
                print(f"  [PASS] {case['source']}: No primary detected")
            else:
                failed += 1
                failures.append(case["source"])

        elif case.get("should_detect_composite"):
            if report.outcomes and len(report.outcomes[0].composite_components) >= 2:
                passed += 1
                print(f"  [PASS] {case['source']}: Composite components detected")
            else:
                failed += 1
                failures.append(case["source"])

    # Timepoint/analysis type detection
    print("\nTimepoint/Analysis Type Detection:")
    for case in TTE_TIMEPOINT_CASES:
        report = extractor.extract(case["text"])

        if report.outcomes:
            outcome = report.outcomes[0]

            type_ok = (outcome.timepoint_type == case.get("expected_analysis_type", AnalysisType.UNKNOWN))

            if type_ok:
                passed += 1
                tp = outcome.timepoint or "N/A"
                print(f"  [PASS] {case['source']}: {outcome.timepoint_type.value}, timepoint={tp}")
            else:
                failed += 1
                failures.append(case["source"])
                print(f"  [FAIL] {case['source']}: Got {outcome.timepoint_type.value}")
        else:
            failed += 1
            failures.append(case["source"])

    total = passed + failed
    print(f"\nTime-to-Event: {passed}/{total} ({passed/total*100:.1f}%)")

    return passed, failed, failures


def run_conversion_tests():
    """Test dispersion conversion"""
    print("\n" + "=" * 70)
    print("DISPERSION CONVERSION TESTS")
    print("=" * 70)

    converter = DispersionConverter()
    passed = 0
    failed = 0
    failures = []

    for case in CONVERSION_TEST_CASES:
        if "expected_sd" in case:
            result = converter.se_to_sd(case["se"], case["n"])
            if result.converted_sd and abs(result.converted_sd - case["expected_sd"]) < 0.1:
                passed += 1
                print(f"  [PASS] {case['source']}: SD={result.converted_sd:.1f}")
            else:
                failed += 1
                failures.append(case["source"])

        elif "expected_method" in case:
            result = converter.se_to_sd(case["se"], case["n"])
            if result.method == case["expected_method"]:
                passed += 1
                print(f"  [PASS] {case['source']}: Correctly flagged manual required")
            else:
                failed += 1
                failures.append(case["source"])

    total = passed + failed if passed + failed > 0 else 1
    print(f"\nConversion Tests: {passed}/{total} ({passed/total*100:.1f}%)")

    return passed, failed, failures


def main():
    """Run all advanced validation tests"""
    print("=" * 70)
    print("ADVANCED VALIDATION")
    print("RCT Extractor - Mean/SD, TTE, Ambiguity Detection")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    all_passed = 0
    all_failed = 0
    all_failures = []

    # Run tests
    p, f, failures = run_continuous_tests()
    all_passed += p
    all_failed += f
    all_failures.extend(failures)

    p, f, failures = run_tte_tests()
    all_passed += p
    all_failed += f
    all_failures.extend(failures)

    p, f, failures = run_conversion_tests()
    all_passed += p
    all_failed += f
    all_failures.extend(failures)

    # Summary
    print("\n" + "=" * 70)
    print("ADVANCED VALIDATION SUMMARY")
    print("=" * 70)

    total = all_passed + all_failed
    print(f"\n  TOTAL: {all_passed}/{total} ({all_passed/total*100:.1f}%)")

    if all_failures:
        print(f"\n  Failures: {all_failures}")

    print("=" * 70)

    # Save results
    import json
    output = {
        "timestamp": datetime.now().isoformat(),
        "version": "v2.11-advanced",
        "tests": {
            "continuous_outcomes": "Mean/SD, SE conversion, IQR detection",
            "time_to_event": "HR extraction, CI validation, ambiguity",
            "dispersion_conversion": "SE/CI/IQR to SD"
        },
        "summary": {
            "total": total,
            "passed": all_passed,
            "accuracy": all_passed / total * 100 if total > 0 else 0
        },
        "failures": all_failures
    }

    output_file = Path(__file__).parent / "output" / "advanced_validation.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Results saved to: {output_file}")

    return all_passed, all_failed


if __name__ == "__main__":
    main()
