"""
Tests for the venous thromboembolism (VTE) specialty profile, registry wiring,
and arm-level extraction. Mirrors the hypertension / dyslipidaemia tests.
"""
import pytest

from rct_extractor._engine.specialties.venous_thromboembolism import (
    VTE_ENDPOINTS, detect_venous_thromboembolism_subspecialty,
    normalize_venous_thromboembolism_endpoint,
    get_venous_thromboembolism_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.venous_thromboembolism_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("extended anticoagulation with apixaban; symptomatic recurrent venous "
     "thromboembolism and post-thrombotic syndrome over 12 months.", "treatment"),
    ("thromboprophylaxis after total hip arthroplasty; prevention of venous "
     "thromboembolism with extended prophylaxis.", "prevention"),
    ("major bleeding and clinically relevant non-major bleeding; intracranial "
     "haemorrhage and fatal bleeding were safety outcomes.", "bleeding"),
    ("pulmonary embolism-related death and all-cause mortality; fatal pulmonary "
     "embolism during follow-up.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_venous_thromboembolism_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("recurrent venous thromboembolism", "RECURRENT_VTE"),
    ("recurrent pulmonary embolism", "RECURRENT_PE"),
    ("deep vein thrombosis", "DVT"),
    ("major bleeding", "MAJOR_BLEEDING"),
    ("clinically relevant non-major bleeding", "CRNM_BLEEDING"),
    ("intracranial haemorrhage", "INTRACRANIAL_HEMORRHAGE"),
    ("post-thrombotic syndrome", "POST_THROMBOTIC_SYNDROME"),
    ("all-cause mortality", "ALL_CAUSE_MORTALITY"),
    ("pulmonary embolism-related death", "PE_RELATED_DEATH"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_venous_thromboembolism_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in VTE_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"treatment", "prevention", "bleeding", "mortality"}


# --- registry wiring ---

def test_vte_registered():
    assert "venous_thromboembolism" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["venous_thromboembolism"]
    assert e["detection_function"] is detect_venous_thromboembolism_subspecialty
    assert e["normalizer"] is normalize_venous_thromboembolism_endpoint
    assert set(e["subspecialties"]) == {"treatment", "prevention", "bleeding", "mortality"}


def test_detect_specialty_routes_to_vte():
    spec, sub, _ = detect_specialty(
        "apixaban versus warfarin for acute venous thromboembolism; symptomatic "
        "recurrent venous thromboembolism and major bleeding over 6 months")
    assert spec == "venous_thromboembolism" and sub == "treatment"


def test_vte_prevention_route():
    spec, sub, _ = detect_specialty(
        "rivaroxaban thromboprophylaxis after total knee arthroplasty; prevention "
        "of venous thromboembolism including deep-vein thrombosis and pulmonary embolism")
    assert spec == "venous_thromboembolism" and sub == "prevention"


def test_vte_does_not_break_siblings_or_cardio():
    # AF anticoagulation trial -> stays cardiology (atrial fibrillation anchors it)
    assert detect_specialty(
        "apixaban versus warfarin in patients with atrial fibrillation; stroke or "
        "systemic embolism and cardiovascular death")[0] == "cardiology"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_recurrent_vte_2x2():
    t = ("Recurrent venous thromboembolism occurred in 36/2419 (1.5%) of apixaban "
         "recipients and 53/2413 (2.2%) of warfarin recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "RECURRENT_VTE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"apixaban", "warfarin"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (36, 2419)


def test_major_bleeding_2x2():
    t = ("Major bleeding occurred in 13/2419 (0.5%) of rivaroxaban-treated patients "
         "and 24/2413 (1.0%) of enoxaparin-treated patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "MAJOR_BLEEDING"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"rivaroxaban", "enoxaparin"}


def test_vte_no_continuous():
    # VTE configures no continuous endpoints
    assert extract_continuous("mean change was 5.0 ± 2.0 units in the apixaban arm") == []
