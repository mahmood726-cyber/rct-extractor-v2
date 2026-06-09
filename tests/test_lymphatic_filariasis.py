"""
Tests for the lymphatic filariasis (LF / elephantiasis) specialty profile,
registry wiring, and arm-level extraction. Mirrors the HIV, malaria, typhoid,
schistosomiasis and helminths tests.
"""
import pytest

from src.specialties.lymphatic_filariasis import (
    LYMPHATIC_FILARIASIS_ENDPOINTS, detect_lymphatic_filariasis_subspecialty,
    normalize_lymphatic_filariasis_endpoint,
    get_lymphatic_filariasis_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.lymphatic_filariasis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Mass drug administration with the triple-drug IDA regimen (ivermectin, "
     "diethylcarbamazine and albendazole) for bancroftian filariasis; mf clearance "
     "and microfilaria density at 12 months.", "mda"),
    ("Community microfilaria prevalence and circulating filarial antigen prevalence "
     "after five annual rounds of MDA; transmission assessment survey and "
     "xenomonitoring of Wuchereria bancrofti.", "transmission"),
    ("Surgery for hydrocele and home-based limb care for lymphoedema (elephantiasis) "
     "in lymphatic filariasis; acute adenolymphangitis episodes and limb volume.",
     "morbidity"),
    ("Safety of single-dose diethylcarbamazine plus albendazole; adverse events, "
     "serious adverse events and systemic post-treatment reactions (fever, headache) "
     "in microfilaraemic adults.", "safety"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_lymphatic_filariasis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("microfilaria clearance", "MF_CLEARANCE"),
    ("clearance of microfilaraemia", "MF_CLEARANCE"),
    ("amicrofilaraemia", "MF_CLEARANCE"),
    ("microfilaria density", "MF_DENSITY"),
    ("circulating filarial antigen clearance", "ANTIGEN_CLEARANCE"),
    ("microfilaria prevalence", "MF_PREVALENCE"),
    ("antigen prevalence", "ANTIGEN_PREVALENCE"),
    ("lymphoedema", "LYMPHOEDEMA"),
    ("hydrocele", "HYDROCELE"),
    ("acute adenolymphangitis", "ACUTE_ATTACK"),
    ("limb volume", "LIMB_VOLUME"),
    ("serious adverse event", "SERIOUS_AE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_lymphatic_filariasis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in LYMPHATIC_FILARIASIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"mda", "transmission", "morbidity", "safety"}


# --- registry wiring ---

def test_lymphatic_filariasis_registered():
    assert "lymphatic_filariasis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["lymphatic_filariasis"]
    assert e["detection_function"] is detect_lymphatic_filariasis_subspecialty
    assert e["normalizer"] is normalize_lymphatic_filariasis_endpoint
    assert set(e["subspecialties"]) == {"mda", "transmission", "morbidity", "safety"}


def test_detect_specialty_routes_to_lymphatic_filariasis():
    spec, sub, _ = detect_specialty(
        "Triple-drug therapy (IDA: ivermectin, diethylcarbamazine, albendazole) "
        "for Wuchereria bancrofti lymphatic filariasis; clearance of microfilaraemia "
        "and microfilaria density reduction at month 12")
    assert spec == "lymphatic_filariasis" and sub == "mda"


def test_lymphatic_filariasis_morbidity_routes():
    spec, sub, _ = detect_specialty(
        "Doxycycline for lymphoedema and hydrocele in bancroftian filariasis; "
        "lymphoedema stage progression and acute adenolymphangitis attacks")
    assert spec == "lymphatic_filariasis" and sub == "morbidity"


def test_lymphatic_filariasis_does_not_break_other_specialties():
    assert detect_specialty(
        "albendazole versus mebendazole for soil-transmitted helminths (Ascaris, "
        "hookworm); parasitological cure rate and egg reduction rate by Kato-Katz"
        )[0] == "helminths"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "praziquantel for Schistosoma mansoni; egg reduction rate and "
        "parasitological cure by Kato-Katz")[0] == "schistosomiasis"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_mf_clearance_2x2():
    t = ("Clearance of microfilaraemia was achieved by 88/100 (88.0%) in the IDA "
         "group and 60/100 (60.0%) in the DEC group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "MF_CLEARANCE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"IDA", "diethylcarbamazine"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (88, 100)


def test_adverse_event_2x2():
    t = ("Adverse events occurred in 20/120 (16.7%) in the ivermectin group versus "
         "12/118 (10.2%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ADVERSE_EVENTS"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"ivermectin", "placebo"}


def test_mf_density_is_lognormal():
    r = extract_continuous(
        "mean microfilaria density 250 ± 80 microfilariae per ml in the DEC group")
    assert r and r[0]["endpoint"] == "MF_DENSITY" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]


def test_limb_volume_continuous_poolable():
    r = extract_continuous(
        "mean affected limb volume 1200 ± 300 ml in the doxycycline group")
    assert r and r[0]["endpoint"] == "LIMB_VOLUME" and r[0]["poolable"] is True
