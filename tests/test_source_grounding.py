"""Tests for source-grounding & multi-candidate disambiguation.

These catch the internally-consistent-but-wrong extractions the consistency
audit surfaced: a ratio value absent from the source (wrong estimand), >=2
same-type estimates in the text (wrong comparison), and >=2 distinct effect
types (ambiguous which outcome is the target). All flag-only / soft.
"""
from rct_extractor._engine.specialties.source_grounding import (
    value_grounded,
    count_type_mentions,
    check_grounding,
    annotate_grounding,
    order_effects,
    denominator_consistency,
    terminal_digit_uniform,
    annotate_trial_level,
    check_pool_measures,
)

RABEAM = ("RA-BEAM: Baricitinib showed superior ACR20 response vs placebo at week 12 "
          "(70% vs 40%; OR 3.0, 95% CI 2.3-4.0). vs adalimumab: OR 1.4 (1.0-1.9).")
GOOD = "CHARM: candesartan. All-cause mortality: hazard ratio 0.84 (95% CI 0.77-0.91)."


# --- value grounding (ratio only, sign-agnostic) ---

def test_value_grounded_present_and_absent():
    assert value_grounded(0.84, GOOD) is True
    assert value_grounded(0.64, GOOD) is False           # 0.64 not in this text


def test_value_grounded_sign_agnostic():
    assert value_grounded(-12.4, "Weight change vs placebo: MD -12.4% ...") is True
    assert value_grounded(12.4, "difference was 12.4 points") is True


def test_grounding_skips_difference_types():
    # MD/ARD/SMD are derived/rounded -> never value-grounded-flagged (would FP).
    assert check_grounding({"type": "MD", "effect_size": -1.6}, "rates 1.65% vs 2.19%") == []


def test_wrong_estimand_ratio_value_absent_is_flagged():
    # an HR whose value is nowhere in a mean-difference abstract -> wrong estimand
    txt = "FVC decline difference 109.9 ml/year (95% CI 75.9-144.0)."
    assert "value_not_in_source" in check_grounding({"type": "HR", "effect_size": 0.64}, txt)


# --- multi-candidate (same type) ---

def test_multiple_candidates_counts_distinct_values():
    assert count_type_mentions(RABEAM, "OR") == 2
    assert "multiple_candidates" in check_grounding({"type": "OR", "effect_size": 1.4}, RABEAM)


def test_english_or_not_matched_as_odds_ratio():
    assert count_type_mentions("death or stroke occurred in 30 patients", "OR") == 0


def test_single_estimate_not_flagged():
    assert count_type_mentions(GOOD, "HR") == 1
    assert check_grounding({"type": "HR", "effect_size": 0.84}, GOOD) == []


# --- multiple effect TYPES (ambiguous primary) ---

def test_multiple_effect_types_flags_all():
    effects = [{"type": "HR", "effect_size": 0.64}, {"type": "MD", "effect_size": 109.9}]
    out = annotate_grounding(effects, "difference 109.9; HR 0.64")
    assert all("multiple_effect_types" in e["grounding"]["flags"] for e in out)
    assert all(e["needs_review"] for e in out)


def test_same_type_effects_not_flagged_multitype():
    effects = [{"type": "HR", "effect_size": 0.84}, {"type": "HR", "effect_size": 0.90}]
    out = annotate_grounding(effects, GOOD)
    assert not any("multiple_effect_types" in e["grounding"]["flags"] for e in out)


def test_annotate_merges_into_consistency_and_sets_review():
    effects = [{"type": "OR", "effect_size": 1.4, "consistency": {"flags": [], "score": 1.0}}]
    out = annotate_grounding(effects, RABEAM)
    assert out[0]["needs_review"] is True
    assert "multiple_candidates" in out[0]["consistency"]["flags"]   # merged for the audit


def test_clean_single_extraction_no_grounding_flags():
    effects = [{"type": "HR", "effect_size": 0.84, "consistency": {"flags": [], "score": 1.0}}]
    out = annotate_grounding(effects, GOOD)
    assert out[0]["grounding"]["flags"] == []
    assert not out[0].get("needs_review")


# --- effect ordering (primary outcome first) -------------------------------

INPULSIS = ("INPULSIS: Nintedanib reduced annual FVC decline in IPF "
            "(-113.6 vs -223.5 ml/year; difference 109.9 ml/year; 95% CI 75.9-144.0). "
            "Time to first acute exacerbation: HR 0.64 (0.39-1.05).")


def test_order_effects_puts_primary_outcome_first_by_position():
    # extractor returned the secondary HR first; the primary MD is mentioned earlier
    effects = [{"type": "HR", "effect_size": 0.64}, {"type": "MD", "effect_size": 109.9}]
    out = order_effects(effects, INPULSIS)
    assert out[0]["type"] == "MD" and out[0]["effect_size"] == 109.9


