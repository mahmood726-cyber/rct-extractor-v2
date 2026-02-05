"""
Tests for CTG Cross-Validation
==============================

Tests for ClinicalTrials.gov scraper and validator modules.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.ctg_scraper import (
    CTGScraper,
    CTGStudy,
    EffectEstimate,
    OutcomeMeasure,
)
from scripts.ctg_validator import (
    CTGValidator,
    ValidationResult,
    StudyValidation,
)


class TestCTGScraperStructures:
    """Tests for CTG scraper data structures"""

    def test_effect_estimate_creation(self):
        """Test EffectEstimate dataclass"""
        effect = EffectEstimate(
            outcome_title="Overall Survival",
            outcome_type="primary",
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            p_value=0.001,
            arm1_name="Treatment",
            arm1_n=500,
            arm1_value=0.25,
            arm2_name="Placebo",
            arm2_n=500,
            arm2_value=0.35,
            analysis_method="Cox regression",
            source_text="HR 0.74 (0.65-0.85)"
        )
        assert effect.effect_type == "HR"
        assert effect.value == 0.74
        assert effect.ci_lower == 0.65
        assert effect.ci_upper == 0.85

    def test_outcome_measure_creation(self):
        """Test OutcomeMeasure dataclass"""
        outcome = OutcomeMeasure(
            title="Overall Survival",
            description="Time to death from any cause",
            time_frame="24 months",
            outcome_type="primary",
            population="ITT",
            units="months"
        )
        assert outcome.title == "Overall Survival"
        assert outcome.outcome_type == "primary"

    def test_ctg_study_creation(self):
        """Test CTGStudy dataclass"""
        study = CTGStudy(
            nct_id="NCT01234567",
            title="Test Study",
            status="Completed",
            phase="Phase 3",
            conditions=["Heart Failure"],
            interventions=["Drug A"],
            enrollment=1000,
            start_date="2020-01-01",
            completion_date="2023-01-01",
            sponsor="Test Sponsor",
            has_results=True,
            outcomes=[],
            effect_estimates=[]
        )
        assert study.nct_id == "NCT01234567"
        assert study.enrollment == 1000

    def test_ctg_study_asdict(self):
        """Test CTGStudy conversion to dict via asdict"""
        from dataclasses import asdict

        effect = EffectEstimate(
            outcome_title="Overall Survival",
            outcome_type="primary",
            effect_type="HR",
            value=0.74,
            ci_lower=0.65,
            ci_upper=0.85,
            p_value=0.001,
            arm1_name="Treatment",
            arm1_n=500,
            arm1_value=0.25,
            arm2_name="Placebo",
            arm2_n=500,
            arm2_value=0.35,
            analysis_method="Cox regression",
            source_text="HR 0.74 (0.65-0.85)"
        )
        study = CTGStudy(
            nct_id="NCT01234567",
            title="Test Study",
            status="Completed",
            phase="Phase 3",
            conditions=[],
            interventions=[],
            enrollment=1000,
            start_date="",
            completion_date="",
            sponsor="",
            has_results=True,
            outcomes=[],
            effect_estimates=[effect]
        )
        data = asdict(study)
        assert data["nct_id"] == "NCT01234567"
        assert len(data["effect_estimates"]) == 1
        assert data["effect_estimates"][0]["value"] == 0.74


class TestCTGScraper:
    """Tests for CTG scraper functionality"""

    def setup_method(self):
        """Set up scraper"""
        self.scraper = CTGScraper()

    def test_scraper_initialization(self):
        """Test scraper initializes correctly"""
        assert self.scraper is not None

    def test_scraper_has_fetch_method(self):
        """Test scraper has fetch_study method"""
        assert hasattr(self.scraper, 'fetch_study')
        assert callable(self.scraper.fetch_study)

    def test_scraper_has_search_method(self):
        """Test scraper has search_studies method"""
        assert hasattr(self.scraper, 'search_studies')
        assert callable(self.scraper.search_studies)

    def test_scraper_has_fetch_multiple_method(self):
        """Test scraper has fetch_multiple method"""
        assert hasattr(self.scraper, 'fetch_multiple')
        assert callable(self.scraper.fetch_multiple)

    def test_empty_nct_id_returns_none(self):
        """Test that empty NCT ID returns None"""
        # This should not make an API call for empty ID
        result = self.scraper.fetch_study("")
        assert result is None

    def test_invalid_nct_format(self):
        """Test that invalid NCT format is handled"""
        # Invalid format should return None without error
        result = self.scraper.fetch_study("INVALID")
        # May return None or make API call and fail gracefully
        assert result is None or isinstance(result, CTGStudy)


class TestCTGValidator:
    """Tests for CTG validator functionality"""

    def setup_method(self):
        """Set up validator"""
        self.validator = CTGValidator()

    def test_validator_initialization(self):
        """Test validator initializes with correct tolerances"""
        assert self.validator.value_tolerance == 0.02  # 2%
        assert self.validator.ci_tolerance == 0.05  # 5%

    def test_values_match_exact(self):
        """Test exact value match"""
        assert self.validator._values_match(0.74, 0.74) == True

    def test_values_match_within_tolerance(self):
        """Test value match within tolerance"""
        # 2% tolerance
        # 0.74 to 0.75 = 1.3% diff (within 2%)
        assert self.validator._values_match(0.74, 0.75) == True
        # 0.74 to 0.76 = 2.7% diff (outside 2%)
        assert self.validator._values_match(0.74, 0.76) == False

    def test_values_match_zero(self):
        """Test value match with zeros"""
        assert self.validator._values_match(0, 0) == True
        assert self.validator._values_match(0, 0.1) == False
        assert self.validator._values_match(0.1, 0) == False

    def test_cis_match_exact(self):
        """Test exact CI match"""
        assert self.validator._cis_match((0.65, 0.85), (0.65, 0.85)) == True

    def test_cis_match_within_tolerance(self):
        """Test CI match within tolerance"""
        assert self.validator._cis_match((0.65, 0.85), (0.66, 0.86)) == True

    def test_cis_match_no_expected(self):
        """Test CI match when no expected CI"""
        assert self.validator._cis_match((None, None), (0.65, 0.85)) == True

    def test_cis_match_no_extracted(self):
        """Test CI match when no extracted CI"""
        assert self.validator._cis_match((0.65, 0.85), (None, None)) == False

    def test_match_score_calculation(self):
        """Test match score calculation"""
        ctg_effect = {
            "effect_type": "HR",
            "value": 0.74,
            "ci_lower": 0.65,
            "ci_upper": 0.85
        }

        # Create mock extraction
        class MockExtraction:
            class EffectType:
                value = "HR"
            effect_type = EffectType()
            point_estimate = 0.74
            class CI:
                lower = 0.65
                upper = 0.85
            ci = CI()

        extraction = MockExtraction()
        score = self.validator._match_score(ctg_effect, extraction)

        # Perfect match should have high score
        assert score >= 0.8


class TestValidationResult:
    """Tests for ValidationResult dataclass"""

    def test_validation_result_creation(self):
        """Test ValidationResult creation"""
        result = ValidationResult(
            nct_id="NCT01234567",
            outcome="Overall Survival",
            expected_type="HR",
            expected_value=0.74,
            expected_ci=(0.65, 0.85),
            extracted_type="HR",
            extracted_value=0.74,
            extracted_ci=(0.65, 0.85),
            value_match=True,
            type_match=True,
            ci_match=True,
            overall_match=True,
            source="ctg"
        )
        assert result.overall_match == True
        assert result.value_match == True


class TestStudyValidation:
    """Tests for StudyValidation dataclass"""

    def test_study_validation_creation(self):
        """Test StudyValidation creation"""
        validation = StudyValidation(
            nct_id="NCT01234567",
            title="Test Study",
            pdf_path=None,
            ctg_effects=5,
            pdf_effects=4,
            matched=4,
            value_accuracy=0.8,
            type_accuracy=1.0,
            ci_accuracy=0.6,
            results=[]
        )
        assert validation.matched == 4
        assert validation.value_accuracy == 0.8


class TestIntegration:
    """Integration tests for CTG validation"""

    def test_validate_study_no_effects(self):
        """Test validation with no effects"""
        validator = CTGValidator()
        ctg_data = {
            "nct_id": "NCT01234567",
            "title": "Test Study",
            "effect_estimates": []
        }
        result = validator.validate_study(ctg_data)
        assert result.ctg_effects == 0
        assert result.matched == 0

    def test_validate_study_with_effects(self):
        """Test validation with effects"""
        validator = CTGValidator()
        ctg_data = {
            "nct_id": "NCT01234567",
            "title": "Test Study",
            "effect_estimates": [
                {
                    "effect_type": "HR",
                    "value": 0.74,
                    "ci_lower": 0.65,
                    "ci_upper": 0.85,
                    "outcome_title": "Overall Survival"
                }
            ]
        }
        # Test with just CTG data (no PDF)
        result = validator.validate_study(ctg_data, pdf_text="")
        assert result.ctg_effects == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
