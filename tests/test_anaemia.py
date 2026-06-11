"""
Tests for the anaemia specialty profile, registry wiring, and arm-level
extraction. Mirrors the tuberculosis / ARDS tests.
"""
import pytest

from rct_extractor._engine.specialties.anaemia import (
    ANAEMIA_ENDPOINTS, detect_anaemia_subspecialty,
    normalize_anaemia_endpoint, get_anaemia_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.anaemia_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Intravenous ferric carboxymaltose vs oral ferrous sulfate for iron-deficiency "
     "anaemia; haemoglobin change, ferritin and transferrin saturation.", "iron_therapy"),
    ("Roxadustat vs darbepoetin for anaemia of chronic kidney disease; haemoglobin "
     "response and target haemoglobin with an erythropoiesis-stimulating agent.", "esa"),
    ("Iron and folic acid supplementation vs placebo in pregnant women; maternal "
     "anaemia correction and anaemia prevalence at endline.", "nutritional"),
    ("Restrictive vs liberal red blood cell transfusion threshold in critically ill "
     "patients; transfusion requirement and 28-day mortality.", "transfusion_anaemia"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_anaemia_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("change in haemoglobin", "HB_CHANGE"),
    ("haemoglobin response", "HB_RESPONSE"),
    ("correction of anaemia", "ANAEMIA_CORRECTION"),
    ("red blood cell transfusion", "TRANSFUSION"),
    ("serum ferritin", "FERRITIN"),
    ("transferrin saturation", "TSAT"),
    ("reticulocyte count", "RETICULOCYTE"),
    ("iron deficiency", "IRON_DEFICIENCY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_anaemia_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in ANAEMIA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"iron_therapy", "esa", "nutritional",
                                        "transfusion_anaemia"}


# --- registry wiring ---

def test_anaemia_registered():
    assert "anaemia" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["anaemia"]
    assert e["detection_function"] is detect_anaemia_subspecialty
    assert e["normalizer"] is normalize_anaemia_endpoint
    assert set(e["subspecialties"]) == {"iron_therapy", "esa", "nutritional",
                                        "transfusion_anaemia"}


def test_detect_specialty_routes_to_anaemia():
    spec, sub, _ = detect_specialty(
        "Intravenous ferric carboxymaltose versus oral iron for iron-deficiency "
        "anaemia; mean change in haemoglobin and serum ferritin at week 12")
    assert spec == "anaemia"


def test_anaemia_does_not_break_malaria_hiv_or_cardio():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in chronic heart failure; cardiovascular death and "
        "heart-failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_hb_response_2x2():
    t = ("Haemoglobin response was achieved in 140/200 (70.0%) with ferric "
         "carboxymaltose and 96/198 (48.5%) with oral iron")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "HB_RESPONSE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"ferric-carboxymaltose", "oral-iron"}


def test_transfusion_2x2():
    t = ("Red blood cell transfusion was required in 30/250 (12.0%) with "
         "intravenous iron and 60/248 (24.2%) with placebo")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "TRANSFUSION"


def test_hb_change_continuous():
    t = ("The change in haemoglobin was 2.4 (SD 1.1) g/dL with ferric carboxymaltose "
         "and 1.3 (SD 1.0) g/dL with oral iron")
    cont = extract_continuous(t)
    assert any(c["endpoint"] == "HB_CHANGE" for c in cont)