def test_order_effects_explicit_primary_label_promoted():
    txt = "Secondary endpoint: OR 1.4 (1.0-1.9). Primary outcome: OR 2.0 (1.5-2.7)."
    effects = [{"type": "OR", "effect_size": 1.4}, {"type": "OR", "effect_size": 2.0}]
    out = order_effects(effects, txt)
    assert out[0]["effect_size"] == 2.0          # primary promoted despite later position


def test_order_effects_stable_and_lossless():
    effects = [{"type": "HR", "effect_size": 0.84}, {"type": "MD", "effect_size": -4.0}]
    out = order_effects(effects, GOOD)            # only one value locatable
    assert len(out) == 2 and {e["effect_size"] for e in out} == {0.84, -4.0}


# --- cross-outcome denominator consistency ----------------------------------

def test_denominator_consistent_arms_not_flagged():
    effects = [
        {"type": "HR", "n_tx": 500, "n_ctrl": 505},
        {"type": "HR", "n_tx": 500, "n_ctrl": 505},
    ]
    annotate_trial_level(effects)
    assert not any(e.get("needs_review") for e in effects)


def test_denominator_drift_flagged():
    # one outcome reports a different treatment-arm N (misread/evaluable-subset)
    effects = [
        {"type": "HR", "n_tx": 500, "n_ctrl": 505},
        {"type": "HR", "n_tx": 500, "n_ctrl": 505},
        {"type": "OR", "n_tx": 312, "n_ctrl": 505},   # 312 != modal 500
    ]
    annotate_trial_level(effects)
    bad = [e for e in effects if e.get("needs_review")]
    assert bad and bad[0]["n_tx"] == 312


def test_denominator_needs_two_values():
    effects = [{"type": "HR", "n_tx": 500, "n_ctrl": 505}]
    assert denominator_consistency(effects) == []


# --- terminal-digit advisory ------------------------------------------------

def test_terminal_digit_uniform_passes_on_varied_counts():
    vals = list(range(30, 90))   # 60 values, all terminal digits present ~evenly
    assert terminal_digit_uniform(vals) is True


def test_terminal_digit_anomaly_on_all_zeros():
    vals = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100] * 4   # all end in 0
    assert terminal_digit_uniform(vals) is False


def test_terminal_digit_too_few_skips():
    assert terminal_digit_uniform([10, 20, 30]) is None


# --- pool summary-measure homogeneity (Cochrane §10.4) ----------------------

def test_pool_continuous_with_binary_is_hard_flag():
    # the cardinal error: a mean difference pooled with an odds ratio
    effects = [{"type": "MD"}, {"type": "OR"}, {"type": "MD"}]
    assert check_pool_measures(effects) == ["mixed_continuous_and_binary"]


def test_pool_continuous_with_hazard_is_hard_flag():
    effects = [{"type": "SMD"}, {"type": "HR"}]
    assert check_pool_measures(effects) == ["mixed_continuous_and_binary"]


def test_pool_two_ratio_families_is_soft_flag():
    # HR (time-to-event) pooled with OR (binary) -> different scales, soft
    effects = [{"type": "HR"}, {"type": "OR"}]
    assert check_pool_measures(effects) == ["mixed_summary_measure"]


def test_pool_or_and_rr_subtype_flag():
    effects = [{"type": "OR"}, {"type": "RR"}, {"type": "OR"}]
    assert check_pool_measures(effects) == ["mixed_effect_subtype"]


def test_pool_md_and_smd_subtype_flag():
    # raw mean difference and standardized mean difference are different scales
    effects = [{"type": "MD"}, {"type": "SMD"}]
    assert check_pool_measures(effects) == ["mixed_effect_subtype"]


def test_pool_homogeneous_or_is_clean():
    effects = [{"type": "OR"}, {"type": "OR"}, {"type": "OR"}]
    assert check_pool_measures(effects) == []


def test_pool_homogeneous_hr_is_clean():
    assert check_pool_measures([{"type": "HR"}, {"type": "HR"}]) == []


def test_pool_ignores_unknown_and_empty_types():
    # unknown/blank types are not classifiable -> no false homogeneity error
    assert check_pool_measures([{"type": "OR"}, {"type": ""}, {"type": "FOO"}]) == []


def test_pool_aliases_normalize():
    # full-word aliases map to the same family as their abbreviations
    assert check_pool_measures([{"type": "oddsRatio"}, {"type": "RR"}]) == ["mixed_effect_subtype"]
    assert check_pool_measures([{"type": "hazardRatio"}, {"type": "MD"}]) == ["mixed_continuous_and_binary"]
