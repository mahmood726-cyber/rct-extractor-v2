"""
Tests for the insomnia specialty profile (pharmacotherapy / cbt_i / objective),
registry wiring, and arm-level extraction.

Routing note: insomnia keywords (insomnia disorder, Insomnia Severity Index/ISI,
sleep-onset latency, wake after sleep onset/WASO, sleep efficiency, hypnotics,
orexin antagonists, CBT-I) are claimed by no existing profile; a depression /
anxiety trial stays with psychiatry. The tests below ground that contract.
"""
import pytest

from rct_extractor._engine.specialties.insomnia import (
    INSOMNIA_ENDPOINTS, detect_insomnia_subspecialty,
    normalize_insomnia_endpoint, get_insomnia_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.insomnia_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Daridorexant versus placebo in chronic insomnia disorder; the Insomnia Severity "
     "Index and wake after sleep onset were primary outcomes.", "pharmacotherapy"),
    ("Digital cognitive behavioural therapy for insomnia (CBT-I) versus sleep hygiene; "
     "the Insomnia Severity Index and sleep efficiency.", "cbt_i"),
    ("Lemborexant versus placebo with overnight polysomnography in insomnia; latency to "
     "persistent sleep and wake after sleep onset.", "objective"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_insomnia_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("Insomnia Severity Index", "ISI"),
    ("sleep onset latency", "SOL"),
    ("wake after sleep onset", "WASO"),
    ("total sleep time", "TST"),
    ("sleep efficiency", "SLEEP_EFFICIENCY"),
    ("Pittsburgh Sleep Quality Index", "PSQI"),
    ("latency to persistent sleep", "LPS"),
    ("insomnia remission", "INSOMNIA_RESPONSE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_insomnia_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"pharmacotherapy", "cbt_i", "objective"}
    for name, info in INSOMNIA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_subspecialty_patterns_cover_all_three():
    for sub in ("pharmacotherapy", "cbt_i", "objective"):
        assert get_insomnia_endpoint_patterns(sub), sub


# --- registry wiring ---

def test_insomnia_registered():
    assert "insomnia" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["insomnia"]
    assert e["detection_function"] is detect_insomnia_subspecialty
    assert e["normalizer"] is normalize_insomnia_endpoint
    assert set(e["subspecialties"]) == {"pharmacotherapy", "cbt_i", "objective"}


def test_detect_specialty_routes_to_insomnia():
    spec, sub, _ = detect_specialty(
        "Daridorexant versus placebo in adults with chronic insomnia disorder; the primary "
        "outcomes were the Insomnia Severity Index and wake after sleep onset, with total "
        "sleep time as a secondary outcome.")
    assert spec == "insomnia" and sub == "pharmacotherapy"


def test_insomnia_does_not_break_neighbors():
    # A depression trial must still route to psychiatry, not insomnia.
    assert detect_specialty(
        "Sertraline versus placebo for major depressive disorder; the primary outcome was "
        "change in the Hamilton Depression Rating Scale and response rate")[0] == "psychiatry"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"


# --- arm-level extraction ---

def test_insomnia_response_2x2():
    t = ("Insomnia remission was achieved in 60/150 (40.0%) in the daridorexant group and "
         "in 30/150 (20.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "INSOMNIA_RESPONSE"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"daridorexant", "placebo"}


def test_isi_continuous_poolable():
    r = extract_continuous("the mean Insomnia Severity Index was 9.0 ± 4.0 in the lemborexant arm")
    assert r and r[0]["endpoint"] == "ISI" and r[0]["poolable"] is True
    assert r[0].get("pooling_note") is None


def test_waso_continuous_poolable():
    r = extract_continuous("the mean wake after sleep onset was 45.0 ± 18.0 minutes in the "
                           "cbt-i arm")
    assert r and r[0]["endpoint"] == "WASO" and r[0]["poolable"] is True
