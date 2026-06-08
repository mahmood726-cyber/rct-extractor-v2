"""
Tests for the cholera specialty profile, registry wiring, and arm-level extraction.
Mirrors the HIV, malaria and typhoid tests.
"""
import pytest

from src.specialties.cholera import (
    CHOLERA_ENDPOINTS, detect_cholera_subspecialty, normalize_cholera_endpoint,
    get_cholera_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.cholera_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Randomized trial of single-dose azithromycin versus ciprofloxacin in cholera; "
     "bacteriological cure, stool culture clearance and duration of diarrhoea.",
     "treatment"),
    ("Rice-based oral rehydration solution versus standard ORS in cholera; total "
     "stool output and need for unscheduled intravenous fluid.", "rehydration"),
    ("Oral cholera vaccine (Shanchol) versus placebo; protective efficacy against "
     "culture-confirmed cholera and vibriocidal seroconversion.", "vaccine"),
    ("Severe dehydration and hypovolaemic shock in cholera; case fatality and acute "
     "kidney injury among severe cholera.", "severe"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_cholera_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("clinical cure rate", "CLINICAL_CURE"),
    ("stool culture clearance", "BACTERIOLOGICAL_CLEARANCE"),
    ("duration of diarrhoea", "DIARRHEA_DURATION"),
    ("total stool output", "STOOL_OUTPUT"),
    ("culture-confirmed cholera", "CHOLERA_INCIDENCE"),
    ("vibriocidal seroconversion", "VIBRIOCIDAL_SEROCONVERSION"),
    ("vibriocidal antibody titre", "IMMUNOGENICITY"),
    ("severe dehydration", "SEVERE_DEHYDRATION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_cholera_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in CHOLERA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"treatment", "rehydration", "vaccine", "severe"}


# --- registry wiring ---

def test_cholera_registered():
    assert "cholera" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["cholera"]
    assert e["detection_function"] is detect_cholera_subspecialty
    assert e["normalizer"] is normalize_cholera_endpoint
    assert set(e["subspecialties"]) == {"treatment", "rehydration", "vaccine", "severe"}


def test_detect_specialty_routes_to_cholera():
    spec, sub, _ = detect_specialty(
        "single-dose doxycycline versus azithromycin for Vibrio cholerae (El Tor) "
        "infection; bacteriological clearance and duration of diarrhoea in cholera")
    assert spec == "cholera" and sub == "treatment"


def test_cholera_vaccine_routes():
    spec, sub, _ = detect_specialty(
        "oral cholera vaccine (Shanchol, killed whole-cell) versus placebo; vaccine "
        "efficacy against culture-confirmed cholera and vibriocidal seroconversion")
    assert spec == "cholera" and sub == "vaccine"


def test_cholera_does_not_break_hiv_malaria_typhoid_or_cardio():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "azithromycin for blood-culture-confirmed typhoid fever; fever clearance "
        "time and clinical cure in enteric fever")[0] == "typhoid"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_bacteriological_clearance_2x2():
    t = ("Bacteriological clearance was achieved by 58/60 (96.7%) in the azithromycin "
         "group and 41/59 (69.5%) in the ciprofloxacin group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "BACTERIOLOGICAL_CLEARANCE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"azithromycin", "ciprofloxacin"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (58, 60)


def test_cholera_incidence_2x2():
    t = ("Culture-confirmed cholera occurred in 12/9999 (0.1%) in the oral cholera "
         "vaccine group versus 38/9999 (0.4%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "CHOLERA_INCIDENCE"


def test_diarrhea_duration_continuous_poolable():
    r = extract_continuous("mean duration of diarrhoea 28 ± 10 hours in the doxycycline arm")
    assert r and r[0]["endpoint"] == "DIARRHEA_DURATION" and r[0]["poolable"] is True


def test_stool_output_continuous_poolable():
    r = extract_continuous("mean total stool output 180 ± 45 mL/kg in the azithromycin arm")
    assert r and r[0]["endpoint"] == "STOOL_OUTPUT" and r[0]["poolable"] is True


def test_immunogenicity_is_lognormal():
    r = extract_continuous("mean vibriocidal antibody titre 1850 ± 420 in the Dukoral arm")
    assert r and r[0]["endpoint"] == "IMMUNOGENICITY" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
