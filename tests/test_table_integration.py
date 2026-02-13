#!/usr/bin/env python3
"""
Tests for Table Effect Extraction Integration
===============================================

Verifies that:
1. TableEffectExtractor correctly extracts effects from table structures
2. Deduplication between text and table effects works correctly
3. CI merging from tables fills gaps in text extractions
4. Table-only effects are properly converted to Extraction objects
5. Graceful degradation when pdfplumber unavailable
"""

import sys
from pathlib import Path
from collections import namedtuple
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from src.core.pdf_extraction_pipeline import PDFExtractionPipeline
from src.core.enhanced_extractor_v3 import (
    EnhancedExtractor, Extraction, EffectType, ConfidenceInterval, AutomationTier
)
from src.tables.table_effect_extractor import TableEffectExtractor, TableEffect


# =============================================================================
# Helpers
# =============================================================================

def make_text_extraction(
    effect_type: EffectType,
    value: float,
    ci_lower=None,
    ci_upper=None,
    source_text=""
) -> Extraction:
    """Create a mock Extraction from text."""
    ci = None
    has_ci = False
    if ci_lower is not None and ci_upper is not None:
        ci = ConfidenceInterval(lower=ci_lower, upper=ci_upper)
        has_ci = True
    return Extraction(
        effect_type=effect_type,
        point_estimate=value,
        ci=ci,
        source_text=source_text or f"{effect_type.value} {value}",
        has_complete_ci=has_ci,
        raw_confidence=0.9,
        calibrated_confidence=0.85,
        automation_tier=AutomationTier.SPOT_CHECK,
    )


def make_table_effect(
    effect_type: str,
    value: float,
    ci_lower=None,
    ci_upper=None,
    outcome=""
) -> TableEffect:
    """Create a mock TableEffect."""
    return TableEffect(
        effect_type=effect_type,
        point_estimate=value,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        outcome_name=outcome,
        source_cells=[f"{value}"],
        confidence=0.85,
    )


# =============================================================================
# Tests
# =============================================================================

class TestTableEffectToExtraction:
    """Test converting TableEffect to Extraction."""

    def setup_method(self):
        self.pipeline = PDFExtractionPipeline(extract_diagnostics=False)

    def test_converts_hr(self):
        te = make_table_effect("HR", 0.74, 0.65, 0.85, "CV death")
        ext = self.pipeline._table_effect_to_extraction(te)
        assert ext is not None
        assert ext.effect_type == EffectType.HR
        assert ext.point_estimate == 0.74
        assert ext.has_complete_ci is True
        assert ext.ci.lower == 0.65
        assert ext.ci.upper == 0.85

    def test_converts_or(self):
        te = make_table_effect("OR", 1.50, 1.10, 2.05, "Response")
        ext = self.pipeline._table_effect_to_extraction(te)
        assert ext is not None
        assert ext.effect_type == EffectType.OR
        assert ext.point_estimate == 1.50

    def test_converts_md(self):
        te = make_table_effect("MD", -2.3, -3.1, -1.5, "HbA1c change")
        ext = self.pipeline._table_effect_to_extraction(te)
        assert ext is not None
        assert ext.effect_type == EffectType.MD
        assert ext.point_estimate == -2.3

    def test_converts_without_ci(self):
        te = make_table_effect("HR", 0.82)
        ext = self.pipeline._table_effect_to_extraction(te)
        assert ext is not None
        assert ext.has_complete_ci is False
        assert ext.ci is None

    def test_unknown_type_returns_none(self):
        te = make_table_effect("UNKNOWN", 1.0)
        ext = self.pipeline._table_effect_to_extraction(te)
        assert ext is None

    def test_table_warning_added(self):
        te = make_table_effect("HR", 0.74, 0.65, 0.85)
        ext = self.pipeline._table_effect_to_extraction(te)
        assert any("table" in w.lower() for w in ext.warnings)

    def test_automation_tier_is_verify(self):
        te = make_table_effect("HR", 0.74, 0.65, 0.85)
        ext = self.pipeline._table_effect_to_extraction(te)
        assert ext.automation_tier == AutomationTier.VERIFY


