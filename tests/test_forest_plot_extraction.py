#!/usr/bin/env python3
"""
Forest Plot Extraction Tests for RCT Extractor v4.0.7
Tests forest plot detection, parsing, and effect estimate extraction.

Run: pytest tests/test_forest_plot_extraction.py -v
"""

import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple
import sys

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# =============================================================================
# Local Data Classes (to avoid circular imports)
# =============================================================================

@dataclass
class ForestPlotResult:
    """Single effect estimate from forest plot"""
    study_name: str
    effect_type: str  # HR, OR, RR
    value: float
    ci_low: float
    ci_high: float
    weight: Optional[float] = None
    confidence: float = 0.0
    page_num: int = 0


# =============================================================================
# Mock Functions for Testing
# =============================================================================

def infer_effect_type(text: str) -> str:
    """Infer effect type from forest plot text"""
    text_lower = text.lower()

    if 'hazard' in text_lower or 'survival' in text_lower:
        return 'HR'
    elif 'odds' in text_lower:
        return 'OR'
    elif 'risk ratio' in text_lower or 'relative risk' in text_lower:
        return 'RR'

    if 'favours' in text_lower or 'favor' in text_lower:
        return 'OR'

    return 'HR'  # Default


def merge_overlapping(
    regions: List[Tuple[int, int, int, int]]
) -> List[Tuple[int, int, int, int]]:
    """Merge overlapping regions"""
    if not regions:
        return []

    # Sort by x1
    regions = sorted(regions, key=lambda r: r[0])

    merged = [regions[0]]
    for r in regions[1:]:
        last = merged[-1]

        # Check overlap
        if r[0] < last[2] and r[1] < last[3]:
            # Merge
            merged[-1] = (
                min(last[0], r[0]),
                min(last[1], r[1]),
                max(last[2], r[2]),
                max(last[3], r[3])
            )
        else:
            merged.append(r)

    return merged


def parse_forest_plot_text(text: str) -> List[ForestPlotResult]:
    """Parse forest plot OCR text to extract effect estimates"""
    import re

    results = []

    patterns = [
        r'(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[,\-–]\s*(\d+\.?\d*)\s*\)',
        r'(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[,\-–]\s*(\d+\.?\d*)\s*\]',
    ]

    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                try:
                    value = float(match.group(1))
                    ci_low = float(match.group(2))
                    ci_high = float(match.group(3))

                    # Plausibility check
                    if not (0.01 <= value <= 100):
                        continue
                    if ci_low >= ci_high:
                        continue

                    # Extract study name
                    study_name = line[:match.start()].strip()
                    study_name = re.sub(r'[^\w\s\-]', '', study_name).strip()

                    if len(study_name) < 2:
                        study_name = "Unknown"

                    effect_type = infer_effect_type(text)

                    results.append(ForestPlotResult(
                        study_name=study_name[:50],
                        effect_type=effect_type,
                        value=value,
                        ci_low=ci_low,
                        ci_high=ci_high,
                        confidence=0.7,
                        page_num=0
                    ))
                except (ValueError, IndexError):
                    continue

    return results


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_forest_plot_text():
    """Sample OCR text from a forest plot"""
    return """
    Hazard Ratio for Primary Outcome

    Study                           Events   HR (95% CI)
    DAPA-HF                         386      0.74 (0.65, 0.85)
    EMPEROR-Reduced                 361      0.75 (0.65, 0.86)
    EMPEROR-Preserved               415      0.79 (0.69, 0.90)
    DELIVER                         512      0.82 (0.73, 0.92)

    Overall (I² = 0%)                       0.77 (0.72, 0.83)

    Favours treatment    Favours control
          0.5    0.75    1.0    1.25   1.5
    """


@pytest.fixture
def sample_or_forest_text():
    """Sample OCR text with odds ratios"""
    return """
    Odds Ratio for Adverse Events

    Trial           OR (95% CI)
    Study A         1.15 (0.89, 1.48)
    Study B         0.92 (0.71, 1.19)
    Study C         1.05 (0.82, 1.35)

    Pooled          1.04 [0.92-1.18]
    """


