"""
Unit tests for the DTA (diagnostic test accuracy) extraction engine.

Covers: 2x2 count extraction, accuracy-measure extraction (with/without CI),
entity extraction (index test / reference standard / target condition),
exact derivation, internal-consistency checks, the negative-context guard,
British/American spelling handling, linear-time regex (no catastrophic
backtracking), and empty/degenerate inputs.
"""
import re
import time

import pytest

import dta_extractor as dta
from dta_extractor._engine import counts, entities, measures
from dta_extractor._engine.derive import check_consistency, derive_measures_from_2x2
from dta_extractor._engine.models import TwoByTwo


# --------------------------------------------------------------------------
# 2x2 extraction
# --------------------------------------------------------------------------
def test_two_by_two_phrase_form():
    t = "the assay yielded 35 true positives, 2 false positives, 8 false negatives and 95 true negatives"
    tabs = counts.extract_two_by_two(t)
    assert len(tabs) == 1
    tab = tabs[0]
    assert (tab.tp, tab.fp, tab.fn, tab.tn) == (35, 2, 8, 95)
    assert tab.origin == "stated"


def test_two_by_two_abbrev_equals_form():
    t = "Counts were TP = 120, FP = 14, FN = 9, TN = 357 in the validation cohort."
    tabs = counts.extract_two_by_two(t)
    assert len(tabs) == 1
    assert (tabs[0].tp, tabs[0].fp, tabs[0].fn, tabs[0].tn) == (120, 14, 9, 357)


def test_two_by_two_requires_both_arms_nonzero():
    # all-diseased degenerate table is rejected
    bad = TwoByTwo(tp=10, fp=0, fn=2, tn=0)
    assert not bad.is_valid()


def test_derive_two_by_two_from_se_sp():
    tab = counts.derive_two_by_two(0.90, 0.80, n_diseased=100, n_healthy=200)
    assert tab is not None
    assert tab.origin == "derived"
    assert tab.tp == 90 and tab.fn == 10
    assert tab.tn == 160 and tab.fp == 40


# --------------------------------------------------------------------------
# measure extraction
# --------------------------------------------------------------------------
def test_measure_with_ci_percentage():
    ms = {m.measure: m for m in measures.extract_measures(
        "Sensitivity was 92.0% (95% CI 88-96) and specificity 85% (95% CI 80-90).")}
    assert pytest.approx(ms["sensitivity"].value, abs=1e-9) == 0.92
    assert pytest.approx(ms["sensitivity"].ci_lower, abs=1e-9) == 0.88
    assert pytest.approx(ms["specificity"].value, abs=1e-9) == 0.85


def test_measure_point_only_no_ci():
    # the bare-point form the RCT CI-only extractor misses
    ms = {m.measure: m for m in measures.extract_measures(
        "The test had a sensitivity of 0.88 and a specificity of 0.91.")}
    assert pytest.approx(ms["sensitivity"].value, abs=1e-9) == 0.88
    assert pytest.approx(ms["specificity"].value, abs=1e-9) == 0.91
    assert ms["sensitivity"].ci_lower is None


def test_ratio_measures_natural_scale():
    ms = {m.measure: m for m in measures.extract_measures(
        "LR+ was 6.5 (95% CI 4.1-10.3), LR- 0.12, and the diagnostic odds ratio was 54.0.")}
    assert pytest.approx(ms["plr"].value, abs=1e-9) == 6.5
    assert pytest.approx(ms["nlr"].value, abs=1e-9) == 0.12
    assert pytest.approx(ms["dor"].value, abs=1e-9) == 54.0


def test_auc_and_ppv_npv():
    ms = {m.measure: m for m in measures.extract_measures(
        "AUC 0.83 (0.78-0.88); PPV was 76% and NPV 0.95.")}
    assert pytest.approx(ms["auc"].value, abs=1e-9) == 0.83
    assert pytest.approx(ms["ppv"].value, abs=1e-9) == 0.76
    assert pytest.approx(ms["npv"].value, abs=1e-9) == 0.95


def test_negative_context_guard():
    # hypothetical / power-calc / threshold statements must NOT be extracted
    for t in [
        "assuming a sensitivity of 90% for the power calculation",
        "a specificity of at least 80% was required",
        "the minimum sensitivity threshold was 0.85",
        "to achieve a specificity of 0.95",
    ]:
        assert measures.extract_measures(t) == [], t


def test_ci_that_does_not_bracket_point_is_dropped():
    # mis-parsed CI (point outside bounds) -> CI nulled, point kept
    ms = measures.extract_measures("sensitivity 50% (95% CI 70-90)")
    assert len(ms) == 1
    assert ms[0].ci_lower is None  # rejected because 0.50 not in [0.70, 0.90]


# --------------------------------------------------------------------------
# entities
# --------------------------------------------------------------------------
def test_entities_basic():
    t = ("We evaluated the diagnostic accuracy of the rapid antigen test for the "
         "detection of SARS-CoV-2 infection using RT-PCR as the reference standard.")
    e = entities.extract_entities(t)
    assert e["index_test"] == "rapid antigen test"
    assert e["reference_standard"] == "RT-PCR"
    assert "SARS-CoV-2" in e["target_condition"]


