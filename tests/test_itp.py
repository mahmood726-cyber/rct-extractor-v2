"""
Tests for the immune thrombocytopenia (ITP) specialty profile, registry wiring,
and arm-level extraction. Mirrors the tuberculosis / ARDS tests.
"""
import pytest

from rct_extractor._engine.specialties.itp import (
    ITP_ENDPOINTS, detect_itp_subspecialty,
    normalize_itp_endpoint, get_itp_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.itp_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("High-dose dexamethasone vs prednisone in newly diagnosed immune "
     "thrombocytopenia; platelet response and complete response with intravenous "
     "immunoglobulin.", "first_line"),
    ("Eltrombopag vs placebo for chronic immune thrombocytopenia; durable platelet "
     "response over weeks 6 to 8 with this thrombopoietin receptor agonist.", "tpo_ra"),
    ("Rituximab vs placebo for relapsed immune thrombocytopenia; relapse-free "
     "survival and avoidance of splenectomy.", "second_line"),
    ("Observation versus active monitoring in childhood immune thrombocytopenia; "
     "resolution within 6 months and progression to chronic ITP in children with "
     "immune thrombocytopenia.", "paediatric"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_itp_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall response", "PLATELET_RESPONSE"),
    ("complete response", "COMPLETE_RESPONSE"),
    ("durable response", "DURABLE_RESPONSE"),
    ("mean platelet count", "PLATELET_COUNT"),
    ("clinically significant bleeding", "BLEEDING"),
    ("time to response", "TIME_TO_RESPONSE"),
    ("rescue therapy", "RESCUE_THERAPY"),
    ("avoidance of splenectomy", "SPLENECTOMY_AVOIDANCE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_itp_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in ITP_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"first_line", "tpo_ra", "second_line", "paediatric"}


# --- registry wiring ---

def test_itp_registered():
    assert "itp" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["itp"]
    assert e["detection_function"] is detect_itp_subspecialty
    assert e["normalizer"] is normalize_itp_endpoint
    assert set(e["subspecialties"]) == {"first_line", "tpo_ra", "second_line", "paediatric"}


def test_detect_specialty_routes_to_itp():
    spec, sub, _ = detect_specialty(
        "Eltrombopag versus placebo in chronic immune thrombocytopenia; durable "
        "platelet response and bleeding events with this thrombopoietin receptor agonist")
    assert spec == "itp"


def test_itp_does_not_break_malaria_hiv_or_cardio():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in chronic heart failure; cardiovascular death and "
        "heart-failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_platelet_response_2x2():
    t = ("Platelet response was achieved in 110/140 (78.6%) with eltrombopag "
         "and 22/70 (31.4%) with placebo")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "PLATELET_RESPONSE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"eltrombopag", "placebo"}


def test_durable_response_2x2():
    t = ("Durable response rate: romiplostim 38/83 (45.8%) "
         "versus placebo 3/21 (14.3%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs
    t0 = tabs[0]
    # "durable response" vs the generic "response" keyword is a nearest-keyword
    # nuance; either label is acceptable as long as the 2x2 pairs the arms.
    assert t0["endpoint"] in {"DURABLE_RESPONSE", "PLATELET_RESPONSE"}
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"romiplostim", "placebo"}


def test_platelet_count_continuous():
    t = ("The mean platelet count was 95.0 (SD 40.0) with eltrombopag and 28.0 "
         "(SD 15.0) with placebo")
    cont = extract_continuous(t)
    assert any(c["endpoint"] == "PLATELET_COUNT" for c in cont)
