"""Tests for the oesophageal-cancer specialty profile, registry wiring, arm-level."""
import pytest

from rct_extractor._engine.specialties.oesophageal_cancer import (
    OESOPHAGEAL_CANCER_ENDPOINTS, detect_oesophageal_cancer_subspecialty,
    normalize_oesophageal_cancer_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.oesophageal_cancer_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("RCT of neoadjuvant chemoradiotherapy (CROSS regimen, carboplatin plus "
     "paclitaxel) versus surgery alone in locally advanced oesophageal cancer; "
     "overall survival and pathological complete response.", "definitive"),
    ("Adjuvant nivolumab versus placebo after oesophagectomy in resected "
     "oesophageal cancer with residual pathological disease (CheckMate-577); "
     "disease-free survival and recurrence.", "adjuvant"),
    ("Phase 3 RCT of pembrolizumab plus chemotherapy versus chemotherapy in "
     "advanced oesophageal squamous cell carcinoma; overall survival, "
     "progression-free survival and objective response.", "advanced"),
    ("Registry follow-up reporting oesophageal cancer mortality and all-cause "
     "mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_oesophageal_cancer_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("progression-free survival", "PFS"),
    ("pathological complete response", "PCR"),
    ("disease-free survival", "DFS"),
    ("objective response rate", "ORR"),
    ("oesophageal cancer mortality", "OESOPHAGEAL_CANCER_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_oesophageal_cancer_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in OESOPHAGEAL_CANCER_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"definitive", "adjuvant", "advanced", "mortality"}


def test_oesophageal_cancer_registered():
    assert "oesophageal_cancer" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["oesophageal_cancer"]
    assert e["detection_function"] is detect_oesophageal_cancer_subspecialty
    assert set(e["subspecialties"]) == {"definitive", "adjuvant", "advanced", "mortality"}


def test_detect_specialty_routes_to_oesophageal():
    spec, sub, _ = detect_specialty(
        "Randomized trial of neoadjuvant chemoradiotherapy (CROSS, carboplatin plus "
        "paclitaxel) before oesophagectomy in locally advanced oesophageal cancer; "
        "overall survival and pathological complete response")
    assert spec == "oesophageal_cancer" and sub == "definitive"


def test_oesophageal_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"


def test_pcr_2x2():
    t = ("A pathological complete response occurred in 60/180 (33.3%) in the "
         "chemoradiotherapy group versus 8/180 (4.4%) in the surgery-alone group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "PCR"
