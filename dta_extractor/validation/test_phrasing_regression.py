"""Regression tests for DTA measure phrasing (value-first swap fix, 2026-07-12).

Guards the root-cause fix for the value-before-keyword label SWAP found on the
malaria/TB/HIV Uganda gold set: "95.2% sensitivity, 66.4% specificity" was being
read as sensitivity=0.664 (the specificity value). See DTA-UGANDA-2026-07-12.md.
"""
from dta_extractor._engine.measures import extract_measures


def _pairs(txt):
    return [(m.measure, round(m.value, 3)) for m in extract_measures(txt)]


def test_value_first_no_swap():
    p = _pairs("SD-Bioline had 95.2% sensitivity, 66.4% specificity.")
    assert ("sensitivity", 0.952) in p
    assert ("specificity", 0.664) in p
    # the swap bug produced sensitivity=0.664; assert it is gone
    assert ("sensitivity", 0.664) not in p


def test_keyword_first_still_works():
    p = _pairs("The sensitivity was 95.2% and the specificity was 66.4%.")
    assert ("sensitivity", 0.952) in p and ("specificity", 0.664) in p


def test_paired_respectively_adjacent():
    p = _pairs("The sensitivity and specificity were 96.6% and 60% respectively.")
    assert ("sensitivity", 0.966) in p and ("specificity", 0.6) in p


def test_gapped_label_testname_value():
    p = _pairs("the sensitivity of tongue swab Xpert Ultra was 77.8% "
               "(95% CI 64.4-88.0) and specificity was 100.0%")
    assert ("sensitivity", 0.778) in p and ("specificity", 1.0) in p


def test_negative_context_still_rejected():
    assert _pairs("assuming a sensitivity of 90% to detect a difference") == []


def test_value_first_ci_after_label():
    p = _pairs("Ultra had an overall sensitivity of 87.5% (95% CI 82.1-91.7).")
    assert ("sensitivity", 0.875) in p
