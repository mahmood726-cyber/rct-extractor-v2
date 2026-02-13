"""
Provenance Metadata Tests for RCT Extractor v2.16
=================================================

Tests the provenance extraction capabilities.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add paths
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir / 'src' / 'core'))

from provenance_extractor import (
    ProvenanceExtractor,
    AnalysisPopulation,
    EndpointType,
    format_provenance
)


def run_tests():
    """Run provenance extraction tests"""
    print("=" * 70)
    print("PROVENANCE EXTRACTOR TESTS v2.16")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    extractor = ProvenanceExtractor()
    tests_passed = 0
    tests_total = 0

    # Test cases
    test_cases = [
        # Test 1: Basic HR with comparison
        {
            "text": """In the DAPA-HF trial, dapagliflozin vs placebo showed a
hazard ratio of 0.74 (95% CI, 0.65 to 0.85; P<0.001) for the primary endpoint
of cardiovascular death or hospitalization for heart failure in the
intention-to-treat population at median follow-up of 18.2 months.""",
            "match_start": 71,
            "match_end": 120,
            "expected": {
                "population": AnalysisPopulation.ITT,
                "endpoint_type": EndpointType.PRIMARY,
                "has_comparison": True,
                "treatment_arm": "Dapagliflozin",
            }
        },
        # Test 2: Per-protocol analysis
        {
            "text": """In the per-protocol analysis, the secondary endpoint of
all-cause mortality showed HR 0.83 (0.71-0.97). This was adjusted for
baseline covariates including age, sex, and diabetes status.""",
            "match_start": 60,
            "match_end": 90,
            "expected": {
                "population": AnalysisPopulation.PER_PROTOCOL,
                "endpoint_type": EndpointType.SECONDARY,
                "is_adjusted": True,
            }
        },
        # Test 3: Subgroup analysis
        {
            "text": """In the subgroup analysis stratified by diabetes status,
patients with diabetes showed HR 0.65 (0.52-0.81), while those without
diabetes showed HR 0.78 (0.64-0.95). P for interaction = 0.12.""",
            "match_start": 60,
            "match_end": 90,
            "expected": {
                "is_subgroup": True,
            }
        },
        # Test 4: Timepoint extraction
        {
            "text": """At week 52, the primary endpoint showed significant
improvement with OR 2.3 (95% CI 1.5-3.4) in the modified ITT population.
Mean follow-up was 12.5 months.""",
            "match_start": 50,
            "match_end": 80,
            "expected": {
                "population": AnalysisPopulation.MITT,
                "has_timepoint": True,
            }
        },
        # Test 5: Safety endpoint
        {
            "text": """The safety analysis showed serious adverse events occurred
in 12.5% vs 10.2% (OR 1.25; 95% CI 0.98-1.60) in the safety population.
Major bleeding: HR 1.70 (1.40-2.05).""",
            "match_start": 80,
            "match_end": 120,
            "expected": {
                "population": AnalysisPopulation.SAFETY,
                "endpoint_type": EndpointType.SAFETY,
            }
        },
        # Test 6: Pembrolizumab vs chemotherapy
        {
            "text": """In KEYNOTE-024, pembrolizumab compared with platinum-based
chemotherapy improved PFS (HR 0.50; 95% CI, 0.37 to 0.68; P<0.001) in the
ITT population. Median follow-up was 11.2 months.""",
            "match_start": 70,
            "match_end": 120,
            "expected": {
                "has_comparison": True,
                "population": AnalysisPopulation.ITT,
                "has_timepoint": True,
            }
        },
    ]

    print("\n## PROVENANCE EXTRACTION TESTS\n")

    for i, test in enumerate(test_cases, 1):
        tests_total += 1
        text = test["text"]
        expected = test["expected"]

        # Extract provenance
        provenance = extractor.extract_provenance(
            text,
            test["match_start"],
            test["match_end"]
        )

        # Check expected values
        all_pass = True

        if "population" in expected:
            if provenance.analysis_population != expected["population"]:
                print(f"  FAIL Test {i}: Population {provenance.analysis_population.value} != {expected['population'].value}")
                all_pass = False

        if "endpoint_type" in expected:
            if provenance.endpoint_type != expected["endpoint_type"]:
                print(f"  FAIL Test {i}: Endpoint {provenance.endpoint_type.value} != {expected['endpoint_type'].value}")
                all_pass = False

        if "has_comparison" in expected:
            has_comp = provenance.comparison_arms is not None
            if has_comp != expected["has_comparison"]:
                print(f"  FAIL Test {i}: Has comparison = {has_comp}")
                all_pass = False

        if "treatment_arm" in expected and provenance.comparison_arms:
            if expected["treatment_arm"].lower() not in provenance.comparison_arms.treatment_arm.lower():
                print(f"  FAIL Test {i}: Treatment arm = {provenance.comparison_arms.treatment_arm}")
                all_pass = False

        if "is_adjusted" in expected:
            if provenance.is_adjusted != expected["is_adjusted"]:
                print(f"  FAIL Test {i}: Is adjusted = {provenance.is_adjusted}")
                all_pass = False

        if "is_subgroup" in expected:
            if provenance.is_subgroup != expected["is_subgroup"]:
                print(f"  FAIL Test {i}: Is subgroup = {provenance.is_subgroup}")
                all_pass = False

        if "has_timepoint" in expected:
            has_tp = provenance.timepoint is not None
            if has_tp != expected["has_timepoint"]:
                print(f"  FAIL Test {i}: Has timepoint = {has_tp}")
                all_pass = False

        if all_pass:
            tests_passed += 1
            print(f"  PASS Test {i}: {list(expected.keys())}")

    # Summary
    accuracy = tests_passed / tests_total * 100 if tests_total > 0 else 0

    print(f"\n## SUMMARY")
    print(f"\nTests passed: {tests_passed}/{tests_total} ({accuracy:.1f}%)")

    # Demo of formatted output
    print("\n## EXAMPLE FORMATTED OUTPUT\n")
    demo_text = """The DAPA-HF trial compared dapagliflozin vs placebo. The primary
composite endpoint (CV death or HF hospitalization) showed hazard ratio 0.74
(95% CI, 0.65 to 0.85; P<0.001) in the intention-to-treat population after
median follow-up of 18.2 months. Analysis was adjusted for baseline characteristics."""

    provenance = extractor.extract_provenance(demo_text, 80, 130)
    print(format_provenance(provenance))

    print("\n" + "=" * 70)

    return tests_passed, tests_total


if __name__ == "__main__":
    run_tests()
