"""
Tests for the otitis-media (middle-ear) specialty profile (aom / ome /
prevention), registry wiring, and arm-level extraction. Mirrors the
pneumonia / allergic_rhinitis tests.

Routing note: middle-ear keywords (otitis media, AOM, OME, glue ear,
tympanostomy tube/grommet, myringotomy, middle-ear effusion, otorrho?ea,
tympanic membrane) are claimed by no existing profile. The tests below ground
that contract against real detect_specialty output. British/American: ear
discharge is otorrhoea (UK) vs otorrhea (US) -> 'otorrho?ea'.
"""
import pytest

from rct_extractor._engine.specialties.otitis_media import (
    OTITIS_MEDIA_ENDPOINTS, detect_otitis_media_subspecialty,
    normalize_otitis_media_endpoint, get_otitis_media_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.otitis_media_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Amoxicillin versus placebo for acute otitis media in children; clinical treatment "
     "failure and ear pain were the primary outcomes, with otorrhoea as a secondary.", "aom"),
    ("Tympanostomy tubes versus watchful waiting for otitis media with effusion (glue ear); "
     "middle-ear effusion resolution and hearing level on audiometry.", "ome"),
    ("Pneumococcal conjugate vaccine versus placebo to prevent recurrent acute otitis media; "
     "AOM recurrence rate per child-year.", "prevention"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_otitis_media_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("clinical treatment failure", "TREATMENT_FAILURE"),
    ("clinical cure", "CLINICAL_CURE"),
    ("AOM recurrence", "AOM_RECURRENCE"),
    ("middle ear effusion", "EFFUSION_RESOLUTION"),
    ("otorrhoea", "OTORRHOEA"),
    ("otorrhea", "OTORRHOEA"),
    ("hearing level", "HEARING_LEVEL"),
    ("ear pain", "EAR_PAIN"),
    ("tympanostomy tube", "TUBE_INSERTION"),
    ("grommet", "TUBE_INSERTION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_otitis_media_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"aom", "ome", "prevention"}
    for name, info in OTITIS_MEDIA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_subspecialty_patterns_cover_all_three():
    for sub in ("aom", "ome", "prevention"):
        assert get_otitis_media_endpoint_patterns(sub), sub


# --- British/American spelling trap (otorrhoea inserts an extra 'o') ---

def test_british_american_otorrhoea():
    assert normalize_otitis_media_endpoint("acute otorrhoea") == \
        normalize_otitis_media_endpoint("acute otorrhea") == "OTORRHOEA"


# --- registry wiring ---

def test_otitis_media_registered():
    assert "otitis_media" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["otitis_media"]
    assert e["detection_function"] is detect_otitis_media_subspecialty
    assert e["normalizer"] is normalize_otitis_media_endpoint
    assert set(e["subspecialties"]) == {"aom", "ome", "prevention"}


def test_detect_specialty_routes_to_otitis_media():
    spec, sub, _ = detect_specialty(
        "Amoxicillin-clavulanate versus placebo for acute otitis media in young children; "
        "the primary outcome was clinical treatment failure, with ear pain and otorrhoea "
        "as secondary middle-ear outcomes.")
    assert spec == "otitis_media" and sub == "aom"


def test_otitis_media_does_not_break_neighbors():
    assert detect_specialty(
        "ceftriaxone versus penicillin for bacterial meningitis; mortality and neurological "
        "sequelae")[0] == "meningitis"
    assert detect_specialty(
        "amoxicillin for community-acquired pneumonia; clinical cure and chest radiograph "
        "resolution with respiratory rate")[0] == "pneumonia"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"


# --- arm-level extraction ---

def test_treatment_failure_2x2():
    t = ("Clinical treatment failure occurred in 30/150 (20.0%) in the amoxicillin group "
         "and in 60/150 (40.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "TREATMENT_FAILURE"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"amoxicillin", "placebo"}


def test_hearing_level_continuous_poolable():
    r = extract_continuous("the mean hearing level was 25.0 ± 6.0 dB in the tympanostomy-tubes arm")
    assert r and r[0]["endpoint"] == "HEARING_LEVEL" and r[0]["poolable"] is True
    assert r[0].get("pooling_note") is None


def test_ear_pain_continuous_poolable():
    r = extract_continuous("the mean ear pain score was 1.5 ± 0.7 in the amoxicillin arm")
    assert r and r[0]["endpoint"] == "EAR_PAIN" and r[0]["poolable"] is True
