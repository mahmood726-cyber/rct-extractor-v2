"""Triangulation against real published trials (not synthetic).

Each fixture is a verbatim PubMed abstract; we assert the extractor reproduces
the trial's OWN published estimate (oracle-free -- the trial reports its number,
so there is no meta-analysis-method ambiguity), that the value is internally
consistent (no false flags), and we PIN known limitations so a future fix has a
regression target. Published meta-analyses are a comparator for triangulation,
NOT ground truth (different trials/sources/methods + human error); these tests
therefore check against each trial's self-reported value, not a pooled one.
"""
import pytest

from rct_extractor.api import extract


# STEP 1 -- Wilding et al., N Engl J Med 2021;384:989-1002.
# PMID 33567185, DOI 10.1056/NEJMoa2032183. NCT03548935.
STEP1 = (
    "The mean change in body weight from baseline to week 68 was -14.9% in the "
    "semaglutide group as compared with -2.4% with placebo, for an estimated "
    "treatment difference of -12.4 percentage points (95% confidence interval "
    "[CI], -13.4 to -11.5; P<0.001)."
)


def _effects(text):
    return extract(text).get("effects", [])


def test_step1_treatment_difference_value_matches_publication():
    # the between-group difference -12.4 (95% CI -13.4 to -11.5) is the trial's
    # own primary estimate; we must reproduce it exactly and ground its CI.
    effs = _effects(STEP1)
    hit = [e for e in effs if abs((e.get("effect_size") or 0) + 12.4) < 1e-6]
    assert hit, f"did not extract the -12.4 treatment difference; got {[e.get('effect_size') for e in effs]}"
    e = hit[0]
    assert abs(e["ci_lower"] - (-13.4)) < 1e-6 and abs(e["ci_upper"] - (-11.5)) < 1e-6


def test_step1_extraction_is_internally_consistent():
    # a correct extraction must raise NO consistency flag (point in CI, etc.)
    effs = _effects(STEP1)
    hit = [e for e in effs if abs((e.get("effect_size") or 0) + 12.4) < 1e-6][0]
    assert (hit.get("consistency") or {}).get("flags") in ([], None)


def test_step1_percentage_point_difference_typed_as_md():
    # The body-weight %-change between-group difference is a MEAN DIFFERENCE, not
    # a binary risk difference -- context-gated ARD->MD reclassification handles
    # the "percentage points" ambiguity (a true risk difference stays ARD).
    effs = _effects(STEP1)
    hit = [e for e in effs if abs((e.get("effect_size") or 0) + 12.4) < 1e-6][0]
    assert str(hit.get("type")).upper() in ("MD", "WMD", "MEANDIFFERENCE")
    assert len(effs) == 1, "must not double-extract (ARD twin)"


# --- ARD vs MD disambiguation (context-gated, FP-safe) ----------------------

@pytest.mark.parametrize("text,expected", [
    ("The mean change in systolic blood pressure was a treatment difference of "
     "-5.0 percentage points (95% CI -7.0 to -3.0).", "MD"),
    ("Change in HbA1c from baseline: treatment difference of -1.2 percentage "
     "points (95% CI -1.5 to -0.9).", "MD"),
    # true risk differences must STAY ARD
    ("The absolute risk difference for death was a treatment difference of -4.2 "
     "percentage points (95% CI, -6.8 to -1.6).", "ARD"),
    ("The rate of myocardial infarction differed by a treatment difference of "
     "2.1 percentage points (95% CI 0.5 to 3.7).", "ARD"),
])
def test_ard_vs_md_disambiguation(text, expected):
    effs = _effects(text)
    assert effs, f"no effect extracted from: {text!r}"
    assert effs[0]["type"] == expected
    assert len(effs) == 1, "single effect only (no cross-type twin)"
