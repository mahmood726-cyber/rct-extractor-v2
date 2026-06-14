"""
Tests for the geriatrics / frailty specialty profile, registry wiring, and
arm-level extraction.
"""
import pytest

from rct_extractor._engine.specialties.geriatrics_frailty import (
    GERIATRICS_FRAILTY_ENDPOINTS, detect_geriatrics_frailty_subspecialty,
    normalize_geriatrics_frailty_endpoint, get_geriatrics_frailty_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.geriatrics_frailty_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("a multifactorial falls-prevention programme in community-dwelling older adults; "
     "rate of falls, fallers and fall-related injury.", "falls"),
    ("comprehensive geriatric assessment to prevent postoperative delirium; incident "
     "delirium and cognitive function (MMSE).", "cognition"),
    ("an exercise programme in frail older adults; short physical performance battery, "
     "gait speed and activities of daily living.", "function"),
    ("comprehensive geriatric assessment in frail elderly; all-cause mortality, "
     "hospitalisation and nursing-home admission.", "outcomes"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_geriatrics_frailty_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("rate of falls", "FALLS"),
    ("proportion of fallers", "FALLERS"),
    ("fall-related injury", "FALL_INJURY"),
    ("postoperative delirium", "DELIRIUM"),
    ("short physical performance battery", "PHYSICAL_FUNCTION"),
    ("nursing-home admission", "INSTITUTIONALISATION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_geriatrics_frailty_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"falls", "cognition", "function", "outcomes"}
    for name, info in GERIATRICS_FRAILTY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_geriatrics_frailty_registered():
    assert "geriatrics_frailty" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["geriatrics_frailty"]
    assert e["detection_function"] is detect_geriatrics_frailty_subspecialty
    assert e["normalizer"] is normalize_geriatrics_frailty_endpoint
    assert set(e["subspecialties"]) == {"falls", "cognition", "function", "outcomes"}


def test_detect_specialty_routes_to_geriatrics_frailty():
    spec, sub, _ = detect_specialty(
        "a multifactorial falls-prevention intervention in community-dwelling older adults "
        "with frailty; rate of falls, fallers and fall-related injury")
    assert spec == "geriatrics_frailty" and sub == "falls"


def test_geriatrics_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_fallers_2x2():
    t = ("At least one fall occurred in 60/300 (20.0%) of exercise patients and "
         "90/300 (30.0%) of usual care patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "FALLERS"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"exercise", "usual-care"}


def test_delirium_2x2():
    t = ("Postoperative delirium occurred in 18/150 (12.0%) of comprehensive geriatric "
         "assessment patients and 33/150 (22.0%) of usual care patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "DELIRIUM"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"comprehensive-geriatric-assessment", "usual-care"}


def test_sppb_continuous_poolable():
    r = extract_continuous("the short physical performance battery was 9.2 ± 2.1 in the "
                           "exercise arm")
    assert r and r[0]["endpoint"] == "PHYSICAL_FUNCTION" and r[0]["poolable"] is True
