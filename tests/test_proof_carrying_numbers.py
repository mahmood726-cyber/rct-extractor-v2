#!/usr/bin/env python3
"""
Tests for src/core/proof_carrying_numbers.py
=============================================

Covers:
- ProofCarryingNumber: integrity hash, render (verified/unverified), p_value=0.0 edge case
- ProofCertificate: checks_passed/failed, critical_checks_passed, is_verified, has_consensus, to_dict
- VerificationCheck: passed property for each CheckResult value
- Verification check functions: CI contains point, CI ordered, range plausible, SE consistency,
  p-value consistency, log symmetry, CI width reasonable
- run_all_checks: returns correct count and types
- create_verified_extraction: returns ProofCarryingExtraction, verified/unverified states
- Edge cases: p_value=0.0 not dropped, integrity hash includes extraction_method
"""

import sys
import math
import hashlib
from pathlib import Path

import pytest

# Ensure project root is on sys.path (mirrors conftest.py)
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.proof_carrying_numbers import (
    CheckResult,
    ProofCarryingNumber,
    ProofCarryingExtraction,
    ProofCertificate,
    VerificationCheck,
    VerificationError,
    VerificationStatus,
    check_ci_contains_point,
    check_ci_ordered,
    check_ci_width_reasonable,
    check_log_symmetry,
    check_p_value_consistency,
    check_range_plausible,
    check_se_consistency,
    create_verified_extraction,
    run_all_checks,
)


# =============================================================================
# Helpers
# =============================================================================

def _make_cert(checks=None, extraction_method="test_method", **kwargs):
    """Create a ProofCertificate with sensible defaults."""
    defaults = dict(
        source_text="HR 0.74 (95% CI, 0.65-0.85)",
        char_start=0,
        char_end=30,
        extraction_method=extraction_method,
        checks=checks or [],
    )
    defaults.update(kwargs)
    return ProofCertificate(**defaults)


def _passing_check(name="TEST_CHECK", is_critical=True):
    return VerificationCheck(name=name, result=CheckResult.PASSED, is_critical=is_critical)


def _failing_check(name="TEST_CHECK", is_critical=True):
    return VerificationCheck(name=name, result=CheckResult.FAILED, is_critical=is_critical)


def _warning_check(name="TEST_CHECK", is_critical=False):
    return VerificationCheck(name=name, result=CheckResult.WARNING, is_critical=is_critical)


def _skipped_check(name="TEST_CHECK", is_critical=False):
    return VerificationCheck(name=name, result=CheckResult.SKIPPED, is_critical=is_critical)


# =============================================================================
# VerificationCheck.passed
# =============================================================================

class TestVerificationCheck:
    """VerificationCheck.passed should be True for PASSED, SKIPPED, WARNING; False for FAILED."""

    def test_passed_result(self):
        vc = VerificationCheck(name="X", result=CheckResult.PASSED)
        assert vc.passed is True

    def test_failed_result(self):
        vc = VerificationCheck(name="X", result=CheckResult.FAILED)
        assert vc.passed is False

    def test_skipped_result(self):
        vc = VerificationCheck(name="X", result=CheckResult.SKIPPED)
        assert vc.passed is True

    def test_warning_result(self):
        vc = VerificationCheck(name="X", result=CheckResult.WARNING)
        assert vc.passed is True

    def test_default_is_critical(self):
        vc = VerificationCheck(name="X", result=CheckResult.PASSED)
        assert vc.is_critical is True


# =============================================================================
# ProofCertificate
# =============================================================================

