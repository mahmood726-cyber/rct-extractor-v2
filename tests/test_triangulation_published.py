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
from rct_extractor._engine.core.diagnostic_accuracy_extractor import extract_diagnostic_accuracy
from rct_extractor._engine.specialties.internal_consistency import (
    check_consistency, dta_plr, dta_nlr,
)


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


# DTA -- Elli et al., Diagn Microbiol Infect Dis 2022;102:115635.
# PMID 35216863, DOI 10.1016/j.diagmicrobio.2022.115635. LumiraDx rapid antigen
# test vs RT-PCR. Se/Sp/PLR/NLR are mutually checkable WITHOUT 2x2 counts.
ELLI = ("The sensitivity and specificity of RAD were 34.2% and 92.3%. "
        "Positive and negative likelihood ratios were 4.4 and 0.71.")


def test_elli_combined_sens_spec_extracted():
    # combined no-CI 'sensitivity and specificity were X% and Y%' must parse
    ds = extract_diagnostic_accuracy(ELLI)
    by = {d.measure_type.value: d.point_estimate for d in ds}
    assert abs(by.get("Sensitivity", 0) - 34.2) < 1e-6
    assert abs(by.get("Specificity", 0) - 92.3) < 1e-6


def test_elli_likelihood_ratios_are_coherent():
    # the trial's own reported LRs must match Se/Sp: PLR=Se/(1-Sp), NLR=(1-Se)/Sp
    se, sp = 0.342, 0.923
    assert abs(dta_plr(se, sp) - 4.44) < 0.05      # published 4.4
    assert abs(dta_nlr(se, sp) - 0.713) < 0.01     # published 0.71
    good = {"type": "DTA", "sensitivity": se, "specificity": sp, "plr": 4.4, "nlr": 0.71}
    assert "dta_lr_mismatch" not in check_consistency(good)["flags"]


def test_dta_lr_mismatch_flags_inconsistent_lr():
    # a transcribed PLR that doesn't match Se/Sp is caught
    bad = {"type": "DTA", "sensitivity": 0.342, "specificity": 0.923, "plr": 9.9}
    assert "dta_lr_mismatch" in check_consistency(bad)["flags"]


# DTA (CI-anchored) -- Zheng et al., PLoS One 2023;18:e0279726.
# PMID 36812225, DOI 10.1371/journal.pone.0279726. miRNAs for sepsis. Decimal
# Se/Sp with "(95% [confidence interval] CI, lo to hi)" -- the comma + "to" form.
ZHENG = ("The overall performance of total miRNAs detection was: pooled "
         "sensitivity, 0.76 (95% confidence interval [CI], 0.75 to 0.77); pooled "
         "specificity, 0.77 (95%CI, 0.75 to 0.78); and area under the summary "
         "receiver operating characteristic curves value (SROC), 0.86.")


def test_zheng_decimal_ci_to_format_extracted():
    ds = extract_diagnostic_accuracy(ZHENG)
    by = {d.measure_type.value: (d.point_estimate, d.ci_lower, d.ci_upper) for d in ds}
    assert by.get("Sensitivity") == (0.76, 0.75, 0.77)
    assert by.get("Specificity") == (0.77, 0.75, 0.78)


# Dose-response -- Greenwood et al., Br J Nutr 2014;112:725-34.
# PMID 24932880, DOI 10.1017/S0007114514001329. Sugar-sweetened soft drinks and
# type 2 diabetes: a PER-INCREMENT trend "RR 1.20/330 ml per d (95% CI 1.12, 1.29)".
GREENWOOD = ("The summary RR for sugar-sweetened and artificially sweetened soft "
             "drinks were 1.20/330 ml per d (95% CI 1.12, 1.29, P<0.001) and "
             "1.13/330 ml per d (95% CI 1.02, 1.25, P=0.02), respectively.")


def test_greenwood_per_increment_dose_response_extracted():
    from rct_extractor._engine.core.doseresponse_extractor import DoseResponseExtractor
    res = DoseResponseExtractor().extract(GREENWOOD)
    effs = getattr(res, "effects", res) or []
    # the sugar-sweetened per-330 ml/day RR 1.20 (95% CI 1.12-1.29) must be caught
    hit = [e for e in effs if abs(e.point_estimate - 1.20) < 1e-6]
    assert hit, f"missed RR 1.20/330 ml per d; got {[e.point_estimate for e in effs]}"
    e = hit[0]
    assert e.relation_type.value == "per_unit"
    assert e.dose_amount == 330.0 and e.dose_unit == "ml"
    assert abs(e.ci_lower - 1.12) < 1e-6 and abs(e.ci_upper - 1.29) < 1e-6


# Dose-response (MA-summary prose) -- Crippa et al., Am J Epidemiol 2014;180:763-75.
# PMID 25156996, DOI 10.1093/aje/kwu194. Coffee and mortality: categorical risk
# reductions "for 4 cups/day ... (16%, 95% CI: 13, 18)" -> RR on the ratio scale.
CRIPPA = ("The largest risk reductions were observed for 4 cups/day for all-cause "
          "mortality (16%, 95% confidence interval: 13, 18) and 3 cups/day for CVD "
          "mortality (21%, 95% confidence interval: 16, 26).")


def test_crippa_ma_summary_risk_reduction_extracted():
    from rct_extractor._engine.core.doseresponse_extractor import DoseResponseExtractor
    effs = DoseResponseExtractor().extract(CRIPPA).effects
    by = {e.category_label: e for e in effs}
    # 16% reduction at 4 cups/day -> RR 0.84 (95% CI 0.82-0.87, bounds flipped)
    e4 = by.get("4 cups/day")
    assert e4 and abs(e4.point_estimate - 0.84) < 1e-6
    assert abs(e4.ci_lower - 0.82) < 1e-6 and abs(e4.ci_upper - 0.87) < 1e-6
    assert e4.effect_type.value == "RR" and e4.relation_type.value == "categorical"
    # 21% reduction at 3 cups/day -> RR 0.79 (0.74-0.84)
    e3 = by.get("3 cups/day")
    assert e3 and abs(e3.point_estimate - 0.79) < 1e-6


def test_ma_summary_requires_risk_reduction_cue():
    # identical numeric shape WITHOUT a risk-reduction cue must NOT extract
    from rct_extractor._engine.core.doseresponse_extractor import DoseResponseExtractor
    txt = "In a survey, 4 cups/day for adults (16%, 95% CI: 13, 18) reported poor sleep."
    assert DoseResponseExtractor().extract(txt).effects == []
