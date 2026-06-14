"""
Tests for the rehabilitation / physiotherapy specialty profile, registry wiring,
and arm-level extraction.
"""
import pytest

from rct_extractor._engine.specialties.rehabilitation_physiotherapy import (
    REHABILITATION_PHYSIOTHERAPY_ENDPOINTS,
    detect_rehabilitation_physiotherapy_subspecialty,
    normalize_rehabilitation_physiotherapy_endpoint,
    get_rehabilitation_physiotherapy_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.rehabilitation_physiotherapy_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("constraint-induced movement therapy after stroke rehabilitation; Fugl-Meyer "
     "assessment, functional independence measure and gait speed.", "neuro"),
    ("exercise-based cardiac rehabilitation; all-cause mortality, hospital readmission "
     "and peak VO2.", "cardiac"),
    ("pulmonary rehabilitation in COPD; 6-minute walk distance, dyspnoea and chronic "
     "respiratory questionnaire.", "pulmonary"),
    ("physiotherapy with exercise therapy; pain intensity, physical function and return "
     "to work.", "musculoskeletal"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_rehabilitation_physiotherapy_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("Fugl-Meyer assessment", "MOTOR_FUNCTION"),
    ("functional independence measure", "FUNCTIONAL_INDEPENDENCE"),
    ("peak VO2", "EXERCISE_CAPACITY"),
    ("6-minute walk distance", "SIX_MWD"),
    ("hospital readmission", "HOSPITAL_READMISSION"),
    ("return to work", "RETURN_TO_WORK"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_rehabilitation_physiotherapy_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"neuro", "cardiac", "pulmonary", "musculoskeletal"}
    for name, info in REHABILITATION_PHYSIOTHERAPY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_rehabilitation_physiotherapy_registered():
    assert "rehabilitation_physiotherapy" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["rehabilitation_physiotherapy"]
    assert e["detection_function"] is detect_rehabilitation_physiotherapy_subspecialty
    assert e["normalizer"] is normalize_rehabilitation_physiotherapy_endpoint
    assert set(e["subspecialties"]) == {"neuro", "cardiac", "pulmonary", "musculoskeletal"}


def test_detect_specialty_routes_to_rehabilitation():
    spec, sub, _ = detect_specialty(
        "exercise-based cardiac rehabilitation versus usual care; all-cause mortality, "
        "hospital readmission and peak VO2 exercise capacity")
    assert spec == "rehabilitation_physiotherapy" and sub == "cardiac"


def test_rehabilitation_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_readmission_2x2():
    t = ("Hospital readmission occurred in 40/250 (16.0%) of cardiac rehabilitation "
         "patients and 65/250 (26.0%) of usual care patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "HOSPITAL_READMISSION"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"cardiac-rehabilitation", "usual-care"}


def test_return_to_work_2x2():
    t = ("Return to work was achieved in 140/200 (70.0%) of physiotherapy patients and "
         "110/200 (55.0%) of usual care patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "RETURN_TO_WORK"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"physiotherapy", "usual-care"}


def test_six_mwd_continuous_poolable():
    r = extract_continuous("the 6-minute walk distance was 420.5 ± 75.3 metres in the "
                           "pulmonary rehabilitation arm")
    assert r and r[0]["endpoint"] == "SIX_MWD" and r[0]["poolable"] is True