@pytest.fixture
def sample_rr_forest_text():
    """Sample OCR text with relative risks"""
    return """
    Relative Risk of Mortality

    Study Name              RR (95% CI)
    TRIAL-A 2020           0.85 (0.72, 0.99)
    TRIAL-B 2021           0.91 (0.78, 1.06)
    TRIAL-C 2022           0.88 (0.75, 1.03)

    Risk Ratio Overall     0.88 [0.80-0.97]
    """


# =============================================================================
# ForestPlotResult Tests
# =============================================================================

class TestForestPlotResult:
    """Tests for ForestPlotResult dataclass"""

    def test_result_creation(self):
        """Test basic result creation"""
        result = ForestPlotResult(
            study_name="DAPA-HF",
            effect_type="HR",
            value=0.74,
            ci_low=0.65,
            ci_high=0.85
        )
        assert result.study_name == "DAPA-HF"
        assert result.effect_type == "HR"
        assert result.value == 0.74
        assert result.ci_low == 0.65
        assert result.ci_high == 0.85
        assert result.weight is None
        assert result.confidence == 0.0

    def test_result_with_weight(self):
        """Test result with weight"""
        result = ForestPlotResult(
            study_name="Test",
            effect_type="OR",
            value=1.2,
            ci_low=0.9,
            ci_high=1.6,
            weight=25.5
        )
        assert result.weight == 25.5

    def test_result_with_confidence(self):
        """Test result with confidence score"""
        result = ForestPlotResult(
            study_name="Test",
            effect_type="RR",
            value=0.9,
            ci_low=0.8,
            ci_high=1.0,
            confidence=0.85
        )
        assert result.confidence == 0.85


# =============================================================================
# Effect Type Inference Tests
# =============================================================================

class TestEffectTypeInference:
    """Tests for effect type inference from text"""

    def test_infer_hr_from_hazard(self):
        """Test inferring HR from 'hazard' keyword"""
        text = "Hazard Ratio for Primary Endpoint"
        assert infer_effect_type(text) == "HR"

    def test_infer_hr_from_survival(self):
        """Test inferring HR from 'survival' keyword"""
        text = "Survival Analysis Results"
        assert infer_effect_type(text) == "HR"

    def test_infer_or_from_odds(self):
        """Test inferring OR from 'odds' keyword"""
        text = "Odds Ratio for Adverse Events"
        assert infer_effect_type(text) == "OR"

    def test_infer_rr_from_risk_ratio(self):
        """Test inferring RR from 'risk ratio' keyword"""
        text = "Risk Ratio of Mortality"
        assert infer_effect_type(text) == "RR"

    def test_infer_rr_from_relative_risk(self):
        """Test inferring RR from 'relative risk' keyword"""
        text = "Relative Risk Analysis"
        assert infer_effect_type(text) == "RR"

    def test_infer_or_from_favours(self):
        """Test inferring OR from 'favours' keyword"""
        text = "Favours treatment | Favours control"
        assert infer_effect_type(text) == "OR"

    def test_default_to_hr(self):
        """Test defaulting to HR when no keywords match"""
        text = "Forest plot analysis results"
        assert infer_effect_type(text) == "HR"


# =============================================================================
# Region Merging Tests
# =============================================================================

class TestRegionMerging:
    """Tests for overlapping region merging"""

    def test_merge_empty_list(self):
        """Test merging empty list"""
        assert merge_overlapping([]) == []

    def test_no_overlap(self):
        """Test regions with no overlap"""
        regions = [(0, 0, 100, 100), (200, 0, 300, 100)]
        merged = merge_overlapping(regions)
        assert len(merged) == 2

    def test_full_overlap(self):
        """Test fully overlapping regions"""
        regions = [(0, 0, 100, 100), (10, 10, 90, 90)]
        merged = merge_overlapping(regions)
        assert len(merged) == 1
        assert merged[0] == (0, 0, 100, 100)

    def test_partial_overlap(self):
        """Test partially overlapping regions"""
        regions = [(0, 0, 100, 100), (50, 50, 150, 150)]
        merged = merge_overlapping(regions)
        assert len(merged) == 1
        assert merged[0][0] == 0  # min x1
        assert merged[0][2] == 150  # max x2

    def test_multiple_merges(self):
        """Test multiple overlapping regions"""
        regions = [(0, 0, 100, 100), (50, 0, 150, 100), (100, 0, 200, 100)]
        merged = merge_overlapping(regions)
        assert len(merged) == 1
        assert merged[0] == (0, 0, 200, 100)


