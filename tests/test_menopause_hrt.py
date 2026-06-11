"""
Tests for the menopause / HRT specialty profile, registry wiring, and arm-level
extraction. Mirrors the cervical-cancer, endometriosis and maternal-neonatal
tests.
"""
import pytest

from rct_extractor._engine.specialties.menopause_hrt import (
    MENOPAUSE_HRT_ENDPOINTS, detect_menopause_hrt_subspecialty,
    normalize_menopause_hrt_endpoint, get_menopause_hrt_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.menopause_hrt_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Double-blind RCT of fezolinetant versus placebo for moderate-to-severe "
     "vasomotor symptoms (hot flushes) in postmenopausal women; daily hot flush "
     "frequency and night sweats.", "vasomotor"),
    ("Postmenopausal women randomized to intravaginal prasterone or placebo for "
     "vulvovaginal atrophy; vaginal dryness, dyspareunia and vaginal maturation "
     "index.", "genitourinary"),
    ("RCT of raloxifene versus placebo in postmenopausal women; vertebral fracture, "
     "non-vertebral fracture and lumbar spine bone mineral density.", "bone"),
    ("Hormone therapy versus placebo in postmenopausal women; invasive breast "
     "cancer, venous thromboembolism, stroke and coronary heart disease over "
     "follow-up.", "safety"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_menopause_hrt_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("daily hot flush frequency", "HOT_FLUSHES"),
    ("night sweats", "NIGHT_SWEATS"),
    ("hot flush severity", "VMS_SEVERITY"),
    ("vms responder", "VMS_RESPONSE"),
    ("vaginal dryness", "VAGINAL_DRYNESS"),
    ("vulvovaginal atrophy", "VULVOVAGINAL_ATROPHY"),
    ("vaginal maturation index", "VAGINAL_PH"),
    ("lumbar spine bmd", "BMD"),
    ("vertebral fracture", "VERTEBRAL_FRACTURE"),
    ("hip fracture", "HIP_FRACTURE"),
    ("invasive breast cancer", "BREAST_CANCER"),
    ("endometrial hyperplasia", "ENDOMETRIAL_HYPERPLASIA"),
    ("venous thromboembolism", "VENOUS_THROMBOEMBOLISM"),
    ("coronary heart disease", "CORONARY_HEART_DISEASE"),
    ("MENQOL", "QUALITY_OF_LIFE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_menopause_hrt_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"vasomotor", "genitourinary", "bone", "safety"}
    for name, info in MENOPAUSE_HRT_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_menopause_hrt_registered():
    assert "menopause_hrt" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["menopause_hrt"]
    assert e["detection_function"] is detect_menopause_hrt_subspecialty
    assert e["normalizer"] is normalize_menopause_hrt_endpoint
    assert set(e["subspecialties"]) == {"vasomotor", "genitourinary", "bone", "safety"}


def test_detect_specialty_routes_to_menopause_vasomotor():
    spec, sub, _ = detect_specialty(
        "randomized placebo-controlled trial of fezolinetant, an NK3 receptor "
        "antagonist, for moderate-to-severe vasomotor symptoms (hot flushes and "
        "night sweats) in postmenopausal women")
    assert spec == "menopause_hrt" and sub == "vasomotor"


def test_detect_specialty_routes_to_menopause_genitourinary():
    spec, sub, _ = detect_specialty(
        "postmenopausal women with vulvovaginal atrophy randomized to intravaginal "
        "prasterone or placebo; genitourinary syndrome of menopause, vaginal dryness "
        "and dyspareunia")
    assert spec == "menopause_hrt" and sub == "genitourinary"


def test_menopause_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "magnesium sulphate versus placebo for severe pre-eclampsia; eclampsia and "
        "maternal mortality")[0] == "maternal_neonatal"
    assert detect_specialty(
        "single-dose HPV vaccine; persistent HPV-16/18 infection and CIN2+ in "
        "young women")[0] == "cervical_cancer"


# --- arm-level extraction ---

def test_vertebral_fracture_2x2():
    t = ("Vertebral fracture occurred in 30/1200 (2.5%) in the raloxifene group and "
         "60/1190 (5.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "VERTEBRAL_FRACTURE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"raloxifene", "placebo"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (30, 1200)


def test_breast_cancer_2x2():
    t = ("Invasive breast cancer was diagnosed in 45/8000 (0.6%) in the estrogen "
         "group and 38/8100 (0.5%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "BREAST_CANCER"


def test_hot_flush_continuous():
    r = extract_continuous("Mean hot flush frequency was 3.2 ± 1.5 in the fezolinetant "
                           "group and 7.8 ± 2.1 in the placebo group")
    assert r and r[0]["endpoint"] == "HOT_FLUSHES"
    assert r[0]["stat"] == "mean_sd" and r[0]["poolable"] is True
