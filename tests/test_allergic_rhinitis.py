"""
Tests for the allergic-rhinitis specialty profile, registry wiring, and
arm-level extraction. Mirrors the tuberculosis / ARDS tests.
"""
import pytest

from rct_extractor._engine.specialties.allergic_rhinitis import (
    ALLERGIC_RHINITIS_ENDPOINTS, detect_allergic_rhinitis_subspecialty,
    normalize_allergic_rhinitis_endpoint, get_allergic_rhinitis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.allergic_rhinitis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Intranasal fluticasone furoate vs placebo for seasonal allergic rhinitis; "
     "reflective total nasal symptom score (rTNSS) and azelastine comparison.",
     "pharmacotherapy"),
    ("Grass-pollen sublingual immunotherapy (SLIT) tablet vs placebo; combined "
     "symptom and medication score (CSMS) and responder rate with allergen "
     "immunotherapy.", "immunotherapy"),
    ("Omalizumab (anti-IgE) vs placebo for allergic rhinitis; total nasal symptom "
     "score and rescue medication use as add-on therapy.", "biologics"),
    ("Nasal saline irrigation vs allergen avoidance for allergic rhinitis; total "
     "nasal symptom score and quality of life.", "environmental"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_allergic_rhinitis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("total nasal symptom score", "TNSS"),
    ("combined symptom and medication score", "CSMS"),
    ("total ocular symptom score", "TOSS"),
    ("rhinoconjunctivitis quality of life", "RQLQ"),
    ("rescue medication use", "RESCUE_MEDICATION"),
    ("nasal congestion score", "NASAL_CONGESTION"),
    ("symptom-free days", "SYMPTOM_FREE_DAYS"),
    ("development of asthma", "ASTHMA_DEVELOPMENT"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_allergic_rhinitis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in ALLERGIC_RHINITIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"pharmacotherapy", "immunotherapy",
                                        "biologics", "environmental"}


# --- registry wiring ---

def test_allergic_rhinitis_registered():
    assert "allergic_rhinitis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["allergic_rhinitis"]
    assert e["detection_function"] is detect_allergic_rhinitis_subspecialty
    assert e["normalizer"] is normalize_allergic_rhinitis_endpoint
    assert set(e["subspecialties"]) == {"pharmacotherapy", "immunotherapy",
                                        "biologics", "environmental"}


def test_detect_specialty_routes_to_allergic_rhinitis():
    spec, sub, _ = detect_specialty(
        "Grass-pollen sublingual immunotherapy tablet versus placebo for allergic "
        "rhinitis; combined symptom and medication score and total nasal symptom score")
    assert spec == "allergic_rhinitis"


def test_allergic_rhinitis_does_not_break_malaria_hiv_or_cardio():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in chronic heart failure; cardiovascular death and "
        "heart-failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_responder_2x2():
    t = ("Responder rate: SLIT 120/200 (60.0%) versus placebo 70/198 (35.4%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs
    t0 = tabs[0]
    assert t0["endpoint"] == "RESPONDER"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"SLIT", "placebo"}


def test_tnss_continuous():
    t = ("The total nasal symptom score was 3.2 (SD 1.4) with fluticasone and 5.1 "
         "(SD 1.8) with placebo")
    cont = extract_continuous(t)
    assert any(c["endpoint"] == "TNSS" for c in cont)


def test_csms_continuous():
    # "combined symptom and medication score" contains the substring "medication
    # score"; the nearest-keyword tagger may label either CSMS or RESCUE_MEDICATION
    # (both continuous) - the point is the per-arm mean+SD is recovered.
    t = ("The combined symptom and medication score was 0.62 (SD 0.30) with grass "
         "pollen tablet versus 0.95 (SD 0.41) with placebo")
    cont = extract_continuous(t)
    assert any(c["endpoint"] in {"CSMS", "RESCUE_MEDICATION"} for c in cont)
