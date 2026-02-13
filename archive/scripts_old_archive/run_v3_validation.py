"""
RCT Extractor v3.0 Comprehensive Validation
============================================

Validates the enhanced extractor against 200+ test cases.
Reports sensitivity, specificity, calibration, and automation metrics.
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
    calculate_automation_metrics,
    to_dict
)
from expanded_validation_v3 import ALL_VALIDATION_CASES, get_validation_stats


def run_validation():
    """Run comprehensive validation"""
    print("=" * 70)
    print("RCT EXTRACTOR v3.0 - COMPREHENSIVE VALIDATION")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Get dataset stats
    stats = get_validation_stats()
    print(f"\nValidation Dataset: {stats['total']} cases")
    print(f"By type: {stats['by_type']}")
    print(f"By difficulty: {stats['by_difficulty']}")

    # Initialize extractor
    extractor = EnhancedExtractor()

    # Results tracking
    results = {
        'total': 0,
        'correct': 0,
        'incorrect': 0,
        'missed': 0,
        'by_type': defaultdict(lambda: {'total': 0, 'correct': 0, 'missed': 0}),
        'by_difficulty': defaultdict(lambda: {'total': 0, 'correct': 0, 'missed': 0}),
        'extractions': [],
        'failures': [],
    }

    # Run validation
    print("\n" + "=" * 70)
    print("RUNNING VALIDATION")
    print("=" * 70)

    for case in ALL_VALIDATION_CASES:
        results['total'] += 1
        results['by_type'][case.expected_type]['total'] += 1
        results['by_difficulty'][case.difficulty]['total'] += 1

        # Extract
        extractions = extractor.extract(case.text)

        # Check if we found the expected extraction
        found_match = False
        for ext in extractions:
            if (ext.effect_type.value == case.expected_type and
                abs(ext.point_estimate - case.expected_value) < 0.02):
                # Check CI
                if ext.ci:
                    ci_low_match = abs(ext.ci.lower - case.expected_ci_low) < 0.02
                    ci_high_match = abs(ext.ci.upper - case.expected_ci_high) < 0.02
                    if ci_low_match and ci_high_match:
                        found_match = True
                        results['correct'] += 1
                        results['by_type'][case.expected_type]['correct'] += 1
                        results['by_difficulty'][case.difficulty]['correct'] += 1
                        results['extractions'].append(ext)
                        break

        if not found_match:
            results['missed'] += 1
            results['by_type'][case.expected_type]['missed'] += 1
            results['by_difficulty'][case.difficulty]['missed'] += 1
            results['failures'].append({
                'case': case,
                'extractions': extractions,
            })

    # Calculate metrics
    sensitivity = results['correct'] / results['total'] if results['total'] > 0 else 0
    miss_rate = results['missed'] / results['total'] if results['total'] > 0 else 0

    # Print results
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)

    print(f"\n## OVERALL METRICS")
    print(f"Total cases: {results['total']}")
    print(f"Correct extractions: {results['correct']}")
    print(f"Missed extractions: {results['missed']}")
    print(f"Sensitivity: {sensitivity:.1%}")
    print(f"Miss rate: {miss_rate:.1%}")

    # By effect type
    print(f"\n## BY EFFECT TYPE")
    print(f"{'Type':<8} {'Total':<8} {'Correct':<10} {'Missed':<8} {'Sensitivity':<12}")
    print("-" * 50)
    for etype in sorted(results['by_type'].keys()):
        data = results['by_type'][etype]
        sens = data['correct'] / data['total'] if data['total'] > 0 else 0
        print(f"{etype:<8} {data['total']:<8} {data['correct']:<10} {data['missed']:<8} {sens:.1%}")

    # By difficulty
    print(f"\n## BY DIFFICULTY")
    print(f"{'Difficulty':<12} {'Total':<8} {'Correct':<10} {'Missed':<8} {'Sensitivity':<12}")
    print("-" * 55)
    for diff in ['easy', 'moderate', 'hard']:
        data = results['by_difficulty'][diff]
        if data['total'] > 0:
            sens = data['correct'] / data['total']
            print(f"{diff:<12} {data['total']:<8} {data['correct']:<10} {data['missed']:<8} {sens:.1%}")

    # Automation metrics
    if results['extractions']:
        print(f"\n## AUTOMATION METRICS")
        auto_metrics = calculate_automation_metrics(results['extractions'])
        print(f"Total extractions: {auto_metrics.total}")
        print(f"Full auto: {auto_metrics.full_auto} ({auto_metrics.full_auto/auto_metrics.total:.1%})")
        print(f"Spot check: {auto_metrics.spot_check} ({auto_metrics.spot_check/auto_metrics.total:.1%})")
        print(f"Verify: {auto_metrics.verify} ({auto_metrics.verify/auto_metrics.total:.1%})")
        print(f"Manual: {auto_metrics.manual} ({auto_metrics.manual/auto_metrics.total:.1%})")
        print(f"Automation rate: {auto_metrics.automation_rate:.1%}")
        print(f"Human effort reduction: {auto_metrics.human_effort_reduction:.1%}")

    # Sample failures
    if results['failures']:
        print(f"\n## SAMPLE FAILURES (first 10)")
        print("-" * 70)
        for i, fail in enumerate(results['failures'][:10]):
            case = fail['case']
            print(f"\n{i+1}. Expected: {case.expected_type} {case.expected_value} ({case.expected_ci_low}-{case.expected_ci_high})")
            print(f"   Text: {case.text[:80]}...")
            if fail['extractions']:
                print(f"   Got: {[(e.effect_type.value, e.point_estimate) for e in fail['extractions']]}")
            else:
                print(f"   Got: No extractions")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    target_sensitivity = 0.95
    target_automation = 0.80

    print(f"\nSensitivity: {sensitivity:.1%} (target: {target_sensitivity:.0%})")
    if sensitivity >= target_sensitivity:
        print("  STATUS: TARGET MET")
    else:
        gap = target_sensitivity - sensitivity
        cases_needed = int(gap * results['total'])
        print(f"  STATUS: {gap:.1%} below target ({cases_needed} more correct extractions needed)")

    if results['extractions']:
        print(f"\nAutomation rate: {auto_metrics.automation_rate:.1%} (target: {target_automation:.0%})")
        if auto_metrics.automation_rate >= target_automation:
            print("  STATUS: TARGET MET")
        else:
            print(f"  STATUS: {target_automation - auto_metrics.automation_rate:.1%} below target")

        print(f"\nHuman effort reduction: {auto_metrics.human_effort_reduction:.1%}")

    print("\n" + "=" * 70)

    return {
        'sensitivity': sensitivity,
        'automation_rate': auto_metrics.automation_rate if results['extractions'] else 0,
        'human_effort_reduction': auto_metrics.human_effort_reduction if results['extractions'] else 0,
        'by_type': dict(results['by_type']),
        'by_difficulty': dict(results['by_difficulty']),
    }


if __name__ == "__main__":
    run_validation()
