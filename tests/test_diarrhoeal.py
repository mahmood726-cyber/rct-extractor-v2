"""
Tests for the diarrhoeal-disease specialty profile, registry wiring, and
arm-level extraction. Mirrors the HIV / malaria / typhoid tests.
"""
import pytest

from rct_extractor._engine.specialties.diarrhoeal import (
    DIARRHOEAL_ENDPOINTS, detect_diarrhoeal_subspecialty, normalize_diarrhoeal_endpoint,
    get_diarrhoeal_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.diarrhoeal_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of reduced-osmolarity ORS plus zinc versus standard ORS for acute watery "
     "diarrhoea; rehydration failure and total stool output.", "rehydration"),
    ("Rotarix (RV1) rotavirus vaccine versus placebo; efficacy against severe "
     "rotavirus gastroenteritis and anti-rotavirus IgA seroconversion.", "rotavirus"),
    ("Azithromycin versus ciprofloxacin for shigella dysentery; clinical cure and "
     "bacteriological clearance with stool culture.", "treatment"),
    ("Zinc supplementation in childhood diarrhoea; duration of diarrhoea, stool "
     "frequency, hospitalisation and case fatality among under-five children.",
     "mortality_duration"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_diarrhoeal_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("clinical cure rate", "CLINICAL_CURE"),
    ("bacteriological clearance", "BACTERIOLOGICAL_CURE"),
    ("duration of diarrhoea", "DIARRHOEA_DURATION"),
    ("duration of diarrhea", "DIARRHOEA_DURATION"),
    ("total stool output", "STOOL_OUTPUT"),
    ("severe rotavirus gastroenteritis", "SEVERE_RV_GE"),
    ("rotavirus gastroenteritis", "ROTAVIRUS_GE"),
    ("anti-rotavirus IgA", "RV_IMMUNOGENICITY"),
    ("rehydration failure", "REHYDRATION_FAILURE"),
    ("severe dehydration", "DEHYDRATION"),
    ("persistent diarrhoea", "PERSISTENT_DIARRHOEA"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_diarrhoeal_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in DIARRHOEAL_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"rehydration", "rotavirus", "treatment",
                                        "mortality_duration"}


def test_british_and_american_spelling_both_match():
    # diarrhoea (UK) and diarrhea (US) must both normalize to the duration endpoint
    assert normalize_diarrhoeal_endpoint("diarrhoeal duration") == "DIARRHOEA_DURATION"
    assert normalize_diarrhoeal_endpoint("diarrheal duration") == "DIARRHOEA_DURATION"


# --- registry wiring ---

def test_diarrhoeal_registered():
    assert "diarrhoeal" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["diarrhoeal"]
    assert e["detection_function"] is detect_diarrhoeal_subspecialty
    assert e["normalizer"] is normalize_diarrhoeal_endpoint
    assert set(e["subspecialties"]) == {"rehydration", "rotavirus", "treatment",
                                        "mortality_duration"}


def test_detect_specialty_routes_to_diarrhoeal_rehydration():
    spec, sub, _ = detect_specialty(
        "reduced-osmolarity oral rehydration solution plus zinc versus standard ORS "
        "for acute watery diarrhoea; rehydration failure and stool output")
    assert spec == "diarrhoeal" and sub == "rehydration"


def test_diarrhoeal_rotavirus_routes():
    spec, sub, _ = detect_specialty(
        "Rotarix (RV1) rotavirus vaccine versus placebo; vaccine efficacy against "
        "severe rotavirus gastroenteritis and anti-rotavirus IgA seroconversion")
    assert spec == "diarrhoeal" and sub == "rotavirus"


def test_diarrhoeal_does_not_break_hiv_malaria_typhoid_or_cardio():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "gatifloxacin versus ceftriaxone for blood-culture-confirmed typhoid fever; "
        "fever clearance time and anti-Vi seroconversion in enteric fever")[0] == "typhoid"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_rehydration_failure_2x2():
    t = ("Rehydration failure occurred in 8/150 (5.3%) in the reduced-osmolarity ORS "
         "group and 22/148 (14.9%) in the standard ORS group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "REHYDRATION_FAILURE"
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (8, 150)


def test_severe_rotavirus_2x2():
    t = ("Severe rotavirus gastroenteritis occurred in 12/2500 (0.5%) in the "
         "rotavirus vaccine group versus 56/2500 (2.2%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "SEVERE_RV_GE"


def test_diarrhoea_duration_continuous_poolable():
    r = extract_continuous("mean duration of diarrhoea 72 ± 18 hours in the zinc arm")
    assert r and r[0]["endpoint"] == "DIARRHOEA_DURATION" and r[0]["poolable"] is True


def test_rotavirus_iga_is_lognormal():
    r = extract_continuous("mean anti-rotavirus IgA 185 ± 42 U/ml in the Rotarix arm")
    assert r and r[0]["endpoint"] == "RV_IMMUNOGENICITY" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
