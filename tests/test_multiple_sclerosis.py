"""
Tests for the multiple sclerosis specialty profile, registry wiring, and
arm-level extraction. Mirrors the tuberculosis / parkinsons tests.
"""
import pytest

from rct_extractor._engine.specialties.multiple_sclerosis import (
    MULTIPLE_SCLEROSIS_ENDPOINTS, detect_multiple_sclerosis_subspecialty,
    normalize_multiple_sclerosis_endpoint, get_multiple_sclerosis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.multiple_sclerosis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


@pytest.mark.parametrize("text,expected", [
    ("Ocrelizumab versus interferon beta-1a in relapsing-remitting multiple "
     "sclerosis (RRMS); annualized relapse rate and gadolinium-enhancing lesions.",
     "relapsing"),
    ("Siponimod versus placebo in secondary progressive multiple sclerosis (SPMS); "
     "3-month confirmed disability progression on EDSS.", "progressive"),
    ("Dalfampridine versus placebo in multiple sclerosis; timed 25-foot walk and "
     "walking speed improvement.", "symptomatic"),
    ("Intravenous methylprednisolone versus plasma exchange for acute relapse in "
     "multiple sclerosis; recovery from relapse.", "acute_relapse"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_multiple_sclerosis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("annualized relapse rate", "ARR"),
    ("3-month confirmed disability progression", "CDP"),
    ("gadolinium-enhancing lesions", "GAD_LESIONS"),
    ("new or enlarging T2 lesions", "T2_LESIONS"),
    ("no evidence of disease activity", "NEDA"),
    ("timed 25-foot walk", "T25FW"),
    ("symbol digit modalities test", "SDMT"),
    ("percentage brain volume change", "BRAIN_ATROPHY"),
    ("change in EDSS", "EDSS_CHANGE"),
    ("recovery from relapse", "RELAPSE_RECOVERY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_multiple_sclerosis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in MULTIPLE_SCLEROSIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"relapsing", "progressive", "symptomatic",
                                        "acute_relapse"}


def test_ms_registered():
    assert "multiple_sclerosis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["multiple_sclerosis"]
    assert e["detection_function"] is detect_multiple_sclerosis_subspecialty
    assert e["normalizer"] is normalize_multiple_sclerosis_endpoint
    assert set(e["subspecialties"]) == {"relapsing", "progressive", "symptomatic",
                                        "acute_relapse"}


def test_detect_specialty_routes_to_ms():
    spec, sub, _ = detect_specialty(
        "Ofatumumab versus teriflunomide in relapsing-remitting multiple sclerosis; "
        "annualized relapse rate and new or enlarging T2 lesions over 2 years")
    assert spec == "multiple_sclerosis" and sub == "relapsing"


def test_ms_wins_over_generic_neurology():
    spec, _, _ = detect_specialty(
        "natalizumab for relapsing multiple sclerosis; EDSS and relapse rate")
    assert spec == "multiple_sclerosis"


def test_ms_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


def test_neda_2x2():
    t = ("NEDA-3 was achieved by 188/400 (47.0%) in the ocrelizumab group and "
         "116/410 (28.3%) in the interferon beta group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "NEDA"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"ocrelizumab", "interferon-beta"}


def test_edss_change_continuous():
    rows = extract_continuous(
        "Mean change in EDSS was 0.10 (SD 0.6) in the siponimod arm and 0.35 "
        "(SD 0.7) in the placebo arm")
    assert any(r["endpoint"] == "EDSS_CHANGE" for r in rows)
