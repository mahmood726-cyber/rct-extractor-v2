"""
Tests for the type-2 diabetes specialty profile, registry wiring, and arm-level
extraction. Mirrors the typhoid, HIV and malaria tests.
"""
import pytest

from src.specialties.diabetes import (
    DIABETES_ENDPOINTS, detect_diabetes_subspecialty, normalize_diabetes_endpoint,
    get_diabetes_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.diabetes_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of semaglutide vs sitagliptin in type 2 diabetes; change in HbA1c and "
     "fasting plasma glucose at week 52, with body-weight reduction.", "glycemic"),
    ("Cardiovascular outcome trial of empagliflozin vs placebo; 3-point MACE, "
     "cardiovascular death and hospitalisation for heart failure.", "cardiorenal"),
    ("Insulin glargine vs insulin degludec in type 2 diabetes; severe hypoglycaemia "
     "and nocturnal hypoglycaemia event rates.", "hypoglycemia"),
    ("Intensive glucose control and diabetic retinopathy progression, diabetic "
     "nephropathy and peripheral neuropathy over five years.", "complications"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_diabetes_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("change in HbA1c", "HBA1C_REDUCTION"),
    ("fasting plasma glucose", "FASTING_PLASMA_GLUCOSE"),
    ("major adverse cardiovascular events", "MACE"),
    ("hospitalisation for heart failure", "HF_HOSPITALIZATION"),
    ("end-stage kidney disease", "ESKD"),
    ("urine albumin-to-creatinine ratio", "UACR"),
    ("severe hypoglycaemia", "SEVERE_HYPOGLYCEMIA"),
    ("diabetic retinopathy", "RETINOPATHY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_diabetes_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in DIABETES_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"glycemic", "cardiorenal", "hypoglycemia", "complications"}


# --- registry wiring ---

def test_diabetes_registered():
    assert "diabetes" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["diabetes"]
    assert e["detection_function"] is detect_diabetes_subspecialty
    assert e["normalizer"] is normalize_diabetes_endpoint
    assert set(e["subspecialties"]) == {"glycemic", "cardiorenal", "hypoglycemia", "complications"}


def test_detect_specialty_routes_to_diabetes():
    spec, sub, _ = detect_specialty(
        "semaglutide versus sitagliptin in adults with type 2 diabetes; change in "
        "HbA1c and fasting plasma glucose with body-weight reduction at week 52")
    assert spec == "diabetes" and sub == "glycemic"


def test_diabetes_cvot_routes():
    spec, sub, _ = detect_specialty(
        "empagliflozin versus placebo in type 2 diabetes (cardiovascular outcome "
        "trial); 3-point MACE, cardiovascular death and hospitalisation for heart "
        "failure, plus a renal composite outcome")
    assert spec == "diabetes" and sub == "cardiorenal"


def test_diabetes_does_not_break_hiv_malaria_or_cardio():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_hba1c_target_2x2():
    t = ("An HbA1c target <7% was achieved by 142/300 (47.3%) in the semaglutide "
         "group and 90/300 (30.0%) in the sitagliptin group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "HBA1C_TARGET"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"semaglutide", "sitagliptin"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (142, 300)


def test_mace_2x2():
    t = ("A major adverse cardiovascular event occurred in 490/3500 (14.0%) in the "
         "empagliflozin group versus 282/1750 (16.1%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "MACE"


def test_hba1c_change_continuous_poolable():
    r = extract_continuous("mean change in HbA1c was -1.5 ± 0.3% in the semaglutide arm")
    assert r and r[0]["endpoint"] == "HBA1C_REDUCTION" and r[0]["poolable"] is True


def test_uacr_is_lognormal():
    r = extract_continuous("mean urine albumin-to-creatinine ratio 320 ± 80 mg/g in the placebo arm")
    assert r and r[0]["endpoint"] == "UACR" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
