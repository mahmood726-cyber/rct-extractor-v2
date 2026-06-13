"""
Tests for the bronchiectasis (non-CF) specialty profile, registry wiring, and
arm-level extraction. Includes a check that bronchiectasis routes away from the
general respiratory specialty (asthma/COPD).
"""
import pytest

from rct_extractor._engine.specialties.bronchiectasis import (
    BRONCHIECTASIS_ENDPOINTS, detect_bronchiectasis_subspecialty,
    normalize_bronchiectasis_endpoint, get_bronchiectasis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.bronchiectasis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("brensocatib in bronchiectasis; annual exacerbation rate and time to first "
     "pulmonary exacerbation.", "exacerbation"),
    ("inhaled colistin for bronchiectasis; Pseudomonas aeruginosa eradication and "
     "sputum bacterial load.", "microbiology"),
    ("azithromycin in bronchiectasis; percent predicted FEV1 and QOL-B respiratory "
     "symptoms score.", "function"),
    ("hypertonic saline in bronchiectasis; 24-hour sputum volume and Leicester Cough "
     "Questionnaire score.", "symptoms"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_bronchiectasis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("annual exacerbation rate", "EXACERBATION"),
    ("time to first exacerbation", "TIME_TO_EXACERBATION"),
    ("severe exacerbation", "SEVERE_EXACERBATION"),
    ("Pseudomonas aeruginosa eradication", "PSEUDOMONAS_ERADICATION"),
    ("QOL-B respiratory symptoms", "QUALITY_OF_LIFE"),
    ("24-hour sputum volume", "SPUTUM_VOLUME"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_bronchiectasis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"exacerbation", "microbiology", "function", "symptoms"}
    for name, info in BRONCHIECTASIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_bronchiectasis_registered():
    assert "bronchiectasis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["bronchiectasis"]
    assert e["detection_function"] is detect_bronchiectasis_subspecialty
    assert e["normalizer"] is normalize_bronchiectasis_endpoint
    assert set(e["subspecialties"]) == {"exacerbation", "microbiology", "function", "symptoms"}


def test_detect_specialty_routes_to_bronchiectasis():
    spec, sub, _ = detect_specialty(
        "brensocatib versus placebo in patients with bronchiectasis; annual exacerbation "
        "rate, time to first exacerbation and QOL-B respiratory symptoms")
    assert spec == "bronchiectasis"


def test_bronchiectasis_vs_respiratory_disambiguation():
    # bronchiectasis -> bronchiectasis, not respiratory
    assert detect_specialty(
        "inhaled colistin in non-CF bronchiectasis; annual exacerbation rate and "
        "Pseudomonas aeruginosa eradication")[0] == "bronchiectasis"
    # general asthma -> stays respiratory
    if "respiratory" in SPECIALTY_REGISTRY:
        assert detect_specialty(
            "budesonide/formoterol versus placebo in moderate asthma; ACQ-5 score, "
            "FEV1 and severe asthma exacerbations")[0] == "respiratory"


def test_bronchiectasis_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_severe_exacerbation_2x2():
    t = ("A severe exacerbation occurred in 30/200 (15.0%) of azithromycin patients and "
         "60/200 (30.0%) of placebo patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "SEVERE_EXACERBATION"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"azithromycin", "placebo"}


def test_pseudomonas_eradication_2x2():
    t = ("Pseudomonas aeruginosa eradication was achieved in 70/100 (70.0%) of colistin "
         "patients and 40/100 (40.0%) of placebo patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "PSEUDOMONAS_ERADICATION"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"colistin", "placebo"}


def test_qol_continuous_poolable():
    r = extract_continuous("the QOL-B respiratory symptoms score was 65.4 ± 18.2 in the "
                           "brensocatib arm")
    assert r and r[0]["endpoint"] == "QUALITY_OF_LIFE" and r[0]["poolable"] is True
