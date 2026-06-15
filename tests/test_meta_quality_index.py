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


def test_hybrid_rate_uses_real_corpus_marginal_for_covered_axis():
    scores = [score_axis(a, 1.0, 0.5, higher_is_better=True, measured=True) for a in QUALITY_AXES]
    a4 = "A4_pooling_robustness"
    # real corpus: 45% of MAs pass A4 (vs literature 45% too) -> hybrid replaces the
    # A4 marginal and multiplies by literature for the rest
    per_ma = [{a4: True}] * 45 + [{a4: False}] * 55
    out = compute_mdqi(scores, per_ma_pass=per_ma)
    assert out["hybrid_covered_axes"] == [a4]
    rest = 1.0
    for ax in QUALITY_AXES:
        if ax.key != a4:
            rest *= ax.published_pass_rate
    assert math.isclose(out["published_all_pass_rate_hybrid"], 0.45 * rest, abs_tol=1e-6)
    # headline never understated against us: >= independence floor
    assert out["percentile_band_top_pct"] >= round(100 * out["published_all_pass_rate_independent"], 1) - 0.1


def test_gap_to_top5_is_honest_and_computed():
    scores = [score_axis(a, 1.0, 0.5, higher_is_better=True, measured=True) for a in QUALITY_AXES]
    gap = gap_to_top5(scores)
    assert gap["target_top_pct"] == 5.0
    # additional gates needed is computed from the actual current tier, not asserted
    assert isinstance(gap["additional_gates_needed_for_top5"], int)
    assert gap["additional_gates_needed_for_top5"] >= 1     # current tier > 5%
    # the most-discriminating passed axis is reported as the per-axis standing
    assert gap["best_single_axis"] == "A4_pooling_robustness"   # 55% fail = highest
    assert "NOT supported" in gap["note"]                  # no blanket top-5% claim


def test_gap_to_top5_reaches_when_already_below_target():
    # if every axis had a huge fail rate, the composite would already be <=5%
    scores = [score_axis(a, 1.0, 0.5, higher_is_better=True, measured=True) for a in QUALITY_AXES]
    gap = gap_to_top5(scores)
    # current is >5% with the real axes, so not reached and >=1 gate needed
    assert gap["reaches_top5_now"] is (gap["current_top_pct"] <= 5.0)
