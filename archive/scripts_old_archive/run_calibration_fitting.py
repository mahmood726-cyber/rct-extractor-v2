"""
Calibration Fitting Script for RCT Extractor v2.16
==================================================

Fits confidence calibration model using external validation results.
Saves calibration model for production use.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add paths
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))
sys.path.insert(0, str(script_dir / 'src' / 'core'))
sys.path.insert(0, str(script_dir / 'data'))

from confidence_calibration import (
    ConfidenceCalibrator,
    CalibratedExtractor,
    format_calibration_report
)

from external_validation_dataset import ALL_EXTERNAL_VALIDATION_TRIALS
from run_extended_validation_v8 import extract_effect_estimates

try:
    from ml_extractor import ConfidenceScorer
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


def collect_validation_data():
    """
    Collect (confidence, is_correct) pairs from external validation.
    """
    print("Collecting validation data...")

    validation_pairs = []
    scorer = ConfidenceScorer() if ML_AVAILABLE else None

    for trial in ALL_EXTERNAL_VALIDATION_TRIALS:
        # Get automated extractions
        text = trial.source_text
        extractions = extract_effect_estimates(text)

        # Build consensus for comparison
        consensus = []
        for ext_a in trial.extractor_a:
            consensus.append({
                'effect_type': ext_a.effect_type,
                'value': ext_a.effect_size,
                'ci_lower': ext_a.ci_lower,
                'ci_upper': ext_a.ci_upper,
            })

        # Match extractions to consensus
        for ext in extractions:
            # Calculate confidence
            if scorer:
                confidence = scorer.score(text, ext)
            else:
                confidence = 0.85

            # Check if correct
            is_correct = False
            for cons in consensus:
                if (ext.get('type') == cons['effect_type'] and
                    abs(ext.get('effect_size', 0) - cons['value']) < 0.02):
                    is_correct = True
                    break

            validation_pairs.append((confidence, is_correct))

    print(f"Collected {len(validation_pairs)} validation pairs")
    return validation_pairs


def main():
    """Fit and save calibration model"""
    print("=" * 60)
    print("CONFIDENCE CALIBRATION FITTING")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Collect validation data
    validation_pairs = collect_validation_data()

    if not validation_pairs:
        print("No validation data collected!")
        return

    # Fit calibration model
    print("\nFitting calibration model...")
    calibrator = ConfidenceCalibrator(n_bins=10)
    model = calibrator.fit(validation_pairs)

    # Print report
    report = format_calibration_report(model)
    print(report)

    # Test calibration
    print("\n## EXAMPLE CALIBRATION")
    test_confidences = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70]
    for raw in test_confidences:
        calibrated = calibrator.calibrate(raw)
        recommendation = calibrator.get_recommendation(raw)
        print(f"Raw: {raw:.2f} -> Calibrated: {calibrated:.3f} [{recommendation}]")

    # Save calibration model
    output_dir = script_dir / "output"
    output_dir.mkdir(exist_ok=True)

    calibration_file = output_dir / "calibration_model.json"
    calibrator.save(str(calibration_file))
    print(f"\nCalibration model saved to: {calibration_file}")

    # Summary
    print("\n" + "=" * 60)
    print("CALIBRATION SUMMARY")
    print("=" * 60)
    print(f"\nSamples: {model.n_samples}")
    print(f"ECE: {model.ece:.4f}")
    print(f"MCE: {model.mce:.4f}")
    print(f"Slope: {model.slope:.3f} (ideal = 1.0)")
    print(f"Intercept: {model.intercept:.3f} (ideal = 0.0)")

    print("\nThresholds for deployment:")
    for target, thresh in sorted(model.thresholds.items(), reverse=True):
        print(f"  {target}: confidence >= {thresh:.3f}")

    # Recommendations
    print("\n## DEPLOYMENT RECOMMENDATIONS")
    thresh_95 = model.thresholds.get("95%", 0.9)
    thresh_80 = model.thresholds.get("80%", 0.7)

    print(f"""
1. HIGH_CONFIDENCE (auto-accept): confidence >= {thresh_95:.2f}
   - Expected accuracy: 95%+
   - No human verification needed

2. VERIFY_RECOMMENDED: {thresh_80:.2f} <= confidence < {thresh_95:.2f}
   - Expected accuracy: 80-95%
   - Flag for human review

3. MANUAL_EXTRACTION_NEEDED: confidence < {thresh_80:.2f}
   - Expected accuracy: <80%
   - Require manual extraction
""")

    print("=" * 60)


if __name__ == "__main__":
    main()
