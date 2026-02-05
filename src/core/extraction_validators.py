"""
Extraction Validators - Catch Silent Wrongness

Based on Al-Fātiḥah Principle 4: "Accountability"
Hard validators catch impossible values. Soft validators flag inconsistencies.
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
import math

from src.core.extraction_schema import (
    RCTExtraction, Outcome, EffectInputs, TrialArm,
    ExtractedValue, ExtractionStatus
)


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    rule_name: str
    passed: bool
    message: str
    severity: str  # "error", "warning", "info"
    field_path: str  # e.g., "outcomes[0].effect.ci_lower"


class ExtractionValidator:
    """
    Validates RCT extractions using hard and soft rules.

    Hard validators: Catch impossible values (errors)
    Soft validators: Flag inconsistencies (warnings)
    """

    def validate(self, extraction: RCTExtraction) -> Tuple[bool, List[ValidationResult]]:
        """
        Run all validators and return (passed, results).

        Returns:
            (passed, results): passed=True if no errors, results contains all messages
        """
        results = []

        # Hard validators (errors)
        results.extend(self._validate_n_consistency(extraction))
        results.extend(self._validate_ci_bounds(extraction))
        results.extend(self._validate_p_values(extraction))
        results.extend(self._validate_positive_values(extraction))
        results.extend(self._validate_effect_plausibility(extraction))

        # Soft validators (warnings)
        results.extend(self._check_n_analyzed_vs_randomized(extraction))
        results.extend(self._check_missing_critical_fields(extraction))
        results.extend(self._check_outcome_context(extraction))
        results.extend(self._check_arm_balance(extraction))

        # Determine pass/fail
        errors = [r for r in results if r.severity == "error"]
        warnings = [r for r in results if r.severity == "warning"]

        passed = len(errors) == 0

        # Update extraction
        extraction.validation_passed = passed
        extraction.validation_errors = [r.message for r in errors]
        extraction.validation_warnings = [r.message for r in warnings]

        return passed, results

    # ========== HARD VALIDATORS ==========

    def _validate_n_consistency(self, extraction: RCTExtraction) -> List[ValidationResult]:
        """
        Hard: Sum of arm Ns should match total (if both available).
        """
        results = []

        if not extraction.n_randomized_total.is_usable():
            return results

        total = extraction.n_randomized_total.value
        arm_sum = 0
        arm_count = 0

        for i, arm in enumerate(extraction.arms):
            if arm.n_randomized.is_usable():
                arm_sum += arm.n_randomized.value
                arm_count += 1

        if arm_count >= 2:
            # Allow small tolerance for rounding
            tolerance = max(2, total * 0.01)
            if abs(arm_sum - total) > tolerance:
                results.append(ValidationResult(
                    rule_name="n_consistency",
                    passed=False,
                    message=f"N mismatch: arms sum to {arm_sum}, but total is {total}",
                    severity="error",
                    field_path="n_randomized_total"
                ))
            else:
                results.append(ValidationResult(
                    rule_name="n_consistency",
                    passed=True,
                    message=f"N consistent: arms={arm_sum}, total={total}",
                    severity="info",
                    field_path="n_randomized_total"
                ))

        return results

    def _validate_ci_bounds(self, extraction: RCTExtraction) -> List[ValidationResult]:
        """
        Hard: CI lower < point estimate < CI upper (for ratio measures).
        For log-scale measures (HR, OR, RR), CI must bracket the estimate.
        """
        results = []

        for i, outcome in enumerate(extraction.outcomes):
            effect = outcome.effect
            if not effect.point_estimate.is_usable():
                continue
            if not effect.has_complete_ci():
                continue

            pe = effect.point_estimate.value
            lower = effect.ci_lower.value
            upper = effect.ci_upper.value

            # Swap if reversed
            if lower > upper:
                lower, upper = upper, lower

            # Check bounds
            if effect.effect_type in ["HR", "OR", "RR", "IRR"]:
                # Log-scale: PE should be between bounds
                # Allow small tolerance for rounding
                margin = 0.01
                if not (lower - margin <= pe <= upper + margin):
                    results.append(ValidationResult(
                        rule_name="ci_bounds",
                        passed=False,
                        message=f"CI doesn't bracket estimate: {effect.effect_type}={pe}, CI=({lower}, {upper})",
                        severity="error",
                        field_path=f"outcomes[{i}].effect.ci"
                    ))
            elif effect.effect_type in ["MD", "SMD", "ARD"]:
                # Linear scale: same check
                margin = 0.1
                if not (lower - margin <= pe <= upper + margin):
                    results.append(ValidationResult(
                        rule_name="ci_bounds",
                        passed=False,
                        message=f"CI doesn't bracket estimate: {effect.effect_type}={pe}, CI=({lower}, {upper})",
                        severity="error",
                        field_path=f"outcomes[{i}].effect.ci"
                    ))

        return results

    def _validate_p_values(self, extraction: RCTExtraction) -> List[ValidationResult]:
        """
        Hard: P-values must be in [0, 1].
        """
        results = []

        for i, outcome in enumerate(extraction.outcomes):
            if not outcome.effect.p_value.is_usable():
                continue

            p = outcome.effect.p_value.value
            if not (0 <= p <= 1):
                results.append(ValidationResult(
                    rule_name="p_value_range",
                    passed=False,
                    message=f"P-value out of range: {p}",
                    severity="error",
                    field_path=f"outcomes[{i}].effect.p_value"
                ))

        return results

    def _validate_positive_values(self, extraction: RCTExtraction) -> List[ValidationResult]:
        """
        Hard: SD must be positive, N must be positive, ratios must be positive.
        """
        results = []

        # Check Ns
        for i, arm in enumerate(extraction.arms):
            if arm.n_randomized.is_usable() and arm.n_randomized.value <= 0:
                results.append(ValidationResult(
                    rule_name="positive_n",
                    passed=False,
                    message=f"Non-positive N in arm {i}: {arm.n_randomized.value}",
                    severity="error",
                    field_path=f"arms[{i}].n_randomized"
                ))

        # Check ratio effects
        for i, outcome in enumerate(extraction.outcomes):
            effect = outcome.effect
            if effect.effect_type in ["HR", "OR", "RR", "IRR"]:
                if effect.point_estimate.is_usable() and effect.point_estimate.value <= 0:
                    results.append(ValidationResult(
                        rule_name="positive_ratio",
                        passed=False,
                        message=f"Non-positive ratio: {effect.effect_type}={effect.point_estimate.value}",
                        severity="error",
                        field_path=f"outcomes[{i}].effect.point_estimate"
                    ))

            # Check SDs
            if effect.sd_treatment.is_usable() and effect.sd_treatment.value <= 0:
                results.append(ValidationResult(
                    rule_name="positive_sd",
                    passed=False,
                    message=f"Non-positive SD: {effect.sd_treatment.value}",
                    severity="error",
                    field_path=f"outcomes[{i}].effect.sd_treatment"
                ))

        return results

    def _validate_effect_plausibility(self, extraction: RCTExtraction) -> List[ValidationResult]:
        """
        Hard: Check for implausible effect sizes.
        HR/OR/RR outside [0.01, 100] is suspicious.
        """
        results = []

        for i, outcome in enumerate(extraction.outcomes):
            effect = outcome.effect
            if not effect.point_estimate.is_usable():
                continue

            pe = effect.point_estimate.value

            if effect.effect_type in ["HR", "OR", "RR", "IRR"]:
                if pe < 0.01 or pe > 100:
                    results.append(ValidationResult(
                        rule_name="effect_plausibility",
                        passed=False,
                        message=f"Implausible {effect.effect_type}: {pe} (expected 0.01-100)",
                        severity="warning",  # Warning, not error - could be real
                        field_path=f"outcomes[{i}].effect.point_estimate"
                    ))
            elif effect.effect_type == "SMD":
                # SMD > 3 is very unusual
                if abs(pe) > 3:
                    results.append(ValidationResult(
                        rule_name="effect_plausibility",
                        passed=False,
                        message=f"Unusually large SMD: {pe} (expected |SMD| < 3)",
                        severity="warning",
                        field_path=f"outcomes[{i}].effect.point_estimate"
                    ))

        return results

    # ========== SOFT VALIDATORS ==========

    def _check_n_analyzed_vs_randomized(self, extraction: RCTExtraction) -> List[ValidationResult]:
        """
        Soft: N analyzed often differs from N randomized - flag if only one appears.
        """
        results = []

        for i, arm in enumerate(extraction.arms):
            has_randomized = arm.n_randomized.is_usable()
            has_analyzed = arm.n_analyzed.is_usable()

            if has_randomized and has_analyzed:
                if arm.n_analyzed.value > arm.n_randomized.value:
                    results.append(ValidationResult(
                        rule_name="n_analyzed_check",
                        passed=False,
                        message=f"Arm {i}: N analyzed ({arm.n_analyzed.value}) > N randomized ({arm.n_randomized.value})",
                        severity="warning",
                        field_path=f"arms[{i}].n_analyzed"
                    ))
            elif has_randomized and not has_analyzed:
                results.append(ValidationResult(
                    rule_name="n_analyzed_check",
                    passed=True,
                    message=f"Arm {i}: Only N randomized found, N analyzed not specified",
                    severity="info",
                    field_path=f"arms[{i}]"
                ))

        return results

    def _check_missing_critical_fields(self, extraction: RCTExtraction) -> List[ValidationResult]:
        """
        Soft: Warn about missing critical fields for meta-analysis.
        """
        results = []

        # Check for any outcomes
        if not extraction.outcomes:
            results.append(ValidationResult(
                rule_name="missing_outcomes",
                passed=False,
                message="No outcomes extracted",
                severity="warning",
                field_path="outcomes"
            ))

        # Check for arms
        if len(extraction.arms) < 2:
            results.append(ValidationResult(
                rule_name="missing_arms",
                passed=False,
                message=f"Expected ≥2 arms, found {len(extraction.arms)}",
                severity="warning",
                field_path="arms"
            ))

        # Check each outcome for meta-analysis readiness
        for i, outcome in enumerate(extraction.outcomes):
            if not outcome.effect.has_meta_analysis_inputs():
                results.append(ValidationResult(
                    rule_name="incomplete_meta_inputs",
                    passed=False,
                    message=f"Outcome '{outcome.name.value}' lacks complete meta-analysis inputs",
                    severity="warning",
                    field_path=f"outcomes[{i}]"
                ))

        return results

    def _check_outcome_context(self, extraction: RCTExtraction) -> List[ValidationResult]:
        """
        Soft: Every outcome should have name and timepoint.
        Addresses critique: "CIs without knowing what it measures"
        """
        results = []

        for i, outcome in enumerate(extraction.outcomes):
            issues = []

            if not outcome.name.is_usable():
                issues.append("missing name")
            if not outcome.timepoint.is_usable():
                issues.append("missing timepoint")
            if outcome.is_primary.status == ExtractionStatus.MISSING:
                issues.append("primary/secondary unknown")

            if issues:
                results.append(ValidationResult(
                    rule_name="outcome_context",
                    passed=False,
                    message=f"Outcome {i}: {', '.join(issues)}",
                    severity="warning",
                    field_path=f"outcomes[{i}]"
                ))

        return results

    def _check_arm_balance(self, extraction: RCTExtraction) -> List[ValidationResult]:
        """
        Soft: Check for reasonable arm balance (not 10:1 ratio unless specified).
        """
        results = []

        ns = [arm.n_randomized.value for arm in extraction.arms if arm.n_randomized.is_usable()]

        if len(ns) >= 2:
            ratio = max(ns) / min(ns) if min(ns) > 0 else float('inf')
            if ratio > 5:
                results.append(ValidationResult(
                    rule_name="arm_balance",
                    passed=False,
                    message=f"Unusual arm imbalance: ratio {ratio:.1f}:1",
                    severity="warning",
                    field_path="arms"
                ))

        return results


def validate_extraction(extraction: RCTExtraction) -> Tuple[bool, List[ValidationResult]]:
    """Convenience function to validate an extraction."""
    validator = ExtractionValidator()
    return validator.validate(extraction)
