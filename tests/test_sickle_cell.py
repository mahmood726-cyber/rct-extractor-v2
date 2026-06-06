"""
Tests for the sickle cell disease specialty profile, registry wiring, and
arm-level extraction. Mirrors the HIV / malaria / typhoid tests.
"""
import pytest

from src.specialties.sickle_cell import (
    SICKLE_CELL_ENDPOINTS, detect_sickle_cell_subspecialty,
    normalize_sickle_cell_endpoint, get_sickle_cell_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.sickle_cell_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Randomised trial of hydroxyurea versus placebo in sickle cell anaemia; "
     "annual rate of vaso-occlusive crises and acute chest syndrome.", "disease_modifying"),
    ("Intravenous magnesium for acute vaso-occlusive crisis; time to crisis "
     "resolution, length of hospital stay and opioid consumption with pain score.",
     "acute_pain"),
    ("Chronic transfusion versus observation for primary stroke prevention in "
     "children with abnormal transcranial Doppler velocity; overt stroke and silent "
     "cerebral infarct.", "prevention"),
    ("Deferasirox versus deferoxamine for iron overload in transfused sickle cell "
     "disease; serum ferritin, liver iron concentration and red cell alloimmunisation.",
     "transfusion"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_sickle_cell_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("vaso-occlusive crisis", "VASO_OCCLUSIVE_CRISIS"),
    ("acute chest syndrome", "ACUTE_CHEST_SYNDROME"),
    ("fetal haemoglobin", "FETAL_HEMOGLOBIN"),
    ("time to crisis resolution", "CRISIS_DURATION"),
    ("overt stroke", "STROKE"),
    ("silent cerebral infarct", "SILENT_INFARCT"),
    ("liver iron concentration", "LIVER_IRON"),
    ("red cell alloimmunization", "ALLOIMMUNIZATION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_sickle_cell_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in SICKLE_CELL_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {
            "disease_modifying", "acute_pain", "prevention", "transfusion"}


# --- registry wiring ---

def test_sickle_cell_registered():
    assert "sickle_cell" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["sickle_cell"]
    assert e["detection_function"] is detect_sickle_cell_subspecialty
    assert e["normalizer"] is normalize_sickle_cell_endpoint
    assert set(e["subspecialties"]) == {
        "disease_modifying", "acute_pain", "prevention", "transfusion"}


def test_detect_specialty_routes_to_sickle_cell():
    spec, sub, _ = detect_specialty(
        "hydroxyurea versus placebo in children with sickle cell anaemia; annual "
        "rate of vaso-occlusive crises, acute chest syndrome and fetal haemoglobin")
    assert spec == "sickle_cell" and sub == "disease_modifying"


def test_sickle_cell_prevention_routes():
    spec, sub, _ = detect_specialty(
        "regular blood transfusion versus standard care for stroke prevention in "
        "sickle cell disease with elevated transcranial Doppler velocity; overt "
        "stroke and silent cerebral infarct")
    assert spec == "sickle_cell" and sub == "prevention"


def test_sickle_cell_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "azithromycin versus ciprofloxacin for blood-culture-confirmed typhoid "
        "fever; fever clearance time")[0] == "typhoid"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_voc_2x2():
    t = ("A vaso-occlusive crisis occurred in 45/150 (30.0%) in the crizanlizumab "
         "group and 70/148 (47.3%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "VASO_OCCLUSIVE_CRISIS"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"crizanlizumab", "placebo"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (45, 150)


def test_stroke_2x2():
    t = ("Overt stroke occurred in 1/99 (1.0%) in the chronic transfusion group "
         "versus 11/100 (11.0%) in the standard care group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "STROKE"


def test_fetal_hemoglobin_continuous_poolable():
    r = extract_continuous("mean fetal haemoglobin 18.4 ± 6.2 % in the hydroxyurea arm")
    assert r and r[0]["endpoint"] == "FETAL_HEMOGLOBIN" and r[0]["poolable"] is True


def test_tcd_velocity_continuous_poolable():
    r = extract_continuous(
        "time-averaged mean velocity 165 ± 22 cm/s in the transfusion arm")
    assert r and r[0]["endpoint"] == "TCD_VELOCITY" and r[0]["poolable"] is True
