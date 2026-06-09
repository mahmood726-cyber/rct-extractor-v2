"""
Tests for the cervical-cancer / HPV specialty profile, registry wiring, and
arm-level extraction. Mirrors the typhoid, HIV and malaria tests.
"""
import pytest

from rct_extractor._engine.specialties.cervical_cancer import (
    CERVICAL_CANCER_ENDPOINTS, detect_cervical_cancer_subspecialty,
    normalize_cervical_cancer_endpoint, get_cervical_cancer_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.cervical_cancer_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Double-blind RCT of the bivalent HPV vaccine (Cervarix) versus hepatitis A "
     "vaccine; persistent HPV-16/18 infection and anti-HPV seroconversion with "
     "geometric mean titre by month 7.", "vaccine"),
    ("Cluster RCT comparing VIA (visual inspection with acetic acid) versus HPV DNA "
     "testing for cervical screening; screen positivity, sensitivity and specificity "
     "for CIN2+ and colposcopy referral.", "screening"),
    ("RCT of thermal ablation versus cryotherapy for CIN2+ precancer treatment; "
     "lesion clearance, HPV clearance and recurrence at 12-month follow-up.",
     "treatment"),
    ("Long-term follow-up of a screening RCT reporting invasive cervical cancer "
     "incidence and cervical cancer mortality per 100,000 woman-years.",
     "mortality"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_cervical_cancer_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("persistent HPV infection", "PERSISTENT_HPV_INFECTION"),
    ("CIN2+", "CIN2_PLUS"),
    ("genital warts", "GENITAL_WARTS"),
    ("anti-HPV IgG geometric mean titre", "HPV_IMMUNOGENICITY"),
    ("VIA positivity", "SCREEN_POSITIVITY"),
    ("colposcopy referral", "COLPOSCOPY_REFERRAL"),
    ("lesion clearance", "LESION_CLEARANCE"),
    ("HPV clearance", "HPV_CLEARANCE"),
    ("recurrence rate", "RECURRENCE"),
    ("invasive cervical cancer", "CERVICAL_CANCER_INCIDENCE"),
    ("cervical cancer mortality", "CERVICAL_CANCER_MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_cervical_cancer_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in CERVICAL_CANCER_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"vaccine", "screening", "treatment", "mortality"}


# --- registry wiring ---

def test_cervical_cancer_registered():
    assert "cervical_cancer" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["cervical_cancer"]
    assert e["detection_function"] is detect_cervical_cancer_subspecialty
    assert e["normalizer"] is normalize_cervical_cancer_endpoint
    assert set(e["subspecialties"]) == {"vaccine", "screening", "treatment", "mortality"}


def test_detect_specialty_routes_to_cervical_vaccine():
    spec, sub, _ = detect_specialty(
        "single-dose HPV vaccine (Cervarix, bivalent) versus control; vaccine "
        "efficacy against persistent HPV-16/18 infection and CIN2+ in young women; "
        "anti-HPV seroconversion and human papillomavirus immunogenicity")
    assert spec == "cervical_cancer" and sub == "vaccine"


def test_detect_specialty_routes_to_cervical_screening():
    spec, sub, _ = detect_specialty(
        "cervical cancer screening RCT comparing VIA (visual inspection with acetic "
        "acid) and HPV DNA testing with Pap cervical cytology; screen positivity, "
        "sensitivity and specificity for CIN2+, and colposcopy referral")
    assert spec == "cervical_cancer" and sub == "screening"


def test_cervical_does_not_break_hiv_malaria_or_cardio():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"
    assert detect_specialty(
        "azithromycin versus ceftriaxone for blood-culture-confirmed typhoid "
        "fever; fever clearance time")[0] == "typhoid"


# --- arm-level extraction ---

def test_cin2plus_2x2():
    t = ("CIN2+ occurred in 12/2810 (0.4%) in the bivalent HPV vaccine group and "
         "75/2800 (2.7%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "CIN2_PLUS"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"bivalent-hpv-vaccine", "placebo"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (12, 2810)


def test_screen_positivity_2x2():
    t = ("Screen positivity was recorded in 180/2000 (9.0%) in the VIA group versus "
         "260/2000 (13.0%) in the cytology group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "SCREEN_POSITIVITY"


def test_lesion_clearance_2x2():
    t = ("Lesion clearance was achieved by 380/420 (90.5%) in the thermal ablation "
         "arm and 350/420 (83.3%) in the cryotherapy arm")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "LESION_CLEARANCE"


def test_immunogenicity_is_lognormal():
    r = extract_continuous("mean anti-HPV IgG geometric mean titre 1850 ± 420 EU/ml "
                           "in the nonavalent HPV vaccine arm")
    assert r and r[0]["endpoint"] == "HPV_IMMUNOGENICITY" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