class TestDeduplication:
    """Test merging text and table extractions."""

    def setup_method(self):
        self.pipeline = PDFExtractionPipeline(extract_diagnostics=False)

    def test_text_with_ci_kept_over_table(self):
        """When text has CI, don't overwrite with table CI."""
        text_effects = [make_text_extraction(EffectType.HR, 0.74, 0.65, 0.85)]
        table_effects = [make_table_effect("HR", 0.74, 0.60, 0.90)]

        merged = self.pipeline._merge_text_and_table_effects(text_effects, table_effects)
        assert len(merged) == 1
        assert merged[0].ci.lower == 0.65  # Original text CI preserved
        assert merged[0].ci.upper == 0.85

    def test_table_ci_fills_missing_text_ci(self):
        """When text lacks CI but table has it, merge CI from table."""
        text_effects = [make_text_extraction(EffectType.HR, 0.74)]  # No CI
        table_effects = [make_table_effect("HR", 0.74, 0.65, 0.85)]

        merged = self.pipeline._merge_text_and_table_effects(text_effects, table_effects)
        assert len(merged) == 1
        assert merged[0].has_complete_ci is True
        assert merged[0].ci.lower == 0.65
        assert merged[0].ci.upper == 0.85
        assert any("CI merged" in w for w in merged[0].warnings)

    def test_table_only_effect_added(self):
        """Table effect with no text match is added as new extraction."""
        text_effects = [make_text_extraction(EffectType.HR, 0.74, 0.65, 0.85)]
        table_effects = [make_table_effect("OR", 1.50, 1.10, 2.05)]

        merged = self.pipeline._merge_text_and_table_effects(text_effects, table_effects)
        assert len(merged) == 2
        types = {e.effect_type.value for e in merged}
        assert "HR" in types
        assert "OR" in types

    def test_no_table_effects_returns_text_unchanged(self):
        text_effects = [make_text_extraction(EffectType.HR, 0.74, 0.65, 0.85)]
        merged = self.pipeline._merge_text_and_table_effects(text_effects, [])
        assert len(merged) == 1
        assert merged[0].point_estimate == 0.74

    def test_no_text_effects_converts_all_table(self):
        table_effects = [
            make_table_effect("HR", 0.74, 0.65, 0.85),
            make_table_effect("OR", 1.50, 1.10, 2.05),
        ]
        merged = self.pipeline._merge_text_and_table_effects([], table_effects)
        assert len(merged) == 2

    def test_matching_uses_tolerance(self):
        """Values within 1% should match for ratio types."""
        text_effects = [make_text_extraction(EffectType.HR, 0.74)]
        table_effects = [make_table_effect("HR", 0.7401, 0.65, 0.85)]

        merged = self.pipeline._merge_text_and_table_effects(text_effects, table_effects)
        assert len(merged) == 1  # Should merge, not create new
        assert merged[0].has_complete_ci is True

    def test_different_values_not_merged(self):
        """Values beyond tolerance should not match."""
        text_effects = [make_text_extraction(EffectType.HR, 0.74)]
        table_effects = [make_table_effect("HR", 0.95, 0.85, 1.05)]

        merged = self.pipeline._merge_text_and_table_effects(text_effects, table_effects)
        assert len(merged) == 2  # Both kept as separate

    def test_md_tolerance_is_absolute(self):
        """MD uses absolute tolerance (0.5)."""
        text_effects = [make_text_extraction(EffectType.MD, -2.3)]
        table_effects = [make_table_effect("MD", -2.31, -3.1, -1.5)]

        merged = self.pipeline._merge_text_and_table_effects(text_effects, table_effects)
        assert len(merged) == 1
        assert merged[0].has_complete_ci is True

    def test_multiple_table_effects_matched(self):
        """Multiple table effects matched to corresponding text effects."""
        text_effects = [
            make_text_extraction(EffectType.HR, 0.74),
            make_text_extraction(EffectType.HR, 0.82),
        ]
        table_effects = [
            make_table_effect("HR", 0.74, 0.65, 0.85),
            make_table_effect("HR", 0.82, 0.70, 0.96),
        ]

        merged = self.pipeline._merge_text_and_table_effects(text_effects, table_effects)
        assert len(merged) == 2
        for m in merged:
            assert m.has_complete_ci is True


class TestTableEffectExtractorDirect:
    """Test the TableEffectExtractor with mock TableStructure."""

    def setup_method(self):
        self.extractor = TableEffectExtractor()

    def test_extract_from_cell_value_with_ci(self):
        result = self.extractor._extract_effect_from_cell("0.74 (0.65-0.85)", "HR")
        assert result is not None
        value, ci_lower, ci_upper = result
        assert abs(value - 0.74) < 0.001
        assert abs(ci_lower - 0.65) < 0.001
        assert abs(ci_upper - 0.85) < 0.001

    def test_extract_from_cell_value_with_comma_ci(self):
        result = self.extractor._extract_effect_from_cell("1.50 (1.10, 2.05)", "OR")
        assert result is not None
        assert abs(result[0] - 1.50) < 0.001

    def test_extract_from_cell_value_with_to_ci(self):
        result = self.extractor._extract_effect_from_cell("0.86 (0.74 to 0.99)", "HR")
        assert result is not None
        assert abs(result[0] - 0.86) < 0.001

    def test_extract_from_cell_value_only(self):
        result = self.extractor._extract_effect_from_cell("0.82", "HR")
        assert result is not None
        assert result[1] is None  # No CI

    def test_extract_ci_from_cell_dash(self):
        result = self.extractor._extract_ci_from_cell("0.65-0.85")
        assert result is not None
        assert abs(result[0] - 0.65) < 0.001
        assert abs(result[1] - 0.85) < 0.001

    def test_extract_ci_from_cell_to(self):
        result = self.extractor._extract_ci_from_cell("0.65 to 0.85")
        assert result is not None

    def test_extract_pvalue(self):
        assert self.extractor._extract_pvalue("<0.001") == 0.001
        assert self.extractor._extract_pvalue("0.023") == 0.023
        assert self.extractor._extract_pvalue("P = 0.04") == 0.04

    def test_extract_pvalue_invalid(self):
        assert self.extractor._extract_pvalue("N/A") is None
        assert self.extractor._extract_pvalue("") is None


class TestGracefulDegradation:
    """Test that table extraction fails gracefully."""

    def test_pipeline_works_without_tables(self):
        """Pipeline should work even if table extraction is disabled."""
        pipeline = PDFExtractionPipeline(
            extract_diagnostics=False,
            extract_tables=False,
        )
        # Use text that's long enough for the text preprocessor
        text = (
            "Background: This randomized trial evaluated the efficacy of Drug X.\n"
            "Methods: Patients were randomly assigned to treatment or placebo.\n"
            "Results: The primary outcome showed a hazard ratio of 0.74 "
            "(95% CI, 0.65 to 0.85; P<0.001) for the composite endpoint.\n"
            "The odds ratio for hospitalization was 0.65 (95% CI, 0.50 to 0.85).\n"
        )
        result = pipeline.extract_from_text(text)
        assert result.table_effects_raw == 0
        # Classification should still work
        assert result.classification is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