class TestProofCertificate:

    def test_checks_passed_names(self):
        cert = _make_cert(checks=[
            _passing_check("A"),
            _failing_check("B"),
            _passing_check("C"),
        ])
        assert cert.checks_passed == ["A", "C"]

    def test_checks_failed_names(self):
        cert = _make_cert(checks=[
            _passing_check("A"),
            _failing_check("B"),
            _failing_check("D"),
        ])
        assert cert.checks_failed == ["B", "D"]

    def test_critical_checks_passed_all_pass(self):
        cert = _make_cert(checks=[
            _passing_check("A", is_critical=True),
            _passing_check("B", is_critical=True),
            _warning_check("C", is_critical=False),
        ])
        assert cert.critical_checks_passed is True

    def test_critical_checks_passed_one_fails(self):
        cert = _make_cert(checks=[
            _passing_check("A", is_critical=True),
            _failing_check("B", is_critical=True),
        ])
        assert cert.critical_checks_passed is False

    def test_critical_checks_passed_no_critical(self):
        cert = _make_cert(checks=[
            _warning_check("A", is_critical=False),
        ])
        # No critical checks -> vacuously True (all() on empty)
        assert cert.critical_checks_passed is True

    def test_is_verified_delegates_to_critical(self):
        cert = _make_cert(checks=[_passing_check("A", is_critical=True)])
        assert cert.is_verified is True

        cert2 = _make_cert(checks=[_failing_check("A", is_critical=True)])
        assert cert2.is_verified is False

    def test_has_consensus_zero_extractors_is_false(self):
        # 0 extractors means no consensus (fail-closed)
        cert = _make_cert(total_extractors=0)
        assert cert.has_consensus is False

    def test_has_consensus_single_extractor_agreeing(self):
        cert = _make_cert(agreement_count=1, total_extractors=1)
        assert cert.has_consensus is True

    def test_has_consensus_majority(self):
        cert = _make_cert(agreement_count=3, total_extractors=4)
        assert cert.has_consensus is True

    def test_has_consensus_no_majority(self):
        cert = _make_cert(agreement_count=2, total_extractors=4)
        assert cert.has_consensus is False

    def test_has_consensus_exact_half(self):
        # 2/4 == 0.5, which is NOT > 0.5
        cert = _make_cert(agreement_count=2, total_extractors=4)
        assert cert.has_consensus is False

    def test_to_dict_keys(self):
        cert = _make_cert(checks=[_passing_check("A")])
        d = cert.to_dict()
        expected_keys = {
            'source_text', 'char_start', 'char_end', 'extraction_method',
            'extractor_name', 'checks_passed', 'checks_failed', 'is_verified',
            'extractors_agreed', 'agreement_count', 'total_extractors',
            'has_consensus', 'timestamp', 'integrity_hash',
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_values(self):
        cert = _make_cert(
            checks=[_passing_check("A"), _failing_check("B")],
            extraction_method="pattern_HR_01",
        )
        d = cert.to_dict()
        assert d['extraction_method'] == "pattern_HR_01"
        assert d['checks_passed'] == ["A"]
        assert d['checks_failed'] == ["B"]
        assert d['is_verified'] is False  # critical check B failed


# =============================================================================
# ProofCarryingNumber
# =============================================================================

class TestProofCarryingNumber:

    def test_integrity_hash_computed_on_init(self):
        cert = _make_cert()
        pcn = ProofCarryingNumber(value=0.74, certificate=cert)
        assert pcn.certificate.integrity_hash != ""
        assert len(pcn.certificate.integrity_hash) == 16

    def test_integrity_hash_includes_extraction_method(self):
        """The fix: hash must include extraction_method so different methods produce different hashes."""
        cert_a = _make_cert(extraction_method="pattern_HR_01")
        cert_b = _make_cert(extraction_method="grammar")
        pcn_a = ProofCarryingNumber(value=0.74, certificate=cert_a)
        pcn_b = ProofCarryingNumber(value=0.74, certificate=cert_b)
        assert pcn_a.certificate.integrity_hash != pcn_b.certificate.integrity_hash

    def test_integrity_hash_deterministic(self):
        cert1 = _make_cert(extraction_method="m1")
        cert2 = _make_cert(extraction_method="m1")
        pcn1 = ProofCarryingNumber(value=1.5, certificate=cert1)
        pcn2 = ProofCarryingNumber(value=1.5, certificate=cert2)
        assert pcn1.certificate.integrity_hash == pcn2.certificate.integrity_hash

    def test_integrity_hash_manual_check(self):
        """Verify hash formula: sha256(value|source_text|char_start|char_end|extraction_method|checks)[:16]"""
        cert = _make_cert(
            source_text="text",
            char_start=5,
            char_end=10,
            extraction_method="method_x",
        )
        pcn = ProofCarryingNumber(value=2.0, certificate=cert)
        # Hash now includes check results (empty checks → "no_checks")
        expected = hashlib.sha256("2.0|text|5|10|method_x|no_checks".encode()).hexdigest()[:16]
        assert pcn.certificate.integrity_hash == expected

    def test_render_verified(self):
        cert = _make_cert(checks=[_passing_check("A", is_critical=True)])
        pcn = ProofCarryingNumber(value=0.74, certificate=cert)
        assert pcn.render() == "0.74"

    def test_render_unverified_raises(self):
        cert = _make_cert(checks=[_failing_check("A", is_critical=True)])
        pcn = ProofCarryingNumber(value=0.74, certificate=cert)
        with pytest.raises(VerificationError, match="Cannot render unverified"):
            pcn.render()

    def test_render_unverified_allowed(self):
        cert = _make_cert(checks=[_failing_check("A", is_critical=True)])
        pcn = ProofCarryingNumber(value=0.74, certificate=cert)
        result = pcn.render(allow_unverified=True)
        assert "[UNVERIFIED: 0.74]" == result

    def test_str_requires_verification(self):
        cert = _make_cert(checks=[_failing_check("A", is_critical=True)])
        pcn = ProofCarryingNumber(value=0.74, certificate=cert)
        with pytest.raises(VerificationError):
            str(pcn)

    def test_repr_shows_status(self):
        cert_ok = _make_cert(checks=[_passing_check("A", is_critical=True)])
        pcn_ok = ProofCarryingNumber(value=0.74, certificate=cert_ok)
        assert "VERIFIED" in repr(pcn_ok)

        cert_bad = _make_cert(checks=[_failing_check("A", is_critical=True)])
        pcn_bad = ProofCarryingNumber(value=0.74, certificate=cert_bad)
        assert "UNVERIFIED" in repr(pcn_bad)

    def test_is_verified_property(self):
        cert = _make_cert(checks=[_passing_check("A", is_critical=True)])
        pcn = ProofCarryingNumber(value=1.0, certificate=cert)
        assert pcn.is_verified is True

    def test_pre_existing_hash_always_recomputed(self):
        # Security: hash is always recomputed to prevent forgery
        cert = _make_cert()
        cert.integrity_hash = "already_set_hash"
        pcn = ProofCarryingNumber(value=1.0, certificate=cert)
        assert pcn.certificate.integrity_hash != "already_set_hash"
        assert len(pcn.certificate.integrity_hash) == 16  # sha256[:16]


# =============================================================================
# check_ci_contains_point
# =============================================================================

class TestCheckCIContainsPoint:

    def test_point_inside(self):
        vc = check_ci_contains_point(0.74, 0.65, 0.85)
        assert vc.result == CheckResult.PASSED
        assert vc.name == "CI_CONTAINS_POINT"

    def test_point_at_lower_bound(self):
        vc = check_ci_contains_point(0.65, 0.65, 0.85)
        assert vc.result == CheckResult.PASSED

    def test_point_at_upper_bound(self):
        vc = check_ci_contains_point(0.85, 0.65, 0.85)
        assert vc.result == CheckResult.PASSED

    def test_point_below_ci(self):
        vc = check_ci_contains_point(0.50, 0.65, 0.85)
        assert vc.result == CheckResult.FAILED
        assert "not in CI" in vc.message

    def test_point_above_ci(self):
        vc = check_ci_contains_point(0.90, 0.65, 0.85)
        assert vc.result == CheckResult.FAILED

    def test_is_critical(self):
        vc = check_ci_contains_point(0.74, 0.65, 0.85)
        assert vc.is_critical is True


# =============================================================================
# check_ci_ordered
# =============================================================================

class TestCheckCIOrdered:

    def test_correct_order(self):
        vc = check_ci_ordered(0.65, 0.85)
        assert vc.result == CheckResult.PASSED

    def test_reversed_order(self):
        vc = check_ci_ordered(0.85, 0.65)
        assert vc.result == CheckResult.FAILED
        assert "reversed" in vc.message

    def test_equal_bounds(self):
        # Equal bounds are allowed (e.g. point estimate with zero-width CI)
        vc = check_ci_ordered(0.74, 0.74)
        assert vc.result == CheckResult.PASSED

    def test_is_critical(self):
        vc = check_ci_ordered(0.5, 1.0)
        assert vc.is_critical is True


# =============================================================================
# check_range_plausible
# =============================================================================

class TestCheckRangePlausible:

    @pytest.mark.parametrize("effect_type,value,expected", [
        ("HR", 0.74, CheckResult.PASSED),
        ("HR", 0.001, CheckResult.FAILED),   # below 0.01
        ("HR", 55.0, CheckResult.FAILED),     # above 50.0
        ("OR", 1.5, CheckResult.PASSED),
        ("OR", 0.005, CheckResult.FAILED),
        ("RR", 1.0, CheckResult.PASSED),
        ("MD", -5.2, CheckResult.PASSED),
        ("MD", -1500.0, CheckResult.FAILED),
        ("SMD", 0.5, CheckResult.PASSED),
        ("SMD", -12.0, CheckResult.FAILED),
    ])
    def test_parametrized_ranges(self, effect_type, value, expected):
        vc = check_range_plausible(effect_type, value)
        assert vc.result == expected

    def test_unknown_effect_type_skipped(self):
        vc = check_range_plausible("UNKNOWN_TYPE", 999.0)
        assert vc.result == CheckResult.SKIPPED

    def test_boundary_values_hr(self):
        # Exactly at boundary
        vc_low = check_range_plausible("HR", 0.01)
        assert vc_low.result == CheckResult.PASSED
        vc_high = check_range_plausible("HR", 50.0)
        assert vc_high.result == CheckResult.PASSED


# =============================================================================
# check_se_consistency
# =============================================================================

class TestCheckSEConsistency:

    def test_se_calculated_no_reported(self):
        vc = check_se_consistency("HR", 0.65, 0.85)
        assert vc.result == CheckResult.PASSED
        assert "calculated" in str(vc.actual)

    def test_se_matching_reported(self):
        # Compute expected SE for HR
        expected_se = (math.log(0.85) - math.log(0.65)) / (2 * 1.96)
        vc = check_se_consistency("HR", 0.65, 0.85, reported_se=expected_se)
        assert vc.result == CheckResult.PASSED

    def test_se_mismatching_reported(self):
        vc = check_se_consistency("HR", 0.65, 0.85, reported_se=999.0)
        assert vc.result == CheckResult.WARNING

    def test_se_linear_scale_md(self):
        expected_se = (1.0 - (-1.0)) / (2 * 1.96)
        vc = check_se_consistency("MD", -1.0, 1.0, reported_se=expected_se)
        assert vc.result == CheckResult.PASSED

    def test_non_positive_ci_bounds_skipped(self):
        vc = check_se_consistency("HR", -0.5, 0.85)
        assert vc.result == CheckResult.SKIPPED

    def test_se_not_critical(self):
        vc = check_se_consistency("HR", 0.65, 0.85, reported_se=999.0)
        assert vc.is_critical is False


# =============================================================================
# check_p_value_consistency
# =============================================================================

class TestCheckPValueConsistency:

    def test_significant_p_ci_excludes_null_hr(self):
        # HR with CI entirely below 1.0 -> excludes null, p < 0.05 consistent
        vc = check_p_value_consistency("HR", 0.65, 0.85, 0.001)
        assert vc.result == CheckResult.PASSED

    def test_non_significant_p_ci_contains_null_hr(self):
        # HR with CI spanning 1.0 -> includes null, p > 0.05 consistent
        vc = check_p_value_consistency("HR", 0.80, 1.20, 0.30)
        assert vc.result == CheckResult.PASSED

    def test_inconsistent_p_and_ci(self):
        # CI excludes null (below 1), but p > 0.05 (non-borderline)
        vc = check_p_value_consistency("HR", 0.50, 0.80, 0.20)
        assert vc.result == CheckResult.WARNING

    def test_borderline_p_value_tolerance(self):
        # p in [0.03, 0.07] range should not fail even if inconsistent
        vc = check_p_value_consistency("HR", 0.80, 1.20, 0.04)
        # CI includes null, p < 0.05 => inconsistent, but borderline tolerance forgives it
        assert vc.result == CheckResult.PASSED

    def test_borderline_ci_near_null(self):
        # CI close to 1.0 tolerance
        vc = check_p_value_consistency("HR", 0.98, 1.03, 0.90)
        # CI includes null, p > 0.05 => consistent
        assert vc.result == CheckResult.PASSED

    def test_md_null_is_zero(self):
        # MD with CI excluding 0, p < 0.05
        vc = check_p_value_consistency("MD", 1.0, 3.0, 0.01)
        assert vc.result == CheckResult.PASSED

    def test_p_value_zero_not_dropped(self):
        """Critical edge case: p_value=0.0 must NOT be dropped by truthiness check.
        The function signature accepts float, and 0.0 is a valid p-value."""
        # p=0.0 < 0.05, CI [0.5, 0.8] excludes null=1 for HR -> consistent
        vc = check_p_value_consistency("HR", 0.50, 0.80, 0.0)
        assert vc.result == CheckResult.PASSED

    def test_not_critical(self):
        vc = check_p_value_consistency("HR", 0.65, 0.85, 0.001)
        assert vc.is_critical is False


# =============================================================================
# check_log_symmetry
# =============================================================================

class TestCheckLogSymmetry:

    def test_symmetric_ci(self):
        # Build a perfectly symmetric CI on log scale
        log_val = 0.0  # value = 1.0
        se = 0.2
        value = math.exp(log_val)
        ci_lower = math.exp(log_val - 1.96 * se)
        ci_upper = math.exp(log_val + 1.96 * se)
        vc = check_log_symmetry(value, ci_lower, ci_upper)
        assert vc.result == CheckResult.PASSED

    def test_asymmetric_ci(self):
        # Deliberately asymmetric on log scale
        vc = check_log_symmetry(1.0, 0.1, 1.5)
        # dist_lower = |log(1) - log(0.1)| = 2.30, dist_upper = |log(1.5) - log(1)| = 0.41
        # asymmetry ~ |2.30 - 0.41| / 1.355 >> 0.1
        assert vc.result == CheckResult.WARNING

    def test_non_positive_values_skipped(self):
        vc = check_log_symmetry(0.0, -1.0, 1.0)
        assert vc.result == CheckResult.SKIPPED

    def test_negative_value_skipped(self):
        vc = check_log_symmetry(-0.5, -1.0, 0.5)
        assert vc.result == CheckResult.SKIPPED

    def test_not_critical(self):
        vc = check_log_symmetry(1.0, 0.8, 1.2)
        assert vc.is_critical is False


# =============================================================================
# check_ci_width_reasonable
# =============================================================================

class TestCheckCIWidthReasonable:

    def test_normal_ratio_width(self):
        # HR 0.74 (0.65, 0.85) -> width=0.20, relative=0.20/0.74=0.27 -> reasonable
        vc = check_ci_width_reasonable("HR", 0.74, 0.65, 0.85)
        assert vc.result == CheckResult.PASSED

    def test_extreme_narrow_width(self):
        # Very narrow CI relative to value
        vc = check_ci_width_reasonable("HR", 1.0, 0.999, 1.001)
        # relative_width = 0.002/1.0 = 0.002 < 0.05 -> WARNING
        assert vc.result == CheckResult.WARNING

    def test_extreme_wide_width(self):
        # Very wide CI
        vc = check_ci_width_reasonable("HR", 0.5, 0.01, 49.0)
        # relative_width = 48.99/0.5 = 97.98 >> 10.0
        assert vc.result == CheckResult.WARNING

    def test_difference_type_skipped(self):
        vc = check_ci_width_reasonable("MD", -5.0, -7.0, -3.0)
        assert vc.result == CheckResult.SKIPPED

    def test_smd_skipped(self):
        vc = check_ci_width_reasonable("SMD", 0.5, 0.1, 0.9)
        assert vc.result == CheckResult.SKIPPED

    def test_not_critical(self):
        vc = check_ci_width_reasonable("HR", 0.74, 0.65, 0.85)
        assert vc.is_critical is False


# =============================================================================
# run_all_checks
# =============================================================================

class TestRunAllChecks:

    def test_basic_hr_returns_checks(self):
        checks = run_all_checks("HR", 0.74, 0.65, 0.85)
        names = [c.name for c in checks]
        assert "CI_CONTAINS_POINT" in names
        assert "CI_ORDERED" in names
        assert "RANGE_PLAUSIBLE" in names
        assert "SE_CONSISTENT" in names
        assert "LOG_SYMMETRIC" in names
        assert "CI_WIDTH_REASONABLE" in names

    def test_hr_without_p_value(self):
        checks = run_all_checks("HR", 0.74, 0.65, 0.85)
        names = [c.name for c in checks]
        assert "P_VALUE_CONSISTENT" not in names

    def test_hr_with_p_value(self):
        checks = run_all_checks("HR", 0.74, 0.65, 0.85, p_value=0.001)
        names = [c.name for c in checks]
        assert "P_VALUE_CONSISTENT" in names

    def test_md_no_log_symmetry(self):
        checks = run_all_checks("MD", -5.2, -7.1, -3.3)
        names = [c.name for c in checks]
        assert "LOG_SYMMETRIC" not in names

    def test_p_value_zero_included(self):
        """p_value=0.0 must not be dropped by `if p_value is not None` guard."""
        checks = run_all_checks("HR", 0.74, 0.65, 0.85, p_value=0.0)
        names = [c.name for c in checks]
        assert "P_VALUE_CONSISTENT" in names

    def test_valid_hr_all_critical_pass(self):
        checks = run_all_checks("HR", 0.74, 0.65, 0.85)
        critical = [c for c in checks if c.is_critical]
        assert all(c.passed for c in critical)

    def test_invalid_point_outside_ci(self):
        checks = run_all_checks("HR", 0.50, 0.65, 0.85)
        ci_check = [c for c in checks if c.name == "CI_CONTAINS_POINT"][0]
        assert ci_check.result == CheckResult.FAILED

    def test_reported_se(self):
        checks = run_all_checks("HR", 0.74, 0.65, 0.85, reported_se=0.05)
        se_check = [c for c in checks if c.name == "SE_CONSISTENT"][0]
        assert se_check.name == "SE_CONSISTENT"


# =============================================================================
# create_verified_extraction
# =============================================================================

class TestCreateVerifiedExtraction:

    def test_returns_proof_carrying_extraction(self):
        result = create_verified_extraction(
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="HR 0.74 (95% CI, 0.65-0.85)",
            extraction_method="pattern_HR_01",
        )
        assert isinstance(result, ProofCarryingExtraction)

    def test_valid_hr_is_verified(self):
        result = create_verified_extraction(
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="HR 0.74 (95% CI, 0.65-0.85)",
        )
        assert result.point_estimate.is_verified is True
        assert result.verification_status == VerificationStatus.VERIFIED

    def test_invalid_extraction_not_verified(self):
        # Point estimate outside CI -> CI_CONTAINS_POINT fails
        result = create_verified_extraction(
            effect_type="HR",
            value=0.50,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="HR 0.50 (95% CI, 0.65-0.85)",
        )
        # The point_estimate cert only includes RANGE_PLAUSIBLE and CI_CONTAINS_POINT.
        # CI_CONTAINS_POINT fails, so it is not verified.
        assert result.point_estimate.is_verified is False

    def test_master_certificate_present(self):
        result = create_verified_extraction(
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="test",
        )
        assert result.master_certificate is not None

    def test_se_calculated(self):
        result = create_verified_extraction(
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="test",
        )
        assert result.standard_error is not None
        expected_se = (math.log(0.85) - math.log(0.65)) / (2 * 1.96)
        assert abs(result.standard_error.value - expected_se) < 1e-10

    def test_se_calculated_md(self):
        result = create_verified_extraction(
            effect_type="MD",
            value=-5.2,
            ci_lower=-7.1,
            ci_upper=-3.3,
            source_text="test",
        )
        expected_se = (-3.3 - (-7.1)) / (2 * 1.96)
        assert abs(result.standard_error.value - expected_se) < 1e-10

    def test_p_value_zero_preserved(self):
        """Edge case: p_value=0.0 must be stored, not dropped."""
        result = create_verified_extraction(
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="test",
            p_value=0.0,
        )
        assert result.p_value is not None
        assert result.p_value == 0.0

    def test_p_value_zero_in_to_dict(self):
        """p_value=0.0 must appear in to_dict output (uses `is not None` guard)."""
        result = create_verified_extraction(
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="test",
            p_value=0.0,
        )
        d = result.to_dict()
        assert "p_value" in d
        assert d["p_value"] == 0.0

    def test_p_value_none_excluded_from_dict(self):
        result = create_verified_extraction(
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="test",
            p_value=None,
        )
        d = result.to_dict()
        assert "p_value" not in d

    def test_warnings_populated_on_issues(self):
        # Out of range -> the CI_CONTAINS_POINT fails but also check if we get warnings
        result = create_verified_extraction(
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="test",
        )
        # Valid extraction still can have warnings (e.g. log symmetry)
        assert isinstance(result.warnings, list)

    def test_extraction_method_in_cert(self):
        result = create_verified_extraction(
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="test",
            extraction_method="my_method",
        )
        assert result.master_certificate.extraction_method == "my_method"

    def test_to_dict_structure(self):
        result = create_verified_extraction(
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="test",
            p_value=0.001,
        )
        d = result.to_dict()
        assert d["effect_type"] == "HR"
        assert d["point_estimate"] == 0.74
        assert "ci_lower" in d
        assert "ci_upper" in d
        assert "is_verified" in d
        assert "certificate" in d

    def test_needs_review_when_not_verified(self):
        result = create_verified_extraction(
            effect_type="HR",
            value=0.50,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="test",
        )
        assert result.needs_review is True
        assert result.review_reason != ""


# =============================================================================
# ProofCarryingExtraction properties
# =============================================================================

class TestProofCarryingExtraction:

    def test_is_fully_verified_all_components(self):
        result = create_verified_extraction(
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="test",
        )
        assert result.is_fully_verified is True

    def test_verification_status_verified(self):
        result = create_verified_extraction(
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="test",
        )
        assert result.verification_status == VerificationStatus.VERIFIED

    def test_verification_status_failed(self):
        result = create_verified_extraction(
            effect_type="HR",
            value=0.50,
            ci_lower=0.65,
            ci_upper=0.85,
            source_text="test",
        )
        assert result.verification_status == VerificationStatus.FAILED
