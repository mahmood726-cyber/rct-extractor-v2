"""
Tests for the heart/lung-transplant specialty profile, registry wiring, and
arm-level extraction. Includes a check that thoracic-organ transplant routes away
from kidney/liver transplant (shared immunosuppression / rejection vocabulary).
"""
import pytest

from rct_extractor._engine.specialties.heart_lung_transplant import (
    HEART_LUNG_TRANSPLANT_ENDPOINTS, detect_heart_lung_transplant_subspecialty,
    normalize_heart_lung_transplant_endpoint, get_heart_lung_transplant_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.heart_lung_transplant_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("everolimus versus mycophenolate in heart transplant recipients; acute cellular "
     "rejection and antibody-mediated rejection on endomyocardial biopsy.", "rejection"),
    ("primary graft dysfunction, cardiac allograft vasculopathy and chronic lung "
     "allograft dysfunction (bronchiolitis obliterans) after thoracic transplantation.", "graft"),
    ("estimated glomerular filtration rate and serum creatinine at 12 months after "
     "heart transplantation (calcineurin-inhibitor nephrotoxicity).", "function"),
    ("patient survival, CMV infection and post-transplant lymphoproliferative disorder "
     "after lung transplantation.", "complications"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_heart_lung_transplant_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("acute cellular rejection", "ACUTE_REJECTION"),
    ("primary graft dysfunction", "PRIMARY_GRAFT_DYSFUNCTION"),
    ("cardiac allograft vasculopathy", "CARDIAC_ALLOGRAFT_VASCULOPATHY"),
    ("chronic lung allograft dysfunction", "CHRONIC_LUNG_ALLOGRAFT_DYSFUNCTION"),
    ("bronchiolitis obliterans syndrome", "CHRONIC_LUNG_ALLOGRAFT_DYSFUNCTION"),
    ("graft loss", "GRAFT_LOSS"),
    ("estimated glomerular filtration rate", "EGFR"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_heart_lung_transplant_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"rejection", "graft", "function", "complications"}
    for name, info in HEART_LUNG_TRANSPLANT_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_heart_lung_transplant_registered():
    assert "heart_lung_transplant" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["heart_lung_transplant"]
    assert e["detection_function"] is detect_heart_lung_transplant_subspecialty
    assert e["normalizer"] is normalize_heart_lung_transplant_endpoint
    assert set(e["subspecialties"]) == {"rejection", "graft", "function", "complications"}


def test_detect_specialty_routes_to_heart_lung_transplant():
    spec, sub, _ = detect_specialty(
        "everolimus versus tacrolimus in heart transplant recipients; acute cellular "
        "rejection, cardiac allograft vasculopathy and graft loss at 12 months")
    assert spec == "heart_lung_transplant" and sub in {"rejection", "graft"}


def test_heart_lung_vs_kidney_transplant_disambiguation():
    # thoracic transplant (CAV/PGD/ISHLT) -> heart_lung_transplant, not kidney
    assert detect_specialty(
        "everolimus after lung transplantation; chronic lung allograft dysfunction, "
        "bronchiolitis obliterans syndrome and primary graft dysfunction")[0] == "heart_lung_transplant"
    # kidney transplant (renal allograft/DGF) -> stays kidney_transplant
    if "kidney_transplant" in SPECIALTY_REGISTRY:
        assert detect_specialty(
            "mycophenolate versus azathioprine in renal allograft recipients; "
            "death-censored graft loss and delayed graft function")[0] == "kidney_transplant"


def test_heart_lung_transplant_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_acute_rejection_2x2():
    t = ("Acute cellular rejection occurred in 28/160 (17.5%) of everolimus recipients "
         "and 45/160 (28.1%) of ciclosporin recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "ACUTE_REJECTION"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"everolimus", "ciclosporin"}


def test_cav_2x2():
    t = ("Cardiac allograft vasculopathy occurred in 15/140 (10.7%) of everolimus "
         "patients and 30/140 (21.4%) of mycophenolate patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "CARDIAC_ALLOGRAFT_VASCULOPATHY"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"everolimus", "mycophenolate"}


def test_egfr_continuous_poolable():
    r = extract_continuous("the estimated glomerular filtration rate was 58.7 ± 19.4 mL/min "
                           "in the everolimus arm")
    assert r and r[0]["endpoint"] == "EGFR" and r[0]["poolable"] is True
