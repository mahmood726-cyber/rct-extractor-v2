"""Tests for the thyroid cancer specialty profile, registry wiring, arm-level.

Distinct from the `thyroid` (benign thyroid dysfunction) specialty.
"""
import pytest

from rct_extractor._engine.specialties.thyroid_cancer import (
    THYROID_CANCER_ENDPOINTS, detect_thyroid_cancer_subspecialty,
    normalize_thyroid_cancer_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.thyroid_cancer_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of lenvatinib versus placebo in radioiodine-refractory "
     "differentiated thyroid cancer (DTC); progression-free survival and "
     "objective response.", "differentiated"),
    ("Randomized trial of cabozantinib versus placebo in progressive medullary "
     "thyroid carcinoma (MTC); progression-free survival and objective response.",
     "medullary"),
    ("Trial of dabrafenib plus trametinib in BRAF V600E anaplastic thyroid "
     "carcinoma (ATC); overall survival and objective response.", "anaplastic"),
    ("Registry follow-up reporting thyroid cancer-specific mortality and "
     "all-cause mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_thyroid_cancer_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("progression-free survival", "PFS"),
    ("objective response rate", "ORR"),
    ("time to progression", "TTP"),
    ("disease control rate", "DCR"),
    ("thyroid cancer-specific mortality", "THYROID_CANCER_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_thyroid_cancer_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in THYROID_CANCER_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"differentiated", "medullary", "anaplastic", "mortality"}


def test_thyroid_cancer_registered():
    assert "thyroid_cancer" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["thyroid_cancer"]
    assert e["detection_function"] is detect_thyroid_cancer_subspecialty
    assert set(e["subspecialties"]) == {"differentiated", "medullary", "anaplastic", "mortality"}


def test_detect_specialty_routes_to_thyroid_cancer():
    spec, sub, _ = detect_specialty(
        "Randomized trial of lenvatinib versus sorafenib in radioiodine-refractory "
        "differentiated thyroid cancer; progression-free survival and objective "
        "response rate.")
    assert spec == "thyroid_cancer" and sub == "differentiated"


def test_thyroid_cancer_distinct_from_thyroid_disease():
    # benign thyroid dysfunction must still route to `thyroid`, not thyroid_cancer
    assert detect_specialty(
        "Levothyroxine versus placebo in subclinical hypothyroidism; TSH "
        "normalisation and free thyroxine.")[0] == "thyroid"


def test_thyroid_cancer_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"


def test_response_2x2():
    t = ("An objective response occurred in 130/200 (65.0%) in the "
         "lenvatinib group versus 4/200 (2.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ORR"
