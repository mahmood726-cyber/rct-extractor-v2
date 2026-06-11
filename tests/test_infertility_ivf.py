"""
Tests for the infertility / IVF specialty profile, registry wiring, and arm-level
extraction. Mirrors the cervical-cancer, endometriosis and menopause tests.

This profile folds the "ovarian stimulation / IVF outcomes" area into the
`stimulation` subspecialty (see module docstring).
"""
import pytest

from rct_extractor._engine.specialties.infertility_ivf import (
    INFERTILITY_IVF_ENDPOINTS, detect_infertility_ivf_subspecialty,
    normalize_infertility_ivf_endpoint, get_infertility_ivf_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.infertility_ivf_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of GnRH antagonist versus long GnRH agonist protocol for controlled "
     "ovarian stimulation in IVF; number of oocytes retrieved, mature MII oocytes "
     "and ovarian hyperstimulation syndrome (OHSS).", "stimulation"),
    ("Randomized trial of ICSI versus conventional IVF; fertilisation rate, "
     "blastocyst formation rate and good-quality embryos.", "lab"),
    ("Fresh versus frozen-thawed embryo transfer in IVF; clinical pregnancy rate, "
     "live birth and miscarriage per transfer.", "transfer"),
    ("Letrozole versus clomiphene citrate for ovulation induction in anovulatory "
     "infertility; ovulation rate and clinical pregnancy.", "ovulation"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_infertility_ivf_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("number of oocytes retrieved", "OOCYTES_RETRIEVED"),
    ("mature MII oocytes", "MATURE_OOCYTES"),
    ("ovarian hyperstimulation syndrome", "OHSS"),
    ("cycle cancellation", "CYCLE_CANCELLATION"),
    ("peak oestradiol", "ESTRADIOL_TRIGGER"),
    ("total gonadotrophin dose", "GONADOTROPHIN_DOSE"),
    ("endometrial thickness", "ENDOMETRIAL_THICKNESS"),
    ("fertilisation rate", "FERTILIZATION_RATE"),
    ("blastocyst formation rate", "BLASTOCYST_RATE"),
    ("clinical pregnancy rate", "CLINICAL_PREGNANCY"),
    ("cumulative live birth", "LIVE_BIRTH"),
    ("ongoing pregnancy", "ONGOING_PREGNANCY"),
    ("implantation rate", "IMPLANTATION_RATE"),
    ("multiple pregnancy", "MULTIPLE_PREGNANCY"),
    ("ovulation rate", "OVULATION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_infertility_ivf_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"stimulation", "lab", "transfer", "ovulation"}
    for name, info in INFERTILITY_IVF_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_infertility_ivf_registered():
    assert "infertility_ivf" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["infertility_ivf"]
    assert e["detection_function"] is detect_infertility_ivf_subspecialty
    assert e["normalizer"] is normalize_infertility_ivf_endpoint
    assert set(e["subspecialties"]) == {"stimulation", "lab", "transfer", "ovulation"}


def test_detect_specialty_routes_to_ivf_stimulation():
    spec, sub, _ = detect_specialty(
        "randomized controlled trial of a GnRH antagonist protocol versus long "
        "agonist for controlled ovarian stimulation in IVF; oocytes retrieved, "
        "ovarian hyperstimulation syndrome (OHSS) and total gonadotrophin dose")
    assert spec == "infertility_ivf" and sub == "stimulation"


def test_detect_specialty_routes_to_ivf_transfer():
    spec, sub, _ = detect_specialty(
        "randomized trial of fresh versus frozen-thawed embryo transfer after IVF; "
        "clinical pregnancy rate, live birth and ongoing pregnancy per transfer")
    assert spec == "infertility_ivf" and sub == "transfer"


def test_infertility_does_not_break_other_specialties():
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "magnesium sulphate versus placebo for severe pre-eclampsia; eclampsia and "
        "maternal mortality")[0] == "maternal_neonatal"
    assert detect_specialty(
        "letrozole adjuvant therapy in postmenopausal hormone-receptor-positive "
        "breast cancer; disease-free survival")[0] == "oncology"


# --- arm-level extraction ---

def test_live_birth_2x2():
    t = ("Live birth occurred in 120/300 (40.0%) in the frozen-thawed embryo "
         "transfer group and 96/300 (32.0%) in the fresh embryo transfer group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "LIVE_BIRTH"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"frozen-transfer", "fresh-transfer"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (120, 300)


def test_ohss_2x2():
    t = ("OHSS occurred in 8/250 (3.2%) in the GnRH antagonist group and 22/248 "
         "(8.9%) in the GnRH agonist group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "OHSS"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == \
        {"gnrh-antagonist", "gnrh-agonist"}


def test_oocytes_retrieved_continuous():
    r = extract_continuous("The mean number of oocytes retrieved was 10.2 ± 4.1 in "
                           "the GnRH antagonist group and 8.5 ± 3.8 in the GnRH "
                           "agonist group")
    assert r and r[0]["endpoint"] == "OOCYTES_RETRIEVED"
    assert r[0]["stat"] == "mean_sd" and r[0]["poolable"] is True
