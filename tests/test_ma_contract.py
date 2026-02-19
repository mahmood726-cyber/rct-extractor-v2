"""Tests for meta-analysis output contract validation."""

import pytest
from pydantic import ValidationError

from src.core.ma_contract import MAExtractionRecord


def _base_record():
    return {
        "study_id": "DAPA_HF_2019",
        "outcome_name": "CV death or HF hospitalization",
        "effect_type": "HR",
        "point_estimate": 0.74,
        "ci_lower": 0.65,
        "ci_upper": 0.85,
        "standard_error": None,
        "p_value": 0.001,
        "timepoint": "median 18.2 months",
        "is_primary": True,
        "is_subgroup": False,
        "computation_origin": "reported",
        "provenance": {
            "source_text": "HR 0.74 (95% CI 0.65-0.85, P<0.001)",
            "page_number": 4,
            "source_type": "text",
            "char_start": 120,
            "char_end": 160,
        },
    }


def test_valid_record_with_ci():
    record = MAExtractionRecord.model_validate(_base_record())
    assert record.is_meta_analysis_ready is True
    assert record.has_complete_ci is True


def test_valid_record_with_standard_error_only():
    payload = _base_record()
    payload["ci_lower"] = None
    payload["ci_upper"] = None
    payload["standard_error"] = 0.0684
    record = MAExtractionRecord.model_validate(payload)
    assert record.is_meta_analysis_ready is True


def test_missing_ci_and_se_is_rejected():
    payload = _base_record()
    payload["ci_lower"] = None
    payload["ci_upper"] = None
    payload["standard_error"] = None
    with pytest.raises(ValidationError):
        MAExtractionRecord.model_validate(payload)


def test_ratio_effect_must_be_positive():
    payload = _base_record()
    payload["point_estimate"] = -0.74
    with pytest.raises(ValidationError):
        MAExtractionRecord.model_validate(payload)


def test_point_must_be_inside_ci():
    payload = _base_record()
    payload["point_estimate"] = 0.9
    payload["ci_lower"] = 0.65
    payload["ci_upper"] = 0.85
    with pytest.raises(ValidationError):
        MAExtractionRecord.model_validate(payload)
