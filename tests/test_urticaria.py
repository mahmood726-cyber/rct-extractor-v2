"""
Tests for the chronic-urticaria / anaphylaxis specialty profile, registry
wiring, and arm-level extraction. Mirrors the tuberculosis / ARDS tests.
"""
import pytest

from rct_extractor._engine.specialties.urticaria import (
    URTICARIA_ENDPOINTS, detect_urticaria_subspecialty,
    normalize_urticaria_endpoint, get_urticaria_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.urticaria_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Updosed bilastine versus standard-dose levocetirizine for chronic spontaneous "
     "urticaria; weekly urticaria activity score (UAS7) and itch severity score.",
     "antihistamine"),
    ("Remibrutinib versus placebo for antihistamine-refractory chronic spontaneous "
     "urticaria; UAS7 and urticaria control test with this BTK inhibitor.", "biologic"),
    ("Intranasal epinephrine auto-injector for anaphylaxis; symptom resolution and "
     "biphasic reaction in food allergy.", "anaphylaxis"),
    ("Ciclosporin for chronic inducible urticaria including cold urticaria and "
     "symptomatic dermographism; critical temperature threshold.", "other"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_urticaria_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("urticaria activity score", "UAS7"),
    ("itch severity score", "ISS7"),
    ("hives severity score", "HSS7"),
    ("urticaria control test", "UCT"),
    ("complete response", "COMPLETE_RESPONSE"),
    ("well-controlled", "WELL_CONTROLLED"),
    ("angioedema activity score", "ANGIOEDEMA"),
    ("dermatology life quality index", "DLQI"),
    ("biphasic reaction", "ANAPHYLAXIS_RECURRENCE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_urticaria_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in URTICARIA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"antihistamine", "biologic", "anaphylaxis", "other"}


# --- registry wiring ---

def test_urticaria_registered():
    assert "urticaria" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["urticaria"]
    assert e["detection_function"] is detect_urticaria_subspecialty
    assert e["normalizer"] is normalize_urticaria_endpoint
    assert set(e["subspecialties"]) == {"antihistamine", "biologic", "anaphylaxis", "other"}


def test_detect_specialty_routes_to_urticaria():
    spec, sub, _ = detect_specialty(
        "Omalizumab versus placebo for chronic spontaneous urticaria; weekly "
        "urticaria activity score (UAS7) and urticaria control test")
    assert spec == "urticaria"


def test_urticaria_does_not_break_malaria_hiv_or_cardio():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in chronic heart failure; cardiovascular death and "
        "heart-failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_complete_response_2x2():
    t = ("Complete response: omalizumab 70/162 (43.2%) "
         "versus placebo 8/80 (10.0%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs
    t0 = tabs[0]
    assert t0["endpoint"] == "COMPLETE_RESPONSE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"omalizumab", "placebo"}


def test_well_controlled_2x2():
    t = ("Well-controlled disease: remibrutinib 90/150 (60.0%) versus placebo 18/75 (24.0%)")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "WELL_CONTROLLED"


def test_uas7_continuous():
    t = ("The change in UAS7 was -19.2 (SD 10.5) with omalizumab and -8.1 (SD 9.4) "
         "with placebo")
    cont = extract_continuous(t)
    assert any(c["endpoint"] == "UAS7" for c in cont)
