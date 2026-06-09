"""
Proof-Carrying Numbers (PCN) for RCT Extractor v4.0
====================================================

Every extracted number carries a proof certificate demonstrating:
1. Where it came from (provenance)
2. How it was parsed (method)
3. Why it's correct (verification)

Numbers cannot be rendered/used without passing verification.
"""

import hashlib
import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime, timezone


class VerificationStatus(Enum):
    """Status of verification"""
    VERIFIED = "verified"
    FAILED = "failed"
    PENDING = "pending"


class CheckResult(Enum):
    """Result of a single check"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"


@dataclass
class VerificationCheck:
    """A single verification check result"""
    name: str
    result: CheckResult
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    message: str = ""
    is_critical: bool = True  # Critical checks must pass for verification

    @property
    def passed(self) -> bool:
        return self.result in [CheckResult.PASSED, CheckResult.SKIPPED, CheckResult.WARNING]


@dataclass
class ProofCertificate:
    """Certificate proving a number's validity"""

    # Provenance
    source_text: str
    char_start: int
    char_end: int
    extraction_method: str  # e.g., "pattern_HR_01", "grammar", "fsm"
    extractor_name: str = ""

    # Verification results
    checks: List[VerificationCheck] = field(default_factory=list)

    # Consensus information (from Team-of-Rivals)
    extractors_agreed: List[str] = field(default_factory=list)
    extractors_disagreed: List[str] = field(default_factory=list)
    agreement_count: int = 0
    total_extractors: int = 0

    # Metadata — use UTC for reproducibility
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    integrity_hash: str = ""

    @property
    def checks_passed(self) -> List[str]:
        return [c.name for c in self.checks if c.passed]

    @property
    def checks_failed(self) -> List[str]:
        return [c.name for c in self.checks if not c.passed]

    @property
    def critical_checks_passed(self) -> bool:
        """All critical checks must pass"""
        critical = [c for c in self.checks if c.is_critical]
        return all(c.passed for c in critical)

    @property
    def is_verified(self) -> bool:
        """Only verified if all critical checks pass"""
        return self.critical_checks_passed

    @property
    def has_consensus(self) -> bool:
        """Majority of extractors agreed (requires at least 1 extractor)"""
        if self.total_extractors <= 0:
            return False  # No extractors = no consensus
        if self.total_extractors == 1:
            return self.agreement_count >= 1
        return self.agreement_count > self.total_extractors / 2

    def add_check(self, check: VerificationCheck):
        """Add a verification check"""
        self.checks.append(check)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'source_text': self.source_text,
            'char_start': self.char_start,
            'char_end': self.char_end,
            'extraction_method': self.extraction_method,
            'extractor_name': self.extractor_name,
            'checks_passed': self.checks_passed,
            'checks_failed': self.checks_failed,
            'is_verified': self.is_verified,
            'extractors_agreed': self.extractors_agreed,
            'agreement_count': self.agreement_count,
            'total_extractors': self.total_extractors,
            'has_consensus': self.has_consensus,
            'timestamp': self.timestamp,
            'integrity_hash': self.integrity_hash,
        }


class VerificationError(Exception):
    """Raised when trying to use an unverified number"""
    pass


