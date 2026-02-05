"""
Tests for Composite Endpoint Standardization v2.14
==================================================

Tests:
1. Standard composite detection (MACE, MAKE, etc.)
2. Component extraction
3. Effect extraction from composites
4. Hierarchical endpoint analysis
5. Custom composite parsing
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src' / 'core'))

from composite_endpoint import (
    CompositeEndpointParser,
    HierarchicalEndpointAnalyzer,
    parse_composite_endpoints,
    standardize_endpoint,
    get_mace_definition,
    EndpointCategory,
    STANDARD_COMPOSITES
)


def test_standard_composite_detection():
    """Test detection of standard composite abbreviations"""
    print("\n" + "=" * 60)
    print("STANDARD COMPOSITE DETECTION TESTS")
    print("=" * 60)

    parser = CompositeEndpointParser()
    passed = 0
    total = 0

    cases = [
        {
            "text": "The primary endpoint was 3-point MACE (cardiovascular death, "
                    "myocardial infarction, or stroke). MACE: HR 0.75 (95% CI 0.65-0.86).",
            "expected_abbrev": "MACE",
            "expected_components": 3,
            "desc": "3-point MACE with components and effect"
        },
        {
            "text": "The composite of CV death or hospitalization for heart failure "
                    "(HF-COMPOSITE) showed HR 0.80 (0.70-0.91).",
            "expected_abbrev": "HF-COMPOSITE",
            "expected_components": 2,
            "desc": "HF composite (CV death + HHF)"
        },
        {
            "text": "MAKE (sustained 40% or greater eGFR decline, ESKD, or renal death) was reduced "
                    "by 30%: HR 0.70 (0.58-0.85).",
            "expected_abbrev": "MAKE",
            "expected_components": 3,
            "desc": "MAKE renal composite"
        },
        {
            "text": "4-point MACE (CV death, MI, stroke, or hospitalization for unstable angina) "
                    "showed HR 0.82 (0.74-0.91).",
            "expected_abbrev": "MACE-4",
            "expected_components": 4,
            "desc": "4-point MACE"
        },
    ]

    for case in cases:
        total += 1
        results = parser.parse(case["text"])

        # Check if we found the expected composite
        found = False
        for ep in results:
            if ep.abbreviation == case["expected_abbrev"]:
                found = True
                if len(ep.components) >= case["expected_components"]:
                    passed += 1
                    print(f"  [PASS] {case['desc']}")
                    print(f"         Abbreviation: {ep.abbreviation}")
                    print(f"         Components: {[c.standardized_name for c in ep.components]}")
                    if ep.effect_size:
                        print(f"         Effect: HR {ep.effect_size} ({ep.ci_lower}-{ep.ci_upper})")
                else:
                    print(f"  [FAIL] {case['desc']}")
                    print(f"         Expected {case['expected_components']} components, "
                          f"got {len(ep.components)}")
                break

        if not found:
            # Check if we found it under a different key
            if results:
                print(f"  [PARTIAL] {case['desc']}")
                print(f"         Found: {[r.abbreviation for r in results]}")
                passed += 0.5
            else:
                print(f"  [FAIL] {case['desc']}")
                print(f"         No composite found")

    print(f"\nStandard Composite Detection: {passed}/{total} ({passed/total*100:.1f}%)")
    return passed, total


def test_component_standardization():
    """Test component name standardization"""
    print("\n" + "=" * 60)
    print("COMPONENT STANDARDIZATION TESTS")
    print("=" * 60)

    parser = CompositeEndpointParser()
    passed = 0
    total = 0

    cases = [
        ("CV death", "cardiovascular death"),
        ("cardiac death", "cardiovascular death"),
        ("MI", "myocardial infarction"),
        ("nonfatal MI", "non-fatal myocardial infarction"),
        ("HHF", "hospitalization for heart failure"),
        ("ESKD", "end-stage kidney disease"),
        ("doubling of creatinine", "sustained doubling of serum creatinine"),
        ("stroke", "stroke"),
        ("ICH", "intracranial hemorrhage"),
    ]

    for original, expected in cases:
        total += 1
        result = parser._standardize_component(original)

        if result == expected:
            passed += 1
            print(f"  [PASS] '{original}' -> '{result}'")
        else:
            print(f"  [FAIL] '{original}' -> '{result}' (expected '{expected}')")

    print(f"\nComponent Standardization: {passed}/{total} ({passed/total*100:.1f}%)")
    return passed, total


def test_custom_composite_parsing():
    """Test parsing of custom composite definitions"""
    print("\n" + "=" * 60)
    print("CUSTOM COMPOSITE PARSING TESTS")
    print("=" * 60)

    parser = CompositeEndpointParser()
    passed = 0
    total = 0

    cases = [
        {
            "text": "The composite endpoint of death, MI, stroke, and urgent revascularization "
                    "showed significant benefit.",
            "min_components": 4,
            "desc": "Custom 4-component composite"
        },
        {
            "text": "Primary outcome: composite of all-cause mortality or hospitalization for heart failure",
            "min_components": 2,
            "desc": "Custom mortality + HHF composite"
        },
        {
            "text": "The composite outcome of sustained eGFR decline 50% or more, ESKD, or death from renal causes",
            "min_components": 3,
            "desc": "Custom renal composite"
        },
        {
            "text": "CV death/HHF composite showed HR 0.76 (0.67-0.86)",
            "min_components": 2,
            "desc": "Slash-separated composite"
        },
    ]

    for case in cases:
        total += 1
        results = parser.parse(case["text"])

        if results and len(results[0].components) >= case["min_components"]:
            passed += 1
            print(f"  [PASS] {case['desc']}")
            print(f"         Components: {[c.standardized_name for c in results[0].components]}")
        else:
            print(f"  [FAIL] {case['desc']}")
            if results:
                print(f"         Found {len(results[0].components)} components, "
                      f"expected {case['min_components']}")
            else:
                print(f"         No composite parsed")

    print(f"\nCustom Composite Parsing: {passed}/{total} ({passed/total*100:.1f}%)")
    return passed, total


def test_component_level_effects():
    """Test extraction of component-level effects"""
    print("\n" + "=" * 60)
    print("COMPONENT-LEVEL EFFECT EXTRACTION TESTS")
    print("=" * 60)

    parser = CompositeEndpointParser()
    passed = 0
    total = 0

    cases = [
        {
            "text": """MACE occurred in 10.5% vs 12.8%.
                       CV death: HR 0.62 (0.49-0.77);
                       MI: HR 0.87 (0.70-1.07);
                       Stroke: HR 0.76 (0.54-1.08).""",
            "expected_effects": {"cardiovascular death": 0.62, "myocardial infarction": 0.87},
            "desc": "Multiple component effects"
        },
        {
            "text": "For cardiovascular death, HR was 0.82 (95% CI 0.69-0.98). "
                    "For hospitalization for HF, HR was 0.67 (95% CI 0.52-0.87).",
            "expected_effects": {"cardiovascular death": 0.82},
            "desc": "Component effects in sentences"
        },
    ]

    for case in cases:
        total += 1
        results = parser.parse(case["text"])

        effects_found = 0
        if results:
            for comp in results[0].components:
                if comp.effect_size:
                    for expected_name, expected_effect in case["expected_effects"].items():
                        if expected_name in comp.standardized_name:
                            if abs(comp.effect_size - expected_effect) < 0.01:
                                effects_found += 1

        if effects_found >= len(case["expected_effects"]) * 0.5:  # At least half found
            passed += 1
            print(f"  [PASS] {case['desc']}")
            if results:
                for c in results[0].components:
                    if c.effect_size:
                        print(f"         {c.standardized_name}: HR {c.effect_size}")
        else:
            print(f"  [FAIL] {case['desc']}")
            print(f"         Expected effects: {case['expected_effects']}")

    print(f"\nComponent-Level Effects: {passed}/{total} ({passed/total*100:.1f}%)")
    return passed, total


def test_endpoint_categorization():
    """Test endpoint categorization"""
    print("\n" + "=" * 60)
    print("ENDPOINT CATEGORIZATION TESTS")
    print("=" * 60)

    parser = CompositeEndpointParser()
    passed = 0
    total = 0

    cases = [
        ("cardiovascular death", EndpointCategory.CARDIOVASCULAR),
        ("myocardial infarction", EndpointCategory.CARDIOVASCULAR),
        ("hospitalization for heart failure", EndpointCategory.CARDIOVASCULAR),
        ("end-stage kidney disease", EndpointCategory.RENAL),
        ("sustained eGFR decline", EndpointCategory.RENAL),
        ("major bleeding", EndpointCategory.SAFETY),
        ("intracranial hemorrhage", EndpointCategory.SAFETY),
        ("all-cause mortality", EndpointCategory.MORTALITY),
    ]

    for name, expected_cat in cases:
        total += 1
        result = parser._categorize_component(name)

        if result == expected_cat:
            passed += 1
            print(f"  [PASS] '{name}' -> {result.value}")
        else:
            print(f"  [FAIL] '{name}' -> {result.value} (expected {expected_cat.value})")

    print(f"\nEndpoint Categorization: {passed}/{total} ({passed/total*100:.1f}%)")
    return passed, total


def test_hierarchical_analysis():
    """Test hierarchical endpoint analysis"""
    print("\n" + "=" * 60)
    print("HIERARCHICAL ENDPOINT ANALYSIS TESTS")
    print("=" * 60)

    parser = CompositeEndpointParser()
    analyzer = HierarchicalEndpointAnalyzer()
    passed = 0
    total = 0

    cases = [
        {
            "text": "Win ratio analysis was used for the hierarchical composite. "
                    "Components were ranked: death first, then hospitalization for HF, "
                    "then change in Kansas City Cardiomyopathy Questionnaire. "
                    "Win ratio 1.28 (95% CI 1.14-1.44).",
            "expected_hierarchical": True,
            "expected_method": "win ratio",
            "desc": "Win ratio hierarchical composite"
        },
        {
            "text": "Time to first event analysis was used for the composite of "
                    "CV death, MI, or stroke. HR 0.85 (0.75-0.96).",
            "expected_hierarchical": True,
            "expected_method": "time to first event",
            "desc": "Time to first event composite"
        },
        {
            "text": "The composite of CV death or HHF was analyzed. HR 0.80 (0.70-0.91).",
            "expected_hierarchical": False,
            "expected_method": None,
            "desc": "Non-hierarchical composite"
        },
    ]

    for case in cases:
        total += 1
        results = parser.parse(case["text"])

        if results:
            ep = analyzer.analyze(case["text"], results[0])

            if ep.is_hierarchical == case["expected_hierarchical"]:
                if not case["expected_hierarchical"] or \
                   (ep.hierarchy_method and case["expected_method"] in ep.hierarchy_method):
                    passed += 1
                    print(f"  [PASS] {case['desc']}")
                    print(f"         Hierarchical: {ep.is_hierarchical}")
                    if ep.hierarchy_method:
                        print(f"         Method: {ep.hierarchy_method}")
                else:
                    print(f"  [FAIL] {case['desc']}")
                    print(f"         Method: {ep.hierarchy_method} (expected {case['expected_method']})")
            else:
                print(f"  [FAIL] {case['desc']}")
                print(f"         Hierarchical: {ep.is_hierarchical} (expected {case['expected_hierarchical']})")
        else:
            print(f"  [FAIL] {case['desc']}")
            print(f"         No composite parsed")

    print(f"\nHierarchical Analysis: {passed}/{total} ({passed/total*100:.1f}%)")
    return passed, total


def test_standard_definitions():
    """Test standard composite definitions"""
    print("\n" + "=" * 60)
    print("STANDARD DEFINITION TESTS")
    print("=" * 60)

    passed = 0
    total = 0

    # Test MACE definitions
    cases = [
        ("MACE", 3, ["cardiovascular death", "myocardial infarction", "stroke"]),
        ("MACE-4", 4, ["cardiovascular death", "myocardial infarction", "stroke", "hospitalization"]),
        ("MAKE", 3, ["egfr", "kidney", "renal"]),
        ("HF-COMPOSITE", 2, ["cardiovascular death", "hospitalization"]),
    ]

    for abbrev, min_components, keywords in cases:
        total += 1
        defn = STANDARD_COMPOSITES.get(abbrev)

        if defn and len(defn["components"]) >= min_components:
            # Check if keywords are present
            components_str = " ".join(defn["components"]).lower()
            keywords_found = sum(1 for k in keywords if k.lower() in components_str)

            if keywords_found >= len(keywords) * 0.5:
                passed += 1
                print(f"  [PASS] {abbrev}: {defn['full_name']}")
                print(f"         Components: {defn['components']}")
            else:
                print(f"  [FAIL] {abbrev}: Missing keywords")
        else:
            print(f"  [FAIL] {abbrev}: Not found or insufficient components")

    print(f"\nStandard Definitions: {passed}/{total} ({passed/total*100:.1f}%)")
    return passed, total


def test_convenience_functions():
    """Test convenience functions"""
    print("\n" + "=" * 60)
    print("CONVENIENCE FUNCTION TESTS")
    print("=" * 60)

    passed = 0
    total = 0

    # Test standardize_endpoint
    total += 1
    name, abbrev = standardize_endpoint("3-point MACE")
    if abbrev == "MACE":
        passed += 1
        print(f"  [PASS] standardize_endpoint('3-point MACE') -> {abbrev}")
    else:
        print(f"  [FAIL] standardize_endpoint('3-point MACE') -> {abbrev}")

    # Test get_mace_definition
    total += 1
    defn = get_mace_definition("3-point")
    if len(defn["components"]) == 3:
        passed += 1
        print(f"  [PASS] get_mace_definition('3-point') -> 3 components")
    else:
        print(f"  [FAIL] get_mace_definition('3-point') -> {len(defn['components'])} components")

    total += 1
    defn = get_mace_definition("4-point")
    if len(defn["components"]) >= 4:
        passed += 1
        print(f"  [PASS] get_mace_definition('4-point') -> {len(defn['components'])} components")
    else:
        print(f"  [FAIL] get_mace_definition('4-point') -> {len(defn['components'])} components")

    # Test parse_composite_endpoints
    total += 1
    results = parse_composite_endpoints("MACE: HR 0.75 (0.65-0.86)")
    if results and results[0].effect_size == 0.75:
        passed += 1
        print(f"  [PASS] parse_composite_endpoints extracted HR 0.75")
    else:
        print(f"  [FAIL] parse_composite_endpoints did not extract effect")

    print(f"\nConvenience Functions: {passed}/{total} ({passed/total*100:.1f}%)")
    return passed, total


def main():
    """Run all composite endpoint tests"""
    print("=" * 70)
    print("COMPOSITE ENDPOINT TESTS v2.14")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    all_passed = 0
    all_total = 0

    # Run all test suites
    p, t = test_standard_composite_detection()
    all_passed += p
    all_total += t

    p, t = test_component_standardization()
    all_passed += p
    all_total += t

    p, t = test_custom_composite_parsing()
    all_passed += p
    all_total += t

    p, t = test_component_level_effects()
    all_passed += p
    all_total += t

    p, t = test_endpoint_categorization()
    all_passed += p
    all_total += t

    p, t = test_hierarchical_analysis()
    all_passed += p
    all_total += t

    p, t = test_standard_definitions()
    all_passed += p
    all_total += t

    p, t = test_convenience_functions()
    all_passed += p
    all_total += t

    # Summary
    print("\n" + "=" * 70)
    print("COMPOSITE ENDPOINT SUMMARY")
    print("=" * 70)
    print(f"\n  TOTAL: {all_passed}/{all_total} ({all_passed/all_total*100:.1f}%)")
    print("=" * 70)

    # Save results
    import json
    output = {
        "timestamp": datetime.now().isoformat(),
        "version": "v2.14-composite-endpoint",
        "summary": {
            "total": all_total,
            "passed": all_passed,
            "accuracy": all_passed / all_total * 100
        }
    }

    output_file = Path(__file__).parent / "output" / "composite_endpoint_tests.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return all_passed, all_total


if __name__ == "__main__":
    main()
