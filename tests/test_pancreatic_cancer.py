"""Tests for the pancreatic-cancer specialty profile, registry wiring, arm-level."""
import pytest

from rct_extractor._engine.specialties.pancreatic_cancer import (
    PANCREATIC_CANCER_ENDPOINTS, detect_pancreatic_cancer_subspecialty,
    normalize_pancreatic_cancer_endpoint,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.pancreatic_cancer_arm_data import (
    extract_arm_level, extract_continuous,
)


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of FOLFIRINOX versus gemcitabine plus nab-paclitaxel in "
     "metastatic pancreatic cancer; overall survival, progression-free survival "
     "and CA19-9 response.", "systemic"),
    ("Adjuvant trial of modified FOLFIRINOX versus gemcitabine after resection of "
     "pancreatic ductal adenocarcinoma; disease-free survival and recurrence "
     "following pancreaticoduodenectomy.", "adjuvant"),
    ("Trial of neoadjuvant chemoradiotherapy in borderline resectable locally "
     "advanced pancreatic cancer; resection conversion rate and local control.",
     "locally_advanced"),
    ("Registry follow-up reporting pancreatic cancer-specific mortality and "
     "all-cause mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_pancreatic_cancer_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("progression-free survival", "PFS"),
    ("CA19-9 response", "CA199_RESPONSE"),
    ("disease-free survival", "DFS"),
    ("R0 resection", "R0_RESECTION"),
    ("resection conversion rate", "RESECTION_CONVERSION"),
    ("pancreatic cancer-specific mortality", "PANCREATIC_CANCER_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_pancreatic_cancer_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in PANCREATIC_CANCER_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"systemic", "adjuvant", "locally_advanced", "mortality"}


def test_pancreatic_cancer_registered():
    assert "pancreatic_cancer" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["pancreatic_cancer"]
    assert e["detection_function"] is detect_pancreatic_cancer_subspecialty
    assert set(e["subspecialties"]) == {"systemic", "adjuvant", "locally_advanced", "mortality"}


def test_detect_specialty_routes_to_pancreatic():
    spec, sub, _ = detect_specialty(
        "Randomized trial of FOLFIRINOX versus gemcitabine plus nab-paclitaxel in "
        "metastatic pancreatic ductal adenocarcinoma; overall survival, "
        "progression-free survival and CA19-9 response")
    assert spec == "pancreatic_cancer" and sub == "systemic"


def test_pancreatic_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"


def test_r0_resection_2x2():
    t = ("R0 resection was achieved in 88/120 (73.3%) in the FOLFIRINOX group "
         "versus 60/120 (50.0%) in the gemcitabine group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "R0_RESECTION"


def test_ca199_level_is_lognormal():
    r = extract_continuous("mean serum CA19-9 level 210.0 ± 60.0 U/ml in the gemcitabine arm")
    assert r and r[0]["endpoint"] == "CA199_LEVEL" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
