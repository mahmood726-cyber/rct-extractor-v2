"""
Tests for the typhoid specialty profile, registry wiring, and arm-level extraction.
Mirrors the HIV and malaria tests.
"""
import pytest

from rct_extractor._engine.specialties.typhoid import (
    TYPHOID_ENDPOINTS, detect_typhoid_subspecialty, normalize_typhoid_endpoint,
    get_typhoid_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.typhoid_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of gatifloxacin vs ceftriaxone for blood-culture-confirmed typhoid; "
     "fever clearance time and clinical cure.", "treatment"),
    ("Vi-tetanus toxoid typhoid conjugate vaccine (TCV) vs meningococcal vaccine; "
     "blood-culture-confirmed typhoid fever incidence and anti-Vi seroconversion.",
     "vaccine"),
    ("Surveillance of multidrug-resistant and extensively drug-resistant typhoid; "
     "fluoroquinolone non-susceptibility and ceftriaxone resistance.", "resistance"),
    ("Typhoid intestinal perforation managed surgically; gastrointestinal bleeding "
     "and typhoid encephalopathy among complicated enteric fever.", "complications"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_typhoid_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("clinical cure rate", "CLINICAL_CURE"),
    ("bacteriological clearance", "MICROBIOLOGICAL_CURE"),
    ("fever clearance time", "FEVER_CLEARANCE_TIME"),
    ("blood culture-confirmed typhoid", "TYPHOID_INCIDENCE"),
    ("anti-Vi IgG", "IMMUNOGENICITY"),
    ("multidrug-resistant typhoid", "MDR_TYPHOID"),
    ("intestinal perforation", "INTESTINAL_PERFORATION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_typhoid_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in TYPHOID_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"treatment", "vaccine", "resistance", "complications"}


# --- registry wiring ---

def test_typhoid_registered():
    assert "typhoid" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["typhoid"]
    assert e["detection_function"] is detect_typhoid_subspecialty
    assert e["normalizer"] is normalize_typhoid_endpoint
    assert set(e["subspecialties"]) == {"treatment", "vaccine", "resistance", "complications"}


def test_detect_specialty_routes_to_typhoid():
    spec, sub, _ = detect_specialty(
        "azithromycin versus ciprofloxacin for blood-culture-confirmed typhoid "
        "fever; fever clearance time and clinical cure in enteric fever")
    assert spec == "typhoid" and sub == "treatment"


def test_typhoid_vaccine_routes():
    spec, sub, _ = detect_specialty(
        "typhoid conjugate vaccine (TCV, Vi-TT) versus meningococcal vaccine; "
        "vaccine efficacy against blood-culture-confirmed typhoid fever and "
        "anti-Vi IgG seroconversion")
    assert spec == "typhoid" and sub == "vaccine"


def test_typhoid_does_not_break_hiv_malaria_or_cardio():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_clinical_cure_2x2():
    t = ("Clinical cure was achieved by 142/150 (94.7%) in the gatifloxacin group "
         "and 120/148 (81.1%) in the ceftriaxone group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "CLINICAL_CURE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"gatifloxacin", "ceftriaxone"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (142, 150)


def test_typhoid_incidence_2x2():
    t = ("Blood culture-confirmed typhoid fever occurred in 12/9999 (0.1%) in the "
         "typhoid conjugate vaccine group versus 38/9999 (0.4%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "TYPHOID_INCIDENCE"


def test_fever_clearance_continuous_poolable():
    r = extract_continuous("mean fever clearance time 92 ± 30 hours in the gatifloxacin arm")
    assert r and r[0]["endpoint"] == "FEVER_CLEARANCE_TIME" and r[0]["poolable"] is True


def test_immunogenicity_is_lognormal():
    r = extract_continuous("mean anti-Vi IgG 1850 ± 420 EU/ml in the TCV arm")
    assert r and r[0]["endpoint"] == "IMMUNOGENICITY" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
