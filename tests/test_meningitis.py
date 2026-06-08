"""
Tests for the meningitis specialty profile, registry wiring, and arm-level extraction.
Mirrors the typhoid, HIV and malaria tests.
"""
import pytest

from src.specialties.meningitis import (
    MENINGITIS_ENDPOINTS, detect_meningitis_subspecialty, normalize_meningitis_endpoint,
    get_meningitis_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.meningitis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of ceftriaxone vs chloramphenicol for bacterial meningitis; CSF "
     "sterilisation and time to clinical recovery with adjunctive dexamethasone.", "treatment"),
    ("Meningococcal A conjugate vaccine (MenAfriVac, MenA-TT) vs polysaccharide "
     "vaccine; serum bactericidal antibody seroconversion and SBA GMT "
     "immunogenicity and nasopharyngeal carriage.", "vaccine"),
    ("Adjunctive therapy and all-cause mortality in pneumococcal meningitis; "
     "in-hospital case fatality and death by day 30.", "mortality"),
    ("Neurological sequelae after bacterial meningitis: sensorineural hearing "
     "loss, seizures, hydrocephalus and neurodevelopmental impairment.", "sequelae"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_meningitis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("clinical cure rate", "CLINICAL_CURE"),
    ("CSF sterilisation", "CSF_STERILIZATION"),
    ("time to clinical recovery", "TIME_TO_RECOVERY"),
    ("case fatality rate", "MORTALITY"),
    ("sensorineural hearing loss", "HEARING_LOSS"),
    ("neurological sequelae", "NEUROLOGICAL_SEQUELAE"),
    ("invasive meningococcal disease", "MENINGITIS_INCIDENCE"),
    ("serum bactericidal antibody", "IMMUNOGENICITY"),
    ("nasopharyngeal carriage", "CARRIAGE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_meningitis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in MENINGITIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"treatment", "vaccine", "mortality", "sequelae"}


# --- registry wiring ---

def test_meningitis_registered():
    assert "meningitis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["meningitis"]
    assert e["detection_function"] is detect_meningitis_subspecialty
    assert e["normalizer"] is normalize_meningitis_endpoint
    assert set(e["subspecialties"]) == {"treatment", "vaccine", "mortality", "sequelae"}


def test_detect_specialty_routes_to_meningitis():
    spec, sub, _ = detect_specialty(
        "ceftriaxone versus chloramphenicol for culture-confirmed bacterial "
        "meningitis; CSF sterilisation and clinical cure with lumbar puncture "
        "follow-up")
    assert spec == "meningitis" and sub == "treatment"


def test_meningitis_vaccine_routes():
    spec, sub, _ = detect_specialty(
        "meningococcal A conjugate vaccine (MenAfriVac) versus polysaccharide "
        "vaccine; vaccine efficacy against meningococcal disease and serum "
        "bactericidal antibody (SBA) seroconversion")
    assert spec == "meningitis" and sub == "vaccine"


def test_meningitis_does_not_break_hiv_malaria_typhoid_or_cardio():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "azithromycin versus ciprofloxacin for blood-culture-confirmed typhoid "
        "fever; fever clearance time in enteric fever")[0] == "typhoid"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_clinical_cure_2x2():
    t = ("Clinical cure was achieved by 142/150 (94.7%) in the ceftriaxone group "
         "and 120/148 (81.1%) in the chloramphenicol group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "CLINICAL_CURE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"ceftriaxone", "chloramphenicol"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (142, 150)


def test_mortality_2x2():
    t = ("Mortality occurred in 18/120 (15.0%) in the dexamethasone group versus "
         "30/118 (25.4%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "MORTALITY"


def test_hearing_loss_2x2():
    t = ("Hearing loss was reported in 9/100 (9.0%) in the dexamethasone group "
         "and 20/102 (19.6%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "HEARING_LOSS"


def test_time_to_recovery_continuous_poolable():
    r = extract_continuous("mean time to recovery 92 ± 30 hours in the ceftriaxone arm")
    assert r and r[0]["endpoint"] == "TIME_TO_RECOVERY" and r[0]["poolable"] is True


def test_immunogenicity_is_lognormal():
    r = extract_continuous("mean serum bactericidal antibody GMT 1850 ± 420 in the MenAfriVac arm")
    assert r and r[0]["endpoint"] == "IMMUNOGENICITY" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
