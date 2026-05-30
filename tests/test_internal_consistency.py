"""
Tests for the internal-consistency layer (src/specialties/internal_consistency.py).

Anchors the Altman-Bland CI<->p formulas and confirms the checks catch the
extraction-error classes they target (misread digit, point outside CI, reversed
CI bounds, significance flip) without flagging correct extractions.
"""
import math
import pytest

from src.specialties.internal_consistency import (
    two_sided_p_from_z, z_from_p, check_consistency, annotate,
)


# --- Altman-Bland formula anchors ---

def test_p_from_z_anchors():
    assert abs(two_sided_p_from_z(1.96) - 0.05) < 0.005     # CI touches null
    assert abs(two_sided_p_from_z(2.58) - 0.01) < 0.003
    assert two_sided_p_from_z(0.0) == pytest.approx(1.0, abs=1e-9)


def test_z_from_p_inverse_consistent():
    # forward then inverse should round-trip approximately
    for z in (1.0, 1.96, 2.5, 3.0):
        p = two_sided_p_from_z(z)
        assert abs(z_from_p(p) - z) < 0.05


# --- Correct extractions pass ---

@pytest.mark.parametrize("effect", [
    {"type": "RR", "effect_size": 0.45, "ci_lower": 0.36, "ci_upper": 0.56, "p_value": 0.0001},
    {"type": "HR", "effect_size": 0.70, "ci_lower": 0.49, "ci_upper": 1.00, "p_value": 0.05},
    {"type": "MD", "effect_size": -7.63, "ci_lower": -11.06, "ci_upper": -4.21, "p_value": 0.0001},
    {"type": "EFFICACY_PCT", "effect_size": 42.7, "ci_lower": 22.5, "ci_upper": 57.7},
    {"type": "IRR", "effect_size": 0.67, "ci_lower": 0.50, "ci_upper": 0.90},
])
def test_good_extractions_consistent(effect):
    c = check_consistency(effect)
    assert c["consistent"] and c["score"] >= 0.6 and not c["flags"]


# --- Error classes are caught ---

def test_point_outside_ci():
    c = check_consistency({"type": "HR", "effect_size": 1.5, "ci_lower": 0.5, "ci_upper": 0.9})
    assert not c["consistent"] and "point_outside_ci" in c["flags"] and c["score"] == 0.0


def test_misread_digit_off_centre():
    # 0.95 cannot be the centre of (0.36, 0.56)
    c = check_consistency({"type": "OR", "effect_size": 0.95, "ci_lower": 0.36, "ci_upper": 0.56})
    assert not c["consistent"]


def test_nonpositive_ratio():
    c = check_consistency({"type": "RR", "effect_size": -0.5, "ci_lower": -1.0, "ci_upper": 0.2})
    assert "nonpositive_ratio" in c["flags"] and c["score"] == 0.0


def test_significance_flip_gross():
    # CI excludes 1 (significant) but p reported as 0.6 (non-significant)
    c = check_consistency({"type": "OR", "effect_size": 0.45, "ci_lower": 0.36,
                           "ci_upper": 0.56, "p_value": 0.6})
    assert "gross_sig_inconsistency" in c["flags"] and c["score"] == 0.0


def test_reversed_ci_repaired():
    c = check_consistency({"type": "RR", "effect_size": 0.70, "ci_lower": 0.90, "ci_upper": 0.49})
    assert c["repair"] == "swapped_ci_bounds" and c["consistent"]


def test_small_p_not_flagged():
    # tiny reported p with strongly-significant CI must NOT be flagged
    c = check_consistency({"type": "RR", "effect_size": 0.45, "ci_lower": 0.36,
                           "ci_upper": 0.56, "p_value": 0.00001})
    assert c["consistent"] and not c["flags"]


# --- annotate(): repair applied, hard failures dropped ---

def test_annotate_drops_hard_and_repairs():
    effects = [
        {"type": "RR", "effect_size": 0.45, "ci_lower": 0.36, "ci_upper": 0.56},   # good
        {"type": "HR", "effect_size": 1.5, "ci_lower": 0.5, "ci_upper": 0.9},      # point outside CI
        {"type": "RR", "effect_size": 0.70, "ci_lower": 0.90, "ci_upper": 0.49},   # reversed CI -> repaired
    ]
    kept = annotate(effects, drop_hard=True)
    assert len(kept) == 2                          # the point-outside-CI one dropped
    repaired = [e for e in kept if e["effect_size"] == 0.70][0]
    assert repaired["ci_lower"] == 0.49 and repaired["ci_upper"] == 0.90
    assert all("consistency" in e for e in kept)