@dataclass
class ProofCarryingNumber:
    """A number that carries its own proof of correctness"""
    value: float
    certificate: ProofCertificate

    def __post_init__(self):
        """Always compute integrity hash (prevents pre-set forgery)"""
        self.certificate.integrity_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute integrity hash of value + source + positions + extraction method + checks"""
        checks_str = "|".join(
            f"{c.name}:{c.result.value}" for c in self.certificate.checks
        ) if self.certificate.checks else "no_checks"
        content = (
            f"{self.value}|{self.certificate.source_text}"
            f"|{self.certificate.char_start}|{self.certificate.char_end}"
            f"|{self.certificate.extraction_method}"
            f"|{checks_str}"
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @property
    def is_verified(self) -> bool:
        return self.certificate.is_verified

    def render(self, allow_unverified: bool = False) -> str:
        """
        Render the number as string.

        By default, refuses to render unverified numbers.
        Set allow_unverified=True to bypass (with warning marker).
        """
        if not self.is_verified:
            if allow_unverified:
                return f"[UNVERIFIED: {self.value}]"
            raise VerificationError(
                f"Cannot render unverified number {self.value}. "
                f"Failed checks: {self.certificate.checks_failed}"
            )
        return str(self.value)

    def __str__(self) -> str:
        """String representation (requires verification)"""
        return self.render()

    def __repr__(self) -> str:
        status = "VERIFIED" if self.is_verified else "UNVERIFIED"
        return f"PCN({self.value}, {status})"


@dataclass
class ProofCarryingCI:
    """Proof-carrying confidence interval"""
    lower: ProofCarryingNumber
    upper: ProofCarryingNumber
    level: float = 0.95

    @property
    def is_verified(self) -> bool:
        return self.lower.is_verified and self.upper.is_verified

    def render(self, allow_unverified: bool = False) -> str:
        if not self.is_verified and not allow_unverified:
            raise VerificationError("Cannot render unverified CI")
        return f"[{self.lower.render(allow_unverified)}, {self.upper.render(allow_unverified)}]"


@dataclass
class ProofCarryingExtraction:
    """Complete extraction with proof certificates"""
    effect_type: str
    point_estimate: ProofCarryingNumber
    ci_lower: Optional[ProofCarryingNumber] = None
    ci_upper: Optional[ProofCarryingNumber] = None
    standard_error: Optional[ProofCarryingNumber] = None
    p_value: Optional[float] = None

    # Master certificate combining all checks
    master_certificate: Optional[ProofCertificate] = None

    # Flags
    warnings: List[str] = field(default_factory=list)
    needs_review: bool = False
    review_reason: str = ""

    @property
    def is_fully_verified(self) -> bool:
        """All components verified"""
        verified = self.point_estimate.is_verified
        if self.ci_lower:
            verified = verified and self.ci_lower.is_verified
        if self.ci_upper:
            verified = verified and self.ci_upper.is_verified
        return verified

    @property
    def verification_status(self) -> VerificationStatus:
        if self.is_fully_verified:
            return VerificationStatus.VERIFIED
        elif any(not getattr(self, f).is_verified for f in ['point_estimate', 'ci_lower', 'ci_upper'] if getattr(self, f)):
            return VerificationStatus.FAILED
        return VerificationStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for output"""
        result = {
            'effect_type': self.effect_type,
            'point_estimate': self.point_estimate.value,
            'is_verified': self.is_fully_verified,
            'verification_status': self.verification_status.value,
            'warnings': self.warnings,
            'needs_review': self.needs_review,
            'review_reason': self.review_reason,
        }

        if self.ci_lower and self.ci_upper:
            result['ci_lower'] = self.ci_lower.value
            result['ci_upper'] = self.ci_upper.value

        if self.standard_error:
            result['standard_error'] = self.standard_error.value

        if self.p_value is not None:
            result['p_value'] = self.p_value

        if self.master_certificate:
            result['certificate'] = self.master_certificate.to_dict()

        return result


# =============================================================================
# VERIFICATION CHECKS
# =============================================================================

def check_ci_contains_point(value: float, ci_lower: float, ci_upper: float, tolerance: float = 0.01) -> VerificationCheck:
    """Verify point estimate is within CI (with tolerance for rounding)"""
    passed = (ci_lower - tolerance) <= value <= (ci_upper + tolerance)

    return VerificationCheck(
        name="CI_CONTAINS_POINT",
        result=CheckResult.PASSED if passed else CheckResult.FAILED,
        expected=f"{ci_lower} <= {value} <= {ci_upper}",
        actual=f"value={value}, ci=[{ci_lower}, {ci_upper}]",
        message="" if passed else f"Point estimate {value} not in CI [{ci_lower}, {ci_upper}]",
        is_critical=True
    )


