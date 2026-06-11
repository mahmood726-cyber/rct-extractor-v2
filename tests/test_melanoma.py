"""Tests for the melanoma specialty profile, registry wiring, arm-level."""
import pytest

from rct_extractor._engine.specialties.melanoma import (
    MELANOMA_ENDPOINTS, detect_melanoma_subspecialty, normalize_melanoma_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.melanoma_arm_data import (
    extract_arm_level, extract_continuous,
)


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of nivolumab plus ipilimumab versus pembrolizumab in metastatic "
     "melanoma; overall survival, progression-free survival and objective response "
     "with BRAF V600 dabrafenib comparison.", "systemic"),
    ("Adjuvant trial of pembrolizumab versus placebo in completely resected stage III "
     "melanoma; recurrence-free survival and distant metastasis-free survival in "
     "sentinel-node-positive disease.", "adjuvant"),
    ("Neoadjuvant nivolumab plus ipilimumab before surgery in melanoma; pathological "
     "complete response and major pathological response with event-free survival.",
     "neoadjuvant"),
    ("Registry follow-up reporting melanoma-specific mortality and all-cause "
     "mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_melanoma_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("recurrence-free survival", "RFS"),
    ("distant metastasis-free survival", "DMFS"),
    ("major pathological response", "PATHOLOGICAL_RESPONSE"),
    ("event-free survival", "EFS"),
    ("melanoma-specific mortality", "MELANOMA_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_melanoma_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in MELANOMA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"systemic", "adjuvant", "neoadjuvant", "mortality"}


def test_melanoma_registered():
    assert "melanoma" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["melanoma"]
    assert e["detection_function"] is detect_melanoma_subspecialty
    assert set(e["subspecialties"]) == {"systemic", "adjuvant", "neoadjuvant", "mortality"}


def test_detect_specialty_routes_to_melanoma():
    spec, sub, _ = detect_specialty(
        "Randomized trial of nivolumab plus ipilimumab versus dabrafenib plus "
        "trametinib in BRAF V600-mutant metastatic melanoma; overall survival, "
        "progression-free survival and objective response")
    assert spec == "melanoma" and sub == "systemic"


def test_melanoma_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"


def test_pathological_response_2x2():
    t = ("A pathological complete response occurred in 70/150 (46.7%) in the "
         "nivolumab group versus 30/150 (20.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "PATHOLOGICAL_RESPONSE"


def test_ldh_level_is_lognormal():
    r = extract_continuous("mean serum LDH level 280.0 ± 60.0 U/l in the dacarbazine arm")
    assert r and r[0]["endpoint"] == "LDH_LEVEL" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
