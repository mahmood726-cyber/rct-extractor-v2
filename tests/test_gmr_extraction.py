#!/usr/bin/env python3
"""
Tests for GMR (Geometric Mean Ratio) extraction (v5.2)
======================================================

Verifies that:
1. All 10 CI pattern variants match correctly
2. Value-only patterns match
3. Plausibility rejects out-of-range values
4. Plausibility rejects negative CI lower bound
5. GMT values are NOT extracted as GMR
6. No false matches on non-GMR text
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from src.core.enhanced_extractor_v3 import EnhancedExtractor, EffectType


@pytest.fixture
def extractor():
    return EnhancedExtractor()


class TestGMRCIPatterns:
    """Test all GMR CI pattern variants."""

    def test_gmr_colon_parentheses(self, extractor):
        """GMR: 0.95 (95% CI 0.87-1.04)"""
        results = extractor.extract("GMR: 0.95 (95% CI 0.87-1.04)", include_value_only=False)
        assert len(results) >= 1
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 1
        assert gmr[0].point_estimate == pytest.approx(0.95, abs=0.01)
        assert gmr[0].ci.lower == pytest.approx(0.87, abs=0.01)
        assert gmr[0].ci.upper == pytest.approx(1.04, abs=0.01)

    def test_gmr_space_to(self, extractor):
        """GMR 1.15 (1.02 to 1.30)"""
        results = extractor.extract("GMR 1.15 (1.02 to 1.30)", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 1
        assert gmr[0].point_estimate == pytest.approx(1.15, abs=0.01)

    def test_gmr_was(self, extractor):
        """GMR was 2.05 (95% CI, 1.45-2.90)"""
        results = extractor.extract("GMR was 2.05 (95% CI, 1.45-2.90)", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 1
        assert gmr[0].point_estimate == pytest.approx(2.05, abs=0.01)

    def test_gmr_equals(self, extractor):
        """GMR=1.08 (0.95-1.23)"""
        results = extractor.extract("GMR=1.08 (0.95-1.23)", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 1
        assert gmr[0].point_estimate == pytest.approx(1.08, abs=0.01)

    def test_gmr_equals_semicolon_ci(self, extractor):
        """GMR=1.08; 95% CI: 0.95-1.23"""
        results = extractor.extract("GMR=1.08; 95% CI: 0.95-1.23", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 1
        assert gmr[0].point_estimate == pytest.approx(1.08, abs=0.01)

    def test_geometric_mean_ratio_long_form(self, extractor):
        """geometric mean ratio 1.23 (95% CI 1.05-1.44)"""
        results = extractor.extract("geometric mean ratio 1.23 (95% CI 1.05-1.44)", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 1
        assert gmr[0].point_estimate == pytest.approx(1.23, abs=0.01)

    def test_geometric_mean_ratio_was(self, extractor):
        """The geometric mean ratio was 1.23 (95% CI 1.05-1.44)."""
        results = extractor.extract("The geometric mean ratio was 1.23 (95% CI 1.05-1.44).", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 1
        assert gmr[0].point_estimate == pytest.approx(1.23, abs=0.01)

    def test_geometric_mean_ratio_square_brackets(self, extractor):
        """geometric mean ratio: 2.05 [95% CI 1.45-2.90]"""
        results = extractor.extract("geometric mean ratio: 2.05 [95% CI 1.45-2.90]", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 1
        assert gmr[0].point_estimate == pytest.approx(2.05, abs=0.01)

    def test_gmr_ci_label_prefix(self, extractor):
        """GMR (95% CI): 1.15 (1.02-1.30)"""
        results = extractor.extract("GMR (95% CI): 1.15 (1.02-1.30)", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 1
        assert gmr[0].point_estimate == pytest.approx(1.15, abs=0.01)

    def test_gmr_square_bracket_ci(self, extractor):
        """GMR: 0.95 [95% CI 0.87-1.04]"""
        results = extractor.extract("GMR: 0.95 [95% CI 0.87-1.04]", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 1


class TestGMRValueOnly:
    """Test value-only patterns."""

    def test_gmr_value_only(self, extractor):
        """GMR 1.23 (no CI)"""
        results = extractor.extract("GMR 1.23", include_value_only=True)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) >= 1
        assert gmr[0].point_estimate == pytest.approx(1.23, abs=0.01)
        assert gmr[0].ci is None

    def test_geometric_mean_ratio_value_only(self, extractor):
        """geometric mean ratio 1.23 (no CI)"""
        results = extractor.extract("geometric mean ratio 1.23", include_value_only=True)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) >= 1


class TestGMRPlausibility:
    """Test plausibility checks for GMR."""

    def test_rejects_out_of_range_high(self, extractor):
        """GMR=200 should be rejected (> 100.0 plausibility limit)."""
        results = extractor.extract("GMR=200.0 (150.0-250.0)", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 0

    def test_accepts_reasonable_value(self, extractor):
        """GMR=1.5 should be accepted."""
        results = extractor.extract("GMR 1.50 (1.10-2.05)", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 1


class TestGMRNonMatches:
    """Ensure GMT and other non-GMR text are NOT extracted."""

    def test_gmt_not_extracted_as_gmr(self, extractor):
        """GMT 256 (95% CI 200-330) should NOT match GMR patterns."""
        results = extractor.extract("GMT 256 (95% CI 200-330)", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 0

    def test_gmt_high_value_not_extracted(self, extractor):
        """GMT: 512 — high value should fail plausibility even if somehow matched."""
        results = extractor.extract("GMT: 512 (95% CI 384-682)", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 0

    def test_ratio_without_gmr_label(self, extractor):
        """'The ratio of titers was 1.5' should not match GMR."""
        results = extractor.extract("The ratio of titers was 1.5.", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 0

    def test_gmr_text_no_value(self, extractor):
        """'GMR values were calculated' — no numeric value, no extraction."""
        results = extractor.extract("GMR values were calculated for each time point.", include_value_only=False)
        gmr = [r for r in results if r.effect_type == EffectType.GMR]
        assert len(gmr) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
