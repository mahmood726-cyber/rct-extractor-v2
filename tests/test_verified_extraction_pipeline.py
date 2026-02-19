"""Regression tests for verified extraction reporting."""

from src.core.verified_extraction_pipeline import (
    PipelineResult,
    PipelineStatus,
    generate_verification_report,
)


def test_report_includes_zero_ci_and_se():
    """Zero-valued CI bounds and SE should not be dropped from report output."""
    result = PipelineResult(
        source_text="synthetic",
        effect_type="MD",
        value=0.0,
        ci_lower=0.0,
        ci_upper=0.2,
        standard_error=0.0,
        p_value=0.0,
        pcn_extraction=None,
        consensus_result=None,
        verification_result=None,
        status=PipelineStatus.VERIFIED,
        confidence=0.9,
        is_usable=True,
    )

    report = generate_verification_report([result])

    assert "95% CI: [0.0, 0.2]" in report
    assert "SE: 0.0000" in report
