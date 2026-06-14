"""
Tests for the vascular-surgery specialty profile, registry wiring, and arm-level
extraction. Includes a check that vascular-surgery (aneurysm/carotid/access/
venous) routes away from peripheral_artery_disease (lower-limb arterial) and
venous_thromboembolism (DVT/PE).
"""
import pytest

from rct_extractor._engine.specialties.vascular_surgery import (
    VASCULAR_SURGERY_ENDPOINTS, detect_vascular_surgery_subspecialty,
    normalize_vascular_surgery_endpoint, get_vascular_surgery_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.vascular_surgery_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("endovascular aneurysm repair (EVAR) versus open repair for abdominal aortic "
     "aneurysm; endoleak, reintervention and aneurysm-related mortality.", "aneurysm"),
    ("carotid endarterectomy versus carotid artery stenting for carotid stenosis; "
     "periprocedural stroke and stroke or death.", "carotid"),
    ("arteriovenous fistula versus av graft for haemodialysis access; primary patency, "
     "fistula maturation and access thrombosis.", "access"),
    ("endovenous laser ablation versus foam sclerotherapy for varicose veins; "
     "anatomical occlusion and varicose vein recurrence.", "venous"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_vascular_surgery_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("type II endoleak", "ENDOLEAK"),
    ("aneurysm-related mortality", "ANEURYSM_MORTALITY"),
    ("stroke or death", "STROKE_OR_DEATH"),
    ("fistula maturation", "ACCESS_MATURATION"),
    ("primary patency", "ACCESS_PATENCY"),
    ("varicose vein recurrence", "VARICOSE_RECURRENCE"),
    ("venous ulcer healing", "VENOUS_ULCER_HEALING"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_vascular_surgery_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"aneurysm", "carotid", "access", "venous"}
    for name, info in VASCULAR_SURGERY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_vascular_surgery_registered():
    assert "vascular_surgery" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["vascular_surgery"]
    assert e["detection_function"] is detect_vascular_surgery_subspecialty
    assert e["normalizer"] is normalize_vascular_surgery_endpoint
    assert set(e["subspecialties"]) == {"aneurysm", "carotid", "access", "venous"}


def test_detect_specialty_routes_to_vascular_surgery():
    spec, sub, _ = detect_specialty(
        "endovascular aneurysm repair versus open repair for abdominal aortic aneurysm; "
        "endoleak, reintervention and 30-day mortality")
    assert spec == "vascular_surgery" and sub == "aneurysm"


def test_vascular_vs_pad_disambiguation():
    # carotid revascularisation -> vascular_surgery, not PAD/stroke
    assert detect_specialty(
        "carotid endarterectomy versus carotid artery stenting for symptomatic carotid "
        "stenosis; periprocedural stroke or death")[0] == "vascular_surgery"
    # lower-limb claudication -> stays peripheral_artery_disease
    if "peripheral_artery_disease" in SPECIALTY_REGISTRY:
        assert detect_specialty(
            "cilostazol for intermittent claudication in peripheral artery disease; "
            "maximal walking distance and ankle-brachial index")[0] == "peripheral_artery_disease"


def test_vascular_surgery_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_endoleak_2x2():
    t = ("Endoleak occurred in 30/250 (12.0%) of EVAR patients and 8/250 (3.2%) of "
         "open repair patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "ENDOLEAK"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"evar", "open-repair"}


def test_access_patency_2x2():
    t = ("Primary patency was achieved in 150/200 (75.0%) of av fistula patients and "
         "120/200 (60.0%) of av graft patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ACCESS_PATENCY"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"av-fistula", "av-graft"}


def test_venous_occlusion_2x2():
    t = ("Anatomical occlusion was achieved in 180/200 (90.0%) of endovenous laser "
         "patients and 150/200 (75.0%) of foam sclerotherapy patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "VENOUS_OCCLUSION"
