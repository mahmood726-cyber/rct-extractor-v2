"""
Tests for the PCOS specialty profile, registry wiring, and arm-level extraction,
including disambiguation from maternal_neonatal (shared pregnancy vocabulary).
"""
import pytest

from rct_extractor._engine.specialties.pcos import (
    PCOS_ENDPOINTS, detect_pcos_subspecialty,
    normalize_pcos_endpoint, get_pcos_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.pcos_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("letrozole versus clomifene for ovulation induction in PCOS; ovulation rate, "
     "clinical pregnancy and live birth.", "reproductive"),
    ("metformin in PCOS; change in body mass index, HOMA-IR and fasting insulin.", "metabolic"),
    ("change in total testosterone, sex hormone-binding globulin and the "
     "Ferriman-Gallwey hirsutism score.", "androgen"),
    ("ovarian hyperstimulation syndrome and gastrointestinal adverse events with "
     "gonadotropins.", "safety"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_pcos_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("ovulation rate", "OVULATION_RATE"),
    ("clinical pregnancy rate", "CLINICAL_PREGNANCY"),
    ("live birth rate", "LIVE_BIRTH"),
    ("ferriman-gallwey score", "HIRSUTISM"),
    ("sex hormone-binding globulin", "SHBG"),
    ("ovarian hyperstimulation syndrome", "OHSS"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_pcos_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"reproductive", "metabolic", "androgen", "safety"}
    for name, info in PCOS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_pcos_registered():
    assert "pcos" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["pcos"]
    assert e["detection_function"] is detect_pcos_subspecialty
    assert e["normalizer"] is normalize_pcos_endpoint
    assert set(e["subspecialties"]) == {"reproductive", "metabolic", "androgen", "safety"}


def test_detect_specialty_routes_to_pcos():
    spec, sub, _ = detect_specialty(
        "letrozole versus clomifene citrate for ovulation induction in women with "
        "polycystic ovary syndrome; ovulation rate, clinical pregnancy and live birth")
    assert spec == "pcos" and sub == "reproductive"


def test_pcos_does_not_break_siblings():
    # generic obstetric trial (no PCOS terms) -> maternal_neonatal
    if "maternal_neonatal" in SPECIALTY_REGISTRY:
        assert detect_specialty(
            "antenatal corticosteroids for women at risk of preterm birth; neonatal "
            "mortality, respiratory distress syndrome and stillbirth")[0] == "maternal_neonatal"
    assert detect_specialty(
        "empagliflozin versus placebo in type 2 diabetes; HbA1c reduction and "
        "fasting plasma glucose at 24 weeks")[0] == "diabetes"


# --- arm-level extraction ---

def test_live_birth_2x2():
    t = ("Live birth occurred in 103/376 (27.4%) of letrozole recipients and "
         "72/376 (19.1%) of clomifene recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "LIVE_BIRTH"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"letrozole", "clomifene"}


def test_ovulation_2x2():
    t = ("Ovulation occurred in 230/376 (61.2%) of letrozole recipients and "
         "180/376 (47.9%) of clomifene recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "OVULATION_RATE"


def test_testosterone_continuous_poolable():
    r = extract_continuous("total testosterone decreased by 0.5 ± 0.3 nmol/L in the "
                           "metformin arm")
    assert r and r[0]["endpoint"] == "TESTOSTERONE" and r[0]["poolable"] is True
