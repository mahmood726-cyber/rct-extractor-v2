"""
Tests for the hypertension / cardiovascular specialty profile, registry wiring,
and arm-level extraction. Mirrors the typhoid, HIV and malaria tests.
"""
import pytest

from rct_extractor._engine.specialties.hypertension import (
    HYPERTENSION_ENDPOINTS, detect_hypertension_subspecialty,
    normalize_hypertension_endpoint, get_hypertension_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.hypertension_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("amlodipine versus hydrochlorothiazide for essential hypertension; "
     "antihypertensive response and blood pressure control at 12 weeks.", "bp_lowering"),
    ("intensive blood-pressure lowering; major adverse cardiovascular events, "
     "stroke, myocardial infarction, heart failure hospitalization and "
     "cardiovascular death.", "cv_events"),
    ("telmisartan versus placebo; reduction in systolic and diastolic blood "
     "pressure and 24-hour ambulatory blood pressure in mmHg.", "bp_reduction"),
    ("pharmacist intervention to improve antihypertensive medication adherence "
     "and persistence; proportion of days covered and treatment discontinuation.",
     "adherence"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_hypertension_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("blood pressure control", "BP_CONTROL"),
    ("systolic blood pressure reduction", "SBP_REDUCTION"),
    ("reduction in diastolic blood pressure", "DBP_REDUCTION"),
    ("24-hour ambulatory blood pressure", "AMBULATORY_SBP"),
    ("major adverse cardiovascular events", "MACE"),
    ("cardiovascular death", "CV_MORTALITY"),
    ("all-cause mortality", "ALL_CAUSE_MORTALITY"),
    ("heart failure hospitalization", "HF_HOSPITALIZATION"),
    ("medication adherence", "MEDICATION_ADHERENCE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_hypertension_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in HYPERTENSION_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"bp_lowering", "cv_events", "bp_reduction", "adherence"}


# --- registry wiring ---

def test_hypertension_registered():
    assert "hypertension" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["hypertension"]
    assert e["detection_function"] is detect_hypertension_subspecialty
    assert e["normalizer"] is normalize_hypertension_endpoint
    assert set(e["subspecialties"]) == {"bp_lowering", "cv_events", "bp_reduction", "adherence"}


def test_detect_specialty_routes_to_hypertension():
    spec, sub, _ = detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; "
        "blood pressure control at 12 weeks and antihypertensive response rate")
    assert spec == "hypertension" and sub == "bp_lowering"


def test_hypertension_cv_outcomes_route():
    spec, sub, _ = detect_specialty(
        "Among adults with hypertension, intensive systolic blood-pressure lowering "
        "to a target below 120 mm Hg versus standard control; the composite of "
        "major adverse cardiovascular events, stroke, myocardial infarction, heart "
        "failure hospitalization and cardiovascular death")
    assert spec == "hypertension" and sub == "cv_events"


def test_hypertension_does_not_break_siblings_or_cardio():
    # CVD-framed but NOT antihypertensive -> stays cardiology
    assert detect_specialty(
        "sacubitril valsartan in heart failure with reduced ejection fraction; "
        "cardiovascular death and heart failure hospitalization")[0] == "cardiology"
    assert detect_specialty(
        "ticagrelor versus clopidogrel after acute coronary syndrome and "
        "percutaneous coronary intervention; cardiovascular death")[0] == "cardiology"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "azithromycin versus ciprofloxacin for blood-culture-confirmed typhoid "
        "fever; fever clearance time and clinical cure in enteric fever")[0] == "typhoid"


# --- arm-level extraction ---

def test_bp_control_2x2():
    t = ("Blood pressure control was achieved in 120/150 (80.0%) of amlodipine "
         "recipients and 90/150 (60.0%) of hydrochlorothiazide recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "BP_CONTROL"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"amlodipine", "hydrochlorothiazide"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (120, 150)


def test_stroke_2x2():
    t = ("Stroke occurred in 105/9048 (1.2%) of chlorthalidone-treated patients "
         "and 80/4870 (1.6%) of amlodipine-treated patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "STROKE"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"chlorthalidone", "amlodipine"}


def test_sbp_reduction_continuous_poolable():
    r = extract_continuous("mean reduction in systolic blood pressure was 12.4 ± 8.2 mmHg "
                           "in the amlodipine arm")
    assert r and r[0]["endpoint"] == "SBP_REDUCTION" and r[0]["poolable"] is True


def test_dbp_reduction_continuous_poolable():
    r = extract_continuous("diastolic blood pressure fell by 7.1 ± 5.0 mmHg in the "
                           "telmisartan group")
    assert r and r[0]["endpoint"] == "DBP_REDUCTION" and r[0]["poolable"] is True


def test_bp_control_arm_not_stolen_by_endpoint_phrase():
    # the word "control" inside "blood pressure control" must NOT be tagged as the
    # generic control arm
    props = extract_proportions(
        "Blood pressure control was achieved in 120/150 (80.0%) of amlodipine recipients")
    assert props and props[0]["arm"] == "amlodipine"
