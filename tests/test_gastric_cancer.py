"""Tests for the gastric-cancer specialty profile, registry wiring, arm-level."""
import pytest

from rct_extractor._engine.specialties.gastric_cancer import (
    GASTRIC_CANCER_ENDPOINTS, detect_gastric_cancer_subspecialty,
    normalize_gastric_cancer_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.gastric_cancer_arm_data import (
    extract_arm_level, extract_continuous,
)


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of trastuzumab plus chemotherapy versus chemotherapy alone in "
     "HER2-positive metastatic gastric cancer; overall survival, progression-free "
     "survival and objective response with ramucirumab comparison.", "systemic"),
    ("Perioperative FLOT versus neoadjuvant chemotherapy in resectable gastric "
     "cancer; pathological complete response, disease-free survival and R0 "
     "resection.", "perioperative"),
    ("Trial of D2 versus D1 lymphadenectomy at gastrectomy for gastric cancer; "
     "recurrence and curative resection.", "surgical"),
    ("Registry follow-up reporting gastric cancer-specific mortality and all-cause "
     "mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_gastric_cancer_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("progression-free survival", "PFS"),
    ("pathological complete response", "PCR"),
    ("disease-free survival", "DFS"),
    ("R0 resection", "R0_RESECTION"),
    ("gastric cancer-specific mortality", "GASTRIC_CANCER_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_gastric_cancer_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in GASTRIC_CANCER_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"systemic", "perioperative", "surgical", "mortality"}


def test_gastric_cancer_registered():
    assert "gastric_cancer" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["gastric_cancer"]
    assert e["detection_function"] is detect_gastric_cancer_subspecialty
    assert set(e["subspecialties"]) == {"systemic", "perioperative", "surgical", "mortality"}


def test_detect_specialty_routes_to_gastric():
    spec, sub, _ = detect_specialty(
        "Randomized trial of perioperative FLOT in resectable gastric cancer "
        "undergoing gastrectomy; pathological complete response, disease-free "
        "survival and R0 resection")
    assert spec == "gastric_cancer" and sub == "perioperative"


def test_gastric_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"


def test_pcr_2x2():
    t = ("A pathological complete response occurred in 40/180 (22.2%) in the FLOT "
         "group versus 18/180 (10.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "PCR"
