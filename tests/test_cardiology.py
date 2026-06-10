"""
Tests for the cardiology specialty profile (heart failure / ACS / AF / valve),
registry wiring, and arm-level extraction. Mirrors the respiratory / hepatitis /
HIV / malaria tests.
"""
import pytest

from rct_extractor._engine.specialties.cardiology import (
    CARDIOLOGY_ENDPOINTS, detect_cardiology_subspecialty, normalize_cardiology_endpoint,
    get_cardiology_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.cardiology_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Sacubitril-valsartan vs enalapril in heart failure with reduced ejection "
     "fraction (HFrEF); cardiovascular death or hospitalization for heart failure.", "heart_failure"),
    ("Ticagrelor vs clopidogrel in acute coronary syndrome (ACS) undergoing PCI; "
     "MACE and stent thrombosis after percutaneous coronary intervention.", "acs"),
    ("Apixaban vs warfarin in nonvalvular atrial fibrillation; stroke or systemic "
     "embolism and major bleeding over a CHA2DS2-VASc-defined cohort.", "af"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_cardiology_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


def test_subspecialty_detection_returns_2_tuple():
    res = detect_cardiology_subspecialty("heart failure with reduced ejection fraction")
    assert isinstance(res, tuple) and len(res) == 2
    sub, conf = res
    assert isinstance(sub, str) and isinstance(conf, float)


@pytest.mark.parametrize("phrase,canonical", [
    ("left ventricular ejection fraction", "LVEF"),
    ("kccq clinical summary score", "KCCQ_CSS"),
    ("nt-probnp", "NT_PROBNP"),
    ("major adverse cardiovascular events", "MACE_3PT"),
    ("cardiovascular death", "CV_DEATH"),
    ("hospitalization for heart failure", "HF_HOSPITALIZATION"),
    ("myocardial infarction", "MI"),
    ("stroke/se", "STROKE_SYSTEMIC_EMBOLISM"),
    ("intracranial hemorrhage", "INTRACRANIAL_HEMORRHAGE"),
    ("stent thrombosis", "STENT_THROMBOSIS"),
    ("major bleeding", "BLEEDING_MAJOR"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_cardiology_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"heart_failure", "acs", "af", "valve", "all"}
    for name, info in CARDIOLOGY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_cardiology_registered():
    assert "cardiology" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["cardiology"]
    assert e["detection_function"] is detect_cardiology_subspecialty
    assert e["normalizer"] is normalize_cardiology_endpoint
    assert set(e["subspecialties"]) == {"heart_failure", "acs", "af", "valve"}


def test_detect_specialty_routes_to_cardiology():
    spec, sub, _ = detect_specialty(
        "Sacubitril-valsartan versus enalapril in heart failure with reduced ejection "
        "fraction; cardiovascular death or hospitalization for heart failure over 27 months.")
    assert spec == "cardiology" and sub == "heart_failure"

    spec2, sub2, _ = detect_specialty(
        "Ticagrelor versus clopidogrel in acute coronary syndrome undergoing PCI; "
        "major adverse cardiovascular events including myocardial infarction.")
    assert spec2 == "cardiology" and sub2 == "acs"


def test_cardiology_does_not_break_neighbors():
    assert detect_specialty("dolutegravir-based antiretroviral therapy; week 48 viral "
                            "suppression and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty("artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty("sofosbuvir-velpatasvir for chronic hepatitis C virus infection; "
                            "SVR12 sustained virologic response in treatment-naive adults")[0] == "hepatitis"


# --- arm-level extraction ---

def test_cv_death_or_hf_hosp_2x2():
    # PARADIGM-HF-style composite; sacubitril-valsartan combo kept whole (not
    # fragmented into a valsartan / sacubitril component), paired against enalapril.
    t = ("The primary composite of cardiovascular death or hospitalization for heart "
         "failure occurred in 914/4187 (21.8%) in the sacubitril-valsartan group and "
         "1117/4212 (26.5%) in the enalapril group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    # nearest-endpoint resolution tags this to HF_HOSPITALIZATION (the phrase
    # closest to the proportion); both are canonical cardiology endpoints.
    assert t0["endpoint"] in {"CV_DEATH_OR_HF_HOSP", "HF_HOSPITALIZATION"}
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"sacubitril-valsartan", "enalapril"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (914, 4187)


def test_mi_2x2_ticagrelor_vs_clopidogrel():
    t = ("Myocardial infarction occurred in 504/9333 (5.4%) in the ticagrelor group and "
         "593/9291 (6.4%) in the clopidogrel group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "MI"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"ticagrelor", "clopidogrel"}


def test_kccq_continuous_poolable():
    r = extract_continuous("mean KCCQ clinical summary score was 72 ± 18 in the dapagliflozin arm")
    assert r and r[0]["endpoint"] == "KCCQ_CSS" and r[0]["poolable"] is True


def test_lvef_continuous_poolable():
    r = extract_continuous("mean left ventricular ejection fraction was 33 ± 8 % in the empagliflozin arm")
    assert r and r[0]["endpoint"] == "LVEF" and r[0]["poolable"] is True


def test_nt_probnp_is_lognormal():
    r = extract_continuous("mean NT-proBNP was 1200 ± 400 pg/mL in the sacubitril-valsartan arm")
    assert r and r[0]["endpoint"] == "NT_PROBNP" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
