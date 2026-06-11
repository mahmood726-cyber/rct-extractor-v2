"""
Tests for the benign-prostatic-hyperplasia (BPH / LUTS) specialty profile,
registry wiring, and arm-level extraction. Mirrors the cervical-cancer,
endometriosis and uterine-fibroids tests. Verifies BPH does not collide with the
prostate_cancer specialty.
"""
import pytest

from rct_extractor._engine.specialties.benign_prostatic_hyperplasia import (
    BENIGN_PROSTATIC_HYPERPLASIA_ENDPOINTS,
    detect_benign_prostatic_hyperplasia_subspecialty,
    normalize_benign_prostatic_hyperplasia_endpoint,
    get_benign_prostatic_hyperplasia_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.benign_prostatic_hyperplasia_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of tamsulosin versus placebo for lower urinary tract symptoms due to "
     "benign prostatic hyperplasia; International Prostate Symptom Score (IPSS) "
     "total and IPSS quality of life.", "symptoms"),
    ("Dutasteride for BPH; maximum urinary flow rate (Qmax), post-void residual "
     "and prostate volume.", "flow"),
    ("Dutasteride versus placebo for BPH; acute urinary retention and BPH-related "
     "surgery over four years.", "progression"),
    ("Adverse events in a BPH trial; ejaculatory dysfunction, retrograde "
     "ejaculation, anejaculation and decreased libido.", "sexual"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_benign_prostatic_hyperplasia_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("international prostate symptom score", "IPSS_TOTAL"),
    ("storage subscore", "IPSS_STORAGE"),
    ("voiding subscore", "IPSS_VOIDING"),
    ("IPSS quality of life", "IPSS_QOL"),
    ("maximum flow rate", "QMAX"),
    ("post-void residual", "POST_VOID_RESIDUAL"),
    ("prostate volume", "PROSTATE_VOLUME"),
    ("acute urinary retention", "ACUTE_URINARY_RETENTION"),
    ("BPH-related surgery", "BPH_SURGERY"),
    ("clinical progression", "CLINICAL_PROGRESSION"),
    ("retrograde ejaculation", "EJACULATORY_DYSFUNCTION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_benign_prostatic_hyperplasia_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"symptoms", "flow", "progression", "sexual"}
    for name, info in BENIGN_PROSTATIC_HYPERPLASIA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_bph_registered():
    assert "benign_prostatic_hyperplasia" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["benign_prostatic_hyperplasia"]
    assert e["detection_function"] is detect_benign_prostatic_hyperplasia_subspecialty
    assert e["normalizer"] is normalize_benign_prostatic_hyperplasia_endpoint
    assert set(e["subspecialties"]) == {"symptoms", "flow", "progression", "sexual"}


def test_detect_specialty_routes_to_bph():
    spec, sub, _ = detect_specialty(
        "randomized trial of tamsulosin and dutasteride combination versus placebo "
        "for lower urinary tract symptoms due to benign prostatic hyperplasia; IPSS "
        "total score and maximum flow rate Qmax")
    assert spec == "benign_prostatic_hyperplasia"


def test_bph_does_not_collide_with_prostate_cancer():
    # The prostate_cancer specialty (oncology cluster) must still win for cancer
    assert detect_specialty(
        "abiraterone plus prednisone for metastatic castration-resistant prostate "
        "cancer; overall survival and radiographic progression-free survival, PSA "
        "response")[0] == "prostate_cancer"


def test_bph_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "single-dose HPV vaccine; persistent HPV-16/18 infection and CIN2+")[0] == \
        "cervical_cancer"


# --- arm-level extraction ---

def test_acute_urinary_retention_2x2():
    t = ("Acute urinary retention occurred in 8/500 (1.6%) in the dutasteride "
         "group and 25/498 (5.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "ACUTE_URINARY_RETENTION"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"dutasteride", "placebo"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (8, 500)


def test_ipss_total_continuous():
    r = extract_continuous("Mean IPSS total score was 8.2 ± 4.1 in the tamsulosin "
                           "group and 12.5 ± 5.3 in the placebo group")
    assert r and r[0]["endpoint"] == "IPSS_TOTAL"
    assert r[0]["stat"] == "mean_sd" and r[0]["poolable"] is True


def test_qmax_continuous():
    r = extract_continuous("Maximum flow rate (Qmax) was 14.5 ± 3.2 in the "
                           "tamsulosin group and 10.1 ± 2.8 in the placebo group")
    assert r and r[0]["endpoint"] == "QMAX"
