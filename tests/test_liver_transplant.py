"""
Tests for the liver-transplant specialty profile, registry wiring, and arm-level
extraction. Includes a check that liver transplant routes away from the
kidney-transplant specialty (shared immunosuppression / rejection vocabulary).
"""
import pytest

from rct_extractor._engine.specialties.liver_transplant import (
    LIVER_TRANSPLANT_ENDPOINTS, detect_liver_transplant_subspecialty,
    normalize_liver_transplant_endpoint, get_liver_transplant_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.liver_transplant_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("tacrolimus versus ciclosporin in liver transplant recipients; biopsy-proven "
     "acute rejection and t-cell-mediated rejection at 12 months.", "rejection"),
    ("everolimus versus standard immunosuppression; graft loss, retransplantation, "
     "hepatic artery thrombosis and biliary stricture after liver transplantation.", "graft"),
    ("estimated glomerular filtration rate and serum creatinine at 24 months after "
     "liver transplantation (calcineurin-inhibitor nephrotoxicity).", "function"),
    ("patient survival, hepatocellular carcinoma recurrence and CMV infection after "
     "liver transplantation.", "complications"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_liver_transplant_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("biopsy-proven acute rejection", "ACUTE_REJECTION"),
    ("hepatic artery thrombosis", "HEPATIC_ARTERY_THROMBOSIS"),
    ("biliary stricture", "BILIARY_COMPLICATION"),
    ("graft loss", "GRAFT_LOSS"),
    ("hepatocellular carcinoma recurrence", "HCC_RECURRENCE"),
    ("estimated glomerular filtration rate", "EGFR"),
    ("primary non-function", "PRIMARY_NONFUNCTION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_liver_transplant_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"rejection", "graft", "function", "complications"}
    for name, info in LIVER_TRANSPLANT_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_liver_transplant_registered():
    assert "liver_transplant" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["liver_transplant"]
    assert e["detection_function"] is detect_liver_transplant_subspecialty
    assert e["normalizer"] is normalize_liver_transplant_endpoint
    assert set(e["subspecialties"]) == {"rejection", "graft", "function", "complications"}


def test_detect_specialty_routes_to_liver_transplant():
    spec, sub, _ = detect_specialty(
        "tacrolimus versus everolimus in liver transplant recipients; biopsy-proven "
        "acute rejection, graft loss and hepatic artery thrombosis at 12 months")
    assert spec == "liver_transplant" and sub in {"rejection", "graft"}


def test_liver_vs_kidney_transplant_disambiguation():
    # liver transplant (hepatic/biliary/MELD) -> liver_transplant, not kidney_transplant
    assert detect_specialty(
        "everolimus versus tacrolimus after orthotopic liver transplantation; hepatic "
        "artery thrombosis, biliary stricture and MELD score")[0] == "liver_transplant"
    # kidney transplant (renal allograft/DGF) -> stays kidney_transplant
    if "kidney_transplant" in SPECIALTY_REGISTRY:
        assert detect_specialty(
            "mycophenolate versus azathioprine in renal allograft recipients; "
            "death-censored graft loss and delayed graft function")[0] == "kidney_transplant"


def test_liver_transplant_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_acute_rejection_2x2():
    t = ("Biopsy-proven acute rejection occurred in 25/150 (16.7%) of everolimus "
         "recipients and 40/150 (26.7%) of tacrolimus recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "ACUTE_REJECTION"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"everolimus", "tacrolimus"}


def test_hcc_recurrence_2x2():
    t = ("Hepatocellular carcinoma recurrence occurred in 10/120 (8.3%) of sirolimus "
         "patients and 22/120 (18.3%) of tacrolimus patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "HCC_RECURRENCE"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"sirolimus", "tacrolimus"}


def test_egfr_continuous_poolable():
    r = extract_continuous("the estimated glomerular filtration rate was 62.4 ± 17.1 mL/min "
                           "in the everolimus arm")
    assert r and r[0]["endpoint"] == "EGFR" and r[0]["poolable"] is True
