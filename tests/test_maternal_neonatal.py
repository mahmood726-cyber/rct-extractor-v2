"""
Tests for the maternal & neonatal health specialty profile, registry wiring, and
arm-level extraction. Mirrors the HIV, malaria and typhoid tests.
"""
import pytest

from src.specialties.maternal_neonatal import (
    MATERNAL_NEONATAL_ENDPOINTS, detect_maternal_neonatal_subspecialty,
    normalize_maternal_neonatal_endpoint, get_maternal_neonatal_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.maternal_neonatal_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of carbetocin versus oxytocin to prevent postpartum haemorrhage; "
     "blood loss and blood transfusion in the third stage of labour.", "maternal"),
    ("Magnesium sulphate versus placebo for severe pre-eclampsia; eclampsia and "
     "eclamptic seizure with gestational hypertension.", "hypertensive"),
    ("Chlorhexidine cord care to reduce neonatal sepsis; neonatal mortality, "
     "stillbirth and birth asphyxia among newborns.", "neonatal"),
    ("Antenatal corticosteroids (dexamethasone) for preterm birth; low birth "
     "weight, respiratory distress syndrome and gestational age at delivery.",
     "preterm"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_maternal_neonatal_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("postpartum haemorrhage", "POSTPARTUM_HAEMORRHAGE"),
    ("estimated blood loss", "BLOOD_LOSS"),
    ("maternal death", "MATERNAL_MORTALITY"),
    ("severe pre-eclampsia", "SEVERE_PREECLAMPSIA"),
    ("eclamptic seizure", "ECLAMPSIA"),
    ("neonatal mortality", "NEONATAL_MORTALITY"),
    ("intrauterine fetal death", "STILLBIRTH"),
    ("hypoxic-ischaemic encephalopathy", "BIRTH_ASPHYXIA"),
    ("preterm delivery", "PRETERM_BIRTH"),
    ("very low birth weight", "LOW_BIRTH_WEIGHT"),
    ("five-minute apgar", "APGAR_SCORE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_maternal_neonatal_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in MATERNAL_NEONATAL_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"maternal", "hypertensive", "neonatal", "preterm"}


# --- registry wiring ---

def test_maternal_neonatal_registered():
    assert "maternal_neonatal" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["maternal_neonatal"]
    assert e["detection_function"] is detect_maternal_neonatal_subspecialty
    assert e["normalizer"] is normalize_maternal_neonatal_endpoint
    assert set(e["subspecialties"]) == {"maternal", "hypertensive", "neonatal", "preterm"}


def test_detect_specialty_routes_to_maternal():
    spec, sub, _ = detect_specialty(
        "carbetocin versus oxytocin for prevention of postpartum haemorrhage; "
        "blood loss, blood transfusion and maternal mortality after caesarean section")
    assert spec == "maternal_neonatal" and sub == "maternal"


def test_hypertensive_routes():
    spec, sub, _ = detect_specialty(
        "magnesium sulphate versus diazepam for eclampsia in women with severe "
        "pre-eclampsia; recurrence of convulsions and maternal death")
    assert spec == "maternal_neonatal" and sub == "hypertensive"


def test_neonatal_routes():
    spec, sub, _ = detect_specialty(
        "kangaroo mother care versus conventional care for low birth weight "
        "newborns; neonatal mortality, neonatal sepsis and birth asphyxia")
    assert spec == "maternal_neonatal"


def test_does_not_break_hiv_malaria_typhoid_or_cardio():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "azithromycin versus ciprofloxacin for blood-culture-confirmed typhoid "
        "fever; fever clearance time and clinical cure in enteric fever")[0] == "typhoid"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_pph_2x2():
    t = ("Postpartum haemorrhage occurred in 45/680 (6.6%) in the carbetocin group "
         "and 78/675 (11.6%) in the oxytocin group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "POSTPARTUM_HAEMORRHAGE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"carbetocin", "oxytocin"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (45, 680)


def test_eclampsia_2x2():
    t = ("Eclampsia developed in 40/5055 (0.8%) in the magnesium sulphate group "
         "versus 96/5055 (1.9%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ECLAMPSIA"


def test_blood_loss_continuous_poolable():
    r = extract_continuous("mean blood loss 350 ± 120 mL in the carbetocin arm")
    assert r and r[0]["endpoint"] == "BLOOD_LOSS" and r[0]["poolable"] is True


def test_birth_weight_continuous_poolable():
    r = extract_continuous("mean birth weight 2950 ± 410 g in the intervention group")
    assert r and r[0]["endpoint"] == "BIRTH_WEIGHT" and r[0]["poolable"] is True


def test_low_birth_weight_2x2_not_mislabelled_birth_weight():
    # "birth weight" is a substring of "low birth weight"; the binary LBW count
    # must tag LOW_BIRTH_WEIGHT, not the continuous BIRTH_WEIGHT endpoint.
    t = ("Low birth weight occurred in 45/300 (15.0%) with betamethasone "
         "versus 72/305 (23.6%) with placebo")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "LOW_BIRTH_WEIGHT"
