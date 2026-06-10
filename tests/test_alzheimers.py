"""
Tests for the Alzheimer's disease / dementia specialty profile, registry wiring,
and arm-level extraction. Mirrors the tuberculosis / parkinsons tests.
"""
import pytest

from rct_extractor._engine.specialties.alzheimers import (
    ALZHEIMERS_ENDPOINTS, detect_alzheimers_subspecialty,
    normalize_alzheimers_endpoint, get_alzheimers_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.alzheimers_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


@pytest.mark.parametrize("text,expected", [
    ("Donepezil versus placebo in mild-to-moderate Alzheimer disease; change in "
     "ADAS-Cog and ADCS-ADL with this cholinesterase inhibitor.", "symptomatic"),
    ("Lecanemab versus placebo in early Alzheimer disease; CDR-SB change, amyloid "
     "PET centiloids and ARIA-E with this anti-amyloid monoclonal antibody.",
     "disease_modifying"),
    ("Brexpiprazole versus placebo for agitation in Alzheimer dementia; change in "
     "CMAI and neuropsychiatric inventory (NPI).", "neuropsychiatric"),
    ("Trial in cognitively unimpaired amyloid-positive participants; prevention of "
     "progression to dementia and time to dementia diagnosis.", "prevention_mci"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_alzheimers_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("ADAS-Cog13", "ADAS_COG"),
    ("CDR sum of boxes", "CDR_SB"),
    ("Mini-Mental State Examination", "MMSE"),
    ("ADCS-ADL", "ADCS_ADL"),
    ("amyloid PET centiloids", "AMYLOID_PET"),
    ("amyloid-related imaging abnormalities", "ARIA"),
    ("neuropsychiatric inventory", "NPI"),
    ("Cohen-Mansfield agitation inventory", "AGITATION"),
    ("progression to dementia", "PROGRESSION_TO_DEMENTIA"),
    ("integrated Alzheimer disease rating scale", "IADRS"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_alzheimers_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in ALZHEIMERS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"symptomatic", "disease_modifying",
                                        "neuropsychiatric", "prevention_mci"}


def test_alzheimers_registered():
    assert "alzheimers" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["alzheimers"]
    assert e["detection_function"] is detect_alzheimers_subspecialty
    assert e["normalizer"] is normalize_alzheimers_endpoint
    assert set(e["subspecialties"]) == {"symptomatic", "disease_modifying",
                                        "neuropsychiatric", "prevention_mci"}


def test_detect_specialty_routes_to_alzheimers():
    spec, sub, _ = detect_specialty(
        "Lecanemab in early Alzheimer disease; CDR-SB change, amyloid PET "
        "centiloids and ARIA over 18 months")
    assert spec == "alzheimers" and sub == "disease_modifying"


def test_alzheimers_wins_over_generic_neurology():
    spec, _, _ = detect_specialty(
        "donepezil for Alzheimer disease dementia; ADAS-Cog and MMSE change")
    assert spec == "alzheimers"


def test_alzheimers_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


def test_aria_2x2():
    t = ("ARIA-E occurred in 50/400 (12.5%) in the lecanemab group and 7/398 "
         "(1.8%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ARIA"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"lecanemab", "placebo"}


def test_adas_cog_continuous():
    rows = extract_continuous(
        "Mean ADAS-Cog change was -2.8 (SD 5.1) in the donepezil arm and -0.5 "
        "(SD 5.4) in the placebo arm")
    assert any(r["endpoint"] == "ADAS_COG" for r in rows)
