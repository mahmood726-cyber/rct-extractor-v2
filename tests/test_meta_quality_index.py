"""Tests for the Meta Data-Quality Index (composite published-MA benchmark)."""
import math

from rct_extractor._engine.benchmark.meta_quality_index import (
    QUALITY_AXES,
    QualityAxis,
    score_axis,
    published_joint_pass_rate_independent,
    published_joint_pass_rate_observed,
    compute_mdqi,
    gap_to_top5,
)


def test_axes_are_cited_and_in_range():
    assert len(QUALITY_AXES) >= 5
    for a in QUALITY_AXES:
        assert 0.0 <= a.published_fail_rate <= 1.0
        assert a.source and a.our_mechanism            # every axis is traceable
        assert math.isclose(a.published_pass_rate, 1 - a.published_fail_rate)


def test_score_axis_higher_and_lower_is_better():
    a = QUALITY_AXES[0]
    assert score_axis(a, 0.96, 0.95, higher_is_better=True, measured=True).passed
    assert not score_axis(a, 0.90, 0.95, higher_is_better=True, measured=True).passed
    # a flag/error RATE: lower is better
    assert score_axis(a, 0.0, 0.0, higher_is_better=False, measured=True).passed
    assert not score_axis(a, 0.1, 0.0, higher_is_better=False, measured=True).passed


def test_score_axis_unmeasured_is_not_a_pass():
    s = score_axis(QUALITY_AXES[0], None, 0.95, higher_is_better=True, measured=False)
    assert s.passed is False and s.measured is False


def test_independence_floor_is_product():
    p = published_joint_pass_rate_independent(QUALITY_AXES)
    expected = 1.0
    for a in QUALITY_AXES:
        expected *= (1 - a.published_fail_rate)
    assert math.isclose(p, expected)
    assert 0.0 < p < 1.0


def test_observed_joint_pass_rate_counts_all_pass_only():
    rows = [
        {"A1": True, "A2": True, "A4": True},     # all pass
        {"A1": True, "A2": False, "A4": True},    # fails A2
        {"A1": True, "A2": True, "A4": False},    # fails A4
    ]
    assert math.isclose(published_joint_pass_rate_observed(rows), 1 / 3)
    assert published_joint_pass_rate_observed([]) is None


def test_compute_mdqi_all_pass_yields_percentile():
    scores = [score_axis(a, 1.0, 0.5, higher_is_better=True, measured=True) for a in QUALITY_AXES]
    out = compute_mdqi(scores)
    assert out["our_gates_passed"] == out["our_gates_total"]
    assert out["our_all_pass_measured"] is True
    # independence floor with A4 (55% fail) present must be well under 50%
    assert 0 < out["percentile_band_top_pct"] < 50
    assert "AACT" in out["source_constraint"]


def test_compute_mdqi_unmeasured_axis_blocks_claim():
    scores = [score_axis(a, 1.0, 0.5, higher_is_better=True, measured=True) for a in QUALITY_AXES]
    scores[0] = score_axis(QUALITY_AXES[0], None, 0.5, higher_is_better=True, measured=False)
    out = compute_mdqi(scores)
    assert out["our_all_pass_measured"] is False
    assert "not yet earned" in out["interpretation"]


def test_observed_rate_is_used_and_is_the_honest_figure():
    scores = [score_axis(a, 1.0, 0.5, higher_is_better=True, measured=True) for a in QUALITY_AXES]
    # observed (e.g. real Pairwise70 joint pass) higher than independence floor
    per_ma = [{"x": True}] * 30 + [{"x": False}] * 70   # 30% all-pass
    out = compute_mdqi(scores, per_ma_pass=per_ma)
    assert math.isclose(out["published_all_pass_rate_observed"], 0.30)
    # reported percentile uses the larger (less self-flattering) of indep/observed
    assert out["percentile_band_top_pct"] >= 100 * out["published_all_pass_rate_independent"]


def test_gap_to_top5_names_concrete_axes():
    scores = [score_axis(a, 1.0, 0.5, higher_is_better=True, measured=True) for a in QUALITY_AXES]
    gap = gap_to_top5(scores)
    assert gap["target_top_pct"] == 5.0
    keys = {c["key"] for c in gap["candidate_axes"]}
    assert "A6_trustworthiness" in keys           # INSPECT-SR
    assert all(c["rationale"] for c in gap["candidate_axes"])


def test_gap_to_top5_projection_is_computed_not_asserted():
    # The projected tier must equal the current tier times the candidate pass factors.
    scores = [score_axis(a, 1.0, 0.5, higher_is_better=True, measured=True) for a in QUALITY_AXES]
    gap = gap_to_top5(scores)
    base = gap["current_top_pct"] / 100.0
    expected = base
    for c in gap["candidate_axes"]:
        expected *= (1 - c["published_fail_rate"])
    assert math.isclose(gap["projected_top_pct_after_candidates"], round(100 * expected, 1), abs_tol=0.2)
    # honesty: reaches_top5 must agree with the computed number, not be asserted
    assert gap["reaches_top5_as_composite"] == (gap["projected_top_pct_after_candidates"] <= 5.0)
