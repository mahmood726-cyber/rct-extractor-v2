"""
Tests for the low-back-pain specialty profile, registry wiring, and arm-level
extraction. Mirrors the tuberculosis / ARDS tests.
"""
import pytest

from rct_extractor._engine.specialties.low_back_pain import (
    LOW_BACK_PAIN_ENDPOINTS, detect_low_back_pain_subspecialty,
    normalize_low_back_pain_endpoint, get_low_back_pain_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.low_back_pain_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Duloxetine versus placebo for chronic low back pain; pain intensity and "
     "responder rate with NSAID comparison.", "pharmacological"),
    ("Epidural steroid injection versus sham for sciatica from lumbar disc "
     "herniation; leg pain and reoperation with microdiscectomy.", "interventional"),
    ("Motor control exercise versus general physiotherapy for chronic low back "
     "pain; Roland-Morris disability and recurrence with spinal manipulation.",
     "physical"),
    ("Cognitive functional therapy versus usual care for disabling low back pain; "
     "return to work and fear-avoidance beliefs with a biopsychosocial approach.",
     "psychological"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_low_back_pain_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("pain intensity", "PAIN_INTENSITY"),
    ("oswestry disability index", "DISABILITY"),
    ("global perceived effect", "GLOBAL_IMPROVEMENT"),
    ("responder rate", "RESPONDER"),
    ("return to work", "RETURN_TO_WORK"),
    ("recurrent low back pain", "RECURRENCE"),
    ("revision surgery", "REOPERATION"),
    ("quality of life", "QOL"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_low_back_pain_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in LOW_BACK_PAIN_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"pharmacological", "interventional",
                                        "physical", "psychological"}


# --- registry wiring ---

def test_low_back_pain_registered():
    assert "low_back_pain" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["low_back_pain"]
    assert e["detection_function"] is detect_low_back_pain_subspecialty
    assert e["normalizer"] is normalize_low_back_pain_endpoint
    assert set(e["subspecialties"]) == {"pharmacological", "interventional",
                                        "physical", "psychological"}


def test_detect_specialty_routes_to_low_back_pain():
    spec, sub, _ = detect_specialty(
        "Exercise therapy versus usual care for chronic low back pain; "
        "Oswestry disability index and pain intensity over 12 months")
    assert spec == "low_back_pain"


def test_low_back_pain_does_not_break_malaria_hiv_or_cardio():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in chronic heart failure; cardiovascular death and "
        "heart-failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_recovery_2x2():
    t = ("Recovery at 12 weeks: exercise 96/160 (60.0%) versus usual-care 56/158 (35.4%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs
    t0 = tabs[0]
    assert t0["endpoint"] == "RECOVERY"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"exercise", "usual-care"}


def test_reoperation_2x2():
    t = ("Reoperation: epidural steroid 6/120 (5.0%) versus sham 9/118 (7.6%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "REOPERATION"


def test_disability_continuous():
    t = ("The Oswestry disability index was 22.4 (SD 12.1) with exercise and 31.8 "
         "(SD 14.3) with usual care")
    cont = extract_continuous(t)
    assert any(c["endpoint"] == "DISABILITY" for c in cont)
