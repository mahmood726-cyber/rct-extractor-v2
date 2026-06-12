"""Tests for the influenza specialty profile, registry wiring, arm-level.

Distinct from `pneumonia` (bacterial), `covid19` (SARS-CoV-2), `respiratory`.
"""
import pytest

from rct_extractor._engine.specialties.influenza import (
    INFLUENZA_ENDPOINTS, detect_influenza_subspecialty, normalize_influenza_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.influenza_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of baloxavir marboxil versus oseltamivir versus placebo in "
     "acute uncomplicated influenza; time to alleviation of symptoms.", "treatment"),
    ("Randomized trial of quadrivalent inactivated influenza vaccine versus "
     "placebo; vaccine efficacy against laboratory-confirmed influenza.", "prevention"),
    ("Trial of oseltamivir versus placebo in high-risk adults with influenza; "
     "hospitalisation and lower respiratory tract complications.", "complications"),
    ("Registry follow-up reporting influenza-related mortality and all-cause "
     "mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_influenza_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("laboratory-confirmed influenza", "INFLUENZA_INCIDENCE"),
    ("vaccine efficacy", "VACCINE_EFFICACY"),
    ("time to alleviation of symptoms", "TIME_TO_ALLEVIATION"),
    ("hospitalisation", "HOSPITALIZATION"),
    ("influenza-related mortality", "INFLUENZA_MORTALITY"),
    ("all-cause mortality", "ALL_CAUSE_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_influenza_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in INFLUENZA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"treatment", "prevention", "complications", "mortality"}


def test_influenza_registered():
    assert "influenza" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["influenza"]
    assert e["detection_function"] is detect_influenza_subspecialty
    assert set(e["subspecialties"]) == {"treatment", "prevention", "complications", "mortality"}


def test_detect_specialty_routes_to_influenza():
    spec, sub, _ = detect_specialty(
        "Randomized trial of baloxavir marboxil versus placebo for acute "
        "influenza; time to alleviation of symptoms and laboratory-confirmed "
        "influenza.")
    assert spec == "influenza" and sub in {"treatment", "prevention"}


def test_influenza_distinct_from_covid_and_pneumonia():
    assert detect_specialty(
        "Nirmatrelvir-ritonavir versus placebo in COVID-19; hospitalisation or "
        "death through day 28 in SARS-CoV-2 infection.")[0] == "covid19"


def test_influenza_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"


def test_influenza_incidence_2x2():
    t = ("Laboratory-confirmed influenza occurred in 11/200 (5.5%) in the "
         "inactivated influenza vaccine group versus 40/200 (20.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "INFLUENZA_INCIDENCE"
