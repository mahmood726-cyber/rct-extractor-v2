"""
Tests for the chronic-pain specialty profile, registry wiring, and arm-level
extraction. Mirrors the tuberculosis / ARDS tests.
"""
import pytest

from rct_extractor._engine.specialties.chronic_pain import (
    CHRONIC_PAIN_ENDPOINTS, detect_chronic_pain_subspecialty,
    normalize_chronic_pain_endpoint, get_chronic_pain_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.chronic_pain_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Pregabalin vs placebo for fibromyalgia; mean pain intensity score on an "
     "11-point NRS and 50% pain reduction responder rate with duloxetine "
     "comparison.", "pharmacological"),
    ("Spinal cord stimulation vs sham for refractory chronic pain; pain intensity "
     "(VAS) and >=50% pain reduction; radiofrequency ablation comparison.",
     "interventional"),
    ("Gabapentin for painful diabetic peripheral neuropathy and postherpetic "
     "neuralgia; average daily pain score and allodynia.", "neuropathic"),
    ("Cognitive behavioural therapy (CBT) vs usual care for chronic pain; physical "
     "function (Oswestry disability index) and quality of life with exercise "
     "therapy.", "behavioural"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_chronic_pain_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("mean pain score", "PAIN_INTENSITY"),
    ("50% pain reduction", "RESPONDER_50"),
    ("30% pain reduction", "RESPONDER_30"),
    ("oswestry disability index", "FUNCTION"),
    ("quality of life", "QOL"),
    ("withdrawal due to adverse events", "WITHDRAWAL_AE"),
    ("sleep quality", "SLEEP"),
    ("opioid consumption", "OPIOID_USE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_chronic_pain_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in CHRONIC_PAIN_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"pharmacological", "interventional",
                                        "neuropathic", "behavioural"}


# --- registry wiring ---

def test_chronic_pain_registered():
    assert "chronic_pain" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["chronic_pain"]
    assert e["detection_function"] is detect_chronic_pain_subspecialty
    assert e["normalizer"] is normalize_chronic_pain_endpoint
    assert set(e["subspecialties"]) == {"pharmacological", "interventional",
                                        "neuropathic", "behavioural"}


def test_detect_specialty_routes_to_chronic_pain():
    spec, sub, _ = detect_specialty(
        "Pregabalin versus placebo for neuropathic pain; weekly mean pain "
        "intensity on an 11-point NRS and 50% pain reduction responder rate")
    assert spec == "chronic_pain"


def test_chronic_pain_does_not_break_malaria_hiv_or_cardio():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in chronic heart failure; cardiovascular death and "
        "heart-failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_responder_2x2():
    t = ("At least 50% pain reduction: pregabalin 90/200 (45.0%) "
         "versus placebo 50/198 (25.3%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs
    t0 = tabs[0]
    assert t0["endpoint"] == "RESPONDER_50"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"pregabalin", "placebo"}


def test_withdrawal_2x2():
    t = ("Withdrawal due to adverse events: duloxetine 40/200 (20.0%) "
         "vs placebo 16/198 (8.1%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "WITHDRAWAL_AE"


def test_pain_intensity_continuous():
    t = ("Mean pain intensity score was 3.8 (SD 1.9) with gabapentin and 5.2 "
         "(SD 2.1) with placebo")
    cont = extract_continuous(t)
    assert any(c["endpoint"] == "PAIN_INTENSITY" for c in cont)
