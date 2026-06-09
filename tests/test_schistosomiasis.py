"""
Tests for the schistosomiasis specialty profile, registry wiring, and arm-level
extraction. Mirrors the HIV, malaria and typhoid tests.
"""
import pytest

from rct_extractor._engine.specialties.schistosomiasis import (
    SCHISTOSOMIASIS_ENDPOINTS, detect_schistosomiasis_subspecialty,
    normalize_schistosomiasis_endpoint, get_schistosomiasis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.schistosomiasis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of praziquantel vs artesunate for Schistosoma mansoni; parasitological "
     "cure rate and egg reduction rate by Kato-Katz at week 4.", "treatment"),
    ("Mass drug administration with praziquantel in school-based treatment; "
     "infection prevalence and reinfection at 12-month follow-up.", "prevention"),
    ("Hepatosplenic schistosomiasis with periportal (liver) fibrosis on ultrasound; "
     "haematuria and bladder pathology and anaemia.", "morbidity"),
    ("Sh28GST (Bilhvax) schistosomiasis vaccine versus placebo; protective efficacy "
     "against infection, anti-Sh28GST IgG immunogenicity and seroconversion.",
     "vaccine"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_schistosomiasis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("parasitological cure rate", "PARASITOLOGICAL_CURE"),
    ("egg reduction rate", "EGG_REDUCTION_RATE"),
    ("geometric mean egg count", "EGG_COUNT"),
    ("infection prevalence", "INFECTION_PREVALENCE"),
    ("reinfection rate", "REINFECTION"),
    ("periportal fibrosis", "PERIPORTAL_FIBROSIS"),
    ("microhaematuria", "HAEMATURIA"),
    ("anti-Sh28GST IgG", "IMMUNOGENICITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_schistosomiasis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in SCHISTOSOMIASIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"treatment", "prevention", "morbidity", "vaccine"}


# --- registry wiring ---

def test_schistosomiasis_registered():
    assert "schistosomiasis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["schistosomiasis"]
    assert e["detection_function"] is detect_schistosomiasis_subspecialty
    assert e["normalizer"] is normalize_schistosomiasis_endpoint
    assert set(e["subspecialties"]) == {"treatment", "prevention", "morbidity", "vaccine"}


def test_detect_specialty_routes_to_schistosomiasis():
    spec, sub, _ = detect_specialty(
        "praziquantel versus oxamniquine for Schistosoma mansoni infection; "
        "parasitological cure rate and egg reduction rate by Kato-Katz")
    assert spec == "schistosomiasis" and sub == "treatment"


def test_schistosomiasis_vaccine_routes():
    spec, sub, _ = detect_specialty(
        "Sh28GST (Bilhvax) schistosomiasis vaccine versus placebo; protective "
        "efficacy against Schistosoma haematobium infection and anti-Sh28GST IgG "
        "antibody response")
    assert spec == "schistosomiasis" and sub == "vaccine"


def test_schistosomiasis_does_not_break_other_specialties():
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

def test_parasitological_cure_2x2():
    t = ("Parasitological cure was achieved by 142/150 (94.7%) in the praziquantel "
         "group and 96/148 (64.9%) in the artesunate group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "PARASITOLOGICAL_CURE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"praziquantel", "artesunate"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (142, 150)


def test_reinfection_2x2():
    t = ("Reinfection occurred in 30/200 (15.0%) in the praziquantel group versus "
         "60/200 (30.0%) in the untreated group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "REINFECTION"


def test_egg_count_is_lognormal():
    r = extract_continuous("mean egg count 250 ± 80 eggs per gram in the praziquantel arm")
    assert r and r[0]["endpoint"] == "EGG_COUNT" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]


def test_anaemia_continuous_poolable():
    r = extract_continuous("mean haemoglobin 11.8 ± 1.4 g/dl in the praziquantel arm")
    assert r and r[0]["endpoint"] == "ANAEMIA" and r[0]["poolable"] is True
