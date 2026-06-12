"""
Tests for the alcohol-use-disorder (AUD) specialty profile (pharmacotherapy /
psychosocial / withdrawal), registry wiring, and arm-level extraction.

Routing note: AUD keywords (alcohol use disorder, alcohol dependence, heavy
drinking, percent days abstinent, naltrexone/acamprosate/nalmefene/disulfiram,
CIWA-Ar) are claimed by no existing profile; an alcohol-associated cirrhosis /
hepatitis trial stays with cirrhosis. The tests below ground that contract.
"""
import pytest

from rct_extractor._engine.specialties.alcohol_use_disorder import (
    ALCOHOL_USE_DISORDER_ENDPOINTS, detect_alcohol_use_disorder_subspecialty,
    normalize_alcohol_use_disorder_endpoint,
    get_alcohol_use_disorder_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.alcohol_use_disorder_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Naltrexone versus placebo for alcohol use disorder; abstinence and percentage of "
     "heavy drinking days were the primary outcomes.", "pharmacotherapy"),
    ("Motivational enhancement therapy versus brief intervention for alcohol use disorder; "
     "percent days abstinent and treatment retention.", "psychosocial"),
    ("Symptom-triggered versus fixed-schedule chlordiazepoxide for alcohol withdrawal; "
     "CIWA-Ar score and withdrawal seizures.", "withdrawal"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_alcohol_use_disorder_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("continuous abstinence", "ABSTINENCE"),
    ("percentage of heavy drinking days", "HEAVY_DRINKING_DAYS"),
    ("percent days abstinent", "PCT_DAYS_ABSTINENT"),
    ("drinks per drinking day", "DRINKS_PER_DAY"),
    ("relapse to heavy drinking", "RELAPSE"),
    ("alcohol craving", "CRAVING"),
    ("CIWA-Ar score", "WITHDRAWAL_SEVERITY"),
    ("treatment retention", "RETENTION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_alcohol_use_disorder_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"pharmacotherapy", "psychosocial", "withdrawal"}
    for name, info in ALCOHOL_USE_DISORDER_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_subspecialty_patterns_cover_all_three():
    for sub in ("pharmacotherapy", "psychosocial", "withdrawal"):
        assert get_alcohol_use_disorder_endpoint_patterns(sub), sub


# --- registry wiring ---

def test_alcohol_use_disorder_registered():
    assert "alcohol_use_disorder" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["alcohol_use_disorder"]
    assert e["detection_function"] is detect_alcohol_use_disorder_subspecialty
    assert e["normalizer"] is normalize_alcohol_use_disorder_endpoint
    assert set(e["subspecialties"]) == {"pharmacotherapy", "psychosocial", "withdrawal"}


def test_detect_specialty_routes_to_alcohol_use_disorder():
    spec, sub, _ = detect_specialty(
        "Extended-release naltrexone versus placebo in adults with alcohol use disorder; "
        "the primary outcome was the percentage of heavy drinking days, with abstinence "
        "and alcohol craving as secondary outcomes.")
    assert spec == "alcohol_use_disorder" and sub == "pharmacotherapy"


def test_alcohol_use_disorder_does_not_break_neighbors():
    # An alcohol-associated cirrhosis trial must still route to cirrhosis.
    assert detect_specialty(
        "Rifaximin versus placebo in decompensated cirrhosis with hepatic encephalopathy; "
        "the primary outcome was time to overt hepatic encephalopathy and variceal "
        "bleeding")[0] == "cirrhosis"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"


# --- arm-level extraction ---

def test_abstinence_2x2():
    t = ("Continuous abstinence was achieved in 72/200 (36.0%) in the naltrexone group and "
         "in 40/200 (20.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ABSTINENCE"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"naltrexone", "placebo"}


def test_heavy_drinking_days_continuous_poolable():
    r = extract_continuous("the mean percentage of heavy drinking days was 15.0 ± 8.0 in the "
                           "acamprosate arm")
    assert r and r[0]["endpoint"] == "HEAVY_DRINKING_DAYS" and r[0]["poolable"] is True
    assert r[0].get("pooling_note") is None


def test_ciwa_continuous_poolable():
    r = extract_continuous("the mean CIWA-Ar score was 6.0 ± 3.0 in the lorazepam arm")
    assert r and r[0]["endpoint"] == "WITHDRAWAL_SEVERITY" and r[0]["poolable"] is True
