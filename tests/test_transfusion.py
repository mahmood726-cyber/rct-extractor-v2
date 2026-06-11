"""
Tests for the blood-transfusion-strategy specialty profile, registry wiring,
and arm-level extraction. Mirrors the tuberculosis / ARDS tests.
"""
import pytest

from rct_extractor._engine.specialties.transfusion import (
    TRANSFUSION_ENDPOINTS, detect_transfusion_subspecialty,
    normalize_transfusion_endpoint, get_transfusion_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.transfusion_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Restrictive versus liberal red blood cell transfusion threshold in cardiac "
     "surgery; 30-day mortality, ischaemic events and units transfused.", "threshold"),
    ("Prophylactic platelet transfusion versus therapeutic platelet transfusion in "
     "haematology patients; WHO bleeding and transfusion reaction.", "platelet_plasma"),
    ("1:1:1 versus 1:1:2 fixed-ratio massive transfusion in trauma; 24-hour "
     "mortality and rebleeding with tranexamic acid.", "massive"),
    ("Fresh versus standard-age stored red cells in critically ill patients; "
     "nosocomial infection and organ dysfunction.", "processing"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_transfusion_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("30-day mortality", "MORTALITY"),
    ("proportion transfused", "TRANSFUSION_EXPOSURE"),
    ("units transfused", "UNITS_TRANSFUSED"),
    ("ischaemic events", "ISCHAEMIC_EVENTS"),
    ("major adverse cardiac events", "MACE"),
    ("nosocomial infection", "INFECTION"),
    ("recurrent bleeding", "REBLEEDING"),
    ("transfusion-related acute lung injury", "TRANSFUSION_REACTION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_transfusion_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in TRANSFUSION_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"threshold", "platelet_plasma", "massive", "processing"}


# --- registry wiring ---

def test_transfusion_registered():
    assert "transfusion" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["transfusion"]
    assert e["detection_function"] is detect_transfusion_subspecialty
    assert e["normalizer"] is normalize_transfusion_endpoint
    assert set(e["subspecialties"]) == {"threshold", "platelet_plasma", "massive", "processing"}


def test_detect_specialty_routes_to_transfusion():
    spec, sub, _ = detect_specialty(
        "Restrictive versus liberal red blood cell transfusion threshold in "
        "patients with gastrointestinal bleeding; 30-day mortality and rebleeding")
    assert spec == "transfusion"


def test_transfusion_does_not_break_malaria_hiv_or_cardio():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in chronic heart failure; cardiovascular death and "
        "heart-failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_mortality_2x2():
    t = ("30-day mortality: restrictive 74/1000 (7.4%) versus liberal 70/1000 (7.0%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs
    t0 = tabs[0]
    assert t0["endpoint"] == "MORTALITY"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"restrictive", "liberal"}


def test_infection_2x2():
    t = ("Nosocomial infection occurred in 50/500 (10.0%) in the restrictive group "
         "versus 90/500 (18.0%) in the liberal group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "INFECTION"


def test_length_of_stay_continuous():
    t = ("Hospital length of stay was 8.2 (SD 3.1) days with restrictive versus "
         "9.4 (SD 3.6) days with liberal")
    cont = extract_continuous(t)
    assert any(c["endpoint"] == "LENGTH_OF_STAY" for c in cont)
