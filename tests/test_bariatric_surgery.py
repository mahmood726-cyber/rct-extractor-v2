"""
Tests for the bariatric / metabolic surgery specialty profile, registry wiring,
and arm-level extraction. Includes a check that bariatric SURGERY routes away
from the pharmacological obesity specialty.
"""
import pytest

from rct_extractor._engine.specialties.bariatric_surgery import (
    BARIATRIC_SURGERY_ENDPOINTS, detect_bariatric_surgery_subspecialty,
    normalize_bariatric_surgery_endpoint, get_bariatric_surgery_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.bariatric_surgery_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Roux-en-Y gastric bypass versus sleeve gastrectomy; percent total weight loss "
     "and percent excess weight loss at 5 years.", "weight"),
    ("gastric bypass versus medical therapy; type 2 diabetes remission and glycated "
     "haemoglobin.", "metabolic"),
    ("sleeve gastrectomy versus gastric bypass; postoperative complications, "
     "anastomotic leak and reoperation.", "complications"),
    ("bariatric surgery; iron-deficiency anaemia and micronutrient deficiency at "
     "2 years.", "nutritional"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_bariatric_surgery_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("percent total weight loss", "TOTAL_WEIGHT_LOSS"),
    ("percent excess weight loss", "EXCESS_WEIGHT_LOSS"),
    ("type 2 diabetes remission", "DIABETES_REMISSION"),
    ("anastomotic leak", "ANASTOMOTIC_LEAK"),
    ("reoperation", "REOPERATION"),
    ("iron-deficiency anaemia", "ANAEMIA"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_bariatric_surgery_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"weight", "metabolic", "complications", "nutritional"}
    for name, info in BARIATRIC_SURGERY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_bariatric_surgery_registered():
    assert "bariatric_surgery" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["bariatric_surgery"]
    assert e["detection_function"] is detect_bariatric_surgery_subspecialty
    assert e["normalizer"] is normalize_bariatric_surgery_endpoint
    assert set(e["subspecialties"]) == {"weight", "metabolic", "complications", "nutritional"}


def test_detect_specialty_routes_to_bariatric_surgery():
    spec, sub, _ = detect_specialty(
        "Roux-en-Y gastric bypass versus sleeve gastrectomy in bariatric surgery; "
        "percent total weight loss, type 2 diabetes remission and anastomotic leak")
    assert spec == "bariatric_surgery"


def test_bariatric_vs_obesity_disambiguation():
    # bariatric SURGERY -> bariatric_surgery, not pharmacological obesity
    assert detect_specialty(
        "sleeve gastrectomy versus Roux-en-Y gastric bypass for weight-loss surgery; "
        "percent excess weight loss and diabetes remission")[0] == "bariatric_surgery"
    # pharmacological obesity trial -> stays obesity
    if "obesity" in SPECIALTY_REGISTRY:
        assert detect_specialty(
            "semaglutide 2.4 mg versus placebo for weight management in obesity; "
            "body weight reduction and waist circumference")[0] == "obesity"


def test_bariatric_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_diabetes_remission_2x2():
    t = ("Type 2 diabetes remission occurred in 75/100 (75.0%) of gastric bypass patients "
         "and 30/100 (30.0%) of medical therapy patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "DIABETES_REMISSION"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"gastric-bypass", "medical-therapy"}


def test_anastomotic_leak_2x2():
    t = ("Anastomotic leak occurred in 6/300 (2.0%) of gastric bypass patients and "
         "3/300 (1.0%) of sleeve gastrectomy patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ANASTOMOTIC_LEAK"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"gastric-bypass", "sleeve-gastrectomy"}


def test_twl_continuous_poolable():
    r = extract_continuous("the percent total weight loss was 28.5 ± 7.4 in the sleeve "
                           "gastrectomy arm")
    assert r and r[0]["endpoint"] == "TOTAL_WEIGHT_LOSS" and r[0]["poolable"] is True
