"""Tests for the leukaemia specialty profile (AML/ALL/CLL/CML), registry wiring, arm-level."""
import pytest

from rct_extractor._engine.specialties.leukaemia import (
    LEUKAEMIA_ENDPOINTS, detect_leukaemia_subspecialty, normalize_leukaemia_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.leukaemia_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of venetoclax plus azacitidine versus azacitidine in acute myeloid "
     "leukemia (AML); complete remission, overall survival and MRD negativity with "
     "FLT3 midostaurin comparison.", "aml"),
    ("Trial of blinatumomab versus chemotherapy in relapsed acute lymphoblastic "
     "leukemia (ALL); complete remission and measurable residual disease negativity "
     "with inotuzumab.", "all"),
    ("Randomized trial of ibrutinib plus obinutuzumab versus chlorambucil in "
     "treatment-naive chronic lymphocytic leukemia (CLL); progression-free survival, "
     "objective response and undetectable MRD.", "cll"),
    ("Trial of nilotinib versus imatinib in chronic-phase chronic myeloid leukemia "
     "(CML); major molecular response and complete cytogenetic response with BCR-ABL "
     "transcript.", "cml"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_leukaemia_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("complete remission", "COMPLETE_REMISSION"),
    ("undetectable MRD", "MRD_NEGATIVITY"),
    ("major molecular response", "MMR"),
    ("complete cytogenetic response", "CCYR"),
    ("event-free survival", "EFS"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_leukaemia_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in LEUKAEMIA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"aml", "all", "cll", "cml"}


def test_leukaemia_registered():
    assert "leukaemia" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["leukaemia"]
    assert e["detection_function"] is detect_leukaemia_subspecialty
    assert set(e["subspecialties"]) == {"aml", "all", "cll", "cml"}


def test_detect_specialty_routes_to_leukaemia():
    spec, sub, _ = detect_specialty(
        "Randomized trial of nilotinib versus imatinib in chronic myeloid leukemia "
        "(CML) with BCR-ABL; major molecular response and complete cytogenetic "
        "response")
    assert spec == "leukaemia" and sub == "cml"


def test_leukaemia_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"


def test_complete_remission_2x2():
    t = ("Complete remission occurred in 130/200 (65.0%) in the venetoclax group "
         "versus 50/200 (25.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "COMPLETE_REMISSION"
