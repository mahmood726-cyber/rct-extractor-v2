"""
RCT Extractor v3.0 Comprehensive Validation
============================================

Addresses all editorial concerns with:
1. Original validation set testing
2. Held-out test set (50+ cases from different sources)
3. False positive testing (100+ negative cases)
4. Calibration metrics (ECE, MCE, Brier score)
5. SE calculation validation
6. ARD normalization validation

Target metrics:
- Sensitivity on held-out set: >90%
- False positive rate: <5%
- Expected Calibration Error (ECE): <0.10
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add paths
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))
sys.path.insert(0, str(script_dir / 'src' / 'core'))
sys.path.insert(0, str(script_dir / 'data'))

from enhanced_extractor_v3 import (
    EnhancedExtractor,
    AutomationTier,
    EffectType,
    calculate_automation_metrics,
    calculate_calibration_metrics,
    generate_reliability_diagram_data,
    calculate_se_from_ci,
    to_dict,
    correct_ocr_errors
)
from expanded_validation_v3 import ALL_VALIDATION_CASES, get_validation_stats
from held_out_test_set import HELD_OUT_CASES, get_held_out_stats
from false_positive_test_cases import NEGATIVE_CASES, get_negative_case_stats


def run_positive_validation(extractor, cases, dataset_name):
    """Run validation on positive cases (should extract correctly)"""
    results = {
        'total': 0,
        'correct': 0,
        'missed': 0,
        'by_type': defaultdict(lambda: {'total': 0, 'correct': 0, 'missed': 0}),
        'extractions': [],
        'failures': [],
        'predictions': [],
        'actuals': [],
    }

    for case in cases:
        results['total'] += 1

        # Get expected type
        if hasattr(case, 'expected_type'):
            expected_type = case.expected_type
            expected_value = case.expected_value
            expected_ci_low = case.expected_ci_low
            expected_ci_high = case.expected_ci_high
        else:
            continue

        results['by_type'][expected_type]['total'] += 1

        # Apply OCR correction if needed
        text = case.text
        if hasattr(case, 'has_ocr_errors') and case.has_ocr_errors:
            text = correct_ocr_errors(text)

        # Extract
        extractions = extractor.extract(text)

        # Check if we found the expected extraction
        found_match = False
        matched_extraction = None

        for ext in extractions:
            if ext.effect_type.value == expected_type:
                value_match = abs(ext.point_estimate - expected_value) < 0.02
                if ext.ci:
                    ci_low_match = abs(ext.ci.lower - expected_ci_low) < 0.02
                    ci_high_match = abs(ext.ci.upper - expected_ci_high) < 0.02
                    if value_match and ci_low_match and ci_high_match:
                        found_match = True
                        matched_extraction = ext
                        break

        if found_match:
            results['correct'] += 1
            results['by_type'][expected_type]['correct'] += 1
            results['extractions'].append(matched_extraction)
            results['predictions'].append(matched_extraction.calibrated_confidence)
            results['actuals'].append(True)
        else:
            results['missed'] += 1
            results['by_type'][expected_type]['missed'] += 1
            results['failures'].append({
                'case': case,
                'extractions': extractions,
            })
            # For missed cases, record the confidence of any extraction (or 0.5 baseline)
            if extractions:
                results['predictions'].append(extractions[0].calibrated_confidence)
            else:
                results['predictions'].append(0.5)
            results['actuals'].append(False)

    return results


def run_false_positive_validation(extractor, cases):
    """Run validation on negative cases (should NOT extract)"""
    results = {
        'total': 0,
        'true_negatives': 0,
        'false_positives': 0,
        'by_category': defaultdict(lambda: {'total': 0, 'tn': 0, 'fp': 0}),
        'fp_examples': [],
    }

    for case in cases:
        results['total'] += 1
        results['by_category'][case.category]['total'] += 1

        # Extract
        extractions = extractor.extract(case.text)

        if len(extractions) == 0:
            # Correct - no extraction
            results['true_negatives'] += 1
            results['by_category'][case.category]['tn'] += 1
        else:
            # False positive - incorrectly extracted something
            results['false_positives'] += 1
            results['by_category'][case.category]['fp'] += 1
            results['fp_examples'].append({
                'case': case,
                'extractions': extractions,
            })

    return results


def print_section_header(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    """Run comprehensive validation"""
    print_section_header("RCT EXTRACTOR v3.0 - COMPREHENSIVE VALIDATION")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("\nAddressing Editorial Concerns:")
    print("1. Held-out test set validation")
    print("2. False positive testing")
    print("3. Calibration metrics (ECE, MCE)")
    print("4. SE calculation validation")
    print("5. ARD normalization validation")

    # Initialize extractor
    extractor = EnhancedExtractor()

    # =========================================================================
    # SECTION 1: ORIGINAL VALIDATION SET
    # =========================================================================
    print_section_header("SECTION 1: ORIGINAL VALIDATION SET")

    orig_stats = get_validation_stats()
    print(f"\nDataset: {orig_stats['total']} cases")
    print(f"By type: {orig_stats['by_type']}")

    orig_results = run_positive_validation(extractor, ALL_VALIDATION_CASES, "Original")

    orig_sensitivity = orig_results['correct'] / orig_results['total'] if orig_results['total'] > 0 else 0
    print(f"\nResults:")
    print(f"  Sensitivity: {orig_sensitivity:.1%} ({orig_results['correct']}/{orig_results['total']})")

    # By type
    print("\n  By Effect Type:")
    for etype in sorted(orig_results['by_type'].keys()):
        data = orig_results['by_type'][etype]
        sens = data['correct'] / data['total'] if data['total'] > 0 else 0
        print(f"    {etype}: {sens:.1%} ({data['correct']}/{data['total']})")

    # =========================================================================
    # SECTION 2: HELD-OUT TEST SET (Critical Revision #1)
    # =========================================================================
    print_section_header("SECTION 2: HELD-OUT TEST SET")
    print("(Critical Revision #1: Address overfitting concerns)")

    held_out_stats = get_held_out_stats()
    print(f"\nDataset: {held_out_stats['total']} NEW cases")
    print(f"By type: {held_out_stats['by_type']}")
    print(f"By source: {held_out_stats['by_source']}")
    print(f"OCR cases: {held_out_stats['ocr_cases']}")

    held_out_results = run_positive_validation(extractor, HELD_OUT_CASES, "Held-Out")

    held_out_sensitivity = held_out_results['correct'] / held_out_results['total'] if held_out_results['total'] > 0 else 0
    print(f"\nResults:")
    print(f"  Sensitivity: {held_out_sensitivity:.1%} ({held_out_results['correct']}/{held_out_results['total']})")
    print(f"  TARGET: >90%  {'PASS' if held_out_sensitivity > 0.90 else 'FAIL'}")

    # By type
    print("\n  By Effect Type:")
    for etype in sorted(held_out_results['by_type'].keys()):
        data = held_out_results['by_type'][etype]
        sens = data['correct'] / data['total'] if data['total'] > 0 else 0
        print(f"    {etype}: {sens:.1%} ({data['correct']}/{data['total']})")

    # Show failures
    if held_out_results['failures']:
        print(f"\n  Failures ({len(held_out_results['failures'])} cases):")
        for i, fail in enumerate(held_out_results['failures'][:5]):
            case = fail['case']
            print(f"    {i+1}. Expected: {case.expected_type} {case.expected_value}")
            print(f"       Source: {case.source}")
            print(f"       Text: {case.text[:60]}...")
            if fail['extractions']:
                print(f"       Got: {[(e.effect_type.value, e.point_estimate) for e in fail['extractions']]}")
            else:
                print(f"       Got: No extractions")

    # =========================================================================
    # SECTION 3: FALSE POSITIVE TESTING (Critical Revision #2)
    # =========================================================================
    print_section_header("SECTION 3: FALSE POSITIVE TESTING")
    print("(Critical Revision #2: Test on text WITHOUT effect estimates)")

    neg_stats = get_negative_case_stats()
    print(f"\nDataset: {neg_stats['total']} negative cases")
    print(f"Categories: {list(neg_stats['by_category'].keys())[:5]}... ({len(neg_stats['by_category'])} total)")

    fp_results = run_false_positive_validation(extractor, NEGATIVE_CASES)

    fpr = fp_results['false_positives'] / fp_results['total'] if fp_results['total'] > 0 else 0
    specificity = fp_results['true_negatives'] / fp_results['total'] if fp_results['total'] > 0 else 0

    print(f"\nResults:")
    print(f"  True Negatives: {fp_results['true_negatives']}/{fp_results['total']}")
    print(f"  False Positives: {fp_results['false_positives']}/{fp_results['total']}")
    print(f"  False Positive Rate: {fpr:.1%}")
    print(f"  Specificity: {specificity:.1%}")
    print(f"  TARGET: FPR <5%  {'PASS' if fpr < 0.05 else 'FAIL'}")

    # By category
    print("\n  By Category:")
    for cat in sorted(fp_results['by_category'].keys())[:10]:
        data = fp_results['by_category'][cat]
        cat_fpr = data['fp'] / data['total'] if data['total'] > 0 else 0
        status = "PASS" if cat_fpr < 0.10 else "FAIL"
        print(f"    {cat}: {data['fp']}/{data['total']} FP ({cat_fpr:.0%}) {status}")

    # Show false positive examples
    if fp_results['fp_examples']:
        print(f"\n  False Positive Examples ({len(fp_results['fp_examples'])} total):")
        for i, fp in enumerate(fp_results['fp_examples'][:5]):
            case = fp['case']
            print(f"    {i+1}. Category: {case.category}")
            print(f"       Text: {case.text[:50]}...")
            print(f"       Extracted: {[(e.effect_type.value, e.point_estimate) for e in fp['extractions']]}")

    # =========================================================================
    # SECTION 4: CALIBRATION METRICS (Critical Revision #3)
    # =========================================================================
    print_section_header("SECTION 4: CALIBRATION METRICS")
    print("(Critical Revision #3: ECE, MCE, Brier Score)")

    # Combine predictions and actuals from all positive validation
    all_predictions = orig_results['predictions'] + held_out_results['predictions']
    all_actuals = orig_results['actuals'] + held_out_results['actuals']

    if len(all_predictions) > 0:
        cal_metrics = calculate_calibration_metrics(all_predictions, all_actuals)

        print(f"\nCalibration Results (N={len(all_predictions)}):")
        print(f"  Expected Calibration Error (ECE): {cal_metrics.ece:.4f}")
        print(f"  Maximum Calibration Error (MCE): {cal_metrics.mce:.4f}")
        print(f"  Brier Score: {cal_metrics.brier_score:.4f}")
        print(f"  Calibration Slope: {cal_metrics.calibration_slope:.3f}")
        print(f"  Calibration Intercept: {cal_metrics.calibration_intercept:.3f}")
        print(f"  TARGET: ECE <0.10  {'PASS' if cal_metrics.ece < 0.10 else 'FAIL'}")

        # Reliability diagram data
        print("\n  Reliability Diagram (Accuracy vs Confidence):")
        print(f"  {'Bin':<8} {'Conf':<10} {'Acc':<10} {'Count':<8} {'Gap':<10}")
        print("  " + "-" * 50)
        for i, (conf, acc, count) in enumerate(zip(
            cal_metrics.bin_confidences,
            cal_metrics.bin_accuracies,
            cal_metrics.bin_counts
        )):
            gap = abs(acc - conf)
            print(f"  {i+1:<8} {conf:.3f}      {acc:.3f}      {count:<8} {gap:.3f}")

    # =========================================================================
    # SECTION 5: STANDARD ERROR VALIDATION
    # =========================================================================
    print_section_header("SECTION 5: STANDARD ERROR CALCULATION")
    print("(High Priority Revision: SE extraction/calculation)")

    # Check SE calculation on correct extractions
    se_stats = {
        'total': 0,
        'calculated': 0,
        'unavailable': 0,
        'by_type': defaultdict(lambda: {'calculated': 0, 'unavailable': 0})
    }

    for ext in orig_results['extractions'] + held_out_results['extractions']:
        se_stats['total'] += 1
        if ext.standard_error is not None:
            se_stats['calculated'] += 1
            se_stats['by_type'][ext.effect_type.value]['calculated'] += 1
        else:
            se_stats['unavailable'] += 1
            se_stats['by_type'][ext.effect_type.value]['unavailable'] += 1

    se_coverage = se_stats['calculated'] / se_stats['total'] if se_stats['total'] > 0 else 0
    print(f"\nSE Calculation Coverage: {se_coverage:.1%} ({se_stats['calculated']}/{se_stats['total']})")
    print(f"TARGET: >95%  {'PASS' if se_coverage > 0.95 else 'FAIL'}")

    print("\n  By Effect Type:")
    for etype in sorted(se_stats['by_type'].keys()):
        data = se_stats['by_type'][etype]
        total = data['calculated'] + data['unavailable']
        cov = data['calculated'] / total if total > 0 else 0
        print(f"    {etype}: {cov:.1%} ({data['calculated']}/{total})")

    # Example SE calculations
    print("\n  Example SE Calculations:")
    for ext in (orig_results['extractions'] + held_out_results['extractions'])[:3]:
        if ext.standard_error is not None:
            print(f"    {ext.effect_type.value} {ext.point_estimate}: SE={ext.standard_error:.4f} ({ext.se_method})")

    # =========================================================================
    # SECTION 6: ARD NORMALIZATION
    # =========================================================================
    print_section_header("SECTION 6: ARD NORMALIZATION")
    print("(High Priority Revision: Consistent decimal scale)")

    # Check ARD extractions for normalization
    ard_extractions = [
        ext for ext in orig_results['extractions'] + held_out_results['extractions']
        if ext.effect_type == EffectType.ARD
    ]

    if ard_extractions:
        print(f"\nARD Extractions: {len(ard_extractions)}")
        print("\n  Normalization Results:")
        print(f"  {'Original':<15} {'Scale':<12} {'Normalized':<15}")
        print("  " + "-" * 45)
        for ext in ard_extractions[:5]:
            orig = f"{ext.point_estimate:.2f}"
            scale = ext.original_scale if ext.original_scale else "unknown"
            norm = f"{ext.normalized_value:.4f}" if ext.normalized_value is not None else "N/A"
            print(f"  {orig:<15} {scale:<12} {norm:<15}")

        # Check consistency
        all_normalized = all(
            ext.normalized_value is not None and -1 <= ext.normalized_value <= 1
            for ext in ard_extractions
        )
        print(f"\n  All ARD values normalized to decimal scale: {'PASS' if all_normalized else 'FAIL'}")
    else:
        print("\n  No ARD extractions found")

    # =========================================================================
    # SECTION 7: AUTOMATION METRICS
    # =========================================================================
    print_section_header("SECTION 7: AUTOMATION METRICS")

    all_extractions = orig_results['extractions'] + held_out_results['extractions']
    if all_extractions:
        auto_metrics = calculate_automation_metrics(all_extractions)
        print(f"\nTotal correct extractions: {auto_metrics.total}")
        print(f"Full Auto: {auto_metrics.full_auto} ({auto_metrics.full_auto/auto_metrics.total:.1%})")
        print(f"Spot Check: {auto_metrics.spot_check} ({auto_metrics.spot_check/auto_metrics.total:.1%})")
        print(f"Verify: {auto_metrics.verify} ({auto_metrics.verify/auto_metrics.total:.1%})")
        print(f"Manual: {auto_metrics.manual} ({auto_metrics.manual/auto_metrics.total:.1%})")
        print(f"\nAutomation Rate: {auto_metrics.automation_rate:.1%}")
        print(f"Human Effort Reduction: {auto_metrics.human_effort_reduction:.1%}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_section_header("COMPREHENSIVE VALIDATION SUMMARY")

    print("\n" + "-" * 50)
    print("CRITICAL METRICS (Editorial Requirements)")
    print("-" * 50)

    metrics = [
        ("Original Sensitivity", f"{orig_sensitivity:.1%}", "100%", orig_sensitivity >= 0.95),
        ("Held-Out Sensitivity", f"{held_out_sensitivity:.1%}", ">90%", held_out_sensitivity > 0.90),
        ("False Positive Rate", f"{fpr:.1%}", "<5%", fpr < 0.05),
        ("ECE (Calibration)", f"{cal_metrics.ece:.3f}" if 'cal_metrics' in dir() else "N/A", "<0.10", cal_metrics.ece < 0.10 if 'cal_metrics' in dir() else False),
        ("SE Coverage", f"{se_coverage:.1%}", ">95%", se_coverage > 0.95),
    ]

    all_pass = True
    for name, value, target, passed in metrics:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  {name:<25} {value:<10} (target: {target:<8}) [{status}]")

    print("\n" + "=" * 70)
    if all_pass:
        print("OVERALL STATUS: ALL TARGETS MET")
        print("Ready for publication in Research Synthesis Methods")
    else:
        print("OVERALL STATUS: SOME TARGETS NOT MET")
        print("Additional work required before publication")
    print("=" * 70)

    return {
        'original_sensitivity': orig_sensitivity,
        'held_out_sensitivity': held_out_sensitivity,
        'false_positive_rate': fpr,
        'ece': cal_metrics.ece if 'cal_metrics' in dir() else None,
        'se_coverage': se_coverage,
        'all_pass': all_pass,
    }


if __name__ == "__main__":
    main()
