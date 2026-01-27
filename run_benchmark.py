"""
Run benchmark on all gold standard files
Reports:
- Overall accuracy by value extraction
- CI extraction accuracy (separate)
- Kappa agreement statistics
"""
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.extractor import NumericParser
from src.benchmark.statistics import cohens_kappa, clopper_pearson_ci, wilson_ci


def run_benchmark():
    """Run benchmark on all gold standard files"""
    gold_dir = Path(__file__).parent / 'data' / 'gold'

    results = {
        'total': 0,
        'correct': 0,
        'by_measure_type': {},
        'failed_cases': [],
        # CI extraction tracking
        'ci_total': 0,
        'ci_low_correct': 0,
        'ci_high_correct': 0,
        'ci_both_correct': 0,
        # For Kappa calculation
        'human_ratings': [],  # 1 = correct extraction
        'system_ratings': []  # 1 = system thinks it's confident
    }

    # Tolerance for comparison
    tolerance = 0.05
    ci_tolerance = 0.10

    for jsonl_file in gold_dir.glob("*.jsonl"):
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    expected = data.get('expected', {})
                    text = data.get('text', '')
                    measure_type = expected.get('measure_type', 'HR')
                    trial_name = data.get('trial_name', f'{jsonl_file.stem}_{line_num}')

                    # Track by measure type
                    if measure_type not in results['by_measure_type']:
                        results['by_measure_type'][measure_type] = {
                            'total': 0, 'correct': 0,
                            'ci_total': 0, 'ci_low_correct': 0,
                            'ci_high_correct': 0, 'ci_both_correct': 0
                        }

                    results['total'] += 1
                    results['by_measure_type'][measure_type]['total'] += 1

                    # Extract based on measure type
                    extracted_value = None
                    extracted_ci_low = None
                    extracted_ci_high = None
                    expected_value = None
                    expected_ci_low = None
                    expected_ci_high = None

                    if measure_type == 'HR':
                        expected_value = expected.get('hr')
                        expected_ci_low = expected.get('hr_ci_low')
                        expected_ci_high = expected.get('hr_ci_high')
                        result = NumericParser.parse_hazard_ratio(text)
                        if result:
                            extracted_value = result.get('hr')
                            extracted_ci_low = result.get('ci_low')
                            extracted_ci_high = result.get('ci_high')

                    elif measure_type == 'OR':
                        expected_value = expected.get('or')
                        expected_ci_low = expected.get('or_ci_low')
                        expected_ci_high = expected.get('or_ci_high')
                        result = NumericParser.parse_odds_ratio(text)
                        if result:
                            extracted_value = result.get('or')
                            extracted_ci_low = result.get('ci_low')
                            extracted_ci_high = result.get('ci_high')

                    elif measure_type == 'RR':
                        expected_value = expected.get('rr')
                        expected_ci_low = expected.get('rr_ci_low')
                        expected_ci_high = expected.get('rr_ci_high')
                        result = NumericParser.parse_relative_risk(text)
                        if result:
                            extracted_value = result.get('rr')
                            extracted_ci_low = result.get('ci_low')
                            extracted_ci_high = result.get('ci_high')

                    elif measure_type == 'RD':
                        expected_value = expected.get('rd')
                        expected_ci_low = expected.get('rd_ci_low')
                        expected_ci_high = expected.get('rd_ci_high')
                        result = NumericParser.parse_risk_difference(text)
                        if result:
                            extracted_value = result.get('rd')
                            extracted_ci_low = result.get('ci_low')
                            extracted_ci_high = result.get('ci_high')

                    elif measure_type == 'MD':
                        expected_value = expected.get('md')
                        expected_ci_low = expected.get('md_ci_low')
                        expected_ci_high = expected.get('md_ci_high')
                        result = NumericParser.parse_mean_difference(text)
                        if result:
                            extracted_value = result.get('md')
                            extracted_ci_low = result.get('ci_low')
                            extracted_ci_high = result.get('ci_high')

                    # Check if value is correct
                    is_correct = False
                    if expected_value is not None and extracted_value is not None:
                        if expected_value == 0:
                            is_correct = abs(extracted_value) < tolerance
                        else:
                            rel_error = abs(extracted_value - expected_value) / abs(expected_value)
                            is_correct = rel_error <= tolerance

                    if is_correct:
                        results['correct'] += 1
                        results['by_measure_type'][measure_type]['correct'] += 1
                        results['human_ratings'].append(1)
                        results['system_ratings'].append(1)
                    else:
                        results['failed_cases'].append({
                            'trial': trial_name,
                            'measure_type': measure_type,
                            'expected': expected_value,
                            'extracted': extracted_value,
                            'text': text[:100] + '...' if len(text) > 100 else text
                        })
                        results['human_ratings'].append(0)
                        results['system_ratings'].append(1 if extracted_value is not None else 0)

                    # Check CI extraction (separate from value)
                    if expected_ci_low is not None:
                        results['ci_total'] += 1
                        results['by_measure_type'][measure_type]['ci_total'] += 1

                        ci_low_ok = False
                        ci_high_ok = False

                        if extracted_ci_low is not None:
                            if abs(expected_ci_low) < 0.001:
                                ci_low_ok = abs(extracted_ci_low) < ci_tolerance
                            else:
                                ci_low_ok = abs(extracted_ci_low - expected_ci_low) / abs(expected_ci_low) <= ci_tolerance

                        if extracted_ci_high is not None and expected_ci_high is not None:
                            if abs(expected_ci_high) < 0.001:
                                ci_high_ok = abs(extracted_ci_high) < ci_tolerance
                            else:
                                ci_high_ok = abs(extracted_ci_high - expected_ci_high) / abs(expected_ci_high) <= ci_tolerance

                        if ci_low_ok:
                            results['ci_low_correct'] += 1
                            results['by_measure_type'][measure_type]['ci_low_correct'] += 1

                        if ci_high_ok:
                            results['ci_high_correct'] += 1
                            results['by_measure_type'][measure_type]['ci_high_correct'] += 1

                        if ci_low_ok and ci_high_ok:
                            results['ci_both_correct'] += 1
                            results['by_measure_type'][measure_type]['ci_both_correct'] += 1

                except json.JSONDecodeError as e:
                    print(f"Error parsing {jsonl_file}:{line_num}: {e}")

    return results


