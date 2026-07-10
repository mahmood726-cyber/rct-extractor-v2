#!/usr/bin/env python3
"""Tests for the primary-outcome + arm-direction lever (audit gap 35):

  * rct_extractor.api.effect_direction -- deterministic side-of-null.
  * rx.extract emits `direction` + `is_primary` on every effect.
  * scripts/score_primary_direction -- top-1 / direction scoring vs the Cochrane
    reference, incl. measure-mismatch and null-band handling.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pytest

import rct_extractor as rx
from rct_extractor.api import effect_direction
import score_primary_direction as spd


# ---------------------------------------------------------------------------
# effect_direction (the emitted field)
# ---------------------------------------------------------------------------

class TestEffectDirection:
    @pytest.mark.parametrize("etype,val,expected", [
        ("HR", 0.74, "decrease"), ("HR", 1.30, "increase"), ("OR", 1.0, "null"),
        ("RR", 0.5, "decrease"), ("IRR", 2.0, "increase"), ("GMR", 0.9, "decrease"),
        ("MD", -2.1, "decrease"), ("MD", 3.4, "increase"), ("SMD", 0.0, "null"),
        ("RMST", 4.5, "increase"), ("ARD", -0.05, "decrease"),
        ("NNT", 5, None), ("NNH", 8, None), ("RRR", 30, None),
        ("HR", None, None), (None, 0.7, None),
    ])
    def test_direction(self, etype, val, expected):
        assert effect_direction(etype, val) == expected


# ---------------------------------------------------------------------------
# rx.extract emission
# ---------------------------------------------------------------------------

class TestExtractEmitsFields:
    def test_direction_and_primary_present(self):
        r = rx.extract(
            "Primary outcome: hazard ratio 0.62 (95% CI 0.45-0.85). "
            "Secondary: mean difference -0.5 (95% CI -0.7 to -0.3).",
            specialty="diabetes",
        )
        assert r["effects"], "expected at least one effect"
        for e in r["effects"]:
            assert "direction" in e and "is_primary" in e
        # exactly one primary, and it is the first effect
        primaries = [i for i, e in enumerate(r["effects"]) if e["is_primary"]]
        assert primaries == [0]
        # direction agrees with the emitted value
        for e in r["effects"]:
            assert e["direction"] == effect_direction(e["type"], e["effect_size"])


# ---------------------------------------------------------------------------
# scorer
# ---------------------------------------------------------------------------

def _rec(study_id, coch, ext_type, ext_val):
    best = {} if ext_val is None else {"type": ext_type, "effect_size": ext_val}
    return {"study_id": study_id, "cochrane_effect": coch, "best_match": best}


class TestScorer:
    def test_agree_but_value_far(self):
        # both < 1 (agree on direction) but 0.9 vs 0.5 is well outside the 25% band.
        s = spd.score_record(_rec("A", 0.50, "RR", 0.90), {"A": "binary"})
        assert s["direction"] == "agree" and s["selection"] == "value_mismatch"

    def test_value_match_and_agree(self):
        s = spd.score_record(_rec("A", 0.90, "RR", 0.92), {"A": "binary"})
        assert s["direction"] == "agree" and s["selection"] == "value_match"

    def test_sign_flip_ratio(self):
        s = spd.score_record(_rec("B", 0.50, "RR", 1.50), {"B": "binary"})
        assert s["direction"] == "sign_flip"

    def test_measure_mismatch(self):
        # Cochrane primary is a continuous MD; extractor picked an OR (wrong kind).
        s = spd.score_record(_rec("C", -2.0, "OR", 1.5), {"C": "continuous"})
        assert s["direction"] == "measure_mismatch" and s["selection"] == "measure_mismatch"

    def test_negative_binary_value_inferred_as_diff(self):
        # outcome_type says 'binary' but value is negative -> must be a difference.
        s = spd.score_record(_rec("D", -3.0, "MD", -2.5), {"D": "binary"})
        assert s["cochrane_kind"] == "diff" and s["direction"] == "agree"

    def test_null_band_ratio(self):
        # Cochrane 1.03 is within +-5% of the null -> not a confident direction.
        s = spd.score_record(_rec("E", 1.03, "RR", 0.60), {"E": "binary"})
        assert s["direction"] == "null_boundary"

    def test_no_extraction(self):
        s = spd.score_record(_rec("F", 0.8, "RR", None), {"F": "binary"})
        assert s["selection"] == "no_extraction" and s["direction"] == "undetermined"

    def test_summarize_rates(self):
        scored = [
            spd.score_record(_rec("a", 0.5, "RR", 0.55), {"a": "binary"}),   # agree, value_match
            spd.score_record(_rec("b", 0.5, "RR", 1.5), {"b": "binary"}),    # sign_flip
            spd.score_record(_rec("c", -2.0, "OR", 1.5), {"c": "continuous"}),  # measure_mismatch
            spd.score_record(_rec("d", 0.8, "RR", None), {"d": "binary"}),   # no_extraction
        ]
        summ = spd.summarize(scored)
        assert summ["n_studies"] == 4
        assert summ["direction_determinable"] == 2          # agree + sign_flip
        assert summ["direction_accuracy"] == pytest.approx(0.5)
        assert summ["sign_flip_rate"] == pytest.approx(0.5)
        assert summ["selection"]["measure_mismatch"] == 1
