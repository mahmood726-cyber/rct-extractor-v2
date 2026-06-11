"""
Tests for the obesity / weight-management specialty profile, registry wiring,
and arm-level extraction. Mirrors the diabetes / dyslipidaemia tests, with
explicit checks that obesity (weight-centric) and diabetes (glycaemic) route
correctly despite a shared incretin drug vocabulary.
"""
import pytest

from rct_extractor._engine.specialties.obesity import (
    OBESITY_ENDPOINTS, detect_obesity_subspecialty,
    normalize_obesity_endpoint, get_obesity_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.obesity_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("semaglutide for weight management in adults with obesity; percent change in "
     "body weight and the proportion achieving 10% weight loss.", "weight_loss"),
    ("change in waist circumference and total fat mass measured by DXA after "
     "lifestyle intervention for obesity.", "body_composition"),
    ("gastrointestinal adverse events including nausea, vomiting and diarrhoea, and "
     "treatment discontinuation with tirzepatide.", "safety"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_obesity_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("percent change in body weight", "BODY_WEIGHT_PCT_CHANGE"),
    ("change in body mass index", "BMI_CHANGE"),
    ("waist circumference reduction", "WAIST_CIRCUMFERENCE"),
    ("fat mass", "FAT_MASS"),
    ("nausea", "GI_ADVERSE_EVENTS"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_obesity_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"weight_loss", "body_composition", "cardiometabolic", "safety"}
    for name, info in OBESITY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_obesity_registered():
    assert "obesity" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["obesity"]
    assert e["detection_function"] is detect_obesity_subspecialty
    assert e["normalizer"] is normalize_obesity_endpoint
    assert set(e["subspecialties"]) == {"weight_loss", "body_composition",
                                        "cardiometabolic", "safety"}


def test_detect_specialty_routes_to_obesity():
    spec, sub, _ = detect_specialty(
        "Once-weekly semaglutide for weight management in adults with obesity or "
        "overweight; percent change in body weight, the proportion achieving 10% "
        "weight loss, and waist circumference reduction")
    assert spec == "obesity" and sub == "weight_loss"


def test_obesity_vs_diabetes_disambiguation():
    # weight-centric obesity trial (shared drug) -> obesity
    assert detect_specialty(
        "tirzepatide versus placebo for chronic weight management in adults with "
        "obesity; mean percent body weight change and >=15% weight loss")[0] == "obesity"
    # glycaemic-centric T2DM trial (shared drug) -> diabetes
    assert detect_specialty(
        "semaglutide versus placebo in type 2 diabetes; HbA1c reduction and fasting "
        "plasma glucose at 26 weeks")[0] == "diabetes"


def test_obesity_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"


# --- arm-level extraction ---

def test_weight_loss_10pct_2x2():
    t = ("At least 10% weight loss was achieved in 419/655 (64.0%) of semaglutide "
         "recipients and 65/655 (10.0%) of placebo recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "WEIGHT_LOSS_10PCT"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"semaglutide", "placebo"}


def test_body_weight_continuous_poolable():
    r = extract_continuous("the mean change in body weight was -14.9 ± 6.2 % in the "
                           "semaglutide arm")
    assert r and r[0]["endpoint"] == "BODY_WEIGHT_PCT_CHANGE" and r[0]["poolable"] is True


def test_waist_circumference_continuous_poolable():
    r = extract_continuous("waist circumference decreased by 13.5 ± 7.1 cm in the "
                           "tirzepatide group")
    assert r and r[0]["endpoint"] == "WAIST_CIRCUMFERENCE" and r[0]["poolable"] is True
