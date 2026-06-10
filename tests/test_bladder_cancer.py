"""Tests for the bladder-cancer specialty profile, registry wiring, arm-level."""
import pytest

from rct_extractor._engine.specialties.bladder_cancer import (
    BLADDER_CANCER_ENDPOINTS, detect_bladder_cancer_subspecialty,
    normalize_bladder_cancer_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.bladder_cancer_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("RCT of intravesical BCG maintenance versus mitomycin C in high-grade "
     "non-muscle-invasive bladder cancer (NMIBC); recurrence-free survival and "
     "progression to muscle-invasive disease.", "nmibc"),
    ("Trial of neoadjuvant gemcitabine plus cisplatin before radical cystectomy in "
     "muscle-invasive bladder cancer (MIBC); pathological complete response and "
     "disease-free survival.", "mibc"),
    ("Phase 3 RCT of pembrolizumab plus enfortumab vedotin versus platinum in "
     "metastatic urothelial carcinoma; overall survival, progression-free survival "
     "and objective response.", "advanced"),
    ("Registry follow-up reporting bladder cancer-specific mortality and all-cause "
     "mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_bladder_cancer_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("recurrence-free survival", "RFS"),
    ("progression to muscle-invasive", "PROGRESSION_TO_MIBC"),
    ("pathological complete response", "PCR"),
    ("disease-free survival", "DFS"),
    ("bladder cancer-specific mortality", "BLADDER_CANCER_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_bladder_cancer_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in BLADDER_CANCER_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"nmibc", "mibc", "advanced", "mortality"}


def test_bladder_cancer_registered():
    assert "bladder_cancer" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["bladder_cancer"]
    assert e["detection_function"] is detect_bladder_cancer_subspecialty
    assert set(e["subspecialties"]) == {"nmibc", "mibc", "advanced", "mortality"}


def test_detect_specialty_routes_to_bladder():
    spec, sub, _ = detect_specialty(
        "Randomized trial of neoadjuvant gemcitabine plus cisplatin before radical "
        "cystectomy in muscle-invasive bladder cancer; pathological complete response "
        "and disease-free survival")
    assert spec == "bladder_cancer" and sub == "mibc"


def test_bladder_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "abiraterone in metastatic castration-resistant prostate cancer; PSA response"
    )[0] != "bladder_cancer"


def test_recurrence_2x2():
    t = ("Recurrence-free survival events occurred in 50/200 (25.0%) in the BCG "
         "group versus 80/200 (40.0%) in the mitomycin group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "RFS"
