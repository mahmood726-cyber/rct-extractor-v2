"""
Tests for Advanced Validator v2.13
==================================

Tests:
1. SE/SD confusion detection
2. Statistical consistency validation
3. Timepoint priority scoring
4. Multi-arm trial detection
5. Additional effect types (sHR, WR, RMST, RD, DOR, LR)
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src' / 'core'))

from advanced_validator import (
    SESDConfusionDetector,
    StatisticalConsistencyValidator,
    TimepointPriorityScorer,
    MultiArmTrialDetector,
    extract_additional_effects,
    ValidationSeverity
)


def test_se_sd_confusion():
    """Test SE/SD confusion detection"""
    print("\n" + "=" * 60)
    print("SE/SD CONFUSION DETECTION TESTS")
    print("=" * 60)

    detector = SESDConfusionDetector()
    passed = 0
    total = 0

    cases = [
        # (mean, reported_sd, n, outcome_type, should_flag)
        # Cases where SE is likely reported as SD
        {"mean": 100, "sd": 2, "n": 500, "type": "ldl", "should_flag": True,
         "desc": "LDL mean=100, 'SD'=2, n=500 - likely SE"},

        {"mean": 7.5, "sd": 0.08, "n": 300, "type": "hba1c", "should_flag": True,
         "desc": "HbA1c mean=7.5, 'SD'=0.08 - likely SE"},

        {"mean": 140, "sd": 1.5, "n": 400, "type": "sbp", "should_flag": True,
         "desc": "SBP mean=140, 'SD'=1.5 - likely SE"},

        # Cases where SD is plausible
        {"mean": 100, "sd": 25, "n": 500, "type": "ldl", "should_flag": False,
         "desc": "LDL mean=100, SD=25 - plausible SD"},

        {"mean": 7.5, "sd": 1.2, "n": 300, "type": "hba1c", "should_flag": False,
         "desc": "HbA1c mean=7.5, SD=1.2 - plausible SD"},

        {"mean": 140, "sd": 18, "n": 400, "type": "sbp", "should_flag": False,
         "desc": "SBP mean=140, SD=18 - plausible SD"},

        # Edge cases
        {"mean": 80, "sd": 0.3, "n": 1000, "type": "weight", "should_flag": True,
         "desc": "Weight mean=80, 'SD'=0.3 - likely SE with large n"},

        {"mean": 500, "sd": 300, "n": 100, "type": "bnp", "should_flag": False,
         "desc": "BNP mean=500, SD=300 - high variability expected"},
    ]

    for case in cases:
        total += 1
        result = detector.detect_confusion(
            case["mean"], case["sd"], case["n"], case["type"]
        )

        # Check if SE_AS_SD warning was raised
        has_flag = any(i.code == "SE_AS_SD" for i in result.issues)

        if has_flag == case["should_flag"]:
            passed += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(f"  [{status}] {case['desc']}")
        if has_flag:
            issue = next(i for i in result.issues if i.code == "SE_AS_SD")
            print(f"         Suggested SD: {issue.corrected_value:.2f}")

    print(f"\nSE/SD Detection: {passed}/{total} ({passed/total*100:.1f}%)")
    return passed, total


def test_statistical_consistency():
    """Test statistical consistency validation"""
    print("\n" + "=" * 60)
    print("STATISTICAL CONSISTENCY TESTS")
    print("=" * 60)

    validator = StatisticalConsistencyValidator()
    passed = 0
    total = 0

    cases = [
        # Valid cases
        {"hr": 0.75, "ci_l": 0.65, "ci_u": 0.86, "p": 0.001, "valid": True,
         "desc": "HR 0.75 (0.65-0.86), p=0.001 - valid"},

        {"hr": 1.02, "ci_l": 0.90, "ci_u": 1.15, "p": 0.75, "valid": True,
         "desc": "HR 1.02 (0.90-1.15), p=0.75 - non-significant, valid"},

        # Invalid cases
        {"hr": 0.50, "ci_l": 0.60, "ci_u": 0.70, "p": 0.01, "valid": False,
         "desc": "HR 0.50 outside CI (0.60-0.70) - invalid"},

        {"hr": 0.75, "ci_l": 0.86, "ci_u": 0.65, "p": 0.01, "valid": False,
         "desc": "CI reversed (0.86-0.65) - invalid"},

        # P-value/CI mismatch (warning but still valid)
        {"hr": 0.75, "ci_l": 0.65, "ci_u": 1.10, "p": 0.01, "valid": True,
         "desc": "P<0.05 but CI crosses 1.0 - warning"},

        {"hr": 0.85, "ci_l": 0.70, "ci_u": 0.95, "p": 0.15, "valid": True,
         "desc": "P=0.15 but CI doesn't cross 1.0 - warning"},
    ]

    for case in cases:
        total += 1
        result = validator.validate_hr_consistency(
            case["hr"], case["ci_l"], case["ci_u"], case.get("p")
        )

        if result.is_valid == case["valid"]:
            passed += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(f"  [{status}] {case['desc']}")
        if result.issues:
            for issue in result.issues:
                print(f"         {issue.severity.value}: {issue.code}")

    print(f"\nStatistical Consistency: {passed}/{total} ({passed/total*100:.1f}%)")
    return passed, total


def test_timepoint_priority():
    """Test timepoint priority scoring"""
    print("\n" + "=" * 60)
    print("TIMEPOINT PRIORITY SCORING TESTS")
    print("=" * 60)

    scorer = TimepointPriorityScorer()
    passed = 0
    total = 0

    # Test individual scoring
    cases = [
        {"tp": "24 months", "ctx": "The primary endpoint at 24 months showed...",
         "min_score": 10, "desc": "Primary endpoint at 24 months"},

        {"tp": "12 months", "ctx": "At the interim analysis at 12 months...",
         "min_score": -2, "desc": "Interim analysis (should be negative)"},

        {"tp": "36 months", "ctx": "The final analysis at 36 months demonstrated...",
         "min_score": 8, "desc": "Final analysis at 36 months"},

        {"tp": "6 months", "ctx": "At 6 months, the exploratory endpoint...",
         "min_score": 2, "desc": "Exploratory endpoint"},
    ]

    for case in cases:
        total += 1
        score, explanation = scorer.score_timepoint(case["tp"], case["ctx"])

        if score >= case["min_score"]:
            passed += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(f"  [{status}] {case['desc']}: score={score}")

    # Test ranking
    total += 1
    timepoints = [
        ("12 months", "At the interim analysis at 12 months"),
        ("24 months", "The primary endpoint at 24 months showed"),
        ("36 months", "At 36 months secondary endpoint"),
    ]

    ranked = scorer.rank_timepoints(timepoints)

    # Primary should be first
    if ranked[0][0] == "24 months":
        passed += 1
        print(f"  [PASS] Ranking: primary endpoint ranked first")
    else:
        print(f"  [FAIL] Ranking: expected '24 months' first, got '{ranked[0][0]}'")

    print(f"         Ranked order: {[r[0] for r in ranked]}")

    print(f"\nTimepoint Priority: {passed}/{total} ({passed/total*100:.1f}%)")
    return passed, total


def test_multiarm_detection():
    """Test multi-arm trial detection"""
    print("\n" + "=" * 60)
    print("MULTI-ARM TRIAL DETECTION TESTS")
    print("=" * 60)

    detector = MultiArmTrialDetector()
    passed = 0
    total = 0

    cases = [
        {
            "text": "Drug A 10mg vs Drug B vs placebo: Drug A showed HR 0.75, Drug B showed HR 0.82",
            "is_multiarm": True,
            "min_arms": 3,
            "desc": "3-arm trial (Drug A, Drug B, placebo)"
        },
        {
            "text": "Treatment vs control: HR 0.75 (95% CI 0.65-0.86)",
            "is_multiarm": False,
            "min_arms": 2,
            "desc": "2-arm trial (not multi-arm)"
        },
        {
            "text": "For Drug A versus placebo, the hazard ratio was 0.70. For Drug B versus placebo, HR was 0.82.",
            "is_multiarm": True,
            "min_arms": 3,
            "desc": "Multiple comparisons to common control"
        },
    ]

    for case in cases:
        total += 1
        result = detector.detect(case["text"])

        arm_check = len(result.arms) >= case["min_arms"]
        multiarm_check = result.is_multiarm == case["is_multiarm"]

        if arm_check and multiarm_check:
            passed += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(f"  [{status}] {case['desc']}")
        print(f"         Arms found: {result.arms}")
        print(f"         Reference: {result.reference_arm}")

    print(f"\nMulti-arm Detection: {passed}/{total} ({passed/total*100:.1f}%)")
    return passed, total


def test_additional_effects():
    """Test additional effect type extraction"""
    print("\n" + "=" * 60)
    print("ADDITIONAL EFFECT TYPE TESTS")
    print("=" * 60)

    passed = 0
    total = 0

    cases = [
        # Subdistribution HR (competing risks)
        {"text": "The subdistribution hazard ratio was 0.72 (95% CI 0.58-0.89)",
         "type": "sHR", "value": 0.72, "desc": "Subdistribution HR"},

        {"text": "sHR 0.65 (0.52-0.81) for the competing risks analysis",
         "type": "sHR", "value": 0.65, "desc": "sHR abbreviation"},

        # Win Ratio
        {"text": "The win ratio was 1.28 (95% CI 1.14-1.44)",
         "type": "WR", "value": 1.28, "desc": "Win Ratio"},

        {"text": "WR 1.35 (1.18-1.54) favoring treatment",
         "type": "WR", "value": 1.35, "desc": "WR abbreviation"},

        # RMST difference
        {"text": "RMST difference 2.3 months (95% CI 1.1-3.5)",
         "type": "RMST", "value": 2.3, "desc": "RMST difference"},

        # Risk Difference
        {"text": "The risk difference was -5.2% (95% CI -8.1 to -2.3)",
         "type": "RD", "value": -5.2, "desc": "Risk Difference (negative)"},

        {"text": "Absolute risk reduction 3.5% (1.2-5.8)",
         "type": "RD", "value": 3.5, "desc": "Absolute risk reduction"},

        # Diagnostic OR
        {"text": "The diagnostic odds ratio was 12.5 (95% CI 8.2-19.0)",
         "type": "DOR", "value": 12.5, "desc": "Diagnostic Odds Ratio"},

        # Likelihood Ratio
        {"text": "Positive likelihood ratio 5.2 (3.8-7.1)",
         "type": "LR", "value": 5.2, "desc": "Likelihood Ratio"},

        # Correlation
        {"text": "Pearson's r = 0.65 (95% CI 0.52-0.75)",
         "type": "r", "value": 0.65, "desc": "Correlation coefficient"},
    ]

    for case in cases:
        total += 1
        results = extract_additional_effects(case["text"])

        # Find matching result
        found = False
        for r in results:
            if r['type'] == case['type'] and abs(r['effect_size'] - case['value']) < 0.01:
                found = True
                break

        if found:
            passed += 1
            print(f"  [PASS] {case['desc']}: {case['type']}={case['value']}")
        else:
            print(f"  [FAIL] {case['desc']}: expected {case['type']}={case['value']}")
            if results:
                print(f"         Found: {results}")
            else:
                print(f"         No results extracted")

    print(f"\nAdditional Effects: {passed}/{total} ({passed/total*100:.1f}%)")
    return passed, total


def main():
    """Run all advanced validator tests"""
    print("=" * 70)
    print("ADVANCED VALIDATOR TESTS v2.13")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    all_passed = 0
    all_total = 0

    # Run all test suites
    p, t = test_se_sd_confusion()
    all_passed += p
    all_total += t

    p, t = test_statistical_consistency()
    all_passed += p
    all_total += t

    p, t = test_timepoint_priority()
    all_passed += p
    all_total += t

    p, t = test_multiarm_detection()
    all_passed += p
    all_total += t

    p, t = test_additional_effects()
    all_passed += p
    all_total += t

    # Summary
    print("\n" + "=" * 70)
    print("ADVANCED VALIDATOR SUMMARY")
    print("=" * 70)
    print(f"\n  TOTAL: {all_passed}/{all_total} ({all_passed/all_total*100:.1f}%)")
    print("=" * 70)

    # Save results
    import json
    output = {
        "timestamp": datetime.now().isoformat(),
        "version": "v2.13-advanced-validator",
        "summary": {
            "total": all_total,
            "passed": all_passed,
            "accuracy": all_passed / all_total * 100
        }
    }

    output_file = Path(__file__).parent / "output" / "advanced_validator_tests.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return all_passed, all_total


if __name__ == "__main__":
    main()
