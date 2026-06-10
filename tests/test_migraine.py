"""
Tests for the migraine specialty profile, registry wiring, and arm-level
extraction. Mirrors the tuberculosis / parkinsons tests.
"""
import pytest

from rct_extractor._engine.specialties.migraine import (
    MIGRAINE_ENDPOINTS, detect_migraine_subspecialty,
    normalize_migraine_endpoint, get_migraine_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.migraine_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


@pytest.mark.parametrize("text,expected", [
    ("Ubrogepant versus placebo for the acute treatment of a single migraine "
     "attack; 2-hour pain freedom and most bothersome symptom freedom.", "acute"),
    ("Erenumab versus placebo for prevention of episodic migraine; change in "
     "monthly migraine days and 50% responder rate.", "preventive"),
    ("OnabotulinumtoxinA versus placebo in chronic migraine; change in monthly "
     "headache days and medication-overuse headache.", "chronic"),
    ("Remote electrical neuromodulation versus sham device for acute migraine; "
     "vagus nerve stimulation comparison.", "device_neuromod"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_migraine_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("2-hour pain freedom", "PAIN_FREEDOM_2H"),
    ("pain relief at 2 hours", "PAIN_RELIEF_2H"),
    ("most bothersome symptom freedom", "MBS_FREEDOM"),
    ("sustained pain freedom", "SUSTAINED_PAIN_FREEDOM"),
    ("change in monthly migraine days", "MMD"),
    ("monthly headache days", "MHD"),
    ("50% responder rate", "RESPONDER_50"),
    ("acute medication days", "ACUTE_MED_DAYS"),
    ("HIT-6", "DISABILITY"),
    ("use of rescue medication", "RESCUE_MEDICATION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_migraine_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in MIGRAINE_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"acute", "preventive", "chronic",
                                        "device_neuromod"}


def test_migraine_registered():
    assert "migraine" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["migraine"]
    assert e["detection_function"] is detect_migraine_subspecialty
    assert e["normalizer"] is normalize_migraine_endpoint
    assert set(e["subspecialties"]) == {"acute", "preventive", "chronic",
                                        "device_neuromod"}


def test_detect_specialty_routes_to_migraine():
    spec, sub, _ = detect_specialty(
        "Rimegepant versus placebo for acute treatment of migraine; 2-hour pain "
        "freedom and freedom from the most bothersome symptom")
    assert spec == "migraine" and sub == "acute"


def test_migraine_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


def test_pain_freedom_2x2():
    t = ("2-hour pain freedom was achieved by 90/450 (20.0%) in the ubrogepant "
         "group and 56/456 (12.3%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "PAIN_FREEDOM_2H"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"ubrogepant", "placebo"}


def test_mmd_continuous():
    rows = extract_continuous(
        "Change in monthly migraine days was -3.7 (SD 4.6) in the erenumab arm "
        "and -1.8 (SD 4.5) in the placebo arm")
    assert any(r["endpoint"] == "MMD" for r in rows)
