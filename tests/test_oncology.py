"""
Tests for the oncology specialty profile (breast / lung / GI), registry wiring,
and arm-level extraction. Mirrors the respiratory / hepatitis / HIV / malaria
tests.

NOTE: detect_oncology_subspecialty returns a 3-TUPLE (subspecialty, subtype,
confidence) -- unlike most other specialties' 2-tuple detectors -- so it is
unpacked as `sub, subtype, conf` throughout.
"""
import pytest

from rct_extractor._engine.specialties.oncology import (
    ONCOLOGY_ENDPOINTS, detect_oncology_subspecialty, normalize_oncology_endpoint,
    get_oncology_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.oncology_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection (3-tuple: sub, subtype, conf) ---

@pytest.mark.parametrize("text,expected", [
    ("HER2-positive breast cancer; trastuzumab plus pertuzumab vs trastuzumab; "
     "objective response rate and overall survival.", "breast"),
    ("Advanced non-small-cell lung cancer (NSCLC) with EGFR mutation; osimertinib "
     "vs chemotherapy; progression-free survival and objective response rate.", "lung"),
    ("Metastatic colorectal cancer (CRC); FOLFOX plus bevacizumab; overall survival "
     "and disease control rate.", "gi"),
])
def test_subspecialty_detection(text, expected):
    sub, subtype, conf = detect_oncology_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("objective response rate", "ORR"),
    ("complete response", "CR"),
    ("partial response", "PR"),
    ("disease control rate", "DCR"),
    ("overall survival", "OS"),
    ("duration of response", "DOR"),
    ("quality of life", "QOL"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_oncology_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in ONCOLOGY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]


def test_endpoint_patterns_emit_canonical_response_codes():
    # The RESPONSE endpoints that the engine can build 2x2s for must be present in
    # ONCOLOGY_ENDPOINTS so a tagged proportion has a real canonical home.
    for code in ("ORR", "CR", "PR", "DCR"):
        assert code in ONCOLOGY_ENDPOINTS
    # subspecialty endpoint patterns are (regex, code) pairs
    for sub in ("breast", "lung", "gi"):
        pats = get_oncology_endpoint_patterns(sub)
        assert pats and all(len(p) == 2 for p in pats)


# --- registry wiring ---

def test_oncology_registered():
    assert "oncology" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["oncology"]
    assert e["detection_function"] is detect_oncology_subspecialty
    assert e["normalizer"] is normalize_oncology_endpoint
    assert {"breast", "lung", "gi"}.issubset(set(e["subspecialties"]))


def test_detect_specialty_routes_to_oncology():
    spec, sub, _ = detect_specialty(
        "HER2-positive breast cancer; trastuzumab plus pertuzumab vs trastuzumab; "
        "objective response rate and overall survival.")
    assert spec == "oncology" and sub == "breast"

    spec2, sub2, _ = detect_specialty(
        "Advanced NSCLC with EGFR mutation; osimertinib vs chemotherapy; "
        "progression-free survival and objective response rate.")
    assert spec2 == "oncology" and sub2 == "lung"


def test_oncology_does_not_break_neighbors():
    assert detect_specialty("dolutegravir-based antiretroviral therapy; week 48 viral "
                            "suppression and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty("artemether-lumefantrine for falciparum malaria; "
                            "day 28 ACPR")[0] == "malaria"
    assert detect_specialty("sofosbuvir-velpatasvir for chronic hepatitis C; "
                            "sustained virologic response SVR12")[0] == "hepatitis"


# --- arm-level extraction (RESPONSE 2x2) ---

def test_objective_response_2x2():
    t = ("An objective response occurred in 150/300 (50.0%) in the pembrolizumab "
         "group and in 90/300 (30.0%) in the chemotherapy group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ORR"
    # "chemotherapy" is normalised to the standard-of-care control label
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {
        "pembrolizumab", "standard-of-care"}
    assert tabs[0]["arm1"]["total"] == 300 and tabs[0]["arm2"]["total"] == 300


def test_disease_control_rate_2x2():
    t = ("Disease control was achieved in 200/300 (66.7%) in the osimertinib group "
         "and 150/300 (50.0%) in the chemotherapy group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "DCR"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {
        "osimertinib", "standard-of-care"}


def test_fixed_combo_arm_not_fragmented():
    # trastuzumab-deruxtecan / trastuzumab-emtansine must be tagged as whole combos,
    # not collapsed to a bare "trastuzumab" arm that then fails to pair.
    t = ("An objective response occurred in 180/300 (60.0%) in the "
         "trastuzumab-deruxtecan group versus 90/300 (30.0%) in the "
         "trastuzumab-emtansine group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {
        "trastuzumab-deruxtecan", "trastuzumab-emtansine"}


def test_qol_continuous_poolable():
    r = extract_continuous("mean quality of life score was 65 ± 12 in the pembrolizumab arm")
    assert r and r[0]["endpoint"] == "QOL" and r[0]["poolable"] is True
    # QOL is a mean difference, NOT log-normal
    assert r[0]["pooling_note"] is None
