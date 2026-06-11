"""
Tests for the gestational-diabetes (GDM) specialty profile, registry wiring, and
arm-level extraction. Mirrors the cervical-cancer, endometriosis and menopause
tests. Includes British/American spelling-trap coverage (hypoglycaemia vs
hypoglycemia, glycaemic vs glycemic) per lessons.md.
"""
import pytest

from rct_extractor._engine.specialties.gestational_diabetes import (
    GESTATIONAL_DIABETES_ENDPOINTS, detect_gestational_diabetes_subspecialty,
    normalize_gestational_diabetes_endpoint, get_gestational_diabetes_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.gestational_diabetes_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of metformin versus insulin for gestational diabetes; glycaemic control, "
     "fasting plasma glucose, postprandial glucose and need for insulin.", "glycemic"),
    ("Treatment of GDM versus routine care; pre-eclampsia, caesarean section and "
     "induction of labour.", "maternal"),
    ("Metformin versus insulin in GDM; macrosomia, large-for-gestational-age and "
     "neonatal hypoglycaemia.", "neonatal"),
    ("One-step versus two-step screening with the oral glucose tolerance test "
     "(OGTT); diagnosis of gestational diabetes.", "screening"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_gestational_diabetes_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("glycaemic control", "GLYCEMIC_TARGET"),
    ("fasting plasma glucose", "FASTING_GLUCOSE"),
    ("postprandial glucose", "POSTPRANDIAL_GLUCOSE"),
    ("HbA1c", "HBA1C"),
    ("need for insulin", "INSULIN_REQUIREMENT"),
    ("pre-eclampsia", "PRE_ECLAMPSIA"),
    ("caesarean section", "CAESAREAN"),
    ("induction of labour", "INDUCTION_LABOUR"),
    ("macrosomia", "MACROSOMIA"),
    ("large-for-gestational-age", "LARGE_FOR_GESTATIONAL_AGE"),
    ("neonatal hypoglycaemia", "NEONATAL_HYPOGLYCAEMIA"),
    ("neonatal hypoglycemia", "NEONATAL_HYPOGLYCAEMIA"),
    ("shoulder dystocia", "SHOULDER_DYSTOCIA"),
    ("diagnosis of gestational diabetes", "GDM_DIAGNOSIS"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_gestational_diabetes_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"glycemic", "maternal", "neonatal", "screening"}
    for name, info in GESTATIONAL_DIABETES_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- British/American spelling traps (lessons.md a?e rule) ---

@pytest.mark.parametrize("text", [
    "neonatal hypoglycaemia",   # British (hypoglyc-AE-mia, both vowels)
    "neonatal hypoglycemia",    # American
])
def test_neonatal_hypoglycaemia_both_spellings_route(text):
    # NEONATAL_PATTERNS endpoint regex must match BOTH spellings
    import re
    pats = get_gestational_diabetes_endpoint_patterns("neonatal")
    assert any(re.search(p, text) for p, ep in pats if ep == "NEONATAL_HYPOGLYCAEMIA")


# --- registry wiring ---

def test_gestational_diabetes_registered():
    assert "gestational_diabetes" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["gestational_diabetes"]
    assert e["detection_function"] is detect_gestational_diabetes_subspecialty
    assert e["normalizer"] is normalize_gestational_diabetes_endpoint
    assert set(e["subspecialties"]) == {"glycemic", "maternal", "neonatal", "screening"}


def test_detect_specialty_routes_gdm_not_diabetes():
    # GDM must win over the general diabetes profile when pregnancy context present
    spec, sub, _ = detect_specialty(
        "randomized trial of metformin versus insulin for gestational diabetes "
        "mellitus (GDM); macrosomia, large-for-gestational-age and neonatal "
        "hypoglycaemia")
    assert spec == "gestational_diabetes"
    # American spelling must route identically
    spec2, _, _ = detect_specialty(
        "metformin versus insulin for GDM; macrosomia and neonatal hypoglycemia")
    assert spec2 == "gestational_diabetes"


def test_general_diabetes_still_routes_to_diabetes():
    assert detect_specialty(
        "empagliflozin versus placebo in type 2 diabetes; HbA1c, fasting glucose "
        "and cardiovascular death")[0] == "diabetes"
    assert detect_specialty(
        "insulin glargine versus NPH in type 1 diabetes; severe hypoglycaemia")[0] \
        == "diabetes"


def test_gdm_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "magnesium sulphate versus placebo for severe pre-eclampsia; eclampsia and "
        "maternal mortality")[0] == "maternal_neonatal"


# --- arm-level extraction ---

def test_macrosomia_2x2():
    t = ("Macrosomia occurred in 12/200 (6.0%) in the metformin group and 28/198 "
         "(14.1%) in the insulin group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "MACROSOMIA"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"metformin", "insulin"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (12, 200)


def test_neonatal_hypoglycaemia_2x2():
    t = ("Neonatal hypoglycaemia occurred in 15/200 (7.5%) in the metformin group "
         "and 30/198 (15.2%) in the insulin group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "NEONATAL_HYPOGLYCAEMIA"


def test_fasting_glucose_continuous():
    r = extract_continuous("Mean fasting plasma glucose was 4.8 ± 0.6 in the "
                           "metformin group and 5.1 ± 0.7 in the insulin group")
    assert r and r[0]["endpoint"] == "FASTING_GLUCOSE"
    assert r[0]["stat"] == "mean_sd" and r[0]["poolable"] is True
