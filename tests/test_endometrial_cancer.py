"""Tests for the endometrial cancer specialty profile, registry wiring, arm-level.

Distinct from the `endometriosis` (benign gynaecological) specialty.
"""
import pytest

from rct_extractor._engine.specialties.endometrial_cancer import (
    ENDOMETRIAL_CANCER_ENDPOINTS, detect_endometrial_cancer_subspecialty,
    normalize_endometrial_cancer_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.endometrial_cancer_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of carboplatin-paclitaxel versus doxorubicin in advanced or "
     "recurrent endometrial carcinoma; progression-free survival and overall "
     "survival.", "advanced"),
    ("Randomized trial of adjuvant pelvic radiotherapy versus vaginal "
     "brachytherapy in early-stage high-intermediate-risk endometrial cancer "
     "(PORTEC); recurrence-free survival.", "adjuvant"),
    ("Trial of dostarlimab plus chemotherapy in mismatch-repair-deficient (dMMR) "
     "endometrial cancer; progression-free survival and objective response.",
     "immunotherapy"),
    ("Registry follow-up reporting endometrial cancer-specific mortality and "
     "all-cause mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_endometrial_cancer_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("progression-free survival", "PFS"),
    ("recurrence-free survival", "RFS"),
    ("objective response rate", "ORR"),
    ("time to progression", "TTP"),
    ("uterine cancer mortality", "ENDOMETRIAL_CANCER_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_endometrial_cancer_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in ENDOMETRIAL_CANCER_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"advanced", "adjuvant", "immunotherapy", "mortality"}


def test_endometrial_cancer_registered():
    assert "endometrial_cancer" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["endometrial_cancer"]
    assert e["detection_function"] is detect_endometrial_cancer_subspecialty
    assert set(e["subspecialties"]) == {"advanced", "adjuvant", "immunotherapy", "mortality"}


def test_detect_specialty_routes_to_endometrial_cancer():
    spec, sub, _ = detect_specialty(
        "Randomized trial of pembrolizumab plus lenvatinib versus chemotherapy in "
        "advanced endometrial cancer; progression-free survival and overall "
        "survival.")
    assert spec == "endometrial_cancer" and sub in {"advanced", "immunotherapy"}


def test_endometrial_cancer_distinct_from_endometriosis():
    # benign endometriosis must still route to `endometriosis`, not the cancer
    assert detect_specialty(
        "Dienogest versus placebo for endometriosis-associated pelvic pain; "
        "reduction in dysmenorrhoea.")[0] == "endometriosis"


def test_endometrial_cancer_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"


def test_response_2x2():
    t = ("An objective response occurred in 90/200 (45.0%) in the "
         "dostarlimab group versus 50/200 (25.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ORR"
