"""
Tests for the chronic-rhinosinusitis (CRS) specialty profile (crswnp / crssnp /
surgery), registry wiring, and arm-level extraction. Mirrors the
allergic_rhinitis / ophthalmology tests.

Routing note: CRS keywords (chronic rhinosinusitis, nasal polyp(s)/polyposis,
SNOT-22, Lund-Mackay, Lund-Kennedy, functional endoscopic sinus surgery / FESS)
are distinct from the nasal allergic_rhinitis profile (hay fever, TNSS,
immunotherapy) and the lower-airway respiratory profile (COPD, asthma, FEV1).
The tests below ground that contract against real detect_specialty output.
"""
import pytest

from rct_extractor._engine.specialties.chronic_rhinosinusitis import (
    CHRONIC_RHINOSINUSITIS_ENDPOINTS, detect_chronic_rhinosinusitis_subspecialty,
    normalize_chronic_rhinosinusitis_endpoint,
    get_chronic_rhinosinusitis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.chronic_rhinosinusitis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Dupilumab versus placebo in chronic rhinosinusitis with nasal polyps (CRSwNP); "
     "nasal polyp score and SNOT-22 were co-primary endpoints, with loss of smell.",
     "crswnp"),
    ("Intranasal mometasone versus saline irrigation in chronic rhinosinusitis without "
     "nasal polyps; SNOT-22 and Lund-Mackay CT score.", "crssnp"),
    ("Functional endoscopic sinus surgery versus medical therapy in chronic rhinosinusitis; "
     "Lund-Kennedy endoscopic score and revision surgery at two years.", "surgery"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_chronic_rhinosinusitis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("SNOT-22", "SNOT22"),
    ("sino-nasal outcome test", "SNOT22"),
    ("nasal polyp score", "NPS"),
    ("nasal congestion", "NASAL_CONGESTION"),
    ("loss of smell", "SMELL"),
    ("Lund-Mackay CT score", "LUND_MACKAY"),
    ("Lund-Kennedy endoscopic score", "LUND_KENNEDY"),
    ("rescue surgery", "RESCUE_INTERVENTION"),
    ("revision surgery", "REVISION_SURGERY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_chronic_rhinosinusitis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"crswnp", "crssnp", "surgery"}
    for name, info in CHRONIC_RHINOSINUSITIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_subspecialty_patterns_cover_all_three():
    for sub in ("crswnp", "crssnp", "surgery"):
        assert get_chronic_rhinosinusitis_endpoint_patterns(sub), sub


# --- registry wiring ---

def test_chronic_rhinosinusitis_registered():
    assert "chronic_rhinosinusitis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["chronic_rhinosinusitis"]
    assert e["detection_function"] is detect_chronic_rhinosinusitis_subspecialty
    assert e["normalizer"] is normalize_chronic_rhinosinusitis_endpoint
    assert set(e["subspecialties"]) == {"crswnp", "crssnp", "surgery"}


def test_detect_specialty_routes_to_chronic_rhinosinusitis():
    spec, sub, _ = detect_specialty(
        "Dupilumab versus placebo in adults with chronic rhinosinusitis with nasal polyps; "
        "the co-primary endpoints were nasal polyp score and nasal congestion, with SNOT-22 "
        "and loss of smell as secondary outcomes.")
    assert spec == "chronic_rhinosinusitis" and sub == "crswnp"


def test_chronic_rhinosinusitis_does_not_break_neighbors():
    # Nasal allergic rhinitis (hay fever) must still route to allergic_rhinitis.
    assert detect_specialty(
        "Grass-pollen sublingual immunotherapy tablet versus placebo for allergic "
        "rhinitis; combined symptom and medication score and total nasal symptom "
        "score")[0] == "allergic_rhinitis"
    # Lower-airway asthma must still route to respiratory.
    assert detect_specialty(
        "Budesonide/formoterol versus placebo in asthma; FEV1 and annual exacerbation "
        "rate were the primary outcomes")[0] == "respiratory"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"


# --- arm-level extraction ---

def test_rescue_intervention_2x2():
    t = ("Rescue surgery was required in 18/120 (15.0%) in the dupilumab group and in "
         "48/120 (40.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "RESCUE_INTERVENTION"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"dupilumab", "placebo"}


def test_snot22_continuous_poolable():
    r = extract_continuous("the mean SNOT-22 score was 22.5 ± 8.0 in the dupilumab arm")
    assert r and r[0]["endpoint"] == "SNOT22" and r[0]["poolable"] is True
    assert r[0].get("pooling_note") is None


def test_nps_continuous_poolable():
    r = extract_continuous("the mean nasal polyp score was 3.5 ± 1.2 in the mometasone arm")
    assert r and r[0]["endpoint"] == "NPS" and r[0]["poolable"] is True
