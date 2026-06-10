"""Tests for the hepatocellular-carcinoma specialty profile, registry wiring, arm-level.
Includes a routing test vs hepatitis (the overlapping bucket)."""
import pytest

from rct_extractor._engine.specialties.hepatocellular_carcinoma import (
    HEPATOCELLULAR_CARCINOMA_ENDPOINTS,
    detect_hepatocellular_carcinoma_subspecialty,
    normalize_hepatocellular_carcinoma_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.hepatocellular_carcinoma_arm_data import (
    extract_arm_level, extract_continuous,
)


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of atezolizumab plus bevacizumab versus sorafenib in unresectable "
     "hepatocellular carcinoma (BCLC-C, Child-Pugh A); overall survival, "
     "progression-free survival and AFP response.", "systemic"),
    ("RCT of transarterial chemoembolization (TACE) plus lenvatinib versus TACE alone "
     "in intermediate-stage HCC; time to progression and objective response by "
     "mRECIST.", "locoregional"),
    ("Adjuvant trial after curative hepatic resection for early-stage hepatocellular "
     "carcinoma; recurrence-free survival and tumour recurrence within Milan "
     "criteria.", "curative"),
    ("Registry follow-up reporting liver cancer mortality and all-cause mortality.",
     "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_hepatocellular_carcinoma_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("time to progression", "TTP"),
    ("AFP response", "AFP_RESPONSE"),
    ("recurrence-free survival", "RFS"),
    ("local tumor control", "LOCAL_CONTROL"),
    ("liver cancer mortality", "LIVER_CANCER_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_hepatocellular_carcinoma_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in HEPATOCELLULAR_CARCINOMA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"systemic", "locoregional", "curative", "mortality"}


def test_hcc_registered():
    assert "hepatocellular_carcinoma" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["hepatocellular_carcinoma"]
    assert e["detection_function"] is detect_hepatocellular_carcinoma_subspecialty
    assert set(e["subspecialties"]) == {"systemic", "locoregional", "curative", "mortality"}


def test_detect_specialty_routes_to_hcc_over_hepatitis():
    # An HCC trial that also mentions cirrhosis/HBV must route to HCC, not hepatitis.
    spec, sub, _ = detect_specialty(
        "Randomized trial of lenvatinib versus sorafenib in unresectable "
        "hepatocellular carcinoma with hepatitis B-related cirrhosis (BCLC-C, "
        "Child-Pugh A); overall survival, progression-free survival, objective "
        "response and alpha-fetoprotein (AFP) response")
    assert spec == "hepatocellular_carcinoma" and sub == "systemic"


def test_hepatitis_antiviral_still_routes_to_hepatitis():
    assert detect_specialty(
        "sofosbuvir-velpatasvir for chronic hepatitis C; sustained virologic "
        "response (SVR12) and HCV RNA suppression")[0] == "hepatitis"


def test_recurrence_2x2():
    t = ("Tumour recurrence occurred in 60/200 (30.0%) in the resection group "
         "versus 90/200 (45.0%) in the RFA group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "RECURRENCE"


def test_afp_level_is_lognormal():
    r = extract_continuous("mean serum AFP level 320.0 ± 80.0 ng/ml in the sorafenib arm")
    assert r and r[0]["endpoint"] == "AFP_LEVEL" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
