"""Tests for the myelodysplastic syndrome (MDS) specialty profile, registry, arm-level.

Distinct from the `leukaemia` (AML/ALL/CLL/CML) specialty.
"""
import pytest

from rct_extractor._engine.specialties.myelodysplastic_syndrome import (
    MYELODYSPLASTIC_SYNDROME_ENDPOINTS, detect_myelodysplastic_syndrome_subspecialty,
    normalize_myelodysplastic_syndrome_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.myelodysplastic_syndrome_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of luspatercept versus epoetin alfa in lower-risk "
     "myelodysplastic syndrome with ring sideroblasts; red-cell transfusion "
     "independence and haematologic improvement.", "lower_risk"),
    ("Randomized trial of azacitidine plus venetoclax versus azacitidine in "
     "higher-risk MDS with excess blasts; overall survival and complete "
     "remission.", "higher_risk"),
    ("Trial reporting haematologic improvement and transfusion independence per "
     "IWG 2006 criteria; overall haematologic response.", "response"),
    ("Registry follow-up reporting MDS-specific mortality, AML transformation "
     "and all-cause mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_myelodysplastic_syndrome_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("transfusion independence", "RBC_TI"),
    ("haematologic improvement", "HI"),       # British spelling
    ("hematologic improvement", "HI"),         # American spelling
    ("complete remission", "CR_RATE"),
    ("AML-free survival", "AML_FREE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_myelodysplastic_syndrome_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in MYELODYSPLASTIC_SYNDROME_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"lower_risk", "higher_risk", "response", "mortality"}


def test_mds_registered():
    assert "myelodysplastic_syndrome" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["myelodysplastic_syndrome"]
    assert e["detection_function"] is detect_myelodysplastic_syndrome_subspecialty
    assert set(e["subspecialties"]) == {"lower_risk", "higher_risk", "response", "mortality"}


def test_detect_specialty_routes_to_mds():
    spec, sub, _ = detect_specialty(
        "Randomized trial of luspatercept versus placebo in transfusion-dependent "
        "lower-risk myelodysplastic syndrome (MDS) with ring sideroblasts; "
        "red-cell transfusion independence.")
    assert spec == "myelodysplastic_syndrome" and sub == "lower_risk"


def test_mds_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "polatuzumab vedotin plus R-CHP versus R-CHOP in diffuse large B-cell "
        "lymphoma (DLBCL); event-free survival")[0] == "lymphoma"


def test_transfusion_independence_2x2():
    t = ("Red-cell transfusion independence occurred in 116/229 (50.7%) in the "
         "luspatercept group versus 30/76 (39.5%) in the epoetin group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "RBC_TI"
