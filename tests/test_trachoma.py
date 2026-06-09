"""
Tests for the trachoma specialty profile, registry wiring, and arm-level
extraction. Mirrors the HIV, malaria, typhoid and schistosomiasis tests.
"""
import pytest

from src.specialties.trachoma import (
    TRACHOMA_ENDPOINTS, detect_trachoma_subspecialty,
    normalize_trachoma_endpoint, get_trachoma_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.trachoma_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Cluster-randomised trial of azithromycin mass drug administration versus "
     "tetracycline eye ointment for active trachoma; trachomatous inflammation-"
     "follicular (TF) prevalence and ocular chlamydia infection by PCR.", "mda"),
    ("Bilamellar tarsal rotation versus epilation for trachomatous trichiasis (TT); "
     "post-operative trichiasis recurrence and corneal opacity at 12 months.",
     "surgery"),
    ("Facial cleanliness and environmental improvement (F&E) with fly control; "
     "clean face, ocular discharge, Musca sorbens fly density and reinfection.",
     "transmission"),
    ("Azithromycin MDA and childhood mortality (MORDOR); all-cause under-5 "
     "mortality, serious adverse events and nasopharyngeal macrolide resistance.",
     "mortality_safety"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_trachoma_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("active trachoma prevalence", "ACTIVE_TRACHOMA"),
    ("trachomatous inflammation-follicular", "ACTIVE_TRACHOMA"),
    ("ocular chlamydial infection", "OCULAR_CHLAMYDIA"),
    ("chlamydial load", "INFECTION_LOAD"),
    ("trachomatous trichiasis", "TRICHIASIS"),
    ("trichiasis recurrence", "TRICHIASIS_RECURRENCE"),
    ("corneal opacity", "CORNEAL_OPACITY"),
    ("best-corrected visual acuity", "VISUAL_ACUITY"),
    ("facial cleanliness", "CLEAN_FACE"),
    ("childhood mortality", "MORTALITY"),
    ("macrolide resistance", "MACROLIDE_RESISTANCE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_trachoma_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in TRACHOMA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"mda", "surgery", "transmission", "mortality_safety"}


# --- registry wiring ---

def test_trachoma_registered():
    assert "trachoma" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["trachoma"]
    assert e["detection_function"] is detect_trachoma_subspecialty
    assert e["normalizer"] is normalize_trachoma_endpoint
    assert set(e["subspecialties"]) == {"mda", "surgery", "transmission", "mortality_safety"}


def test_detect_specialty_routes_to_trachoma():
    spec, sub, _ = detect_specialty(
        "Azithromycin mass drug administration versus tetracycline eye ointment "
        "for active trachoma; trachomatous inflammation-follicular (TF) prevalence "
        "and ocular chlamydia trachomatis infection by PCR")
    assert spec == "trachoma" and sub == "mda"


def test_trachoma_surgery_routes():
    spec, sub, _ = detect_specialty(
        "Bilamellar tarsal rotation (BLTR) versus epilation for trachomatous "
        "trichiasis; trichiasis recurrence and corneal opacity in a trachoma-"
        "endemic district")
    assert spec == "trachoma" and sub == "surgery"


def test_trachoma_normalizer_via_registry():
    assert normalize_endpoint_by_specialty(
        "trichiasis recurrence", "trachoma") == "TRICHIASIS_RECURRENCE"
    assert "trachoma" not in {None}
    assert "ACTIVE_TRACHOMA" in get_all_endpoints("trachoma")


def test_trachoma_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "azithromycin versus ceftriaxone for blood-culture-confirmed typhoid "
        "fever; fever clearance time")[0] == "typhoid"
    assert detect_specialty(
        "oral cholera vaccine (Shanchol) versus placebo; vibriocidal seroconversion "
        "and protective efficacy against Vibrio cholerae")[0] == "cholera"
    assert detect_specialty(
        "praziquantel for Schistosoma mansoni; parasitological cure and egg "
        "reduction rate by Kato-Katz")[0] == "schistosomiasis"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_active_trachoma_2x2():
    t = ("Active trachoma (TF) was present in 30/200 (15.0%) in the azithromycin "
         "group and 60/200 (30.0%) in the tetracycline group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "ACTIVE_TRACHOMA"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"azithromycin", "tetracycline"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (30, 200)


def test_trichiasis_recurrence_2x2():
    t = ("Trichiasis recurrence occurred in 18/120 (15.0%) after bilamellar tarsal "
         "rotation versus 36/120 (30.0%) after epilation")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "TRICHIASIS_RECURRENCE"


def test_childhood_mortality_2x2():
    t = ("Childhood mortality was 40/1000 (4.0%) in the azithromycin group versus "
         "55/1000 (5.5%) in the placebo group")
    tabs = extract_arm_level(t)["tables_2x2"]
    assert tabs and tabs[0]["endpoint"] == "MORTALITY"


def test_infection_load_is_lognormal():
    r = extract_continuous("mean chlamydial load 250 ± 80 in the azithromycin arm")
    assert r and r[0]["endpoint"] == "INFECTION_LOAD" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]


def test_visual_acuity_continuous_poolable():
    r = extract_continuous("mean visual acuity 0.30 ± 0.15 logMAR in the azithromycin arm")
    assert r and r[0]["endpoint"] == "VISUAL_ACUITY" and r[0]["poolable"] is True
