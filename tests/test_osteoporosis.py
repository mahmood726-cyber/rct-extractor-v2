"""
Tests for the osteoporosis specialty profile, registry wiring, and arm-level
extraction. Mirrors the diabetes / thyroid tests.
"""
import pytest

from rct_extractor._engine.specialties.osteoporosis import (
    OSTEOPOROSIS_ENDPOINTS, detect_osteoporosis_subspecialty,
    normalize_osteoporosis_endpoint, get_osteoporosis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.osteoporosis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("denosumab versus placebo in postmenopausal osteoporosis; new vertebral "
     "fracture, hip fracture and non-vertebral fracture over 36 months.", "fracture"),
    ("change in lumbar spine bone mineral density and total hip BMD by DXA after "
     "alendronate.", "bmd"),
    ("bone-turnover markers serum CTX and P1NP after a single zoledronic acid "
     "infusion.", "bone_turnover"),
    ("osteonecrosis of the jaw and atypical femoral fracture and hypocalcaemia "
     "were monitored as safety events.", "safety"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_osteoporosis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("new vertebral fracture", "VERTEBRAL_FRACTURE"),
    ("non-vertebral fracture", "NONVERTEBRAL_FRACTURE"),
    ("hip fracture", "HIP_FRACTURE"),
    ("lumbar spine bone mineral density", "BMD_LUMBAR_SPINE"),
    ("total hip bmd", "BMD_TOTAL_HIP"),
    ("p1np", "P1NP"),
    ("osteonecrosis of the jaw", "OSTEONECROSIS_JAW"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_osteoporosis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"fracture", "bmd", "bone_turnover", "safety"}
    for name, info in OSTEOPOROSIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_osteoporosis_registered():
    assert "osteoporosis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["osteoporosis"]
    assert e["detection_function"] is detect_osteoporosis_subspecialty
    assert e["normalizer"] is normalize_osteoporosis_endpoint
    assert set(e["subspecialties"]) == {"fracture", "bmd", "bone_turnover", "safety"}


def test_detect_specialty_routes_to_osteoporosis():
    spec, sub, _ = detect_specialty(
        "denosumab versus placebo in postmenopausal women with osteoporosis; new "
        "vertebral fracture, hip fracture and non-vertebral fracture over 36 months")
    assert spec == "osteoporosis" and sub == "fracture"


def test_osteoporosis_bmd_route():
    spec, sub, _ = detect_specialty(
        "alendronate for osteoporosis; percent change in lumbar spine bone mineral "
        "density and total hip BMD measured by DXA")
    assert spec == "osteoporosis" and sub == "bmd"


def test_osteoporosis_does_not_break_siblings():
    assert detect_specialty(
        "empagliflozin versus placebo in type 2 diabetes; HbA1c reduction and "
        "fasting plasma glucose at 24 weeks")[0] == "diabetes"
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_vertebral_fracture_2x2():
    t = ("New vertebral fracture occurred in 90/3902 (2.3%) of denosumab recipients "
         "and 281/3906 (7.2%) of placebo recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "VERTEBRAL_FRACTURE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"denosumab", "placebo"}


def test_hip_fracture_2x2():
    t = ("Hip fracture occurred in 43/3902 (1.1%) of zoledronic acid-treated patients "
         "and 88/3906 (2.3%) of placebo-treated patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "HIP_FRACTURE"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"zoledronic-acid", "placebo"}


def test_bmd_continuous_poolable():
    r = extract_continuous("lumbar spine bone mineral density increased by 6.5 ± 3.2 % "
                           "in the teriparatide arm")
    assert r and r[0]["endpoint"] == "BMD_LUMBAR_SPINE" and r[0]["poolable"] is True


def test_ctx_continuous_poolable():
    r = extract_continuous("serum CTX decreased by 1.2 ± 0.5 ng/mL in the "
                           "alendronate group")
    assert r and r[0]["endpoint"] == "CTX" and r[0]["poolable"] is True
