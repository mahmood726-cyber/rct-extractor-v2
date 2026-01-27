"""
Validators for RCT extraction.
Every extracted value passes through these validators.
Failed validation -> Review Queue (never silent failure).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Any
from enum import Enum
import re

from ..core.models import (
    ExtractionRecord, BinaryOutcome, HazardRatioCI, OddsRatioCI,
    RiskRatioCI, MeanDifference, Arm, ReviewQueueItem, ReviewSeverity,
    Provenance, ExtractionConfidence
)


class ValidationResult(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ValidationIssue:
    """Single validation issue"""
    code: str
    message: str
    severity: ReviewSeverity
    field: Optional[str] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None


@dataclass
class ValidationReport:
    """Complete validation report for one extraction"""
    record_id: str
    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    confidence: ExtractionConfidence = ExtractionConfidence.REVIEW_REQUIRED

    def add_issue(self, issue: ValidationIssue):
        self.issues.append(issue)
        if issue.severity == ReviewSeverity.ERROR:
            self.passed = False


# ============================================================
# INDIVIDUAL VALIDATORS
# ============================================================

def validate_binary_outcome(outcome: BinaryOutcome) -> List[ValidationIssue]:
    """Validate binary outcome (events/n)"""
    issues = []

    # Events must be <= n
    if outcome.events > outcome.n:
        issues.append(ValidationIssue(
            code="EVENTS_GT_N",
            message=f"Events ({outcome.events}) cannot exceed total ({outcome.n})",
            severity=ReviewSeverity.ERROR,
            field="events",
            expected=f"<= {outcome.n}",
            actual=outcome.events
        ))

    # n must be positive
    if outcome.n <= 0:
        issues.append(ValidationIssue(
            code="N_NOT_POSITIVE",
            message=f"Total n must be positive, got {outcome.n}",
            severity=ReviewSeverity.ERROR,
            field="n",
            expected="> 0",
            actual=outcome.n
        ))

    # Events must be non-negative
    if outcome.events < 0:
        issues.append(ValidationIssue(
            code="EVENTS_NEGATIVE",
            message=f"Events cannot be negative, got {outcome.events}",
            severity=ReviewSeverity.ERROR,
            field="events",
            expected=">= 0",
            actual=outcome.events
        ))

    # Percentage consistency check (if provided)
    if outcome.percentage is not None:
        expected_pct = (outcome.events / outcome.n) * 100
        if abs(outcome.percentage - expected_pct) > 1.0:  # Allow 1% tolerance
            issues.append(ValidationIssue(
                code="PERCENTAGE_MISMATCH",
                message=f"Reported percentage ({outcome.percentage}%) doesn't match calculated ({expected_pct:.1f}%)",
                severity=ReviewSeverity.WARNING,
                field="percentage",
                expected=f"{expected_pct:.1f}%",
                actual=f"{outcome.percentage}%"
            ))

    # Provenance check
    if not outcome.provenance or not outcome.provenance.raw_text:
        issues.append(ValidationIssue(
            code="MISSING_PROVENANCE",
            message="Binary outcome missing provenance",
            severity=ReviewSeverity.ERROR,
            field="provenance"
        ))

    return issues


def validate_hazard_ratio(hr: HazardRatioCI) -> List[ValidationIssue]:
    """Validate hazard ratio with CI"""
    issues = []

    # HR must be positive
    if hr.hr <= 0:
        issues.append(ValidationIssue(
            code="HR_NOT_POSITIVE",
            message=f"Hazard ratio must be positive, got {hr.hr}",
            severity=ReviewSeverity.ERROR,
            field="hr",
            expected="> 0",
            actual=hr.hr
        ))

    # NEW: HR plausibility check (unusual values get warning)
    if hr.hr > 0:
        if hr.hr < 0.1 or hr.hr > 10.0:
            issues.append(ValidationIssue(
                code="HR_IMPLAUSIBLE",
                message=f"Hazard ratio {hr.hr} is outside typical range [0.1, 10.0]",
                severity=ReviewSeverity.WARNING,
                field="hr",
                expected="[0.1, 10.0]",
                actual=hr.hr
            ))
        elif hr.hr < 0.3 or hr.hr > 3.0:
            issues.append(ValidationIssue(
                code="HR_UNUSUAL",
                message=f"Hazard ratio {hr.hr} is outside common range [0.3, 3.0]",
                severity=ReviewSeverity.INFO,
                field="hr",
                expected="[0.3, 3.0]",
                actual=hr.hr
            ))

    # CI bounds must be positive
    if hr.ci_low <= 0 or hr.ci_high <= 0:
        issues.append(ValidationIssue(
            code="CI_NOT_POSITIVE",
            message=f"CI bounds must be positive, got [{hr.ci_low}, {hr.ci_high}]",
            severity=ReviewSeverity.ERROR,
            field="ci",
            expected="> 0",
            actual=f"[{hr.ci_low}, {hr.ci_high}]"
        ))

    # CI lower < upper
    if hr.ci_low >= hr.ci_high:
        issues.append(ValidationIssue(
            code="CI_INVERTED",
            message=f"CI lower ({hr.ci_low}) must be < upper ({hr.ci_high})",
            severity=ReviewSeverity.ERROR,
            field="ci",
            expected="lower < upper",
            actual=f"{hr.ci_low} >= {hr.ci_high}"
        ))

    # HR within CI
    if not (hr.ci_low <= hr.hr <= hr.ci_high):
        issues.append(ValidationIssue(
            code="HR_OUTSIDE_CI",
            message=f"HR ({hr.hr}) not within CI [{hr.ci_low}, {hr.ci_high}]",
            severity=ReviewSeverity.ERROR,
            field="hr",
            expected=f"[{hr.ci_low}, {hr.ci_high}]",
            actual=hr.hr
        ))

    # P-value consistency (if provided)
    if hr.p_value is not None:
        ci_excludes_one = hr.ci_low > 1.0 or hr.ci_high < 1.0
        p_significant = hr.p_value < 0.05

        if ci_excludes_one != p_significant:
            issues.append(ValidationIssue(
                code="PVALUE_CI_MISMATCH",
                message=f"P-value ({hr.p_value}) inconsistent with CI [{hr.ci_low}, {hr.ci_high}]",
                severity=ReviewSeverity.WARNING,
                field="p_value"
            ))

    # CI width sanity check
    ci_width = hr.ci_high - hr.ci_low
    if ci_width > hr.hr * 5:  # Very wide CI
        issues.append(ValidationIssue(
            code="CI_VERY_WIDE",
            message=f"CI width ({ci_width:.2f}) is very wide relative to HR ({hr.hr})",
            severity=ReviewSeverity.INFO,
            field="ci"
        ))

    # Provenance check
    if not hr.provenance or not hr.provenance.raw_text:
        issues.append(ValidationIssue(
            code="MISSING_PROVENANCE",
            message="Hazard ratio missing provenance",
            severity=ReviewSeverity.ERROR,
            field="provenance"
        ))

    return issues


def validate_odds_ratio(or_val: OddsRatioCI) -> List[ValidationIssue]:
    """Validate odds ratio with CI"""
    issues = []

    if or_val.or_value <= 0:
        issues.append(ValidationIssue(
            code="OR_NOT_POSITIVE",
            message=f"Odds ratio must be positive, got {or_val.or_value}",
            severity=ReviewSeverity.ERROR,
            field="or"
        ))

    if or_val.ci_low >= or_val.ci_high:
        issues.append(ValidationIssue(
            code="CI_INVERTED",
            message=f"CI lower >= upper: [{or_val.ci_low}, {or_val.ci_high}]",
            severity=ReviewSeverity.ERROR,
            field="ci"
        ))

    if not or_val.provenance:
        issues.append(ValidationIssue(
            code="MISSING_PROVENANCE",
            message="Odds ratio missing provenance",
            severity=ReviewSeverity.ERROR,
            field="provenance"
        ))

    return issues


def validate_risk_ratio(rr: RiskRatioCI) -> List[ValidationIssue]:
    """Validate relative risk with CI"""
    issues = []

    if rr.rr <= 0:
        issues.append(ValidationIssue(
            code="RR_NOT_POSITIVE",
            message=f"Relative risk must be positive, got {rr.rr}",
            severity=ReviewSeverity.ERROR,
            field="rr"
        ))

    if rr.ci_low >= rr.ci_high:
        issues.append(ValidationIssue(
            code="CI_INVERTED",
            message=f"CI lower >= upper: [{rr.ci_low}, {rr.ci_high}]",
            severity=ReviewSeverity.ERROR,
            field="ci"
        ))

    if not rr.provenance:
        issues.append(ValidationIssue(
            code="MISSING_PROVENANCE",
            message="Relative risk missing provenance",
            severity=ReviewSeverity.ERROR,
            field="provenance"
        ))

    return issues


def validate_mean_difference(md: MeanDifference) -> List[ValidationIssue]:
    """Validate mean difference with CI"""
    issues = []

    # MD can be negative, but CI must be properly ordered
    if md.ci_low >= md.ci_high:
        issues.append(ValidationIssue(
            code="CI_INVERTED",
            message=f"CI lower >= upper: [{md.ci_low}, {md.ci_high}]",
            severity=ReviewSeverity.ERROR,
            field="ci"
        ))

    # MD should be within CI
    if not (md.ci_low <= md.md <= md.ci_high):
        issues.append(ValidationIssue(
            code="MD_OUTSIDE_CI",
            message=f"MD ({md.md}) not within CI [{md.ci_low}, {md.ci_high}]",
            severity=ReviewSeverity.ERROR,
            field="md"
        ))

    if not md.provenance:
        issues.append(ValidationIssue(
            code="MISSING_PROVENANCE",
            message="Mean difference missing provenance",
            severity=ReviewSeverity.ERROR,
            field="provenance"
        ))

    return issues


def validate_measure_type(hr: HazardRatioCI, context: Optional[str] = None) -> List[ValidationIssue]:
    """
    Check if the value might be misclassified (e.g., OR labeled as HR).

    Large HR values (>3) without survival/hazard context may actually be ORs.
    """
    issues = []

    if hr.hr > 3.0 and context:
        context_lower = context.lower()
        # Check if context suggests this is truly an HR
        hr_keywords = ['hazard', 'survival', 'time to', 'kaplan', 'cox', 'event-free']
        or_keywords = ['odds', 'logistic', 'case-control']

        has_hr_context = any(kw in context_lower for kw in hr_keywords)
        has_or_context = any(kw in context_lower for kw in or_keywords)

        if has_or_context and not has_hr_context:
            issues.append(ValidationIssue(
                code="POSSIBLE_OR_MISCLASSIFIED",
                message=f"Value {hr.hr} may be odds ratio, not hazard ratio (context suggests OR)",
                severity=ReviewSeverity.WARNING,
                field="measure_type",
                expected="HR or OR",
                actual="HR"
            ))
        elif not has_hr_context and hr.hr > 5.0:
            issues.append(ValidationIssue(
                code="LARGE_HR_NO_CONTEXT",
                message=f"Large HR ({hr.hr}) without hazard/survival context - verify measure type",
                severity=ReviewSeverity.INFO,
                field="measure_type"
            ))

    return issues


def validate_arm_consistency(arms: List[Arm], extractions: List[ExtractionRecord]) -> List[ValidationIssue]:
    """Check arm data consistency across extractions"""
    issues = []

    arm_totals = {arm.arm_id: arm.n_randomized for arm in arms if arm.n_randomized}

    for extraction in extractions:
        if extraction.binary_outcomes:
            for outcome in extraction.binary_outcomes:
                if outcome.arm_id in arm_totals:
                    expected_n = arm_totals[outcome.arm_id]
                    # Allow 10% tolerance for ITT vs analyzed populations
                    if abs(outcome.n - expected_n) / expected_n > 0.10:
                        issues.append(ValidationIssue(
                            code="ARM_N_MISMATCH",
                            message=f"Arm '{outcome.arm_id}' n={outcome.n} differs from randomized={expected_n}",
                            severity=ReviewSeverity.WARNING,
                            field=f"binary_outcomes.{outcome.arm_id}.n",
                            expected=expected_n,
                            actual=outcome.n
                        ))

    return issues


def validate_duplicate_endpoints(extractions: List[ExtractionRecord]) -> List[ValidationIssue]:
    """Check for duplicate endpoint extractions with conflicting values"""
    issues = []

    seen = {}  # endpoint_canonical -> list of extractions
    for ext in extractions:
        key = (ext.endpoint_canonical, ext.timepoint.normalized_label)
        if key not in seen:
            seen[key] = []
        seen[key].append(ext)

    for key, ext_list in seen.items():
        if len(ext_list) > 1:
            # Check if values conflict
            values = []
            for ext in ext_list:
                if ext.effect_estimate:
                    if isinstance(ext.effect_estimate, HazardRatioCI):
                        values.append(ext.effect_estimate.hr)
                    elif isinstance(ext.effect_estimate, OddsRatioCI):
                        values.append(ext.effect_estimate.or_value)

            if values and len(set(values)) > 1:
                issues.append(ValidationIssue(
                    code="DUPLICATE_ENDPOINT_CONFLICT",
                    message=f"Endpoint '{key[0]}' at '{key[1]}' has conflicting values: {values}",
                    severity=ReviewSeverity.ERROR,
                    field=f"endpoint:{key[0]}"
                ))
            else:
                issues.append(ValidationIssue(
                    code="DUPLICATE_ENDPOINT",
                    message=f"Endpoint '{key[0]}' at '{key[1]}' extracted {len(ext_list)} times",
                    severity=ReviewSeverity.WARNING,
                    field=f"endpoint:{key[0]}"
                ))

    return issues


def validate_timepoint_consistency(extractions: List[ExtractionRecord]) -> List[ValidationIssue]:
    """Check timepoint consistency"""
    issues = []

    timepoints = set()
    primary_timepoints = []

    for ext in extractions:
        if ext.timepoint.normalized_label:
            timepoints.add(ext.timepoint.normalized_label)
        if ext.timepoint.is_primary:
            primary_timepoints.append(ext.timepoint.normalized_label)

    # Multiple primary timepoints is suspicious
    if len(set(primary_timepoints)) > 1:
        issues.append(ValidationIssue(
            code="MULTIPLE_PRIMARY_TIMEPOINTS",
            message=f"Multiple timepoints marked as primary: {set(primary_timepoints)}",
            severity=ReviewSeverity.WARNING,
            field="timepoint"
        ))

    return issues


def validate_cross_check(extraction: ExtractionRecord) -> List[ValidationIssue]:
    """Check Pass A vs Pass B agreement"""
    issues = []

    if extraction.pass_a_value and extraction.pass_b_value:
        if extraction.passes_agree is False:
            issues.append(ValidationIssue(
                code="PASS_DISAGREEMENT",
                message=f"Pass A ({extraction.pass_a_value}) != Pass B ({extraction.pass_b_value})",
                severity=ReviewSeverity.ERROR,
                field="cross_check"
            ))

    return issues


# ============================================================
# MAIN VALIDATION RUNNER
# ============================================================

class Validator:
    """Main validator orchestrator"""

    def __init__(self):
        self.issue_counts = {
            ReviewSeverity.ERROR: 0,
            ReviewSeverity.WARNING: 0,
            ReviewSeverity.INFO: 0
        }

    def validate_extraction(self, extraction: ExtractionRecord, arms: List[Arm]) -> ValidationReport:
        """Validate single extraction record"""
        report = ValidationReport(
            record_id=f"{extraction.endpoint_canonical}_{extraction.timepoint.raw_text}",
            passed=True
        )

        # Validate binary outcomes
        if extraction.binary_outcomes:
            for outcome in extraction.binary_outcomes:
                issues = validate_binary_outcome(outcome)
                for issue in issues:
                    report.add_issue(issue)

        # Validate effect estimates
        if extraction.effect_estimate:
            if isinstance(extraction.effect_estimate, HazardRatioCI):
                issues = validate_hazard_ratio(extraction.effect_estimate)
            elif isinstance(extraction.effect_estimate, OddsRatioCI):
                issues = validate_odds_ratio(extraction.effect_estimate)
            elif isinstance(extraction.effect_estimate, RiskRatioCI):
                issues = validate_risk_ratio(extraction.effect_estimate)
            elif isinstance(extraction.effect_estimate, MeanDifference):
                issues = validate_mean_difference(extraction.effect_estimate)
            else:
                issues = []

            for issue in issues:
                report.add_issue(issue)

        # Validate cross-check
        issues = validate_cross_check(extraction)
        for issue in issues:
            report.add_issue(issue)

        # Determine confidence
        error_count = sum(1 for i in report.issues if i.severity == ReviewSeverity.ERROR)
        warn_count = sum(1 for i in report.issues if i.severity == ReviewSeverity.WARNING)

        if error_count > 0:
            report.confidence = ExtractionConfidence.REVIEW_REQUIRED
        elif warn_count > 0:
            report.confidence = ExtractionConfidence.MEDIUM
        else:
            report.confidence = ExtractionConfidence.HIGH

        return report

    def validate_all(self, extractions: List[ExtractionRecord], arms: List[Arm]) -> List[ValidationReport]:
        """Validate all extractions"""
        reports = []

        # Individual validation
        for ext in extractions:
            report = self.validate_extraction(ext, arms)
            reports.append(report)

        # Cross-extraction validation
        dup_issues = validate_duplicate_endpoints(extractions)
        tp_issues = validate_timepoint_consistency(extractions)
        arm_issues = validate_arm_consistency(arms, extractions)

        # Add cross-extraction issues to relevant reports
        for issue in dup_issues + tp_issues + arm_issues:
            if reports:
                reports[0].add_issue(issue)

        return reports

    def generate_review_queue(self, reports: List[ValidationReport], pdf_file: str) -> List[ReviewQueueItem]:
        """Generate review queue items from validation reports"""
        queue = []

        for report in reports:
            if not report.passed or report.confidence == ExtractionConfidence.REVIEW_REQUIRED:
                for issue in report.issues:
                    if issue.severity in [ReviewSeverity.ERROR, ReviewSeverity.WARNING]:
                        queue.append(ReviewQueueItem(
                            record_id=report.record_id,
                            pdf_file=pdf_file,
                            page_number=0,  # Would be populated from extraction
                            severity=issue.severity,
                            reason_code=issue.code,
                            reason_text=issue.message,
                            suggested_action="manual_review"
                        ))

        return queue
