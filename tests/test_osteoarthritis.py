"""
Tests for the osteoarthritis specialty profile, registry wiring, and arm-level
extraction. Mirrors the tuberculosis / parkinsons tests.
"""
import pytest

from rct_extractor._engine.specialties.osteoarthritis import (
    OSTEOARTHRITIS_ENDPOINTS, detect_osteoarthritis_subspecialty,
    normalize_osteoarthritis_endpoint, get_osteoarthritis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.osteoarthritis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


@pytest.mark.parametrize("text,expected", [
    ("Duloxetine versus placebo for knee osteoarthritis; change in WOMAC pain and "
     "WOMAC physical function over 14 weeks.", "pharmacologic"),
    ("Intra-articular hyaluronic acid versus saline in knee osteoarthritis; single "
     "injection, ultrasound-guided.", "intraarticular"),
    ("Sprifermin versus placebo as a disease-modifying osteoarthritis drug; "
     "change in minimum joint space width and cartilage thickness over 2 years.",
     "structural"),
    ("Supervised exercise and weight loss versus usual care in knee osteoarthritis; "
     "KOOS and rate of total knee replacement.", "nonpharm"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_osteoarthritis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("WOMAC pain subscale", "WOMAC_PAIN"),
    ("WOMAC physical function", "WOMAC_FUNCTION"),
    ("WOMAC total score", "WOMAC_TOTAL"),
    ("pain VAS", "PAIN_VAS"),
    ("OMERACT-OARSI responder", "RESPONDER"),
    ("minimum joint space width", "JOINT_SPACE_WIDTH"),
    ("total knee replacement", "TJR"),
    ("knee injury and osteoarthritis outcome score", "KOOS"),
    ("rescue analgesic", "RESCUE_MEDICATION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_osteoarthritis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in OSTEOARTHRITIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"pharmacologic", "intraarticular",
                                        "structural", "nonpharm"}


def test_osteoarthritis_registered():
    assert "osteoarthritis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["osteoarthritis"]
    assert e["detection_function"] is detect_osteoarthritis_subspecialty
    assert e["normalizer"] is normalize_osteoarthritis_endpoint
    assert set(e["subspecialties"]) == {"pharmacologic", "intraarticular",
                                        "structural", "nonpharm"}


def test_detect_specialty_routes_to_osteoarthritis():
    spec, _, _ = detect_specialty(
        "Celecoxib versus naproxen in knee and hip osteoarthritis; change in WOMAC "
        "pain and OMERACT-OARSI responder rate")
    assert spec == "osteoarthritis"


def test_osteoarthritis_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


def test_tjr_2x2():
    t = ("Total knee replacement occurred in 12/200 (6.0%) in the celecoxib group "
         "and 28/198 (14.1%) in the naproxen group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "TJR"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"celecoxib", "naproxen"}


def test_womac_pain_continuous():
    rows = extract_continuous(
        "Change in WOMAC pain was -3.2 (SD 2.1) in the duloxetine arm and -1.6 "
        "(SD 2.3) in the placebo arm")
    assert any(r["endpoint"] == "WOMAC_PAIN" for r in rows)
