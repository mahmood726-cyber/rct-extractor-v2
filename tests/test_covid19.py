"""
Tests for the COVID-19 specialty profile, registry wiring, and arm-level
extraction. Mirrors the tuberculosis / parkinsons tests.
"""
import pytest

from rct_extractor._engine.specialties.covid19 import (
    COVID19_ENDPOINTS, detect_covid19_subspecialty,
    normalize_covid19_endpoint, get_covid19_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.covid19_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


@pytest.mark.parametrize("text,expected", [
    ("Nirmatrelvir-ritonavir versus placebo in non-hospitalized COVID-19; "
     "COVID-19-related hospitalization or death and time to sustained recovery.",
     "antiviral"),
    ("Tocilizumab versus standard care in hospitalized COVID-19; 28-day mortality "
     "and progression to invasive mechanical ventilation.", "immunomodulator"),
    ("BNT162b2 vaccine versus placebo; vaccine efficacy against symptomatic "
     "COVID-19.", "prophylaxis_vaccine"),
    ("Convalescent plasma versus standard care in critically ill COVID-19; "
     "organ support-free days.", "severe_supportive"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_covid19_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("COVID-19-related hospitalization or death", "HOSPITALIZATION_DEATH"),
    ("28-day mortality", "MORTALITY"),
    ("time to sustained recovery", "RECOVERY"),
    ("invasive mechanical ventilation", "PROGRESSION"),
    ("time to viral clearance", "VIRAL_CLEARANCE"),
    ("vaccine efficacy", "VACCINE_EFFICACY"),
    ("symptomatic COVID-19", "SYMPTOMATIC_INFECTION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_covid19_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in COVID19_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"antiviral", "immunomodulator",
                                        "prophylaxis_vaccine", "severe_supportive"}


def test_covid19_registered():
    assert "covid19" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["covid19"]
    assert e["detection_function"] is detect_covid19_subspecialty
    assert e["normalizer"] is normalize_covid19_endpoint
    assert set(e["subspecialties"]) == {"antiviral", "immunomodulator",
                                        "prophylaxis_vaccine", "severe_supportive"}


def test_detect_specialty_routes_to_covid19():
    spec, sub, _ = detect_specialty(
        "Molnupiravir versus placebo in non-hospitalized adults with COVID-19; "
        "hospitalization or death by day 29")
    assert spec == "covid19" and sub == "antiviral"


def test_covid19_wins_over_generic_infectious_disease():
    spec, _, _ = detect_specialty(
        "remdesivir for sars-cov-2; viral infection; antiviral therapy")
    assert spec == "covid19"


def test_covid19_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


def test_hospitalization_death_2x2():
    t = ("COVID-19-related hospitalization or death occurred in 5/1039 (0.5%) in "
         "the nirmatrelvir-ritonavir group and 44/1046 (4.2%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "HOSPITALIZATION_DEATH"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"nirmatrelvir-ritonavir", "placebo"}


def test_mortality_2x2():
    t = ("28-day mortality was 29/100 (29.0%) in the dexamethasone group and "
         "40/100 (40.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "MORTALITY"
