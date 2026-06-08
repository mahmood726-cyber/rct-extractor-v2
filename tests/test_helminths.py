"""
Tests for the soil-transmitted helminths (STH) / deworming specialty profile,
registry wiring, and arm-level extraction. Mirrors the HIV, malaria, typhoid and
schistosomiasis tests.
"""
import pytest

from src.specialties.helminths import (
    HELMINTHS_ENDPOINTS, detect_helminths_subspecialty,
    normalize_helminths_endpoint, get_helminths_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.helminths_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of albendazole versus mebendazole for soil-transmitted helminths; "
     "parasitological cure rate and egg reduction rate by Kato-Katz at day 21.",
     "treatment"),
    ("Mass drug administration with albendazole for school-based deworming; "
     "soil-transmitted helminth infection and moderate-to-heavy infection at "
     "12-month follow-up.", "mass_deworming"),
    ("Twice-yearly deworming with albendazole; effect on weight gain, "
     "height-for-age (stunting), haemoglobin and school attendance in preschool "
     "children.", "nutrition"),
    ("Reinfection with soil-transmitted helminths after albendazole treatment; "
     "reinfection rate and incidence of infection 6 and 12 months post-treatment.",
     "reinfection"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_helminths_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("parasitological cure rate", "CURE_RATE"),
    ("egg reduction rate", "EGG_REDUCTION_RATE"),
    ("fecal egg count reduction", "EGG_REDUCTION_RATE"),
    ("geometric mean egg count", "EGG_COUNT"),
    ("eggs per gram", "EGG_COUNT"),
    ("infection prevalence", "INFECTION_PREVALENCE"),
    ("moderate-to-heavy infection", "HEAVY_INFECTION"),
    ("height-for-age z-score", "HEIGHT"),
    ("mid-upper-arm circumference", "MUAC"),
    ("reinfection rate", "REINFECTION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_helminths_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in HELMINTHS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {
            "treatment", "mass_deworming", "nutrition", "reinfection"}


# --- registry wiring ---

def test_helminths_registered():
    assert "helminths" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["helminths"]
    assert e["detection_function"] is detect_helminths_subspecialty
    assert e["normalizer"] is normalize_helminths_endpoint
    assert set(e["subspecialties"]) == {
        "treatment", "mass_deworming", "nutrition", "reinfection"}


def test_detect_specialty_routes_to_helminths():
    spec, sub, _ = detect_specialty(
        "albendazole versus mebendazole for Ascaris lumbricoides and hookworm; "
        "parasitological cure rate and egg reduction rate by Kato-Katz")
    assert spec == "helminths" and sub == "treatment"


def test_helminths_nutrition_routes():
    spec, sub, _ = detect_specialty(
        "School-based deworming with albendazole; effect on weight gain, "
        "height-for-age and haemoglobin in school-age children")
    assert spec == "helminths" and sub == "nutrition"


def test_helminths_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "azithromycin versus ceftriaxone for blood-culture-confirmed typhoid "
        "fever; fever clearance time")[0] == "typhoid"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_cure_rate_2x2():
    t = ("Parasitological cure was achieved by 142/150 (94.7%) in the albendazole "
         "group and 96/148 (64.9%) in the mebendazole group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "CURE_RATE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"albendazole", "mebendazole"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (142, 150)


def test_reinfection_2x2():
    t = ("Reinfection occurred in 30/200 (15.0%) in the albendazole group versus "
         "60/200 (30.0%) in the untreated group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "REINFECTION"


def test_egg_count_is_lognormal():
    r = extract_continuous("mean egg count 250 ± 80 eggs per gram in the albendazole arm")
    assert r and r[0]["endpoint"] == "EGG_COUNT" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]


def test_weight_gain_continuous_poolable():
    r = extract_continuous("mean weight gain 2.4 ± 1.1 kg in the albendazole arm")
    assert r and r[0]["endpoint"] == "WEIGHT" and r[0]["poolable"] is True


def test_haemoglobin_continuous_poolable():
    r = extract_continuous("mean haemoglobin 11.8 ± 1.4 g/dl in the albendazole arm")
    assert r and r[0]["endpoint"] == "ANAEMIA" and r[0]["poolable"] is True
