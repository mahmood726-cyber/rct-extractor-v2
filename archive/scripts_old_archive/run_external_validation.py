"""
External Validation Runner for RCT Extractor v2.16
===================================================

Runs comprehensive external validation against 120+ real clinical trials
with dual manual extraction comparison.

Outputs:
1. Sensitivity/specificity metrics
2. Inter-rater reliability (Cohen's kappa)
3. Bland-Altman analysis
4. Calibration assessment
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add paths for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))
sys.path.insert(0, str(script_dir / 'src' / 'core'))
sys.path.insert(0, str(script_dir / 'data'))

from external_validation_dataset import (
    ALL_EXTERNAL_VALIDATION_TRIALS,
    ExternalValidationTrial,
    ExtractionDifficulty,
    calculate_overall_agreement,
    print_dataset_summary
)

from external_validation import (
    ExternalValidator,
    InterRaterReliability,
    ExtractionMatch,
    ValidationMetrics,
    BlandAltmanResult,
    CalibrationResult,
    format_validation_report,
    interpret_kappa,
    get_confidence_threshold
)

# Import the main extractor
from run_extended_validation_v8 import extract_effect_estimates

# Import ML confidence scorer
try:
    from ml_extractor import ConfidenceScorer, EnsembleExtractor
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


def run_automated_extraction(trial: ExternalValidationTrial) -> tuple:
    """
    Run automated extraction on a trial's source text.

    Returns:
        (extractions, confidence_scores)
    """
    text = trial.source_text
    extractions = extract_effect_estimates(text)

    # Calculate confidence scores if ML available
    confidence_scores = []
    if ML_AVAILABLE:
        scorer = ConfidenceScorer()
        for ext in extractions:
            confidence = scorer.score(text, ext)
            confidence_scores.append(confidence)
    else:
        # Default confidence based on pattern match
        confidence_scores = [0.85] * len(extractions)

    return extractions, confidence_scores


def build_consensus(trial: ExternalValidationTrial) -> list:
    """
    Build consensus from dual manual extractions.

    For now, uses extractor A as the primary (simulating consensus).
    In real validation, this would be the adjudicated result.
    """
    consensus = []

    for ext_a in trial.extractor_a:
        # Find matching extraction from B
        matched = False
        for ext_b in trial.extractor_b:
            if (ext_a.effect_type == ext_b.effect_type and
                abs(ext_a.effect_size - ext_b.effect_size) < 0.02):
                # Agreement - use as consensus
                consensus.append({
                    'effect_type': ext_a.effect_type,
                    'value': ext_a.effect_size,
                    'ci_lower': ext_a.ci_lower,
                    'ci_upper': ext_a.ci_upper,
                    'outcome': ext_a.outcome,
                    'comparison': ext_a.comparison,
                    'analysis_population': ext_a.analysis_population,
                    'timepoint': ext_a.timepoint,
                })
                matched = True
                break

        if not matched:
            # Use extractor A value (would need adjudication in practice)
            consensus.append({
                'effect_type': ext_a.effect_type,
                'value': ext_a.effect_size,
                'ci_lower': ext_a.ci_lower,
                'ci_upper': ext_a.ci_upper,
                'outcome': ext_a.outcome,
                'comparison': ext_a.comparison,
                'analysis_population': ext_a.analysis_population,
                'timepoint': ext_a.timepoint,
            })

    return consensus


def calculate_inter_rater_reliability(trials: list) -> dict:
    """Calculate inter-rater reliability across all trials"""
    irr = InterRaterReliability()

    for trial in trials:
        # Match extractions between A and B
        for ext_a in trial.extractor_a:
            # Find corresponding extraction from B
            for ext_b in trial.extractor_b:
                if ext_a.effect_type == ext_b.effect_type:
                    irr.add_comparison(
                        {
                            'effect_type': ext_a.effect_type,
                            'value': ext_a.effect_size,
                            'ci_lower': ext_a.ci_lower,
                            'ci_upper': ext_a.ci_upper,
                        },
                        {
                            'effect_type': ext_b.effect_type,
                            'value': ext_b.effect_size,
                            'ci_lower': ext_b.ci_lower,
                            'ci_upper': ext_b.ci_upper,
                        }
                    )
                    break

    return irr.calculate_agreement()


def run_validation(verbose: bool = False) -> dict:
    """Run full external validation"""
    print("=" * 70)
    print("EXTERNAL VALIDATION v2.16")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Print dataset summary
    print_dataset_summary()

    # Initialize validator
    validator = ExternalValidator()

    # Track results by category
    results_by_area = {}
    results_by_difficulty = {}
    results_by_journal = {}

    print("\n" + "=" * 70)
    print("RUNNING AUTOMATED EXTRACTION")
    print("=" * 70)

    for trial in ALL_EXTERNAL_VALIDATION_TRIALS:
        # Get consensus from manual extractions
        consensus = build_consensus(trial)

        # Run automated extraction
        extractions, confidence_scores = run_automated_extraction(trial)

        # Validate
        matches = validator.validate_extraction(
            trial.trial_name,
            extractions,
            consensus,
            confidence_scores
        )

        # Track by category
        area = trial.therapeutic_area.split(" - ")[0]
        if area not in results_by_area:
            results_by_area[area] = {'correct': 0, 'total': 0}
        results_by_area[area]['total'] += len(consensus)
        results_by_area[area]['correct'] += len(matches)

        # Track by difficulty
        diff = trial.difficulty.value
        if diff not in results_by_difficulty:
            results_by_difficulty[diff] = {'correct': 0, 'total': 0}
        results_by_difficulty[diff]['total'] += len(consensus)
        results_by_difficulty[diff]['correct'] += len(matches)

        # Track by journal
        journal = trial.journal
        if journal not in results_by_journal:
            results_by_journal[journal] = {'correct': 0, 'total': 0}
        results_by_journal[journal]['total'] += len(consensus)
        results_by_journal[journal]['correct'] += len(matches)

        # Print progress
        pct = len(matches) / len(consensus) * 100 if consensus else 0
        status = "[OK]" if pct >= 80 else "[PARTIAL]" if pct >= 50 else "[MISS]"
        if verbose or pct < 80:
            print(f"  {status} {trial.trial_name}: {len(matches)}/{len(consensus)} ({pct:.0f}%)")

    # Calculate comprehensive metrics
    print("\n" + "=" * 70)
    print("CALCULATING METRICS")
    print("=" * 70)

    metrics = validator.calculate_metrics()
    bland_altman = validator.bland_altman_analysis()
    calibration = validator.calibration_analysis()

    # Calculate inter-rater reliability
    irr_metrics = calculate_inter_rater_reliability(ALL_EXTERNAL_VALIDATION_TRIALS)

    # Print report
    report = format_validation_report(metrics, bland_altman, calibration)
    print(report)

    # Print additional breakdowns
    print("\n## RESULTS BY THERAPEUTIC AREA\n")
    print(f"{'Area':<25} {'Correct':<10} {'Total':<10} {'Accuracy':<12}")
    for area, data in sorted(results_by_area.items()):
        acc = data['correct'] / data['total'] * 100 if data['total'] > 0 else 0
        print(f"{area:<25} {data['correct']:<10} {data['total']:<10} {acc:.1f}%")

    print("\n## RESULTS BY DIFFICULTY\n")
    print(f"{'Difficulty':<15} {'Correct':<10} {'Total':<10} {'Accuracy':<12}")
    for diff, data in sorted(results_by_difficulty.items()):
        acc = data['correct'] / data['total'] * 100 if data['total'] > 0 else 0
        print(f"{diff:<15} {data['correct']:<10} {data['total']:<10} {acc:.1f}%")

    print("\n## RESULTS BY JOURNAL\n")
    print(f"{'Journal':<15} {'Correct':<10} {'Total':<10} {'Accuracy':<12}")
    for journal, data in sorted(results_by_journal.items(), key=lambda x: -x[1]['total']):
        acc = data['correct'] / data['total'] * 100 if data['total'] > 0 else 0
        print(f"{journal:<15} {data['correct']:<10} {data['total']:<10} {acc:.1f}%")

    print("\n## INTER-RATER RELIABILITY (Dual Manual Extraction)\n")
    print(f"Effect Type Agreement: {irr_metrics.get('effect_type_agreement', 0):.1%}")
    print(f"Value Agreement: {irr_metrics.get('value_agreement', 0):.1%}")
    print(f"CI Agreement: {irr_metrics.get('ci_agreement', 0):.1%}")
    print(f"Cohen's Kappa: {irr_metrics.get('cohens_kappa', 0):.3f}")
    print(f"  Interpretation: {interpret_kappa(irr_metrics.get('cohens_kappa', 0))}")

    # Confidence thresholds
    if calibration:
        print("\n## RECOMMENDED CONFIDENCE THRESHOLDS\n")
        thresh_95 = get_confidence_threshold(calibration, 0.95)
        thresh_90 = get_confidence_threshold(calibration, 0.90)
        thresh_80 = get_confidence_threshold(calibration, 0.80)
        print(f"For 95% accuracy: confidence >= {thresh_95:.2f}")
        print(f"For 90% accuracy: confidence >= {thresh_90:.2f}")
        print(f"For 80% accuracy: confidence >= {thresh_80:.2f}")

    print("\n" + "=" * 70)

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "version": "v2.16-external-validation",
        "summary": {
            "total_trials": metrics.total_trials,
            "total_effects": metrics.total_effects,
            "true_positives": metrics.true_positives,
            "false_positives": metrics.false_positives,
            "false_negatives": metrics.false_negatives,
            "sensitivity": metrics.sensitivity,
            "specificity": metrics.specificity,
            "precision": metrics.precision,
            "f1_score": metrics.f1_score,
            "accuracy": metrics.accuracy,
            "cohen_kappa": metrics.cohen_kappa,
        },
        "error_metrics": {
            "mean_error": metrics.mean_error,
            "std_error": metrics.std_error,
            "mae": metrics.mean_absolute_error,
            "rmse": metrics.rmse,
        },
        "bland_altman": {
            "bias": bland_altman.mean_difference if bland_altman else None,
            "sd": bland_altman.std_difference if bland_altman else None,
            "upper_limit": bland_altman.upper_limit if bland_altman else None,
            "lower_limit": bland_altman.lower_limit if bland_altman else None,
            "percent_within_limits": bland_altman.percent_within_limits if bland_altman else None,
        },
        "calibration": {
            "ece": calibration.expected_calibration_error if calibration else None,
            "mce": calibration.max_calibration_error if calibration else None,
            "slope": calibration.calibration_slope if calibration else None,
            "intercept": calibration.calibration_intercept if calibration else None,
        },
        "inter_rater_reliability": irr_metrics,
        "by_therapeutic_area": results_by_area,
        "by_difficulty": results_by_difficulty,
        "by_journal": results_by_journal,
    }

    output_file = Path(__file__).parent / "output" / "external_validation.json"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return output


def main():
    """Run external validation"""
    import argparse
    parser = argparse.ArgumentParser(description="External Validation")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show all trials")
    args = parser.parse_args()

    run_validation(verbose=args.verbose)


if __name__ == "__main__":
    main()
