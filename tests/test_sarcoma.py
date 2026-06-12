"""Tests for the soft-tissue sarcoma specialty profile, registry wiring, arm-level."""
import pytest

from rct_extractor._engine.specialties.sarcoma import (
    SARCOMA_ENDPOINTS, detect_sarcoma_subspecialty, normalize_sarcoma_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.sarcoma_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of pazopanib versus placebo in advanced metastatic soft-tissue "
     "sarcoma (leiomyosarcoma, synovial sarcoma); progression-free survival and "
     "overall survival.", "advanced"),
    ("Randomized trial of regorafenib versus placebo in advanced gastrointestinal "
     "stromal tumour (GIST) after imatinib and sunitinib; progression-free "
     "survival and time to progression.", "gist"),
    ("Trial of adjuvant doxorubicin-ifosfamide versus observation in resected "
     "extremity soft-tissue sarcoma; recurrence-free survival and overall "
     "survival.", "localized"),
    ("Registry follow-up reporting sarcoma-specific mortality and all-cause "
     "mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_sarcoma_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("progression-free survival", "PFS"),
    ("recurrence-free survival", "RFS"),
    ("objective response rate", "ORR"),
    ("time to progression", "TTP"),
    ("sarcoma-specific mortality", "SARCOMA_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_sarcoma_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in SARCOMA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"advanced", "gist", "localized", "mortality"}


def test_sarcoma_registered():
    assert "sarcoma" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["sarcoma"]
    assert e["detection_function"] is detect_sarcoma_subspecialty
    assert set(e["subspecialties"]) == {"advanced", "gist", "localized", "mortality"}


def test_detect_specialty_routes_to_sarcoma():
    spec, sub, _ = detect_specialty(
        "Randomized trial of trabectedin versus dacarbazine in advanced "
        "leiomyosarcoma and liposarcoma (soft-tissue sarcoma); progression-free "
        "survival and objective response.")
    assert spec == "sarcoma" and sub == "advanced"


def test_sarcoma_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "polatuzumab vedotin plus R-CHP versus R-CHOP in diffuse large B-cell "
        "lymphoma (DLBCL); event-free survival")[0] == "lymphoma"


def test_response_2x2():
    t = ("An objective response occurred in 60/200 (30.0%) in the "
         "pazopanib group versus 16/200 (8.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ORR"
