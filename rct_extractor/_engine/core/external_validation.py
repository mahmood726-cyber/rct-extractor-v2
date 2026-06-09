"""
External Validation Framework for RCT Extractor v2.16
======================================================

Implements:
1. Automated vs manual extraction comparison
2. Inter-rater reliability (Cohen's kappa)
3. Bland-Altman analysis
4. Sensitivity/specificity metrics
5. Calibration assessment
"""

import math
import statistics
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any
from enum import Enum
from collections import defaultdict


@dataclass
class ExtractionMatch:
    """A match between automated and manual extraction"""
    trial_name: str
    effect_type: str
    automated_value: float
    manual_value: float  # Consensus value
    automated_ci_lower: float
    automated_ci_upper: float
    manual_ci_lower: float
    manual_ci_upper: float
    confidence: float
    is_correct: bool
    error: float  # automated - manual
    relative_error: float  # (automated - manual) / manual


@dataclass
class ValidationMetrics:
    """Comprehensive validation metrics"""
    # Basic accuracy
    total_trials: int
    total_effects: int
    true_positives: int  # Correctly extracted
    false_positives: int  # Extracted but wrong
    false_negatives: int  # Missed extractions
    true_negatives: int  # Correctly rejected non-effects

    # Derived metrics
    sensitivity: float  # TP / (TP + FN)
    specificity: float  # TN / (TN + FP)
    precision: float    # TP / (TP + FP)
    f1_score: float     # 2 * (precision * recall) / (precision + recall)
    accuracy: float     # (TP + TN) / total

    # Agreement metrics
    cohen_kappa: float
    percent_agreement: float

    # Error metrics
    mean_error: float
    std_error: float
    mean_absolute_error: float
    rmse: float

    # By effect type
    metrics_by_type: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # By difficulty
    metrics_by_difficulty: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class BlandAltmanResult:
    """Bland-Altman analysis result"""
    mean_difference: float  # Bias
    std_difference: float
    upper_limit: float  # Mean + 1.96*SD
    lower_limit: float  # Mean - 1.96*SD
    points: List[Tuple[float, float]]  # (mean, difference) pairs
    percent_within_limits: float


@dataclass
class CalibrationResult:
    """Calibration assessment result"""
    bins: List[Tuple[float, float, float, int]]  # (bin_start, bin_end, observed_accuracy, n)
    expected_calibration_error: float
    max_calibration_error: float
    calibration_slope: float
    calibration_intercept: float


