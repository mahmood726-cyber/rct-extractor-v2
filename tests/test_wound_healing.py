"""
Tests for the burns / wound-healing specialty profile, registry wiring, and
arm-level extraction. Mirrors the tuberculosis / ARDS tests.
"""
import pytest

from rct_extractor._engine.specialties.wound_healing import (
    WOUND_HEALING_ENDPOINTS, detect_wound_healing_subspecialty,
    normalize_wound_healing_endpoint, get_wound_healing_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.wound_healing_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Early excision and split-thickness skin graft versus enzymatic debridement "
     "(bromelain) for deep partial-thickness burns; time to re-epithelialization "
     "and graft take.", "burns"),
    ("Negative-pressure wound therapy versus standard dressing for diabetic foot "
     "ulcer; complete wound healing and amputation in chronic wounds.", "chronic_wounds"),
    ("Closed-incision negative-pressure wound therapy versus standard dressing after "
     "laparotomy; surgical-site infection and wound dehiscence.", "surgical_wounds"),
    ("Hyperbaric oxygen therapy versus sham for non-healing wounds; complete "
     "healing and wound area reduction with platelet-rich plasma.", "adjuncts"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_wound_healing_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("complete wound closure", "COMPLETE_HEALING"),
    ("time to complete healing", "TIME_TO_HEALING"),
    ("wound area reduction", "WOUND_AREA_REDUCTION"),
    ("major amputation", "AMPUTATION"),
    ("surgical site infection", "INFECTION"),
    ("wound dehiscence", "DEHISCENCE"),
    ("graft take", "GRAFT_TAKE"),
    ("vancouver scar scale", "SCAR_SCORE"),
    ("ulcer recurrence", "RECURRENCE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_wound_healing_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in WOUND_HEALING_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"burns", "chronic_wounds",
                                        "surgical_wounds", "adjuncts"}


# --- registry wiring ---

def test_wound_healing_registered():
    assert "wound_healing" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["wound_healing"]
    assert e["detection_function"] is detect_wound_healing_subspecialty
    assert e["normalizer"] is normalize_wound_healing_endpoint
    assert set(e["subspecialties"]) == {"burns", "chronic_wounds",
                                        "surgical_wounds", "adjuncts"}


def test_detect_specialty_routes_to_wound_healing():
    spec, sub, _ = detect_specialty(
        "Negative-pressure wound therapy versus standard care for diabetic foot "
        "ulcer; complete wound healing and time to wound closure")
    assert spec == "wound_healing"


def test_wound_healing_does_not_break_malaria_hiv_or_cardio():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in chronic heart failure; cardiovascular death and "
        "heart-failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_complete_healing_2x2():
    t = ("Complete wound healing: NPWT 96/150 (64.0%) versus standard-care 60/148 (40.5%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs
    t0 = tabs[0]
    assert t0["endpoint"] == "COMPLETE_HEALING"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"NPWT", "standard-care"}


def test_amputation_2x2():
    t = ("Major amputation: hyperbaric oxygen 8/100 (8.0%) versus sham 20/98 (20.4%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "AMPUTATION"


def test_time_to_healing_continuous():
    t = ("Healing time was 42.3 (SD 18.1) days with NPWT and 61.7 "
         "(SD 22.4) days with standard care")
    cont = extract_continuous(t)
    assert any(c["endpoint"] == "TIME_TO_HEALING" for c in cont)
