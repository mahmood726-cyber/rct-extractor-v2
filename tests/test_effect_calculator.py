"""
Tests for effect_calculator.py — verify computations against known values.

Uses real data from gold standard COUNTS_ONLY entries where Cochrane's
computed effects are known, plus textbook examples.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.effect_calculator import (
    compute_or,
    compute_rr,
    compute_rd,
    compute_md,
    compute_smd,
    sem_to_sd,
    pct_to_events,
    compute_effect_family_from_raw_data,
    compute_effect_from_raw_data,
)


# ============================================================
# OR from 2×2 table
# ============================================================

class TestComputeOR:
    def test_hirono_2019(self):
        """Hirono 2019: mattress 11/107 vs interrupted 7/103. Cochrane OR≈1.57."""
        result = compute_or(events_t=11, n_t=107, events_c=7, n_c=103)
        assert result is not None
        assert result.effect_type == "OR"
        # Exact OR = (11*96) / (96*7) = 1056/672 = 1.571
        # Wait: a=11, b=107-11=96, c=7, d=103-7=96
        # OR = (11*96)/(96*7) = 1056/672 = 1.5714
        assert abs(result.point_estimate - 1.57) < 0.05
        assert result.ci_lower < 1.57
        assert result.ci_upper > 1.57
        assert result.method == "woolf_log_or"

    def test_delroy_2013(self):
        """Delroy 2013: mesh 7/40 vs AC 17/39. Cochrane OR≈0.27."""
        result = compute_or(events_t=7, n_t=40, events_c=17, n_c=39)
        assert result is not None
        # a=7, b=33, c=17, d=22
        # OR = (7*22)/(33*17) = 154/561 = 0.2745
        assert abs(result.point_estimate - 0.27) < 0.05
        assert result.ci_lower < 0.27
        assert result.ci_upper > 0.27

    def test_feltner_2009(self):
        """Feltner 2009: paroxetine dropout 15/56 vs placebo 18/57. Cochrane OR≈0.79."""
        result = compute_or(events_t=15, n_t=56, events_c=18, n_c=57)
        assert result is not None
        # a=15, b=41, c=18, d=39
        # OR = (15*39)/(41*18) = 585/738 = 0.7927
        assert abs(result.point_estimate - 0.79) < 0.05

    def test_zero_cell_continuity_correction(self):
        """Zero cell should use continuity correction (0.5 added)."""
        result = compute_or(events_t=0, n_t=50, events_c=5, n_c=50)
        assert result is not None
        assert result.notes is not None
        assert "continuity" in result.notes

    def test_all_zero_returns_none(self):
        """Both arms zero events should still compute (with CC)."""
        result = compute_or(events_t=0, n_t=50, events_c=0, n_c=50)
        assert result is not None  # CC makes it computable
        assert abs(result.point_estimate - 1.0) < 0.1  # OR ≈ 1

    def test_invalid_events_gt_n(self):
        """Events > N should return None."""
        result = compute_or(events_t=60, n_t=50, events_c=5, n_c=50)
        assert result is None

    def test_textbook_example(self):
        """Classic 2×2: 10/100 vs 20/100. OR = (10*80)/(90*20) = 0.444."""
        result = compute_or(events_t=10, n_t=100, events_c=20, n_c=100)
        assert result is not None
        assert abs(result.point_estimate - 0.444) < 0.01
        # CI should span the null (1.0) or not — check it contains the point estimate
        assert result.ci_lower <= result.point_estimate <= result.ci_upper


# ============================================================
# RR from 2×2 table
# ============================================================

class TestComputeRR:
    def test_habib_2017(self):
        """Habib 2017: 32% of 26110 vs 25% of 23334. Cochrane RR≈1.28."""
        a = pct_to_events(32, 26110)  # 8355
        c = pct_to_events(25, 23334)  # 5834
        result = compute_rr(events_t=a, n_t=26110, events_c=c, n_c=23334)
        assert result is not None
        assert result.effect_type == "RR"
        assert abs(result.point_estimate - 1.28) < 0.05

    def test_simple_rr(self):
        """50/100 vs 25/100 → RR = 2.0."""
        result = compute_rr(events_t=50, n_t=100, events_c=25, n_c=100)
        assert result is not None
        assert abs(result.point_estimate - 2.0) < 0.01

    def test_zero_control_events(self):
        """Zero events in control should use continuity correction."""
        result = compute_rr(events_t=5, n_t=50, events_c=0, n_c=50)
        assert result is not None
        assert result.notes is not None


# ============================================================
# RD from 2×2 table
# ============================================================

class TestComputeRD:
    def test_simple_rd(self):
        """50/100 vs 25/100 → RD = 0.25."""
        result = compute_rd(events_t=50, n_t=100, events_c=25, n_c=100)
        assert result is not None
        assert abs(result.point_estimate - 0.25) < 0.01

    def test_negative_rd(self):
        """10/100 vs 20/100 → RD = -0.10."""
        result = compute_rd(events_t=10, n_t=100, events_c=20, n_c=100)
        assert result is not None
        assert abs(result.point_estimate - (-0.10)) < 0.01


# ============================================================
# MD from means/SDs
# ============================================================

class TestComputeMD:
    def test_marigold_2005(self):
        """Marigold 2005: 49.1(5.0) n=22 vs 48.1(5.7) n=26. Cochrane MD=1.0."""
        result = compute_md(49.1, 5.0, 22, 48.1, 5.7, 26)
        assert result is not None
        assert result.effect_type == "MD"
        assert abs(result.point_estimate - 1.0) < 0.01
        assert result.method == "independent_groups_md"

    def test_jiang_2020(self):
        """Jiang 2020: NRS 1.43(0.94) n=51 vs 2.13(1.10) n=49. MD=-0.70."""
        result = compute_md(1.43, 0.94, 51, 2.13, 1.10, 49)
        assert result is not None
        assert abs(result.point_estimate - (-0.70)) < 0.01

    def test_beiranvand_2014(self):
        """Beiranvand 2014: SSC 8.76(3.63) n=46 vs routine 7.25(3.50) n=44. MD≈1.51."""
        result = compute_md(8.76, 3.63, 46, 7.25, 3.50, 44)
        assert result is not None
        assert abs(result.point_estimate - 1.51) < 0.01

    def test_jandaghi_2021(self):
        """Jandaghi 2021: TUG 10.0(1.2) n=15 vs 15.4(3.0) n=15. MD=-5.4."""
        result = compute_md(10.0, 1.2, 15, 15.4, 3.0, 15)
        assert result is not None
        assert abs(result.point_estimate - (-5.4)) < 0.01

    def test_zero_sd(self):
        """Zero SD should still work (perfect agreement within group)."""
        result = compute_md(10.0, 0.0, 20, 8.0, 0.0, 20)
        assert result is not None
        assert abs(result.point_estimate - 2.0) < 0.01

    def test_ci_contains_point(self):
        """CI should always contain point estimate."""
        result = compute_md(50.0, 10.0, 30, 45.0, 12.0, 30)
        assert result is not None
        assert result.ci_lower <= result.point_estimate <= result.ci_upper


# ============================================================
# SMD (Hedges' g) from means/SDs
# ============================================================

class TestComputeSMD:
    def test_bomyea_2015(self):
        """Bomyea 2015: HIC 45.32(19.92) n=22, LIC 58.50(18.61) n=20. Cochrane SMD≈-0.67."""
        result = compute_smd(45.32, 19.92, 22, 58.50, 18.61, 20)
        assert result is not None
        assert result.effect_type == "SMD"
        # Cohen's d = (45.32-58.50)/Sp = -13.18/19.30 ≈ -0.683
        # Hedges' J = 1 - 3/(4*40-1) = 1 - 3/159 ≈ 0.9811
        # g = -0.683 * 0.9811 ≈ -0.670
        assert abs(result.point_estimate - (-0.67)) < 0.05
        assert result.method == "hedges_g"

    def test_textbook_smd(self):
        """Large sample SMD ≈ Cohen's d (J → 1)."""
        result = compute_smd(100, 15, 200, 90, 15, 200)
        assert result is not None
        # d = 10/15 = 0.667, J ≈ 0.998 → g ≈ 0.666
        assert abs(result.point_estimate - 0.666) < 0.01

    def test_small_sample_correction(self):
        """Small samples should show bigger Hedges correction."""
        # n=5 per group: J = 1 - 3/(4*8-1) = 1 - 3/31 ≈ 0.903
        result = compute_smd(10, 2, 5, 8, 2, 5)
        assert result is not None
        d = 2 / 2  # Cohen's d = 1.0
        j = 1 - 3 / (4 * 8 - 1)  # 0.9032
        expected_g = d * j
        assert abs(result.point_estimate - expected_g) < 0.01

    def test_n_too_small(self):
        """n=1 per group should return None (df=0)."""
        result = compute_smd(10, 2, 1, 8, 2, 1)
        assert result is None


