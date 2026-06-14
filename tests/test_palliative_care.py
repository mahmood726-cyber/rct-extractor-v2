"""
Tests for the palliative / end-of-life care specialty profile, registry wiring,
and arm-level extraction. Includes a check that palliative-care trials route away
from the oncology specialty (cancer-directed therapy).
"""
import pytest

from rct_extractor._engine.specialties.palliative_care import (
    PALLIATIVE_CARE_ENDPOINTS, detect_palliative_care_subspecialty,
    normalize_palliative_care_endpoint, get_palliative_care_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.palliative_care_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("a palliative care intervention; pain intensity, dyspnoea and total symptom "
     "burden (ESAS).", "symptoms"),
    ("early palliative care; health-related quality of life (FACIT-Pal) and hospital "
     "anxiety and depression scale.", "quality_of_life"),
    ("advance care planning in palliative care; home death, hospital admission and "
     "aggressive end-of-life care.", "care_utilisation"),
    ("specialist palliative care in advanced cancer; overall survival and median "
     "survival time.", "survival"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_palliative_care_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("total symptom burden", "SYMPTOM_BURDEN"),
    ("health-related quality of life", "QUALITY_OF_LIFE"),
    ("home death", "HOME_DEATH"),
    ("aggressive end-of-life care", "AGGRESSIVE_EOL_CARE"),
    ("advance care planning completion", "ADVANCE_CARE_PLANNING"),
    ("overall survival", "SURVIVAL"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_palliative_care_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"symptoms", "quality_of_life", "care_utilisation", "survival"}
    for name, info in PALLIATIVE_CARE_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_palliative_care_registered():
    assert "palliative_care" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["palliative_care"]
    assert e["detection_function"] is detect_palliative_care_subspecialty
    assert e["normalizer"] is normalize_palliative_care_endpoint
    assert set(e["subspecialties"]) == {"symptoms", "quality_of_life", "care_utilisation", "survival"}


def test_detect_specialty_routes_to_palliative_care():
    spec, sub, _ = detect_specialty(
        "early palliative care versus usual oncology care in advanced cancer; home "
        "death, aggressive end-of-life care and advance care planning completion")
    assert spec == "palliative_care"


def test_palliative_vs_oncology_disambiguation():
    # palliative / end-of-life intervention -> palliative_care
    assert detect_specialty(
        "specialist palliative care versus usual care; place of death, hospital "
        "admission and symptom burden in patients with life-limiting illness"
    )[0] == "palliative_care"
    # cancer-directed therapy -> oncology stays
    if "oncology" in SPECIALTY_REGISTRY:
        spec = detect_specialty(
            "pembrolizumab plus chemotherapy versus chemotherapy in metastatic "
            "non-small-cell lung cancer; progression-free survival and objective "
            "response rate")[0]
        assert spec in {"oncology", "respiratory"}


def test_palliative_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_home_death_2x2():
    t = ("Death at home occurred in 90/200 (45.0%) of early palliative care patients "
         "and 60/200 (30.0%) of usual care patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "HOME_DEATH"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"early-palliative-care", "usual-care"}


def test_advance_care_planning_2x2():
    t = ("Advance care planning completion occurred in 130/200 (65.0%) of advance care "
         "planning patients and 80/200 (40.0%) of usual care patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ADVANCE_CARE_PLANNING"


def test_symptom_burden_continuous_poolable():
    r = extract_continuous("the total symptom burden was 24.5 ± 9.1 in the early "
                           "palliative care arm")
    assert r and r[0]["endpoint"] == "SYMPTOM_BURDEN" and r[0]["poolable"] is True
