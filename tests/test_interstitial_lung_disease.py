"""
Tests for the interstitial-lung-disease / pulmonary-fibrosis specialty profile,
registry wiring, and arm-level extraction. Includes a check that ILD routes away
from the general respiratory specialty (asthma/COPD).
"""
import pytest

from rct_extractor._engine.specialties.interstitial_lung_disease import (
    INTERSTITIAL_LUNG_DISEASE_ENDPOINTS, detect_interstitial_lung_disease_subspecialty,
    normalize_interstitial_lung_disease_endpoint,
    get_interstitial_lung_disease_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.interstitial_lung_disease_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("nintedanib in idiopathic pulmonary fibrosis; annual rate of decline in FVC and "
     "diffusing capacity (DLCO).", "function"),
    ("pirfenidone in IPF; disease progression and progression-free survival.", "progression"),
    ("antifibrotic therapy in progressive fibrosing ILD; all-cause mortality and "
     "transplant-free survival.", "mortality"),
    ("nintedanib in IPF; acute exacerbation of idiopathic pulmonary fibrosis and "
     "respiratory hospitalisation.", "acute_events"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_interstitial_lung_disease_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("forced vital capacity", "FVC"),
    ("percent predicted FVC", "PPFVC"),
    ("diffusing capacity", "DLCO"),
    ("progression-free survival", "PROGRESSION_FREE_SURVIVAL"),
    ("acute exacerbation of IPF", "ACUTE_EXACERBATION"),
    ("transplant-free survival", "TRANSPLANT_FREE_SURVIVAL"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_interstitial_lung_disease_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"function", "progression", "mortality", "acute_events"}
    for name, info in INTERSTITIAL_LUNG_DISEASE_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_interstitial_lung_disease_registered():
    assert "interstitial_lung_disease" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["interstitial_lung_disease"]
    assert e["detection_function"] is detect_interstitial_lung_disease_subspecialty
    assert e["normalizer"] is normalize_interstitial_lung_disease_endpoint
    assert set(e["subspecialties"]) == {"function", "progression", "mortality", "acute_events"}


def test_detect_specialty_routes_to_ild():
    spec, sub, _ = detect_specialty(
        "nintedanib versus placebo in idiopathic pulmonary fibrosis; annual rate of "
        "decline in forced vital capacity, acute exacerbation and all-cause mortality")
    assert spec == "interstitial_lung_disease"


def test_ild_vs_respiratory_disambiguation():
    # IPF / antifibrotic -> interstitial_lung_disease, not respiratory
    assert detect_specialty(
        "pirfenidone in idiopathic pulmonary fibrosis; FVC decline and disease "
        "progression with usual interstitial pneumonia")[0] == "interstitial_lung_disease"
    # general asthma -> stays respiratory
    if "respiratory" in SPECIALTY_REGISTRY:
        assert detect_specialty(
            "budesonide/formoterol versus placebo in moderate asthma; ACQ-5 score, "
            "FEV1 and severe asthma exacerbations")[0] == "respiratory"


def test_ild_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_acute_exacerbation_2x2():
    t = ("Acute exacerbation occurred in 15/300 (5.0%) of nintedanib patients and "
         "30/300 (10.0%) of placebo patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "ACUTE_EXACERBATION"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"nintedanib", "placebo"}


def test_mortality_2x2():
    t = ("All-cause mortality occurred in 20/250 (8.0%) of pirfenidone patients and "
         "35/250 (14.0%) of placebo patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "MORTALITY"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"pirfenidone", "placebo"}


def test_fvc_continuous_poolable():
    r = extract_continuous("the forced vital capacity was 2750.0 ± 620.0 mL in the "
                           "nintedanib arm")
    assert r and r[0]["endpoint"] == "FVC" and r[0]["poolable"] is True