class ExternalValidator:
    """
    External validation framework comparing automated vs manual extraction.
    """

    def __init__(self):
        self.matches: List[ExtractionMatch] = []
        self.trials_validated = 0
        self.effects_expected = 0
        self.effects_found = 0

    def add_match(self, match: ExtractionMatch):
        """Add a validation match"""
        self.matches.append(match)

    def validate_extraction(
        self,
        trial_name: str,
        automated_results: List[Dict],
        manual_consensus: List[Dict],
        confidence_scores: List[float] = None
    ) -> List[ExtractionMatch]:
        """
        Compare automated extraction against manual consensus.

        Args:
            trial_name: Name of the trial
            automated_results: List of automated extractions
            manual_consensus: List of consensus manual extractions
            confidence_scores: Confidence scores for automated extractions

        Returns:
            List of ExtractionMatch objects
        """
        matches = []
        self.trials_validated += 1
        self.effects_expected += len(manual_consensus)

        # Match automated to manual by effect type and approximate value
        matched_manual = set()

        for i, auto in enumerate(automated_results):
            confidence = confidence_scores[i] if confidence_scores else 0.8

            best_match = None
            best_error = float('inf')

            for j, manual in enumerate(manual_consensus):
                if j in matched_manual:
                    continue

                # Check if effect types match
                if auto.get('type') != manual.get('effect_type'):
                    continue

                # Calculate error
                auto_value = auto.get('effect_size', 0)
                manual_value = manual.get('value', 0)
                error = abs(auto_value - manual_value)
                relative_error = error / abs(manual_value) if manual_value != 0 else float('inf')

                # Accept if within 5% relative error
                if relative_error < 0.05 and error < best_error:
                    best_match = (j, manual)
                    best_error = error

            if best_match:
                j, manual = best_match
                matched_manual.add(j)
                self.effects_found += 1

                auto_value = auto.get('effect_size', 0)
                manual_value = manual.get('value', 0)
                error = auto_value - manual_value
                rel_error = error / abs(manual_value) if manual_value != 0 else 0

                match = ExtractionMatch(
                    trial_name=trial_name,
                    effect_type=auto.get('type', ''),
                    automated_value=auto_value,
                    manual_value=manual_value,
                    automated_ci_lower=auto.get('ci_lower', auto.get('ci_low', 0)),
                    automated_ci_upper=auto.get('ci_upper', auto.get('ci_high', 0)),
                    manual_ci_lower=manual.get('ci_lower', 0),
                    manual_ci_upper=manual.get('ci_upper', 0),
                    confidence=confidence,
                    is_correct=True,
                    error=error,
                    relative_error=rel_error
                )
                matches.append(match)
                self.matches.append(match)

        return matches

    def calculate_metrics(self) -> ValidationMetrics:
        """Calculate comprehensive validation metrics"""
        if not self.matches:
            return None

        # Basic counts
        tp = sum(1 for m in self.matches if m.is_correct)
        fp = sum(1 for m in self.matches if not m.is_correct)
        fn = self.effects_expected - self.effects_found
        tn = 0  # Depends on adversarial test results

        # Derived metrics
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 1
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = sensitivity
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0

        # Agreement
        percent_agreement = tp / len(self.matches) if self.matches else 0
        kappa = self._calculate_cohens_kappa()

        # Error metrics
        errors = [m.error for m in self.matches if m.is_correct]
        abs_errors = [abs(e) for e in errors]

        mean_error = statistics.mean(errors) if errors else 0
        std_error = statistics.stdev(errors) if len(errors) > 1 else 0
        mae = statistics.mean(abs_errors) if abs_errors else 0
        rmse = math.sqrt(statistics.mean([e**2 for e in errors])) if errors else 0

        # By effect type
        metrics_by_type = self._calculate_metrics_by_group('effect_type')

        return ValidationMetrics(
            total_trials=self.trials_validated,
            total_effects=self.effects_expected,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            true_negatives=tn,
            sensitivity=sensitivity,
            specificity=specificity,
            precision=precision,
            f1_score=f1,
            accuracy=accuracy,
            cohen_kappa=kappa,
            percent_agreement=percent_agreement,
            mean_error=mean_error,
            std_error=std_error,
            mean_absolute_error=mae,
            rmse=rmse,
            metrics_by_type=metrics_by_type
        )

    def _calculate_cohens_kappa(self) -> float:
        """
        Calculate Cohen's kappa for inter-rater reliability.

        For extraction validation, we compare:
        - Rater 1: Automated extraction
        - Rater 2: Manual consensus

        Categories: correct extraction, incorrect extraction
        """
        if not self.matches:
            return 0.0

        n = len(self.matches)
        correct = sum(1 for m in self.matches if m.is_correct)

        # Observed agreement
        po = correct / n

        # Expected agreement (by chance)
        # Assuming both raters have similar accuracy
        pe = (correct / n) ** 2 + ((n - correct) / n) ** 2

        # Cohen's kappa
        if pe == 1:
            return 1.0

        kappa = (po - pe) / (1 - pe)
        return kappa

    def _calculate_metrics_by_group(self, group_key: str) -> Dict[str, Dict[str, float]]:
        """Calculate metrics grouped by a key"""
        groups = defaultdict(list)

        for match in self.matches:
            key = getattr(match, group_key, 'unknown')
            groups[key].append(match)

        metrics = {}
        for key, matches in groups.items():
            correct = sum(1 for m in matches if m.is_correct)
            total = len(matches)
            errors = [m.error for m in matches if m.is_correct]

            metrics[key] = {
                'count': total,
                'accuracy': correct / total if total > 0 else 0,
                'mean_error': statistics.mean(errors) if errors else 0,
                'mae': statistics.mean([abs(e) for e in errors]) if errors else 0,
            }

        return metrics

    def bland_altman_analysis(self) -> BlandAltmanResult:
        """
        Perform Bland-Altman analysis comparing automated vs manual extraction.

        Returns:
            BlandAltmanResult with bias, limits of agreement, and plot data
        """
        if not self.matches:
            return None

        # Calculate means and differences for each pair
        points = []
        differences = []

        for match in self.matches:
            if match.is_correct:
                mean_val = (match.automated_value + match.manual_value) / 2
                diff = match.automated_value - match.manual_value
                points.append((mean_val, diff))
                differences.append(diff)

        if not differences:
            return None

        # Calculate statistics
        mean_diff = statistics.mean(differences)
        std_diff = statistics.stdev(differences) if len(differences) > 1 else 0

        # Limits of agreement (95%)
        upper_limit = mean_diff + 1.96 * std_diff
        lower_limit = mean_diff - 1.96 * std_diff

        # Percent within limits
        within = sum(1 for d in differences if lower_limit <= d <= upper_limit)
        percent_within = within / len(differences) if differences else 0

        return BlandAltmanResult(
            mean_difference=mean_diff,
            std_difference=std_diff,
            upper_limit=upper_limit,
            lower_limit=lower_limit,
            points=points,
            percent_within_limits=percent_within
        )

    def calibration_analysis(self, n_bins: int = 10) -> CalibrationResult:
        """
        Assess calibration of confidence scores.

        A well-calibrated model should have:
        - Confidence of 0.8 means 80% of extractions are correct

        Args:
            n_bins: Number of calibration bins

        Returns:
            CalibrationResult with calibration metrics
        """
        if not self.matches:
            return None

        # Sort matches by confidence
        sorted_matches = sorted(self.matches, key=lambda m: m.confidence)

        # Create bins
        bin_size = len(sorted_matches) // n_bins
        if bin_size == 0:
            bin_size = 1

        bins = []
        ece_sum = 0  # Expected Calibration Error
        mce = 0      # Maximum Calibration Error

        for i in range(0, len(sorted_matches), bin_size):
            bin_matches = sorted_matches[i:i+bin_size]
            if not bin_matches:
                continue

            bin_start = bin_matches[0].confidence
            bin_end = bin_matches[-1].confidence
            n = len(bin_matches)

            # Mean predicted confidence
            mean_confidence = statistics.mean(m.confidence for m in bin_matches)

            # Observed accuracy
            observed_accuracy = sum(1 for m in bin_matches if m.is_correct) / n

            bins.append((bin_start, bin_end, observed_accuracy, n))

            # ECE contribution
            calibration_error = abs(observed_accuracy - mean_confidence)
            ece_sum += calibration_error * n
            mce = max(mce, calibration_error)

        ece = ece_sum / len(sorted_matches) if sorted_matches else 0

        # Calibration slope/intercept (simple linear regression)
        if len(bins) >= 2:
            x = [statistics.mean([b[0], b[1]]) for b in bins]  # Mean confidence
            y = [b[2] for b in bins]  # Observed accuracy

            x_mean = statistics.mean(x)
            y_mean = statistics.mean(y)

            numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
            denominator = sum((xi - x_mean) ** 2 for xi in x)

            slope = numerator / denominator if denominator != 0 else 1
            intercept = y_mean - slope * x_mean
        else:
            slope = 1
            intercept = 0

        return CalibrationResult(
            bins=bins,
            expected_calibration_error=ece,
            max_calibration_error=mce,
            calibration_slope=slope,
            calibration_intercept=intercept
        )


