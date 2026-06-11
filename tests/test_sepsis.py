"""
Tests for the sepsis / septic shock specialty profile, registry wiring, and
arm-level extraction. Mirrors the tuberculosis / parkinsons tests.
"""
import pytest

from rct_extractor._engine.specialties.sepsis import (
    SEPSIS_ENDPOINTS, detect_sepsis_subspecialty,
    normalize_sepsis_endpoint, get_sepsis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.sepsis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


@pytest.mark.parametrize("text,expected", [
    ("Norepinephrine plus early vasopressin versus norepinephrine alone in septic "
     "shock; 28-day mortality and vasopressor-free days.", "hemodynamic"),
    ("Hydrocortisone plus fludrocortisone versus placebo in septic shock; "
     "metabolic resuscitation and 90-day mortality.", "adjunctive"),
    ("Procalcitonin-guided antibiotic therapy versus standard care in sepsis; "
     "antibiotic duration and source control.", "antimicrobial_source"),
    ("Early versus delayed renal replacement therapy in sepsis-associated acute "
     "kidney injury; ventilator-free days and SOFA score.", "organ_support"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_sepsis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("28-day mortality", "MORTALITY_28"),
    ("90-day all-cause mortality", "MORTALITY_90"),
    ("time to shock reversal", "SHOCK_REVERSAL"),
    ("vasopressor-free days", "VASOPRESSOR_FREE_DAYS"),
    ("ventilator-free days", "VENTILATOR_FREE_DAYS"),
    ("renal replacement therapy", "AKI_RRT"),
    ("SOFA score", "SOFA"),
    ("antibiotic duration", "ANTIBIOTIC_DURATION"),
    ("ICU length of stay", "LENGTH_OF_STAY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_sepsis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in SEPSIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"hemodynamic", "adjunctive",
                                        "antimicrobial_source", "organ_support"}


def test_sepsis_registered():
    assert "sepsis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["sepsis"]
    assert e["detection_function"] is detect_sepsis_subspecialty
    assert e["normalizer"] is normalize_sepsis_endpoint
    assert set(e["subspecialties"]) == {"hemodynamic", "adjunctive",
                                        "antimicrobial_source", "organ_support"}


def test_detect_specialty_routes_to_sepsis():
    spec, sub, _ = detect_specialty(
        "Vasopressin versus norepinephrine in septic shock; 28-day mortality and "
        "vasopressor-free days")
    assert spec == "sepsis" and sub == "hemodynamic"


def test_sepsis_wins_over_generic_infectious_disease():
    spec, _, _ = detect_specialty(
        "early antibiotics for sepsis; bacterial infection; 28-day mortality and SOFA")
    assert spec == "sepsis"


def test_sepsis_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


def test_mortality_2x2():
    t = ("28-day mortality was 308/1000 (30.8%) in the vasopressin group and "
         "338/1000 (33.8%) in the norepinephrine group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    # nearest-keyword tagging may resolve to the generic MORTALITY or the
    # 28-day-specific MORTALITY_28; both are valid mortality labels.
    assert tabs and tabs[0]["endpoint"] in {"MORTALITY_28", "MORTALITY"}
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"vasopressin", "norepinephrine"}


def test_sofa_continuous():
    rows = extract_continuous(
        "Mean SOFA score was 7.2 (SD 3.1) in the hydrocortisone arm and 8.5 "
        "(SD 3.4) in the placebo arm")
    assert any(r["endpoint"] == "SOFA" for r in rows)