def test_entities_gold_standard_wording():
    t = "Histopathology served as the reference standard for diagnosing prostate cancer."
    e = entities.extract_entities(t)
    assert e["reference_standard"] and "istopathology" in e["reference_standard"]


# --------------------------------------------------------------------------
# British / American spelling (rules/lessons.md insert-vowel trap)
# --------------------------------------------------------------------------
def test_british_spelling_target_terms_detected():
    # tumour (UK) vs tumor (US); oesophageal (UK) vs esophageal (US)
    assert dta.detect_domain("accuracy of MRI for oesophageal tumour staging") == "oncology"
    assert dta.detect_domain("accuracy of MRI for esophageal tumor staging") == "oncology"
    # coeliac (UK) vs celiac (US)
    assert dta.detect_domain("tTG-IgA for coeliac disease") == "gastroenterology"
    assert dta.detect_domain("tTG-IgA for celiac disease") == "gastroenterology"


# --------------------------------------------------------------------------
# exact derivation + consistency
# --------------------------------------------------------------------------
def test_derivation_matches_textbook():
    tab = TwoByTwo(tp=80, fp=20, fn=20, tn=180)
    d = derive_measures_from_2x2(tab)
    assert pytest.approx(d["sensitivity"].value, abs=1e-12) == 0.80
    assert pytest.approx(d["specificity"].value, abs=1e-12) == 0.90
    assert pytest.approx(d["ppv"].value, abs=1e-12) == 0.80
    assert pytest.approx(d["npv"].value, abs=1e-12) == 0.90
    # DOR = (TP*TN)/(FP*FN) = (80*180)/(20*20) = 36
    assert pytest.approx(d["dor"].value, abs=1e-9) == 36.0
    # LR+ = se/(1-sp) = 0.8/0.1 = 8 ; LR- = (1-se)/sp = 0.2/0.9
    assert pytest.approx(d["plr"].value, abs=1e-9) == 8.0
    assert pytest.approx(d["nlr"].value, abs=1e-9) == (0.2 / 0.9)


def test_consistency_flags_mismatch():
    tab = TwoByTwo(tp=80, fp=20, fn=20, tn=180)  # derived se=0.80
    from dta_extractor._engine.models import DTAMeasure
    stated = {"sensitivity": DTAMeasure(measure="sensitivity", value=0.95)}
    notes = check_consistency(tab, stated)
    assert notes and "sensitivity" in notes[0]


def test_consistency_passes_when_agree():
    tab = TwoByTwo(tp=80, fp=20, fn=20, tn=180)
    from dta_extractor._engine.models import DTAMeasure
    stated = {"sensitivity": DTAMeasure(measure="sensitivity", value=0.80)}
    assert check_consistency(tab, stated) == []


# --------------------------------------------------------------------------
# orchestrator
# --------------------------------------------------------------------------
def test_extract_end_to_end_record():
    t = ("Diagnostic accuracy of D-dimer for pulmonary embolism, with CTPA as the "
         "reference standard. TP = 60, FP = 140, FN = 6, TN = 294. Sensitivity was "
         "90.9% and specificity 67.7%.")
    r = dta.extract(t)
    assert r["domain"] == "cardiology"
    assert len(r["two_by_two"]) == 1
    assert r["poolable"] is True
    rec = r["records"][0]
    assert rec["two_by_two"]["tp"] == 60
    # stated se ~ derived se=60/66=0.909 -> consistent, no notes
    assert rec["consistency"] == []


def test_ligature_normalisation():
    # PDF "fi"/"ffi" ligatures must normalise so the word matches
    t = "The test had a speciﬁcity of 88% and suﬃcient sensitivity of 92%."
    ms = {m["measure"]: m["value"] for m in dta.extract(t)["measures"]}
    assert pytest.approx(ms["specificity"], abs=1e-9) == 0.88
    assert pytest.approx(ms["sensitivity"], abs=1e-9) == 0.92


def test_empty_input():
    r = dta.extract("")
    assert r["poolable"] is False
    assert r["measures"] == [] and r["two_by_two"] == []


# --------------------------------------------------------------------------
# linear-time regex guard (no catastrophic backtracking)
# --------------------------------------------------------------------------
def test_no_catastrophic_backtracking():
    # adversarial inputs that would blow up a poorly-written nested quantifier
    adversarial = [
        "sensitivity " + "9" * 5000,
        "true positives " * 2000,
        ("diagnostic accuracy of " + "abc " * 2000),
        ("a" * 20000),
        "specificity " + "(" * 3000,
    ]
    for text in adversarial:
        start = time.perf_counter()
        measures.extract_measures(text)
        counts.extract_two_by_two(text)
        entities.extract_entities(text)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"regex too slow ({elapsed:.2f}s) on {text[:30]!r}"
