"""Tests for the multiple myeloma specialty profile, registry wiring, arm-level."""
import pytest

from rct_extractor._engine.specialties.multiple_myeloma import (
    MULTIPLE_MYELOMA_ENDPOINTS, detect_multiple_myeloma_subspecialty,
    normalize_multiple_myeloma_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.multiple_myeloma_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of daratumumab plus bortezomib, lenalidomide and dexamethasone "
     "(D-VRd) versus VRd in transplant-eligible newly diagnosed multiple myeloma "
     "(NDMM); progression-free survival and MRD-negativity.", "newly_diagnosed"),
    ("Randomized trial of isatuximab plus pomalidomide and dexamethasone in "
     "relapsed and refractory multiple myeloma (RRMM) after two prior lines of "
     "therapy; progression-free survival and overall response.", "relapsed_refractory"),
    ("Trial reporting depth of response: overall response rate, very good partial "
     "response and complete response per IMWG criteria.", "response"),
    ("Registry follow-up reporting myeloma-specific mortality and all-cause "
     "mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_multiple_myeloma_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("progression-free survival", "PFS"),
    ("time to progression", "TTP"),
    ("very good partial response", "VGPR"),
    ("stringent complete response", "CR_RATE"),
    ("MRD negativity", "MRD_NEG"),
    ("myeloma-specific mortality", "MM_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_multiple_myeloma_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in MULTIPLE_MYELOMA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"newly_diagnosed", "relapsed_refractory",
                                        "response", "mortality"}


def test_multiple_myeloma_registered():
    assert "multiple_myeloma" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["multiple_myeloma"]
    assert e["detection_function"] is detect_multiple_myeloma_subspecialty
    assert set(e["subspecialties"]) == {"newly_diagnosed", "relapsed_refractory",
                                        "response", "mortality"}


def test_detect_specialty_routes_to_multiple_myeloma():
    spec, sub, _ = detect_specialty(
        "Randomized trial of daratumumab plus lenalidomide and dexamethasone "
        "versus lenalidomide-dexamethasone in newly diagnosed multiple myeloma; "
        "progression-free survival and MRD-negativity.")
    assert spec == "multiple_myeloma" and sub == "newly_diagnosed"


def test_multiple_myeloma_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "polatuzumab vedotin plus R-CHP versus R-CHOP in diffuse large B-cell "
        "lymphoma (DLBCL); event-free survival")[0] == "lymphoma"


def test_response_2x2():
    t = ("A very good partial response occurred in 180/250 (72.0%) in the "
         "daratumumab group versus 125/250 (50.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "VGPR"
