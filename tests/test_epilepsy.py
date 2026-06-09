"""
Tests for the epilepsy / AED specialty profile, registry wiring, and arm-level
extraction. Mirrors the HIV, malaria, typhoid and cholera tests.
"""
import pytest

from src.specialties.epilepsy import (
    EPILEPSY_ENDPOINTS, detect_epilepsy_subspecialty, normalize_epilepsy_endpoint,
    get_epilepsy_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.epilepsy_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)

_SUBS = {"efficacy", "tolerability", "status_epilepticus", "treatment_gap"}


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of levetiracetam versus carbamazepine monotherapy for focal-onset "
     "seizures; 12-month seizure freedom and >=50% responder rate in epilepsy.",
     "efficacy"),
    ("Lamotrigine versus carbamazepine in newly diagnosed epilepsy; treatment "
     "withdrawal due to adverse events, serious adverse events and drug rash.",
     "tolerability"),
    ("Intramuscular midazolam versus intravenous lorazepam for convulsive status "
     "epilepticus; clinical seizure cessation and seizure recurrence.",
     "status_epilepticus"),
    ("Phenobarbital delivered by community health workers to close the epilepsy "
     "treatment gap; medication adherence and retention in care in rural Africa.",
     "treatment_gap"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_epilepsy_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("seizure-free rate", "SEIZURE_FREEDOM"),
    (">=50% responder", "RESPONDER_50"),
    ("monthly seizure frequency", "SEIZURE_FREQUENCY"),
    ("withdrawal due to adverse events", "TREATMENT_WITHDRAWAL"),
    ("clinical seizure cessation", "SEIZURE_CESSATION"),
    ("medication adherence", "ADHERENCE"),
    ("epilepsy treatment gap", "TREATMENT_GAP"),
    ("QOLIE-31", "QUALITY_OF_LIFE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_epilepsy_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in EPILEPSY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in _SUBS


# --- registry wiring ---

def test_epilepsy_registered():
    assert "epilepsy" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["epilepsy"]
    assert e["detection_function"] is detect_epilepsy_subspecialty
    assert e["normalizer"] is normalize_epilepsy_endpoint
    assert set(e["subspecialties"]) == _SUBS


def test_detect_specialty_routes_to_epilepsy():
    spec, sub, _ = detect_specialty(
        "levetiracetam versus carbamazepine monotherapy for newly diagnosed focal "
        "epilepsy; 12-month seizure freedom and >=50% responder rate")
    assert spec == "epilepsy" and sub == "efficacy"


def test_epilepsy_status_routes():
    spec, sub, _ = detect_specialty(
        "buccal midazolam versus rectal diazepam for convulsive status epilepticus "
        "in children; clinical seizure cessation and time to seizure cessation")
    assert spec == "epilepsy" and sub == "status_epilepticus"


def test_epilepsy_treatment_gap_routes():
    spec, sub, _ = detect_specialty(
        "task-shifting phenobarbital delivery by community health workers to reduce "
        "the epilepsy treatment gap; medication adherence and quality of life (QOLIE)")
    assert spec == "epilepsy" and sub == "treatment_gap"


def test_epilepsy_does_not_break_hiv_malaria_cardio_or_neuro():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"
    assert detect_specialty(
        "ocrelizumab in multiple sclerosis; annualized relapse rate and disability "
        "progression on EDSS")[0] == "neurology"


def test_epilepsy_endpoints_exposed_via_registry():
    eps = get_all_endpoints("epilepsy")
    assert "SEIZURE_FREEDOM" in eps and "STATUS" not in eps
    assert normalize_endpoint_by_specialty("responder rate", "epilepsy") == "RESPONDER_50"


# --- arm-level extraction ---

def test_responder_2x2():
    t = ("The 50% responder rate was 96/180 (53.3%) in the levetiracetam group "
         "and 70/179 (39.1%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "RESPONDER_50"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"levetiracetam", "placebo"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (96, 180)


def test_seizure_freedom_2x2():
    t = ("Seizure freedom was achieved in 85/130 (65.4%) of the carbamazepine arm "
         "versus 78/128 (60.9%) in the lamotrigine arm")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "SEIZURE_FREEDOM"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"carbamazepine", "lamotrigine"}


def test_seizure_frequency_is_lognormal():
    r = extract_continuous("mean monthly seizure frequency 4.2 ± 1.8 in the levetiracetam arm")
    assert r and r[0]["endpoint"] == "SEIZURE_FREQUENCY" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]


def test_quality_of_life_continuous_poolable():
    r = extract_continuous("mean QOLIE-31 quality of life score 62.5 ± 12.0 in the lamotrigine arm")
    assert r and r[0]["endpoint"] == "QUALITY_OF_LIFE" and r[0]["poolable"] is True