def check_ci_ordered(ci_lower: float, ci_upper: float) -> VerificationCheck:
    """Verify CI bounds are correctly ordered (equal bounds allowed for heavily rounded CIs)"""
    passed = ci_lower <= ci_upper

    return VerificationCheck(
        name="CI_ORDERED",
        result=CheckResult.PASSED if passed else CheckResult.FAILED,
        expected="ci_lower < ci_upper",
        actual=f"ci_lower={ci_lower}, ci_upper={ci_upper}",
        message="" if passed else f"CI bounds reversed: {ci_lower} >= {ci_upper}",
        is_critical=True
    )


def check_range_plausible(effect_type: str, value: float) -> VerificationCheck:
    """Verify value is within plausible range for effect type"""
    RANGES = {
        'HR': (0.01, 50.0),
        'OR': (0.01, 100.0),
        'RR': (0.01, 50.0),
        'IRR': (0.01, 100.0),
        'MD': (-1000.0, 1000.0),
        'SMD': (-10.0, 10.0),
        'ARD': (-100.0, 100.0),
        'NNT': (1.0, 10000.0),
        'NNH': (1.0, 10000.0),
    }

    if effect_type not in RANGES:
        return VerificationCheck(
            name="RANGE_PLAUSIBLE",
            result=CheckResult.SKIPPED,
            message=f"No range defined for {effect_type}"
        )

    min_val, max_val = RANGES[effect_type]
    passed = min_val <= value <= max_val

    return VerificationCheck(
        name="RANGE_PLAUSIBLE",
        result=CheckResult.PASSED if passed else CheckResult.FAILED,
        expected=f"{min_val} <= value <= {max_val}",
        actual=value,
        message="" if passed else f"Value {value} outside plausible range [{min_val}, {max_val}]",
        is_critical=True
    )


def check_se_consistency(effect_type: str, ci_lower: float, ci_upper: float,
                         reported_se: Optional[float] = None) -> VerificationCheck:
    """Verify SE is consistent with CI width"""
    try:
        if effect_type in ['HR', 'OR', 'RR', 'IRR']:
            # Log scale for ratios
            if ci_lower <= 0 or ci_upper <= 0:
                return VerificationCheck(
                    name="SE_CONSISTENT",
                    result=CheckResult.SKIPPED,
                    message="Cannot compute SE for non-positive CI bounds"
                )
            expected_se = (math.log(ci_upper) - math.log(ci_lower)) / (2 * 1.96)
        else:
            # Linear scale for differences
            expected_se = (ci_upper - ci_lower) / (2 * 1.96)

        if reported_se is None:
            return VerificationCheck(
                name="SE_CONSISTENT",
                result=CheckResult.PASSED,
                expected=expected_se,
                actual="calculated",
                message=f"SE calculated as {expected_se:.4f}"
            )

        # Check if reported SE matches expected
        tolerance = 0.05 * expected_se if expected_se > 0 else 0.01
        matches = abs(reported_se - expected_se) <= tolerance

        return VerificationCheck(
            name="SE_CONSISTENT",
            result=CheckResult.PASSED if matches else CheckResult.WARNING,
            expected=expected_se,
            actual=reported_se,
            message="" if matches else f"Reported SE {reported_se} differs from expected {expected_se:.4f}",
            is_critical=False  # Warning only, not critical
        )

    except (ValueError, ZeroDivisionError) as e:
        return VerificationCheck(
            name="SE_CONSISTENT",
            result=CheckResult.SKIPPED,
            message=f"Cannot compute SE: {e}"
        )


