#!/usr/bin/env python3
"""
Tests for Primary Outcome Detector
====================================

Verifies that:
1. Primary outcome scoring produces expected rankings
2. Abstract effects get higher scores
3. "Primary endpoint" label boosts score
4. Secondary/exploratory labels reduce score
5. First effect in results section gets bonus
6. Ties result in no primary marking
7. Integration with pipeline works
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from src.core.primary_outcome_detector import PrimaryOutcomeDetector
from src.core.enhanced_extractor_v3 import (
    Extraction, EffectType, ConfidenceInterval, AutomationTier
)
from src.core.pdf_extraction_pipeline import PDFExtractionPipeline


def make_extraction(
    effect_type: EffectType,
    value: float,
    char_start: int = 0,
    p_value=None,
    has_ci=True,
    source_text=""
) -> Extraction:
    """Create a test Extraction."""
    ci = ConfidenceInterval(lower=value * 0.8, upper=value * 1.2) if has_ci else None
    return Extraction(
        effect_type=effect_type,
        point_estimate=value,
        ci=ci,
        p_value=p_value,
        char_start=char_start,
        source_text=source_text or f"{effect_type.value} {value}",
        has_complete_ci=has_ci,
        raw_confidence=0.9,
        calibrated_confidence=0.85,
        automation_tier=AutomationTier.SPOT_CHECK,
    )


class TestPrimaryOutcomeDetector:
    """Test the detector directly."""

    def setup_method(self):
        self.detector = PrimaryOutcomeDetector()

    def test_abstract_effect_scores_higher(self):
        """Effect in abstract should score higher than one in discussion."""
        text = (
            "Abstract: The primary outcome showed HR 0.74.\n\n"
            "Introduction\n"
            "This study evaluated...\n\n"
            "Results\n"
            "The secondary endpoint showed OR 1.50.\n"
        )
        ext1 = make_extraction(EffectType.HR, 0.74, char_start=30, p_value=0.001)
        ext2 = make_extraction(EffectType.OR, 1.50, char_start=120)

        self.detector.score_extractions([ext1, ext2], text)
        assert ext1.primary_score > ext2.primary_score
        assert ext1.is_primary is True
        assert ext2.is_primary is False

    def test_primary_label_boosts_score(self):
        """Nearby 'primary endpoint' label should boost score."""
        text = (
            "Introduction\nThis study...\n\n"
            "Results\n"
            "The primary endpoint showed HR 0.74 (95% CI 0.65-0.85, P<0.001).\n"
            "A secondary outcome was OR 1.50 (95% CI 1.10-2.05).\n"
        )
        # Position ext1 after "primary endpoint" context
        primary_pos = text.index("HR 0.74")
        secondary_pos = text.index("OR 1.50")

        ext1 = make_extraction(EffectType.HR, 0.74, char_start=primary_pos, p_value=0.001)
        ext2 = make_extraction(EffectType.OR, 1.50, char_start=secondary_pos)

        self.detector.score_extractions([ext1, ext2], text)
        assert ext1.primary_score > ext2.primary_score
        assert ext1.is_primary is True

    def test_secondary_label_reduces_score(self):
        """Secondary/exploratory context should reduce score."""
        text = (
            "Results\n"
            "Main finding: HR 0.74.\n"
            "Exploratory analysis: OR 1.50.\n"
        )
        results_pos = text.index("HR 0.74")
        exploratory_pos = text.index("OR 1.50")

        ext1 = make_extraction(EffectType.HR, 0.74, char_start=results_pos, p_value=0.01)
        ext2 = make_extraction(EffectType.OR, 1.50, char_start=exploratory_pos)

        self.detector.score_extractions([ext1, ext2], text)
        assert ext1.primary_score > ext2.primary_score

    def test_first_in_results_gets_bonus(self):
        """First effect after 'Results' heading should get bonus."""
        text = (
            "Methods\nStudy design...\n\n"
            "Results\n"
            "First HR 0.74 (CI 0.65-0.85; P=0.001).\n"
            "Second OR 1.50 (CI 1.10-2.05).\n"
        )
        results_pos = text.index("Results\n") + len("Results\n")
        first_pos = text.index("HR 0.74")
        second_pos = text.index("OR 1.50")

        ext1 = make_extraction(EffectType.HR, 0.74, char_start=first_pos, p_value=0.001)
        ext2 = make_extraction(EffectType.OR, 1.50, char_start=second_pos)

        self.detector.score_extractions([ext1, ext2], text)
        assert ext1.primary_score > ext2.primary_score

    def test_p_value_adds_score(self):
        """Having a p-value should add to score."""
        text = "Results\nHR 0.74 (P<0.001).\nOR 1.50.\n"

        ext1 = make_extraction(EffectType.HR, 0.74, char_start=10, p_value=0.001)
        ext2 = make_extraction(EffectType.OR, 1.50, char_start=30)

        self.detector.score_extractions([ext1, ext2], text)
        # ext1 has p-value, ext2 doesn't
        assert ext1.primary_score > ext2.primary_score

    def test_ties_resolved_by_position(self):
        """Equal scores should be resolved by earliest char_start (v5.2)."""
        text = "Results\nHR 0.74.\nOR 0.74.\n"

        ext1 = make_extraction(EffectType.HR, 0.74, char_start=10)
        ext2 = make_extraction(EffectType.OR, 0.74, char_start=20)

        self.detector.score_extractions([ext1, ext2], text)
        if ext1.primary_score == ext2.primary_score:
            # v5.2: earliest position wins the tiebreak
            assert ext1.is_primary is True
            assert ext2.is_primary is False

    def test_single_extraction_is_primary(self):
        """Single extraction should be marked primary if it has any score."""
        text = "Results\nThe primary outcome: HR 0.74 (P<0.001).\n"
        ext = make_extraction(EffectType.HR, 0.74, char_start=10, p_value=0.001)

        self.detector.score_extractions([ext], text)
        assert ext.is_primary is True
        assert ext.primary_score > 0

    def test_empty_extractions(self):
        """Empty list should not error."""
        result = self.detector.score_extractions([], "some text")
        assert result == []

    def test_table_primary_label(self):
        """Table-sourced extraction with 'Primary' in source_text."""
        text = "Results\nSee Table 2.\n"
        ext1 = make_extraction(
            EffectType.HR, 0.74, char_start=10,
            source_text="[table] Primary composite: 0.74"
        )
        ext2 = make_extraction(
            EffectType.OR, 1.50, char_start=20,
            source_text="[table] Safety endpoint: 1.50"
        )

        self.detector.score_extractions([ext1, ext2], text)
        assert ext1.primary_score > ext2.primary_score


class TestPrimaryOutcomeIntegration:
    """Test integration with the pipeline."""

    def setup_method(self):
        self.pipeline = PDFExtractionPipeline(extract_diagnostics=False)

    def test_primary_fields_set_on_extraction(self):
        """Extraction results should have primary fields populated."""
        text = (
            "Background: Randomized trial of Drug X. NCT01234567.\n"
            "Methods: Double-blind, placebo-controlled.\n\n"
            "Results\n"
            "The primary endpoint showed HR 0.74 (95% CI, 0.65 to 0.85; P<0.001).\n"
            "A secondary outcome was OR 1.50 (95% CI, 1.10 to 2.05).\n"
        )
        result = self.pipeline.extract_from_text(text)

        # Check that primary_score is set on all extractions
        for ext in result.effect_estimates:
            assert hasattr(ext, 'primary_score')
            assert hasattr(ext, 'is_primary')

    def test_at_most_one_primary(self):
        """At most one extraction should be marked primary."""
        text = (
            "Methods: RCT of Drug X.\n\n"
            "Results\n"
            "The primary outcome: HR 0.74 (95% CI, 0.65-0.85, P<0.001).\n"
            "Secondary outcome: OR 1.50 (95% CI, 1.10-2.05).\n"
            "Safety: RR 0.92 (95% CI, 0.80-1.05).\n"
        )
        result = self.pipeline.extract_from_text(text)

        primary_count = sum(1 for e in result.effect_estimates if e.is_primary)
        assert primary_count <= 1


class TestAbstractDetection:
    """Test abstract boundary detection."""

    def setup_method(self):
        self.detector = PrimaryOutcomeDetector()

    def test_finds_abstract_end_at_introduction(self):
        text = "Abstract content here.\n\nIntroduction\nMore text."
        end = self.detector._find_abstract_end(text)
        assert end < len(text)
        assert end > 0

    def test_finds_abstract_end_at_methods(self):
        text = "Abstract content here.\n\nMethods\nMore text."
        end = self.detector._find_abstract_end(text)
        assert end > 0

    def test_finds_results_start(self):
        text = "Introduction...\n\nResults\nThe primary outcome..."
        start = self.detector._find_results_start(text)
        assert start > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
