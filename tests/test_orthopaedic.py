"""
Tests for the orthopaedic / fracture-surgery specialty profile, registry wiring,
and arm-level extraction. Mirrors the tuberculosis / ARDS tests.
"""
import pytest

from rct_extractor._engine.specialties.orthopaedic import (
    ORTHOPAEDIC_ENDPOINTS, detect_orthopaedic_subspecialty,
    normalize_orthopaedic_endpoint, get_orthopaedic_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.orthopaedic_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Intramedullary nailing versus locking plate fixation for tibial fracture; "
     "reoperation and nonunion with open reduction internal fixation.", "fracture_fixation"),
    ("Cemented total hip arthroplasty versus uncemented hemiarthroplasty for femoral "
     "neck fracture; periprosthetic joint infection and revision.", "arthroplasty"),
    ("Low-intensity pulsed ultrasound versus placebo for fracture healing; time to "
     "union and nonunion with bone graft.", "healing"),
    ("ACL reconstruction versus structured rehabilitation; Lysholm score, return to "
     "sport and range of motion.", "functional"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_orthopaedic_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("revision surgery", "REOPERATION"),
    ("delayed union", "NONUNION"),
    ("time to union", "UNION_TIME"),
    ("harris hip score", "FUNCTIONAL_SCORE"),
    ("periprosthetic joint infection", "INFECTION"),
    ("range of motion", "RANGE_OF_MOTION"),
    ("return to sport", "RETURN_TO_ACTIVITY"),
    ("deep vein thrombosis", "VTE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_orthopaedic_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in ORTHOPAEDIC_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"fracture_fixation", "arthroplasty",
                                        "healing", "functional"}


# --- registry wiring ---

def test_orthopaedic_registered():
    assert "orthopaedic" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["orthopaedic"]
    assert e["detection_function"] is detect_orthopaedic_subspecialty
    assert e["normalizer"] is normalize_orthopaedic_endpoint
    assert set(e["subspecialties"]) == {"fracture_fixation", "arthroplasty",
                                        "healing", "functional"}


def test_detect_specialty_routes_to_orthopaedic():
    spec, sub, _ = detect_specialty(
        "Intramedullary nailing versus plate fixation for distal tibial fracture; "
        "reoperation, nonunion and time to union")
    assert spec == "orthopaedic"


def test_orthopaedic_does_not_break_malaria_hiv_or_cardio():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in chronic heart failure; cardiovascular death and "
        "heart-failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_reoperation_2x2():
    t = ("Reoperation rate: intramedullary nail 18/150 (12.0%) "
         "versus plate fixation 42/148 (28.4%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs
    t0 = tabs[0]
    assert t0["endpoint"] == "REOPERATION"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"intramedullary-nail", "plate-fixation"}


def test_nonunion_2x2():
    t = ("Nonunion: operative 8/120 (6.7%) versus nonoperative 24/118 (20.3%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "NONUNION"


def test_functional_score_continuous():
    t = ("The Harris hip score was 88.4 (SD 9.2) with total hip arthroplasty and "
         "79.1 (SD 11.5) with hemiarthroplasty")
    cont = extract_continuous(t)
    assert any(c["endpoint"] == "FUNCTIONAL_SCORE" for c in cont)
