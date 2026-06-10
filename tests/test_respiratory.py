"""
Tests for the respiratory specialty profile (COPD / asthma / ILD), registry
wiring, and arm-level extraction. Mirrors the hepatitis / HIV / malaria tests.
"""
import pytest

from rct_extractor._engine.specialties.respiratory import (
    RESPIRATORY_ENDPOINTS, detect_respiratory_subspecialty, normalize_respiratory_endpoint,
    get_respiratory_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.respiratory_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Tiotropium vs placebo in chronic obstructive pulmonary disease (COPD); rate of "
     "moderate or severe exacerbations and trough FEV1 over 52 weeks.", "copd"),
    ("Benralizumab vs placebo in severe eosinophilic asthma; annualised asthma "
     "exacerbation rate and ACQ-6 asthma control questionnaire score.", "asthma"),
    ("Nintedanib vs placebo in idiopathic pulmonary fibrosis (IPF); annual rate of "
     "decline in forced vital capacity (FVC) over 52 weeks.", "ild"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_respiratory_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("rate of moderate or severe exacerbations", "COPD_EXACERBATION"),
    ("trough FEV1", "TROUGH_FEV1"),
    ("St George's Respiratory Questionnaire", "SGRQ"),
    ("asthma control questionnaire", "ACQ"),
    ("forced vital capacity", "FVC"),
    ("annual rate of decline in FVC", "FVC_DECLINE"),
    ("fractional exhaled nitric oxide", "FENO"),
    ("6-minute walk distance", "SIX_MIN_WALK"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_respiratory_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"copd", "asthma", "ild", "general_respiratory"}
    for name, info in RESPIRATORY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_respiratory_registered():
    assert "respiratory" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["respiratory"]
    assert e["detection_function"] is detect_respiratory_subspecialty
    assert e["normalizer"] is normalize_respiratory_endpoint
    assert set(e["subspecialties"]) == {"copd", "asthma", "ild", "general_respiratory"}


def test_detect_specialty_routes_to_respiratory():
    spec, sub, _ = detect_specialty(
        "Triple therapy (fluticasone furoate-umeclidinium-vilanterol) vs dual therapy in "
        "COPD; rate of moderate or severe exacerbations and trough FEV1.")
    assert spec == "respiratory" and sub == "copd"

    spec2, sub2, _ = detect_specialty(
        "Mepolizumab in severe eosinophilic asthma; annual asthma exacerbation rate, "
        "blood eosinophil count, and ACQ-5 score.")
    assert spec2 == "respiratory" and sub2 == "asthma"


def test_respiratory_does_not_break_neighbors():
    assert detect_specialty("dolutegravir-based antiretroviral therapy; week 48 viral "
                            "suppression and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty("artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty("sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_copd_exacerbation_2x2():
    t = ("A moderate or severe COPD exacerbation occurred in 120/400 (30.0%) in the "
         "tiotropium group and 160/410 (39.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "COPD_EXACERBATION"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"tiotropium", "placebo"}


def test_fev1_continuous_poolable():
    r = extract_continuous("mean change in trough FEV1 was 120 ± 40 mL in the umeclidinium arm")
    assert r and r[0]["endpoint"] == "TROUGH_FEV1" and r[0]["poolable"] is True


def test_feno_is_lognormal():
    r = extract_continuous("mean FeNO was 25 ± 8 ppb in the dupilumab arm")
    assert r and r[0]["endpoint"] == "FENO" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
