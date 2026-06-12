"""
Tests for the cataract / lens-surgery specialty profile (surgery / iol / pco /
complications), registry wiring, and arm-level extraction. Mirrors the
ophthalmology / nephrology / hepatitis tests.

Routing note: cataract keywords are lens-surgery-specific (cataract surgery,
phacoemulsification, FLACS, MSICS, intraocular lens / IOL, monofocal /
multifocal / trifocal / EDOF / toric, posterior capsule opacification, Nd:YAG
capsulotomy, spectacle independence, surgically induced astigmatism, endothelial
cell loss, cystoid macular o?edema, endophthalmitis) -- anchors the generic
ophthalmology profile (AMD / DME / glaucoma / dry eye) does NOT claim, so a
cataract-surgery trial routes here and the AMD/glaucoma trials still route to
ophthalmology. The tests below ground that contract against real detect_specialty
output.
"""
import pytest

from rct_extractor._engine.specialties.cataract import (
    CATARACT_ENDPOINTS, detect_cataract_subspecialty,
    normalize_cataract_endpoint, get_cataract_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.cataract_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Femtosecond laser-assisted cataract surgery (FLACS) versus phacoemulsification; "
     "the primary outcome was surgically induced astigmatism and corrected-distance "
     "visual acuity (CDVA, logMAR), with corneal endothelial cell loss as a secondary "
     "outcome.", "surgery"),
    ("Trifocal versus monofocal intraocular lens implantation after cataract surgery; "
     "spectacle independence, uncorrected distance visual acuity, and halos/dysphotopsia.",
     "iol"),
    ("Hydrophobic versus hydrophilic intraocular lens after cataract surgery and posterior "
     "capsule opacification; Nd:YAG capsulotomy rate at three years.", "pco"),
    ("Intracameral cefuroxime to prevent endophthalmitis after cataract surgery; incidence "
     "of postoperative endophthalmitis and cystoid macular oedema.", "complications"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_cataract_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("corrected distance visual acuity", "CDVA_CHANGE"),
    ("BCVA", "CDVA_CHANGE"),
    ("surgically induced astigmatism", "SIA"),
    ("endothelial cell loss", "ENDOTHELIAL_CELL_LOSS"),
    ("central corneal thickness", "CCT_CHANGE"),
    ("uncorrected distance visual acuity", "UDVA_CHANGE"),
    ("spectacle independence", "SPECTACLE_INDEPENDENCE"),
    ("dysphotopsia", "DYSPHOTOPSIA"),
    ("posterior capsule opacification", "PCO"),
    ("Nd:YAG capsulotomy", "YAG_CAPSULOTOMY"),
    ("cystoid macular edema", "CMO"),
    ("cystoid macular oedema", "CMO"),
    ("endophthalmitis", "ENDOPHTHALMITIS"),
    ("central macular thickness", "CMT_CHANGE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_cataract_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"surgery", "iol", "pco", "complications"}
    for name, info in CATARACT_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_subspecialty_patterns_cover_all_four():
    for sub in ("surgery", "iol", "pco", "complications"):
        assert get_cataract_endpoint_patterns(sub), sub


# --- registry wiring ---

def test_cataract_registered():
    assert "cataract" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["cataract"]
    assert e["detection_function"] is detect_cataract_subspecialty
    assert e["normalizer"] is normalize_cataract_endpoint
    assert set(e["subspecialties"]) == {"surgery", "iol", "pco", "complications"}


def test_detect_specialty_routes_to_cataract():
    spec, sub, _ = detect_specialty(
        "Femtosecond laser-assisted cataract surgery versus standard phacoemulsification "
        "for age-related cataract; the primary outcome was surgically induced astigmatism "
        "with corrected-distance visual acuity and corneal endothelial cell loss.")
    assert spec == "cataract" and sub == "surgery"

    spec2, sub2, _ = detect_specialty(
        "Trifocal versus monofocal intraocular lens after cataract surgery; spectacle "
        "independence and uncorrected distance visual acuity were the primary outcomes.")
    assert spec2 == "cataract" and sub2 == "iol"


def test_cataract_does_not_break_ophthalmology():
    # The generic ophthalmology AMD / glaucoma contract must still hold.
    assert detect_specialty(
        "Aflibercept versus ranibizumab in neovascular age-related macular degeneration; "
        "intravitreal anti-VEGF, mean change in best-corrected visual acuity (ETDRS "
        "letters) and central retinal thickness on OCT.")[0] == "ophthalmology"
    assert detect_specialty(
        "Latanoprost versus timolol eye drops in open-angle glaucoma; reduction in "
        "intraocular pressure (IOP, mmHg) and visual field progression.")[0] == "ophthalmology"


def test_cataract_does_not_break_neighbors():
    assert detect_specialty("dolutegravir-based antiretroviral therapy; week 48 viral "
                            "suppression and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty("artemether-lumefantrine for falciparum malaria; day 28 "
                            "ACPR")[0] == "malaria"
    assert detect_specialty("sacubitril valsartan in heart failure; cardiovascular "
                            "death and heart failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_spectacle_independence_2x2():
    t = ("Complete spectacle independence was achieved in 90/120 (75.0%) in the trifocal "
         "group and in 30/120 (25.0%) in the monofocal group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "SPECTACLE_INDEPENDENCE"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"trifocal-iol", "monofocal-iol"}


def test_yag_capsulotomy_2x2():
    t = ("Nd:YAG capsulotomy was required in 12/100 (12.0%) in the hydrophobic group and "
         "in 28/100 (28.0%) in the hydrophilic group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "YAG_CAPSULOTOMY"


def test_sia_continuous_poolable():
    r = extract_continuous("the mean surgically induced astigmatism was 0.45 ± 0.20 dioptres "
                           "in the phacoemulsification arm")
    assert r and r[0]["endpoint"] == "SIA" and r[0]["poolable"] is True
    # cataract continuous measures are NOT log-normal -> no pooling note
    assert r[0].get("pooling_note") is None


def test_cdva_continuous_poolable():
    r = extract_continuous("the mean corrected distance visual acuity was 0.10 ± 0.08 logMAR "
                           "in the flacs arm")
    assert r and r[0]["endpoint"] == "CDVA_CHANGE" and r[0]["poolable"] is True
    assert r[0].get("pooling_note") is None