class InterRaterReliability:
    """
    Calculate inter-rater reliability between two manual extractors.
    """

    def __init__(self):
        self.comparisons: List[Tuple[Dict, Dict]] = []

    def add_comparison(self, extractor_a: Dict, extractor_b: Dict):
        """Add a comparison between two extractors"""
        self.comparisons.append((extractor_a, extractor_b))

    def calculate_agreement(self) -> Dict[str, float]:
        """Calculate agreement metrics"""
        if not self.comparisons:
            return {}

        # Effect type agreement
        type_agree = sum(
            1 for a, b in self.comparisons
            if a.get('effect_type') == b.get('effect_type')
        )

        # Value agreement (within tolerance)
        value_agree = sum(
            1 for a, b in self.comparisons
            if abs(a.get('value', 0) - b.get('value', 0)) < 0.02
        )

        # CI agreement
        ci_agree = sum(
            1 for a, b in self.comparisons
            if (abs(a.get('ci_lower', 0) - b.get('ci_lower', 0)) < 0.02 and
                abs(a.get('ci_upper', 0) - b.get('ci_upper', 0)) < 0.02)
        )

        n = len(self.comparisons)

        return {
            'effect_type_agreement': type_agree / n if n > 0 else 0,
            'value_agreement': value_agree / n if n > 0 else 0,
            'ci_agreement': ci_agree / n if n > 0 else 0,
            'overall_agreement': (type_agree + value_agree + ci_agree) / (3 * n) if n > 0 else 0,
            'cohens_kappa': self._calculate_kappa()
        }

    def _calculate_kappa(self) -> float:
        """Calculate Cohen's kappa for categorical agreement"""
        if not self.comparisons:
            return 0.0

        # For effect type agreement
        n = len(self.comparisons)
        agree = sum(
            1 for a, b in self.comparisons
            if a.get('effect_type') == b.get('effect_type')
        )

        po = agree / n

        # Expected agreement
        types_a = defaultdict(int)
        types_b = defaultdict(int)

        for a, b in self.comparisons:
            types_a[a.get('effect_type', '')] += 1
            types_b[b.get('effect_type', '')] += 1

        pe = sum(
            (types_a.get(t, 0) / n) * (types_b.get(t, 0) / n)
            for t in set(types_a.keys()) | set(types_b.keys())
        )

        if pe == 1:
            return 1.0

        kappa = (po - pe) / (1 - pe)
        return kappa