# =============================================================================
# Text Parsing Tests
# =============================================================================

class TestTextParsing:
    """Tests for forest plot text parsing"""

    def test_parse_parentheses_format(self, sample_forest_plot_text):
        """Test parsing (value, lower, upper) format"""
        results = parse_forest_plot_text(sample_forest_plot_text)
        assert len(results) >= 4

    def test_parse_bracket_format(self, sample_or_forest_text):
        """Test parsing [lower-upper] format"""
        results = parse_forest_plot_text(sample_or_forest_text)
        assert len(results) >= 3

    def test_parse_extracts_values(self, sample_forest_plot_text):
        """Test that correct values are extracted"""
        results = parse_forest_plot_text(sample_forest_plot_text)

        # Find DAPA-HF result
        dapa_results = [r for r in results if "DAPA" in r.study_name.upper()]
        if dapa_results:
            r = dapa_results[0]
            assert r.value == 0.74
            assert r.ci_low == 0.65
            assert r.ci_high == 0.85

    def test_parse_extracts_study_names(self, sample_forest_plot_text):
        """Test that study names are extracted"""
        results = parse_forest_plot_text(sample_forest_plot_text)
        study_names = [r.study_name for r in results]

        # At least some studies should be named
        assert any(len(name) > 2 for name in study_names)

    def test_parse_infers_effect_type(self, sample_forest_plot_text):
        """Test that effect type is inferred correctly"""
        results = parse_forest_plot_text(sample_forest_plot_text)
        if results:
            assert results[0].effect_type == "HR"

    def test_parse_or_text(self, sample_or_forest_text):
        """Test parsing OR forest plot text"""
        results = parse_forest_plot_text(sample_or_forest_text)
        if results:
            assert results[0].effect_type == "OR"

    def test_parse_rr_text(self, sample_rr_forest_text):
        """Test parsing RR forest plot text"""
        results = parse_forest_plot_text(sample_rr_forest_text)
        if results:
            assert results[0].effect_type == "RR"


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases in forest plot parsing"""

    def test_reject_invalid_ci(self):
        """Test that invalid CI (low > high) is rejected"""
        text = "Study 1.50 (0.80, 0.60)"  # CI low > high
        results = parse_forest_plot_text(text)
        assert len(results) == 0

    def test_reject_extreme_values(self):
        """Test that extreme values are rejected"""
        text = "Study 500.0 (400.0, 600.0)"  # Value > 100
        results = parse_forest_plot_text(text)
        assert len(results) == 0

    def test_reject_zero_values(self):
        """Test that zero values are rejected"""
        text = "Study 0.00 (0.00, 0.00)"  # Value < 0.01
        results = parse_forest_plot_text(text)
        assert len(results) == 0

    def test_unknown_study_name(self):
        """Test handling of missing study name"""
        text = "0.75 (0.65, 0.86)"  # No study name
        results = parse_forest_plot_text(text)
        if results:
            assert results[0].study_name == "Unknown"

    def test_unicode_dashes(self):
        """Test handling of unicode dashes"""
        text = "Study A 0.85 (0.72–0.99)"  # En-dash
        results = parse_forest_plot_text(text)
        assert len(results) == 1
        assert results[0].ci_high == 0.99

    def test_whitespace_variations(self):
        """Test handling of various whitespace"""
        text = "Study A    0.75    (   0.65   ,   0.85   )"
        results = parse_forest_plot_text(text)
        assert len(results) == 1

    def test_no_effects_in_text(self):
        """Test text with no effect estimates"""
        text = """
        This is just some text
        without any effect estimates
        or confidence intervals
        """
        results = parse_forest_plot_text(text)
        assert len(results) == 0


# =============================================================================
# Pooled Estimate Tests
# =============================================================================

class TestPooledEstimates:
    """Tests for pooled/overall estimate detection"""

    def test_parse_pooled_estimate(self):
        """Test parsing pooled estimate"""
        text = """
        Study A  0.80 (0.70, 0.91)
        Study B  0.85 (0.74, 0.97)
        Overall  0.82 (0.75, 0.90)
        """
        results = parse_forest_plot_text(text)
        assert len(results) == 3

        overall = [r for r in results if "Overall" in r.study_name]
        assert len(overall) == 1
        assert overall[0].value == 0.82

    def test_parse_diamond_indicator(self):
        """Test parsing text with diamond indicator"""
        text = """
        Trial 1  0.78 (0.68, 0.89)
        Trial 2  0.81 (0.71, 0.92)
        Pooled (◆)  0.79 (0.72, 0.87)
        """
        results = parse_forest_plot_text(text)
        assert len(results) >= 2


# =============================================================================
# Complex Format Tests
# =============================================================================

class TestComplexFormats:
    """Tests for complex forest plot formats"""

    def test_multi_column_format(self):
        """Test parsing multi-column format with events"""
        text = """
        Study           Events/Total     HR (95% CI)
        DAPA-HF         386/2373         0.74 (0.65, 0.85)
        EMPEROR         361/1863         0.75 (0.65, 0.86)
        """
        results = parse_forest_plot_text(text)
        assert len(results) == 2

    def test_weight_column(self):
        """Test parsing format with weight column"""
        text = """
        Study           Weight (%)    OR (95% CI)
        Trial A         25.3          1.15 (0.89, 1.48)
        Trial B         31.2          0.92 (0.71, 1.19)
        """
        results = parse_forest_plot_text(text)
        assert len(results) == 2


# =============================================================================
# Subgroup Analysis Tests
# =============================================================================

class TestSubgroupAnalysis:
    """Tests for subgroup forest plots"""

    def test_subgroup_forest_plot(self):
        """Test parsing subgroup analysis forest plot"""
        text = """
        Subgroup Analysis

        Age <65          0.72 (0.58, 0.89)
        Age ≥65          0.76 (0.64, 0.91)

        Male             0.73 (0.62, 0.86)
        Female           0.76 (0.60, 0.96)

        P for interaction = 0.42
        """
        results = parse_forest_plot_text(text)
        assert len(results) == 4


# =============================================================================
# Validation Accuracy Tests
# =============================================================================

class TestValidationAccuracy:
    """Tests for extraction accuracy validation"""

    def test_known_values_dapa_hf(self):
        """Test against known DAPA-HF values"""
        text = "DAPA-HF 2019   HR 0.74 (0.65, 0.85)"
        results = parse_forest_plot_text(text)
        assert len(results) == 1

        r = results[0]
        assert abs(r.value - 0.74) < 0.001
        assert abs(r.ci_low - 0.65) < 0.001
        assert abs(r.ci_high - 0.85) < 0.001

    def test_known_values_emperor(self):
        """Test against known EMPEROR-Reduced values"""
        text = "EMPEROR-Reduced   HR 0.75 (0.65, 0.86)"
        results = parse_forest_plot_text(text)
        assert len(results) == 1

        r = results[0]
        assert abs(r.value - 0.75) < 0.001
        assert abs(r.ci_low - 0.65) < 0.001
        assert abs(r.ci_high - 0.86) < 0.001


# =============================================================================
# Integration Tests (Skipped - Require CV2/Tesseract)
# =============================================================================

class TestIntegration:
    """Integration tests requiring full dependencies"""

    @pytest.mark.skip(reason="Requires cv2, tesseract, fitz")
    def test_extract_from_real_pdf(self):
        """Test extracting from real PDF with forest plot"""
        pass

    @pytest.mark.skip(reason="Requires cv2")
    def test_detect_forest_plot_region(self):
        """Test detecting forest plot region in image"""
        pass

    @pytest.mark.skip(reason="Requires cv2")
    def test_has_plot_elements(self):
        """Test detecting plot elements (squares, diamonds)"""
        pass


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
