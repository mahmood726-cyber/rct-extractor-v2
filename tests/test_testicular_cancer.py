"""Tests for the testicular cancer (germ cell) specialty profile, registry, arm-level."""
import pytest

from rct_extractor._engine.specialties.testicular_cancer import (
    TESTICULAR_CANCER_ENDPOINTS, detect_testicular_cancer_subspecialty,
    normalize_testicular_cancer_endpoint,
)
from rct_extractor._engine.specialties.registry import detect_specialty, SPECIALTY_REGISTRY
from rct_extractor._engine.specialties.testicular_cancer_arm_data import extract_arm_level


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of adjuvant single-agent carboplatin versus para-aortic "
     "radiotherapy in stage I seminoma; relapse-free survival.", "seminoma"),
    ("Randomized trial of BEP (bleomycin-etoposide-cisplatin) versus surveillance "
     "with retroperitoneal lymph-node dissection (RPLND) in non-seminomatous germ "
     "cell tumour (NSGCT); progression-free survival.", "nonseminoma"),
    ("Trial of high-dose chemotherapy versus VIP salvage chemotherapy in "
     "metastatic poor-risk germ cell tumour; progression-free survival and "
     "overall survival.", "advanced"),
    ("Registry follow-up reporting testicular cancer-specific mortality and "
     "all-cause mortality.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_testicular_cancer_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("overall survival", "OS"),
    ("progression-free survival", "PFS"),
    ("relapse-free survival", "RFS"),
    ("favourable response", "ORR"),
    ("testicular cancer-specific mortality", "TESTICULAR_CANCER_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_testicular_cancer_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in TESTICULAR_CANCER_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"seminoma", "nonseminoma", "advanced", "mortality"}


def test_testicular_cancer_registered():
    assert "testicular_cancer" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["testicular_cancer"]
    assert e["detection_function"] is detect_testicular_cancer_subspecialty
    assert set(e["subspecialties"]) == {"seminoma", "nonseminoma", "advanced", "mortality"}


def test_detect_specialty_routes_to_testicular_cancer():
    spec, sub, _ = detect_specialty(
        "Randomized trial of adjuvant carboplatin versus surveillance after "
        "orchidectomy in stage I seminoma (testicular germ cell tumour); "
        "relapse-free survival.")
    assert spec == "testicular_cancer" and sub == "seminoma"


def test_testicular_cancer_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "polatuzumab vedotin plus R-CHP versus R-CHOP in diffuse large B-cell "
        "lymphoma (DLBCL); event-free survival")[0] == "lymphoma"


def test_response_2x2():
    t = ("Relapse occurred in 10/200 (5.0%) in the "
         "carboplatin group versus 28/200 (14.0%) in the surveillance group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "RELAPSE"
