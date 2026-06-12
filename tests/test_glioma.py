"""Tests for the glioma/glioblastoma specialty profile, registry wiring, arm-level."""
import pytest

from rct_extractor._engine.specialties.glioma import (
    GLIOMA_ENDPOINTS, detect_glioma_subspecialty, normalize_glioma_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.glioma_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of tumour-treating fields (TTFields) plus temozolomide versus "
     "temozolomide alone after chemoradiotherapy in newly diagnosed glioblastoma "
     "(GBM); overall survival and progression-free survival.", "glioblastoma"),
    ("Randomized trial of bevacizumab versus lomustine in recurrent glioblastoma; "
     "overall survival, progression-free survival and objective response.", "recurrent"),
    ("Trial of vorasidenib versus placebo in IDH-mutant grade 2 glioma "
     "(oligodendroglioma/astrocytoma); progression-free survival.", "low_grade"),
    ("Registry follow-up reporting glioma-specific mortality and all-cause "
     "mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_glioma_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("progression-free survival", "PFS"),
    ("6-month progression-free survival", "PFS6"),
    ("objective response rate", "ORR"),
    ("time to progression", "TTP"),
    ("brain tumour mortality", "GLIOMA_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_glioma_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in GLIOMA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"glioblastoma", "recurrent", "low_grade", "mortality"}


def test_glioma_registered():
    assert "glioma" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["glioma"]
    assert e["detection_function"] is detect_glioma_subspecialty
    assert set(e["subspecialties"]) == {"glioblastoma", "recurrent", "low_grade", "mortality"}


def test_detect_specialty_routes_to_glioma():
    spec, sub, _ = detect_specialty(
        "Randomized trial of temozolomide plus radiotherapy (Stupp protocol) in "
        "newly diagnosed glioblastoma; MGMT methylation, overall survival and "
        "progression-free survival.")
    assert spec == "glioma" and sub == "glioblastoma"


def test_glioma_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "polatuzumab vedotin plus R-CHP versus R-CHOP in diffuse large B-cell "
        "lymphoma (DLBCL); event-free survival")[0] == "lymphoma"


def test_response_2x2():
    t = ("An objective response occurred in 90/200 (45.0%) in the "
         "bevacizumab group versus 40/200 (20.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ORR"
