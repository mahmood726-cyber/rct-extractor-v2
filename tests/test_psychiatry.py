"""
Tests for the psychiatry specialty profile (depression / anxiety / bipolar /
psychosis), registry wiring, and arm-level extraction. Mirrors the stroke /
respiratory / hepatitis tests.

Routing note: psychiatry anchors on psych-specific terms and deliberately does
NOT claim bare 'relapse' / 'response' / 'remission' (those collide with
neurology's MS annualized-relapse-rate bucket and with generic effect words). A
schizophrenia/PANSS trial that mentions 'psychotic relapse' still routes to
psychiatry/psychosis because psychiatry out-scores neurology on the
psych-specific keywords (schizophrenia, PANSS, antipsychotic), not on the bare
'relapse' that neurology also carries.
"""
import pytest

from rct_extractor._engine.specialties.psychiatry import (
    PSYCHIATRY_ENDPOINTS, detect_psychiatry_subspecialty, normalize_psychiatry_endpoint,
    get_psychiatry_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.psychiatry_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Sertraline versus placebo in adults with major depressive disorder; the "
     "antidepressant treatment response and change in MADRS at week 8.", "depression"),
    ("Escitalopram versus placebo for generalized anxiety disorder; change in the "
     "Hamilton anxiety rating scale (HAM-A) and GAD-7 at week 8.", "anxiety"),
    ("Lithium versus quetiapine for acute mania in bipolar disorder; change in the "
     "Young Mania Rating Scale (YMRS) at week 3.", "bipolar"),
    ("Risperidone versus placebo in schizophrenia; change in PANSS total score and "
     "psychotic relapse over 6 months.", "psychosis"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_psychiatry_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("treatment response", "RESPONSE"),
    ("clinical remission", "REMISSION"),
    ("MADRS", "MADRS_CHANGE"),
    ("HAM-D", "HAMD_CHANGE"),
    ("PHQ-9", "PHQ9_CHANGE"),
    ("relapse of depression", "RELAPSE_DEPRESSION"),
    ("HAM-A", "HAMA_CHANGE"),
    ("GAD-7", "GAD7_CHANGE"),
    ("YMRS", "YMRS_CHANGE"),
    ("mood relapse", "MOOD_RELAPSE"),
    ("PANSS", "PANSS_CHANGE"),
    ("psychotic relapse", "PSYCHOSIS_RELAPSE"),
    ("clinical global impression", "CGI"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_psychiatry_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"depression", "anxiety", "bipolar", "psychosis"}
    for name, info in PSYCHIATRY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_all_four_subspecialties_present():
    subs = {info["subspecialty"] for info in PSYCHIATRY_ENDPOINTS.values()}
    assert subs == {"depression", "anxiety", "bipolar", "psychosis"}


# --- registry wiring ---

def test_psychiatry_registered():
    assert "psychiatry" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["psychiatry"]
    assert e["detection_function"] is detect_psychiatry_subspecialty
    assert e["normalizer"] is normalize_psychiatry_endpoint
    assert set(e["subspecialties"]) == {"depression", "anxiety", "bipolar", "psychosis"}


def test_detect_specialty_routes_to_psychiatry():
    spec, sub, _ = detect_specialty(
        "Sertraline versus placebo in adults with major depressive disorder; the "
        "antidepressant treatment response and change in MADRS at week 8.")
    assert spec == "psychiatry" and sub == "depression"

    # A pure schizophrenia / PANSS trial now routes to the dedicated, more-specific
    # 'schizophrenia' specialty (added later) rather than generic psychiatry. The
    # psychiatry extractor still owns mood, anxiety and bipolar (incl. psychotic
    # features); see test_detect_specialty_routes_to_schizophrenia for the schizo path.
    spec2, sub2, _ = detect_specialty(
        "Risperidone versus placebo in schizophrenia; change in PANSS total score and "
        "psychotic relapse over 6 months.")
    assert spec2 == "schizophrenia"


def test_psychiatry_does_not_break_neighbors():
    assert detect_specialty("dolutegravir-based antiretroviral therapy; week 48 viral "
                            "suppression and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty("artemether-lumefantrine for falciparum malaria; day 28 "
                            "ACPR")[0] == "malaria"
    assert detect_specialty("sofosbuvir-velpatasvir for chronic hepatitis C; sustained "
                            "virologic response SVR12")[0] == "hepatitis"
    assert detect_specialty("sacubitril valsartan in heart failure; cardiovascular "
                            "death and heart failure hospitalization")[0] == "cardiology"
    assert detect_specialty(
        "Endovascular thrombectomy versus medical management in acute ischaemic stroke "
        "with large vessel occlusion; functional independence (modified Rankin scale "
        "0-2) at 90 days and successful reperfusion (TICI 2b-3).")[0] == "stroke"


# --- arm-level extraction ---

def test_response_2x2():
    t = ("Treatment response was achieved in 90/150 (60.0%) in the sertraline group and "
         "in 60/150 (40.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "RESPONSE"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"sertraline", "placebo"}


def test_remission_2x2():
    t = ("Remission occurred in 45/150 (30.0%) in the escitalopram group and in "
         "30/150 (20.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "REMISSION"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"escitalopram", "placebo"}


def test_madrs_continuous_poolable():
    r = extract_continuous("the mean change in MADRS was -18 ± 6 in the sertraline arm")
    assert r and r[0]["endpoint"] == "MADRS_CHANGE" and r[0]["poolable"] is True
    # psychiatric rating scales are NOT log-normal -> no pooling note
    assert r[0].get("pooling_note") is None


def test_panss_continuous_poolable():
    r = extract_continuous("mean change in PANSS total was -25 ± 12 in the risperidone arm")
    assert r and r[0]["endpoint"] == "PANSS_CHANGE" and r[0]["poolable"] is True
    assert r[0].get("pooling_note") is None
