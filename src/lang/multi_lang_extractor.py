"""
Multi-Language Effect Extractor
===============================

Provides language detection and language-specific extraction patterns
for RCT effect estimates in German, French, Spanish, Italian, and Portuguese.

Usage:
    from src.lang.multi_lang_extractor import MultiLangExtractor

    extractor = MultiLangExtractor()
    effects = extractor.extract(text, language='auto')  # Auto-detect
    effects = extractor.extract(text, language='de')     # Force German
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from enum import Enum


class Language(Enum):
    """Supported languages"""
    ENGLISH = "en"
    GERMAN = "de"
    FRENCH = "fr"
    SPANISH = "es"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    UNKNOWN = "unknown"


@dataclass
class LanguageDetection:
    """Result of language detection"""
    language: Language
    confidence: float
    indicators: List[str]


# Language-specific keywords for detection
LANGUAGE_INDICATORS = {
    Language.GERMAN: [
        r'\bund\b', r'\bdie\b', r'\bder\b', r'\bdas\b', r'\bwurde\b',
        r'\bPatient(?:en)?\b', r'\bStudie\b', r'\bBehandlung\b',
        r'\bKonfidenzintervall\b', r'\bHazard[-\s]?Ratio\b',
        r'\bRelatives?\s+Risiko\b', r'\bMittlere\s+Differenz\b',
        r'\bErgebnis(?:se)?\b', r'\bSignifikant\b',
    ],
    Language.FRENCH: [
        r'\bet\b', r'\bles\b', r'\bdes\b', r'\bune?\b', r'\bétait\b',
        r'\bpatients?\b', r'\bétude\b', r'\btraitement\b',
        r'\bintervalle\s+de\s+confiance\b', r'\brapport\s+de\s+(?:risque|cotes)\b',
        r'\brisque\s+relatif\b', r'\bdifférence\s+moyenne\b',
        r'\brésultats?\b', r'\bsignificatif\b',
    ],
    Language.SPANISH: [
        r'\by\b', r'\blos\b', r'\blas\b', r'\buna?\b', r'\bfue\b',
        r'\bpacientes?\b', r'\bestudio\b', r'\btratamiento\b',
        r'\bintervalo\s+de\s+confianza\b', r'\brazón\s+de\s+(?:riesgo|momios)\b',
        r'\briesgo\s+relativo\b', r'\bdiferencia\s+de\s+medias\b',
        r'\bresultados?\b', r'\bsignificativo\b',
    ],
    Language.ITALIAN: [
        r'\be\b', r'\bgli\b', r'\ble\b', r'\buna?\b', r'\bera\b',
        r'\bpazienti?\b', r'\bstudio\b', r'\btrattamento\b',
        r'\bintervallo\s+di\s+confidenza\b', r'\brapporto\s+di\s+rischio\b',
        r'\brischio\s+relativo\b', r'\bdifferenza\s+media\b',
        r'\brisultati?\b', r'\bsignificativo\b',
    ],
    Language.PORTUGUESE: [
        r'\be\b', r'\bos\b', r'\bas\b', r'\buma?\b', r'\bfoi\b',
        r'\bpacientes?\b', r'\bestudo\b', r'\btratamento\b',
        r'\bintervalo\s+de\s+confiança\b', r'\brazão\s+de\s+(?:risco|chances)\b',
        r'\brisco\s+relativo\b', r'\bdiferença\s+média\b',
        r'\bresultados?\b', r'\bsignificativo\b',
    ],
    Language.CHINESE: [
        r'[\u4e00-\u9fff]',  # Chinese characters
        r'风险比', r'比值比', r'相对危险度', r'均数差',
        r'置信区间', r'患者', r'研究', r'治疗',
    ],
    Language.JAPANESE: [
        r'[\u3040-\u309f\u30a0-\u30ff]',  # Hiragana and Katakana
        r'ハザード比', r'オッズ比', r'相対危険',
        r'信頼区間', r'患者', r'研究', r'治療',
    ],
    Language.KOREAN: [
        r'[\uac00-\ud7af]',  # Korean Hangul
        r'위험비', r'교차비', r'상대위험도',
        r'신뢰구간', r'환자', r'연구', r'치료',
    ],
}


# Language-specific effect patterns
LANGUAGE_PATTERNS = {
    Language.GERMAN: {
        'HR': [
            r'[Hh]azard[-\s]?[Rr]atio\s+(\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?(?:KI|Konfidenzintervall)[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
            r'\bHR\b\s+(\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?KI[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'OR': [
            r'[Oo]dds[-\s]?[Rr]atio\s+(\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?(?:KI|Konfidenzintervall)[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
            r'\bOR\b\s+(\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?KI[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'RR': [
            r'[Rr]elatives?\s+[Rr]isiko\s+(\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?(?:KI|Konfidenzintervall)[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
            r'\bRR\b\s+(\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?KI[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'MD': [
            r'[Mm]ittlere\s+[Dd]ifferenz\s+(-?\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?(?:KI)[:\s]*(-?\d+[,.]?\d*)\s*[-–—]\s*(-?\d+[,.]?\d*)',
            r'\bMD\b\s+(-?\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?KI[:\s]*(-?\d+[,.]?\d*)\s*[-–—]\s*(-?\d+[,.]?\d*)',
        ],
        'CI_LABEL': 'KI',
    },
    Language.FRENCH: {
        'HR': [
            r'[Rr]apport\s+de\s+risque\s+(\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
            r'\bHR\b\s+(\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?IC[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'OR': [
            r'[Rr]apport\s+de\s+cotes?\s+(\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
            r'\bOR\b\s+(\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?IC[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'RR': [
            r'[Rr]isque\s+relatif\s+(\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
            r'\bRR\b\s+(\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?IC[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'MD': [
            r'[Dd]ifférence\s+moyenne\s+(-?\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(-?\d+[,.]?\d*)\s*[-–—]\s*(-?\d+[,.]?\d*)',
            r'\bDM\b\s+(-?\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?IC[:\s]*(-?\d+[,.]?\d*)\s*[-–—]\s*(-?\d+[,.]?\d*)',
        ],
        'CI_LABEL': 'IC',
    },
    Language.SPANISH: {
        'HR': [
            r'[Rr]azón\s+de\s+riesgo\s+(\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
            r'\bHR\b\s+(\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?IC[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'OR': [
            r'[Rr]azón\s+de\s+momios\s+(\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
            r'\bOR\b\s+(\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?IC[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'RR': [
            r'[Rr]iesgo\s+relativo\s+(\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
            r'\bRR\b\s+(\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?IC[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'MD': [
            r'[Dd]iferencia\s+de\s+medias\s+(-?\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(-?\d+[,.]?\d*)\s*[-–—]\s*(-?\d+[,.]?\d*)',
            r'\bDM\b\s+(-?\d+[,.]?\d*)\s*\(\s*(?:95%?[\s-]*)?IC[:\s]*(-?\d+[,.]?\d*)\s*[-–—]\s*(-?\d+[,.]?\d*)',
        ],
        'CI_LABEL': 'IC',
    },
    Language.ITALIAN: {
        'HR': [
            r'[Rr]apporto\s+di\s+rischio\s+(\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'OR': [
            r'[Rr]apporto\s+di\s+probabilità\s+(\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'RR': [
            r'[Rr]ischio\s+relativo\s+(\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'MD': [
            r'[Dd]ifferenza\s+media\s+(-?\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(-?\d+[,.]?\d*)\s*[-–—]\s*(-?\d+[,.]?\d*)',
        ],
        'CI_LABEL': 'IC',
    },
    Language.PORTUGUESE: {
        'HR': [
            r'[Rr]azão\s+de\s+risco\s+(\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'OR': [
            r'[Rr]azão\s+de\s+chances\s+(\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'RR': [
            r'[Rr]isco\s+relativo\s+(\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[,.]?\d*)\s*[-–—]\s*(\d+[,.]?\d*)',
        ],
        'MD': [
            r'[Dd]iferença\s+média\s+(-?\d+[,.]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(-?\d+[,.]?\d*)\s*[-–—]\s*(-?\d+[,.]?\d*)',
        ],
        'CI_LABEL': 'IC',
    },
}

# OCR language configuration for Tesseract
OCR_LANG_CONFIG = {
    'en': 'eng',
    'de': 'deu+eng',
    'fr': 'fra+eng',
    'es': 'spa+eng',
    'it': 'ita+eng',
    'pt': 'por+eng',
    'zh': 'chi_sim+eng',
    'ja': 'jpn+eng',
    'ko': 'kor+eng',
    'multi': 'eng+deu+fra+spa+ita+por',
}


def detect_language(text: str) -> LanguageDetection:
    """
    Detect the primary language of the text.

    Args:
        text: Input text to analyze

    Returns:
        LanguageDetection with detected language and confidence
    """
    scores = {}
    indicators_found = {}

    text_lower = text.lower()

    for lang, patterns in LANGUAGE_INDICATORS.items():
        count = 0
        found = []
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                count += len(matches)
                found.append(pattern)
        scores[lang] = count
        indicators_found[lang] = found

    # Find the language with highest score
    if not scores or max(scores.values()) == 0:
        return LanguageDetection(
            language=Language.ENGLISH,  # Default to English
            confidence=0.5,
            indicators=[]
        )

    best_lang = max(scores, key=scores.get)
    total_indicators = sum(scores.values())
    confidence = scores[best_lang] / total_indicators if total_indicators > 0 else 0

    # Boost confidence if we found many indicators
    if scores[best_lang] >= 10:
        confidence = min(confidence + 0.2, 1.0)

    return LanguageDetection(
        language=best_lang,
        confidence=confidence,
        indicators=indicators_found.get(best_lang, [])
    )


def normalize_european_decimals(text: str) -> str:
    """
    Convert European decimal format (comma) to standard (period).
    Only converts when clearly a decimal (digit,digit pattern).

    Args:
        text: Input text

    Returns:
        Text with normalized decimals
    """
    # Pattern: digit(s), digit(s) where it's clearly a decimal
    # E.g., "0,74" -> "0.74", "1,25" -> "1.25"
    return re.sub(r'(\d),(\d)', r'\1.\2', text)


@dataclass
class MultiLangExtraction:
    """Extraction result with language information"""
    effect_type: str
    point_estimate: float
    ci_lower: Optional[float]
    ci_upper: Optional[float]
    source_text: str
    language: Language
    pattern_used: str


class MultiLangExtractor:
    """
    Multi-language effect estimate extractor.

    Supports extraction from German, French, Spanish, Italian,
    Portuguese, Chinese, Japanese, and Korean texts.
    """

    def __init__(self):
        self.language_patterns = LANGUAGE_PATTERNS
        self.ocr_config = OCR_LANG_CONFIG

    def extract(
        self,
        text: str,
        language: str = 'auto'
    ) -> List[MultiLangExtraction]:
        """
        Extract effect estimates from text in any supported language.

        Args:
            text: Input text
            language: Language code ('auto', 'en', 'de', 'fr', 'es', 'it', 'pt')
                     'auto' will detect the language automatically

        Returns:
            List of MultiLangExtraction objects
        """
        # Detect language if auto
        if language == 'auto':
            detection = detect_language(text)
            detected_lang = detection.language
        else:
            lang_map = {
                'en': Language.ENGLISH,
                'de': Language.GERMAN,
                'fr': Language.FRENCH,
                'es': Language.SPANISH,
                'it': Language.ITALIAN,
                'pt': Language.PORTUGUESE,
                'zh': Language.CHINESE,
                'ja': Language.JAPANESE,
                'ko': Language.KOREAN,
            }
            detected_lang = lang_map.get(language, Language.ENGLISH)

        # Normalize European decimals
        normalized_text = normalize_european_decimals(text)

        results = []
        seen = set()

        # Get language-specific patterns
        if detected_lang in self.language_patterns:
            lang_patterns = self.language_patterns[detected_lang]

            for effect_type, patterns in lang_patterns.items():
                if effect_type == 'CI_LABEL':
                    continue

                for pattern in patterns:
                    for match in re.finditer(pattern, normalized_text, re.IGNORECASE):
                        groups = match.groups()

                        if len(groups) >= 1:
                            try:
                                value = float(groups[0].replace(',', '.'))
                                ci_lower = float(groups[1].replace(',', '.')) if len(groups) > 1 else None
                                ci_upper = float(groups[2].replace(',', '.')) if len(groups) > 2 else None

                                # Create unique key to avoid duplicates
                                key = (effect_type, round(value, 3), round(ci_lower or 0, 3), round(ci_upper or 0, 3))

                                if key not in seen:
                                    seen.add(key)
                                    results.append(MultiLangExtraction(
                                        effect_type=effect_type,
                                        point_estimate=value,
                                        ci_lower=ci_lower,
                                        ci_upper=ci_upper,
                                        source_text=match.group(0),
                                        language=detected_lang,
                                        pattern_used=pattern
                                    ))
                            except (ValueError, IndexError):
                                continue

        return results

    def get_ocr_config(self, language: str = 'auto', text: str = '') -> str:
        """
        Get Tesseract OCR language configuration.

        Args:
            language: Language code or 'auto'
            text: Text sample for auto-detection

        Returns:
            Tesseract language string (e.g., 'deu+eng')
        """
        if language == 'auto' and text:
            detection = detect_language(text)
            lang_code = detection.language.value
        else:
            lang_code = language if language != 'auto' else 'en'

        return self.ocr_config.get(lang_code, 'eng')

    def get_ci_label(self, language: Language) -> str:
        """
        Get the confidence interval label for a language.

        Args:
            language: Language enum

        Returns:
            CI label (e.g., 'CI', 'KI', 'IC')
        """
        if language in self.language_patterns:
            return self.language_patterns[language].get('CI_LABEL', 'CI')
        return 'CI'


# Convenience function
def extract_multilang(text: str, language: str = 'auto') -> List[MultiLangExtraction]:
    """
    Convenience function to extract effects from multi-language text.

    Args:
        text: Input text
        language: Language code ('auto', 'en', 'de', 'fr', 'es', 'it', 'pt')

    Returns:
        List of extractions
    """
    extractor = MultiLangExtractor()
    return extractor.extract(text, language)
