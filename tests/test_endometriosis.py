"""
Tests for the endometriosis specialty profile, registry wiring, and arm-level
extraction. Mirrors the cervical-cancer, maternal-neonatal and malaria tests.
"""
import pytest

from rct_extractor._engine.specialties.endometriosis import (
    ENDOMETRIOSIS_ENDPOINTS, detect_endometriosis_subspecialty,
    normalize_endometriosis_endpoint, get_endometriosis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.endometriosis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Randomized trial of dienogest versus placebo for endometriosis; induced "
     "amenorrhoea, abnormal uterine bleeding, hot flushes and bone mineral density "
     "loss over 24 weeks.", "medical"),
    ("Double-blind RCT of laparoscopic excision versus ablation of endometrioma; "
     "endometrioma recurrence, reoperation and rASRM score at 12-month follow-up.",
     "surgical"),
    ("RCT comparing elagolix and placebo for endometriosis-associated pelvic pain; "
     "dysmenorrhoea and dyspareunia on a numeric rating scale and pain responder "
     "rate.", "pain"),
    ("Trial of laparoscopic surgery versus expectant management for endometriosis-"
     "associated infertility; clinical pregnancy rate, live birth and miscarriage.",
     "fertility"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_endometriosis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("chronic pelvic pain", "PELVIC_PAIN"),
    ("dysmenorrhoea", "DYSMENORRHOEA"),
    ("deep dyspareunia", "DYSPAREUNIA"),
    ("pain responder", "PAIN_RESPONSE"),
    ("induced amenorrhoea", "AMENORRHOEA"),
    ("abnormal uterine bleeding", "ABNORMAL_BLEEDING"),
    ("hot flushes", "HOT_FLUSHES"),
    ("bone mineral density loss", "BMD_LOSS"),
    ("endometrioma recurrence", "DISEASE_RECURRENCE"),
    ("reoperation", "REOPERATION"),
    ("clinical pregnancy rate", "CLINICAL_PREGNANCY"),
    ("live birth rate", "LIVE_BIRTH"),
    ("miscarriage", "MISCARRIAGE"),
    ("EHP-30", "QUALITY_OF_LIFE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_endometriosis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"pain", "medical", "surgical", "fertility"}
    for name, info in ENDOMETRIOSIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_endometriosis_registered():
    assert "endometriosis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["endometriosis"]
    assert e["detection_function"] is detect_endometriosis_subspecialty
    assert e["normalizer"] is normalize_endometriosis_endpoint
    assert set(e["subspecialties"]) == {"pain", "medical", "surgical", "fertility"}


def test_detect_specialty_routes_to_endometriosis_medical():
    spec, sub, _ = detect_specialty(
        "double-blind RCT of dienogest versus placebo in women with endometriosis; "
        "induced amenorrhoea, breakthrough bleeding and change in lumbar spine bone "
        "mineral density over 52 weeks")
    assert spec == "endometriosis" and sub == "medical"


def test_detect_specialty_routes_to_endometriosis_surgical():
    spec, sub, _ = detect_specialty(
        "laparoscopic excision versus ablation for ovarian endometrioma; endometrioma "
        "recurrence, reoperation and adhesion at follow-up in deep infiltrating "
        "endometriosis")
    assert spec == "endometriosis" and sub == "surgical"


def test_endometriosis_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "magnesium sulphate versus placebo for severe pre-eclampsia; eclampsia and "
        "maternal mortality")[0] == "maternal_neonatal"
    assert detect_specialty(
        "single-dose HPV vaccine; persistent HPV-16/18 infection and CIN2+")[0] == \
        "cervical_cancer"


# --- arm-level extraction ---

def test_recurrence_2x2():
    t = ("Disease recurrence occurred in 18/120 (15.0%) in the dienogest group and "
         "42/118 (35.6%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "DISEASE_RECURRENCE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"dienogest", "placebo"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (18, 120)


def test_clinical_pregnancy_2x2():
    t = ("Clinical pregnancy occurred in 55/150 (36.7%) in the excision group and "
         "30/148 (20.3%) in the ablation group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "CLINICAL_PREGNANCY"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"excision", "ablation"}


def test_pelvic_pain_continuous():
    r = extract_continuous("Mean pelvic pain VAS score was 2.1 ± 1.4 in the elagolix "
                           "group and 4.8 ± 1.9 in the placebo group")
    assert r and r[0]["endpoint"] == "PELVIC_PAIN"
    assert r[0]["stat"] == "mean_sd" and r[0]["poolable"] is True
