"""
Tests for the pulmonary-hypertension specialty profile, registry wiring, and
arm-level extraction.
"""
import pytest

from rct_extractor._engine.specialties.pulmonary_hypertension import (
    PULMONARY_HYPERTENSION_ENDPOINTS, detect_pulmonary_hypertension_subspecialty,
    normalize_pulmonary_hypertension_endpoint, get_pulmonary_hypertension_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.pulmonary_hypertension_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("macitentan in pulmonary arterial hypertension; change in 6-minute walk "
     "distance and WHO functional class improvement at week 16.", "functional"),
    ("riociguat; pulmonary vascular resistance, mean pulmonary arterial pressure "
     "and cardiac index by right heart catheterisation.", "hemodynamics"),
    ("selexipag; time to clinical worsening, hospitalisation for pulmonary "
     "hypertension and all-cause mortality.", "clinical_worsening"),
    ("sotatercept; change in NT-proBNP and brain natriuretic peptide levels.", "biomarker"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_pulmonary_hypertension_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("6-minute walk distance", "SIX_MWD"),
    ("who functional class", "WHO_FC"),
    ("pulmonary vascular resistance", "PVR"),
    ("mean pulmonary arterial pressure", "MPAP"),
    ("cardiac index", "CARDIAC_INDEX"),
    ("time to clinical worsening", "CLINICAL_WORSENING"),
    ("nt-probnp", "NT_PROBNP"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_pulmonary_hypertension_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"functional", "hemodynamics", "clinical_worsening", "biomarker"}
    for name, info in PULMONARY_HYPERTENSION_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_pulmonary_hypertension_registered():
    assert "pulmonary_hypertension" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["pulmonary_hypertension"]
    assert e["detection_function"] is detect_pulmonary_hypertension_subspecialty
    assert e["normalizer"] is normalize_pulmonary_hypertension_endpoint
    assert set(e["subspecialties"]) == {"functional", "hemodynamics",
                                        "clinical_worsening", "biomarker"}


def test_detect_specialty_routes_to_ph():
    spec, sub, _ = detect_specialty(
        "macitentan versus placebo in pulmonary arterial hypertension; change in "
        "6-minute walk distance and pulmonary vascular resistance at week 16")
    assert spec == "pulmonary_hypertension"


def test_ph_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"
    assert detect_specialty(
        "empagliflozin versus placebo in type 2 diabetes; HbA1c reduction and "
        "fasting plasma glucose at 24 weeks")[0] == "diabetes"


# --- arm-level extraction ---

def test_six_mwd_continuous_poolable():
    r = extract_continuous("the 6-minute walk distance increased by 33.0 ± 28.0 meters "
                           "in the macitentan arm")
    assert r and r[0]["endpoint"] == "SIX_MWD" and r[0]["poolable"] is True


def test_pvr_continuous_poolable():
    r = extract_continuous("pulmonary vascular resistance decreased by 250.0 ± 120.0 "
                           "in the riociguat group")
    assert r and r[0]["endpoint"] == "PVR" and r[0]["poolable"] is True


def test_clinical_worsening_2x2():
    t = ("Clinical worsening occurred in 76/242 (31.4%) of macitentan recipients "
         "and 116/250 (46.4%) of placebo recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "CLINICAL_WORSENING"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"macitentan", "placebo"}
