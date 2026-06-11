"""Tests for the public rct_extractor facade API (packaging-facing contract)."""
import importlib

import pytest

import rct_extractor as rx
from rct_extractor.api import SPECIALTIES

# Canonical disease specialties that the package promises to support
# (full text->arm-level extractors). Kept as an explicit set so an accidental
# addition or removal of a specialty fails this contract loudly.
EXPECTED_SPECIALTIES = {
    "ards",
    "perioperative",
    "chronic_pain",
    "hiv", "malaria", "typhoid", "schistosomiasis", "sickle_cell", "cholera",
    "maternal_neonatal", "tuberculosis", "hepatitis", "meningitis", "pneumonia",
    "diarrhoeal", "malnutrition", "helminths", "hypertension", "cervical_cancer",
    "endometriosis",
    "menopause_hrt",
    "infertility_ivf",
    "gestational_diabetes",
    "diabetes", "respiratory", "cardiology", "oncology", "stroke",
    "nephrology", "psychiatry", "rheumatology", "gastroenterology",
    "dermatology", "ophthalmology",
    # oncology cluster (12)
    "oesophageal_cancer", "prostate_cancer", "ovarian_cancer", "pancreatic_cancer",
    "gastric_cancer", "hepatocellular_carcinoma", "melanoma", "leukaemia",
    "lymphoma", "head_neck_cancer", "bladder_cancer", "renal_cell_carcinoma",
    # cardio-metabolic / renal cluster (9)
    "dyslipidaemia", "venous_thromboembolism", "peripheral_artery_disease",
    "obesity", "thyroid", "osteoporosis", "kidney_transplant",
    "pulmonary_hypertension", "pcos",
    # neuro / psych / GI / rheum cluster (9)
    "parkinsons", "alzheimers", "multiple_sclerosis", "migraine",
    "schizophrenia", "cirrhosis", "osteoarthritis", "covid19", "sepsis",
}


def test_version_is_exposed():
    assert isinstance(rx.__version__, str) and rx.__version__


def test_list_specialties_has_all():
    assert set(rx.list_specialties()) == EXPECTED_SPECIALTIES
    assert set(SPECIALTIES) == EXPECTED_SPECIALTIES
    assert len(SPECIALTIES) == len(EXPECTED_SPECIALTIES)


def test_public_symbols_present():
    for name in ("extract", "extract_batch", "detect_specialty",
                 "list_specialties", "to_metakit_config", "SPECIALTIES"):
        assert hasattr(rx, name), f"missing public symbol {name}"


@pytest.mark.parametrize("specialty", sorted(EXPECTED_SPECIALTIES))
def test_each_specialty_arm_module_importable(specialty):
    """Every specialty must have an importable arm-data module with extract_arm_level."""
    mod = importlib.import_module(f"rct_extractor._engine.specialties.{specialty}_arm_data")
    assert hasattr(mod, "extract_arm_level")


@pytest.mark.parametrize("specialty", sorted(EXPECTED_SPECIALTIES))
def test_extract_forced_specialty_smoke(specialty):
    """extract() returns the expected shape for every forced specialty."""
    text = ("In this randomized trial the primary outcome occurred in "
            "100/200 (50.0%) in the intervention group and 130/200 (65.0%) "
            "in the control group (hazard ratio 0.70, 95% CI 0.55-0.90).")
    res = rx.extract(text, specialty=specialty)
    assert res["specialty"] == specialty
    assert "subspecialty" in res
    assert isinstance(res["effects"], list)
    assert res["arm_level"] is not None
    assert "poolable_2x2" in res["arm_level"]
    assert "tables_2x2" in res["arm_level"]
    assert "continuous" in res["arm_level"]


def test_extract_rejects_unknown_specialty():
    with pytest.raises(ValueError):
        rx.extract("some text", specialty="not_a_specialty")


def test_extract_auto_detects_diabetes():
    text = ("Empagliflozin versus placebo in type 2 diabetes: HbA1c was "
            "reduced and cardiovascular death occurred (hazard ratio 0.62, "
            "95% CI 0.45-0.85).")
    res = rx.extract(text)  # auto
    assert res["specialty"] == "diabetes"
    assert any(e.get("type") == "HR" for e in res["effects"])


def test_extract_with_effects_finds_hr():
    text = "The primary endpoint had a hazard ratio of 0.62 (95% CI 0.45-0.85)."
    res = rx.extract(text, specialty="hypertension")
    hrs = [e for e in res["effects"] if e.get("type") == "HR"]
    assert hrs and abs(hrs[0]["effect_size"] - 0.62) < 1e-6


def test_extract_flags_toggle_off():
    text = "hazard ratio 0.62 (95% CI 0.45-0.85)"
    res = rx.extract(text, specialty="hiv", with_effects=False, with_arm_level=False)
    assert res["effects"] == []
    assert res["arm_level"] is None


def test_extract_batch_echoes_metadata():
    recs = [
        {"name": "T1", "nct": "NCT1", "text": "hazard ratio 0.80 (95% CI 0.70-0.92)"},
        {"name": "T2", "nct": "NCT2", "text": "HR 0.87 (95% CI 0.76-0.98)"},
    ]
    out = rx.extract_batch(recs, specialty="hypertension")
    assert len(out) == 2
    assert out[0]["record"]["name"] == "T1"
    assert "text" not in out[0]["record"]


def test_to_metakit_config_effect_path():
    recs = [
        {"name": "SPRINT", "text": "hazard ratio 0.75 (95% CI 0.64-0.89)"},
        {"name": "ACCORD", "text": "hazard ratio of 0.88 (95% CI 0.73-1.06)"},
    ]
    cfg = rx.to_metakit_config(recs, title="BP CV events", effect_measure="HR")
    assert cfg["effect_measure"] == "HR"
    assert len(cfg["trials"]) == 2
    names = {t["name"] for t in cfg["trials"]}
    assert names == {"SPRINT", "ACCORD"}
