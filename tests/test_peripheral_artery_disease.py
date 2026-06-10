"""
Tests for the peripheral artery disease (PAD) specialty profile, registry wiring,
and arm-level extraction. Mirrors the hypertension / VTE tests.
"""
import pytest

from rct_extractor._engine.specialties.peripheral_artery_disease import (
    PAD_ENDPOINTS, detect_peripheral_artery_disease_subspecialty,
    normalize_peripheral_artery_disease_endpoint,
    get_peripheral_artery_disease_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.peripheral_artery_disease_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("major amputation, amputation-free survival and limb salvage after lower-limb "
     "revascularisation for chronic limb-threatening ischaemia.", "limb_outcomes"),
    ("drug-coated balloon versus plain balloon angioplasty in femoropopliteal "
     "disease; primary patency and target-lesion revascularisation at 12 months.",
     "revascularisation"),
    ("ticagrelor versus clopidogrel in symptomatic PAD; major adverse cardiovascular "
     "events, myocardial infarction and major bleeding.", "medical_therapy"),
    ("cilostazol for intermittent claudication; maximal walking distance, pain-free "
     "walking distance and ankle-brachial index on a treadmill test.", "functional"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_peripheral_artery_disease_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("major adverse limb events", "MALE"),
    ("amputation-free survival", "AMPUTATION_FREE_SURVIVAL"),
    ("major amputation", "AMPUTATION"),
    ("primary patency", "PRIMARY_PATENCY"),
    ("target lesion revascularization", "TLR"),
    ("maximal walking distance", "MAX_WALKING_DISTANCE"),
    ("pain-free walking distance", "PAIN_FREE_WALKING_DISTANCE"),
    ("ankle-brachial index", "ABI"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_peripheral_artery_disease_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"limb_outcomes", "revascularisation", "medical_therapy", "functional"}
    for name, info in PAD_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_pad_registered():
    assert "peripheral_artery_disease" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["peripheral_artery_disease"]
    assert e["detection_function"] is detect_peripheral_artery_disease_subspecialty
    assert e["normalizer"] is normalize_peripheral_artery_disease_endpoint
    assert set(e["subspecialties"]) == {"limb_outcomes", "revascularisation",
                                        "medical_therapy", "functional"}


def test_detect_specialty_routes_to_pad():
    spec, sub, _ = detect_specialty(
        "cilostazol for intermittent claudication in peripheral artery disease; "
        "maximal walking distance and ankle-brachial index on treadmill testing")
    assert spec == "peripheral_artery_disease" and sub == "functional"


def test_pad_revascularisation_route():
    spec, sub, _ = detect_specialty(
        "drug-coated balloon versus percutaneous transluminal angioplasty for "
        "femoropopliteal peripheral artery disease; primary patency and "
        "target-lesion revascularisation at 12 months")
    assert spec == "peripheral_artery_disease" and sub == "revascularisation"


def test_pad_does_not_break_siblings_or_cardio():
    assert detect_specialty(
        "sacubitril valsartan in heart failure with reduced ejection fraction; "
        "cardiovascular death and heart failure hospitalization")[0] == "cardiology"
    assert detect_specialty(
        "rosuvastatin versus placebo for hypercholesterolaemia; percent reduction "
        "in LDL cholesterol and non-HDL cholesterol")[0] == "dyslipidaemia" \
        if "dyslipidaemia" in SPECIALTY_REGISTRY else True
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_primary_patency_2x2():
    t = ("Primary patency was achieved in 120/150 (80.0%) of drug-coated balloon "
         "recipients and 90/150 (60.0%) of balloon angioplasty recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "PRIMARY_PATENCY"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"drug-coated-balloon", "balloon-angioplasty"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (120, 150)


def test_amputation_2x2():
    t = ("Major amputation occurred in 18/657 (2.7%) of rivaroxaban-treated patients "
         "and 30/657 (4.6%) of placebo-treated patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "AMPUTATION"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"rivaroxaban", "placebo"}


def test_walking_distance_continuous_poolable():
    r = extract_continuous("maximal walking distance increased by 45.2 ± 20.1 meters "
                           "in the cilostazol arm")
    assert r and r[0]["endpoint"] == "MAX_WALKING_DISTANCE" and r[0]["poolable"] is True


def test_abi_continuous_poolable():
    r = extract_continuous("the ankle-brachial index improved by 0.12 ± 0.08 in the "
                           "supervised exercise group")
    assert r and r[0]["endpoint"] == "ABI" and r[0]["poolable"] is True
