"""Tests for the renal-cell-carcinoma specialty profile, registry wiring, arm-level.
Includes a routing test vs nephrology (the overlapping bucket)."""
import pytest

from rct_extractor._engine.specialties.renal_cell_carcinoma import (
    RENAL_CELL_CARCINOMA_ENDPOINTS, detect_renal_cell_carcinoma_subspecialty,
    normalize_renal_cell_carcinoma_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.renal_cell_carcinoma_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of ipilimumab plus nivolumab versus sunitinib in advanced "
     "clear-cell renal cell carcinoma (mRCC); overall survival, progression-free "
     "survival and objective response in IMDC intermediate/poor-risk.", "advanced"),
    ("Adjuvant trial of pembrolizumab versus placebo in resected high-risk renal "
     "cell carcinoma after nephrectomy; disease-free survival and overall "
     "survival.", "adjuvant"),
    ("Trial of cabozantinib versus everolimus in previously treated renal cell "
     "carcinoma after prior VEGF therapy; progression-free survival and objective "
     "response.", "subsequent_line"),
    ("Registry follow-up reporting kidney cancer mortality and all-cause "
     "mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_renal_cell_carcinoma_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("progression-free survival", "PFS"),
    ("objective response rate", "ORR"),
    ("disease-free survival", "DFS"),
    ("kidney cancer mortality", "KIDNEY_CANCER_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_renal_cell_carcinoma_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in RENAL_CELL_CARCINOMA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"advanced", "adjuvant", "subsequent_line", "mortality"}


def test_rcc_registered():
    assert "renal_cell_carcinoma" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["renal_cell_carcinoma"]
    assert e["detection_function"] is detect_renal_cell_carcinoma_subspecialty
    assert set(e["subspecialties"]) == {"advanced", "adjuvant", "subsequent_line", "mortality"}


def test_detect_specialty_routes_to_rcc_over_nephrology():
    spec, sub, _ = detect_specialty(
        "Randomized trial of ipilimumab plus nivolumab versus sunitinib in advanced "
        "clear-cell renal cell carcinoma (mRCC) after nephrectomy; overall survival, "
        "progression-free survival and objective response")
    assert spec == "renal_cell_carcinoma" and sub == "advanced"


def test_nephrology_still_routes_to_nephrology():
    # A pure CKD trial must not be captured by RCC.
    assert detect_specialty(
        "dapagliflozin in chronic kidney disease; eGFR decline, dialysis initiation "
        "and end-stage kidney disease")[0] != "renal_cell_carcinoma"


def test_orr_2x2():
    t = ("An objective response occurred in 120/200 (60.0%) in the nivolumab group "
         "versus 80/200 (40.0%) in the sunitinib group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ORR"
