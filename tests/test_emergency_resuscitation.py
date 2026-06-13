"""
Tests for the emergency-medicine / resuscitation specialty profile, registry
wiring, and arm-level extraction. Includes a check that cardiac-arrest trials
route to emergency_resuscitation rather than sepsis/cardiology.
"""
import pytest

from rct_extractor._engine.specialties.emergency_resuscitation import (
    EMERGENCY_RESUSCITATION_ENDPOINTS, detect_emergency_resuscitation_subspecialty,
    normalize_emergency_resuscitation_endpoint, get_emergency_resuscitation_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.emergency_resuscitation_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("adrenaline versus placebo in out-of-hospital cardiac arrest; return of spontaneous "
     "circulation, survival to discharge and favourable neurological outcome.", "cardiac_arrest"),
    ("tranexamic acid in major trauma; 28-day mortality, massive transfusion and death "
     "due to bleeding.", "trauma"),
    ("video laryngoscopy versus direct laryngoscopy for emergency tracheal intubation; "
     "first-pass success and overall intubation success.", "airway"),
    ("an emergency department pathway; early mortality, unplanned hospital admission and "
     "short-term mortality in acute undifferentiated presentations.", "acute_care"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_emergency_resuscitation_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("return of spontaneous circulation", "ROSC"),
    ("survival to hospital discharge", "SURVIVAL_TO_DISCHARGE"),
    ("favourable neurological outcome", "FAVOURABLE_NEURO_OUTCOME"),
    ("first-pass success", "FIRST_PASS_SUCCESS"),
    ("massive transfusion", "MASSIVE_TRANSFUSION"),
    ("28-day mortality", "TRAUMA_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_emergency_resuscitation_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"cardiac_arrest", "trauma", "airway", "acute_care"}
    for name, info in EMERGENCY_RESUSCITATION_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_emergency_resuscitation_registered():
    assert "emergency_resuscitation" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["emergency_resuscitation"]
    assert e["detection_function"] is detect_emergency_resuscitation_subspecialty
    assert e["normalizer"] is normalize_emergency_resuscitation_endpoint
    assert set(e["subspecialties"]) == {"cardiac_arrest", "trauma", "airway", "acute_care"}


def test_detect_specialty_routes_to_emergency_resuscitation():
    spec, sub, _ = detect_specialty(
        "adrenaline versus placebo in out-of-hospital cardiac arrest; return of "
        "spontaneous circulation, survival to hospital discharge and favourable "
        "neurological outcome (CPC 1-2)")
    assert spec == "emergency_resuscitation" and sub == "cardiac_arrest"


def test_emergency_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_rosc_2x2():
    t = ("Return of spontaneous circulation occurred in 72/200 (36.0%) of adrenaline "
         "patients and 40/200 (20.0%) of placebo patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "ROSC"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"adrenaline", "placebo"}


def test_first_pass_success_2x2():
    t = ("First-pass success was achieved in 160/200 (80.0%) of video laryngoscopy "
         "patients and 130/200 (65.0%) of direct laryngoscopy patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "FIRST_PASS_SUCCESS"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"video-laryngoscopy", "direct-laryngoscopy"}


def test_trauma_mortality_2x2():
    t = ("28-day mortality occurred in 90/600 (15.0%) of tranexamic acid patients and "
         "120/600 (20.0%) of placebo patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "TRAUMA_MORTALITY"
