"""
Confidence Calibration Analysis for RCT Extractor v2

Includes:
- ROC curve analysis (discrimination of correct vs incorrect extractions)
- Precision-Recall curve analysis
- Calibration (reliability) analysis
- Expected Calibration Error (ECE)
- Specificity analysis (rejecting non-matches)
"""
import sys
import json
from pathlib import Path
from typing import Dict, Tuple, List

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.extractor import NumericParser
from src.benchmark.statistics import (
    calculate_roc_curve,
    calculate_precision_recall_curve,
    calculate_calibration_curve,
    calculate_confidence_score,
    interpret_auc,
    clopper_pearson_ci
)


def load_all_cases():
    """Load all gold standard cases"""
    gold_dir = Path(__file__).parent / 'data' / 'gold'
    cases = []

    for jsonl_file in gold_dir.glob("*.jsonl"):
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    data['source_file'] = jsonl_file.stem
                    cases.append(data)
                except json.JSONDecodeError:
                    pass

    return cases


def extract_with_confidence(text: str, measure_type: str) -> Tuple[Dict, float]:
    """Extract value and calculate confidence score"""
    result = None

    if measure_type == 'HR':
        result = NumericParser.parse_hazard_ratio(text)
    elif measure_type == 'OR':
        result = NumericParser.parse_odds_ratio(text)
    elif measure_type == 'RR':
        result = NumericParser.parse_relative_risk(text)
    elif measure_type == 'RD':
        result = NumericParser.parse_risk_difference(text)
    elif measure_type == 'MD':
        result = NumericParser.parse_mean_difference(text)

    confidence = calculate_confidence_score(result or {}, text)
    return result, confidence


def check_match(extracted: float, expected: float, tolerance: float = 0.05) -> bool:
    """Check if values match within tolerance"""
    if extracted is None or expected is None:
        return False
    if expected == 0:
        return abs(extracted) < tolerance
    return abs(extracted - expected) / abs(expected) <= tolerance


