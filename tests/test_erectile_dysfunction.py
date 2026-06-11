"""
Tests for the erectile-dysfunction (ED) specialty profile, registry wiring, and
arm-level extraction. Mirrors the BPH, cervical-cancer and endometriosis tests.
"""
import pytest

from rct_extractor._engine.specialties.erectile_dysfunction import (
    ERECTILE_DYSFUNCTION_ENDPOINTS, detect_erectile_dysfunction_subspecialty,
    normalize_erectile_dysfunction_endpoint, get_erectile_dysfunction_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.erectile_dysfunction_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of tadalafil versus placebo for erectile dysfunction; IIEF erectile "
     "function domain, SEP2 and SEP3 success rates and the global assessment "
     "question.", "pharmacologic"),
    ("Low-intensity extracorporeal shockwave therapy (Li-ESWT) versus sham for "
     "erectile dysfunction; IIEF-EF and erection hardness score.", "shockwave"),
    ("Vacuum erection device versus penile prosthesis for erectile dysfunction; "
     "IIEF-EF and treatment satisfaction (EDITS).", "device"),
    ("Adverse events of sildenafil; headache, flushing, dyspepsia and nasal "
     "congestion.", "safety"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_erectile_dysfunction_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("international index of erectile function", "IIEF_EF"),
    ("SEP question 2", "SEP2"),
    ("SEP question 3", "SEP3"),
    ("global assessment question", "GAQ"),
    ("erection hardness score", "EHS"),
    ("treatment satisfaction", "TREATMENT_SATISFACTION"),
    ("headache", "HEADACHE"),
    ("facial flushing", "FLUSHING"),
    ("nasal congestion", "NASAL_CONGESTION"),
    ("priapism", "PRIAPISM"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_erectile_dysfunction_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"pharmacologic", "shockwave", "device", "safety"}
    for name, info in ERECTILE_DYSFUNCTION_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_erectile_dysfunction_registered():
    assert "erectile_dysfunction" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["erectile_dysfunction"]
    assert e["detection_function"] is detect_erectile_dysfunction_subspecialty
    assert e["normalizer"] is normalize_erectile_dysfunction_endpoint
    assert set(e["subspecialties"]) == {"pharmacologic", "shockwave", "device", "safety"}


def test_detect_specialty_routes_to_erectile_dysfunction():
    spec, sub, _ = detect_specialty(
        "randomized double-blind placebo-controlled trial of sildenafil for erectile "
        "dysfunction; international index of erectile function (IIEF) erectile "
        "function domain, SEP2 and SEP3")
    assert spec == "erectile_dysfunction" and sub == "pharmacologic"


def test_ed_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "abiraterone for metastatic castration-resistant prostate cancer; overall "
        "survival and PSA progression")[0] == "prostate_cancer"
    assert detect_specialty(
        "single-dose HPV vaccine; persistent HPV-16/18 infection and CIN2+")[0] == \
        "cervical_cancer"


# --- arm-level extraction ---

def test_sep3_2x2():
    t = ("Successful intercourse (SEP3) was achieved in 145/200 (72.5%) in the "
         "tadalafil group and 60/198 (30.3%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "SEP3"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"tadalafil", "placebo"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (145, 200)


def test_iief_ef_continuous():
    r = extract_continuous("Mean IIEF erectile function domain score was 24.1 ± 5.2 "
                           "in the sildenafil group and 14.3 ± 6.1 in the placebo group")
    assert r and r[0]["endpoint"] == "IIEF_EF"
    assert r[0]["stat"] == "mean_sd" and r[0]["poolable"] is True


def test_headache_2x2():
    t = ("Headache was reported in 30/200 (15.0%) in the sildenafil group and "
         "8/198 (4.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "HEADACHE"
