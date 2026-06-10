"""
Tests for the ophthalmology (eye) specialty profile (amd / dme / glaucoma /
dry_eye), registry wiring, and arm-level extraction. Mirrors the nephrology /
stroke / respiratory / hepatitis / HIV / malaria tests.

Routing note (coordinated with diabetes): ophthalmology keywords are EYE-specific
(age-related macular degeneration, neovascular, anti-VEGF, intravitreal, BCVA,
ETDRS letters, central retinal thickness, OCT, diabetic macular edema, diabetic
retinopathy, intraocular pressure, IOP, glaucoma, ocular, corneal, dry eye,
Schirmer, OSDI). A DIABETIC MACULAR EDEMA trial is eye-primary and carries enough
eye anchors to route to ophthalmology/dme, whereas a PURE glycaemic diabetes
trial (HbA1c / hypoglycaemia / weight loss, no eye primary) stays with diabetes.
We deliberately do NOT claim bare 'diabetes' / 'diabetic' as ophthalmology
keywords -- only the compound eye terms 'diabetic macular edema' / 'diabetic
retinopathy'. The tests below ground that contract against real detect_specialty
output.
"""
import pytest

from rct_extractor._engine.specialties.ophthalmology import (
    OPHTHALMOLOGY_ENDPOINTS, detect_ophthalmology_subspecialty,
    normalize_ophthalmology_endpoint, get_ophthalmology_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.ophthalmology_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Ranibizumab versus aflibercept in neovascular age-related macular degeneration; "
     "intravitreal anti-VEGF, mean change in best-corrected visual acuity (ETDRS letters) "
     "and central retinal thickness on OCT.", "amd"),
    ("Faricimab versus aflibercept in diabetic macular edema; BCVA change, central subfield "
     "thickness on OCT, and >=2-step diabetic retinopathy improvement.", "dme"),
    ("Latanoprost versus timolol in open-angle glaucoma; intraocular pressure (IOP) "
     "reduction in mmHg, reaching target IOP, and visual field progression.", "glaucoma"),
    ("Cyclosporine versus vehicle in dry eye disease; ocular surface disease index (OSDI), "
     "corneal fluorescein staining, and Schirmer test.", "dry_eye"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_ophthalmology_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("best-corrected visual acuity", "BCVA_CHANGE"),
    ("change in BCVA", "BCVA_CHANGE"),
    ("ETDRS letters", "BCVA_CHANGE"),
    ("gain of at least 15 letters", "VISION_GAIN_15"),
    (">=15-letter gain", "VISION_GAIN_15"),
    ("avoidance of loss", "VISION_LOSS_15"),
    ("central retinal thickness", "CRT_CHANGE"),
    ("2-step improvement", "DR_IMPROVEMENT"),
    ("intraocular pressure reduction", "IOP_CHANGE"),
    ("target IOP", "IOP_TARGET"),
    ("visual field progression", "VF_PROGRESSION"),
    ("OSDI", "OSDI_CHANGE"),
    ("corneal staining", "CORNEAL_STAINING"),
    ("Schirmer test", "SCHIRMER"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_ophthalmology_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"amd", "dme", "glaucoma", "dry_eye"}
    for name, info in OPHTHALMOLOGY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_subspecialty_patterns_cover_all_four():
    for sub in ("amd", "dme", "glaucoma", "dry_eye"):
        assert get_ophthalmology_endpoint_patterns(sub), sub


# --- registry wiring ---

def test_ophthalmology_registered():
    assert "ophthalmology" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["ophthalmology"]
    assert e["detection_function"] is detect_ophthalmology_subspecialty
    assert e["normalizer"] is normalize_ophthalmology_endpoint
    assert set(e["subspecialties"]) == {"amd", "dme", "glaucoma", "dry_eye"}


def test_detect_specialty_routes_to_ophthalmology():
    # Neovascular-AMD anti-VEGF sentence must route to ophthalmology/amd.
    spec, sub, _ = detect_specialty(
        "Aflibercept versus ranibizumab in neovascular age-related macular degeneration; "
        "intravitreal anti-VEGF therapy, with mean change in best-corrected visual acuity "
        "(ETDRS letters) and central retinal thickness on OCT as outcomes.")
    assert spec == "ophthalmology" and sub == "amd"

    # Glaucoma / IOP sentence must route to ophthalmology/glaucoma.
    spec2, sub2, _ = detect_specialty(
        "Latanoprost versus timolol eye drops in open-angle glaucoma; the primary outcome "
        "was reduction in intraocular pressure (IOP, mmHg) with visual field progression "
        "as a secondary outcome.")
    assert spec2 == "ophthalmology" and sub2 == "glaucoma"


def test_diabetic_macular_edema_routes_to_ophthalmology():
    # A diabetic-macular-edema trial is EYE-primary -> ophthalmology/dme, not diabetes.
    spec, sub, _ = detect_specialty(
        "Faricimab versus aflibercept in diabetic macular edema; intravitreal anti-VEGF, "
        "with BCVA change, central subfield thickness on OCT, and a 2-step improvement in "
        "diabetic retinopathy severity as outcomes.")
    assert spec == "ophthalmology" and sub == "dme"


def test_pure_glycemic_diabetes_stays_diabetes():
    # CRUCIAL: a pure type-2-diabetes glycaemic trial with NO eye primary outcome must
    # NOT be stolen by ophthalmology -- it stays with diabetes.
    spec, sub, _ = detect_specialty(
        "Tirzepatide versus insulin glargine in adults with type 2 diabetes; the primary "
        "outcome was change in HbA1c at week 40, with hypoglycaemia and body weight as "
        "secondary outcomes.")
    assert spec == "diabetes"


def test_ophthalmology_does_not_break_neighbors():
    assert detect_specialty("dolutegravir-based antiretroviral therapy; week 48 viral "
                            "suppression and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty("artemether-lumefantrine for falciparum malaria; day 28 "
                            "ACPR")[0] == "malaria"
    assert detect_specialty("sofosbuvir-velpatasvir for chronic hepatitis C; sustained "
                            "virologic response SVR12")[0] == "hepatitis"
    assert detect_specialty("sacubitril valsartan in heart failure; cardiovascular "
                            "death and heart failure hospitalization")[0] == "cardiology"
    assert detect_specialty("dapagliflozin versus placebo in chronic kidney disease (CKD); "
                            "composite kidney outcome of sustained 50% eGFR decline and "
                            "end-stage kidney disease")[0] == "nephrology"


# --- arm-level extraction ---

def test_vision_gain_2x2():
    t = ("A gain of at least 15 letters occurred in 150/300 (50.0%) in the aflibercept "
         "group and in 120/300 (40.0%) in the ranibizumab group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "VISION_GAIN_15"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"aflibercept", "ranibizumab"}


def test_target_iop_2x2():
    t = ("Target IOP was reached in 80/120 (66.7%) in the latanoprost group and in "
         "60/120 (50.0%) in the timolol group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "IOP_TARGET"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"latanoprost", "timolol"}


def test_bcva_continuous_poolable():
    r = extract_continuous("the mean BCVA change was 8 ± 3 letters in the aflibercept arm")
    assert r and r[0]["endpoint"] == "BCVA_CHANGE" and r[0]["poolable"] is True
    # ophthalmology continuous measures are NOT log-normal -> no pooling note
    assert r[0].get("pooling_note") is None


def test_iop_continuous_poolable():
    r = extract_continuous("the mean IOP reduction was 7.5 ± 2.1 mmHg in the latanoprost arm")
    assert r and r[0]["endpoint"] == "IOP_CHANGE" and r[0]["poolable"] is True
    assert r[0].get("pooling_note") is None