def main():
    print("=" * 70)
    print("RCT EXTRACTOR v2 - CONFIDENCE CALIBRATION ANALYSIS")
    print("=" * 70)

    # Load cases
    cases = load_all_cases()
    print(f"\nLoaded {len(cases)} test cases")

    # Separate positive and adversarial cases
    positive_cases = [c for c in cases if not c.get('adversarial', False)]
    adversarial_cases = [c for c in cases if c.get('adversarial', False)]
    print(f"  - Positive cases (should extract): {len(positive_cases)}")
    print(f"  - Adversarial cases (should not extract): {len(adversarial_cases)}")

    # ================================================================
    # PART 1: EXTRACTION ACCURACY ON POSITIVE CASES
    # ================================================================
    print("\n" + "=" * 70)
    print("1. EXTRACTION ACCURACY (Positive Cases)")
    print("=" * 70)

    positive_results = []
    for case in positive_cases:
        expected = case.get('expected', {})
        text = case.get('text', '')
        measure_type = expected.get('measure_type', 'HR')

        expected_value = expected.get(measure_type.lower())
        result, confidence = extract_with_confidence(text, measure_type)

        extracted_value = None
        if result:
            extracted_value = (result.get('hr') or result.get('or') or
                             result.get('rr') or result.get('rd') or result.get('md'))

        is_correct = check_match(extracted_value, expected_value) if expected_value else False
        positive_results.append({
            'case': case,
            'expected': expected_value,
            'extracted': extracted_value,
            'correct': is_correct,
            'confidence': confidence
        })

    correct_count = sum(1 for r in positive_results if r['correct'])
    accuracy = correct_count / len(positive_results) if positive_results else 0
    ci_low, ci_high = clopper_pearson_ci(correct_count, len(positive_results))

    print(f"\nAccuracy: {accuracy*100:.1f}% ({correct_count}/{len(positive_results)})")
    print(f"95% CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%]")

    # ================================================================
    # PART 2: SPECIFICITY ON ADVERSARIAL CASES
    # ================================================================
    print("\n" + "=" * 70)
    print("2. SPECIFICITY (Adversarial Cases)")
    print("=" * 70)

    adversarial_results = []
    for case in adversarial_cases:
        expected = case.get('expected', {})
        text = case.get('text', '')
        measure_type = expected.get('measure_type', 'HR')

        result, confidence = extract_with_confidence(text, measure_type)

        extracted_value = None
        if result:
            extracted_value = (result.get('hr') or result.get('or') or
                             result.get('rr') or result.get('rd') or result.get('md'))

        # For adversarial: correct = did NOT extract anything (or extracted None)
        is_correct = extracted_value is None
        adversarial_results.append({
            'case': case,
            'extracted': extracted_value,
            'correct': is_correct,
            'confidence': confidence
        })

    if adversarial_results:
        reject_count = sum(1 for r in adversarial_results if r['correct'])
        specificity = reject_count / len(adversarial_results)
        spec_ci_low, spec_ci_high = clopper_pearson_ci(reject_count, len(adversarial_results))

        print(f"\nSpecificity (correct rejections): {specificity*100:.1f}% ({reject_count}/{len(adversarial_results)})")
        print(f"95% CI: [{spec_ci_low*100:.1f}%, {spec_ci_high*100:.1f}%]")

        # Show false positives
        false_positives = [r for r in adversarial_results if not r['correct']]
        if false_positives:
            print(f"\nFalse Positives ({len(false_positives)}):")
            for fp in false_positives[:5]:  # Show first 5
                print(f"  - {fp['case']['trial_name']}: extracted {fp['extracted']}")
    else:
        print("\nNo adversarial cases found.")
        specificity = 1.0

    # ================================================================
    # PART 3: ROC ANALYSIS (Combined)
    # ================================================================
    print("\n" + "=" * 70)
    print("3. ROC CURVE ANALYSIS")
    print("=" * 70)

    # For ROC: label=1 means "extraction should succeed", score = confidence
    # True positive: high confidence + should extract + correct extraction
    # True negative: low confidence + should not extract + no extraction
    # False positive: high confidence + should not extract + extraction anyway
    # False negative: low confidence + should extract + no extraction

    # Combine labels and scores
    all_labels = []  # 1 = correct behavior, 0 = incorrect behavior
    all_scores = []  # confidence scores

    for r in positive_results:
        all_labels.append(1 if r['correct'] else 0)
        all_scores.append(r['confidence'])

    for r in adversarial_results:
        # For adversarial: invert confidence (high confidence = bad if extracted)
        # Actually, we want: label=1 if correct rejection, score = 1 - confidence
        all_labels.append(1 if r['correct'] else 0)
        # If we correctly rejected, confidence should be low (close to 0)
        all_scores.append(1 - r['confidence'] if r['correct'] else r['confidence'])

    # ROC for "correct behavior" prediction
    roc = calculate_roc_curve(all_labels, all_scores)
    print(f"\nArea Under ROC Curve (AUC-ROC): {roc['auc']:.4f}")
    print(f"Interpretation: {interpret_auc(roc['auc'])}")

    if roc['auc'] >= 0.9:
        print("  -> Excellent discrimination between correct and incorrect extractions")
    elif roc['auc'] >= 0.8:
        print("  -> Good discrimination - confidence scores are informative")
    elif roc['auc'] >= 0.7:
        print("  -> Fair discrimination - some information in confidence scores")
    else:
        print("  -> Confidence scores need improvement for discrimination")

    # ================================================================
    # PART 4: PRECISION-RECALL ANALYSIS
    # ================================================================
    print("\n" + "=" * 70)
    print("4. PRECISION-RECALL ANALYSIS")
    print("=" * 70)

    pr = calculate_precision_recall_curve(all_labels, all_scores)
    print(f"\nAverage Precision (AP): {pr['average_precision']:.4f}")

    # F1 at different thresholds
    print("\nPerformance at Key Thresholds:")
    print(f"  {'Threshold':<12} {'Precision':<12} {'Recall':<12} {'F1':<12}")
    print(f"  {'-'*48}")

    for i in [len(pr['thresholds'])//4, len(pr['thresholds'])//2, 3*len(pr['thresholds'])//4]:
        if 0 <= i < len(pr['thresholds']):
            prec = pr['precision'][i]
            rec = pr['recall'][i]
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
            print(f"  {pr['thresholds'][i]:<12.3f} {prec:<12.4f} {rec:<12.4f} {f1:<12.4f}")

    # ================================================================
    # PART 5: CALIBRATION ANALYSIS
    # ================================================================
    print("\n" + "=" * 70)
    print("5. CALIBRATION ANALYSIS")
    print("=" * 70)

    # Calibration on positive cases only
    pos_labels = [1 if r['correct'] else 0 for r in positive_results]
    pos_scores = [r['confidence'] for r in positive_results]

    calibration = calculate_calibration_curve(pos_labels, pos_scores)
    print(f"\nExpected Calibration Error (ECE): {calibration['ece']:.4f}")

    if calibration['ece'] < 0.05:
        print("  -> Excellent calibration: confidence scores match actual accuracy")
    elif calibration['ece'] < 0.10:
        print("  -> Good calibration: confidence scores are reasonably accurate")
    elif calibration['ece'] < 0.15:
        print("  -> Fair calibration: some miscalibration present")
    else:
        print("  -> Poor calibration: confidence scores need recalibration")

    print("\nCalibration by Confidence Bin:")
    print(f"  {'Bin':<12} {'Mean Conf.':<15} {'Actual Acc.':<15} {'Gap':<12} {'N':<8}")
    print(f"  {'-'*62}")

    for i in range(len(calibration['mean_predicted'])):
        bin_range = f"{i/10:.1f}-{(i+1)/10:.1f}"
        mean_conf = calibration['mean_predicted'][i]
        actual_acc = calibration['fraction_positive'][i]
        gap = abs(mean_conf - actual_acc)
        count = calibration['bin_counts'][i]
        if count > 0:
            print(f"  {bin_range:<12} {mean_conf:<15.4f} {actual_acc:<15.4f} {gap:<12.4f} {count:<8}")

    # ================================================================
    # PART 6: BY MEASURE TYPE
    # ================================================================
    print("\n" + "=" * 70)
    print("6. ANALYSIS BY MEASURE TYPE")
    print("=" * 70)

    measure_stats = {}
    for r in positive_results:
        mt = r['case'].get('expected', {}).get('measure_type', 'HR')
        if mt not in measure_stats:
            measure_stats[mt] = {'correct': 0, 'total': 0, 'confidences': []}
        measure_stats[mt]['total'] += 1
        if r['correct']:
            measure_stats[mt]['correct'] += 1
        measure_stats[mt]['confidences'].append(r['confidence'])

    print(f"\n  {'Measure':<10} {'N':<8} {'Accuracy':<12} {'Mean Conf.':<15} {'Min Conf.':<12}")
    print(f"  {'-'*57}")

    for mt, stats in sorted(measure_stats.items()):
        n = stats['total']
        acc = stats['correct'] / n if n > 0 else 0
        mean_conf = sum(stats['confidences']) / n if n > 0 else 0
        min_conf = min(stats['confidences']) if stats['confidences'] else 0
        print(f"  {mt:<10} {n:<8} {acc*100:>6.1f}%     {mean_conf:<15.4f} {min_conf:<12.4f}")

    # ================================================================
    # PART 7: OVERALL SUMMARY
    # ================================================================
    print("\n" + "=" * 70)
    print("7. CONFIDENCE CALIBRATION SUMMARY")
    print("=" * 70)

    overall_correct = correct_count + (sum(1 for r in adversarial_results if r['correct']) if adversarial_results else 0)
    overall_total = len(positive_results) + len(adversarial_results)
    overall_accuracy = overall_correct / overall_total if overall_total > 0 else 0

    print(f"""
Dataset:
  - Positive cases: {len(positive_results)}
  - Adversarial cases: {len(adversarial_results)}
  - Total cases: {overall_total}

Classification Performance:
  - Sensitivity (on positive cases): {accuracy*100:.1f}%
  - Specificity (on adversarial cases): {specificity*100:.1f}%
  - Overall Accuracy: {overall_accuracy*100:.1f}%

ROC Analysis:
  - AUC-ROC: {roc['auc']:.4f} ({interpret_auc(roc['auc'])})

Precision-Recall Analysis:
  - Average Precision: {pr['average_precision']:.4f}

Calibration:
  - Expected Calibration Error: {calibration['ece']:.4f}
  - Interpretation: {'Well-calibrated' if calibration['ece'] < 0.1 else 'Needs calibration'}

Confidence Score Distribution:
  - Mean (positive cases): {sum(pos_scores)/len(pos_scores):.4f}
  - Min: {min(pos_scores):.4f}
  - Max: {max(pos_scores):.4f}
""")

    print("=" * 70)


if __name__ == "__main__":
    main()