def print_report(results):
    """Print benchmark report"""
    print("=" * 70)
    print("RCT EXTRACTOR v2 - COMPREHENSIVE BENCHMARK REPORT")
    print("=" * 70)

    total = results['total']
    correct = results['correct']
    accuracy = correct / total * 100 if total > 0 else 0

    print(f"\n1. POINT ESTIMATE EXTRACTION ACCURACY")
    print("-" * 50)
    print(f"Overall: {accuracy:.1f}% ({correct}/{total})")

    # Calculate 95% CI for accuracy using Clopper-Pearson
    ci_low, ci_high = clopper_pearson_ci(correct, total, 0.95)
    print(f"95% CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%]")

    print("\nBy Measure Type:")
    for mt, stats in sorted(results['by_measure_type'].items()):
        mt_acc = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
        mt_ci_low, mt_ci_high = clopper_pearson_ci(stats['correct'], stats['total'], 0.95)
        print(f"  {mt:6s}: {mt_acc:5.1f}% ({stats['correct']}/{stats['total']}) "
              f"[{mt_ci_low*100:.1f}%-{mt_ci_high*100:.1f}%]")

    print(f"\n2. CONFIDENCE INTERVAL EXTRACTION ACCURACY")
    print("-" * 50)
    ci_total = results['ci_total']
    if ci_total > 0:
        ci_low_acc = results['ci_low_correct'] / ci_total * 100
        ci_high_acc = results['ci_high_correct'] / ci_total * 100
        ci_both_acc = results['ci_both_correct'] / ci_total * 100

        print(f"CI Lower Bound: {ci_low_acc:.1f}% ({results['ci_low_correct']}/{ci_total})")
        print(f"CI Upper Bound: {ci_high_acc:.1f}% ({results['ci_high_correct']}/{ci_total})")
        print(f"Both CI Bounds: {ci_both_acc:.1f}% ({results['ci_both_correct']}/{ci_total})")

        print("\nCI Extraction by Measure Type:")
        for mt, stats in sorted(results['by_measure_type'].items()):
            if stats['ci_total'] > 0:
                mt_ci_both = stats['ci_both_correct'] / stats['ci_total'] * 100
                print(f"  {mt:6s}: {mt_ci_both:5.1f}% both bounds correct "
                      f"({stats['ci_both_correct']}/{stats['ci_total']})")
    else:
        print("No CI data in gold standard")

    print(f"\n3. AGREEMENT STATISTICS (Kappa)")
    print("-" * 50)
    if results['human_ratings'] and results['system_ratings']:
        kappa, kappa_ci_low, kappa_ci_high = cohens_kappa(
            results['human_ratings'],
            results['system_ratings']
        )
        # Interpret kappa
        if kappa >= 0.81:
            interpretation = "Almost Perfect"
        elif kappa >= 0.61:
            interpretation = "Substantial"
        elif kappa >= 0.41:
            interpretation = "Moderate"
        elif kappa >= 0.21:
            interpretation = "Fair"
        else:
            interpretation = "Slight"

        print(f"Cohen's Kappa: {kappa:.4f} ({interpretation})")
        print(f"95% CI: [{kappa_ci_low:.4f}, {kappa_ci_high:.4f}]")

        # Agreement rate
        agreement = sum(1 for h, s in zip(results['human_ratings'], results['system_ratings']) if h == s)
        agreement_rate = agreement / len(results['human_ratings']) * 100
        print(f"Raw Agreement: {agreement_rate:.1f}% ({agreement}/{len(results['human_ratings'])})")

    print(f"\n4. SUMMARY")
    print("-" * 50)
    print(f"Total test cases: {total}")
    print(f"Therapeutic areas: 6 (Cardiology, Oncology, Infectious Disease, ")
    print(f"                      Diabetes/Metabolic, Psychiatry/Neurology, ")
    print(f"                      Respiratory/Autoimmune)")
    print(f"Effect measures: HR, OR, RR, RD, MD")

    if results['failed_cases']:
        print(f"\nFAILED CASES ({len(results['failed_cases'])}):")
        print("-" * 50)
        for case in results['failed_cases'][:10]:
            print(f"  [{case['measure_type']}] {case['trial']}: "
                  f"expected={case['expected']}, extracted={case['extracted']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    results = run_benchmark()
    print_report(results)
