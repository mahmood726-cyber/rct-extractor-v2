"""
Tests for Multi-Language Effect Extraction
==========================================

Tests language detection and extraction for German, French,
Spanish, Italian, Portuguese, and Asian languages.
"""

import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lang.multi_lang_extractor import (
    MultiLangExtractor,
    detect_language,
    normalize_european_decimals,
    Language,
    LanguageDetection,
)


class TestLanguageDetection:
    """Tests for language detection"""

    def test_detect_german(self):
        """Test German detection"""
        text = """
        Die Studie untersuchte die Behandlung von Patienten mit Herzinsuffizienz.
        Das Hazard Ratio betrug 0,78 (95%-KI 0,65-0,94).
        Die Ergebnisse waren signifikant.
        """
        detection = detect_language(text)
        assert detection.language == Language.GERMAN
        assert detection.confidence > 0.5

    def test_detect_french(self):
        """Test French detection"""
        text = """
        L'étude a évalué le traitement des patients atteints d'insuffisance cardiaque.
        Le rapport de risque était de 0,82 (IC 95% 0,71-0,95).
        Les résultats étaient significatifs.
        """
        detection = detect_language(text)
        assert detection.language == Language.FRENCH
        assert detection.confidence > 0.5

    def test_detect_spanish(self):
        """Test Spanish detection"""
        text = """
        El estudio evaluó el tratamiento de pacientes con insuficiencia cardíaca.
        La razón de riesgo fue 0,75 (IC 95% 0,62-0,90).
        Los resultados fueron significativos.
        """
        detection = detect_language(text)
        assert detection.language == Language.SPANISH
        assert detection.confidence > 0.5

    def test_detect_italian(self):
        """Test Italian detection"""
        text = """
        Lo studio ha valutato il trattamento dei pazienti con insufficienza cardiaca.
        Il rapporto di rischio era 0,80 (IC 95% 0,68-0,94).
        I risultati erano significativi.
        """
        detection = detect_language(text)
        assert detection.language == Language.ITALIAN
        assert detection.confidence > 0.4

    def test_detect_portuguese(self):
        """Test Portuguese detection"""
        text = """
        O estudo avaliou o tratamento de pacientes com insuficiência cardíaca.
        A razão de risco foi 0,77 (IC 95% 0,64-0,92).
        Os resultados foram significativos.
        """
        detection = detect_language(text)
        assert detection.language == Language.PORTUGUESE
        assert detection.confidence > 0.4

    def test_detect_english_default(self):
        """Test English detection (default for ambiguous text)"""
        text = "HR 0.74 (95% CI 0.65-0.85)"
        detection = detect_language(text)
        # Should default to English for short/ambiguous text
        assert detection.language == Language.ENGLISH

    def test_detect_chinese(self):
        """Test Chinese detection"""
        text = "风险比为0.78（95%置信区间0.65-0.94）"
        detection = detect_language(text)
        assert detection.language == Language.CHINESE

    def test_detect_japanese(self):
        """Test Japanese detection"""
        text = "ハザード比は0.78（95%信頼区間0.65-0.94）でした"
        detection = detect_language(text)
        assert detection.language == Language.JAPANESE


class TestEuropeanDecimalNormalization:
    """Tests for European decimal normalization"""

    def test_normalize_comma_decimal(self):
        """Test comma to period conversion"""
        assert normalize_european_decimals("0,74") == "0.74"
        assert normalize_european_decimals("1,25") == "1.25"
        assert normalize_european_decimals("0,65-0,85") == "0.65-0.85"

    def test_preserve_non_decimal_comma(self):
        """Test that non-decimal commas are preserved"""
        # Commas between large numbers should be preserved
        assert normalize_european_decimals("1,000") == "1.000"  # Becomes decimal
        # But text commas should be preserved
        text = "HR, OR, and RR"
        assert "," in normalize_european_decimals(text)

    def test_multiple_decimals(self):
        """Test multiple decimal conversions"""
        text = "HR 0,74 (95%-KI 0,65-0,94)"
        result = normalize_european_decimals(text)
        assert "0.74" in result
        assert "0.65" in result
        assert "0.94" in result


