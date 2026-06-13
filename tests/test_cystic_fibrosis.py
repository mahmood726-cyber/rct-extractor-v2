"""
Tests for the cystic-fibrosis specialty profile, registry wiring, and arm-level
extraction. Includes a check that CF routes away from the general respiratory
specialty (shared FEV1 / exacerbation vocabulary).
"""
import pytest

from rct_extractor._engine.specialties.cystic_fibrosis import (
    CYSTIC_FIBROSIS_ENDPOINTS, detect_cystic_fibrosis_subspecialty,
    normalize_cystic_fibrosis_endpoint, get_cystic_fibrosis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.cystic_fibrosis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("elexacaftor/tezacaftor/ivacaftor in cystic fibrosis; absolute change in percent "
     "predicted FEV1 and pulmonary exacerbations through 24 weeks.", "pulmonary"),
    ("nutritional intervention in children with cystic fibrosis; change in body mass "
     "index and weight-for-age z-score.", "nutrition"),
    ("inhaled tobramycin for early Pseudomonas aeruginosa eradication; culture "
     "conversion and sputum bacterial density.", "microbiology"),
    ("ivacaftor reduced sweat chloride concentration and improved the CFQ-R "
     "respiratory domain score.", "systemic"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_cystic_fibrosis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


def test_unknown_text_returns_general():
    sub, conf = detect_cystic_fibrosis_subspecialty("A study of nothing in particular.")
    assert sub == "general_cf"


@pytest.mark.parametrize("phrase,canonical", [
    ("absolute change in percent predicted FEV1", "PPFEV1"),
    ("lung clearance index", "LCI"),
    ("protocol-defined pulmonary exacerbation", "PULMONARY_EXACERBATION"),
    ("sweat chloride concentration", "SWEAT_CHLORIDE"),
    ("Pseudomonas aeruginosa eradication", "PSEUDOMONAS_ERADICATION"),
    ("CFQ-R respiratory domain", "CFQ_R"),
    ("body mass index", "BMI"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_cystic_fibrosis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"pulmonary", "nutrition", "microbiology", "systemic"}
    for name, info in CYSTIC_FIBROSIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_cystic_fibrosis_registered():
    assert "cystic_fibrosis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["cystic_fibrosis"]
    assert e["detection_function"] is detect_cystic_fibrosis_subspecialty
    assert e["normalizer"] is normalize_cystic_fibrosis_endpoint
    assert set(e["subspecialties"]) == {"pulmonary", "nutrition", "microbiology", "systemic"}


def test_detect_specialty_routes_to_cystic_fibrosis():
    spec, sub, _ = detect_specialty(
        "elexacaftor/tezacaftor/ivacaftor in patients with cystic fibrosis and at least "
        "one F508del allele; percent predicted FEV1 and pulmonary exacerbations")
    assert spec == "cystic_fibrosis" and sub == "pulmonary"


def test_cf_vs_respiratory_disambiguation():
    # CF (CFTR modulator / sweat chloride / F508del) -> cystic_fibrosis, not respiratory
    assert detect_specialty(
        "lumacaftor/ivacaftor in cystic fibrosis homozygous for F508del; sweat chloride "
        "and percent predicted FEV1")[0] == "cystic_fibrosis"
    # general asthma trial (no CF terms) -> stays respiratory
    if "respiratory" in SPECIALTY_REGISTRY:
        assert detect_specialty(
            "budesonide/formoterol versus placebo in moderate asthma; ACQ-5 score, "
            "FEV1 and severe asthma exacerbations")[0] == "respiratory"


def test_cystic_fibrosis_does_not_break_siblings():
    assert detect_specialty(
        "amlodipine versus hydrochlorothiazide for essential hypertension; blood "
        "pressure control at 12 weeks and antihypertensive response rate")[0] == "hypertension"


# --- arm-level extraction ---

def test_pulmonary_exacerbation_2x2():
    t = ("A pulmonary exacerbation occurred in 30/200 (15.0%) of elexacaftor/tezacaftor/"
         "ivacaftor recipients and 60/200 (30.0%) of placebo recipients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs, "expected a poolable 2x2 table"
    t0 = tabs[0]
    assert t0["endpoint"] == "PULMONARY_EXACERBATION"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"eti", "placebo"}


def test_pseudomonas_eradication_2x2():
    t = ("Pseudomonas aeruginosa eradication was achieved in 80/100 (80.0%) of tobramycin "
         "patients and 50/100 (50.0%) of placebo patients")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "PSEUDOMONAS_ERADICATION"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"tobramycin", "placebo"}


def test_sweat_chloride_continuous_poolable():
    r = extract_continuous("the sweat chloride concentration was 45.1 ± 12.3 mmol/L "
                           "in the ivacaftor arm")
    assert r and r[0]["endpoint"] == "SWEAT_CHLORIDE" and r[0]["poolable"] is True
