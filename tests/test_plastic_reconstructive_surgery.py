"""
Tests for the plastic / reconstructive surgery specialty profile, registry
wiring, and arm-level extraction. Includes a check that plastic-surgery routes
away from the wound_healing specialty (chronic ulcers).
"""
import pytest

from rct_extractor._engine.specialties.plastic_reconstructive_surgery import (
    PLASTIC_RECONSTRUCTIVE_SURGERY_ENDPOINTS,
    detect_plastic_reconstructive_surgery_subspecialty,
    normalize_plastic_reconstructive_surgery_endpoint,
    get_plastic_reconstructive_surgery_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.plastic_reconstructive_surgery_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("free flap versus pedicled flap in reconstructive surgery; total flap failure, "
     "partial flap necrosis and fat necrosis.", "flap"),
    ("implant-based versus autologous breast reconstruction; implant loss, capsular "
     "contracture and BREAST-Q satisfaction.", "breast"),
    ("negative-pressure wound therapy after surgery; surgical-site infection, wound "
     "dehiscence, haematoma and seroma.", "complications"),
    ("silicone gel for scar management; hypertrophic scar, Vancouver Scar Scale and "
     "patient satisfaction.", "scar"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_plastic_reconstructive_surgery_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("total flap failure", "FLAP_FAILURE"),
    ("partial flap necrosis", "PARTIAL_FLAP_NECROSIS"),
    ("capsular contracture", "CAPSULAR_CONTRACTURE"),
    ("surgical-site infection", "SSI"),
    ("wound dehiscence", "DEHISCENCE"),
    ("hypertrophic scar", "HYPERTROPHIC_SCAR"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_plastic_reconstructive_surgery_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"flap", "breast", "complications", "scar"}
    for name, info in PLASTIC_RECONSTRUCTIVE_SURGERY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_plastic_reconstructive_surgery_registered():
    assert "plastic_reconstructive_surgery" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["plastic_reconstructive_surgery"]
    assert e["detection_function"] is detect_plastic_reconstructive_surgery_subspecialty
    assert e["normalizer"] is normalize_plastic_reconstructive_surgery_endpoint
    assert set(e["subspecialties"]) == {"flap", "breast", "complications", "scar"}


def test_detect_specialty_routes_to_plastic():
    spec, sub, _ = detect_specialty(
        "free flap versus pedicled flap in reconstructive surgery; total flap failure, "
        "partial flap necrosis and surgical-site infection")
    assert spec == "plastic_reconstructive_surgery"


def test_plastic_vs_wound_healing_disambiguation():
    # breast reconstruction -> plastic_reconstructive_surgery
    assert detect_specialty(
        "implant-based breast reconstruction with acellular dermal matrix; implant loss "
        "and capsular contracture after mastectomy")[0] == "plastic_reconstructive_surgery"
    # chronic diabetic-foot ulcer -> stays wound_healing
    if "wound_healing" in SPECIALTY_REGISTRY:
        assert detect_specialty(
            "an advanced dressing for diabetic foot ulcers; complete wound healing and "
            "time to healing of chronic foot ulcers")[0] == "wound_healing"


def test_plastic_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_flap_failure_2x2():
    t = ("Total flap failure occurred in 6/150 (4.0%) of free flap patients and "
         "18/150 (12.0%) of pedicled flap patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "FLAP_FAILURE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"free-flap", "pedicled-flap"}


def test_ssi_2x2():
    t = ("Surgical-site infection occurred in 10/200 (5.0%) of npwt patients and "
         "24/200 (12.0%) of standard care patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "SSI"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"npwt", "standard-of-care"}


def test_breast_q_continuous_poolable():
    r = extract_continuous("the BREAST-Q satisfaction with breasts score was 68.4 ± 15.2 "
                           "in the autologous arm")
    assert r and r[0]["endpoint"] == "BREAST_Q" and r[0]["poolable"] is True
