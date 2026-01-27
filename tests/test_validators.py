"""
Tests for validators module
"""

import pytest
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.models import (
    BinaryOutcome, HazardRatioCI, OddsRatioCI, RiskRatioCI,
    MeanDifference, Provenance, ReviewSeverity
)
from src.validators.validators import (
    validate_binary_outcome,
    validate_hazard_ratio,
    validate_odds_ratio,
    validate_risk_ratio,
    validate_mean_difference,
    ValidationIssue
)


class TestValidateBinaryOutcome:
    """Tests for binary outcome validation"""

    def test_valid_outcome(self):
        """Valid binary outcome passes validation"""
        outcome = BinaryOutcome(
            arm_id="treatment",
            events=50,
            n=100,
            percentage=50.0,
            provenance=Provenance(
                pdf_file="test.pdf",
                page_number=1,
                raw_text="50/100 (50%)",
                extraction_method="test"
            )
        )
        issues = validate_binary_outcome(outcome)
        error_issues = [i for i in issues if i.severity == ReviewSeverity.ERROR]
        assert len(error_issues) == 0

    def test_events_greater_than_n(self):
        """Events > n should fail"""
        outcome = BinaryOutcome(
            arm_id="treatment",
            events=150,
            n=100,
            provenance=Provenance(
                pdf_file="test.pdf",
                page_number=1,
                raw_text="150/100",
                extraction_method="test"
            )
        )
        issues = validate_binary_outcome(outcome)
        assert any(i.code == "EVENTS_GT_N" for i in issues)

    def test_negative_n(self):
        """Negative n should fail"""
        outcome = BinaryOutcome(
            arm_id="treatment",
            events=50,
            n=-100,
            provenance=Provenance(
                pdf_file="test.pdf",
                page_number=1,
                raw_text="50/-100",
                extraction_method="test"
            )
        )
        issues = validate_binary_outcome(outcome)
        assert any(i.code == "N_NOT_POSITIVE" for i in issues)

    def test_percentage_mismatch(self):
        """Percentage mismatch should warn"""
        outcome = BinaryOutcome(
            arm_id="treatment",
            events=50,
            n=100,
            percentage=60.0,  # Wrong! Should be 50%
            provenance=Provenance(
                pdf_file="test.pdf",
                page_number=1,
                raw_text="50/100 (60%)",
                extraction_method="test"
            )
        )
        issues = validate_binary_outcome(outcome)
        assert any(i.code == "PERCENTAGE_MISMATCH" for i in issues)


class TestValidateHazardRatio:
    """Tests for hazard ratio validation"""

    def test_valid_hr(self):
        """Valid HR passes validation"""
        hr = HazardRatioCI(
            hr=0.75,
            ci_low=0.65,
            ci_high=0.87,
            provenance=Provenance(
                pdf_file="test.pdf",
                page_number=1,
                raw_text="HR 0.75 (95% CI 0.65-0.87)",
                extraction_method="test"
            )
        )
        issues = validate_hazard_ratio(hr)
        error_issues = [i for i in issues if i.severity == ReviewSeverity.ERROR]
        assert len(error_issues) == 0

    def test_negative_hr(self):
        """Negative HR should fail"""
        hr = HazardRatioCI(
            hr=-0.75,
            ci_low=0.65,
            ci_high=0.87,
            provenance=Provenance(
                pdf_file="test.pdf",
                page_number=1,
                raw_text="HR -0.75",
                extraction_method="test"
            )
        )
        issues = validate_hazard_ratio(hr)
        assert any(i.code == "HR_NOT_POSITIVE" for i in issues)

    def test_inverted_ci(self):
        """CI lower >= upper should fail"""
        hr = HazardRatioCI(
            hr=0.75,
            ci_low=0.87,
            ci_high=0.65,  # Inverted!
            provenance=Provenance(
                pdf_file="test.pdf",
                page_number=1,
                raw_text="HR 0.75 (95% CI 0.87-0.65)",
                extraction_method="test"
            )
        )
        issues = validate_hazard_ratio(hr)
        assert any(i.code == "CI_INVERTED" for i in issues)

    def test_hr_outside_ci(self):
        """HR outside CI should fail"""
        hr = HazardRatioCI(
            hr=0.50,  # Outside CI
            ci_low=0.65,
            ci_high=0.87,
            provenance=Provenance(
                pdf_file="test.pdf",
                page_number=1,
                raw_text="HR 0.50 (95% CI 0.65-0.87)",
                extraction_method="test"
            )
        )
        issues = validate_hazard_ratio(hr)
        assert any(i.code == "HR_OUTSIDE_CI" for i in issues)

    def test_pvalue_ci_mismatch(self):
        """P-value inconsistent with CI should warn"""
        hr = HazardRatioCI(
            hr=0.90,
            ci_low=0.80,
            ci_high=1.10,  # CI crosses 1, so p should be > 0.05
            p_value=0.01,  # But p < 0.05!
            provenance=Provenance(
                pdf_file="test.pdf",
                page_number=1,
                raw_text="HR 0.90 (95% CI 0.80-1.10), p=0.01",
                extraction_method="test"
            )
        )
        issues = validate_hazard_ratio(hr)
        assert any(i.code == "PVALUE_CI_MISMATCH" for i in issues)


class TestValidateOddsRatio:
    """Tests for odds ratio validation"""

    def test_valid_or(self):
        """Valid OR passes validation"""
        or_val = OddsRatioCI(
            or_value=1.50,
            ci_low=1.20,
            ci_high=1.88,
            provenance=Provenance(
                pdf_file="test.pdf",
                page_number=1,
                raw_text="OR 1.50 (95% CI 1.20-1.88)",
                extraction_method="test"
            )
        )
        issues = validate_odds_ratio(or_val)
        error_issues = [i for i in issues if i.severity == ReviewSeverity.ERROR]
        assert len(error_issues) == 0


class TestValidateMeanDifference:
    """Tests for mean difference validation"""

    def test_valid_md(self):
        """Valid MD passes validation"""
        md = MeanDifference(
            md=-2.5,
            ci_low=-4.0,
            ci_high=-1.0,
            provenance=Provenance(
                pdf_file="test.pdf",
                page_number=1,
                raw_text="MD -2.5 (95% CI -4.0 to -1.0)",
                extraction_method="test"
            )
        )
        issues = validate_mean_difference(md)
        error_issues = [i for i in issues if i.severity == ReviewSeverity.ERROR]
        assert len(error_issues) == 0

    def test_md_outside_ci(self):
        """MD outside CI should fail"""
        md = MeanDifference(
            md=-5.0,  # Outside CI
            ci_low=-4.0,
            ci_high=-1.0,
            provenance=Provenance(
                pdf_file="test.pdf",
                page_number=1,
                raw_text="MD -5.0 (95% CI -4.0 to -1.0)",
                extraction_method="test"
            )
        )
        issues = validate_mean_difference(md)
        assert any(i.code == "MD_OUTSIDE_CI" for i in issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
