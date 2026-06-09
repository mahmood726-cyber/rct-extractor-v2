"""
Tests for the onchocerciasis (river blindness) specialty profile, registry wiring,
and arm-level extraction. Mirrors the HIV, malaria, typhoid and schistosomiasis tests.
"""
import pytest

from src.specialties.onchocerciasis import (
    ONCHOCERCIASIS_ENDPOINTS, detect_onchocerciasis_subspecialty,
    normalize_onchocerciasis_endpoint, get_onchocerciasis_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.onchocerciasis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of ivermectin vs moxidectin for Onchocerca volvulus; skin microfilarial "
     "density and microfilarial clearance by skin snip at month 12.", "treatment"),
    ("Community-directed treatment with ivermectin (CDTI) as mass drug "
     "administration; microfilarial prevalence, palpable-nodule prevalence and "
     "annual transmission potential after years of treatment.", "mda"),
    ("Ocular onchocerciasis with microfilariae in the cornea and anterior chamber; "
     "sclerosing keratitis, visual impairment / blindness, onchodermatitis with "
     "severe itching and onchocerciasis-associated epilepsy.", "morbidity"),
    ("Adverse events and Mazzotti reaction after ivermectin; serious adverse events "
     "including post-ivermectin encephalopathy in a Loa loa co-endemic area.",
     "safety"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_onchocerciasis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("microfilarial clearance", "MICROFILARIAL_CLEARANCE"),
    ("skin microfilarial density", "SKIN_MF_DENSITY"),
    ("community microfilarial load", "SKIN_MF_DENSITY"),
    ("microfilarial density reduction", "MICROFILARIAL_REDUCTION"),
    ("palpable nodule", "NODULE_PREVALENCE"),
    ("annual transmission potential", "TRANSMISSION"),
    ("punctate keratitis", "OCULAR_MICROFILARIAE"),
    ("onchodermatitis", "SKIN_DISEASE"),
    ("mazzotti reaction", "MAZZOTTI_REACTION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_onchocerciasis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in ONCHOCERCIASIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"treatment", "mda", "morbidity", "safety"}


# --- registry wiring ---

def test_onchocerciasis_registered():
    assert "onchocerciasis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["onchocerciasis"]
    assert e["detection_function"] is detect_onchocerciasis_subspecialty
    assert e["normalizer"] is normalize_onchocerciasis_endpoint
    assert set(e["subspecialties"]) == {"treatment", "mda", "morbidity", "safety"}


def test_detect_specialty_routes_to_onchocerciasis():
    spec, sub, _ = detect_specialty(
        "ivermectin versus moxidectin for Onchocerca volvulus (river blindness); "
        "skin microfilarial density by skin snip and microfilarial clearance")
    assert spec == "onchocerciasis" and sub == "treatment"


def test_onchocerciasis_mda_routes():
    spec, sub, _ = detect_specialty(
        "community-directed treatment with ivermectin (CDTI) for onchocerciasis; "
        "microfilarial prevalence and annual transmission potential by Simulium catch")
    assert spec == "onchocerciasis" and sub == "mda"


def test_onchocerciasis_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "praziquantel versus oxamniquine for Schistosoma mansoni; parasitological "
        "cure rate and egg reduction rate by Kato-Katz")[0] == "schistosomiasis"
    assert detect_specialty(
        "albendazole versus mebendazole for soil-transmitted helminths; hookworm "
        "and Ascaris cure rate and egg reduction rate by Kato-Katz")[0] == "helminths"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_microfilarial_clearance_2x2():
    t = ("Microfilarial clearance (skin-snip negative) was achieved by 142/150 "
         "(94.7%) in the ivermectin group and 96/148 (64.9%) in the moxidectin group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "MICROFILARIAL_CLEARANCE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"ivermectin", "moxidectin"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (142, 150)


def test_nodule_prevalence_2x2():
    t = ("Palpable nodules were present in 30/200 (15.0%) in the ivermectin group "
         "versus 60/200 (30.0%) in the untreated group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "NODULE_PREVALENCE"


def test_skin_mf_density_is_lognormal():
    r = extract_continuous("mean skin microfilarial density 18.5 ± 6.2 microfilariae "
                           "per mg in the ivermectin arm")
    assert r and r[0]["endpoint"] == "SKIN_MF_DENSITY" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]


def test_microfilarial_reduction_continuous_poolable():
    r = extract_continuous("mean microfilarial reduction 92.0 ± 5.0 in the ivermectin arm")
    assert r and r[0]["endpoint"] == "MICROFILARIAL_REDUCTION" and r[0]["poolable"] is True
