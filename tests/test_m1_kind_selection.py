#!/usr/bin/env python3
"""M1: kind-aware primary selection. When the paper's PRIMARY outcome is clearly a
continuous measure but the top-ranked effect is a ratio, promote the best
difference-type effect (incl. a table-recovered MD) to primary. Measured on the
real efetch/EPMC eval to lift top-1 9.3%->11.6% and direction 41.7%->47.1%."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import rct_extractor as rx
from rct_extractor.api import _infer_primary_kind


class TestInferPrimaryKind:
    def test_continuous_primary(self):
        assert _infer_primary_kind(
            "The primary outcome was the mean change in the pain score from baseline. "
            "The primary endpoint mean difference in score was assessed.") == "diff"

    def test_ratio_primary(self):
        assert _infer_primary_kind(
            "The primary outcome was all-cause mortality (hazard ratio). "
            "The primary endpoint was death; survival and the risk ratio were reported.") == "ratio"

    def test_ambiguous_returns_none(self):
        assert _infer_primary_kind("We enrolled patients and measured things.") is None


class TestM1Promotion:
    def test_table_md_promoted_when_continuous_primary(self):
        # prose has only a ratio; a continuous-primary is indicated; a table MD exists.
        text = ("The primary outcome was the mean change in symptom score from baseline. "
                "The primary endpoint mean difference in the symptom score, a change from "
                "baseline on the questionnaire scale, was the key measure. "
                "A secondary odds ratio 1.50 (95% CI 1.1-2.0) was noted for a binary event.")
        tbl = ("<article><table-wrap><table>"
               "<tr><th>Outcome</th><th>Drug</th><th>Placebo</th></tr>"
               "<tr><td>Symptom score change</td><td>-7.0 (4.1)</td><td>-5.0 (4.4)</td></tr>"
               "</table></table-wrap></article>")
        r = rx.extract(text, specialty="cardiology", tables_xml=tbl)
        prim = r["effects"][0]
        assert prim["type"] == "MD" and prim["is_primary"] is True
        assert abs(prim["effect_size"] - (-2.0)) < 1e-6      # -7 - (-5)

    def test_ratio_primary_not_disturbed(self):
        # a clear ratio primary must stay primary (M1 must not misfire).
        text = ("The primary outcome was all-cause mortality, hazard ratio 0.70 "
                "(95% CI 0.55-0.89). A secondary mean difference -2.0 was seen.")
        r = rx.extract(text, specialty="cardiology")
        assert r["effects"][0]["type"] == "HR" and r["effects"][0]["is_primary"] is True
