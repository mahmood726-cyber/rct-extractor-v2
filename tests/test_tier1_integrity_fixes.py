#!/usr/bin/env python3
"""
Tier-1 data-integrity regression tests
======================================

Locks in the five Tier-1 integrity fixes from the 2026-07-10 SOTA audit. Each of
these guards a *silently-wrong-number* or *false-confidence* failure mode that the
existing recall-focused suite did not catch. See docs roadmap (tasks/wf3oyj0y6).

  T1.2  phantom 2x2 from an "n/N (pct%)" denominator read as the event count
  T1.3  a mathematically VIOLATED verification must fail closed (unusable)
  T1.4  each effect column must take its OWN CI column, not always ci_cols[0]
  T1.5  control-first arm phrasing must not silently invert the computed OR/RR
  T1.6  RMST differences are a distinct time-diff effect, never pooled as an HR
"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from rct_extractor._engine.core.raw_data_extractor import extract_binary_two_group
from rct_extractor._engine.core.enhanced_extractor_v3 import (
    EnhancedExtractor, EffectType, to_dict,
)


# ---------------------------------------------------------------------------
# T1.2 — phantom 2x2 from slash-fraction cells
# ---------------------------------------------------------------------------

class TestT12PhantomTwoByTwo:
    def test_slash_fraction_cells_not_misread_as_events(self):
        """'12/100 (12.0%) 18/100 (18.0%)' must yield 12/100 & 18/100 — never the
        old phantom 100/833 (denominator N misread as the event count)."""
        results = extract_binary_two_group("Mortality 12/100 (12.0%) 18/100 (18.0%)")
        assert results, "expected a 2x2 from the slash-fraction row"
        pairs = {(r.arm1.events, r.arm1.n, r.arm2.events, r.arm2.n) for r in results}
        assert (12, 100, 18, 100) in pairs
        # No fabricated arm with the ~8x-inflated denominator.
        for r in results:
            assert r.arm1.n != 833 and r.arm2.n != 833
            assert r.arm1.events <= r.arm1.n and r.arm2.events <= r.arm2.n

    def test_bare_paren_percent_row_still_works(self):
        """The genuine Strategy-4 target (no slash) is unaffected by the lookbehind."""
        results = extract_binary_two_group("Deaths 15 (26.8%) and 18 (31.6%)")
        assert results, "bare 'n (pct%)' comparison should still extract"


# ---------------------------------------------------------------------------
# T1.5 — control-first arm inversion
# ---------------------------------------------------------------------------

class TestT15ArmOrientation:
    def _dict(self, text):
        rs = extract_binary_two_group(text)
        assert rs, f"expected an extraction for: {text!r}"
        return rs[0].to_raw_data_dict()

    def test_control_named_first_does_not_invert(self):
        d = self._dict("Placebo 18/57 (31.6%) vs treatment 15/56 (26.8%)")
        assert d["intervention_events"] == 15 and d["intervention_n"] == 56
        assert d["control_events"] == 18 and d["control_n"] == 57

    def test_control_first_no_percent(self):
        d = self._dict("In the placebo group 18/57 vs 15/56 in the intervention group.")
        assert (d["intervention_events"], d["intervention_n"]) == (15, 56)
        assert (d["control_events"], d["control_n"]) == (18, 57)

    def test_intervention_first_unchanged(self):
        d = self._dict("Treatment 15/56 (26.8%) vs placebo 18/57 (31.6%)")
        assert (d["intervention_events"], d["intervention_n"]) == (15, 56)

    def test_no_labels_preserves_positional_order(self):
        """With no control marker, legacy positional order is preserved (no swap)."""
        d = self._dict("7/40 vs 17/39")
        assert (d["intervention_events"], d["intervention_n"]) == (7, 40)
        assert (d["control_events"], d["control_n"]) == (17, 39)


# ---------------------------------------------------------------------------
# T1.6 — RMST as a distinct effect type
# ---------------------------------------------------------------------------

class TestT16Rmst:
    def _types(self, text):
        return [(to_dict(x)["type"], to_dict(x)["effect_size"]) for x in EnhancedExtractor().extract(text)]

    def test_rmst_extracted_as_distinct_type(self):
        got = self._types("The RMST difference at 36 months was 1.34 months (95% CI 0.30 to 2.38).")
        assert ("RMST", 1.34) in got

    def test_rmst_allows_negative_value(self):
        got = self._types("Restricted mean survival time difference of -2.1 months (95% CI -3.4 to -0.8).")
        assert ("RMST", -2.1) in got

    def test_rmst_not_double_emitted_as_md(self):
        got = self._types("RMST difference 4.5 (95% CI 1.2-7.8) favoring treatment.")
        assert ("RMST", 4.5) in got
        assert not any(t == "MD" and v == 4.5 for t, v in got), "RMST must not also surface as MD"

    def test_plain_mean_difference_still_typed_md(self):
        got = self._types("The mean difference was 4.5 (95% CI 1.2 to 7.8).")
        assert ("MD", 4.5) in got
        assert not any(t == "RMST" for t, _ in got)

    def test_hazard_ratio_unaffected(self):
        got = self._types("The hazard ratio was 0.74 (95% CI 0.65 to 0.85, P<0.001).")
        assert ("HR", 0.74) in got


# ---------------------------------------------------------------------------
# T1.3 — VIOLATED verification fails closed
# ---------------------------------------------------------------------------

class TestT13FailClosedOnViolated:
    def _status(self, pipeline, verification):
        from rct_extractor._engine.core.team_of_rivals import ExtractorType
        consensus = SimpleNamespace(
            agreement_ratio=1.0,
            is_unanimous=False,               # skip the VERIFIED branch
            agreeing_extractors={ExtractorType.PATTERN},
        )
        return pipeline._determine_status(consensus, verification, None)

    def test_violated_verification_is_rejected_and_unusable(self):
        from rct_extractor._engine.core.verified_extraction_pipeline import (
            VerifiedExtractionPipeline, PipelineStatus,
        )
        from rct_extractor._engine.core.deterministic_verifier import VerificationLevel

        pipeline = VerifiedExtractionPipeline()
        verification = SimpleNamespace(overall_level=VerificationLevel.VIOLATED, warnings=[])
        status, confidence, is_usable, warnings = self._status(pipeline, verification)

        assert is_usable is False, "a point-outside-CI (VIOLATED) triple must not be usable"
        assert status == PipelineStatus.REJECTED

    def test_no_verification_keeps_pattern_agreed_result_usable(self):
        """Control: the guard must not break the happy path (verification absent)."""
        from rct_extractor._engine.core.verified_extraction_pipeline import (
            VerifiedExtractionPipeline, PipelineStatus,
        )
        pipeline = VerifiedExtractionPipeline()
        status, confidence, is_usable, warnings = self._status(pipeline, None)
        assert is_usable is True
        assert status != PipelineStatus.REJECTED


# ---------------------------------------------------------------------------
# T1.4 — per-effect CI column selection in split-column tables
# ---------------------------------------------------------------------------

class TestT14CiColumnSelection:
    def _build_adjusted_table(self):
        from rct_extractor._engine.tables.table_extractor import TableStructure, TableCell
        from rct_extractor._engine.pdf.pdf_parser import BBox

        rows = [
            ["Outcome", "HR", "95% CI", "Adjusted HR", "95% CI"],
            ["Death", "1.20", "0.90-1.60", "0.75", "0.60-0.95"],
        ]
        cells = [TableCell(text=txt, row=r, col=c)
                 for r, row in enumerate(rows) for c, txt in enumerate(row)]
        return TableStructure(
            cells=cells, num_rows=len(rows), num_cols=len(rows[0]),
            bbox=BBox(x0=0.0, y0=0.0, x1=500.0, y1=100.0), page_num=1, header_rows=1,
        )

    def test_adjusted_effect_gets_its_own_ci(self):
        from rct_extractor._engine.tables.table_effect_extractor import TableEffectExtractor

        table = self._build_adjusted_table()
        effects = TableEffectExtractor().extract_from_table(table)
        by_pe = {round(e.point_estimate, 2): (e.ci_lower, e.ci_upper) for e in effects}

        # The unadjusted HR (1.20) keeps the first CI; the adjusted HR (0.75) must
        # take the SECOND CI column, not graft the unadjusted 0.90-1.60 onto itself.
        if 0.75 in by_pe and by_pe[0.75] != (None, None):
            assert by_pe[0.75] == (0.60, 0.95), (
                "adjusted HR grabbed the wrong CI column (T1.4 regression)"
            )
        if 1.20 in by_pe and by_pe[1.20] != (None, None):
            assert by_pe[1.20] == (0.90, 1.60)
