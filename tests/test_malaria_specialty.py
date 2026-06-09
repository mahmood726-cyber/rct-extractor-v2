"""
Tests for the malaria specialty profile and its registry wiring.

Covers: subspecialty detection, endpoint normalization, registry integration,
and end-to-end effect extraction on representative malaria-trial sentences.
"""
import re
import pytest

from rct_extractor._engine.specialties.malaria import (
    MALARIA_ENDPOINTS,
    detect_malaria_subspecialty,
    normalize_malaria_endpoint,
    get_malaria_endpoint_patterns,
    TREATMENT_PATTERNS,
    PREVENTION_PATTERNS,
    SEVERE_PATTERNS,
    TRANSMISSION_PATTERNS,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty,
    normalize_endpoint_by_specialty,
    get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict


# --------------------------------------------------------------------------
# Subspecialty detection
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("Open-label RCT of artemether-lumefantrine vs dihydroartemisinin-piperaquine "
     "for uncomplicated P. falciparum malaria; day 28 PCR-corrected ACPR.", "treatment"),
    ("Cluster-randomized trial of seasonal malaria chemoprevention with "
     "sulfadoxine-pyrimethamine; incidence of clinical malaria per child-year.", "prevention"),
    ("Children with severe falciparum malaria randomized to intravenous artesunate "
     "versus quinine; in-hospital mortality and coma recovery.", "severe"),
    ("Single low-dose primaquine added to ACT to reduce gametocyte carriage and "
     "mosquito infectivity (transmission-blocking).", "transmission"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_malaria_subspecialty(text)
    assert sub == expected
    assert 0.0 < conf <= 1.0


def test_unknown_text_returns_general():
    sub, conf = detect_malaria_subspecialty("A study of nothing in particular.")
    assert sub == "general_malaria"


# --------------------------------------------------------------------------
# Endpoint normalization
# --------------------------------------------------------------------------

@pytest.mark.parametrize("phrase,canonical", [
    ("Day 28 PCR-corrected ACPR", "ACPR"),
    ("adequate clinical and parasitological response", "ACPR"),
    ("PCR-confirmed recrudescence", "RECRUDESCENCE"),
    ("parasite clearance time", "PARASITE_CLEARANCE_TIME"),
    ("incidence of clinical malaria", "CLINICAL_MALARIA"),
    ("vaccine efficacy against severe malaria", "PROTECTIVE_EFFICACY"),
    ("gametocyte carriage", "GAMETOCYTE_CARRIAGE"),
    ("in-hospital mortality", "MORTALITY"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_malaria_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in MALARIA_ENDPOINTS.items():
        assert info["aliases"], f"{name} missing aliases"
        assert info["measure_types"], f"{name} missing measure_types"
        assert info["subspecialty"] in {
            "treatment", "prevention", "severe", "transmission"}


# --------------------------------------------------------------------------
# Registry integration
# --------------------------------------------------------------------------

def test_malaria_registered():
    assert "malaria" in SPECIALTY_REGISTRY
    entry = SPECIALTY_REGISTRY["malaria"]
    assert entry["detection_function"] is detect_malaria_subspecialty
    assert entry["normalizer"] is normalize_malaria_endpoint
    assert set(entry["subspecialties"]) == {
        "treatment", "prevention", "severe", "transmission"}


def test_detect_specialty_routes_to_malaria():
    text = ("Efficacy of dihydroartemisinin-piperaquine for uncomplicated "
            "Plasmodium falciparum malaria: day 42 ACPR and parasite clearance.")
    spec, sub, conf = detect_specialty(text)
    assert spec == "malaria"
    assert sub == "treatment"


def test_registry_endpoint_normalization():
    assert normalize_endpoint_by_specialty(
        "incidence of clinical malaria", "malaria", "prevention") == "CLINICAL_MALARIA"


def test_get_all_endpoints_malaria():
    eps = get_all_endpoints("malaria")
    assert "ACPR" in eps and "CLINICAL_MALARIA" in eps and "MORTALITY" in eps


# --------------------------------------------------------------------------
# Pattern hygiene (all regexes compile)
# --------------------------------------------------------------------------

def test_all_patterns_compile():
    for bundle in (TREATMENT_PATTERNS, PREVENTION_PATTERNS,
                   SEVERE_PATTERNS, TRANSMISSION_PATTERNS):
        for kw in bundle["detection_keywords"]:
            re.compile(kw)
        for pat, _ in bundle["endpoint_patterns"]:
            re.compile(pat)
        for pat in bundle["context_patterns"]:
            re.compile(pat)


# --------------------------------------------------------------------------
# End-to-end extraction on malaria sentences
# --------------------------------------------------------------------------

def test_extracts_malaria_effects():
    extractor = EnhancedExtractor()
    text = ("Day 28 PCR-corrected ACPR was 98.2% vs 94.5% (risk ratio 1.04, "
            "95% CI 1.01-1.07). Recurrent parasitaemia was lower with DHA-PPQ "
            "(hazard ratio 0.45, 95% CI 0.30-0.68).")
    results = [to_dict(x) for x in extractor.extract(text)]
    types = {r["type"] for r in results}
    assert "RR" in types and "HR" in types
    hr = next(r for r in results if r["type"] == "HR")
    assert abs(hr["effect_size"] - 0.45) < 1e-6
    assert abs(hr["ci_lower"] - 0.30) < 1e-6
    assert abs(hr["ci_upper"] - 0.68) < 1e-6


def test_protective_efficacy_context():
    extractor = EnhancedExtractor()
    text = ("Seasonal malaria chemoprevention reduced clinical malaria "
            "incidence (incidence rate ratio 0.26, 95% CI 0.20-0.34).")
    results = [to_dict(x) for x in extractor.extract(text)]
    assert any(abs(r["effect_size"] - 0.26) < 1e-6 for r in results)


# --- Multi-persona review: clinical vocabulary additions ---

@pytest.mark.parametrize("phrase,canonical", [
    ("vivax relapse", "RELAPSE"),
    ("radical cure", "RELAPSE"),
    # species-neutral recurrence terms route to RECURRENT_PARASITAEMIA, not RELAPSE
    ("time to first recurrence", "RECURRENT_PARASITAEMIA"),
    ("recurrence-free efficacy", "RECURRENT_PARASITAEMIA"),
    ("recurrent parasitaemia", "RECURRENT_PARASITAEMIA"),
    ("kelch13 mutation", "MOLECULAR_MARKER"),
    ("parasite reduction ratio", "PARASITE_REDUCTION_RATIO"),
    ("placental malaria", "PLACENTAL_MALARIA"),
    ("low birth weight", "LOW_BIRTH_WEIGHT"),
    ("maternal anaemia", "MATERNAL_ANAEMIA"),
    ("preterm birth", "PRETERM_BIRTH"),
    ("acute haemolytic anaemia", "HAEMOLYSIS"),
    ("hypoglycaemia", "HYPOGLYCAEMIA"),
    ("acute kidney injury", "ACUTE_KIDNEY_INJURY"),
])
def test_new_endpoint_normalization(phrase, canonical):
    assert normalize_malaria_endpoint(phrase) == canonical


def test_relapse_routes_before_recrudescence():
    import re
    pats = get_malaria_endpoint_patterns("treatment")
    def route(t):
        for p, ep in pats:
            if re.search(p, t.lower()):
                return ep
    assert route("day 42 vivax relapse") == "RELAPSE"
    # species-neutral "recurrence-free" is NOT relapse (falciparum trials use it)
    assert route("day 42 recurrence-free efficacy") == "RECURRENT_PARASITAEMIA"
    assert route("PCR-confirmed recrudescence") == "RECRUDESCENCE"
    # recurrent parasitaemia is PCR-uncorrected -> not TREATMENT_FAILURE
    assert route("recurrent parasitaemia at day 28") == "RECURRENT_PARASITAEMIA"


def test_generic_aliases_not_shadowed():
    # specific endpoints must win over generic substrings
    assert normalize_malaria_endpoint("anaemia") == "ANAEMIA"
    assert normalize_malaria_endpoint("parasitaemia") == "PARASITAEMIA"


def test_lbw_vs_mean_birthweight_split():
    import re
    pats = get_malaria_endpoint_patterns("prevention")
    def route(t):
        best=None
        for p, ep in pats:
            if re.search(p, t.lower()):
                return ep
    # binary LBW vs continuous mean birth weight must be different endpoints
    assert route("low birth weight occurred in") == "LOW_BIRTH_WEIGHT"
    assert route("mean birth weight was 3010 g") == "BIRTH_WEIGHT"


def test_aki_no_name_collision():
    import re
    pats = get_malaria_endpoint_patterns("severe")
    matched = any(re.search(p, "as reported by aki et al".lower()) and ep == "ACUTE_KIDNEY_INJURY"
                  for p, ep in pats)
    assert not matched
    assert any(re.search(p, "acute kidney injury") and ep == "ACUTE_KIDNEY_INJURY"
               for p, ep in pats)
