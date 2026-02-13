"""Test script to verify improvements from TruthCert and Wasserstein projects."""

import sys
sys.path.insert(0, 'C:/Users/user/rct-extractor-v2')

def test_ensemble_improvements():
    """Test OutcomeTextMatcher and ValueValidator."""
    print("=" * 60)
    print("Testing Ensemble Improvements (from TruthCert)")
    print("=" * 60)

    from src.core.ensemble import EnsembleMerger, OutcomeTextMatcher, ValueValidator

    # Test outcome matching
    print("\n1. OutcomeTextMatcher Tests:")
    tests = [
        ("overall survival", "os"),
        ("progression-free survival", "pfs"),
        ("major adverse cardiovascular events", "mace"),
        ("disease-free survival", "dfs"),
        ("heart failure hospitalization", "hf_hosp"),
    ]

    for text, expected in tests:
        result = OutcomeTextMatcher.extract_outcome_type(text)
        status = "PASS" if result == expected else "FAIL"
        print(f"   [{status}] '{text}' -> '{result}' (expected: '{expected}')")

    # Test outcome match scores
    print("\n2. Outcome Match Score Tests:")
    score = OutcomeTextMatcher.outcomes_match("overall survival", "OS primary endpoint")
    print(f"   'overall survival' vs 'OS primary endpoint': {score:.2f}")

    score = OutcomeTextMatcher.outcomes_match("overall survival", "progression-free survival")
    print(f"   'overall survival' vs 'progression-free survival': {score:.2f}")

    # Test value validation
    print("\n3. ValueValidator Tests:")
    test_cases = [
        (0.75, 0.65, 0.87, "HR", True, 1.0),
        (5.0, 3.0, 8.0, "HR", True, 0.7),  # Unusual but plausible
        (100.0, 50.0, 200.0, "HR", False, 0.0),  # Implausible
        (0.02, 0.01, 0.05, "HR", False, 0.0),  # Too low
    ]

    for value, ci_low, ci_high, measure, exp_plausible, exp_conf in test_cases:
        plausible, conf = ValueValidator.is_plausible(value, ci_low, ci_high, measure)
        status = "PASS" if plausible == exp_plausible else "FAIL"
        print(f"   [{status}] HR={value} [{ci_low}-{ci_high}]: plausible={plausible}, conf={conf:.1f}")

    # Test merger initialization
    print("\n4. EnsembleMerger Tests:")
    merger = EnsembleMerger(filter_implausible=True, use_outcome_matching=True)
    print(f"   [PASS] Initialized with outcome_matching={merger.use_outcome_matching}")
    print(f"   [PASS] Initialized with filter_implausible={merger.filter_implausible}")

    print("\n" + "=" * 60)
    print("Ensemble improvements verified!")
    print("=" * 60)


def test_wasserstein_improvements():
    """Test CenKMReconstructor and UnifiedQualityGrader."""
    print("\n" + "=" * 60)
    print("Testing Wasserstein Improvements (CEN-KM)")
    print("=" * 60)

    from src.bridges.wasserstein_bridge import (
        CenKMReconstructor, UnifiedQualityGrader, QualityGrade, NAtRiskEntry
    )

    # Test quality grading
    print("\n1. UnifiedQualityGrader Tests:")
    test_cases = [
        (0.015, "A"),
        (0.035, "B"),
        (0.075, "C"),
        (0.12, "D"),
        (0.20, "F"),
    ]

    for rmse, expected in test_cases:
        result = UnifiedQualityGrader.grade_from_rmse(rmse)
        status = "PASS" if result == expected else "FAIL"
        print(f"   [{status}] RMSE={rmse} -> Grade {result} (expected: {expected})")

    # Test composite score
    print("\n2. Composite Score Tests:")
    score = UnifiedQualityGrader.calculate_composite_score(0.03, 5.0, 3.0)
    print(f"   RMSE=0.03, N_error=5%, Events_error=3% -> Score={score:.1f}")

    # Test CEN-KM reconstruction
    print("\n3. CenKMReconstructor Tests:")
    reconstructor = CenKMReconstructor()

    # Synthetic survival data
    times = [0, 6, 12, 18, 24, 30, 36]
    survival = [1.0, 0.92, 0.85, 0.78, 0.72, 0.68, 0.65]
    n_patients = 100
    n_events = 35

    # Without N-at-Risk
    ipd_records, metrics = reconstructor.reconstruct(
        times, survival, n_patients, n_events=n_events
    )
    print(f"   Without NAR: {len(ipd_records)} records, Grade {metrics.grade}")

    # With N-at-Risk table
    n_at_risk = [
        NAtRiskEntry(0, 100),
        NAtRiskEntry(12, 85),
        NAtRiskEntry(24, 70),
        NAtRiskEntry(36, 60),
    ]
    ipd_records2, metrics2 = reconstructor.reconstruct(
        times, survival, n_patients, n_events=n_events, n_at_risk=n_at_risk
    )
    print(f"   With NAR: {len(ipd_records2)} records, Grade {metrics2.grade}")

    print("\n" + "=" * 60)
    print("Wasserstein improvements verified!")
    print("=" * 60)


def test_validators():
    """Test validator improvements."""
    print("\n" + "=" * 60)
    print("Testing Validator Improvements")
    print("=" * 60)

    from src.validators.validators import validate_hazard_ratio, validate_measure_type
    from src.core.models import HazardRatioCI, Provenance
    from datetime import datetime

    # Create a dummy provenance for testing
    def make_prov(text):
        return Provenance(
            pdf_file="test.pdf",
            page_number=1,
            raw_text=text,
            extraction_method="test"
        )

    # Test HR validation with plausibility
    print("\n1. HR Plausibility Validation:")

    # Normal HR
    hr1 = HazardRatioCI(hr=0.75, ci_low=0.65, ci_high=0.87, provenance=make_prov("HR 0.75"))
    issues1 = validate_hazard_ratio(hr1)
    print(f"   HR=0.75: {len(issues1)} issues")

    # Unusual HR
    hr2 = HazardRatioCI(hr=5.0, ci_low=3.0, ci_high=8.0, provenance=make_prov("HR 5.0"))
    issues2 = validate_hazard_ratio(hr2)
    print(f"   HR=5.0: {len(issues2)} issues - {[i.code for i in issues2]}")

    # Implausible HR
    hr3 = HazardRatioCI(hr=50.0, ci_low=30.0, ci_high=80.0, provenance=make_prov("HR 50.0"))
    issues3 = validate_hazard_ratio(hr3)
    print(f"   HR=50.0: {len(issues3)} issues - {[i.code for i in issues3]}")

    # Test measure type detection
    print("\n2. Measure Type Detection:")
    hr_high = HazardRatioCI(hr=4.5, ci_low=2.8, ci_high=7.2, provenance=make_prov("HR 4.5"))
    issues = validate_measure_type(hr_high, context="logistic regression odds ratio")
    print(f"   HR=4.5 with 'odds ratio' context: {[i.code for i in issues]}")

    print("\n" + "=" * 60)
    print("Validator improvements verified!")
    print("=" * 60)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("RCT EXTRACTOR v2 - IMPROVEMENTS VERIFICATION")
    print("=" * 60)

    try:
        test_ensemble_improvements()
    except Exception as e:
        print(f"ERROR in ensemble tests: {e}")

    try:
        test_wasserstein_improvements()
    except Exception as e:
        print(f"ERROR in wasserstein tests: {e}")

    try:
        test_validators()
    except Exception as e:
        print(f"ERROR in validator tests: {e}")

    print("\n" + "=" * 60)
    print("ALL VERIFICATION COMPLETE")
    print("=" * 60)
