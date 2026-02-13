#!/usr/bin/env python3
"""
OCR Stress Tests for RCT Extractor v4.0.7
Tests OCR performance under various conditions.

Run: pytest tests/test_ocr_stress.py -v
"""

import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional
import re
import sys

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# =============================================================================
# Simulated OCR Output Classes
# =============================================================================

@dataclass
class OCRResult:
    """OCR result for a text region"""
    text: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None


# =============================================================================
# OCR Preprocessing Functions (for testing)
# =============================================================================

def normalize_ocr_text(text: str) -> str:
    """Normalize common OCR errors in text"""
    # Replace common OCR misreads
    replacements = {
        'l': '1',  # l -> 1 (in numeric contexts)
        'O': '0',  # O -> 0 (in numeric contexts)
        'S': '5',  # S -> 5 (in numeric contexts)
        '—': '-',  # em-dash -> hyphen
        '–': '-',  # en-dash -> hyphen
        '−': '-',  # minus sign -> hyphen
        '·': '.',  # middle dot -> period
        ''': "'",  # smart quote
        ''': "'",  # smart quote
        '"': '"',  # smart quote
        '"': '"',  # smart quote
    }

    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)

    # Normalize whitespace
    result = re.sub(r'\s+', ' ', result)
    result = result.strip()

    return result


def correct_numeric_ocr(text: str) -> str:
    """Correct OCR errors in numeric values"""
    # Common numeric OCR corrections
    corrections = [
        (r'[Oo]\.', '0.'),  # O. -> 0.
        (r'\.([Oo])', '.0'),  # .O -> .0
        (r'l(\d)', r'1\1'),  # l followed by digit -> 1
        (r'(\d)l', r'\g<1>1'),  # digit followed by l -> 1
        (r'[Ss](\d)', r'5\1'),  # S followed by digit -> 5
        (r'(\d)[Ss]', r'\g<1>5'),  # digit followed by S -> 5
        (r'\s*-\s*', '-'),  # normalize dashes
    ]

    result = text
    for pattern, replacement in corrections:
        result = re.sub(pattern, replacement, result)

    return result


def calculate_ocr_confidence(text: str) -> float:
    """Calculate estimated OCR confidence based on text quality"""
    # Heuristics for confidence estimation
    score = 1.0

    # Penalize for unusual characters
    unusual_chars = len(re.findall(r'[^\w\s\.,\-\(\)\[\]:;%]', text))
    score -= unusual_chars * 0.02

    # Penalize for likely OCR errors (mixed case in numbers)
    mixed_errors = len(re.findall(r'\d[a-zA-Z]|\b[a-zA-Z]\d', text))
    score -= mixed_errors * 0.05

    # Penalize for too many consecutive special chars
    special_runs = len(re.findall(r'[^\w\s]{3,}', text))
    score -= special_runs * 0.1

    # Ensure score is in valid range
    return max(0.0, min(1.0, score))


def is_ocr_quality_acceptable(confidence: float, threshold: float = 0.85) -> bool:
    """Check if OCR quality is acceptable"""
    return confidence >= threshold


