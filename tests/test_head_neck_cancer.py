"""Tests for the head-and-neck-cancer specialty profile, registry wiring, arm-level."""
import pytest

from rct_extractor._engine.specialties.head_neck_cancer import (
    HEAD_NECK_CANCER_ENDPOINTS, detect_head_neck_cancer_subspecialty,
    normalize_head_neck_cancer_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.head_neck_cancer_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of concurrent chemoradiotherapy with cisplatin versus cetuximab "
     "plus radiotherapy in locally advanced head and neck squamous cell carcinoma; "
     "overall survival and locoregional control.", "definitive"),
    ("Trial of pembrolizumab versus cetuximab with platinum and 5-FU (EXTREME) in "
     "recurrent or metastatic head and neck cancer; overall survival, "
     "progression-free survival and objective response.", "recurrent_metastatic"),
    ("RCT of gemcitabine plus cisplatin induction chemotherapy in endemic "
     "nasopharyngeal carcinoma (NPC) with Epstein-Barr virus; overall survival and "
     "distant metastasis-free survival.", "nasopharyngeal"),
    ("Registry follow-up reporting head and neck cancer mortality and all-cause "
     "mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_head_neck_cancer_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("progression-free survival", "PFS"),
    ("locoregional control", "LOCOREGIONAL_CONTROL"),
    ("distant metastasis-free survival", "DMFS"),
    ("disease-free survival", "DFS"),
    ("head and neck cancer mortality", "HEAD_NECK_CANCER_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_head_neck_cancer_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in HEAD_NECK_CANCER_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"definitive", "recurrent_metastatic", "nasopharyngeal", "mortality"}


def test_head_neck_cancer_registered():
    assert "head_neck_cancer" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["head_neck_cancer"]
    assert e["detection_function"] is detect_head_neck_cancer_subspecialty
    assert set(e["subspecialties"]) == {"definitive", "recurrent_metastatic", "nasopharyngeal", "mortality"}


def test_detect_specialty_routes_to_head_neck():
    spec, sub, _ = detect_specialty(
        "Randomized trial of concurrent chemoradiotherapy with cisplatin in locally "
        "advanced head and neck squamous cell carcinoma (HNSCC); overall survival "
        "and locoregional control")
    assert spec == "head_neck_cancer" and sub == "definitive"


def test_head_neck_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "single-dose HPV vaccine (Cervarix, bivalent); CIN2+ and persistent HPV "
        "infection")[0] == "cervical_cancer"


def test_locoregional_control_2x2():
    t = ("Locoregional failure occurred in 40/200 (20.0%) in the cisplatin group "
         "versus 70/200 (35.0%) in the cetuximab group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "LOCOREGIONAL_CONTROL"