def check_p_value_consistency(effect_type: str, ci_lower: float, ci_upper: float,
                               p_value: float) -> VerificationCheck:
    """Verify p-value is consistent with CI"""
    # Null value depends on effect type
    if effect_type in ['HR', 'OR', 'RR', 'IRR']:
        null_value = 1.0
    else:
        null_value = 0.0

    ci_excludes_null = not (ci_lower <= null_value <= ci_upper)
    p_significant = p_value < 0.05

    # These should match (with some tolerance for borderline cases)
    consistent = ci_excludes_null == p_significant

    # Allow borderline cases (p close to 0.05, CI close to null)
    # Tolerance matches deterministic_verifier.py: 0.03-0.07
    if not consistent:
        if 0.03 <= p_value <= 0.07:  # Borderline p-value
            consistent = True  # Don't fail on borderline
        elif effect_type in ['HR', 'OR', 'RR', 'IRR']:
            if 0.95 <= ci_lower <= 1.05 or 0.95 <= ci_upper <= 1.05:  # CI close to 1
                consistent = True

    return VerificationCheck(
        name="P_VALUE_CONSISTENT",
        result=CheckResult.PASSED if consistent else CheckResult.WARNING,
        expected=f"CI excludes null ({null_value}): {ci_excludes_null} should match p<0.05: {p_significant}",
        actual=f"p={p_value}, CI=[{ci_lower}, {ci_upper}]",
        message="" if consistent else f"P-value {p_value} inconsistent with CI [{ci_lower}, {ci_upper}]",
        is_critical=False  # Warning only
    )


def check_log_symmetry(value: float, ci_lower: float, ci_upper: float,
                       tolerance: float = 0.1) -> VerificationCheck:
    """Verify CI is symmetric on log scale (for ratios)"""
    try:
        if value <= 0 or ci_lower <= 0 or ci_upper <= 0:
            return VerificationCheck(
                name="LOG_SYMMETRIC",
                result=CheckResult.SKIPPED,
                message="Cannot check log symmetry for non-positive values"
            )

        log_value = math.log(value)
        log_lower = math.log(ci_lower)
        log_upper = math.log(ci_upper)

        dist_lower = log_value - log_lower
        dist_upper = log_upper - log_value

        # Check symmetry
        avg_dist = (dist_lower + dist_upper) / 2
        asymmetry = abs(dist_lower - dist_upper) / avg_dist if avg_dist > 0 else 0

        passed = asymmetry <= tolerance

        return VerificationCheck(
            name="LOG_SYMMETRIC",
            result=CheckResult.PASSED if passed else CheckResult.WARNING,
            expected=f"Asymmetry <= {tolerance}",
            actual=f"Asymmetry = {asymmetry:.3f}",
            message="" if passed else f"CI asymmetric on log scale: {asymmetry:.3f} > {tolerance}",
            is_critical=False  # Warning only
        )

    except (ValueError, ZeroDivisionError) as e:
        return VerificationCheck(
            name="LOG_SYMMETRIC",
            result=CheckResult.SKIPPED,
            message=f"Cannot check log symmetry: {e}"
        )


def check_ci_width_reasonable(effect_type: str, value: float,
                               ci_lower: float, ci_upper: float) -> VerificationCheck:
    """Verify CI width is reasonable (not impossibly narrow or wide)"""
    ci_width = ci_upper - ci_lower

    if effect_type in ['HR', 'OR', 'RR', 'IRR']:
        # For ratios, check width relative to value
        relative_width = ci_width / value if value > 0 else ci_width

        # Typical range: 0.1 to 5.0 (10% to 500% of point estimate)
        reasonable = 0.05 <= relative_width <= 10.0

        return VerificationCheck(
            name="CI_WIDTH_REASONABLE",
            result=CheckResult.PASSED if reasonable else CheckResult.WARNING,
            expected="0.05 <= relative_width <= 10.0",
            actual=f"relative_width = {relative_width:.3f}",
            message="" if reasonable else f"CI width {ci_width} unusual for value {value}",
            is_critical=False
        )

    else:
        # For differences, harder to check without context
        return VerificationCheck(
            name="CI_WIDTH_REASONABLE",
            result=CheckResult.SKIPPED,
            message="Width check not applicable for differences without context"
        )


# =============================================================================
# VERIFICATION RUNNER
# =============================================================================

