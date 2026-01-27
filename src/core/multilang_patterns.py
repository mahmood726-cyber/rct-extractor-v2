"""
Multi-Language Pattern Support for RCT Extractor v2
====================================================

Provides regex patterns for extracting effect estimates (HR, OR, RR, RD, MD)
from clinical trial publications in multiple languages.

Supported Languages:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Chinese (zh) - simplified patterns
- Japanese (ja) - simplified patterns

Author: RCT Extractor v2 Team
Version: 1.0.0
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class LanguagePatterns:
    """Patterns for a specific language"""
    language_code: str
    language_name: str
    hr_patterns: List[str]
    or_patterns: List[str]
    rr_patterns: List[str]
    rd_patterns: List[str]
    md_patterns: List[str]
    ci_patterns: List[str]
    rejection_patterns: List[str]


# Common numeric pattern components - handles negative numbers too
NUM = r'(-?\d+\.?\d*)'
# CI separator - includes dash, en-dash, em-dash, "to", "a" (Spanish/Portuguese/French), "bis" (German)
CI_SEP = r'\s*(?:[-–—]|to|a|bis)\s*'
CI_COMMA = r'\s*[,;]\s*'

# Optional CI prefix patterns for different languages
CI_PREFIX_EN = r'(?:95%?\s*CI[,:\s]*)?'
CI_PREFIX_ES = r'(?:IC\s*(?:del?\s*)?95%?[,:\s]*)?'
CI_PREFIX_FR = r'(?:IC\s*(?:[aà]\s*)?95%?[,:\s]*)?'
CI_PREFIX_DE = r'(?:(?:95%?[-\s]?KI|KI\s*(?:von\s*)?95%?)[,:\s]*)?'
CI_PREFIX_IT = r'(?:IC\s*(?:al\s*)?95%?[,:\s]*)?'
CI_PREFIX_PT = r'(?:IC\s*(?:de\s*)?95%?[,:\s]*)?'
CI_PREFIX_ZH = r'(?:95%?\s*(?:CI|可信区间|置信区间)[,:\s]*)?'
CI_PREFIX_JA = r'(?:95%?\s*(?:CI|信頼区間)[,:\s]*)?'


def make_patterns(term: str, ci_prefix: str = CI_PREFIX_EN) -> List[str]:
    """Generate flexible patterns for a measure term"""
    return [
        # term: value (CI: low-high) or term: value (low-high)
        rf'{term}[,:\s]+{NUM}\s*\(\s*{ci_prefix}{NUM}{CI_SEP}{NUM}\s*\)',
        # term: value [low, high]
        rf'{term}[,:\s]+{NUM}\s*\[\s*{ci_prefix}{NUM}{CI_COMMA}{NUM}\s*\]',
        # term was/is value (CI: low-high)
        rf'{term}\s+(?:fue|was|war|era|foi|etait|ist)\s+(?:de\s+)?{NUM}\s*\(\s*{ci_prefix}{NUM}{CI_SEP}{NUM}\s*\)',
    ]


LANGUAGE_PATTERNS: Dict[str, LanguagePatterns] = {

    # English patterns (reference)
    'en': LanguagePatterns(
        language_code='en',
        language_name='English',
        hr_patterns=[
            rf'hazard\s*ratio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'hazard\s*ratio\s+(?:was|of)\s+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'HR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'HR[,:\s=]+{NUM}\s*\[\s*{NUM}{CI_COMMA}{NUM}\s*\]',
        ],
        or_patterns=[
            rf'odds\s*ratio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'odds\s*ratio\s+(?:was|of)\s+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'OR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rr_patterns=[
            rf'relative\s*risk[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'risk\s*ratio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'RR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rd_patterns=[
            rf'risk\s*difference[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'absolute\s*risk\s*(?:reduction|difference)[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'RD[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        md_patterns=[
            rf'mean\s*difference[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'difference\s*(?:in\s*)?means?[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'MD[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_EN}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        ci_patterns=[
            r'95%?\s*CI',
            r'95%?\s*confidence\s*interval',
            r'\(95%?\s*CI[,:\s]',
        ],
        rejection_patterns=[
            r'\(SD\s', r'\(SE\s', r'\(IQR\s', r'\(SEM\s',
            r'SD\s*[=:]\s*\d', r'\bSD\s+\d',
        ],
    ),

    # Spanish patterns
    'es': LanguagePatterns(
        language_code='es',
        language_name='Spanish',
        hr_patterns=[
            rf'raz[oó]n\s*de\s*riesgo[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'raz[oó]n\s*de\s*riesgo\s+fue\s+(?:de\s+)?{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'hazard\s*ratio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'HR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        or_patterns=[
            rf'raz[oó]n\s*de\s*(?:posibilidades|momios)[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'odds\s*ratio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'odds\s*ratio\s+fue\s+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'OR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rr_patterns=[
            rf'riesgo\s*relativo[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'RR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rd_patterns=[
            rf'diferencia\s*de\s*riesgo[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'reducci[oó]n\s*absoluta\s*(?:del\s*)?riesgo[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        md_patterns=[
            rf'diferencia\s*de\s*medias[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'diferencia\s*de\s*medias\s+fue\s+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
            # With optional unit between value and CI
            rf'diferencia\s*de\s*medias\s+fue\s+{NUM}\s*(?:kg|mm|cm|ml|mg|%|mmHg)?\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'diferencia\s*media[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_ES}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        ci_patterns=[
            r'IC\s*(?:del?\s*)?95%?',
            r'intervalo\s*de\s*confianza\s*(?:del?\s*)?95%?',
        ],
        rejection_patterns=[
            r'\(DE\s', r'\(EE\s', r'\(RIC\s',
            r'DE\s*[=:]\s*\d',
        ],
    ),

    # French patterns
    'fr': LanguagePatterns(
        language_code='fr',
        language_name='French',
        hr_patterns=[
            rf'rapport\s*(?:de\s*)?(?:risque|hasard)[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'rapport\s*(?:de\s*)?(?:risque|hasard)\s+[eé]tait\s+(?:de\s+)?{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'hazard\s*ratio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'HR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        or_patterns=[
            rf'rapport\s*(?:de\s*)?(?:cotes|chances)[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'rapport\s*(?:de\s*)?(?:cotes|chances)\s+[eé]tait\s+{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'odds\s*ratio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'OR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rr_patterns=[
            rf'risque\s*relatif[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'RR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rd_patterns=[
            rf'diff[eé]rence\s*(?:de\s*)?risque[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'r[eé]duction\s*absolue\s*(?:du\s*)?risque[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        md_patterns=[
            rf'diff[eé]rence\s*(?:de\s*)?moyennes?[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'diff[eé]rence\s*moyenne[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_FR}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        ci_patterns=[
            r'IC\s*(?:[aà]\s*)?95%?',
            r'intervalle\s*de\s*confiance\s*(?:[aà]\s*)?95%?',
        ],
        rejection_patterns=[
            r'\([EÉ]T\s', r'\(ES\s', r'\(EIQ\s',
            r'[EÉ]T\s*[=:]\s*\d',
        ],
    ),

    # German patterns
    'de': LanguagePatterns(
        language_code='de',
        language_name='German',
        hr_patterns=[
            rf'Hazard[-\s]?Ratio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'Hazard[-\s]?Ratio\s+betrug\s+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'Gef[aä]hrdungsverh[aä]ltnis[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'HR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        or_patterns=[
            rf'Odds[-\s]?Ratio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'Chancenverh[aä]ltnis[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'OR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rr_patterns=[
            rf'relatives?\s*Risiko[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'relatives?\s*Risiko\s+war\s+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'Risikoverh[aä]ltnis[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'RR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rd_patterns=[
            rf'Risikodifferenz[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'absolute\s*Risikoreduktion[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        md_patterns=[
            rf'Mittelwertdifferenz[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'mittlere\s*Differenz[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_DE}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        ci_patterns=[
            r'95%?[-\s]?KI',
            r'Konfidenzintervall\s*(?:von\s*)?95%?',
        ],
        rejection_patterns=[
            r'\(SD\s', r'\(SA\s', r'\(SE\s', r'\(IQR\s',
            r'SD\s*[=:]\s*\d', r'SA\s*[=:]\s*\d',
        ],
    ),

    # Italian patterns
    'it': LanguagePatterns(
        language_code='it',
        language_name='Italian',
        hr_patterns=[
            rf'rapporto\s*(?:di\s*)?rischio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_IT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'rapporto\s*(?:di\s*)?rischio\s+era\s+(?:di\s+)?{NUM}\s*\(\s*{CI_PREFIX_IT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'hazard\s*ratio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_IT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'HR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_IT}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        or_patterns=[
            rf'odds\s*ratio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_IT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'rapporto\s*(?:di\s*)?(?:probabilit[aà]|quote)[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_IT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'OR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_IT}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rr_patterns=[
            rf'rischio\s*relativo[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_IT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'RR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_IT}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rd_patterns=[
            rf'differenza\s*(?:di\s*)?rischio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_IT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'riduzione\s*assoluta\s*(?:del\s*)?rischio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_IT}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        md_patterns=[
            rf'differenza\s*(?:delle?\s*)?medie[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_IT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'differenza\s*media[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_IT}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        ci_patterns=[
            r'IC\s*(?:al\s*)?95%?',
            r'intervallo\s*di\s*confidenza\s*(?:al\s*)?95%?',
        ],
        rejection_patterns=[
            r'\(DS\s', r'\(ES\s', r'\(IQR\s',
            r'DS\s*[=:]\s*\d',
        ],
    ),

    # Portuguese patterns
    'pt': LanguagePatterns(
        language_code='pt',
        language_name='Portuguese',
        hr_patterns=[
            rf'raz[aã]o\s*de\s*risco[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_PT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'raz[aã]o\s*de\s*risco\s+foi\s+(?:de\s+)?{NUM}\s*\(\s*{CI_PREFIX_PT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'hazard\s*ratio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_PT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'HR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_PT}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        or_patterns=[
            rf'raz[aã]o\s*(?:de\s*)?(?:chances|possibilidades)[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_PT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'odds\s*ratio[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_PT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'OR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_PT}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rr_patterns=[
            rf'risco\s*relativo[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_PT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'RR[,:\s=]+{NUM}\s*\(\s*{CI_PREFIX_PT}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rd_patterns=[
            rf'diferen[cç]a\s*(?:de\s*)?risco[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_PT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'redu[cç][aã]o\s*absoluta\s*(?:do\s*)?risco[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_PT}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        md_patterns=[
            rf'diferen[cç]a\s*(?:de\s*)?m[eé]dias[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_PT}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'diferen[cç]a\s*m[eé]dia[,:\s]+{NUM}\s*\(\s*{CI_PREFIX_PT}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        ci_patterns=[
            r'IC\s*(?:de\s*)?95%?',
            r'intervalo\s*de\s*confian[cç]a\s*(?:de\s*)?95%?',
        ],
        rejection_patterns=[
            r'\(DP\s', r'\(EP\s', r'\(IIQ\s',
            r'DP\s*[=:]\s*\d',
        ],
    ),

    # Chinese patterns (simplified - using common terms)
    'zh': LanguagePatterns(
        language_code='zh',
        language_name='Chinese',
        hr_patterns=[
            rf'风险比[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'危险比[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'风险比为{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'HR[,:\s=]*{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        or_patterns=[
            rf'比值比[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'优势比[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'OR[,:\s=]*{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rr_patterns=[
            rf'相对危险度[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'相对风险[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'RR[,:\s=]*{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rd_patterns=[
            rf'风险差[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'绝对风险降低[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        md_patterns=[
            rf'均数差[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'平均差[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_ZH}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        ci_patterns=[
            r'95%?\s*CI',
            r'95%?\s*可信区间',
            r'95%?\s*置信区间',
        ],
        rejection_patterns=[
            r'\(标准差\s', r'\(标准误\s',
            r'SD\s*[=:]\s*\d',
        ],
    ),

    # Japanese patterns (simplified)
    'ja': LanguagePatterns(
        language_code='ja',
        language_name='Japanese',
        hr_patterns=[
            rf'ハザード比[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_JA}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'ハザード比は{NUM}\s*\(\s*{CI_PREFIX_JA}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'危険率比[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_JA}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'HR[,:\s=]*{NUM}\s*\(\s*{CI_PREFIX_JA}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        or_patterns=[
            rf'オッズ比[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_JA}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'OR[,:\s=]*{NUM}\s*\(\s*{CI_PREFIX_JA}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rr_patterns=[
            rf'相対リスク[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_JA}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'相対危険度[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_JA}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'RR[,:\s=]*{NUM}\s*\(\s*{CI_PREFIX_JA}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        rd_patterns=[
            rf'リスク差[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_JA}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'絶対リスク減少[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_JA}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        md_patterns=[
            rf'平均差[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_JA}{NUM}{CI_SEP}{NUM}\s*\)',
            rf'平均値の差[,:\s]*{NUM}\s*\(\s*{CI_PREFIX_JA}{NUM}{CI_SEP}{NUM}\s*\)',
        ],
        ci_patterns=[
            r'95%?\s*CI',
            r'95%?\s*信頼区間',
        ],
        rejection_patterns=[
            r'\(標準偏差\s', r'\(標準誤差\s',
            r'SD\s*[=:]\s*\d',
        ],
    ),
}


class MultiLanguageExtractor:
    """
    Extracts effect estimates from text in multiple languages.

    Usage:
        extractor = MultiLanguageExtractor()
        result = extractor.extract_hazard_ratio(text)
        # or with specific language
        result = extractor.extract_hazard_ratio(text, language='es')
    """

    def __init__(self, languages: Optional[List[str]] = None):
        """
        Initialize extractor with specified languages.

        Args:
            languages: List of language codes. If None, uses all languages.
        """
        if languages is None:
            self.languages = list(LANGUAGE_PATTERNS.keys())
        else:
            self.languages = [l for l in languages if l in LANGUAGE_PATTERNS]

    def detect_language(self, text: str) -> str:
        """
        Attempt to detect language from CI pattern usage.

        Returns:
            Language code or 'en' as default
        """
        text_lower = text.lower()

        # Check for language-specific CI patterns
        for lang_code, patterns in LANGUAGE_PATTERNS.items():
            for ci_pattern in patterns.ci_patterns:
                if re.search(ci_pattern, text_lower):
                    # Spanish/Portuguese/Italian/French use IC
                    if 'IC' in ci_pattern and lang_code in ['es', 'pt', 'it', 'fr']:
                        return lang_code
                    # German uses KI
                    elif 'KI' in ci_pattern and lang_code == 'de':
                        return lang_code
                    # Chinese uses specific characters
                    elif '可信区间' in ci_pattern or '置信区间' in ci_pattern:
                        return 'zh'
                    # Japanese
                    elif '信頼区間' in ci_pattern:
                        return 'ja'

        return 'en'  # Default to English

    def _should_reject(self, text: str, language: str) -> bool:
        """Check if text matches rejection patterns (SD, SE, etc.)"""
        patterns = LANGUAGE_PATTERNS.get(language, LANGUAGE_PATTERNS['en'])
        for pattern in patterns.rejection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def extract_hazard_ratio(
        self,
        text: str,
        language: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Extract hazard ratio from text.

        Args:
            text: Input text
            language: Optional language code. If None, tries all languages.

        Returns:
            Dict with 'hr', 'ci_low', 'ci_high', 'language' or None
        """
        languages_to_try = [language] if language else self.languages

        for lang in languages_to_try:
            if lang not in LANGUAGE_PATTERNS:
                continue

            if self._should_reject(text, lang):
                continue

            patterns = LANGUAGE_PATTERNS[lang]

            for pattern in patterns.hr_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        return {
                            'hr': float(match.group(1)),
                            'ci_low': float(match.group(2)),
                            'ci_high': float(match.group(3)),
                            'language': lang
                        }
                    except (ValueError, IndexError):
                        continue

        return None

    def extract_odds_ratio(
        self,
        text: str,
        language: Optional[str] = None
    ) -> Optional[Dict]:
        """Extract odds ratio from text."""
        languages_to_try = [language] if language else self.languages

        for lang in languages_to_try:
            if lang not in LANGUAGE_PATTERNS:
                continue

            if self._should_reject(text, lang):
                continue

            patterns = LANGUAGE_PATTERNS[lang]

            for pattern in patterns.or_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        return {
                            'or': float(match.group(1)),
                            'ci_low': float(match.group(2)),
                            'ci_high': float(match.group(3)),
                            'language': lang
                        }
                    except (ValueError, IndexError):
                        continue

        return None

    def extract_relative_risk(
        self,
        text: str,
        language: Optional[str] = None
    ) -> Optional[Dict]:
        """Extract relative risk from text."""
        languages_to_try = [language] if language else self.languages

        for lang in languages_to_try:
            if lang not in LANGUAGE_PATTERNS:
                continue

            if self._should_reject(text, lang):
                continue

            patterns = LANGUAGE_PATTERNS[lang]

            for pattern in patterns.rr_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        return {
                            'rr': float(match.group(1)),
                            'ci_low': float(match.group(2)),
                            'ci_high': float(match.group(3)),
                            'language': lang
                        }
                    except (ValueError, IndexError):
                        continue

        return None

    def extract_risk_difference(
        self,
        text: str,
        language: Optional[str] = None
    ) -> Optional[Dict]:
        """Extract risk difference from text."""
        languages_to_try = [language] if language else self.languages

        for lang in languages_to_try:
            if lang not in LANGUAGE_PATTERNS:
                continue

            if self._should_reject(text, lang):
                continue

            patterns = LANGUAGE_PATTERNS[lang]

            for pattern in patterns.rd_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        return {
                            'rd': float(match.group(1)),
                            'ci_low': float(match.group(2)),
                            'ci_high': float(match.group(3)),
                            'language': lang
                        }
                    except (ValueError, IndexError):
                        continue

        return None

    def extract_mean_difference(
        self,
        text: str,
        language: Optional[str] = None
    ) -> Optional[Dict]:
        """Extract mean difference from text."""
        languages_to_try = [language] if language else self.languages

        for lang in languages_to_try:
            if lang not in LANGUAGE_PATTERNS:
                continue

            if self._should_reject(text, lang):
                continue

            patterns = LANGUAGE_PATTERNS[lang]

            for pattern in patterns.md_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        return {
                            'md': float(match.group(1)),
                            'ci_low': float(match.group(2)),
                            'ci_high': float(match.group(3)),
                            'language': lang
                        }
                    except (ValueError, IndexError):
                        continue

        return None

    def extract_all(
        self,
        text: str,
        language: Optional[str] = None
    ) -> Dict[str, Optional[Dict]]:
        """
        Extract all measure types from text.

        Returns:
            Dict with keys 'hr', 'or', 'rr', 'rd', 'md' containing results or None
        """
        return {
            'hr': self.extract_hazard_ratio(text, language),
            'or': self.extract_odds_ratio(text, language),
            'rr': self.extract_relative_risk(text, language),
            'rd': self.extract_risk_difference(text, language),
            'md': self.extract_mean_difference(text, language),
        }


def get_supported_languages() -> List[str]:
    """Return list of supported language codes."""
    return list(LANGUAGE_PATTERNS.keys())


def get_language_name(code: str) -> str:
    """Return full language name for code."""
    if code in LANGUAGE_PATTERNS:
        return LANGUAGE_PATTERNS[code].language_name
    return "Unknown"


# Convenience function for single extraction
def extract_effect_estimate(
    text: str,
    measure_type: str = 'HR',
    language: Optional[str] = None
) -> Optional[Dict]:
    """
    Extract a specific effect estimate type from text.

    Args:
        text: Input text
        measure_type: One of 'HR', 'OR', 'RR', 'RD', 'MD'
        language: Optional language code

    Returns:
        Dict with value and CI or None
    """
    extractor = MultiLanguageExtractor()

    if measure_type == 'HR':
        return extractor.extract_hazard_ratio(text, language)
    elif measure_type == 'OR':
        return extractor.extract_odds_ratio(text, language)
    elif measure_type == 'RR':
        return extractor.extract_relative_risk(text, language)
    elif measure_type == 'RD':
        return extractor.extract_risk_difference(text, language)
    elif measure_type == 'MD':
        return extractor.extract_mean_difference(text, language)

    return None
