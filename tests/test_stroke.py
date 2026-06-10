"""
Tests for the stroke (cerebrovascular) specialty profile (acute ischemic /
hemorrhagic / secondary prevention / recovery), registry wiring, and arm-level
extraction. Mirrors the respiratory / hepatitis / HIV / malaria tests.

Routing note: a pure atrial-fibrillation anticoagulation trial (apixaban vs
warfarin for stroke prevention in AF) is a deliberately ambiguous case. Stroke
keywords are anchored on stroke-specific terms and do NOT claim bare 'atrial
fibrillation' / 'anticoagulation' / 'MACE' / 'major bleeding', so such a trial
ties on stroke-keyword count and is resolved to cardiology's `af` subspecialty
(cardiology is registered before stroke; max() breaks the tie toward it). The
test below accepts EITHER specialty but documents that it lands on cardiology.
"""
import pytest

from rct_extractor._engine.specialties.stroke import (
    STROKE_ENDPOINTS, detect_stroke_subspecialty, normalize_stroke_endpoint,
    get_stroke_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.stroke_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Endovascular thrombectomy plus alteplase vs alteplase alone in acute ischaemic "
     "stroke with large vessel occlusion; functional independence (modified Rankin "
     "scale 0-2) at 90 days and successful reperfusion (TICI 2b-3).", "acute_ischemic"),
    ("Tranexamic acid vs placebo in spontaneous intracerebral haemorrhage; haematoma "
     "expansion and poor outcome (mRS 3-6) at 90 days.", "hemorrhagic"),
    ("Clopidogrel plus aspirin (dual antiplatelet) vs aspirin for secondary prevention "
     "after minor ischaemic stroke or TIA; recurrent stroke at 90 days.", "secondary_prevention"),
    ("Robot-assisted upper-limb training vs conventional stroke rehabilitation; "
     "Fugl-Meyer assessment and Barthel Index at 3 months.", "recovery"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_stroke_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("functional independence", "FUNCTIONAL_INDEPENDENCE"),
    ("mRS 0-2", "FUNCTIONAL_INDEPENDENCE"),
    ("ordinal mRS shift", "MRS_SHIFT"),
    ("successful reperfusion", "RECANALIZATION"),
    ("symptomatic intracranial haemorrhage", "SYMPTOMATIC_ICH"),
    ("recurrent stroke", "RECURRENT_STROKE"),
    ("hematoma expansion", "HEMATOMA_EXPANSION"),
    ("poor outcome", "POOR_OUTCOME"),
    ("major bleeding", "MAJOR_BLEEDING"),
    ("Fugl-Meyer assessment", "MOTOR_FUNCTION"),
    ("Barthel Index", "BARTHEL_INDEX"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_stroke_endpoint(phrase) == canonical


def test_nihss_normalizes_to_a_nihss_scale_endpoint():
    # 'nihss' is a shared alias of both EARLY_NEURO_IMPROVEMENT (acute) and the
    # recovery-scale NIHSS endpoint; longest-alias ties resolve to the first in
    # STROKE_ENDPOINTS insertion order (EARLY_NEURO_IMPROVEMENT). Grounded in real
    # output -- assert the actual canonical rather than guessing.
    assert normalize_stroke_endpoint("NIHSS") == "EARLY_NEURO_IMPROVEMENT"


def test_endpoints_have_required_fields():
    valid = {"acute_ischemic", "hemorrhagic", "secondary_prevention", "recovery"}
    for name, info in STROKE_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


# --- registry wiring ---

def test_stroke_registered():
    assert "stroke" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["stroke"]
    assert e["detection_function"] is detect_stroke_subspecialty
    assert e["normalizer"] is normalize_stroke_endpoint
    assert set(e["subspecialties"]) == {
        "acute_ischemic", "hemorrhagic", "secondary_prevention", "recovery"}


def test_detect_specialty_routes_to_stroke():
    spec, sub, _ = detect_specialty(
        "Endovascular thrombectomy versus medical management in acute ischaemic stroke "
        "with large vessel occlusion; functional independence (modified Rankin scale "
        "0-2) at 90 days, successful reperfusion (TICI 2b-3), and symptomatic "
        "intracranial haemorrhage.")
    assert spec == "stroke" and sub == "acute_ischemic"

    spec2, sub2, _ = detect_specialty(
        "Ticagrelor plus aspirin versus aspirin alone for secondary stroke prevention "
        "after acute ischaemic stroke or transient ischaemic attack; recurrent stroke "
        "within 30 days.")
    assert spec2 == "stroke" and sub2 == "secondary_prevention"


def test_af_anticoagulation_is_ambiguous_but_not_stolen():
    # A pure AF-anticoagulation trial must NOT be mis-stolen by stroke. It routes
    # to EITHER cardiology OR stroke; with the current keyword sets it lands on
    # cardiology/af (documented expected behaviour).
    spec, sub, _ = detect_specialty(
        "Apixaban versus warfarin in patients with atrial fibrillation for the "
        "prevention of stroke; the primary outcome was stroke or systemic embolism "
        "and major bleeding.")
    assert spec in {"cardiology", "stroke"}
    assert spec == "cardiology" and sub == "af"   # documented resolution


def test_stroke_does_not_break_neighbors():
    assert detect_specialty("dolutegravir-based antiretroviral therapy; week 48 viral "
                            "suppression and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty("artemether-lumefantrine for falciparum malaria; day 28 "
                            "ACPR")[0] == "malaria"
    assert detect_specialty("sofosbuvir-velpatasvir for chronic hepatitis C; sustained "
                            "virologic response SVR12")[0] == "hepatitis"
    assert detect_specialty("sacubitril valsartan in heart failure; cardiovascular "
                            "death and heart failure hospitalization")[0] == "cardiology"


# --- arm-level extraction ---

def test_functional_independence_2x2():
    t = ("Functional independence (mRS 0-2) was achieved in 120/200 (60.0%) in the "
         "thrombectomy group and in 80/200 (40.0%) in the alteplase group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "FUNCTIONAL_INDEPENDENCE"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"thrombectomy", "alteplase"}


def test_mortality_2x2():
    t = ("90-day mortality occurred in 30/300 (10.0%) in the tenecteplase group and "
         "in 45/300 (15.0%) in the alteplase group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "MORTALITY"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"tenecteplase", "alteplase"}


def test_nihss_continuous_poolable():
    r = extract_continuous("the mean NIHSS score was 8 ± 3 in the tenecteplase arm")
    assert r and r[0]["endpoint"] == "EARLY_NEURO_IMPROVEMENT" and r[0]["poolable"] is True
    # stroke scales are NOT log-normal -> no pooling note
    assert r[0].get("pooling_note") is None


def test_fugl_meyer_continuous_poolable():
    r = extract_continuous("mean Fugl-Meyer assessment was 45 ± 12 in the intervention arm")
    assert r and r[0]["endpoint"] == "MOTOR_FUNCTION" and r[0]["poolable"] is True
