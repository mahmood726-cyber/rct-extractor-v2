"""
Tests for the substance/opioid-use-disorder (SUD) specialty profile (opioid /
stimulant / general), registry wiring, and arm-level extraction.

Routing note: addiction keywords (opioid/substance use disorder, OUD/SUD,
buprenorphine/methadone/naltrexone for the disorder, urine drug screen,
treatment retention, COWS/SOWS) are claimed by no existing profile; a chronic-pain
trial that uses opioids as analgesics stays with chronic_pain. The tests below
ground that contract.
"""
import pytest

from rct_extractor._engine.specialties.substance_use_disorder import (
    SUBSTANCE_USE_DISORDER_ENDPOINTS, detect_substance_use_disorder_subspecialty,
    normalize_substance_use_disorder_endpoint,
    get_substance_use_disorder_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.substance_use_disorder_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Buprenorphine-naloxone versus methadone for opioid use disorder; treatment retention "
     "and opioid-negative urine drug screens were primary outcomes.", "opioid"),
    ("Contingency management versus treatment as usual for cocaine use disorder; "
     "cocaine-negative urine drug screens and abstinence.", "stimulant"),
    ("A digital intervention versus treatment as usual for substance use disorder; treatment "
     "retention and self-reported abstinence.", "general"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_substance_use_disorder_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("treatment retention", "RETENTION"),
    ("opioid-negative urine drug screen", "NEGATIVE_UDS"),
    ("sustained abstinence", "ABSTINENCE"),
    ("non-fatal overdose", "OVERDOSE"),
    ("relapse to use", "RELAPSE"),
    ("opioid craving", "CRAVING"),
    ("clinical opiate withdrawal scale", "WITHDRAWAL_SEVERITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_substance_use_disorder_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"opioid", "stimulant", "general"}
    for name, info in SUBSTANCE_USE_DISORDER_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_subspecialty_patterns_cover_all_three():
    for sub in ("opioid", "stimulant", "general"):
        assert get_substance_use_disorder_endpoint_patterns(sub), sub


# --- registry wiring ---

def test_substance_use_disorder_registered():
    assert "substance_use_disorder" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["substance_use_disorder"]
    assert e["detection_function"] is detect_substance_use_disorder_subspecialty
    assert e["normalizer"] is normalize_substance_use_disorder_endpoint
    assert set(e["subspecialties"]) == {"opioid", "stimulant", "general"}


def test_detect_specialty_routes_to_substance_use_disorder():
    spec, sub, _ = detect_specialty(
        "Buprenorphine-naloxone versus extended-release naltrexone for opioid use disorder; "
        "the primary outcomes were treatment retention and opioid-negative urine drug screens, "
        "with overdose events as a secondary outcome.")
    assert spec == "substance_use_disorder" and sub == "opioid"


def test_substance_use_disorder_does_not_break_neighbors():
    # A chronic-pain trial that uses opioids as analgesics stays with chronic_pain.
    assert detect_specialty(
        "Pregabalin versus placebo for chronic neuropathic pain; the primary outcome was "
        "change in the 11-point pain numeric rating scale and 30% pain responders")[0] == "chronic_pain"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"


# --- arm-level extraction ---

def test_retention_2x2():
    t = ("Treatment retention was achieved in 130/200 (65.0%) in the methadone group and "
         "in 90/200 (45.0%) in the buprenorphine group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "RETENTION"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"methadone", "buprenorphine"}


def test_craving_continuous_poolable():
    r = extract_continuous("the mean opioid craving score was 2.5 ± 1.1 in the buprenorphine arm")
    assert r and r[0]["endpoint"] == "CRAVING" and r[0]["poolable"] is True
    assert r[0].get("pooling_note") is None


def test_withdrawal_continuous_poolable():
    r = extract_continuous("the mean clinical opiate withdrawal scale was 8.0 ± 3.5 in the "
                           "lofexidine arm")
    assert r and r[0]["endpoint"] == "WITHDRAWAL_SEVERITY" and r[0]["poolable"] is True
