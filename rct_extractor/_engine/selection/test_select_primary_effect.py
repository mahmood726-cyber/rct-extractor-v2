"""
Regression tests for select_primary_effect — the mis-grabbed-HR fix.

Rows are verbatim from AACT snapshot aact_2026-04-12 (real registry data), so these
tests pin the exact bug class the deterministic extractors hit: choosing a plausible
but WRONG row (secondary outcome / off-ITT population / single-dose sub-analysis)
when a trial reports many effect estimates.
"""
from select_primary_effect import select_primary_effect, score_candidate, first_row

def C(otype, title, pop, pt, v, lo, hi, gd="", ed=""):
    return {"outcome_type": otype, "title": title, "population": pop, "param_type": pt,
            "param_value": v, "ci_lower_limit": lo, "ci_upper_limit": hi,
            "groups_description": gd, "estimate_description": ed}

# --- CANVAS NCT01032629: 3 PRIMARY MACE HRs (dose-1, dose-2, combined) + SECONDARY on-treatment renal ---
CANVAS = [
    C("PRIMARY", "Major Adverse Cardiovascular Events (MACE)",
      "the intent-to-treat (ITT) analysis set ... all randomized participants", "Hazard Ratio (HR)",
      0.93, 0.78, 1.12, "canagliflozin 100 mg versus placebo"),
    C("PRIMARY", "Major Adverse Cardiovascular Events (MACE)",
      "the intent-to-treat (ITT) analysis set ... all randomized participants", "Hazard Ratio (HR)",
      0.88, 0.75, 1.03, "combined for both doses"),
    C("SECONDARY", "Progression of Albuminuria",
      "On-treatment analysis set ... received at least 1 dose", "Odds Ratio (OR)",
      0.80, 0.67, 0.97),
    C("SECONDARY", "Change in Urinary Albumin/Creatinine Ratio",
      "On-treatment analysis set ... evaluable participants", "Geometric mean ratio",
      0.71, 0.58, 0.85),
]

def test_canvas_bug_reproduced_by_naive():
    # a "grab the striking number" prose extractor lands on the significant renal effect
    striking = min(CANVAS, key=lambda c: c["param_value"])
    assert striking["param_value"] == 0.71 and striking["outcome_type"] == "SECONDARY"

def test_canvas_selector_picks_primary_mace_not_renal():
    pick = select_primary_effect(CANVAS)["pick"]
    assert pick["outcome_type"] == "PRIMARY"
    assert "MACE" in pick["title"]
    assert pick["param_value"] in (0.93, 0.88)   # a primary MACE HR, never a renal secondary

def test_canvas_prefers_combined_over_single_dose():
    # among the two PRIMARY MACE rows, the dose-COMBINED one outranks the single-dose sub-analysis
    pick = select_primary_effect(CANVAS)["pick"]
    assert pick["param_value"] == 0.88

# --- PRoFESS NCT00153062: ITT population phrased "...regardless of whether still on treatment" ---
def test_itt_marker_overrides_bare_on_treatment():
    itt_primary = C("PRIMARY", "First Recurrent Stroke",
        "analyzed as randomized ... regardless of whether they were still on treatment",
        "Hazard Ratio (HR)", 1.01, 0.92, 1.11)
    sc, reasons = score_candidate(itt_primary)
    assert "ITT" in reasons and "off-ITT(-)" not in reasons

# --- A stratified primary analysis is the OVERALL analysis, not a subgroup ---
def test_stratified_by_is_not_a_subgroup():
    strat = C("PRIMARY", "Overall Survival",
        "All randomized participants", "Hazard Ratio (HR)", 0.94, 0.77, 1.14,
        gd="Cox model stratified by region and prior therapy")
    sc, reasons = score_candidate(strat)
    assert "subgroup(-)" not in reasons

# --- off-ITT / subgroup rows are demoted below a clean primary ---
def test_off_itt_and_subgroup_demoted():
    clean = C("PRIMARY", "Overall Survival", "Full Analysis Set (all randomized)",
              "Hazard Ratio (HR)", 0.80, 0.65, 0.98)
    pp = C("PRIMARY", "Overall Survival", "Per-protocol set", "Hazard Ratio (HR)",
           0.55, 0.40, 0.75)
    sub = C("PRIMARY", "Overall Survival", "subgroup: PD-L1 >= 50%", "Hazard Ratio (HR)",
            0.40, 0.25, 0.64)
    assert select_primary_effect([pp, sub, clean])["pick"] is clean

# --- co-primary tie: keep SOURCE ORDER and FLAG ambiguous (don't silently reorder) ---
def test_coprimary_keeps_source_order_and_flags():
    a = C("PRIMARY", "Radiographic PFS", "All randomized participants", "Hazard Ratio (HR)", 1.20, 0.96, 1.49)
    b = C("PRIMARY", "Overall Survival", "All randomized participants", "Hazard Ratio (HR)", 1.16, 0.88, 1.53)
    r = select_primary_effect([a, b])
    assert r["pick"] is a and r["ambiguous"] is True

def test_empty_and_singleton():
    assert select_primary_effect([])["pick"] is None
    one = C("PRIMARY", "X", "ITT", "Hazard Ratio (HR)", 0.9, 0.8, 1.0)
    assert select_primary_effect([one])["pick"] is one

if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"  PASS {fn.__name__}")
        except AssertionError as e:
            print(f"  FAIL {fn.__name__}: {e}")
    print(f"{p}/{len(fns)} passed")
    sys.exit(0 if p == len(fns) else 1)
