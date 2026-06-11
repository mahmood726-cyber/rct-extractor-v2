"""Tests for the lymphoma specialty profile, registry wiring, arm-level."""
import pytest

from rct_extractor._engine.specialties.lymphoma import (
    LYMPHOMA_ENDPOINTS, detect_lymphoma_subspecialty, normalize_lymphoma_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.lymphoma_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of brentuximab vedotin plus AVD (BV-AVD) versus ABVD in advanced "
     "classical Hodgkin lymphoma; progression-free survival and complete metabolic "
     "response by interim PET.", "hodgkin"),
    ("Trial of polatuzumab vedotin plus R-CHP versus R-CHOP in diffuse large B-cell "
     "lymphoma (DLBCL); event-free survival, progression-free survival and complete "
     "response.", "aggressive"),
    ("Randomized trial of obinutuzumab plus bendamustine versus rituximab in "
     "follicular lymphoma; progression-free survival, objective response and time to "
     "next treatment.", "indolent"),
    ("Registry follow-up reporting lymphoma-specific mortality and all-cause "
     "mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_lymphoma_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("progression-free survival", "PFS"),
    ("event-free survival", "EFS"),
    ("complete metabolic response", "CR_RATE"),
    ("time to next treatment", "TTNT"),
    ("lymphoma-specific mortality", "LYMPHOMA_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_lymphoma_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in LYMPHOMA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"hodgkin", "aggressive", "indolent", "mortality"}


def test_lymphoma_registered():
    assert "lymphoma" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["lymphoma"]
    assert e["detection_function"] is detect_lymphoma_subspecialty
    assert set(e["subspecialties"]) == {"hodgkin", "aggressive", "indolent", "mortality"}


def test_detect_specialty_routes_to_lymphoma():
    spec, sub, _ = detect_specialty(
        "Randomized trial of polatuzumab vedotin plus R-CHP versus R-CHOP in "
        "diffuse large B-cell lymphoma (DLBCL); event-free survival and complete "
        "response")
    assert spec == "lymphoma" and sub == "aggressive"


def test_lymphoma_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"


def test_complete_response_2x2():
    t = ("A complete metabolic response occurred in 160/250 (64.0%) in the "
         "brentuximab-AVD group versus 120/250 (48.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "CR_RATE"
