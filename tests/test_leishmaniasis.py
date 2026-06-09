"""
Tests for the leishmaniasis specialty profile, registry wiring, and arm-level
extraction. Mirrors the HIV, malaria, typhoid and schistosomiasis tests.
"""
import pytest

from src.specialties.leishmaniasis import (
    LEISHMANIASIS_ENDPOINTS, detect_leishmaniasis_subspecialty,
    normalize_leishmaniasis_endpoint, get_leishmaniasis_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.leishmaniasis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of liposomal amphotericin B for visceral leishmaniasis (kala-azar) in "
     "East Africa; initial cure at end of treatment and definitive cure at 6 months "
     "with relapse and splenic parasite clearance.", "visceral"),
    ("Randomized trial of topical paromomycin versus intralesional meglumine "
     "antimoniate for cutaneous leishmaniasis due to Leishmania major; complete "
     "cure by re-epithelialisation and lesion size reduction at week 12.", "cutaneous"),
    ("Open-label RCT comparing a 17-day combination therapy of sodium stibogluconate "
     "and paromomycin with 30-day monotherapy; treatment duration and length of "
     "hospital stay were secondary endpoints.", "combination"),
    ("Safety analysis of pentavalent antimonials in visceral leishmaniasis: serious "
     "adverse events, cardiotoxicity with QTc prolongation, nephrotoxicity and "
     "treatment-related mortality.", "safety"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_leishmaniasis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("definitive cure", "DEFINITIVE_CURE"),
    ("final cure rate", "DEFINITIVE_CURE"),
    ("initial cure", "INITIAL_CURE"),
    ("relapse rate", "RELAPSE"),
    ("splenic parasite clearance", "PARASITE_CLEARANCE"),
    ("complete cure", "CUTANEOUS_CURE"),
    ("cure rate", "CUTANEOUS_CURE"),
    ("lesion size", "LESION_SIZE"),
    ("treatment duration", "TREATMENT_DURATION"),
    ("qtc prolongation", "CARDIOTOXICITY"),
    ("serious adverse events", "SERIOUS_ADVERSE_EVENTS"),
    ("nephrotoxicity", "NEPHROTOXICITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_leishmaniasis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in LEISHMANIASIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"visceral", "cutaneous", "combination", "safety"}


# --- registry wiring ---

def test_leishmaniasis_registered():
    assert "leishmaniasis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["leishmaniasis"]
    assert e["detection_function"] is detect_leishmaniasis_subspecialty
    assert e["normalizer"] is normalize_leishmaniasis_endpoint
    assert set(e["subspecialties"]) == {"visceral", "cutaneous", "combination", "safety"}


def test_detect_specialty_routes_to_visceral():
    spec, sub, _ = detect_specialty(
        "liposomal amphotericin B versus sodium stibogluconate for visceral "
        "leishmaniasis (kala-azar); definitive cure at 6 months and relapse")
    assert spec == "leishmaniasis" and sub == "visceral"


def test_detect_specialty_routes_to_cutaneous():
    spec, sub, _ = detect_specialty(
        "intralesional meglumine antimoniate for cutaneous leishmaniasis caused by "
        "Leishmania tropica; complete cure by re-epithelialisation and lesion size")
    assert spec == "leishmaniasis" and sub == "cutaneous"


def test_leishmaniasis_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "azithromycin versus ceftriaxone for blood-culture-confirmed typhoid "
        "fever; fever clearance time")[0] == "typhoid"
    assert detect_specialty(
        "praziquantel versus oxamniquine for Schistosoma mansoni; parasitological "
        "cure rate and egg reduction rate by Kato-Katz")[0] == "schistosomiasis"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_definitive_cure_2x2():
    t = ("Definitive cure at 6 months was achieved by 95/100 (95.0%) in the "
         "miltefosine group and 80/100 (80.0%) in the paromomycin group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "DEFINITIVE_CURE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"miltefosine", "paromomycin"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (95, 100)


def test_relapse_2x2():
    t = ("Relapse occurred in 8/95 (8.4%) in the miltefosine group and "
         "4/98 (4.1%) in the paromomycin group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "RELAPSE"


def test_liposomal_amphotericin_b_arm_label():
    # the multi-word drug name (which contains "amphotericin B" as a substring)
    # must resolve to the liposomal label, not the bare amphotericin-B one
    props = extract_proportions(
        "complete cure in 47/50 (94.0%) of patients treated with liposomal "
        "amphotericin B")
    assert any(p["arm"] == "liposomal-amphotericin-b" for p in props)


def test_lesion_size_continuous_poolable():
    r = extract_continuous("mean lesion size 12.5 ± 4.2 mm in the miltefosine arm")
    assert r and r[0]["endpoint"] == "LESION_SIZE" and r[0]["poolable"] is True
