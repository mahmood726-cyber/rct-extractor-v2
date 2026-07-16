#!/usr/bin/env python3
"""D13 regression — the arm N declared in the COLUMN HEADER must reach the SE.

THE DEFECT (D13, found 2026-07-16 by the cross-vendor attack; root-caused here):
    jats_table_extractor._from_row_mean_sd_cells passed n1/n2=None UNCONDITIONALLY,
    and neither row parser ever read the column header. For the standard journal
    layout -- "Drug (N=150)" in the header, "12.4 (3.1)" in the cell -- per-arm N was
    therefore *structurally* unavailable and every effect fell through to the
    `no_n` pooled-SD fallback. The per-arm-N branch in _md_effect was DEAD CODE on
    real data: measured 159/159 (100%) `table_arm_means_no_n` across the cached OA
    corpus.

WHY IT MATTERS MORE THAN A RECALL MISS:
    The fallback does not fail loudly. It emits an effect with a type, a value, a CI
    and a NON-None standard_error. Nothing downstream can see that the SE is a proxy.
    On the fixture below it is 8.63x too large, costs ~74x pooled weight, and flips a
    genuinely significant effect to non-significant.

THE FIXTURE IS DERIVED, NOT INVENTED. sd1/sd2/n1/n2 below were recovered by solving
the attack report's own published numbers (SE_no_n=3.2535, SE_correct=0.3771,
8.6x, 74x, CI (-2.18,10.58) vs (3.46,4.94)) and reproduce all five to 3 d.p.

The load-bearing test is TestD13Mutation::test_removing_the_header_read_reintroduces_the_defect:
it drives the PRODUCTION entrypoint and fails if the header read is ever removed.
A test that exercised a side-car copy of this logic would pass while the defect shipped.

Run:  python -m pytest tests/test_jats_table_header_n.py -v
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from rct_extractor._engine.core import jats_table_extractor as J
from rct_extractor._engine.core.jats_table_extractor import (
    extract_continuous_effects_from_xml as ext,
)

SD1, SD2, N1, N2 = 3.1, 3.4, 150, 148
MEAN1, MEAN2 = 12.4, 8.2
MD = MEAN1 - MEAN2                                    # 4.2
SE_GOOD = math.sqrt(SD1**2 / N1 + SD2**2 / N2)        # 0.3771
SE_BAD = math.sqrt((SD1**2 + SD2**2) / 2)             # 3.2535

# The standard journal layout: N declared ONCE, in the arm's column header.
TABLE_HEADER_N = f"""<article><table-wrap><table>
  <thead><tr><th>Outcome</th><th>Drug (N={N1})</th><th>Placebo (N={N2})</th></tr></thead>
  <tbody>
    <tr><td>Change in score</td><td>{MEAN1} ({SD1})</td><td>{MEAN2} ({SD2})</td></tr>
  </tbody>
</table></table-wrap></article>"""

# Same shape, header states no N -- the coarse fallback is then CORRECT behaviour.
TABLE_NO_N = TABLE_HEADER_N.replace(f"Drug (N={N1})", "Drug").replace(f"Placebo (N={N2})", "Placebo")


def _one(xml):
    effs = [e for e in ext(xml) if e["endpoint"] == "Change in score"]
    assert len(effs) == 1, f"expected exactly 1 effect, got {len(effs)}"
    return effs[0]


class TestD13TheFix:
    """The header states the N. Read the header."""

    def test_header_n_reaches_the_arms(self):
        e = _one(TABLE_HEADER_N)
        assert e["arm1_n"] == N1 and e["arm2_n"] == N2

    def test_se_is_computed_from_per_arm_n(self):
        e = _one(TABLE_HEADER_N)
        assert abs(e["standard_error"] - SE_GOOD) < 1e-4

    def test_se_method_records_the_provenance_not_just_existence(self):
        """A consumer must be able to tell a real SE from the fallback proxy."""
        assert _one(TABLE_HEADER_N)["se_method"] == "table_arm_means_header_n"
        assert _one(TABLE_NO_N)["se_method"] == "table_arm_means_no_n"

    def test_the_effect_is_significant_again(self):
        """The defect's headline damage: a real effect silently made non-significant."""
        e = _one(TABLE_HEADER_N)
        assert e["ci_lower"] > 0, "CI must exclude the null"
        assert (round(e["ci_lower"], 2), round(e["ci_upper"], 2)) == (3.46, 4.94)

    def test_arm_n_is_not_swapped(self):
        """A swapped N computes a confident SE from the other arm's denominator --
        the 'worse than no join' failure. Arm 1 is the FIRST data column."""
        e = _one(TABLE_HEADER_N)
        assert e["arm1_mean"] == MEAN1 and e["arm1_n"] == N1
        assert e["arm2_mean"] == MEAN2 and e["arm2_n"] == N2


