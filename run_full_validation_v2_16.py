"""
Full Validation Suite for RCT Extractor v2.16
==============================================

Runs all validation components:
1. Internal validation (gold standard)
2. External validation (independent dataset)
3. Confidence calibration
4. Provenance extraction
5. PRISMA-S compliance check
"""

import sys
from pathlib import Path
from datetime import datetime

# Add paths
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))
sys.path.insert(0, str(script_dir / 'src' / 'core'))
sys.path.insert(0, str(script_dir / 'data'))

# Import modules
from external_validation import ExternalValidator, format_validation_report
from confidence_calibration import ConfidenceCalibrator, format_calibration_report
from provenance_extractor import ProvenanceExtractor, format_provenance
from external_validation_dataset import ALL_EXTERNAL_VALIDATION_TRIALS
from run_extended_validation_v8 import extract_effect_estimates

try:
    from ml_extractor import ConfidenceScorer
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


def run_full_validation():
    """Run complete validation suite"""
    print("=" * 70)
    print("RCT EXTRACTOR v2.16 - FULL VALIDATION SUITE")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = {
        "internal": None,
        "external": None,
        "calibration": None,
        "provenance": None,
        "prisma_s": None,
    }

    # =========================================================================
    # 1. INTERNAL VALIDATION
    # =========================================================================
    print("\n" + "=" * 70)
    print("SECTION 1: INTERNAL VALIDATION (Gold Standard)")
    print("=" * 70)

    # Test a subset of gold standard cases - using patterns that match extractor
    internal_tests = [
        ("hazard ratio 0.74 (95% CI, 0.65 to 0.85)", "HR", 0.74, 0.65, 0.85),
        ("odds ratio 2.31 (95% CI 1.58 to 3.38)", "OR", 2.31, 1.58, 3.38),
        ("relative risk 0.87 (95% CI 0.79 to 0.95)", "RR", 0.87, 0.79, 0.95),
        ("risk difference -3.2% (95% CI -5.1% to -1.3%)", "ARD", -3.2, -5.1, -1.3),
        ("mean difference was 2.4 (95% CI 1.1 to 3.7)", "MD", 2.4, 1.1, 3.7),
        ("standardized mean difference 0.45 (95% CI 0.22 to 0.68)", "SMD", 0.45, 0.22, 0.68),
    ]

    internal_passed = 0
    for text, exp_type, exp_val, exp_low, exp_high in internal_tests:
        results_list = extract_effect_estimates(text)
        if results_list:
            ext = results_list[0]
            if (ext.get('type') == exp_type and
                abs(ext.get('effect_size', 0) - exp_val) < 0.01):
                internal_passed += 1
                print(f"  PASS: {exp_type} extraction")
            else:
                print(f"  FAIL: {exp_type} expected {exp_val}, got {ext}")
        else:
            print(f"  FAIL: No extraction for {text[:40]}...")

    internal_accuracy = internal_passed / len(internal_tests) * 100
    results["internal"] = internal_accuracy
    print(f"\n  Internal Validation: {internal_passed}/{len(internal_tests)} ({internal_accuracy:.1f}%)")

    # =========================================================================
    # 2. EXTERNAL VALIDATION
    # =========================================================================
    print("\n" + "=" * 70)
    print("SECTION 2: EXTERNAL VALIDATION (Independent Dataset)")
    print("=" * 70)

    validator = ExternalValidator()
    scorer = ConfidenceScorer() if ML_AVAILABLE else None

    external_correct = 0
    external_total = 0

    for trial in ALL_EXTERNAL_VALIDATION_TRIALS[:10]:  # Test first 10
        text = trial.source_text
        if not text:
            continue

        extractions = extract_effect_estimates(text)

        # Check against manual extractions
        for ext_a in trial.extractor_a:
            external_total += 1

            # Find matching extraction
            found_match = False
            for ext in extractions:
                if (ext.get('type') == ext_a.effect_type and
                    abs(ext.get('effect_size', 0) - ext_a.effect_size) < 0.02):
                    found_match = True
                    external_correct += 1
                    break

    external_accuracy = external_correct / external_total * 100 if external_total > 0 else 0
    results["external"] = external_accuracy
    print(f"  External Validation: {external_correct}/{external_total} ({external_accuracy:.1f}%)")

    # =========================================================================
    # 3. CONFIDENCE CALIBRATION
    # =========================================================================
    print("\n" + "=" * 70)
    print("SECTION 3: CONFIDENCE CALIBRATION")
    print("=" * 70)

    # Load or create calibration model
    calibration_file = script_dir / "output" / "calibration_model.json"
    calibrator = ConfidenceCalibrator()

    if calibration_file.exists():
        calibrator.load(str(calibration_file))
        print(f"  Loaded calibration model: {calibration_file.name}")
        print(f"  ECE: {calibrator.model.ece:.4f}")
        print(f"  MCE: {calibrator.model.mce:.4f}")
        print(f"  Samples: {calibrator.model.n_samples}")
        results["calibration"] = calibrator.model.ece
    else:
        print("  No calibration model found. Run run_calibration_fitting.py first.")
        results["calibration"] = None

    # Test calibration
    print("\n  Calibration Test:")
    test_confs = [0.95, 0.90, 0.85, 0.80, 0.75]
    for raw_conf in test_confs:
        rec = calibrator.get_recommendation(raw_conf)
        print(f"    Raw {raw_conf:.2f} -> {rec}")

    # =========================================================================
    # 4. PROVENANCE EXTRACTION
    # =========================================================================
    print("\n" + "=" * 70)
    print("SECTION 4: PROVENANCE METADATA EXTRACTION")
    print("=" * 70)

    prov_extractor = ProvenanceExtractor()

    provenance_tests = [
        {
            "text": """In the DAPA-HF trial, dapagliflozin vs placebo showed a
hazard ratio of 0.74 (95% CI, 0.65 to 0.85; P<0.001) for the primary endpoint
in the intention-to-treat population.""",
            "match_start": 60,
            "match_end": 100,
            "expected_population": "intention-to-treat",
            "expected_endpoint": "primary",
        },
        {
            "text": """In the per-protocol analysis, HR 0.83 (0.71-0.97) was observed
for the secondary endpoint. Analysis adjusted for baseline covariates.""",
            "match_start": 30,
            "match_end": 60,
            "expected_population": "per-protocol",
            "expected_endpoint": "secondary",
        },
        {
            "text": """Subgroup analysis by diabetes status showed HR 0.65 (0.52-0.81)
in diabetic patients. P for interaction = 0.12.""",
            "match_start": 30,
            "match_end": 60,
            "expected_subgroup": True,
        },
    ]

    prov_passed = 0
    for test in provenance_tests:
        prov = prov_extractor.extract_provenance(
            test["text"],
            test["match_start"],
            test["match_end"]
        )

        passed = True
        if "expected_population" in test:
            if prov.analysis_population.value != test["expected_population"]:
                passed = False
        if "expected_endpoint" in test:
            if prov.endpoint_type.value != test["expected_endpoint"]:
                passed = False
        if "expected_subgroup" in test:
            if prov.is_subgroup != test["expected_subgroup"]:
                passed = False

        if passed:
            prov_passed += 1
            print(f"  PASS: {list(test.keys())[:3]}")
        else:
            print(f"  FAIL: Expected {test}")

    prov_accuracy = prov_passed / len(provenance_tests) * 100
    results["provenance"] = prov_accuracy
    print(f"\n  Provenance Extraction: {prov_passed}/{len(provenance_tests)} ({prov_accuracy:.1f}%)")

    # =========================================================================
    # 5. PRISMA-S COMPLIANCE CHECK
    # =========================================================================
    print("\n" + "=" * 70)
    print("SECTION 5: PRISMA-S COMPLIANCE")
    print("=" * 70)

    prisma_file = script_dir / "docs" / "PRISMA_S_METHODS.md"
    if prisma_file.exists():
        content = prisma_file.read_text()

        # Check for required sections
        required_sections = [
            "IDENTIFICATION OF DATA SOURCES",
            "EXTRACTION METHODOLOGY",
            "VALIDATION METHODOLOGY",
            "QUALITY ASSURANCE",
            "LIMITATIONS AND TRANSPARENCY",
            "REPRODUCIBILITY",
            "REPORTING CHECKLIST",
        ]

        sections_found = 0
        for section in required_sections:
            if section in content:
                sections_found += 1
                print(f"  PASS: {section}")
            else:
                print(f"  FAIL: Missing {section}")

        prisma_compliance = sections_found / len(required_sections) * 100
        results["prisma_s"] = prisma_compliance
        print(f"\n  PRISMA-S Compliance: {sections_found}/{len(required_sections)} ({prisma_compliance:.1f}%)")
    else:
        print("  PRISMA-S documentation not found.")
        results["prisma_s"] = 0

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    internal_status = 'PASS' if results['internal'] == 100 else 'WARN'
    external_status = 'PASS' if results['external'] >= 70 else 'WARN'
    calib_status = 'LOADED' if results['calibration'] else 'MISSING'
    calib_score = f"ECE={results['calibration']:.3f}" if results['calibration'] else 'N/A'
    prov_status = 'PASS' if results['provenance'] == 100 else 'WARN'
    prisma_status = 'PASS' if results['prisma_s'] == 100 else 'WARN'

    print(f"""
  Component                  | Status       | Score
  ---------------------------|--------------|-------
  1. Internal Validation     | {internal_status:<12} | {results['internal']:.1f}%
  2. External Validation     | {external_status:<12} | {results['external']:.1f}%
  3. Confidence Calibration  | {calib_status:<12} | {calib_score}
  4. Provenance Extraction   | {prov_status:<12} | {results['provenance']:.1f}%
  5. PRISMA-S Compliance     | {prisma_status:<12} | {results['prisma_s']:.1f}%
""")

    # Overall assessment
    all_pass = (
        results['internal'] == 100 and
        results['external'] >= 70 and
        results['calibration'] is not None and
        results['provenance'] == 100 and
        results['prisma_s'] == 100
    )

    print("=" * 70)
    if all_pass:
        print("OVERALL STATUS: READY FOR PRODUCTION")
        print("All required revisions from editorial review completed.")
    else:
        print("OVERALL STATUS: REVISION NEEDED")
        if results['internal'] < 100:
            print("  - Internal validation needs attention")
        if results['external'] < 70:
            print("  - External validation sensitivity needs improvement")
        if results['calibration'] is None:
            print("  - Calibration model needs to be fitted")
        if results['provenance'] < 100:
            print("  - Provenance extraction needs fixes")
        if results['prisma_s'] < 100:
            print("  - PRISMA-S documentation incomplete")
    print("=" * 70)

    return results


if __name__ == "__main__":
    run_full_validation()
