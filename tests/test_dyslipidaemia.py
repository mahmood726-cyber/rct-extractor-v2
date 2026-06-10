"""
Tests for the dyslipidaemia / lipid-lowering specialty profile, registry wiring,
and arm-level extraction. Mirrors the hypertension, diabetes and HIV tests.
"""
import pytest

from rct_extractor._engine.specialties.dyslipidaemia import (
    DYSLIPIDAEMIA_ENDPOINTS, detect_dyslipidaemia_subspecialty,
    normalize_dyslipidaemia_endpoint, get_dyslipidaemia_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.dyslipidaemia_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("rosuvastatin versus atorvastatin; reduction in LDL cholesterol, non-HDL "
     "cholesterol and apolipoprotein B at 12 weeks in mg/dL.", "lipid_lowering"),
    ("proportion of patients reaching the LDL target of <70 mg/dL; LDL goal "
     "attainment and target attainment were the primary endpoints.", "ldl_target"),
    ("evolocumab versus placebo; major adverse cardiovascular events, myocardial "
     "infarction, stroke and cardiovascular death over median follow-up.", "cv_events"),
    ("statin safety: new-onset diabetes, myalgia and muscle symptoms, and "
     "alanine aminotransferase elevation leading to discontinuation.", "safety"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_dyslipidaemia_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("reduction in ldl cholesterol", "LDL_REDUCTION"),
    ("non-hdl cholesterol", "NON_HDL_REDUCTION"),
    ("change in triglycerides", "TG_REDUCTION"),
    ("apolipoprotein b", "APOB_REDUCTION"),
    ("lipoprotein(a)", "LPA_REDUCTION"),
    ("ldl goal attainment", "LDL_GOAL_ATTAINMENT"),
    ("major adverse cardiovascular events", "MACE"),
    ("new-onset diabetes", "NEW_ONSET_DIABETES"),
    ("coronary revascularization", "REVASCULARIZATION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_dyslipidaemia_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in DYSLIPIDAEMIA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"lipid_lowering", "ldl_target", "cv_events", "safety"}


# --- registry wiring ---

def test_dyslipidaemia_registered():
    assert "dyslipidaemia" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["dyslipidaemia"]
    assert e["detection_function"] is detect_dyslipidaemia_subspecialty
    assert e["normalizer"] is normalize_dyslipidaemia_endpoint
    assert set(e["subspecialties"]) == {"lipid_lowering", "ldl_target", "cv_events", "safety"}


def test_detect_specialty_routes_to_dyslipidaemia():
    spec, sub, _ = detect_specialty(
        "rosuvastatin versus placebo for hypercholesterolaemia; percent reduction "
        "in LDL cholesterol and non-HDL cholesterol at week 12")
    assert spec == "dyslipidaemia" and sub == "lipid_lowering"


def test_dyslipidaemia_cv_outcomes_route():
    spec, sub, _ = detect_specialty(
        "In patients on statin therapy, evolocumab added to lower LDL cholesterol; "
        "the composite of major adverse cardiovascular events, myocardial infarction, "
        "stroke and cardiovascular death")
    assert spec == "dyslipidaemia" and sub == "cv_events"


def test_dyslipidaemia_does_not_break_siblings_or_cardio():
    # CVD-framed but NOT lipid-lowering -> stays cardiology
    assert detect_specialty(
        "sacubitril valsartan in heart failure with reduced ejection fraction; "
        "cardiovascular death and heart failure hospitalization")[0] == "cardiology"
    assert detect_specialty(
        "ticagrelor versus clopidogrel after acute coronary syndrome and "
        "percutaneous coronary intervention; cardiovascular death")[0] == "cardiology"
    # glycemic-framed diabetes trial -> stays diabetes (no lipid vocabulary)
    assert detect_specialty(
        "empagliflozin versus placebo in type 2 diabetes; HbA1c reduction and "
        "fasting plasma glucose at 24 weeks")[0] == "diabetes"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_ldl_goal_2x2():
    t = ("The LDL goal attainment was achieved in 135/200 (67.5%) of evolocumab "
         "recipients and 80/200 (40.0%) of placebo recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "LDL_GOAL_ATTAINMENT"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"evolocumab", "placebo"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (135, 200)


def test_new_onset_diabetes_2x2():
    t = ("New-onset diabetes occurred in 270/8901 (3.0%) of rosuvastatin-treated "
         "patients and 216/8901 (2.4%) of placebo-treated patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "NEW_ONSET_DIABETES"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"rosuvastatin", "placebo"}


def test_ldl_reduction_continuous_poolable():
    r = extract_continuous("mean reduction in LDL cholesterol was 54.3 ± 18.2 mg/dL "
                           "in the atorvastatin arm")
    assert r and r[0]["endpoint"] == "LDL_REDUCTION" and r[0]["poolable"] is True


def test_triglyceride_reduction_continuous_poolable():
    r = extract_continuous("triglycerides fell by 38.6 ± 22.1 mg/dL in the "
                           "icosapent ethyl group")
    assert r and r[0]["endpoint"] == "TG_REDUCTION" and r[0]["poolable"] is True
