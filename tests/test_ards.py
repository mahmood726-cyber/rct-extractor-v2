"""
Tests for the ARDS / acute-respiratory-failure specialty profile, registry
wiring, and arm-level extraction. Mirrors the tuberculosis / sepsis tests.
"""
import pytest

from rct_extractor._engine.specialties.ards import (
    ARDS_ENDPOINTS, detect_ards_subspecialty,
    normalize_ards_endpoint, get_ards_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.ards_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Lung-protective ventilation with low tidal volume (6 ml/kg) vs traditional "
     "tidal volume in moderate-to-severe ARDS; ventilator-free days and "
     "barotrauma. Higher PEEP open-lung strategy.", "ventilation"),
    ("Early cisatracurium neuromuscular blockade vs placebo for moderate-to-severe "
     "ARDS; 90-day mortality and oxygenation (PaO2:FiO2). Inhaled nitric oxide.",
     "pharmacotherapy"),
    ("Veno-venous ECMO vs conventional mechanical ventilation for severe ARDS with "
     "refractory hypoxaemia (EOLIA); rescue therapy and 60-day mortality.", "rescue"),
    ("High-flow nasal oxygen vs non-invasive ventilation vs standard oxygen therapy "
     "in acute hypoxaemic respiratory failure; need for intubation and ICU-free days. "
     "Conservative oxygen target.", "supportive"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_ards_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("28-day mortality", "MORTALITY"),
    ("ventilator-free days at day 28", "VENTILATOR_FREE_DAYS"),
    ("new pneumothorax", "BAROTRAUMA"),
    ("successful extubation", "EXTUBATION"),
    ("pao2:fio2", "OXYGENATION"),
    ("organ-failure-free days", "ORGAN_FAILURE"),
    ("need for intubation", "TREATMENT_FAILURE"),
    ("icu length of stay", "LENGTH_OF_STAY"),
    ("duration of mechanical ventilation", "DURATION_VENTILATION"),
    ("incidence of ards", "ARDS_INCIDENCE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_ards_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in ARDS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"ventilation", "pharmacotherapy", "rescue", "supportive"}


# --- registry wiring ---

def test_ards_registered():
    assert "ards" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["ards"]
    assert e["detection_function"] is detect_ards_subspecialty
    assert e["normalizer"] is normalize_ards_endpoint
    assert set(e["subspecialties"]) == {"ventilation", "pharmacotherapy", "rescue", "supportive"}


def test_detect_specialty_routes_to_ards():
    spec, sub, _ = detect_specialty(
        "Prone positioning vs supine in moderate-to-severe ARDS (Berlin definition); "
        "lung-protective ventilation, ventilator-free days and 28-day mortality")
    assert spec == "ards" and sub in {"ventilation", "rescue", "supportive", "pharmacotherapy"}


def test_ards_does_not_break_malaria_hiv_or_cardio():
    assert detect_specialty(
        "artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression and "
        "CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty(
        "sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


def test_ards_does_not_steal_copd_asthma():
    # COPD / asthma chronic respiratory trials must still route to respiratory,
    # not the critical-care ARDS bucket.
    assert detect_specialty(
        "tiotropium vs placebo in COPD; FEV1 and exacerbation rate over 52 weeks")[0] == "respiratory"
    assert detect_specialty(
        "benralizumab in severe eosinophilic asthma; annual exacerbation rate and FEV1")[0] == "respiratory"


# --- arm-level extraction ---

def test_mortality_2x2():
    t = ("28-day mortality occurred in 90/237 (38.0%) in the prone group and "
         "116/229 (50.7%) in the supine group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "MORTALITY"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"prone", "supine"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (90, 237)


def test_barotrauma_2x2():
    t = ("Barotrauma occurred in 10/300 (3.3%) in the low-tidal-volume group versus "
         "26/295 (8.8%) in the traditional tidal volume group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "BAROTRAUMA"


def test_intubation_2x2():
    t = ("The need for intubation occurred in 40/188 (21.3%) in the high-flow nasal "
         "oxygen group and 75/191 (39.3%) in the standard oxygen therapy group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "TREATMENT_FAILURE"


def test_ventilator_free_days_continuous():
    t = ("Ventilator-free days were 10.6 (SD 9.5) in the dexamethasone group and "
         "6.8 (SD 8.9) in the control group")
    cont = extract_continuous(t)
    assert any(c["endpoint"] == "VENTILATOR_FREE_DAYS" for c in cont)
