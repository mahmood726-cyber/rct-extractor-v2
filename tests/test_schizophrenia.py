"""
Tests for the schizophrenia specialty profile, registry wiring, and arm-level
extraction. Mirrors the tuberculosis / parkinsons tests.
"""
import pytest

from rct_extractor._engine.specialties.schizophrenia import (
    SCHIZOPHRENIA_ENDPOINTS, detect_schizophrenia_subspecialty,
    normalize_schizophrenia_endpoint, get_schizophrenia_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.schizophrenia_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


@pytest.mark.parametrize("text,expected", [
    ("Cariprazine versus placebo in an acute exacerbation of schizophrenia; change "
     "in PANSS total score and CGI-S over 6 weeks.", "acute"),
    ("Paliperidone palmitate long-acting injectable versus oral antipsychotic for "
     "relapse prevention in schizophrenia; time to relapse and rehospitalization.",
     "maintenance"),
    ("Trial in schizophrenia with predominant negative symptoms; change in PANSS "
     "negative subscale and MCCB cognition.", "negative_cognitive"),
    ("Clozapine versus risperidone in treatment-resistant schizophrenia; weight "
     "gain, akathisia and extrapyramidal symptoms.", "safety"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_schizophrenia_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("PANSS total score", "PANSS_TOTAL"),
    ("PANSS negative subscale", "PANSS_NEGATIVE"),
    ("clinical global impression", "CGI"),
    ("time to relapse", "RELAPSE"),
    ("rehospitalization", "HOSPITALIZATION"),
    ("all-cause discontinuation", "ALL_CAUSE_DISCONTINUATION"),
    ("clinically significant weight gain", "WEIGHT_GAIN"),
    ("extrapyramidal symptoms", "EPS"),
    ("MCCB", "COGNITION"),
    ("personal and social performance", "FUNCTIONING"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_schizophrenia_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in SCHIZOPHRENIA_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"acute", "maintenance", "negative_cognitive",
                                        "safety"}


def test_schizophrenia_registered():
    assert "schizophrenia" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["schizophrenia"]
    assert e["detection_function"] is detect_schizophrenia_subspecialty
    assert e["normalizer"] is normalize_schizophrenia_endpoint
    assert set(e["subspecialties"]) == {"acute", "maintenance", "negative_cognitive",
                                        "safety"}


def test_detect_specialty_routes_to_schizophrenia():
    spec, sub, _ = detect_specialty(
        "Lurasidone versus placebo in acute schizophrenia; change in PANSS total "
        "score and CGI-S, with response defined as >=30% PANSS reduction")
    assert spec == "schizophrenia" and sub == "acute"


def test_schizophrenia_does_not_break_other_specialties():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


def test_response_2x2():
    t = ("A PANSS responder (>=30% reduction) was achieved by 120/250 (48.0%) in "
         "the cariprazine group and 80/248 (32.3%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "RESPONSE"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"cariprazine", "placebo"}


def test_panss_total_continuous():
    rows = extract_continuous(
        "Change in PANSS total score was -20.5 (SD 18.2) in the olanzapine arm and "
        "-12.1 (SD 17.9) in the placebo arm")
    assert any(r["endpoint"] == "PANSS_TOTAL" for r in rows)
