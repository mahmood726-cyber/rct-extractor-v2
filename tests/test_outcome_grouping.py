"""Tests for the outcome-mixing guard and maximum-valid-pooling partition.

Outcome mixing (pooling different constructs / time points as one) is the
'deadly' meta-analysis error -- invisible to numeric checks because every number
is individually correct. These tests pin the guard and the partitioner.
"""
from rct_extractor._engine.specialties.outcome_grouping import (
    canonical_outcome,
    parse_timepoint,
    outcome_signature,
    annotate_outcomes,
    check_pool_outcomes,
    partition_valid_pools,
)


# --- canonical outcome + timepoint parsing ----------------------------------

def test_canonical_outcome_normalizes_synonyms():
    assert canonical_outcome("death from any cause was lower") == "all-cause mortality"
    assert canonical_outcome("cardiovascular mortality") == "cardiovascular death"
    assert canonical_outcome("hospitalization for heart failure") == "hospitalization for heart failure"


def test_canonical_outcome_unknown_returns_none():
    assert canonical_outcome("the widget score improved") is None


def test_canonical_outcome_word_boundary_no_mi_in_mild():
    # 'mi' must not fire inside 'mild' / 'family'
    assert canonical_outcome("mild symptoms in the family") is None


def test_parse_timepoint_units_to_days():
    assert parse_timepoint("at 52 weeks")[0] == 52 * 7
    assert parse_timepoint("over 6 months")[0] == 6 * 30
    assert parse_timepoint("no time here") is None


def test_outcome_signature_uses_clause_before_effect():
    txt = ("All-cause mortality at 52 weeks was lower (HR 0.80). "
           "Myocardial infarction at 52 weeks: HR 0.70.")
    mi_pos = txt.index("HR 0.70")
    sig = outcome_signature(txt, char_start=mi_pos)
    assert sig["outcome"] == "myocardial infarction"
    assert sig["timepoint_days"] == 52 * 7


# --- the guard: mixed outcomes / timepoints ---------------------------------

def test_mixed_outcome_flagged_deadly():
    effects = [
        {"outcome_signature": {"outcome": "all-cause mortality", "timepoint_days": 364}},
        {"outcome_signature": {"outcome": "cardiovascular death", "timepoint_days": 364}},
    ]
    assert "mixed_outcome" in check_pool_outcomes(effects)


def test_same_outcome_not_flagged():
    effects = [
        {"outcome_signature": {"outcome": "all-cause mortality", "timepoint_days": 364}},
        {"outcome_signature": {"outcome": "all-cause mortality", "timepoint_days": 350}},
    ]
    assert check_pool_outcomes(effects) == []


def test_mixed_timepoint_flagged():
    effects = [
        {"outcome_signature": {"outcome": "all-cause mortality", "timepoint_days": 84}},   # 12wk
        {"outcome_signature": {"outcome": "all-cause mortality", "timepoint_days": 364}},  # 52wk
    ]
    assert "mixed_timepoint" in check_pool_outcomes(effects)


def test_unknown_outcomes_never_false_flag():
    # two unrecognised but correctly-matched outcomes -> no assertion of mixing
    effects = [
        {"outcome_signature": {"outcome": None, "timepoint_days": 84}},
        {"outcome_signature": {"outcome": None, "timepoint_days": 90}},
    ]
    assert check_pool_outcomes(effects) == []


def test_annotate_outcomes_binds_each_effect():
    txt = ("All-cause mortality was lower (HR 0.80). "
           "Stroke: HR 0.70.")
    effects = [
        {"type": "HR", "effect_size": 0.80, "char_start": txt.index("HR 0.80")},
        {"type": "HR", "effect_size": 0.70, "char_start": txt.index("HR 0.70")},
    ]
    annotate_outcomes(effects, txt)
    assert effects[0]["outcome_signature"]["outcome"] == "all-cause mortality"
    assert effects[1]["outcome_signature"]["outcome"] == "stroke"
    assert "mixed_outcome" in check_pool_outcomes(effects)


# --- maximum valid pooling --------------------------------------------------

def test_partition_groups_by_outcome_measure_timepoint():
    items = [
        {"label": "A", "type": "HR", "outcome": "all-cause mortality", "timepoint_days": 364},
        {"label": "B", "type": "HR", "outcome": "all-cause mortality", "timepoint_days": 350},
        {"label": "C", "type": "HR", "outcome": "cardiovascular death", "timepoint_days": 364},
        {"label": "D", "type": "OR", "outcome": "all-cause mortality", "timepoint_days": 364},
    ]
    pools = partition_valid_pools(items)
    # largest valid pool = A+B (same outcome, HR, same bucket)
    assert {it["label"] for it in pools[0]["items"]} == {"A", "B"}
    assert pools[0]["key"]["outcome"] == "all-cause mortality"
    # C (different outcome) and D (different measure) are separate pools
    assert len(pools) == 3


def test_partition_maximises_pool_size_not_fragments_unknowns():
    # items with no outcome/timepoint info should NOT fragment -> one pool
    items = [{"label": x, "type": "OR"} for x in "ABCDE"]
    pools = partition_valid_pools(items)
    assert len(pools) == 1 and len(pools[0]["items"]) == 5
