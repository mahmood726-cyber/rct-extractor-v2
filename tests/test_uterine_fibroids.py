"""
Tests for the uterine-fibroids (leiomyoma) specialty profile, registry wiring,
and arm-level extraction. Mirrors the cervical-cancer, endometriosis and menopause
tests. Includes British/American spelling coverage (anaemia/anemia, haemoglobin/
hemoglobin, amenorrhoea/amenorrhea, embolisation/embolization).
"""
import pytest

from rct_extractor._engine.specialties.uterine_fibroids import (
    UTERINE_FIBROIDS_ENDPOINTS, detect_uterine_fibroids_subspecialty,
    normalize_uterine_fibroids_endpoint, get_uterine_fibroids_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.uterine_fibroids_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of relugolix combination therapy versus placebo for heavy menstrual "
     "bleeding due to uterine fibroids; menstrual blood loss, amenorrhoea and "
     "haemoglobin.", "bleeding"),
    ("Ulipristal acetate versus placebo for uterine leiomyoma; fibroid volume and "
     "total uterine volume reduction on MRI.", "volume"),
    ("Uterine artery embolisation versus myomectomy for symptomatic fibroids; "
     "re-intervention, symptom severity score (UFS-QoL) and length of hospital "
     "stay.", "procedural"),
    ("Treatment of uterine fibroids; UFS-QoL health-related quality of life and "
     "pelvic pressure (bulk symptoms).", "qol"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_uterine_fibroids_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("menstrual blood loss", "MENSTRUAL_BLOOD_LOSS"),
    ("PBAC score", "MENSTRUAL_BLOOD_LOSS"),
    ("bleeding control", "BLEEDING_CONTROL"),
    ("induced amenorrhoea", "AMENORRHOEA"),
    ("change in haemoglobin", "HAEMOGLOBIN"),
    ("iron-deficiency anaemia", "ANAEMIA"),
    ("fibroid volume", "FIBROID_VOLUME"),
    ("total uterine volume", "UTERINE_VOLUME"),
    ("re-intervention", "REINTERVENTION"),
    ("hysterectomy", "HYSTERECTOMY"),
    ("symptom severity score", "SYMPTOM_SEVERITY"),
    ("length of hospital stay", "HOSPITAL_STAY"),
    ("health-related quality of life", "QUALITY_OF_LIFE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_uterine_fibroids_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"bleeding", "volume", "procedural", "qol"}
    for name, info in UTERINE_FIBROIDS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_uterine_fibroids_registered():
    assert "uterine_fibroids" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["uterine_fibroids"]
    assert e["detection_function"] is detect_uterine_fibroids_subspecialty
    assert e["normalizer"] is normalize_uterine_fibroids_endpoint
    assert set(e["subspecialties"]) == {"bleeding", "volume", "procedural", "qol"}


def test_detect_specialty_routes_to_uterine_fibroids():
    spec, sub, _ = detect_specialty(
        "randomized placebo-controlled trial of relugolix combination therapy for "
        "heavy menstrual bleeding associated with uterine fibroids; menstrual blood "
        "loss, amenorrhoea and haemoglobin")
    assert spec == "uterine_fibroids" and sub == "bleeding"


def test_detect_specialty_routes_to_uterine_fibroids_procedural():
    spec, sub, _ = detect_specialty(
        "uterine artery embolisation versus myomectomy for symptomatic uterine "
        "fibroids; re-intervention, hysterectomy and symptom severity score")
    assert spec == "uterine_fibroids" and sub == "procedural"


def test_uterine_fibroids_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "magnesium sulphate versus placebo for severe pre-eclampsia; eclampsia and "
        "maternal mortality")[0] == "maternal_neonatal"
    assert detect_specialty(
        "single-dose HPV vaccine; persistent HPV-16/18 infection and CIN2+")[0] == \
        "cervical_cancer"


# --- arm-level extraction ---

def test_amenorrhoea_2x2():
    t = ("Amenorrhoea was achieved in 80/128 (62.5%) in the relugolix group and "
         "6/127 (4.7%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "AMENORRHOEA"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"relugolix", "placebo"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (80, 128)


def test_reintervention_2x2():
    t = ("Re-intervention occurred in 28/100 (28.0%) in the uterine artery "
         "embolisation group and 8/98 (8.2%) in the myomectomy group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "REINTERVENTION"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"uae", "myomectomy"}


def test_fibroid_volume_continuous():
    r = extract_continuous("Mean fibroid volume was 120.5 ± 40.2 in the ulipristal "
                           "group and 180.3 ± 55.1 in the placebo group")
    assert r and r[0]["endpoint"] == "FIBROID_VOLUME"
    assert r[0]["stat"] == "mean_sd" and r[0]["poolable"] is True
