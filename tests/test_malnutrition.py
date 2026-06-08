"""
Tests for the malnutrition specialty profile, registry wiring, and arm-level
extraction. Mirrors the typhoid, HIV and malaria tests.
"""
import pytest

from src.specialties.malnutrition import (
    MALNUTRITION_ENDPOINTS, detect_malnutrition_subspecialty,
    normalize_malnutrition_endpoint, get_malnutrition_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.malnutrition_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of ready-to-use therapeutic food (RUTF) for severe acute malnutrition; "
     "nutritional recovery rate and weight gain in a CMAM programme.",
     "therapeutic_feeding"),
    ("Zinc and vitamin A supplementation with multiple micronutrient powder (MNP); "
     "stunting, anaemia and serum retinol among undernourished children.",
     "micronutrient"),
    ("Routine amoxicillin in severe acute malnutrition; in-hospital mortality and "
     "case fatality among children who died during inpatient treatment.",
     "mortality"),
    ("Anthropometric recovery of severe acute malnutrition; change in "
     "weight-for-height z-score (WHZ), MUAC gain and time to recovery.",
     "recovery_growth"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_malnutrition_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("nutritional recovery rate", "NUTRITIONAL_RECOVERY"),
    ("rate of weight gain", "WEIGHT_GAIN_RATE"),
    ("prevalence of stunting", "STUNTING"),
    ("iron-deficiency anaemia", "ANAEMIA"),
    ("serum zinc", "MICRONUTRIENT_STATUS"),
    ("weight-for-height z-score", "WEIGHT_FOR_HEIGHT"),
    ("mid-upper arm circumference", "MUAC_CHANGE"),
    ("case-fatality rate", "CASE_FATALITY"),
    ("time to recovery", "TIME_TO_RECOVERY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_malnutrition_endpoint(phrase) == canonical


def test_anaemia_british_and_american_spelling():
    # lessons.md: ha?emoglobin / ana?emia must match both spellings.
    assert normalize_malnutrition_endpoint("anaemia") == "ANAEMIA"
    assert normalize_malnutrition_endpoint("anemia") == "ANAEMIA"


def test_endpoints_have_required_fields():
    for name, info in MALNUTRITION_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {
            "therapeutic_feeding", "micronutrient", "mortality", "recovery_growth"}


# --- registry wiring ---

def test_malnutrition_registered():
    assert "malnutrition" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["malnutrition"]
    assert e["detection_function"] is detect_malnutrition_subspecialty
    assert e["normalizer"] is normalize_malnutrition_endpoint
    assert set(e["subspecialties"]) == {
        "therapeutic_feeding", "micronutrient", "mortality", "recovery_growth"}


def test_detect_specialty_routes_to_malnutrition():
    spec, sub, _ = detect_specialty(
        "ready-to-use therapeutic food (RUTF) versus F-100 for severe acute "
        "malnutrition; nutritional recovery and rate of weight gain in a "
        "community-based management of acute malnutrition programme")
    assert spec == "malnutrition" and sub == "therapeutic_feeding"


def test_malnutrition_micronutrient_routes():
    spec, sub, _ = detect_specialty(
        "multiple micronutrient powder (MNP) with zinc and vitamin A versus "
        "placebo; effect on stunting, wasting and anaemia (haemoglobin) and serum "
        "retinol in undernutrition")
    assert spec == "malnutrition" and sub == "micronutrient"


def test_normalize_via_registry():
    assert normalize_endpoint_by_specialty(
        "rate of weight gain", "malnutrition") == "WEIGHT_GAIN_RATE"


def test_malnutrition_endpoints_in_get_all():
    eps = get_all_endpoints("malnutrition")
    assert "NUTRITIONAL_RECOVERY" in eps and "MUAC_CHANGE" in eps


def test_malnutrition_does_not_break_hiv_malaria_typhoid_or_cardio():
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

def test_nutritional_recovery_2x2():
    t = ("Nutritional recovery was achieved by 142/150 (94.7%) in the ready-to-use "
         "therapeutic food group and 120/148 (81.1%) in the standard of care group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "NUTRITIONAL_RECOVERY"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"rutf", "standard-of-care"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (142, 150)


def test_mortality_2x2():
    t = ("Mortality occurred in 12/400 (3.0%) in the amoxicillin group versus "
         "30/402 (7.5%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "MORTALITY"


def test_weight_gain_rate_continuous_poolable():
    r = extract_continuous(
        "mean rate of weight gain 8.2 ± 3.1 g/kg/day in the RUTF arm")
    assert r and r[0]["endpoint"] == "WEIGHT_GAIN_RATE" and r[0]["poolable"] is True


def test_micronutrient_status_is_lognormal():
    r = extract_continuous("mean serum ferritin 42 ± 15 µg/L in the iron arm")
    assert r and r[0]["endpoint"] == "MICRONUTRIENT_STATUS" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