def run_all_checks(effect_type: str, value: float, ci_lower: float, ci_upper: float,
                   p_value: Optional[float] = None,
                   reported_se: Optional[float] = None) -> List[VerificationCheck]:
    """Run all verification checks and return results"""
    checks = []

    # Critical checks
    checks.append(check_ci_contains_point(value, ci_lower, ci_upper))
    checks.append(check_ci_ordered(ci_lower, ci_upper))
    checks.append(check_range_plausible(effect_type, value))

    # SE consistency
    checks.append(check_se_consistency(effect_type, ci_lower, ci_upper, reported_se))

    # P-value consistency (if provided)
    if p_value is not None:
        checks.append(check_p_value_consistency(effect_type, ci_lower, ci_upper, p_value))

    # Log symmetry (for ratios only)
    if effect_type in ['HR', 'OR', 'RR', 'IRR']:
        checks.append(check_log_symmetry(value, ci_lower, ci_upper))

    # CI width check
    checks.append(check_ci_width_reasonable(effect_type, value, ci_lower, ci_upper))

    return checks


def create_verified_extraction(
    effect_type: str,
    value: float,
    ci_lower: float,
    ci_upper: float,
    source_text: str,
    char_start: int = 0,
    char_end: int = 0,
    extraction_method: str = "unknown",
    p_value: Optional[float] = None,
    extractor_name: str = ""
) -> ProofCarryingExtraction:
    """Create a proof-carrying extraction with verification"""

    # Run all verification checks
    checks = run_all_checks(effect_type, value, ci_lower, ci_upper, p_value)

    # Create master certificate
    master_cert = ProofCertificate(
        source_text=source_text,
        char_start=char_start,
        char_end=char_end,
        extraction_method=extraction_method,
        extractor_name=extractor_name,
        checks=checks
    )

    # Create PCN for point estimate
    point_cert = ProofCertificate(
        source_text=source_text,
        char_start=char_start,
        char_end=char_end,
        extraction_method=extraction_method,
        checks=[c for c in checks if c.name in ['RANGE_PLAUSIBLE', 'CI_CONTAINS_POINT']]
    )
    point_pcn = ProofCarryingNumber(value=value, certificate=point_cert)

    # Create PCN for CI bounds
    ci_lower_cert = ProofCertificate(
        source_text=source_text,
        char_start=char_start,
        char_end=char_end,
        extraction_method=extraction_method,
        checks=[c for c in checks if c.name == 'CI_ORDERED']
    )
    ci_lower_pcn = ProofCarryingNumber(value=ci_lower, certificate=ci_lower_cert)

    ci_upper_cert = ProofCertificate(
        source_text=source_text,
        char_start=char_start,
        char_end=char_end,
        extraction_method=extraction_method,
        checks=[c for c in checks if c.name == 'CI_ORDERED']
    )
    ci_upper_pcn = ProofCarryingNumber(value=ci_upper, certificate=ci_upper_cert)

    # Calculate SE
    se_pcn = None
    try:
        if effect_type in ['HR', 'OR', 'RR', 'IRR']:
            if ci_lower <= 0 or ci_upper <= 0:
                raise ValueError("Cannot log non-positive CI bounds for ratio measure")
            se_value = (math.log(ci_upper) - math.log(ci_lower)) / (2 * 1.96)
        else:
            se_value = (ci_upper - ci_lower) / (2 * 1.96)

        se_cert = ProofCertificate(
            source_text="calculated",
            char_start=0,
            char_end=0,
            extraction_method="se_from_ci",
            checks=[VerificationCheck("SE_CALCULATED", CheckResult.PASSED)]
        )
        se_pcn = ProofCarryingNumber(value=se_value, certificate=se_cert)
    except (ValueError, ZeroDivisionError):
        pass

    # Determine if review needed
    warnings = [c.message for c in checks if c.result == CheckResult.WARNING and c.message]
    needs_review = not master_cert.is_verified or len(warnings) > 0
    review_reason = "; ".join(master_cert.checks_failed) if not master_cert.is_verified else ""

    return ProofCarryingExtraction(
        effect_type=effect_type,
        point_estimate=point_pcn,
        ci_lower=ci_lower_pcn,
        ci_upper=ci_upper_pcn,
        standard_error=se_pcn,
        p_value=p_value,
        master_certificate=master_cert,
        warnings=warnings,
        needs_review=needs_review,
        review_reason=review_reason
    )
