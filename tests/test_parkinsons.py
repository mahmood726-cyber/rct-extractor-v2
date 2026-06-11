"""
Tests for the Parkinson's disease specialty profile, registry wiring, and
arm-level extraction. Mirrors the tuberculosis / HIV / malaria tests.
"""
import pytest

from rct_extractor._engine.specialties.parkinsons import (
    PARKINSONS_ENDPOINTS, detect_parkinsons_subspecialty,
    normalize_parkinsons_endpoint, get_parkinsons_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.parkinsons_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Randomized trial of pramipexole versus placebo in early Parkinson disease; "
     "change in MDS-UPDRS Part III motor score and responder rate.", "motor"),
    ("Deep brain stimulation of the subthalamic nucleus (STN-DBS) versus best "
     "medical therapy in advanced Parkinson disease with motor fluctuations; "
     "ON time without troublesome dyskinesia.", "device_advanced"),
    ("Pimavanserin versus placebo for Parkinson disease psychosis; change in "
     "SAPS-PD and hallucinations.", "nonmotor"),
    ("Exenatide versus placebo as a disease-modifying therapy in early Parkinson "
     "disease; MDS-UPDRS total progression and time to dopaminergic therapy.",
     "neuroprotection"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_parkinsons_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("MDS-UPDRS Part III", "UPDRS_III"),
    ("MDS-UPDRS total score", "UPDRS_TOTAL"),
    ("levodopa equivalent daily dose", "LEDD"),
    ("troublesome dyskinesia", "DYSKINESIA"),
    ("on time without troublesome dyskinesia", "ON_TIME"),
    ("reduction in off time", "OFF_TIME"),
    ("PDQ-39 summary index", "QUALITY_OF_LIFE"),
    ("Parkinson disease psychosis", "PSYCHOSIS"),
    ("neurogenic orthostatic hypotension", "ORTHOSTATIC_HYPOTENSION"),
    ("time to initiation of dopaminergic therapy", "DISEASE_PROGRESSION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_parkinsons_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in PARKINSONS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"motor", "device_advanced", "nonmotor",
                                        "neuroprotection"}


# --- registry wiring ---

def test_parkinsons_registered():
    assert "parkinsons" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["parkinsons"]
    assert e["detection_function"] is detect_parkinsons_subspecialty
    assert e["normalizer"] is normalize_parkinsons_endpoint
    assert set(e["subspecialties"]) == {"motor", "device_advanced", "nonmotor",
                                        "neuroprotection"}


def test_detect_specialty_routes_to_parkinsons():
    spec, sub, _ = detect_specialty(
        "Randomized trial of rasagiline in early Parkinson disease; MDS-UPDRS "
        "Part III motor score change and levodopa equivalent daily dose")
    assert spec == "parkinsons" and sub == "motor"


def test_parkinsons_wins_over_generic_neurology():
    # The generic neurology catch-all also keys on 'parkinson'; the specific
    # parkinsons specialty must win (neurology is now a fallback bucket).
    spec, _, _ = detect_specialty(
        "deep brain stimulation for Parkinson disease motor fluctuations; "
        "dyskinesia and off time")
    assert spec == "parkinsons"


def test_parkinsons_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"
    # A generic neurology trial with no PD vocabulary still falls back sensibly
    # (alzheimer/stroke routing is handled by their own future modules).
    spec, _, _ = detect_specialty(
        "thrombectomy for acute ischemic stroke; functional independence")
    assert spec in {"neurology", "cardiology"}


# --- arm-level extraction ---

def test_responder_2x2():
    t = ("A motor responder was achieved by 96/150 (64.0%) in the safinamide group "
         "and 60/148 (40.5%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "MOTOR_RESPONDER"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"safinamide", "placebo"}


def test_dyskinesia_2x2():
    t = ("Treatment-emergent dyskinesia occurred in 30/200 (15.0%) in the levodopa "
         "group versus 12/198 (6.1%) in the pramipexole group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "DYSKINESIA"


def test_updrs_iii_continuous():
    # UPDRS Part III is a continuous score -> per-arm mean +/- SD.
    rows = extract_continuous(
        "Mean MDS-UPDRS Part III change was -8.5 (SD 6.2) in the rotigotine arm "
        "and -3.1 (SD 5.9) in the placebo arm")
    assert any(r["endpoint"] == "UPDRS_III" for r in rows)
