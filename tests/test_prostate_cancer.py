"""
Tests for the prostate-cancer specialty profile, registry wiring, and arm-level
extraction. Mirrors the cervical-cancer, typhoid, HIV and malaria tests.
"""
import pytest

from rct_extractor._engine.specialties.prostate_cancer import (
    PROSTATE_CANCER_ENDPOINTS, detect_prostate_cancer_subspecialty,
    normalize_prostate_cancer_endpoint, get_prostate_cancer_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.prostate_cancer_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of enzalutamide plus androgen-deprivation therapy versus placebo "
     "in metastatic castration-resistant prostate cancer (mCRPC); radiographic "
     "progression-free survival and PSA response.", "systemic"),
    ("RCT of dose-escalated external-beam radiotherapy versus radical prostatectomy "
     "in localized prostate cancer; biochemical recurrence-free survival and "
     "metastasis-free survival in intermediate-risk Gleason 7 disease.", "localized"),
    ("Trial of degarelix versus leuprolide for androgen-deprivation therapy; "
     "castrate testosterone level and testosterone suppression at 12 months.",
     "hormonal"),
    ("Long-term follow-up of a screening RCT reporting prostate cancer-specific "
     "mortality and distant metastasis per 1000 person-years.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_prostate_cancer_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("radiographic progression-free survival", "RPFS"),
    ("PSA response rate", "PSA_RESPONSE"),
    ("time to PSA progression", "TIME_TO_PSA_PROGRESSION"),
    ("skeletal-related event", "SRE"),
    ("biochemical recurrence", "BIOCHEMICAL_RECURRENCE"),
    ("biochemical recurrence-free survival", "BRFS"),
    ("metastasis-free survival", "MFS"),
    ("castrate testosterone", "TESTOSTERONE_SUPPRESSION"),
    ("time to castration resistance", "TIME_TO_CRPC"),
    ("prostate cancer-specific mortality", "PROSTATE_CANCER_MORTALITY"),
    ("overall survival", "OS"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_prostate_cancer_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in PROSTATE_CANCER_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"systemic", "localized", "hormonal", "mortality"}


# --- registry wiring ---

def test_prostate_cancer_registered():
    assert "prostate_cancer" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["prostate_cancer"]
    assert e["detection_function"] is detect_prostate_cancer_subspecialty
    assert e["normalizer"] is normalize_prostate_cancer_endpoint
    assert set(e["subspecialties"]) == {"systemic", "localized", "hormonal", "mortality"}


def test_detect_specialty_routes_to_prostate_systemic():
    spec, sub, _ = detect_specialty(
        "Randomized trial of abiraterone acetate plus prednisone versus placebo in "
        "metastatic castration-resistant prostate cancer (mCRPC); radiographic "
        "progression-free survival, overall survival and PSA response with "
        "prostate-specific antigen decline")
    assert spec == "prostate_cancer" and sub == "systemic"


def test_detect_specialty_routes_to_prostate_localized():
    spec, sub, _ = detect_specialty(
        "Randomized trial of dose-escalated external-beam radiotherapy in localized "
        "prostate cancer with Gleason score 7; biochemical recurrence-free survival "
        "and biochemical failure after radical prostatectomy")
    assert spec == "prostate_cancer" and sub == "localized"


def test_prostate_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"
    assert detect_specialty(
        "single-dose HPV vaccine (Cervarix, bivalent) versus control; vaccine "
        "efficacy against persistent HPV-16/18 infection and CIN2+")[0] == "cervical_cancer"


# --- arm-level extraction ---

def test_psa_response_2x2():
    t = ("A confirmed PSA response occurred in 180/300 (60.0%) in the enzalutamide "
         "group and 60/300 (20.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "PSA_RESPONSE"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"enzalutamide", "placebo"}


def test_biochemical_recurrence_2x2():
    t = ("Biochemical recurrence occurred in 45/400 (11.3%) in the radiotherapy group "
         "versus 80/400 (20.0%) in the brachytherapy group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "BIOCHEMICAL_RECURRENCE"


def test_psa_level_is_lognormal():
    r = extract_continuous("mean serum PSA level 12.4 ± 3.1 ng/ml in the abiraterone arm")
    assert r and r[0]["endpoint"] == "PSA_LEVEL" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
