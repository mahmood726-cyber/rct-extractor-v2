"""
Tests for the cirrhosis / decompensated liver disease specialty profile, registry
wiring, and arm-level extraction. Mirrors the tuberculosis / parkinsons tests.
"""
import pytest

from rct_extractor._engine.specialties.cirrhosis import (
    CIRRHOSIS_ENDPOINTS, detect_cirrhosis_subspecialty,
    normalize_cirrhosis_endpoint, get_cirrhosis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.cirrhosis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


@pytest.mark.parametrize("text,expected", [
    ("Carvedilol versus endoscopic band ligation for primary prophylaxis of "
     "oesophageal variceal bleeding in cirrhosis; rebleeding and HVPG response.",
     "portal_hypertension"),
    ("Terlipressin plus albumin versus placebo for hepatorenal syndrome in "
     "cirrhosis with refractory ascites; HRS reversal and spontaneous bacterial "
     "peritonitis.", "decompensation"),
    ("Rifaximin versus lactulose for prevention of overt hepatic encephalopathy "
     "recurrence in cirrhosis.", "encephalopathy"),
    ("Long-term albumin versus standard care in decompensated cirrhosis; "
     "acute-on-chronic liver failure and transplant-free survival with MELD.",
     "progression"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_cirrhosis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("variceal haemorrhage", "VARICEAL_BLEEDING"),
    ("variceal rebleeding", "REBLEEDING"),
    ("hepatic venous pressure gradient", "HVPG"),
    ("hepatorenal syndrome reversal", "HRS_REVERSAL"),
    ("spontaneous bacterial peritonitis", "SBP"),
    ("recurrence of overt he", "HE_RECURRENCE"),
    ("transplant-free survival", "TRANSPLANT_FREE_SURVIVAL"),
    ("acute-on-chronic liver failure", "ACLF"),
    ("refractory ascites", "ASCITES_CONTROL"),
    ("MELD score", "MELD"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_cirrhosis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in CIRRHOSIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"portal_hypertension", "decompensation",
                                        "encephalopathy", "progression"}


def test_cirrhosis_registered():
    assert "cirrhosis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["cirrhosis"]
    assert e["detection_function"] is detect_cirrhosis_subspecialty
    assert e["normalizer"] is normalize_cirrhosis_endpoint
    assert set(e["subspecialties"]) == {"portal_hypertension", "decompensation",
                                        "encephalopathy", "progression"}


def test_detect_specialty_routes_to_cirrhosis():
    # Must win over hepatitis (whose only cirrhosis signal is the bare keyword).
    spec, sub, _ = detect_specialty(
        "Terlipressin plus albumin for hepatorenal syndrome in decompensated "
        "cirrhosis with refractory ascites; HRS-AKI reversal and 90-day mortality")
    assert spec == "cirrhosis" and sub == "decompensation"


def test_cirrhosis_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "sofosbuvir-velpatasvir for chronic hepatitis C; sustained virologic "
        "response (SVR12) and HBsAg")[0] == "hepatitis"


def test_rebleeding_2x2():
    t = ("Variceal rebleeding occurred in 18/120 (15.0%) in the carvedilol group "
         "and 33/118 (28.0%) in the propranolol group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "REBLEEDING"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"carvedilol", "propranolol"}


def test_meld_continuous():
    rows = extract_continuous(
        "Mean MELD score was 14.2 (SD 4.1) in the statin arm and 16.8 (SD 4.5) in "
        "the placebo arm")
    assert any(r["endpoint"] == "MELD" for r in rows)
