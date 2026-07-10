#!/usr/bin/env python3
"""Phase-2 primary-selection / direction parity fixes:

  S5 -- malaria path now calls order_effects (primary promoted to effects[0]).
  S6 -- continuous raw-data path gets the T1.5 control-first orientation guard.
  E2E -- order_effects + is_primary + direction validated on real api.extract output
         (the selection path the oracle scorecard cannot observe).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import rct_extractor as rx
from rct_extractor._engine.core.raw_data_extractor import extract_continuous_two_group


# ---------------------------------------------------------------------------
# S6 -- continuous control-first orientation
# ---------------------------------------------------------------------------

class TestS6ContinuousOrientation:
    def _md(self, text):
        rs = extract_continuous_two_group(text)
        assert rs, f"expected a continuous extraction for {text!r}"
        d = rs[0].to_raw_data_dict()
        assert d is not None
        return d

    def test_control_first_not_inverted(self):
        d = self._md("Placebo 58.5 (18.6), n=20 versus Drug 45.3 (19.9), n=22")
        assert abs(d["intervention_mean"] - 45.3) < 1e-6
        assert abs(d["control_mean"] - 58.5) < 1e-6

    def test_intervention_first_unchanged(self):
        d = self._md("Drug 45.3 (19.9), n=22 versus placebo 58.5 (18.6), n=20")
        assert abs(d["intervention_mean"] - 45.3) < 1e-6
        assert abs(d["control_mean"] - 58.5) < 1e-6

    def test_no_control_marker_preserves_positional(self):
        # No control keyword -> keep positional order (first mentioned = arm1).
        d = self._md("Group A 45.3 (19.9), n=22 versus Group B 58.5 (18.6), n=20")
        assert abs(d["intervention_mean"] - 45.3) < 1e-6


# ---------------------------------------------------------------------------
# E2E -- real api.extract selection path (order_effects + is_primary + direction)
# ---------------------------------------------------------------------------

class TestEndToEndSelection:
    def test_primary_label_wins_effects_zero(self):
        text = (
            "The secondary endpoint was an odds ratio 1.50 (95% CI 1.10-2.05). "
            "The primary outcome was mortality, hazard ratio 0.70 (95% CI 0.55-0.89)."
        )
        r = rx.extract(text, specialty="cardiology")
        assert r["effects"], "expected effects"
        prim = r["effects"][0]
        assert prim["is_primary"] is True
        # the explicitly-primary HR 0.70 must win effects[0] over the earlier OR 1.50
        assert prim["type"] == "HR" and abs(prim["effect_size"] - 0.70) < 1e-6
        assert prim["direction"] == "decrease"
        # exactly one primary
        assert sum(1 for e in r["effects"] if e.get("is_primary")) == 1

    def test_malaria_path_orders_primary_first(self):
        # S5: malaria abstract, primary labelled after a secondary ratio. With
        # order_effects now wired into the malaria path, the primary wins effects[0].
        text = (
            "Secondary analysis showed a risk ratio 1.30 (95% CI 1.05-1.60) for adverse events. "
            "The primary outcome, clinical malaria, had a risk ratio 0.55 (95% CI 0.42-0.72)."
        )
        r = rx.extract(text, specialty="malaria")
        assert r["effects"], "expected malaria effects"
        prim = r["effects"][0]
        assert prim["is_primary"] is True
        assert abs(prim["effect_size"] - 0.55) < 1e-6
        assert prim["direction"] == "decrease"