class TestD13TheDefect:
    """Characterisation: prove the old behaviour really was this wrong."""

    def test_no_n_fallback_still_fires_when_the_header_is_silent(self):
        e = _one(TABLE_NO_N)
        assert e["arm1_n"] is None and e["arm2_n"] is None
        assert abs(e["standard_error"] - SE_BAD) < 1e-4

    def test_the_fallback_is_the_one_that_hides_the_effect(self):
        e = _one(TABLE_NO_N)
        assert e["ci_lower"] < 0 < e["ci_upper"], "the proxy SE crosses the null"

    def test_measured_damage_reproduces(self):
        """8.63x SE inflation, ~74x weight loss -- the attack report's numbers."""
        bad, good = _one(TABLE_NO_N), _one(TABLE_HEADER_N)
        assert round(bad["standard_error"] / good["standard_error"], 1) == 8.6
        assert round((bad["standard_error"] / good["standard_error"]) ** 2) == 74

    def test_a_non_none_se_is_not_evidence_of_a_real_se(self):
        """THE GATE LESSON. Both effects carry a non-None SE. A rescue/coverage gate
        of the form `standard_error is not None` is satisfied BY the defect -- which
        is exactly how 98/98 rung7 rescues rode the broken path."""
        assert _one(TABLE_NO_N)["standard_error"] is not None
        assert _one(TABLE_HEADER_N)["standard_error"] is not None


class TestD13Mutation:
    """THE LOAD-BEARING TEST. It drives the production entrypoint, not a copy.

    A test that imports a side-car reimplementation of the fix passes while the
    production path still ships the defect. This mutates the real module and asserts
    the real entrypoint goes wrong.
    """

    def test_removing_the_header_read_reintroduces_the_defect(self, monkeypatch):
        # Mutation: make the header-N map return nothing, exactly as before the fix.
        monkeypatch.setattr(J, "_header_ns", lambda grid: {})
        e = _one(TABLE_HEADER_N)
        assert e["arm1_n"] is None, "MUTATION DID NOT BITE -- this test is theatre"
        assert e["se_method"] == "table_arm_means_no_n"
        assert abs(e["standard_error"] - SE_BAD) < 1e-4

    def test_breaking_the_header_regex_reintroduces_the_defect(self, monkeypatch):
        """Second mutation, at a different layer: the regex itself."""
        import re
        monkeypatch.setattr(J, "_HDR_N", re.compile(r"(ZZZ_NEVER_MATCHES)(\d)"))
        assert _one(TABLE_HEADER_N)["se_method"] == "table_arm_means_no_n"


class TestD13Safety:
    """N is read, never invented."""

    def test_no_n_is_invented_when_header_is_silent(self):
        assert _one(TABLE_NO_N)["arm1_n"] is None

    def test_implausible_arm_n_is_refused(self):
        """n<2 has no estimable SE; treat as undeclared rather than divide by it."""
        xml = TABLE_HEADER_N.replace(f"Drug (N={N1})", "Drug (N=1)")
        e = _one(xml)
        assert e["arm1_n"] is None
        assert e["se_method"] == "table_arm_means_no_n"

    def test_row_stated_n_still_wins_and_is_labelled_row(self):
        """Layout B states N per row; that must not be relabelled as header-derived."""
        xml = """<article><table-wrap><table>
          <thead><tr><th>Outcome</th><th>n</th><th>Mean</th><th>SD</th>
                     <th>n</th><th>Mean</th><th>SD</th></tr></thead>
          <tbody><tr><td>OMAS</td><td>28</td><td>65.54</td><td>20.2</td>
                     <td>30</td><td>52.10</td><td>15.7</td></tr></tbody>
        </table></table-wrap></article>"""
        e = [x for x in ext(xml) if x["endpoint"] == "OMAS"][0]
        assert (e["arm1_n"], e["arm2_n"]) == (28, 30)
        assert e["se_method"] == "table_arm_means"

    def test_colspan_header_attaches_n_to_the_right_arm(self):
        """A group header spanning sub-columns must not shift the N onto the wrong arm."""
        xml = f"""<article><table-wrap><table>
          <thead>
            <tr><th></th><th colspan="2">Randomised</th></tr>
            <tr><th>Outcome</th><th>Drug (N={N1})</th><th>Placebo (N={N2})</th></tr>
          </thead>
          <tbody><tr><td>Change in score</td><td>{MEAN1} ({SD1})</td>
                     <td>{MEAN2} ({SD2})</td></tr></tbody>
        </table></table-wrap></article>"""
        e = _one(xml)
        assert (e["arm1_n"], e["arm2_n"]) == (N1, N2)
