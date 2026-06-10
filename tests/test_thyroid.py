"""
Tests for the thyroid-disorders specialty profile, registry wiring, and
arm-level extraction. Mirrors the diabetes / obesity tests.
"""
import pytest

from rct_extractor._engine.specialties.thyroid import (
    THYROID_ENDPOINTS, detect_thyroid_subspecialty,
    normalize_thyroid_endpoint, get_thyroid_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.thyroid_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("levothyroxine for hypothyroidism; TSH normalisation and thyroid-related "
     "quality of life on the ThyPRO score.", "hypothyroidism"),
    ("methimazole versus radioactive iodine for Graves disease; remission and "
     "relapse of hyperthyroidism after 18 months of antithyroid therapy.", "hyperthyroidism"),
    ("change in serum free thyroxine and free triiodothyronine and total "
     "thyroxine levels measured at week 12.", "thyroid_function"),
    ("thyroid autoimmunity in pregnancy; miscarriage, pregnancy loss and preterm "
     "birth were the primary outcomes.", "outcomes"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_thyroid_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("thyroid-stimulating hormone", "TSH_LEVEL"),
    ("free thyroxine", "FT4_LEVEL"),
    ("free triiodothyronine", "FT3_LEVEL"),
    ("tsh normalization", "TSH_NORMALIZATION"),
    ("remission", "REMISSION"),
    ("relapse", "RELAPSE"),
    ("miscarriage", "PREGNANCY_LOSS"),
    ("preterm birth", "PRETERM_BIRTH"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_thyroid_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"hypothyroidism", "hyperthyroidism", "thyroid_function", "outcomes"}
    for name, info in THYROID_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_thyroid_registered():
    assert "thyroid" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["thyroid"]
    assert e["detection_function"] is detect_thyroid_subspecialty
    assert e["normalizer"] is normalize_thyroid_endpoint
    assert set(e["subspecialties"]) == {"hypothyroidism", "hyperthyroidism",
                                        "thyroid_function", "outcomes"}


def test_detect_specialty_routes_to_thyroid():
    spec, sub, _ = detect_specialty(
        "levothyroxine versus placebo for subclinical hypothyroidism; TSH "
        "normalisation and thyroid-related quality of life")
    assert spec == "thyroid" and sub == "hypothyroidism"


def test_thyroid_hyperthyroid_route():
    spec, sub, _ = detect_specialty(
        "methimazole versus radioactive iodine for Graves disease and "
        "thyrotoxicosis; remission and relapse of hyperthyroidism")
    assert spec == "thyroid" and sub == "hyperthyroidism"


def test_thyroid_does_not_break_siblings():
    assert detect_specialty(
        "empagliflozin versus placebo in type 2 diabetes; HbA1c reduction and "
        "fasting plasma glucose at 24 weeks")[0] == "diabetes"
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"


# --- arm-level extraction ---

def test_tsh_normalization_2x2():
    t = ("TSH normalisation was achieved in 120/150 (80.0%) of levothyroxine "
         "recipients and 30/150 (20.0%) of placebo recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "TSH_NORMALIZATION"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"levothyroxine", "placebo"}


def test_remission_2x2():
    t = ("Remission was achieved in 84/150 (56.0%) of methimazole-treated patients "
         "and 60/150 (40.0%) of carbimazole-treated patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "REMISSION"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"methimazole", "carbimazole"}


def test_tsh_continuous_poolable():
    r = extract_continuous("the mean serum TSH decreased by 3.2 ± 1.4 mIU/L in the "
                           "levothyroxine arm")
    assert r and r[0]["endpoint"] == "TSH_LEVEL" and r[0]["poolable"] is True


def test_ft4_continuous_poolable():
    r = extract_continuous("free thyroxine increased by 5.1 ± 2.3 pmol/L in the "
                           "liothyronine group")
    assert r and r[0]["endpoint"] == "FT4_LEVEL" and r[0]["poolable"] is True
