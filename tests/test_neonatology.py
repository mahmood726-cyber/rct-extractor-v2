"""
Tests for the neonatology (NICU) specialty profile, registry wiring, and arm-level
extraction. Includes a check that NICU-complication trials route away from the
obstetric maternal_neonatal specialty (shared neonatal-outcome vocabulary).
"""
import pytest

from rct_extractor._engine.specialties.neonatology import (
    NEONATOLOGY_ENDPOINTS, detect_neonatology_subspecialty,
    normalize_neonatology_endpoint, get_neonatology_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.neonatology_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("surfactant versus CPAP in preterm infants; bronchopulmonary dysplasia and "
     "respiratory distress syndrome.", "respiratory"),
    ("probiotics in very low birth weight infants; necrotising enterocolitis and "
     "spontaneous intestinal perforation.", "gastrointestinal"),
    ("therapeutic hypothermia for hypoxic-ischaemic encephalopathy; intraventricular "
     "haemorrhage, periventricular leukomalacia and cerebral palsy.", "neurological"),
    ("prophylactic indomethacin in preterm neonates; retinopathy of prematurity, "
     "patent ductus arteriosus and late-onset sepsis.", "complications"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_neonatology_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("bronchopulmonary dysplasia", "BRONCHOPULMONARY_DYSPLASIA"),
    ("necrotising enterocolitis", "NECROTISING_ENTEROCOLITIS"),
    ("necrotizing enterocolitis", "NECROTISING_ENTEROCOLITIS"),
    ("intraventricular haemorrhage", "INTRAVENTRICULAR_HAEMORRHAGE"),
    ("intraventricular hemorrhage", "INTRAVENTRICULAR_HAEMORRHAGE"),
    ("retinopathy of prematurity", "RETINOPATHY_OF_PREMATURITY"),
    ("patent ductus arteriosus", "PATENT_DUCTUS_ARTERIOSUS"),
    ("periventricular leucomalacia", "PERIVENTRICULAR_LEUKOMALACIA"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_neonatology_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"respiratory", "gastrointestinal", "neurological", "complications"}
    for name, info in NEONATOLOGY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_neonatology_registered():
    assert "neonatology" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["neonatology"]
    assert e["detection_function"] is detect_neonatology_subspecialty
    assert e["normalizer"] is normalize_neonatology_endpoint
    assert set(e["subspecialties"]) == {"respiratory", "gastrointestinal", "neurological", "complications"}


def test_detect_specialty_routes_to_neonatology():
    spec, sub, _ = detect_specialty(
        "preterm infants randomized to surfactant versus nasal CPAP; bronchopulmonary "
        "dysplasia, necrotising enterocolitis, intraventricular haemorrhage and "
        "retinopathy of prematurity")
    assert spec == "neonatology"


def test_neonatology_vs_maternal_neonatal_disambiguation():
    # NICU-complication trial -> neonatology, not maternal_neonatal
    assert detect_specialty(
        "very low birth weight infants randomized to probiotics; necrotising "
        "enterocolitis, late-onset sepsis and bronchopulmonary dysplasia in the NICU"
    )[0] == "neonatology"
    # obstetric / birth-outcome trial -> stays maternal_neonatal
    if "maternal_neonatal" in SPECIALTY_REGISTRY:
        assert detect_specialty(
            "antenatal corticosteroids before preterm birth; stillbirth, perinatal "
            "mortality and pre-eclampsia in pregnant women")[0] == "maternal_neonatal"


def test_neonatology_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_bpd_2x2():
    t = ("Bronchopulmonary dysplasia occurred in 40/200 (20.0%) of CPAP infants and "
         "70/200 (35.0%) of surfactant infants")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "BRONCHOPULMONARY_DYSPLASIA"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"cpap", "surfactant"}


def test_nec_2x2():
    t = ("Necrotising enterocolitis occurred in 12/250 (4.8%) of probiotics infants "
         "and 28/250 (11.2%) of placebo infants")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "NECROTISING_ENTEROCOLITIS"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"probiotics", "placebo"}


def test_rop_2x2():
    t = ("Retinopathy of prematurity occurred in 18/120 (15.0%) of caffeine infants "
         "and 30/120 (25.0%) of placebo infants")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "RETINOPATHY_OF_PREMATURITY"
