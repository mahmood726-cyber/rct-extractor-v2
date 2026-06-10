"""
Tests for the ovarian-cancer specialty profile, registry wiring, and arm-level
extraction. Mirrors the prostate-cancer and cervical-cancer tests.
"""
import pytest

from rct_extractor._engine.specialties.ovarian_cancer import (
    OVARIAN_CANCER_ENDPOINTS, detect_ovarian_cancer_subspecialty,
    normalize_ovarian_cancer_endpoint, get_ovarian_cancer_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.ovarian_cancer_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


@pytest.mark.parametrize("text,expected", [
    ("Phase 3 RCT of carboplatin-paclitaxel plus bevacizumab versus chemotherapy "
     "alone in platinum-sensitive recurrent ovarian cancer; progression-free "
     "survival, overall survival and GCIG CA-125 response.", "systemic"),
    ("Randomized maintenance trial of olaparib versus placebo after first-line "
     "chemotherapy in BRCA-mutated ovarian cancer; maintenance progression-free "
     "survival and time to first subsequent therapy with niraparib comparison.",
     "maintenance"),
    ("Trial of primary debulking surgery versus interval debulking after "
     "neoadjuvant chemotherapy in advanced epithelial ovarian cancer; complete "
     "cytoreduction (R0 resection) and residual disease.", "surgical"),
    ("Long-term follow-up reporting ovarian cancer-specific mortality and "
     "all-cause mortality after screening.", "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_ovarian_cancer_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("progression-free survival", "PFS"),
    ("overall survival", "OS"),
    ("GCIG CA-125 response", "CA125_RESPONSE"),
    ("PFS2", "PFS2"),
    ("maintenance progression-free survival", "MAINTENANCE_PFS"),
    ("time to first subsequent therapy", "TFST"),
    ("complete cytoreduction", "COMPLETE_RESECTION"),
    ("ovarian cancer-specific mortality", "OVARIAN_CANCER_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_ovarian_cancer_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in OVARIAN_CANCER_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"systemic", "maintenance", "surgical", "mortality"}


def test_ovarian_cancer_registered():
    assert "ovarian_cancer" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["ovarian_cancer"]
    assert e["detection_function"] is detect_ovarian_cancer_subspecialty
    assert e["normalizer"] is normalize_ovarian_cancer_endpoint
    assert set(e["subspecialties"]) == {"systemic", "maintenance", "surgical", "mortality"}


def test_detect_specialty_routes_to_ovarian():
    spec, sub, _ = detect_specialty(
        "Randomized trial of olaparib maintenance therapy versus placebo as "
        "maintenance treatment in BRCA-mutated ovarian cancer; maintenance "
        "progression-free survival and time to first subsequent therapy")
    assert spec == "ovarian_cancer" and sub == "maintenance"


def test_ovarian_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression in HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "abiraterone in metastatic castration-resistant prostate cancer; PSA response")[0] != "ovarian_cancer"


def test_ca125_response_2x2():
    t = ("A GCIG CA-125 response occurred in 120/200 (60.0%) in the olaparib group "
         "versus 70/200 (35.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "CA125_RESPONSE"


def test_ca125_level_is_lognormal():
    r = extract_continuous("mean serum CA-125 level 45.0 ± 12.0 U/ml in the bevacizumab arm")
    assert r and r[0]["endpoint"] == "CA125_LEVEL" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
