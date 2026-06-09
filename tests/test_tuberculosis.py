"""
Tests for the tuberculosis specialty profile, registry wiring, and arm-level
extraction. Mirrors the HIV and malaria tests.
"""
import pytest

from rct_extractor._engine.specialties.tuberculosis import (
    TUBERCULOSIS_ENDPOINTS, detect_tuberculosis_subspecialty,
    normalize_tuberculosis_endpoint, get_tuberculosis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.tuberculosis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("4-month rifapentine-moxifloxacin regimen vs standard 6-month HRZE for "
     "drug-susceptible pulmonary tuberculosis; 2-month sputum culture conversion "
     "and relapse.", "treatment"),
    ("BPaLM vs the standard regimen for rifampicin-resistant MDR-TB; favourable "
     "outcome and acquired resistance with bedaquiline and pretomanid.", "drug_resistant"),
    ("M72/AS01E candidate tuberculosis vaccine vs placebo; prevention of active "
     "TB disease and vaccine efficacy over 3 years.", "prevention"),
    ("3HP weekly rifapentine plus isoniazid vs 6 months isoniazid for latent "
     "tuberculosis infection (LTBI); TB preventive therapy completion.", "latent"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_tuberculosis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("2-month sputum culture conversion", "CULTURE_CONVERSION"),
    ("time to culture conversion", "TIME_TO_CULTURE_CONVERSION"),
    ("treatment success", "TREATMENT_SUCCESS"),
    ("composite unfavourable outcome", "UNFAVORABLE_OUTCOME"),
    ("recurrent tuberculosis", "RELAPSE"),
    ("acquired drug resistance", "ACQUIRED_RESISTANCE"),
    ("incident tuberculosis", "TB_INCIDENCE"),
    ("vaccine efficacy", "VACCINE_EFFICACY"),
    ("preventive therapy completion", "TPT_COMPLETION"),
    ("drug-induced liver injury", "HEPATOTOXICITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_tuberculosis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in TUBERCULOSIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"treatment", "drug_resistant", "prevention", "latent"}


# --- registry wiring ---

def test_tuberculosis_registered():
    assert "tuberculosis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["tuberculosis"]
    assert e["detection_function"] is detect_tuberculosis_subspecialty
    assert e["normalizer"] is normalize_tuberculosis_endpoint
    assert set(e["subspecialties"]) == {"treatment", "drug_resistant", "prevention", "latent"}


def test_detect_specialty_routes_to_tuberculosis():
    spec, sub, _ = detect_specialty(
        "4-month rifapentine-moxifloxacin regimen for drug-susceptible pulmonary "
        "tuberculosis; 2-month sputum culture conversion and relapse")
    assert spec == "tuberculosis" and sub == "treatment"


def test_tuberculosis_does_not_break_malaria_hiv_or_cardio():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_culture_conversion_2x2():
    t = ("Two-month sputum culture conversion was achieved by 280/350 (80.0%) in "
         "the moxifloxacin group and 245/345 (71.0%) in the ethambutol group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "CULTURE_CONVERSION"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"moxifloxacin", "ethambutol"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (280, 350)


def test_treatment_success_2x2():
    t = ("Favourable outcome occurred in 180/200 (90.0%) in the BPaLM group versus "
         "150/195 (76.9%) in the standard regimen group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "TREATMENT_SUCCESS"


def test_tpt_completion_2x2():
    t = ("Treatment completion was 165/180 (91.7%) in the 3HP group and 120/175 "
         "(68.6%) in the 6H group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "TPT_COMPLETION"


def test_relapse_2x2():
    t = ("Relapse occurred in 12/300 (4.0%) in the rifapentine group versus "
         "30/295 (10.2%) in the rifampicin group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "RELAPSE"


def test_tb_arm_level_is_binary_only():
    # TB poolable arm-level data is binary 2x2; time-to-event pools as an HR via
    # the core engine, so the continuous extractor yields nothing here.
    assert extract_continuous(
        "median time to culture conversion was 42 days in the bedaquiline arm") == []