# ============================================================
# Utility functions
# ============================================================

class TestUtilities:
    def test_sem_to_sd(self):
        """SEM * sqrt(n) = SD."""
        assert abs(sem_to_sd(0.7, 35) - 0.7 * math.sqrt(35)) < 0.001

    def test_pct_to_events(self):
        """32% of 26110 = 8355 (rounded)."""
        assert pct_to_events(32, 26110) == 8355

    def test_pct_to_events_rounding(self):
        """Check proper rounding (Python uses banker's rounding)."""
        assert pct_to_events(50, 101) == 50  # 50.5 → banker's rounds to 50
        assert pct_to_events(33, 100) == 33


# ============================================================
# compute_effect_from_raw_data dispatcher
# ============================================================

class TestComputeFromRawData:
    def test_binary_events(self):
        """Raw data with events/N should compute OR."""
        raw = {"intervention_events": 11, "intervention_n": 107,
               "control_events": 7, "control_n": 103}
        result = compute_effect_from_raw_data(raw, "binary")
        assert result is not None
        assert result.effect_type == "OR"
        assert abs(result.point_estimate - 1.57) < 0.05

    def test_binary_events_as_rr(self):
        """Dispatch to RR when cochrane_effect_type specifies."""
        raw = {"intervention_events": 11, "intervention_n": 107,
               "control_events": 7, "control_n": 103}
        result = compute_effect_from_raw_data(raw, "binary", cochrane_effect_type="RR")
        assert result is not None
        assert result.effect_type == "RR"

    def test_continuous_means(self):
        """Raw data with means/SDs should compute MD."""
        raw = {"intervention_mean": 49.1, "intervention_sd": 5.0, "intervention_n": 22,
               "control_mean": 48.1, "control_sd": 5.7, "control_n": 26}
        result = compute_effect_from_raw_data(raw, "continuous")
        assert result is not None
        assert result.effect_type == "MD"
        assert abs(result.point_estimate - 1.0) < 0.01

    def test_continuous_as_smd(self):
        """Dispatch to SMD when cochrane_effect_type specifies."""
        raw = {"intervention_mean": 45.32, "intervention_sd": 19.92, "intervention_n": 22,
               "control_mean": 58.50, "control_sd": 18.61, "control_n": 20}
        result = compute_effect_from_raw_data(raw, "continuous", cochrane_effect_type="SMD")
        assert result is not None
        assert result.effect_type == "SMD"
        assert abs(result.point_estimate - (-0.67)) < 0.05

    def test_percentage_data(self):
        """Percentage-based data should convert to events first."""
        raw = {"intervention_pct": 32, "intervention_n": 26110,
               "control_pct": 25, "control_n": 23334}
        result = compute_effect_from_raw_data(raw, "binary", cochrane_effect_type="RR")
        assert result is not None
        assert result.effect_type == "RR"
        assert abs(result.point_estimate - 1.28) < 0.05

    def test_change_scores_with_sem(self):
        """Change scores with SEM should convert SEM→SD and compute MD."""
        raw = {"intervention_change": -0.4, "intervention_sem": 0.7, "intervention_n": 35,
               "control_change": 0.2, "control_sem": 0.9, "control_n": 30}
        result = compute_effect_from_raw_data(raw, "continuous")
        assert result is not None
        assert result.effect_type == "MD"
        assert abs(result.point_estimate - (-0.6)) < 0.01

    def test_binary_exp_ctrl_aliases(self):
        """exp_*/ctrl_* aliases should map to intervention/control for binary data."""
        raw = {"exp_cases": 11, "exp_n": 107, "ctrl_cases": 7, "ctrl_n": 103}
        result = compute_effect_from_raw_data(raw, "binary")
        assert result is not None
        assert result.effect_type == "OR"
        assert abs(result.point_estimate - 1.57) < 0.05

    def test_continuous_exp_ctrl_aliases(self):
        """exp_*/ctrl_* aliases should map to intervention/control for continuous data."""
        raw = {
            "exp_mean": 49.1,
            "exp_sd": 5.0,
            "exp_n": 22,
            "ctrl_mean": 48.1,
            "ctrl_sd": 5.7,
            "ctrl_n": 26,
        }
        result = compute_effect_from_raw_data(raw, "continuous")
        assert result is not None
        assert result.effect_type == "MD"
        assert abs(result.point_estimate - 1.0) < 0.01

    def test_empty_raw_data(self):
        """Empty dict should return None."""
        result = compute_effect_from_raw_data({}, "binary")
        assert result is None

    def test_none_raw_data(self):
        """None should return None."""
        result = compute_effect_from_raw_data(None, "binary")
        assert result is None


class TestComputeEffectFamilyFromRawData:
    def test_binary_family_contains_or_rr_rd(self):
        raw = {
            "intervention_events": 11,
            "intervention_n": 107,
            "control_events": 7,
            "control_n": 103,
        }
        results = compute_effect_family_from_raw_data(raw, "binary")
        kinds = {r.effect_type for r in results}
        assert {"OR", "RR", "RD"}.issubset(kinds)

    def test_continuous_family_contains_md_smd(self):
        raw = {
            "intervention_mean": 49.1,
            "intervention_sd": 5.0,
            "intervention_n": 22,
            "control_mean": 48.1,
            "control_sd": 5.7,
            "control_n": 26,
        }
        results = compute_effect_family_from_raw_data(raw, "continuous")
        kinds = {r.effect_type for r in results}
        assert {"MD", "SMD"}.issubset(kinds)