def format_validation_report(
    metrics: ValidationMetrics,
    bland_altman: BlandAltmanResult,
    calibration: CalibrationResult
) -> str:
    """Format a comprehensive validation report"""
    report = []
    report.append("=" * 70)
    report.append("EXTERNAL VALIDATION REPORT")
    report.append("=" * 70)

    report.append("\n## SUMMARY STATISTICS\n")
    report.append(f"Trials validated: {metrics.total_trials}")
    report.append(f"Effects expected: {metrics.total_effects}")
    report.append(f"Effects correctly extracted: {metrics.true_positives}")
    report.append(f"False positives: {metrics.false_positives}")
    report.append(f"False negatives: {metrics.false_negatives}")

    report.append("\n## PERFORMANCE METRICS\n")
    report.append(f"Sensitivity (Recall): {metrics.sensitivity:.3f}")
    report.append(f"Specificity: {metrics.specificity:.3f}")
    report.append(f"Precision: {metrics.precision:.3f}")
    report.append(f"F1 Score: {metrics.f1_score:.3f}")
    report.append(f"Overall Accuracy: {metrics.accuracy:.3f}")

    report.append("\n## AGREEMENT METRICS\n")
    report.append(f"Percent Agreement: {metrics.percent_agreement:.1%}")
    report.append(f"Cohen's Kappa: {metrics.cohen_kappa:.3f}")
    kappa_interp = interpret_kappa(metrics.cohen_kappa)
    report.append(f"  Interpretation: {kappa_interp}")

    report.append("\n## ERROR METRICS\n")
    report.append(f"Mean Error (Bias): {metrics.mean_error:.4f}")
    report.append(f"Standard Deviation: {metrics.std_error:.4f}")
    report.append(f"Mean Absolute Error: {metrics.mean_absolute_error:.4f}")
    report.append(f"Root Mean Square Error: {metrics.rmse:.4f}")

    if bland_altman:
        report.append("\n## BLAND-ALTMAN ANALYSIS\n")
        report.append(f"Mean Difference (Bias): {bland_altman.mean_difference:.4f}")
        report.append(f"SD of Differences: {bland_altman.std_difference:.4f}")
        report.append(f"Upper Limit of Agreement: {bland_altman.upper_limit:.4f}")
        report.append(f"Lower Limit of Agreement: {bland_altman.lower_limit:.4f}")
        report.append(f"% Within Limits: {bland_altman.percent_within_limits:.1%}")

    if calibration:
        report.append("\n## CALIBRATION ASSESSMENT\n")
        report.append(f"Expected Calibration Error (ECE): {calibration.expected_calibration_error:.4f}")
        report.append(f"Maximum Calibration Error (MCE): {calibration.max_calibration_error:.4f}")
        report.append(f"Calibration Slope: {calibration.calibration_slope:.3f}")
        report.append(f"Calibration Intercept: {calibration.calibration_intercept:.3f}")

        report.append("\nCalibration Bins:")
        report.append(f"{'Confidence Range':<20} {'Observed Accuracy':<20} {'N':<10}")
        for start, end, obs_acc, n in calibration.bins:
            report.append(f"{start:.2f} - {end:.2f}         {obs_acc:.3f}                {n}")

    if metrics.metrics_by_type:
        report.append("\n## METRICS BY EFFECT TYPE\n")
        report.append(f"{'Type':<10} {'Count':<10} {'Accuracy':<12} {'MAE':<12}")
        for etype, m in sorted(metrics.metrics_by_type.items()):
            report.append(f"{etype:<10} {m['count']:<10} {m['accuracy']:.3f}        {m['mae']:.4f}")

    report.append("\n" + "=" * 70)

    return "\n".join(report)


def interpret_kappa(kappa: float) -> str:
    """Interpret Cohen's kappa value"""
    if kappa < 0:
        return "Poor (less than chance)"
    elif kappa < 0.20:
        return "Slight agreement"
    elif kappa < 0.40:
        return "Fair agreement"
    elif kappa < 0.60:
        return "Moderate agreement"
    elif kappa < 0.80:
        return "Substantial agreement"
    else:
        return "Almost perfect agreement"


def get_confidence_threshold(calibration: CalibrationResult, target_accuracy: float = 0.95) -> float:
    """
    Determine confidence threshold for target accuracy.

    Args:
        calibration: Calibration result
        target_accuracy: Desired accuracy (default 0.95)

    Returns:
        Confidence threshold where observed accuracy >= target
    """
    if not calibration or not calibration.bins:
        return 0.8  # Default

    # Find the lowest confidence bin where accuracy >= target
    for start, end, obs_acc, n in reversed(calibration.bins):
        if obs_acc >= target_accuracy:
            return start

    # If no bin meets target, return the highest threshold
    return calibration.bins[-1][1] if calibration.bins else 0.9
