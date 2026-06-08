"""
Tests for the pneumonia specialty profile, registry wiring, and arm-level extraction.
Mirrors the HIV, malaria and typhoid tests.
"""
import pytest

from src.specialties.pneumonia import (
    PNEUMONIA_ENDPOINTS, detect_pneumonia_subspecialty, normalize_pneumonia_endpoint,
    get_pneumonia_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.pneumonia_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of oral amoxicillin versus co-trimoxazole for non-severe childhood "
     "pneumonia; clinical cure and treatment failure with time to resolution of "
     "fast breathing.", "treatment"),
    ("Pneumococcal conjugate vaccine (PCV13) versus placebo; vaccine efficacy "
     "against radiologically-confirmed pneumonia, invasive pneumococcal disease "
     "and vaccine-type nasopharyngeal carriage with serotype-specific IgG.", "vaccine"),
    ("Effect of zinc on all-cause mortality and pneumonia-specific mortality in "
     "children; case fatality among children who died of pneumonia.", "mortality"),
    ("Severe pneumonia requiring hospital admission; need for mechanical "
     "ventilation, intensive care unit admission and empyema with pleural effusion.",
     "severe"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_pneumonia_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("clinical cure rate", "CLINICAL_CURE"),
    ("treatment failure", "TREATMENT_FAILURE"),
    ("time to resolution of symptoms", "TIME_TO_RESOLUTION"),
    ("radiologically-confirmed pneumonia", "PNEUMONIA_INCIDENCE"),
    ("invasive pneumococcal disease", "INVASIVE_PNEUMOCOCCAL_DISEASE"),
    ("nasopharyngeal carriage", "NASOPHARYNGEAL_CARRIAGE"),
    ("serotype-specific IgG", "IMMUNOGENICITY"),
    ("pneumonia-specific mortality", "PNEUMONIA_MORTALITY"),
    ("case fatality rate", "CASE_FATALITY"),
    ("severe pneumonia", "SEVERE_PNEUMONIA"),
    ("hospital admission", "HOSPITALISATION"),
    ("mechanical ventilation", "MECHANICAL_VENTILATION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_pneumonia_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in PNEUMONIA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"treatment", "vaccine", "mortality", "severe"}


# --- registry wiring ---

def test_pneumonia_registered():
    assert "pneumonia" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["pneumonia"]
    assert e["detection_function"] is detect_pneumonia_subspecialty
    assert e["normalizer"] is normalize_pneumonia_endpoint
    assert set(e["subspecialties"]) == {"treatment", "vaccine", "mortality", "severe"}


def test_detect_specialty_routes_to_pneumonia():
    spec, sub, _ = detect_specialty(
        "oral amoxicillin versus injectable penicillin for WHO-defined severe "
        "childhood pneumonia; clinical cure and treatment failure with time to "
        "resolution of chest indrawing in community-acquired pneumonia")
    assert spec == "pneumonia" and sub == "treatment"


def test_pneumonia_vaccine_routes():
    spec, sub, _ = detect_specialty(
        "pneumococcal conjugate vaccine (PCV13) versus placebo; vaccine efficacy "
        "against radiologically-confirmed pneumonia and invasive pneumococcal "
        "disease with vaccine-type nasopharyngeal carriage and anti-pneumococcal IgG")
    assert spec == "pneumonia" and sub == "vaccine"


def test_pneumonia_does_not_break_hiv_malaria_typhoid_or_cardio():
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

def test_clinical_cure_2x2():
    t = ("Clinical cure was achieved by 142/150 (94.7%) in the amoxicillin group "
         "and 120/148 (81.1%) in the co-trimoxazole group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "CLINICAL_CURE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"amoxicillin", "co-trimoxazole"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (142, 150)


def test_pneumonia_incidence_2x2():
    t = ("Radiologically-confirmed pneumonia occurred in 333/9999 (3.3%) in the "
         "pneumococcal conjugate vaccine group versus 513/9999 (5.1%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "PNEUMONIA_INCIDENCE"


def test_time_to_resolution_continuous_poolable():
    r = extract_continuous("mean time to resolution of fever 48 ± 18 hours in the amoxicillin arm")
    assert r and r[0]["endpoint"] == "TIME_TO_RESOLUTION" and r[0]["poolable"] is True


def test_immunogenicity_is_lognormal():
    r = extract_continuous("mean anti-pneumococcal IgG 4.2 ± 1.3 mcg/ml in the PCV13 arm")
    assert r and r[0]["endpoint"] == "IMMUNOGENICITY" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]


# --- regression: American "bacteremia/bacteremic" spelling (ae-trap fix 2026-06-08) ---
# `bacterae?mic`/`bacterae?mia` matched only the British spelling and silently
# missed the dominant American forms, dropping IPD/bacteraemic-pneumonia events.

@pytest.mark.parametrize("phrase", [
    "bacteremic pneumonia", "bacteraemic pneumonia",
    "pneumococcal bacteremia", "pneumococcal bacteraemia",
])
def test_bacteremia_both_spellings_tag_ipd(phrase):
    import re
    pats = []
    for sub in ("treatment", "vaccine", "mortality", "severe"):
        pats += get_pneumonia_endpoint_patterns(sub)
    ep = next((e for p, e in pats if re.search(p, phrase, re.I)), None)
    assert ep == "INVASIVE_PNEUMOCOCCAL_DISEASE", phrase
