"""
Confidence Calibration Module for RCT Extractor v2.16
======================================================

Implements empirical calibration of confidence scores:
1. Calibration curve fitting
2. Threshold determination for target accuracy
3. Calibrated probability output
4. Reliability diagrams
"""

import math
import statistics
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from pathlib import Path


@dataclass
class CalibrationBin:
    """A single bin in the calibration curve"""
    bin_start: float
    bin_end: float
    mean_confidence: float
    observed_accuracy: float
    count: int
    correct: int


@dataclass
class CalibrationModel:
    """Fitted calibration model"""
    bins: List[CalibrationBin]
    ece: float  # Expected Calibration Error
    mce: float  # Maximum Calibration Error
    slope: float  # Calibration slope (ideal = 1)
    intercept: float  # Calibration intercept (ideal = 0)
    thresholds: Dict[str, float]  # Threshold for each accuracy level
    n_samples: int
    version: str = "v2.16"


class ConfidenceCalibrator:
    """
    Calibrates confidence scores based on observed accuracy.

    Usage:
        1. Fit on validation data: calibrator.fit(predictions, actuals)
        2. Apply calibration: calibrated = calibrator.calibrate(raw_confidence)
        3. Get threshold: thresh = calibrator.get_threshold(target_accuracy=0.95)
    """

    def __init__(self, n_bins: int = 10):
        self.n_bins = n_bins
        self.model: Optional[CalibrationModel] = None
        self.fitted = False

    def fit(self, predictions: List[Tuple[float, bool]]) -> CalibrationModel:
        """
        Fit calibration model on validation data.

        Args:
            predictions: List of (confidence, is_correct) tuples

        Returns:
            CalibrationModel with fitted parameters
        """
        if not predictions:
            # Return an identity calibration model (no adjustment)
            self.model = CalibrationModel(
                bins=[], ece=0.0, mce=0.0, slope=1.0, intercept=0.0,
                thresholds={}, n_samples=0,
            )
            self.fitted = True
            return self.model

        # Sort by confidence
        sorted_preds = sorted(predictions, key=lambda x: x[0])
        n = len(sorted_preds)

        # Guard against degenerate calibration with too few samples
        if n < self.n_bins * 2:
            self.model = CalibrationModel(
                bins=[], ece=0.0, mce=0.0, slope=1.0, intercept=0.0,
                thresholds={}, n_samples=n,
            )
            self.fitted = False
            return self.model

        # Create bins
        bin_size = max(1, n // self.n_bins)
        bins = []

        for i in range(0, n, bin_size):
            bin_preds = sorted_preds[i:i + bin_size]
            if not bin_preds:
                continue

            confidences = [p[0] for p in bin_preds]
            correct = sum(1 for p in bin_preds if p[1])

            bin_obj = CalibrationBin(
                bin_start=min(confidences),
                bin_end=max(confidences),
                mean_confidence=statistics.mean(confidences),
                observed_accuracy=correct / len(bin_preds),
                count=len(bin_preds),
                correct=correct
            )
            bins.append(bin_obj)

        # Calculate ECE and MCE
        ece = 0
        mce = 0
        for b in bins:
            calibration_error = abs(b.observed_accuracy - b.mean_confidence)
            ece += calibration_error * b.count / n
            mce = max(mce, calibration_error)

        # Calculate slope and intercept (linear regression)
        if len(bins) >= 2:
            x = [b.mean_confidence for b in bins]
            y = [b.observed_accuracy for b in bins]
            slope, intercept = self._linear_regression(x, y)
        else:
            slope, intercept = 1.0, 0.0

        # Determine thresholds for various accuracy targets
        thresholds = self._determine_thresholds(bins)

        self.model = CalibrationModel(
            bins=bins,
            ece=ece,
            mce=mce,
            slope=slope,
            intercept=intercept,
            thresholds=thresholds,
            n_samples=n
        )
        self.fitted = True

        return self.model

    def _linear_regression(self, x: List[float], y: List[float]) -> Tuple[float, float]:
        """Simple linear regression"""
        n = len(x)
        if n < 2:
            return 1.0, 0.0

        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)

        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
        denominator = sum((xi - x_mean) ** 2 for xi in x)

        if denominator == 0:
            return 1.0, 0.0

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        return slope, intercept

    def _determine_thresholds(self, bins: List[CalibrationBin]) -> Dict[str, float]:
        """Determine confidence thresholds for various accuracy levels.

        Uses cumulative accuracy from the highest-confidence bin downward
        to handle non-monotonic accuracy bins correctly.
        """
        thresholds = {}
        target_accuracies = [0.99, 0.95, 0.90, 0.85, 0.80, 0.75]

        # Sort bins by confidence descending
        sorted_bins = sorted(bins, key=lambda x: x.bin_start, reverse=True)

        for target in target_accuracies:
            threshold = 1.0  # Default to maximum
            cumulative_correct = 0
            cumulative_count = 0

            # Walk from highest confidence bin down, computing cumulative accuracy
            for b in sorted_bins:
                cumulative_correct += b.correct
                cumulative_count += b.count
                cumulative_accuracy = cumulative_correct / cumulative_count if cumulative_count > 0 else 0
                if cumulative_accuracy >= target:
                    threshold = b.bin_start
                else:
                    break

            thresholds[f"{int(target*100)}%"] = threshold

        return thresholds

    def calibrate(self, raw_confidence: float) -> float:
        """
        Apply calibration to a raw confidence score.

        Args:
            raw_confidence: Raw confidence score (0-1)

        Returns:
            Calibrated probability (0-1)
        """
        if not self.fitted or not self.model:
            return raw_confidence

        # Use interpolation from calibration bins
        for i, b in enumerate(self.model.bins):
            if b.bin_start <= raw_confidence <= b.bin_end:
                # Return observed accuracy for this bin (step-function calibration)
                return b.observed_accuracy

        # If outside bins, use linear model
        calibrated = self.model.slope * raw_confidence + self.model.intercept
        return max(0, min(1, calibrated))

    def get_threshold(self, target_accuracy: float = 0.95) -> float:
        """
        Get confidence threshold for target accuracy.

        Args:
            target_accuracy: Desired accuracy (e.g., 0.95 for 95%)

        Returns:
            Confidence threshold
        """
        if not self.fitted or not self.model:
            return 0.8  # Default

        key = f"{int(target_accuracy * 100)}%"
        return self.model.thresholds.get(key, 0.8)

    def get_recommendation(self, confidence: float) -> str:
        """
        Get human-readable recommendation based on confidence.

        Args:
            confidence: Raw confidence score

        Returns:
            Recommendation string
        """
        if not self.fitted:
            if confidence >= 0.9:
                return "HIGH_CONFIDENCE"
            elif confidence >= 0.7:
                return "VERIFY_RECOMMENDED"
            else:
                return "MANUAL_EXTRACTION_NEEDED"

        thresh_95 = self.get_threshold(0.95)
        thresh_80 = self.get_threshold(0.80)

        if confidence >= thresh_95:
            return "HIGH_CONFIDENCE"
        elif confidence >= thresh_80:
            return "VERIFY_RECOMMENDED"
        else:
            return "MANUAL_EXTRACTION_NEEDED"

    def save(self, filepath: str):
        """Save calibration model to file"""
        if not self.model:
            return

        data = {
            "version": self.model.version,
            "n_samples": self.model.n_samples,
            "ece": self.model.ece,
            "mce": self.model.mce,
            "slope": self.model.slope,
            "intercept": self.model.intercept,
            "thresholds": self.model.thresholds,
            "bins": [
                {
                    "bin_start": b.bin_start,
                    "bin_end": b.bin_end,
                    "mean_confidence": b.mean_confidence,
                    "observed_accuracy": b.observed_accuracy,
                    "count": b.count,
                    "correct": b.correct
                }
                for b in self.model.bins
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self, filepath: str):
        """Load calibration model from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)

        bins = [
            CalibrationBin(
                bin_start=b["bin_start"],
                bin_end=b["bin_end"],
                mean_confidence=b["mean_confidence"],
                observed_accuracy=b["observed_accuracy"],
                count=b["count"],
                correct=b["correct"]
            )
            for b in data["bins"]
        ]

        self.model = CalibrationModel(
            bins=bins,
            ece=data["ece"],
            mce=data["mce"],
            slope=data["slope"],
            intercept=data["intercept"],
            thresholds=data["thresholds"],
            n_samples=data["n_samples"],
            version=data.get("version", "unknown")
        )
        self.fitted = True


@dataclass
class CalibratedExtraction:
    """An extraction with calibrated confidence"""
    effect_type: str
    effect_size: float
    ci_lower: float
    ci_upper: float
    raw_confidence: float
    calibrated_confidence: float
    recommendation: str
    expected_accuracy: float


class CalibratedExtractor:
    """
    Wrapper around the main extractor that applies calibration.
    """

    def __init__(self, calibrator: ConfidenceCalibrator = None):
        self.calibrator = calibrator or ConfidenceCalibrator()

    def extract_with_calibration(
        self,
        text: str,
        extractions: List[Dict],
        raw_confidences: List[float]
    ) -> List[CalibratedExtraction]:
        """
        Apply calibration to extraction results.

        Args:
            text: Source text
            extractions: Raw extraction results
            raw_confidences: Raw confidence scores

        Returns:
            List of CalibratedExtraction objects
        """
        calibrated_results = []

        for ext, raw_conf in zip(extractions, raw_confidences):
            cal_conf = self.calibrator.calibrate(raw_conf) if self.calibrator.fitted else raw_conf
            recommendation = self.calibrator.get_recommendation(raw_conf)

            calibrated_results.append(CalibratedExtraction(
                effect_type=ext.get('type', ''),
                effect_size=ext.get('effect_size', 0),
                ci_lower=ext.get('ci_lower', ext.get('ci_low', 0)),
                ci_upper=ext.get('ci_upper', ext.get('ci_high', 0)),
                raw_confidence=raw_conf,
                calibrated_confidence=cal_conf,
                recommendation=recommendation,
                expected_accuracy=cal_conf
            ))

        return calibrated_results


def format_calibration_report(model: CalibrationModel) -> str:
    """Format a calibration report"""
    report = []
    report.append("=" * 60)
    report.append("CONFIDENCE CALIBRATION REPORT")
    report.append("=" * 60)

    report.append(f"\nSamples used for calibration: {model.n_samples}")
    report.append(f"Number of bins: {len(model.bins)}")

    report.append("\n## CALIBRATION METRICS")
    report.append(f"Expected Calibration Error (ECE): {model.ece:.4f}")
    report.append(f"Maximum Calibration Error (MCE): {model.mce:.4f}")
    report.append(f"Calibration Slope: {model.slope:.3f} (ideal = 1.0)")
    report.append(f"Calibration Intercept: {model.intercept:.3f} (ideal = 0.0)")

    # Interpretation
    if model.ece < 0.05:
        interp = "Well calibrated"
    elif model.ece < 0.10:
        interp = "Reasonably calibrated"
    elif model.ece < 0.15:
        interp = "Moderately miscalibrated"
    else:
        interp = "Poorly calibrated"
    report.append(f"Interpretation: {interp}")

    report.append("\n## CALIBRATION BINS")
    report.append(f"{'Confidence':<15} {'Obs. Accuracy':<15} {'Count':<10} {'Gap':<10}")
    for b in model.bins:
        gap = abs(b.observed_accuracy - b.mean_confidence)
        report.append(f"{b.mean_confidence:.3f}          {b.observed_accuracy:.3f}           {b.count:<10} {gap:.3f}")

    report.append("\n## RECOMMENDED THRESHOLDS")
    for target, threshold in sorted(model.thresholds.items(), reverse=True):
        report.append(f"For {target} accuracy: confidence >= {threshold:.3f}")

    report.append("\n" + "=" * 60)

    return "\n".join(report)


# =============================================================================
# INTEGRATION WITH MAIN EXTRACTOR
# =============================================================================

def create_calibrated_extractor(calibration_file: str = None) -> CalibratedExtractor:
    """
    Create a calibrated extractor, loading existing calibration if available.

    Args:
        calibration_file: Path to saved calibration model (optional)

    Returns:
        CalibratedExtractor instance
    """
    calibrator = ConfidenceCalibrator()

    if calibration_file and Path(calibration_file).exists():
        calibrator.load(calibration_file)

    return CalibratedExtractor(calibrator)


def fit_calibration_from_validation(validation_results: List[Tuple[float, bool]]) -> ConfidenceCalibrator:
    """
    Fit calibration model from validation results.

    Args:
        validation_results: List of (confidence, is_correct) tuples

    Returns:
        Fitted ConfidenceCalibrator
    """
    calibrator = ConfidenceCalibrator()
    calibrator.fit(validation_results)
    return calibrator