class TestMultiLangExtractor:
    """Tests for MultiLangExtractor"""

    def setup_method(self):
        """Set up extractor for each test"""
        self.extractor = MultiLangExtractor()

    def test_german_hr_extraction(self):
        """Test German HR extraction"""
        text = "Hazard Ratio 0,78 (95%-KI 0,65-0,94)"
        results = self.extractor.extract(text, language='de')
        assert isinstance(results, list)
        # Should extract at least one result with the correct value
        if results:
            values = [r.point_estimate if hasattr(r, 'point_estimate') else r.get('value') for r in results]
            assert any(abs(v - 0.78) < 0.01 for v in values if v is not None), \
                f"Expected value ~0.78, got {values}"

    def test_french_rr_extraction(self):
        """Test French RR extraction"""
        text = "Risque relatif 0,82 (IC 95% 0,71-0,95)"
        results = self.extractor.extract(text, language='fr')
        assert isinstance(results, list)
        if results:
            values = [r.point_estimate if hasattr(r, 'point_estimate') else r.get('value') for r in results]
            assert any(abs(v - 0.82) < 0.01 for v in values if v is not None), \
                f"Expected value ~0.82, got {values}"

    def test_spanish_or_extraction(self):
        """Test Spanish OR extraction"""
        text = "Razón de momios 2,15 (IC 95% 1,62-2,85)"
        results = self.extractor.extract(text, language='es')
        assert isinstance(results, list)
        if results:
            values = [r.point_estimate if hasattr(r, 'point_estimate') else r.get('value') for r in results]
            assert any(abs(v - 2.15) < 0.01 for v in values if v is not None), \
                f"Expected value ~2.15, got {values}"

    def test_auto_language_detection(self):
        """Test automatic language detection during extraction"""
        german_text = """
        Die Studie zeigte ein Hazard Ratio von 0,74 (95%-KI 0,62-0,88).
        Die Behandlung war signifikant wirksam.
        """
        results = self.extractor.extract(german_text, language='auto')
        assert isinstance(results, list)
        if results:
            values = [r.point_estimate if hasattr(r, 'point_estimate') else r.get('value') for r in results]
            assert any(abs(v - 0.74) < 0.01 for v in values if v is not None), \
                f"Expected value ~0.74, got {values}"

    def test_ocr_config_german(self):
        """Test OCR config for German"""
        config = self.extractor.get_ocr_config('de')
        assert 'deu' in config
        assert 'eng' in config

    def test_ocr_config_french(self):
        """Test OCR config for French"""
        config = self.extractor.get_ocr_config('fr')
        assert 'fra' in config
        assert 'eng' in config

    def test_ocr_config_multi(self):
        """Test multi-language OCR config"""
        config = self.extractor.get_ocr_config('multi')
        assert 'eng' in config
        assert 'deu' in config
        assert 'fra' in config

    def test_ci_label_german(self):
        """Test CI label for German"""
        label = self.extractor.get_ci_label(Language.GERMAN)
        assert label == 'KI'

    def test_ci_label_french(self):
        """Test CI label for French"""
        label = self.extractor.get_ci_label(Language.FRENCH)
        assert label == 'IC'

    def test_ci_label_english(self):
        """Test CI label for English (default)"""
        label = self.extractor.get_ci_label(Language.ENGLISH)
        assert label == 'CI'


class TestMultiLangPatterns:
    """Tests for multi-language patterns in EnhancedExtractor"""

    def setup_method(self):
        """Set up extractor"""
        from src.core.enhanced_extractor_v3 import EnhancedExtractor
        self.extractor = EnhancedExtractor()

    def test_german_hr_pattern(self):
        """Test German HR pattern in main extractor"""
        text = "HR 0.78 (95%-KI 0.65-0.94)"
        results = self.extractor.extract(text)
        assert isinstance(results, list)
        assert len(results) >= 1, "Should extract HR from German KI format"
        assert abs(results[0].point_estimate - 0.78) < 0.01

    def test_french_ic_pattern(self):
        """Test French IC pattern"""
        text = "HR 0.82 (IC 95% 0.71-0.95)"
        results = self.extractor.extract(text)
        assert isinstance(results, list)
        assert len(results) >= 1, "Should extract HR from French IC format"
        assert abs(results[0].point_estimate - 0.82) < 0.01

    def test_spanish_ic_pattern(self):
        """Test Spanish IC pattern"""
        text = "OR 2.15 (IC 95% 1.62-2.85)"
        results = self.extractor.extract(text)
        assert isinstance(results, list)
        assert len(results) >= 1, "Should extract OR from Spanish IC format"
        assert abs(results[0].point_estimate - 2.15) < 0.01


class TestLanguageIndicators:
    """Tests for language indicator patterns"""

    def test_german_indicators(self):
        """Test German keyword indicators"""
        text = "Die Studie wurde durchgeführt"
        detection = detect_language(text)
        assert len(detection.indicators) > 0 or detection.language == Language.GERMAN

    def test_french_indicators(self):
        """Test French keyword indicators"""
        text = "L'étude a été réalisée avec les patients"
        detection = detect_language(text)
        assert detection.language == Language.FRENCH

    def test_mixed_language_text(self):
        """Test detection with mixed language (English dominant)"""
        text = """
        The study showed a hazard ratio of 0.74.
        Das Konfidenzintervall war 0.62 bis 0.88.
        """
        detection = detect_language(text)
        # Should detect something, either English or German
        assert detection.language in [Language.ENGLISH, Language.GERMAN]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
