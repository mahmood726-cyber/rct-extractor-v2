"""
Tests for the internal-consistency layer (src/specialties/internal_consistency.py).

Anchors the Altman-Bland CI<->p formulas and confirms the checks catch the
extraction-error classes they target (misread digit, point outside CI, reversed
CI bounds, significance flip) without flagging correct extractions.
"""
import json
import math
import pytest

from rct_extractor._engine.specialties.internal_consistency import (
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
    # CI excludes 1 (significant) but p reported as 0.6 (non-significant).
    # P0-6: discordant REPORTING -> flagged + needs_review, NOT hard-dropped.
    c = check_consistency({"type": "OR", "effect_size": 0.45, "ci_lower": 0.36,
                           "ci_upper": 0.56, "p_value": 0.6})
    assert "gross_sig_inconsistency" in c["flags"] and 0.0 < c["score"] < 1.0


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


def test_p0_5_rrr_treated_as_percentage():
    # RRR/efficacy 95% with CI 90.3-97.6: null=0 (excluded), consistent
    c = check_consistency({"type": "RRR", "effect_size": 95.0, "ci_lower": 90.3, "ci_upper": 97.6})
    assert c["consistent"] and c["ci_excludes_null"] is True
    # a null efficacy result correctly shows CI includes the null
    c2 = check_consistency({"type": "RRR", "effect_size": 2.0, "ci_lower": -10.0, "ci_upper": 13.0})
    assert c2["ci_excludes_null"] is False


def test_p0_6_sig_discordance_not_dropped():
    # CI includes 1 but p<0.05 (discordant reporting) -> flagged, NOT hard-dropped
    c = check_consistency({"type": "OR", "effect_size": 0.9, "ci_lower": 0.8, "ci_upper": 1.02, "p_value": 0.04})
    assert "gross_sig_inconsistency" in c["flags"] and c["score"] > 0.0
    kept = annotate([{"type": "OR", "effect_size": 0.9, "ci_lower": 0.8, "ci_upper": 1.02, "p_value": 0.04}], drop_hard=True)
    assert len(kept) == 1 and kept[0]["needs_review"]


# --- count-level checks (2x2 cell counts) -----------------------------------

def test_events_exceed_n_is_hard_negated_count_trap():
    # The negated-count trap: an extracted N that is actually a "Not randomised"
    # count, so events (1807) exceed the arm N (500). Hard failure -> dropped.
    c = check_consistency({"type": "RR", "effect_size": 0.8, "ci_lower": 0.6, "ci_upper": 1.0,
                           "events_tx": 1807, "n_tx": 500, "events_ctrl": 40, "n_ctrl": 505})
    assert "events_exceed_n" in c["flags"]
    assert c["score"] == 0.0 and not c["consistent"]


def test_arm_n_nonpositive_and_negative_events_hard():
    c1 = check_consistency({"type": "OR", "effect_size": 1.2, "ci_lower": 0.9, "ci_upper": 1.6,
                            "events_tx": 10, "n_tx": 0, "events_ctrl": 8, "n_ctrl": 100})
    assert "arm_n_nonpositive" in c1["flags"] and c1["score"] == 0.0
    c2 = check_consistency({"type": "OR", "effect_size": 1.2, "ci_lower": 0.9, "ci_upper": 1.6,
                            "events_tx": -3, "n_tx": 100, "events_ctrl": 8, "n_ctrl": 100})
    assert "events_negative" in c2["flags"] and c2["score"] == 0.0


def test_effect_table_mismatch_is_soft_and_consistent_table_passes():
    # RR from counts = (10/100)/(50/100) = 0.2; reported 0.8 disagrees (soft flag).
    c = check_consistency({"type": "RR", "effect_size": 0.8, "ci_lower": 0.5, "ci_upper": 1.2,
                           "events_tx": 10, "n_tx": 100, "events_ctrl": 50, "n_ctrl": 100})
    assert "effect_table_mismatch" in c["flags"] and 0.0 < c["score"] < 1.0   # soft, not dropped
    # reported 0.2 matches the table -> no mismatch
    c2 = check_consistency({"type": "RR", "effect_size": 0.2, "ci_lower": 0.11, "ci_upper": 0.37,
                            "events_tx": 10, "n_tx": 100, "events_ctrl": 50, "n_ctrl": 100})
    assert "effect_table_mismatch" not in c2["flags"]


def test_hr_table_not_recomputed():
    # HR depends on person-time/censoring; a risk-ratio proxy would false-flag it,
    # so HR/IRR are NOT cross-checked against the 2x2.
    c = check_consistency({"type": "HR", "effect_size": 0.80, "ci_lower": 0.70, "ci_upper": 0.92,
                           "events_tx": 10, "n_tx": 100, "events_ctrl": 50, "n_ctrl": 100})
    assert "effect_table_mismatch" not in c["flags"]


def test_counts_absent_raise_no_count_flags():
    c = check_consistency({"type": "RR", "effect_size": 0.45, "ci_lower": 0.36, "ci_upper": 0.56})
    assert not any(f in c["flags"] for f in
                   ("events_exceed_n", "arm_n_nonpositive", "events_negative", "effect_table_mismatch"))


# --- percentage-scale (RRR / efficacy): a consistent % extraction is NOT flagged
# (the "4S" case is a correct extraction vs a proportion-encoded gold value) ----

def test_pct_consistent_percent_scale_passes():
    # the 4S case: RRR 30% with CI 21-38% — internally consistent, NO flag
    c = check_consistency({"type": "RRR", "effect_size": 30.0, "ci_lower": 21.0, "ci_upper": 38.0})
    assert c["consistent"] and not c["flags"]


def test_pct_proportion_scale_mismatch_caught_by_containment():
    # a proportion point against a %-scale CI is already a point-outside-CI error
    c = check_consistency({"type": "RRR", "effect_size": 0.30, "ci_lower": 21.0, "ci_upper": 38.0})
    assert "point_outside_ci" in c["flags"] and not c["consistent"]


# --- gold-set false-positive audit ------------------------------------------

_NAME_TO_ABBR = {
    "RISK RATIO": "RR", "RELATIVE RISK": "RR", "HAZARD RATIO": "HR",
    "ODDS RATIO": "OR", "INCIDENCE RATE RATIO": "IRR", "RATE RATIO": "IRR",
    "MEAN DIFFERENCE": "MD", "STANDARDIZED MEAN DIFFERENCE": "SMD",
    "RISK DIFFERENCE": "RD",
}


def test_gold_set_zero_false_positives():
    """Every gold extraction is correct, so check_consistency must raise NO
    flags on it (the FP-audit that licenses trusting the flags downstream)."""
    from pathlib import Path
    gold = Path(__file__).resolve().parent.parent / "data" / "validation_dataset.jsonl"
    n, bad = 0, []
    for line in gold.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        g = r.get("gold_standard") or {}
        pt, lo, hi = g.get("point_estimate"), g.get("ci_lower"), g.get("ci_upper")
        if pt is None or lo is None or hi is None:
            continue
        etype = _NAME_TO_ABBR.get(str(r.get("effect_type", "")).upper(), r.get("effect_type"))
        n += 1
        c = check_consistency({"type": etype, "effect_size": pt, "ci_lower": lo, "ci_upper": hi})
        if c["flags"]:
            bad.append((r.get("trial_name"), etype, pt, lo, hi, c["flags"]))
    assert n >= 150, f"expected the full gold set, only checked {n}"
    assert not bad, f"{len(bad)} false positive(s) on the gold set: {bad[:5]}"
