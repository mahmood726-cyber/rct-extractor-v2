"""
Tests for the urinary-incontinence / overactive-bladder (OAB) specialty profile,
registry wiring, and arm-level extraction. Mirrors the BPH, ED and cervical-cancer
tests. Verifies UI/OAB does not collide with the bladder_cancer specialty.
"""
import pytest

from rct_extractor._engine.specialties.urinary_incontinence import (
    URINARY_INCONTINENCE_ENDPOINTS, detect_urinary_incontinence_subspecialty,
    normalize_urinary_incontinence_endpoint, get_urinary_incontinence_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.urinary_incontinence_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of mirabegron versus solifenacin for overactive bladder; urgency urinary "
     "incontinence episodes, micturition frequency and urgency episodes.", "oab"),
    ("Midurethral sling versus duloxetine for stress urinary incontinence; objective "
     "cure, pad test and leakage episodes.", "sui"),
    ("Intradetrusor onabotulinumtoxinA versus sacral neuromodulation for refractory "
     "urgency; urinary retention requiring catheterisation and urinary tract "
     "infection.", "procedural"),
    ("Treatment of urinary incontinence; ICIQ-SF, OAB-q symptom bother and King's "
     "Health Questionnaire.", "qol"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_urinary_incontinence_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("urgency urinary incontinence episodes", "UUI_EPISODES"),
    ("micturition frequency", "MICTURITION_FREQUENCY"),
    ("urgency episodes per day", "URGENCY_EPISODES"),
    ("nocturia", "NOCTURIA"),
    ("dry rate", "CONTINENCE"),
    ("dry mouth", "DRY_MOUTH"),
    ("constipation", "CONSTIPATION"),
    ("pad test", "PAD_TEST"),
    ("objective cure", "OBJECTIVE_CURE"),
    ("urinary retention", "URINARY_RETENTION"),
    ("urinary tract infection", "URINARY_TRACT_INFECTION"),
    ("ICIQ-SF", "ICIQ"),
    ("OAB-q", "OAB_Q"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_urinary_incontinence_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"oab", "sui", "procedural", "qol"}
    for name, info in URINARY_INCONTINENCE_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_urinary_incontinence_registered():
    assert "urinary_incontinence" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["urinary_incontinence"]
    assert e["detection_function"] is detect_urinary_incontinence_subspecialty
    assert e["normalizer"] is normalize_urinary_incontinence_endpoint
    assert set(e["subspecialties"]) == {"oab", "sui", "procedural", "qol"}


def test_detect_specialty_routes_to_urinary_incontinence():
    spec, sub, _ = detect_specialty(
        "randomized trial of mirabegron versus placebo for overactive bladder; "
        "urgency urinary incontinence episodes and micturition frequency on a "
        "3-day bladder diary")
    assert spec == "urinary_incontinence" and sub == "oab"


def test_ui_does_not_collide_with_bladder_cancer():
    # The bladder_cancer specialty (oncology cluster) must still win for cancer
    assert detect_specialty(
        "intravesical BCG versus chemotherapy for non-muscle-invasive bladder "
        "cancer; recurrence-free survival, progression and radical cystectomy")[0] \
        == "bladder_cancer"


def test_ui_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "tamsulosin for benign prostatic hyperplasia LUTS; IPSS and Qmax")[0] \
        in ("benign_prostatic_hyperplasia", "unknown")  # BPH not on this branch


# --- arm-level extraction ---

def test_continence_2x2():
    t = ("Complete continence was achieved in 90/200 (45.0%) in the mirabegron "
         "group and 60/198 (30.3%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "CONTINENCE"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"mirabegron", "placebo"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (90, 200)


def test_uui_episodes_continuous():
    r = extract_continuous("Mean urgency urinary incontinence episodes per day were "
                           "1.2 ± 0.8 in the solifenacin group and 2.5 ± 1.1 in the "
                           "placebo group")
    assert r and r[0]["endpoint"] == "UUI_EPISODES"
    assert r[0]["stat"] == "mean_sd" and r[0]["poolable"] is True


def test_pad_test_continuous():
    r = extract_continuous("Mean pad weight was 5.2 ± 2.1 g in the midurethral sling "
                           "group and 18.4 ± 6.3 g in the duloxetine group")
    assert r and r[0]["endpoint"] == "PAD_TEST"
