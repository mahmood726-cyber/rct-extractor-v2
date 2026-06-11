"""
Tests for the postoperative-pain specialty profile, registry wiring, and
arm-level extraction. Mirrors the tuberculosis / ARDS tests.
"""
import pytest

from rct_extractor._engine.specialties.postoperative_pain import (
    POSTOPERATIVE_PAIN_ENDPOINTS, detect_postoperative_pain_subspecialty,
    normalize_postoperative_pain_endpoint, get_postoperative_pain_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.postoperative_pain_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Transversus abdominis plane (TAP) block vs placebo for postoperative pain "
     "after caesarean section; time to first rescue analgesia and pain at rest.",
     "regional_analgesia"),
    ("Dexamethasone vs placebo as part of multimodal analgesia; moderate-to-severe "
     "pain, rescue analgesia and 24-hour morphine consumption.", "multimodal"),
    ("Patient-controlled analgesia (PCA) morphine vs opioid-sparing regimen; "
     "respiratory depression and opioid-related adverse events.", "opioid"),
    ("Pregabalin for prevention of chronic post-surgical pain after thoracotomy; "
     "persistent post-surgical pain at 3 months and 6 months.", "chronic_postsurgical"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_postoperative_pain_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("pain at rest", "PAIN_SCORE"),
    ("24-hour morphine consumption", "OPIOID_CONSUMPTION"),
    ("time to first rescue analgesia", "TIME_TO_RESCUE"),
    ("need for rescue analgesia", "RESCUE_ANALGESIA"),
    ("postoperative nausea and vomiting", "PONV"),
    ("moderate-to-severe pain", "MODERATE_SEVERE_PAIN"),
    ("chronic post-surgical pain", "CPSP"),
    ("patient satisfaction", "SATISFACTION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_postoperative_pain_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in POSTOPERATIVE_PAIN_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"regional_analgesia", "multimodal",
                                        "opioid", "chronic_postsurgical"}


# --- registry wiring ---

def test_postoperative_pain_registered():
    assert "postoperative_pain" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["postoperative_pain"]
    assert e["detection_function"] is detect_postoperative_pain_subspecialty
    assert e["normalizer"] is normalize_postoperative_pain_endpoint
    assert set(e["subspecialties"]) == {"regional_analgesia", "multimodal",
                                        "opioid", "chronic_postsurgical"}


def test_detect_specialty_routes_to_postoperative_pain():
    spec, sub, _ = detect_specialty(
        "Transversus abdominis plane block versus placebo for postoperative pain; "
        "24-hour morphine consumption and time to first rescue analgesia")
    assert spec == "postoperative_pain"


def test_postoperative_pain_does_not_break_malaria_hiv_or_cardio():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in chronic heart failure; cardiovascular death and "
        "heart-failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_rescue_analgesia_2x2():
    t = ("Need for rescue analgesia: TAP block 30/120 (25.0%) "
         "versus placebo 72/118 (61.0%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs
    t0 = tabs[0]
    assert t0["endpoint"] == "RESCUE_ANALGESIA"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"TAP-block", "placebo"}


def test_ponv_2x2():
    t = ("Postoperative nausea and vomiting: dexamethasone 20/150 (13.3%) "
         "versus placebo 48/150 (32.0%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "PONV"


def test_opioid_consumption_continuous():
    t = ("24-hour morphine consumption was 18.4 (SD 8.2) mg with ketamine and "
         "29.7 (SD 10.1) mg with placebo")
    cont = extract_continuous(t)
    assert any(c["endpoint"] == "OPIOID_CONSUMPTION" for c in cont)
