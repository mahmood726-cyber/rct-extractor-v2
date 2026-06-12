"""
Tests for the obstructive-sleep-apnoea (OSA) specialty profile (cpap /
oral_appliance / intervention), registry wiring, and arm-level extraction.

Routing note: sleep-apnoea keywords (obstructive sleep apnoea, OSA/OSAS,
apnoea-hypopnoea index / AHI, CPAP, Epworth Sleepiness Scale, polysomnography,
mandibular advancement, hypoglossal nerve stimulation) are claimed by no
existing profile. British/American: apnoea (UK) vs apnea (US) -> 'apno?ea'.
"""
import pytest

from rct_extractor._engine.specialties.obstructive_sleep_apnea import (
    OBSTRUCTIVE_SLEEP_APNEA_ENDPOINTS, detect_obstructive_sleep_apnea_subspecialty,
    normalize_obstructive_sleep_apnea_endpoint,
    get_obstructive_sleep_apnea_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.obstructive_sleep_apnea_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Continuous positive airway pressure (CPAP) versus sham CPAP in obstructive sleep "
     "apnoea; apnoea-hypopnoea index and Epworth Sleepiness Scale were the primary "
     "outcomes, with CPAP adherence.", "cpap"),
    ("Mandibular advancement device versus CPAP for obstructive sleep apnoea; apnoea-"
     "hypopnoea index and daytime sleepiness.", "oral_appliance"),
    ("Hypoglossal nerve stimulation versus sham for obstructive sleep apnoea; apnoea-"
     "hypopnoea index reduction and surgical success.", "intervention"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_obstructive_sleep_apnea_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("apnoea-hypopnoea index", "AHI"),
    ("apnea-hypopnea index", "AHI"),
    ("oxygen desaturation index", "ODI"),
    ("Epworth Sleepiness Scale", "ESS"),
    ("CPAP adherence", "CPAP_ADHERENCE"),
    ("systolic blood pressure", "BLOOD_PRESSURE"),
    ("nadir oxygen saturation", "MINIMUM_SPO2"),
    ("functional outcomes of sleep questionnaire", "FOSQ"),
    ("ahi responder", "AHI_RESPONDER"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_obstructive_sleep_apnea_endpoint(phrase) == canonical


def test_british_american_apnoea():
    assert normalize_obstructive_sleep_apnea_endpoint("apnoea-hypopnoea index") == \
        normalize_obstructive_sleep_apnea_endpoint("apnea-hypopnea index") == "AHI"


def test_endpoints_have_required_fields():
    valid = {"cpap", "oral_appliance", "intervention"}
    for name, info in OBSTRUCTIVE_SLEEP_APNEA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_subspecialty_patterns_cover_all_three():
    for sub in ("cpap", "oral_appliance", "intervention"):
        assert get_obstructive_sleep_apnea_endpoint_patterns(sub), sub


# --- registry wiring ---

def test_obstructive_sleep_apnea_registered():
    assert "obstructive_sleep_apnea" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["obstructive_sleep_apnea"]
    assert e["detection_function"] is detect_obstructive_sleep_apnea_subspecialty
    assert e["normalizer"] is normalize_obstructive_sleep_apnea_endpoint
    assert set(e["subspecialties"]) == {"cpap", "oral_appliance", "intervention"}


def test_detect_specialty_routes_to_obstructive_sleep_apnea():
    spec, sub, _ = detect_specialty(
        "Continuous positive airway pressure versus sham CPAP in adults with moderate-to-"
        "severe obstructive sleep apnoea; the primary outcome was the apnoea-hypopnoea index "
        "with the Epworth Sleepiness Scale and CPAP adherence as secondary outcomes.")
    assert spec == "obstructive_sleep_apnea" and sub == "cpap"


def test_obstructive_sleep_apnea_does_not_break_neighbors():
    assert detect_specialty(
        "Budesonide/formoterol versus placebo in asthma; FEV1 and annual exacerbation "
        "rate")[0] == "respiratory"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death and heart failure "
        "hospitalization")[0] == "cardiology"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"


# --- arm-level extraction ---

def test_ahi_responder_2x2():
    t = ("Treatment response was achieved in 75/100 (75.0%) in the cpap group and in "
         "25/100 (25.0%) in the sham group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "AHI_RESPONDER"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"cpap", "sham"}


def test_ahi_continuous_poolable():
    r = extract_continuous("the mean apnoea-hypopnoea index was 8.5 ± 4.0 events/h in the cpap arm")
    assert r and r[0]["endpoint"] == "AHI" and r[0]["poolable"] is True
    assert r[0].get("pooling_note") is None


def test_ess_continuous_poolable():
    r = extract_continuous("the mean Epworth Sleepiness Scale was 7.0 ± 3.0 in the "
                           "mandibular-advancement-device arm")
    assert r and r[0]["endpoint"] == "ESS" and r[0]["poolable"] is True
