"""
Tests for the perioperative & anaesthesia specialty profile, registry wiring,
and arm-level extraction. Mirrors the tuberculosis / ARDS tests.
"""
import pytest

from rct_extractor._engine.specialties.perioperative import (
    PERIOPERATIVE_ENDPOINTS, detect_perioperative_subspecialty,
    normalize_perioperative_endpoint, get_perioperative_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.perioperative_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Spinal anaesthesia vs general anaesthesia for hip fracture surgery; "
     "postoperative pain score and cumulative opioid consumption with a "
     "peripheral nerve block.", "anaesthetic_technique"),
    ("Ondansetron plus dexamethasone vs ondansetron alone for prophylaxis of "
     "postoperative nausea and vomiting (PONV); rescue antiemetic use.", "ponv"),
    ("Perioperative beta-blocker vs placebo in non-cardiac surgery; major adverse "
     "cardiac events, myocardial injury after non-cardiac surgery and postoperative "
     "delirium with troponin monitoring.", "organ_protection"),
    ("Enhanced recovery after surgery (ERAS) vs standard care for colorectal "
     "resection; postoperative complications, surgical-site infection and "
     "hospital length of stay.", "recovery"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_perioperative_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("30-day mortality", "MORTALITY"),
    ("major adverse cardiac events", "MACE"),
    ("myocardial injury after non-cardiac surgery", "MYOCARDIAL_INJURY"),
    ("postoperative nausea and vomiting", "PONV"),
    ("rescue antiemetic", "RESCUE_ANTIEMETIC"),
    ("postoperative delirium", "DELIRIUM"),
    ("acute kidney injury", "AKI"),
    ("surgical site infection", "SSI"),
    ("hospital length of stay", "LENGTH_OF_STAY"),
    ("cumulative opioid consumption", "OPIOID_CONSUMPTION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_perioperative_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in PERIOPERATIVE_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"anaesthetic_technique", "ponv",
                                        "organ_protection", "recovery"}


# --- registry wiring ---

def test_perioperative_registered():
    assert "perioperative" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["perioperative"]
    assert e["detection_function"] is detect_perioperative_subspecialty
    assert e["normalizer"] is normalize_perioperative_endpoint
    assert set(e["subspecialties"]) == {"anaesthetic_technique", "ponv",
                                        "organ_protection", "recovery"}


def test_detect_specialty_routes_to_perioperative():
    spec, sub, _ = detect_specialty(
        "Dexamethasone vs placebo for prophylaxis of postoperative nausea and "
        "vomiting after laparoscopic surgery under general anaesthesia")
    assert spec == "perioperative" and sub in {"ponv", "anaesthetic_technique",
                                               "organ_protection", "recovery"}


def test_perioperative_does_not_break_malaria_hiv_or_cardio():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in chronic heart failure with reduced ejection "
        "fraction; cardiovascular death and heart-failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_ponv_2x2():
    t = ("Postoperative nausea and vomiting occurred in 30/150 (20.0%) in the "
         "dexamethasone group and 60/150 (40.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "PONV"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"dexamethasone", "placebo"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (30, 150)


def test_mace_2x2():
    t = ("Major adverse cardiac events occurred in 18/500 (3.6%) in the "
         "metoprolol group versus 32/498 (6.4%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "MACE"


def test_ssi_2x2():
    t = ("Surgical-site infection occurred in 12/220 (5.5%) with dexamethasone "
         "versus 28/218 (12.8%) with placebo")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "SSI"


def test_length_of_stay_continuous():
    t = ("Hospital length of stay was 4.2 (SD 1.8) days in the regional anaesthesia "
         "group and 6.1 (SD 2.4) days in the general anaesthesia group")
    cont = extract_continuous(t)
    assert any(c["endpoint"] == "LENGTH_OF_STAY" for c in cont)
