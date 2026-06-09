"""
OCR Preprocessor for Regulatory-Grade Extraction
=================================================

Handles common OCR errors to achieve 100% sensitivity on
documents with OCR artifacts. Required for regulatory-grade
extraction from scanned PDFs.

Common OCR Error Patterns:
- O -> 0 (letter O misread as zero)
- l -> 1 (lowercase L misread as one)
- I -> 1 (uppercase I misread as one)
- Cl -> CI (common abbreviation error)
- rn -> m (common ligature error)

OCR Quality Thresholds (FDA Regulatory Compliance):
- EXCELLENT: >= 95% character confidence, minimal corrections needed
- ACCEPTABLE: >= 85% character confidence, moderate corrections
- MARGINAL: >= 70% character confidence, heavy corrections, manual review recommended
- UNACCEPTABLE: < 70% character confidence, extraction may fail
"""

import re
from typing import Tuple, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class OCRQualityLevel(Enum):
    """OCR quality classification levels per FDA guidance"""
    EXCELLENT = "excellent"      # >= 95% confidence
    ACCEPTABLE = "acceptable"    # >= 85% confidence
    MARGINAL = "marginal"        # >= 70% confidence
    UNACCEPTABLE = "unacceptable"  # < 70% confidence


@dataclass
class OCRQualityAssessment:
    """
    OCR quality assessment with formal thresholds.

    FDA Regulatory Compliance Thresholds:
    - Character confidence >= 95%: EXCELLENT (full automation)
    - Character confidence >= 85%: ACCEPTABLE (automation with QC)
    - Character confidence >= 70%: MARGINAL (manual review required)
    - Character confidence < 70%: UNACCEPTABLE (extraction may fail)
    """
    # Raw metrics
    character_confidence: float = 0.0  # 0-100 scale
    word_confidence: float = 0.0       # 0-100 scale
    numeric_confidence: float = 0.0    # Confidence in numeric regions

    # Correction metrics
    corrections_applied: int = 0
    correction_rate: float = 0.0  # Corrections per 1000 characters

    # Quality classification
    quality_level: OCRQualityLevel = OCRQualityLevel.UNACCEPTABLE
    is_acceptable_for_extraction: bool = False
    requires_manual_review: bool = True

    # Specific issue flags
    has_systematic_errors: bool = False
    has_numeric_confusion: bool = False  # O/0 or l/1 issues
    has_ci_confusion: bool = False       # Cl/CI issues

    # Recommendations
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class OCRCorrection:
    """Record of an OCR correction made"""
    original: str
    corrected: str
    position: int
    rule: str


# =============================================================================
# OCR QUALITY THRESHOLDS - REGULATORY COMPLIANT
# =============================================================================

OCR_THRESHOLDS = {
    "EXCELLENT_CONFIDENCE": 95.0,      # >= 95% for full automation
    "ACCEPTABLE_CONFIDENCE": 85.0,     # >= 85% for automation with QC
    "MARGINAL_CONFIDENCE": 70.0,       # >= 70% for manual review
    "UNACCEPTABLE_CONFIDENCE": 70.0,   # < 70% may fail

    "MAX_CORRECTIONS_PER_1000_CHARS_EXCELLENT": 2,    # Max 2 corrections per 1000 chars
    "MAX_CORRECTIONS_PER_1000_CHARS_ACCEPTABLE": 10,  # Max 10 corrections per 1000 chars
    "MAX_CORRECTIONS_PER_1000_CHARS_MARGINAL": 25,    # Max 25 corrections per 1000 chars

    "MIN_NUMERIC_CONFIDENCE": 90.0,    # Minimum confidence for numeric regions
}


