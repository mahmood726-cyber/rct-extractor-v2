"""
Tests for the allergic-conjunctivitis (ocular allergy) specialty profile
(seasonal_perennial / vernal_atopic / challenge_model), registry wiring, and
arm-level extraction. Mirrors the ophthalmology / allergic_rhinitis tests.

Routing note: ocular-allergy keywords (allergic conjunctivitis, ocular allergy,
conjunctival allergen challenge, ocular itching, conjunctival hypera?emia,
vernal/atopic keratoconjunctivitis, ocular antihistamine drops) are distinct from
both the nasal allergic_rhinitis profile (TNSS, immunotherapy) and the generic
ophthalmology profile (AMD/glaucoma/dry eye). The tests below ground that
contract against real detect_specialty output.
"""
import pytest

from rct_extractor._engine.specialties.allergic_conjunctivitis import (
    ALLERGIC_CONJUNCTIVITIS_ENDPOINTS, detect_allergic_conjunctivitis_subspecialty,
    normalize_allergic_conjunctivitis_endpoint,
    get_allergic_conjunctivitis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.allergic_conjunctivitis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Olopatadine versus placebo for seasonal allergic conjunctivitis; ocular itching "
     "and conjunctival hyperaemia were the primary outcomes.", "seasonal_perennial"),
    ("Ciclosporin eye drops versus vehicle in vernal keratoconjunctivitis (VKC); corneal "
     "involvement, shield ulcer healing and ocular itching.", "vernal_atopic"),
    ("Bepotastine versus placebo in a conjunctival allergen challenge (CAC) model; onset "
     "ocular itching score 3 minutes post-challenge and conjunctival hyperaemia.",
     "challenge_model"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_allergic_conjunctivitis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("ocular itching", "OCULAR_ITCHING"),
    ("conjunctival hyperaemia", "CONJUNCTIVAL_HYPERAEMIA"),
    ("conjunctival hyperemia", "CONJUNCTIVAL_HYPERAEMIA"),
    ("ocular redness", "CONJUNCTIVAL_HYPERAEMIA"),
    ("tearing", "TEARING"),
    ("lacrimation", "TEARING"),
    ("chemosis", "CHEMOSIS"),
    ("eyelid swelling", "EYELID_SWELLING"),
    ("total ocular symptom score", "TOSS"),
    ("symptom responder", "SYMPTOM_RESPONDER"),
    ("corneal involvement", "CORNEAL_INVOLVEMENT"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_allergic_conjunctivitis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"seasonal_perennial", "vernal_atopic", "challenge_model"}
    for name, info in ALLERGIC_CONJUNCTIVITIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_subspecialty_patterns_cover_all_three():
    for sub in ("seasonal_perennial", "vernal_atopic", "challenge_model"):
        assert get_allergic_conjunctivitis_endpoint_patterns(sub), sub


# --- British/American spelling trap (hyperaemia inserts an extra 'a') ---

def test_british_american_hyperaemia():
    # Both spellings must normalize identically; the pattern uses 'hypera?emia'.
    assert normalize_allergic_conjunctivitis_endpoint("conjunctival hyperaemia") == \
        normalize_allergic_conjunctivitis_endpoint("conjunctival hyperemia")


# --- registry wiring ---

def test_allergic_conjunctivitis_registered():
    assert "allergic_conjunctivitis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["allergic_conjunctivitis"]
    assert e["detection_function"] is detect_allergic_conjunctivitis_subspecialty
    assert e["normalizer"] is normalize_allergic_conjunctivitis_endpoint
    assert set(e["subspecialties"]) == {"seasonal_perennial", "vernal_atopic", "challenge_model"}


def test_detect_specialty_routes_to_allergic_conjunctivitis():
    spec, sub, _ = detect_specialty(
        "Olopatadine ophthalmic solution versus placebo for seasonal allergic "
        "conjunctivitis; the primary outcome was ocular itching with conjunctival "
        "hyperaemia and tearing as secondary ocular symptoms.")
    assert spec == "allergic_conjunctivitis" and sub == "seasonal_perennial"


def test_allergic_conjunctivitis_does_not_break_neighbors():
    # Nasal allergic rhinitis must still route to allergic_rhinitis.
    assert detect_specialty(
        "Grass-pollen sublingual immunotherapy tablet versus placebo for allergic "
        "rhinitis; combined symptom and medication score and total nasal symptom "
        "score")[0] == "allergic_rhinitis"
    # Ophthalmology AMD must still route to ophthalmology.
    assert detect_specialty(
        "Aflibercept versus ranibizumab in neovascular age-related macular degeneration; "
        "intravitreal anti-VEGF, best-corrected visual acuity (ETDRS letters) and central "
        "retinal thickness on OCT.")[0] == "ophthalmology"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"


# --- arm-level extraction ---

def test_symptom_responder_2x2():
    t = ("A composite symptom responder was achieved in 96/120 (80.0%) in the olopatadine "
         "group and in 60/120 (50.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "SYMPTOM_RESPONDER"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"olopatadine", "placebo"}


def test_ocular_itching_continuous_poolable():
    r = extract_continuous("the mean ocular itching score was 1.2 ± 0.6 in the bepotastine arm")
    assert r and r[0]["endpoint"] == "OCULAR_ITCHING" and r[0]["poolable"] is True
    assert r[0].get("pooling_note") is None


def test_hyperaemia_continuous_poolable():
    r = extract_continuous("the mean conjunctival hyperaemia score was 0.9 ± 0.4 in the "
                           "ketotifen arm")
    assert r and r[0]["endpoint"] == "CONJUNCTIVAL_HYPERAEMIA" and r[0]["poolable"] is True
