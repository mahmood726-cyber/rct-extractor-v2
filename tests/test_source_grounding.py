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
