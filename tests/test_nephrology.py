"""
Tests for the nephrology (kidney) specialty profile (ckd / dialysis / aki /
glomerular), registry wiring, and arm-level extraction. Mirrors the stroke /
respiratory / hepatitis / HIV / malaria tests.

Routing note (coordinated with diabetes / cardiology): nephrology keywords are
KIDNEY-specific (chronic kidney disease, CKD, eGFR, ESKD/ESRD, dialysis,
albuminuria, proteinuria, nephropathy, glomerulonephritis, KDIGO, UACR). A
type-2-diabetes trial whose PRIMARY estimand is a KIDNEY outcome (e.g.
dapagliflozin in diabetic kidney disease with a composite kidney endpoint)
carries enough kidney anchors to route to nephrology, whereas a PURE glycaemic
diabetes trial (HbA1c / hypoglycaemia / weight loss, no kidney primary) stays
with diabetes. We deliberately do NOT claim bare 'diabetes', 'SGLT2',
'gliflozin', or 'finerenone' as nephrology keywords. The tests below ground that
contract against real detect_specialty output.
"""
import pytest

from rct_extractor._engine.specialties.nephrology import (
    NEPHROLOGY_ENDPOINTS, detect_nephrology_subspecialty,
    normalize_nephrology_endpoint, get_nephrology_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.nephrology_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Dapagliflozin versus placebo in chronic kidney disease (CKD); the composite "
     "kidney outcome was sustained 50% decline in eGFR, end-stage kidney disease "
     "(ESKD), and renal death; albuminuria (UACR) reduction.", "ckd"),
    ("High-flux versus low-flux haemodialysis in maintenance dialysis patients; "
     "dialysis adequacy (Kt/V) and arteriovenous fistula vascular access patency.", "dialysis"),
    ("Balanced crystalloids versus saline to prevent acute kidney injury (AKI) "
     "after major surgery; need for renal replacement therapy and recovery of "
     "kidney function.", "aki"),
    ("Rituximab versus cyclophosphamide in membranous nephropathy; complete or "
     "partial remission of proteinuria (UPCR) and relapse at 24 months.", "glomerular"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_nephrology_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("kidney failure", "KIDNEY_FAILURE"),
    ("end-stage kidney disease", "KIDNEY_FAILURE"),
    ("composite kidney outcome", "COMPOSITE_KIDNEY"),
    ("annual eGFR slope", "EGFR_SLOPE"),
    ("UACR", "ALBUMINURIA"),
    ("urinary albumin-to-creatinine ratio", "ALBUMINURIA"),
    ("Kt/V", "DIALYSIS_ADEQUACY"),
    ("vascular access failure", "VASCULAR_ACCESS"),
    ("acute kidney injury", "AKI_INCIDENCE"),
    ("need for renal replacement therapy", "NEED_FOR_RRT"),
    ("recovery of kidney function", "KIDNEY_RECOVERY"),
    ("complete remission", "COMPLETE_REMISSION"),
    ("relapse", "RELAPSE"),
    ("UPCR", "PROTEINURIA"),
    ("24-hour urine protein", "PROTEINURIA"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_nephrology_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"ckd", "dialysis", "aki", "glomerular"}
    for name, info in NEPHROLOGY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_subspecialty_patterns_cover_all_four():
    for sub in ("ckd", "dialysis", "aki", "glomerular"):
        assert get_nephrology_endpoint_patterns(sub), sub


# --- registry wiring ---

def test_nephrology_registered():
    assert "nephrology" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["nephrology"]
    assert e["detection_function"] is detect_nephrology_subspecialty
    assert e["normalizer"] is normalize_nephrology_endpoint
    assert set(e["subspecialties"]) == {"ckd", "dialysis", "aki", "glomerular"}


def test_detect_specialty_routes_to_nephrology():
    # CKD-progression sentence (diabetic kidney disease with a KIDNEY primary
    # outcome) must route to nephrology/ckd, not diabetes.
    spec, sub, _ = detect_specialty(
        "Dapagliflozin versus placebo in patients with chronic kidney disease (CKD) "
        "and type 2 diabetes; the primary composite kidney outcome was sustained 50% "
        "decline in eGFR, end-stage kidney disease, or renal death; albuminuria "
        "(UACR) was a secondary endpoint.")
    assert spec == "nephrology" and sub == "ckd"

    # AKI sentence routes to nephrology/aki.
    spec2, sub2, _ = detect_specialty(
        "Balanced crystalloids versus saline in critically ill patients; acute "
        "kidney injury (AKI) and need for renal replacement therapy within 7 days.")
    assert spec2 == "nephrology" and sub2 == "aki"


def test_pure_glycemic_diabetes_stays_diabetes():
    # CRUCIAL: a pure type-2-diabetes glycaemic trial with NO kidney primary
    # outcome must NOT be stolen by nephrology -- it stays with diabetes.
    spec, sub, _ = detect_specialty(
        "Tirzepatide versus insulin glargine in adults with type 2 diabetes; the "
        "primary outcome was change in HbA1c at week 40, with hypoglycaemia and body "
        "weight as secondary outcomes.")
    assert spec == "diabetes"


def test_nephrology_does_not_break_neighbors():
    assert detect_specialty("dolutegravir-based antiretroviral therapy; week 48 viral "
                            "suppression and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty("artemether-lumefantrine for falciparum malaria; day 28 "
                            "ACPR")[0] == "malaria"
    assert detect_specialty("sofosbuvir-velpatasvir for chronic hepatitis C; sustained "
                            "virologic response SVR12")[0] == "hepatitis"
    assert detect_specialty("sacubitril valsartan in heart failure; cardiovascular "
                            "death and heart failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_kidney_failure_2x2():
    t = ("End-stage kidney disease (ESKD) occurred in 40/600 (6.7%) in the "
         "dapagliflozin group and in 70/600 (11.7%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "KIDNEY_FAILURE"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"dapagliflozin", "placebo"}


def test_albuminuria_continuous_is_lognormal_not_poolable():
    # UACR / albuminuria is log-normal -> poolable False + a pooling_note steering
    # to the log scale (GMR), never a raw-scale MD.
    r = extract_continuous("the mean UACR was 850 ± 200 mg/g in the finerenone arm")
    assert r and r[0]["endpoint"] == "ALBUMINURIA"
    assert r[0]["poolable"] is False
    assert r[0]["pooling_note"] is not None and "log" in r[0]["pooling_note"].lower()
