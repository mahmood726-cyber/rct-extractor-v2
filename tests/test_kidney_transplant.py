"""
Tests for the kidney-transplant specialty profile, registry wiring, and arm-level
extraction. Includes a check that transplant routes away from the general
nephrology specialty (shared renal-function vocabulary).
"""
import pytest

from rct_extractor._engine.specialties.kidney_transplant import (
    KIDNEY_TRANSPLANT_ENDPOINTS, detect_kidney_transplant_subspecialty,
    normalize_kidney_transplant_endpoint, get_kidney_transplant_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.kidney_transplant_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("tacrolimus versus ciclosporin in kidney transplant recipients; biopsy-proven "
     "acute rejection and antibody-mediated rejection at 12 months.", "rejection"),
    ("belatacept versus tacrolimus; death-censored graft loss, graft survival and "
     "delayed graft function in renal allograft recipients.", "graft"),
    ("estimated glomerular filtration rate and serum creatinine at 24 months after "
     "kidney transplantation.", "function"),
    ("CMV infection, BK viraemia, post-transplant lymphoproliferative disorder and "
     "new-onset diabetes after transplantation.", "complications"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_kidney_transplant_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("biopsy-proven acute rejection", "ACUTE_REJECTION"),
    ("antibody-mediated rejection", "ANTIBODY_MEDIATED_REJECTION"),
    ("delayed graft function", "DELAYED_GRAFT_FUNCTION"),
    ("graft loss", "GRAFT_LOSS"),
    ("estimated glomerular filtration rate", "EGFR"),
    ("cmv infection", "CMV_INFECTION"),
    ("bk viraemia", "BK_INFECTION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_kidney_transplant_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"rejection", "graft", "function", "complications"}
    for name, info in KIDNEY_TRANSPLANT_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_kidney_transplant_registered():
    assert "kidney_transplant" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["kidney_transplant"]
    assert e["detection_function"] is detect_kidney_transplant_subspecialty
    assert e["normalizer"] is normalize_kidney_transplant_endpoint
    assert set(e["subspecialties"]) == {"rejection", "graft", "function", "complications"}


def test_detect_specialty_routes_to_kidney_transplant():
    spec, sub, _ = detect_specialty(
        "tacrolimus versus belatacept in kidney transplant recipients; biopsy-proven "
        "acute rejection, graft loss and antibody-mediated rejection at 12 months")
    assert spec == "kidney_transplant" and sub == "rejection"


def test_transplant_vs_nephrology_disambiguation():
    # transplant (allograft/rejection/tacrolimus) -> kidney_transplant, not nephrology
    assert detect_specialty(
        "mycophenolate versus azathioprine in renal allograft recipients; "
        "death-censored graft loss and delayed graft function")[0] == "kidney_transplant"
    # general CKD progression (no transplant terms) -> stays nephrology
    if "nephrology" in SPECIALTY_REGISTRY:
        assert detect_specialty(
            "finerenone in chronic kidney disease; eGFR decline, doubling of serum "
            "creatinine and progression to end-stage kidney disease")[0] == "nephrology"


def test_kidney_transplant_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_acute_rejection_2x2():
    t = ("Biopsy-proven acute rejection occurred in 30/200 (15.0%) of belatacept "
         "recipients and 50/200 (25.0%) of ciclosporin recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "ACUTE_REJECTION"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"belatacept", "ciclosporin"}


def test_graft_loss_2x2():
    t = ("Graft loss occurred in 12/200 (6.0%) of tacrolimus-treated patients "
         "and 24/200 (12.0%) of sirolimus-treated patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "GRAFT_LOSS"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"tacrolimus", "sirolimus"}


def test_egfr_continuous_poolable():
    r = extract_continuous("the estimated glomerular filtration rate was 55.3 ± 18.2 mL/min "
                           "in the belatacept arm")
    assert r and r[0]["endpoint"] == "EGFR" and r[0]["poolable"] is True