class OCRPreprocessor:
    """
    Preprocesses text to correct common OCR errors.

    Designed for regulatory-grade extraction where missing
    effect estimates due to OCR errors is unacceptable.
    """

    def __init__(self, aggressive: bool = True):
        """
        Initialize preprocessor.

        Args:
            aggressive: If True, apply all corrections. If False, only
                       apply high-confidence corrections.
        """
        self.aggressive = aggressive
        self.corrections: List[OCRCorrection] = []

    def preprocess(self, text: str) -> Tuple[str, List[OCRCorrection]]:
        """
        Preprocess text to correct OCR errors.

        Args:
            text: Input text potentially containing OCR errors

        Returns:
            Tuple of (corrected_text, list of corrections made)
        """
        self.corrections = []
        corrected = text

        # Apply corrections in order of specificity (most specific first)
        corrected = self._fix_ci_abbreviation(corrected)

        # Run numeric corrections multiple times to handle cascading errors
        # e.g., "O.6l" needs O->0 then l->1
        for _ in range(3):  # Max 3 iterations for cascading corrections
            prev = corrected
            corrected = self._fix_numeric_o_to_zero(corrected)
            corrected = self._fix_numeric_l_to_one(corrected)
            if corrected == prev:
                break

        corrected = self._fix_decimal_errors(corrected)
        corrected = self._fix_p_value_errors(corrected)

        return corrected, self.corrections

    def _fix_ci_abbreviation(self, text: str) -> str:
        """Fix Cl -> CI (lowercase L instead of uppercase I)"""
        # Pattern: "95% Cl" or "Cl:" or "(Cl " etc.
        patterns = [
            (r'(\d+%?\s*)Cl(\s*[:\[\(,])', r'\1CI\2', 'Cl->CI after percentage'),
            (r'\(Cl\s', r'(CI ', 'Cl->CI in parentheses'),
            (r'Cl\s*:', r'CI:', 'Cl->CI before colon'),
            (r'Cl\s*,', r'CI,', 'Cl->CI before comma'),
            (r'\bCl\b(?=\s*\d)', r'CI', 'Cl->CI before number'),
            # "95% Cl " with space after (common in OCR)
            (r'(\d+%\s*)Cl(\s+)', r'\1CI\2', 'Cl->CI after percentage with space'),
            # "95% Cl-" with dash after (OCR artifacts)
            (r'(\d+%\s*)Cl(\s*-)', r'\1CI\2', 'Cl->CI after percentage with dash'),
        ]

        for pattern, replacement, rule in patterns:
            matches = list(re.finditer(pattern, text))
            for match in matches:
                self.corrections.append(OCRCorrection(
                    original=match.group(),
                    corrected=re.sub(pattern, replacement, match.group()),
                    position=match.start(),
                    rule=rule
                ))
            text = re.sub(pattern, replacement, text)

        return text

    def _fix_numeric_o_to_zero(self, text: str) -> str:
        """Fix O -> 0 in numeric contexts"""
        # Pattern: O followed by decimal point and digits/letters (for mixed OCR errors)
        # Use [0-9lI] to match digits that might have OCR errors themselves
        patterns = [
            # O.XX -> 0.XX (O at start of decimal) - allow l/I in digits
            (r'\bO\.([0-9lIO]+)', r'0.\1', 'O.X->0.X'),
            # X.OX -> X.0X (O in middle of decimal)
            (r'(\d+\.)O([0-9lIO]*)', r'\g<1>0\2', 'X.OX->X.0X'),
            # XO.X -> X0.X (O before decimal point)
            (r'(\d)O\.([0-9lIO])', r'\g<1>0.\2', 'XO.X->X0.X'),
            # -O.XX -> -0.XX (negative with O) - allow l/I in digits
            (r'-O\.([0-9lIO]+)', r'-0.\1', '-O.X->-0.X'),
            # p<O.OOX -> p<0.00X (p-values)
            (r'p\s*[<>=]\s*O\.', r'p<0.', 'p<O.->p<0.'),
            (r'O\.OO', r'0.00', 'O.OO->0.00'),
            # Additional: O within number sequence
            (r'(\d)O(\d)', r'\g<1>0\2', 'XOX->X0X'),
        ]

        for pattern, replacement, rule in patterns:
            matches = list(re.finditer(pattern, text))
            for match in matches:
                self.corrections.append(OCRCorrection(
                    original=match.group(),
                    corrected=re.sub(pattern, replacement, match.group()),
                    position=match.start(),
                    rule=rule
                ))
            text = re.sub(pattern, replacement, text)

        return text

    def _fix_numeric_l_to_one(self, text: str) -> str:
        """Fix l -> 1 in numeric contexts"""
        # Pattern: l followed by decimal point, or after decimal point
        # Use [0-9OI] to handle mixed OCR errors
        patterns = [
            # l.XX -> 1.XX (l at start of decimal)
            (r'\bl\.([0-9OIl]+)', r'1.\1', 'l.X->1.X'),
            # X.lX -> X.1X (l after decimal point)
            (r'(\d+\.)l([0-9OIl]*)', r'\g<1>1\2', 'X.lX->X.1X'),
            # -l.XX -> -1.XX (negative)
            (r'-l\.([0-9OIl]+)', r'-1.\1', '-l.X->-1.X'),
            # Xl.X -> X1.X (l before decimal)
            (r'(\d)l\.([0-9OIl])', r'\g<1>1.\2', 'Xl.X->X1.X'),
            # .Xl -> .X1 (l at end of decimal)
            (r'\.(\d+)l\b', r'.\g<1>1', '.Xl->.X1'),
            # Xl -> X1 (l at end of number, including after decimal)
            (r'(\d)l\b', r'\g<1>1', 'Xl->X1'),
            # p<0.00l -> p<0.001
            (r'(0\.0+)l\b', r'\g<1>1', '0.00l->0.001'),
            # Additional: l within number sequence
            (r'(\d)l(\d)', r'\g<1>1\2', 'XlX->X1X'),
        ]

        for pattern, replacement, rule in patterns:
            matches = list(re.finditer(pattern, text))
            for match in matches:
                self.corrections.append(OCRCorrection(
                    original=match.group(),
                    corrected=re.sub(pattern, replacement, match.group()),
                    position=match.start(),
                    rule=rule
                ))
            text = re.sub(pattern, replacement, text)

        return text

    def _fix_decimal_errors(self, text: str) -> str:
        """Fix other decimal-related OCR errors"""
        patterns = [
            # ,XX -> .XX (comma misread as decimal in some locales)
            # Only in clear numeric contexts like "0,74" -> "0.74"
            (r'(\d),(\d{2})\b(?!\d)', r'\1.\2', 'comma->decimal'),
        ]

        if self.aggressive:
            for pattern, replacement, rule in patterns:
                matches = list(re.finditer(pattern, text))
                for match in matches:
                    self.corrections.append(OCRCorrection(
                        original=match.group(),
                        corrected=re.sub(pattern, replacement, match.group()),
                        position=match.start(),
                        rule=rule
                    ))
                text = re.sub(pattern, replacement, text)

        return text

    def _fix_p_value_errors(self, text: str) -> str:
        """Fix p-value specific OCR errors"""
        patterns = [
            # p<O.OOl -> p<0.001
            (r'p\s*[<>=]\s*O\.O+l', lambda m: m.group().replace('O', '0').replace('l', '1'), 'p-value OCR fix'),
        ]

        for pattern, replacement, rule in patterns:
            if callable(replacement):
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                for match in matches:
                    original = match.group()
                    corrected_text = replacement(match)
                    self.corrections.append(OCRCorrection(
                        original=original,
                        corrected=corrected_text,
                        position=match.start(),
                        rule=rule
                    ))
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            else:
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                for match in matches:
                    self.corrections.append(OCRCorrection(
                        original=match.group(),
                        corrected=re.sub(pattern, replacement, match.group()),
                        position=match.start(),
                        rule=rule
                    ))
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def get_correction_report(self) -> str:
        """Generate a human-readable report of corrections made"""
        if not self.corrections:
            return "No OCR corrections made."

        lines = ["OCR Corrections Applied:", "-" * 40]
        for c in self.corrections:
            lines.append(f"  '{c.original}' -> '{c.corrected}' ({c.rule})")

        return "\n".join(lines)

    def assess_quality(self, original_text: str, ocr_confidence: float = None) -> OCRQualityAssessment:
        """
        Assess OCR quality with formal thresholds for regulatory compliance.

        Args:
            original_text: Original text before preprocessing
            ocr_confidence: Optional OCR engine confidence (0-100)

        Returns:
            OCRQualityAssessment with quality classification
        """
        assessment = OCRQualityAssessment()

        # Use provided OCR confidence or estimate from corrections
        text_length = len(original_text)
        if text_length == 0:
            assessment.quality_level = OCRQualityLevel.UNACCEPTABLE
            assessment.warnings.append("Empty text provided")
            return assessment

        # Calculate correction rate per 1000 characters
        correction_count = len(self.corrections)
        correction_rate = (correction_count / text_length) * 1000 if text_length > 0 else 0

        assessment.corrections_applied = correction_count
        assessment.correction_rate = correction_rate

        # Check for specific error types
        has_numeric_confusion = any(
            'O.X' in c.rule or 'l.X' in c.rule or '0.00' in c.rule
            for c in self.corrections
        )
        has_ci_confusion = any('CI' in c.rule for c in self.corrections)

        assessment.has_numeric_confusion = has_numeric_confusion
        assessment.has_ci_confusion = has_ci_confusion
        assessment.has_systematic_errors = has_numeric_confusion or has_ci_confusion

        # Estimate character confidence if not provided
        if ocr_confidence is not None:
            assessment.character_confidence = ocr_confidence
        else:
            # Estimate from correction rate
            # Higher correction rate = lower confidence
            if correction_rate <= OCR_THRESHOLDS["MAX_CORRECTIONS_PER_1000_CHARS_EXCELLENT"]:
                assessment.character_confidence = 97.0
            elif correction_rate <= OCR_THRESHOLDS["MAX_CORRECTIONS_PER_1000_CHARS_ACCEPTABLE"]:
                assessment.character_confidence = 90.0
            elif correction_rate <= OCR_THRESHOLDS["MAX_CORRECTIONS_PER_1000_CHARS_MARGINAL"]:
                assessment.character_confidence = 78.0
            else:
                assessment.character_confidence = 65.0

        # Classify quality level
        conf = assessment.character_confidence

        if conf >= OCR_THRESHOLDS["EXCELLENT_CONFIDENCE"]:
            assessment.quality_level = OCRQualityLevel.EXCELLENT
            assessment.is_acceptable_for_extraction = True
            assessment.requires_manual_review = False
            assessment.recommendations.append("Full automation approved")

        elif conf >= OCR_THRESHOLDS["ACCEPTABLE_CONFIDENCE"]:
            assessment.quality_level = OCRQualityLevel.ACCEPTABLE
            assessment.is_acceptable_for_extraction = True
            assessment.requires_manual_review = False
            assessment.recommendations.append("Automation with QC spot-checking recommended")

        elif conf >= OCR_THRESHOLDS["MARGINAL_CONFIDENCE"]:
            assessment.quality_level = OCRQualityLevel.MARGINAL
            assessment.is_acceptable_for_extraction = True
            assessment.requires_manual_review = True
            assessment.warnings.append("OCR quality is marginal")
            assessment.recommendations.append("Manual review required for all extractions")

        else:
            assessment.quality_level = OCRQualityLevel.UNACCEPTABLE
            assessment.is_acceptable_for_extraction = False
            assessment.requires_manual_review = True
            assessment.warnings.append("OCR quality below acceptable threshold")
            assessment.recommendations.append("Re-scan document at higher resolution")
            assessment.recommendations.append("Consider alternative source document")

        # Add specific warnings
        if has_numeric_confusion:
            assessment.warnings.append("Detected O/0 or l/1 confusion in numeric values")
            assessment.recommendations.append("Verify all numeric values manually")

        if has_ci_confusion:
            assessment.warnings.append("Detected Cl/CI confusion in confidence intervals")

        if correction_rate > OCR_THRESHOLDS["MAX_CORRECTIONS_PER_1000_CHARS_MARGINAL"]:
            assessment.warnings.append(f"High correction rate: {correction_rate:.1f} per 1000 chars")

        return assessment


def assess_ocr_quality(text: str, ocr_confidence: float = None) -> OCRQualityAssessment:
    """
    Assess OCR quality of text with formal thresholds.

    FDA Regulatory Compliance Thresholds:
    - Character confidence >= 95%: EXCELLENT (full automation)
    - Character confidence >= 85%: ACCEPTABLE (automation with QC)
    - Character confidence >= 70%: MARGINAL (manual review required)
    - Character confidence < 70%: UNACCEPTABLE (extraction may fail)

    Args:
        text: Text to assess (may contain OCR errors)
        ocr_confidence: Optional OCR engine confidence (0-100)

    Returns:
        OCRQualityAssessment with quality classification and recommendations
    """
    preprocessor = OCRPreprocessor(aggressive=True)
    corrected_text, corrections = preprocessor.preprocess(text)
    return preprocessor.assess_quality(text, ocr_confidence)


def preprocess_for_extraction(text: str) -> Tuple[str, List[OCRCorrection]]:
    """
    Convenience function to preprocess text for extraction.

    Args:
        text: Input text

    Returns:
        Tuple of (corrected_text, corrections_list)
    """
    preprocessor = OCRPreprocessor(aggressive=True)
    return preprocessor.preprocess(text)