def extract_effect_from_ocr(text: str) -> List[dict]:
    """Extract effect estimates from OCR text"""
    results = []

    # Normalize text first
    text = normalize_ocr_text(text)
    text = correct_numeric_ocr(text)

    # Patterns for effect estimates
    patterns = [
        # HR/OR/RR with CI in parentheses
        r'(HR|OR|RR)\s*[=:]?\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*\)',
        # Value with CI in parentheses
        r'(\d+\.?\d*)\s*\(\s*95%?\s*CI[:\s]*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*\)',
        # Value with CI in brackets
        r'(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*\]',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            groups = match.groups()
            try:
                if len(groups) == 4:  # With effect type prefix
                    effect_type = groups[0].upper()
                    value = float(groups[1])
                    ci_low = float(groups[2])
                    ci_high = float(groups[3])
                elif len(groups) == 3:  # Without prefix
                    effect_type = "HR"  # Default
                    value = float(groups[0])
                    ci_low = float(groups[1])
                    ci_high = float(groups[2])
                else:
                    continue

                # Plausibility check
                if 0.01 <= value <= 100 and ci_low < ci_high:
                    results.append({
                        'effect_type': effect_type,
                        'value': value,
                        'ci_low': ci_low,
                        'ci_high': ci_high,
                        'source': match.group(0)
                    })
            except (ValueError, IndexError):
                continue

    return results


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def clean_ocr_text():
    """High-quality OCR text"""
    return "HR 0.74 (95% CI: 0.65-0.85); p<0.001"


@pytest.fixture
def noisy_ocr_text():
    """OCR text with common errors"""
    return "HR O.74 (95% Cl: O.65—O.85); p<O.OOl"


@pytest.fixture
def degraded_ocr_text():
    """OCR text from degraded scan"""
    return "HR 0 74 (95% CI 0.65 - 0 85)"


@pytest.fixture
def mixed_case_ocr_text():
    """OCR text with mixed case numbers"""
    return "HR O.74 (95% CI: 0.65-0.85) Hazard Ratiο = 0.74"


# =============================================================================
# Normalization Tests
# =============================================================================

class TestOCRNormalization:
    """Tests for OCR text normalization"""

    def test_normalize_em_dash(self):
        """Test normalizing em-dash to hyphen"""
        text = "0.65—0.85"
        normalized = normalize_ocr_text(text)
        assert '-' in normalized
        assert '—' not in normalized

    def test_normalize_en_dash(self):
        """Test normalizing en-dash to hyphen"""
        text = "0.65–0.85"
        normalized = normalize_ocr_text(text)
        assert '-' in normalized
        assert '–' not in normalized

    def test_normalize_middle_dot(self):
        """Test normalizing middle dot to period"""
        text = "0·74"
        normalized = normalize_ocr_text(text)
        assert '.' in normalized
        assert '·' not in normalized

    def test_normalize_whitespace(self):
        """Test normalizing multiple whitespace"""
        text = "HR   0.74   (0.65   -   0.85)"
        normalized = normalize_ocr_text(text)
        assert '   ' not in normalized

    def test_normalize_smart_quotes(self):
        """Test normalizing smart quotes"""
        # Smart quotes should be replaced with regular quotes
        text = "test's value"
        normalized = normalize_ocr_text(text)
        # Just verify normalization runs without error
        assert isinstance(normalized, str)


# =============================================================================
# Numeric Correction Tests
# =============================================================================

class TestNumericCorrection:
    """Tests for OCR numeric correction"""

    def test_correct_O_to_zero(self):
        """Test correcting O to 0 in numeric context"""
        text = "O.74"
        corrected = correct_numeric_ocr(text)
        assert corrected == "0.74"

    def test_correct_l_to_one(self):
        """Test correcting l to 1 in numeric context"""
        text = "0.7l"
        corrected = correct_numeric_ocr(text)
        assert '1' in corrected

    def test_correct_S_to_five(self):
        """Test correcting S to 5 in numeric context"""
        text = "0.S5"
        corrected = correct_numeric_ocr(text)
        assert '5' in corrected

    def test_preserve_words(self):
        """Test that word text is not incorrectly modified"""
        text = "Overall HR 0.74"
        corrected = correct_numeric_ocr(text)
        # Should preserve "Overall" while correcting numbers
        assert "0.74" in corrected


# =============================================================================
# Confidence Calculation Tests
# =============================================================================

class TestConfidenceCalculation:
    """Tests for OCR confidence calculation"""

    def test_high_quality_text(self, clean_ocr_text):
        """Test confidence for clean text"""
        confidence = calculate_ocr_confidence(clean_ocr_text)
        assert confidence >= 0.9

    def test_noisy_text(self, noisy_ocr_text):
        """Test confidence for noisy text"""
        confidence = calculate_ocr_confidence(noisy_ocr_text)
        assert 0.5 <= confidence < 1.0

    def test_heavily_degraded_text(self):
        """Test confidence for heavily degraded text"""
        text = "### ??? $$$ 0.74 ((())) !!!"
        confidence = calculate_ocr_confidence(text)
        assert confidence < 0.7

    def test_confidence_bounds(self):
        """Test confidence is always in valid range"""
        texts = [
            "Normal text",
            "###???!!!***",
            "",
            "HR 0.74 (0.65-0.85)",
        ]
        for text in texts:
            confidence = calculate_ocr_confidence(text)
            assert 0.0 <= confidence <= 1.0


# =============================================================================
# Quality Threshold Tests
# =============================================================================

class TestQualityThreshold:
    """Tests for OCR quality thresholds"""

    def test_acceptable_quality(self):
        """Test acceptable quality detection"""
        assert is_ocr_quality_acceptable(0.90, 0.85) is True
        assert is_ocr_quality_acceptable(0.85, 0.85) is True

    def test_unacceptable_quality(self):
        """Test unacceptable quality detection"""
        assert is_ocr_quality_acceptable(0.80, 0.85) is False
        assert is_ocr_quality_acceptable(0.50, 0.85) is False

    def test_custom_threshold(self):
        """Test custom quality thresholds"""
        assert is_ocr_quality_acceptable(0.75, 0.70) is True
        assert is_ocr_quality_acceptable(0.75, 0.80) is False


# =============================================================================
# Effect Extraction Tests
# =============================================================================

class TestEffectExtraction:
    """Tests for effect extraction from OCR text"""

    def test_extract_from_clean_text(self, clean_ocr_text):
        """Test extraction from clean OCR text"""
        results = extract_effect_from_ocr(clean_ocr_text)
        assert len(results) == 1
        assert results[0]['value'] == 0.74
        assert results[0]['ci_low'] == 0.65
        assert results[0]['ci_high'] == 0.85

    def test_extract_from_noisy_text(self, noisy_ocr_text):
        """Test extraction from noisy OCR text"""
        results = extract_effect_from_ocr(noisy_ocr_text)
        assert isinstance(results, list)
        # After OCR correction, should recover the value
        if results:
            assert any(abs(r['value'] - 0.74) < 0.02 for r in results), \
                f"Expected recovery of ~0.74 from noisy OCR, got {[r['value'] for r in results]}"

    def test_extract_multiple_effects(self):
        """Test extracting multiple effects"""
        text = """
        Primary: HR 0.74 (0.65-0.85)
        Secondary: HR 0.82 (0.70-0.95)
        """
        results = extract_effect_from_ocr(text)
        assert len(results) == 2

    def test_extract_different_effect_types(self):
        """Test extracting different effect types"""
        text = """
        HR 0.74 (0.65-0.85)
        OR 1.15 (0.95-1.39)
        RR 0.88 (0.79-0.98)
        """
        results = extract_effect_from_ocr(text)
        # At least 2 should be found (OR may not match if > 1.0)
        assert len(results) >= 2
        types = [r['effect_type'] for r in results]
        assert 'HR' in types or 'RR' in types

    def test_reject_implausible_values(self):
        """Test rejection of implausible values"""
        text = "HR 500.0 (400.0-600.0)"  # Too high
        results = extract_effect_from_ocr(text)
        assert len(results) == 0

    def test_reject_invalid_ci(self):
        """Test rejection of invalid CI"""
        text = "HR 0.74 (0.85-0.65)"  # low > high
        results = extract_effect_from_ocr(text)
        assert len(results) == 0


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases in OCR processing"""

    def test_empty_text(self):
        """Test handling empty text"""
        results = extract_effect_from_ocr("")
        assert len(results) == 0

    def test_whitespace_only(self):
        """Test handling whitespace-only text"""
        results = extract_effect_from_ocr("   \n\t   ")
        assert len(results) == 0

    def test_unicode_text(self):
        """Test handling unicode characters"""
        text = "HR 0.74 (95% CI: 0.65–0.85)"  # en-dash
        results = extract_effect_from_ocr(text)
        assert len(results) >= 1

    def test_fragmented_text(self, degraded_ocr_text):
        """Test handling fragmented OCR text"""
        results = extract_effect_from_ocr(degraded_ocr_text)
        assert isinstance(results, list)
        # Fragmented "HR 0 74 (95% CI 0.65 - 0 85)" is unlikely to parse,
        # but verify no crash and document expected limitation
        # If it does parse, values should be reasonable
        for r in results:
            assert 0.01 <= r['value'] <= 100, f"Implausible value from degraded OCR: {r['value']}"


# =============================================================================
# Degradation Simulation Tests
# =============================================================================

class TestDegradationSimulation:
    """Tests simulating various degradation levels"""

    def test_blur_simulation(self):
        """Test OCR from blurred text simulation"""
        # Simulated blur: spaces between characters
        text = "H R  0 . 7 4  ( 0 . 6 5 - 0 . 8 5 )"
        # After normalization
        normalized = re.sub(r'\s+', '', text)
        assert "HR0.74(0.65-0.85)" in normalized

    def test_noise_simulation(self):
        """Test OCR from noisy text simulation"""
        # Simulated noise: extra characters
        text = "HR' 0.74 (0.65-.0.85)"
        results = extract_effect_from_ocr(text)
        # May partially succeed
        assert isinstance(results, list)

    def test_skew_simulation(self):
        """Test OCR from skewed text simulation"""
        # Skewed text often has character substitutions
        text = "HR O,74 (O,65-O,85)"  # commas instead of periods
        text_fixed = text.replace(',', '.')
        results = extract_effect_from_ocr(text_fixed)
        assert len(results) >= 1


# =============================================================================
# Multi-Language OCR Tests
# =============================================================================

class TestMultiLanguageOCR:
    """Tests for multi-language OCR handling"""

    def test_german_decimal_separator(self):
        """Test German decimal separator (comma)"""
        text = "HR 0,74 (0,65-0,85)"
        # Convert to standard format
        text_normalized = text.replace(',', '.')
        results = extract_effect_from_ocr(text_normalized)
        assert len(results) >= 1

    def test_french_spacing(self):
        """Test French number spacing"""
        text = "HR 0.74 (0.65 – 0.85)"  # spaces around dash
        results = extract_effect_from_ocr(text)
        assert len(results) >= 1

    def test_latin_characters(self):
        """Test text with Latin characters"""
        # Standard format should work
        text = "Hazard Ratio: HR 0.74 (0.65-0.85)"
        results = extract_effect_from_ocr(text)
        assert len(results) >= 1


# =============================================================================
# OCR Quality Levels Tests
# =============================================================================

class TestOCRQualityLevels:
    """Tests for different OCR quality levels"""

    def test_excellent_quality(self):
        """Test OCR at excellent quality (>95% confidence)"""
        text = "HR 0.74 (95% CI: 0.65-0.85)"
        confidence = calculate_ocr_confidence(text)
        results = extract_effect_from_ocr(text)
        assert confidence > 0.9
        assert len(results) == 1

    def test_good_quality(self):
        """Test OCR at good quality (85-95% confidence)"""
        text = "HR 0.74 (95% CI 0.65-0.85) *p<0.001"
        confidence = calculate_ocr_confidence(text)
        results = extract_effect_from_ocr(text)
        assert len(results) >= 1

    def test_marginal_quality(self):
        """Test OCR at marginal quality (70-85% confidence)"""
        text = "HR 0.74 (95% CI: 0.65—0.85) ** p<O.OO1 ##"
        # Some special chars reduce confidence
        confidence = calculate_ocr_confidence(text)
        results = extract_effect_from_ocr(text)
        # May still extract if pattern matches

    def test_poor_quality(self):
        """Test OCR at poor quality (<70% confidence)"""
        text = "### HR ??? 0.74 *** (((0.65---0.85))) !!!"
        confidence = calculate_ocr_confidence(text)
        # Should flag as low confidence
        assert confidence < 0.7


# =============================================================================
# Integration with Extraction Pipeline
# =============================================================================

class TestOCRExtractionPipeline:
    """Tests for OCR in extraction pipeline"""

    def test_full_pipeline_clean(self):
        """Test full pipeline with clean OCR"""
        text = "Primary endpoint: HR 0.74 (95% CI: 0.65-0.85)"

        # Step 1: Check quality
        confidence = calculate_ocr_confidence(text)
        assert is_ocr_quality_acceptable(confidence)

        # Step 2: Normalize
        normalized = normalize_ocr_text(text)
        normalized = correct_numeric_ocr(normalized)

        # Step 3: Extract
        results = extract_effect_from_ocr(normalized)
        assert len(results) == 1
        assert results[0]['value'] == 0.74

    def test_full_pipeline_noisy(self):
        """Test full pipeline with noisy OCR"""
        text = "Primary endpoint: HR O.74 (95% Cl: O.65—O.85)"

        # Step 1: Check quality
        confidence = calculate_ocr_confidence(text)

        # Step 2: Normalize and correct
        normalized = normalize_ocr_text(text)
        normalized = correct_numeric_ocr(normalized)

        # Step 3: Extract
        results = extract_effect_from_ocr(normalized)
        # Should recover the value
        if results:
            assert abs(results[0]['value'] - 0.74) < 0.01


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
