"""
Diagnostic Accuracy Extractor
=============================

Extracts diagnostic test accuracy measures from clinical text:
- Sensitivity (Se, Sn)
- Specificity (Sp)
- Positive Predictive Value (PPV)
- Negative Predictive Value (NPV)
- Positive Likelihood Ratio (LR+, PLR)
- Negative Likelihood Ratio (LR-, NLR)
- Diagnostic Odds Ratio (DOR)
- Area Under ROC Curve (AUC, AUROC, c-statistic)

Regulatory-grade extraction for FDA/EMA submissions.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


class DiagnosticMeasureType(Enum):
    """Supported diagnostic accuracy measure types"""
    SENSITIVITY = "Sensitivity"
    SPECIFICITY = "Specificity"
    PPV = "PPV"           # Positive Predictive Value
    NPV = "NPV"           # Negative Predictive Value
    PLR = "PLR"           # Positive Likelihood Ratio (LR+)
    NLR = "NLR"           # Negative Likelihood Ratio (LR-)
    DOR = "DOR"           # Diagnostic Odds Ratio
    AUC = "AUC"           # Area Under ROC Curve
    ACCURACY = "Accuracy" # Overall accuracy
    YOUDEN = "Youden"     # Youden's J statistic


@dataclass
class DiagnosticExtraction:
    """A single diagnostic accuracy extraction"""
    measure_type: DiagnosticMeasureType
    point_estimate: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    ci_level: float = 0.95

    # Source tracking
    source_text: str = ""
    char_start: int = 0
    char_end: int = 0

    # Quality flags
    is_percentage: bool = False  # True if reported as percentage
    normalized_value: Optional[float] = None  # Always 0-1 scale
    normalized_ci_lower: Optional[float] = None
    normalized_ci_upper: Optional[float] = None

    # Verification
    is_verified: bool = False
    warnings: List[str] = field(default_factory=list)


class DiagnosticAccuracyExtractor:
    """
    Extracts diagnostic test accuracy measures from clinical text.

    Supports extraction of sensitivity, specificity, PPV, NPV,
    likelihood ratios, DOR, and AUC with confidence intervals.
    """

    # ==========================================================================
    # SENSITIVITY PATTERNS
    # ==========================================================================
    SENSITIVITY_PATTERNS = [
        # Standard formats
        r'[Ss]ensitivity\s*(?:was|of|:)?\s*(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        r'[Ss]ensitivity\s*(?:was|of|:)?\s*(\d+\.?\d*)%?\s*\[\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\]',
        r'[Ss]ensitivity\s*(?:was|of|:)?\s*(\d+\.?\d*)%?\s*,\s*(?:95%?\s*)?CI\s*(\d+\.?\d*)%?\s*[-–—to]\s*(\d+\.?\d*)%?',
        r'[Ss]ensitivity[:\s]+(\d+\.?\d*)%?\s*\(\s*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',

        # Abbreviations
        r'\bSe\b[:\s=]+(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        r'\bSn\b[:\s=]+(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',

        # "sensitivity of 92% (95% CI: 88-96%)"
        r'[Ss]ensitivity\s+of\s+(\d+\.?\d*)%\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',

        # "sensitivity 0.92 (0.88-0.96)"
        r'[Ss]ensitivity\s*(?:was|of|:)?\s*(0\.\d+)\s*\(\s*(0\.\d+)\s*[-–—]\s*(0\.\d+)\s*\)',

        # "Se = 85% (95% CI 78-91%)"
        r'\bSe\b\s*=\s*(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',

        # Table format: "Sensitivity | 0.89 | 0.82-0.94"
        r'[Ss]ensitivity\s*\|\s*(\d+\.?\d*)%?\s*\|\s*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?',
    ]

    # ==========================================================================
    # SPECIFICITY PATTERNS
    # ==========================================================================
    SPECIFICITY_PATTERNS = [
        # Standard formats
        r'[Ss]pecificity\s*(?:was|of|:)?\s*(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        r'[Ss]pecificity\s*(?:was|of|:)?\s*(\d+\.?\d*)%?\s*\[\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\]',
        r'[Ss]pecificity\s*(?:was|of|:)?\s*(\d+\.?\d*)%?\s*,\s*(?:95%?\s*)?CI\s*(\d+\.?\d*)%?\s*[-–—to]\s*(\d+\.?\d*)%?',
        r'[Ss]pecificity[:\s]+(\d+\.?\d*)%?\s*\(\s*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',

        # Abbreviations
        r'\bSp\b[:\s=]+(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',

        # "specificity of 95% (95% CI: 91-98%)"
        r'[Ss]pecificity\s+of\s+(\d+\.?\d*)%\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',

        # "specificity 0.95 (0.91-0.98)"
        r'[Ss]pecificity\s*(?:was|of|:)?\s*(0\.\d+)\s*\(\s*(0\.\d+)\s*[-–—]\s*(0\.\d+)\s*\)',

        # "Sp = 92% (95% CI 87-96%)"
        r'\bSp\b\s*=\s*(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',

        # Table format
        r'[Ss]pecificity\s*\|\s*(\d+\.?\d*)%?\s*\|\s*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?',
    ]

    # ==========================================================================
    # PPV PATTERNS
    # ==========================================================================
    PPV_PATTERNS = [
        # Full name
        r'[Pp]ositive\s+[Pp]redictive\s+[Vv]alue\s*(?:was|of|:)?\s*(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        r'[Pp]ositive\s+[Pp]redictive\s+[Vv]alue\s*(?:was|of|:)?\s*(0\.\d+)\s*\(\s*(0\.\d+)\s*[-–—]\s*(0\.\d+)\s*\)',

        # Abbreviation
        r'\bPPV\b[:\s=]+(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        r'\bPPV\b[:\s=]+(0\.\d+)\s*\(\s*(0\.\d+)\s*[-–—]\s*(0\.\d+)\s*\)',
        r'\bPPV\b\s*=\s*(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',

        # "PPV of 78% (72-84%)"
        r'\bPPV\b\s+of\s+(\d+\.?\d*)%?\s*\(\s*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',

        # Table format
        r'\bPPV\b\s*\|\s*(\d+\.?\d*)%?\s*\|\s*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?',
    ]

    # ==========================================================================
    # NPV PATTERNS
    # ==========================================================================
    NPV_PATTERNS = [
        # Full name
        r'[Nn]egative\s+[Pp]redictive\s+[Vv]alue\s*(?:was|of|:)?\s*(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        r'[Nn]egative\s+[Pp]redictive\s+[Vv]alue\s*(?:was|of|:)?\s*(0\.\d+)\s*\(\s*(0\.\d+)\s*[-–—]\s*(0\.\d+)\s*\)',

        # Abbreviation
        r'\bNPV\b[:\s=]+(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        r'\bNPV\b[:\s=]+(0\.\d+)\s*\(\s*(0\.\d+)\s*[-–—]\s*(0\.\d+)\s*\)',
        r'\bNPV\b\s*=\s*(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',

        # "NPV of 96% (93-98%)"
        r'\bNPV\b\s+of\s+(\d+\.?\d*)%?\s*\(\s*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',

        # Table format
        r'\bNPV\b\s*\|\s*(\d+\.?\d*)%?\s*\|\s*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?',
    ]

    # ==========================================================================
    # LIKELIHOOD RATIO POSITIVE (LR+, PLR) PATTERNS
    # ==========================================================================
    PLR_PATTERNS = [
        # Full name
        r'[Pp]ositive\s+[Ll]ikelihood\s+[Rr]atio\s*(?:was|of|:)?\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # Abbreviations - note: no \b after + since + is not a word character
        r'\bLR\s*\+[:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        r'\bPLR\b[:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        r'\bLR\s*\(\s*\+\s*\)[:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # "LR+ = 5.2 (3.8-7.1)" - critical: LR\s*\+ allows optional space
        r'\bLR\s*\+\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        r'\bPLR\b\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # "positive likelihood ratio of 8.5 (95% CI 5.2-13.9)"
        r'[Pp]ositive\s+[Ll]ikelihood\s+[Rr]atio\s+of\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # Table format
        r'\bLR\s*\+\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\bPLR\b\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
    ]

    # ==========================================================================
    # LIKELIHOOD RATIO NEGATIVE (LR-, NLR) PATTERNS
    # ==========================================================================
    NLR_PATTERNS = [
        # Full name
        r'[Nn]egative\s+[Ll]ikelihood\s+[Rr]atio\s*(?:was|of|:)?\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # Abbreviations - note: no \b after - since - is not a word character
        r'\bLR\s*-[:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        r'\bNLR\b[:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        r'\bLR\s*\(\s*-\s*\)[:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # "LR- = 0.15 (0.08-0.28)" - critical: LR\s*- allows optional space
        r'\bLR\s*-\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        r'\bNLR\b\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # "negative likelihood ratio of 0.12 (95% CI 0.06-0.24)"
        r'[Nn]egative\s+[Ll]ikelihood\s+[Rr]atio\s+of\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # Table format
        r'\bLR\s*-\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\bNLR\b\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
    ]

    # ==========================================================================
    # DIAGNOSTIC ODDS RATIO (DOR) PATTERNS
    # ==========================================================================
    DOR_PATTERNS = [
        # Full name
        r'[Dd]iagnostic\s+[Oo]dds\s+[Rr]atio\s*(?:was|of|:)?\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # Abbreviation
        r'\bDOR\b[:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        r'\bDOR\b\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # "diagnostic odds ratio of 45.2 (95% CI 28.1-72.6)"
        r'[Dd]iagnostic\s+[Oo]dds\s+[Rr]atio\s+of\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # "DOR 52.3 (31.5-86.9)"
        r'\bDOR\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # Table format
        r'\bDOR\b\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
    ]

    # ==========================================================================
    # AUC / AUROC / C-STATISTIC PATTERNS
    # ==========================================================================
    AUC_PATTERNS = [
        # AUC formats
        r'\bAUC\b[:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        r'\bAUC\b\s+(?:was|of)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        r'\bAUC\b\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # AUROC formats
        r'\bAUROC\b[:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        r'\bAUROC\b\s+(?:was|of)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # C-statistic formats
        r'[Cc]-statistic\s*(?:was|of|:)?\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        r'[Cc]-index\s*(?:was|of|:)?\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # Area under the ROC curve
        r'[Aa]rea\s+under\s+(?:the\s+)?(?:ROC|receiver\s+operating\s+characteristic)\s+curve\s*(?:was|of|:)?\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # "AUC of 0.85 (0.79-0.91)"
        r'\bAUC\b\s+of\s+(0\.\d+)\s*\(\s*(0\.\d+)\s*[-–—]\s*(0\.\d+)\s*\)',

        # Table format
        r'\bAUC\b\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\bAUROC\b\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
    ]

    # ==========================================================================
    # ACCURACY PATTERNS
    # ==========================================================================
    ACCURACY_PATTERNS = [
        r'[Aa]ccuracy\s*(?:was|of|:)?\s*(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        r'[Oo]verall\s+[Aa]ccuracy\s*(?:was|of|:)?\s*(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        r'[Aa]ccuracy\s*=\s*(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        r'[Aa]ccuracy\s+of\s+(\d+\.?\d*)%?\s*\(\s*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
    ]

    # ==========================================================================
    # NEGATIVE CONTEXT PATTERNS (text that should NOT be extracted)
    # ==========================================================================
    NEGATIVE_CONTEXT_PATTERNS = [
        r'(?:assuming|hypothetical|expected|required|target)\s+(?:sensitivity|specificity|AUC)',
        r'(?:sensitivity|specificity|AUC)\s+(?:of at least|required|needed|threshold)',
        r'(?:power|sample size)\s+(?:calculation|analysis)\s+(?:assuming|with)',
        r'(?:minimum|threshold)\s+(?:sensitivity|specificity|AUC)',
    ]

    def __init__(self):
        """Initialize the diagnostic accuracy extractor."""
        self.negative_patterns = [re.compile(p, re.IGNORECASE) for p in self.NEGATIVE_CONTEXT_PATTERNS]

        # Compile all patterns
        self.pattern_map = {
            DiagnosticMeasureType.SENSITIVITY: [re.compile(p, re.IGNORECASE) for p in self.SENSITIVITY_PATTERNS],
            DiagnosticMeasureType.SPECIFICITY: [re.compile(p, re.IGNORECASE) for p in self.SPECIFICITY_PATTERNS],
            DiagnosticMeasureType.PPV: [re.compile(p, re.IGNORECASE) for p in self.PPV_PATTERNS],
            DiagnosticMeasureType.NPV: [re.compile(p, re.IGNORECASE) for p in self.NPV_PATTERNS],
            DiagnosticMeasureType.PLR: [re.compile(p, re.IGNORECASE) for p in self.PLR_PATTERNS],
            DiagnosticMeasureType.NLR: [re.compile(p, re.IGNORECASE) for p in self.NLR_PATTERNS],
            DiagnosticMeasureType.DOR: [re.compile(p, re.IGNORECASE) for p in self.DOR_PATTERNS],
            DiagnosticMeasureType.AUC: [re.compile(p, re.IGNORECASE) for p in self.AUC_PATTERNS],
            DiagnosticMeasureType.ACCURACY: [re.compile(p, re.IGNORECASE) for p in self.ACCURACY_PATTERNS],
        }

    def _is_negative_context(self, text: str, start: int) -> bool:
        """Check if extraction is in negative context (hypothetical, planning, etc.)"""
        # Get surrounding context (100 chars before)
        context_start = max(0, start - 100)
        context = text[context_start:start + 50].lower()

        for pattern in self.negative_patterns:
            if pattern.search(context):
                return True
        return False

    def _normalize_value(self, value: float, is_percentage: bool) -> float:
        """Normalize value to 0-1 scale."""
        if is_percentage or value > 1:
            return value / 100.0
        return value

    def _is_percentage(self, value: float, source_text: str) -> bool:
        """Determine if value is reported as percentage."""
        if value > 1:
            return True
        if '%' in source_text:
            return True
        return False

    def _verify_extraction(self, extraction: DiagnosticExtraction) -> DiagnosticExtraction:
        """Verify extraction for plausibility."""
        warnings = []

        # Normalize value
        is_pct = self._is_percentage(extraction.point_estimate, extraction.source_text)
        extraction.is_percentage = is_pct
        extraction.normalized_value = self._normalize_value(extraction.point_estimate, is_pct)

        if extraction.ci_lower is not None:
            extraction.normalized_ci_lower = self._normalize_value(extraction.ci_lower, is_pct)
        if extraction.ci_upper is not None:
            extraction.normalized_ci_upper = self._normalize_value(extraction.ci_upper, is_pct)

        # Validate ranges based on measure type
        norm_val = extraction.normalized_value

        if extraction.measure_type in [DiagnosticMeasureType.SENSITIVITY,
                                        DiagnosticMeasureType.SPECIFICITY,
                                        DiagnosticMeasureType.PPV,
                                        DiagnosticMeasureType.NPV,
                                        DiagnosticMeasureType.AUC,
                                        DiagnosticMeasureType.ACCURACY]:
            # These should be 0-1 after normalization
            if not (0 <= norm_val <= 1):
                warnings.append(f"Value {norm_val} outside valid range [0, 1]")
                extraction.is_verified = False
            else:
                extraction.is_verified = True

        elif extraction.measure_type == DiagnosticMeasureType.PLR:
            # PLR should be > 1 (higher is better)
            if extraction.point_estimate < 1:
                warnings.append(f"PLR {extraction.point_estimate} < 1 is unusual")
            extraction.is_verified = True

        elif extraction.measure_type == DiagnosticMeasureType.NLR:
            # NLR should be < 1 (lower is better)
            if extraction.point_estimate > 1:
                warnings.append(f"NLR {extraction.point_estimate} > 1 is unusual")
            extraction.is_verified = True

        elif extraction.measure_type == DiagnosticMeasureType.DOR:
            # DOR should be > 1
            if extraction.point_estimate < 1:
                warnings.append(f"DOR {extraction.point_estimate} < 1 is unusual")
            extraction.is_verified = True

        # Verify CI containment
        if extraction.ci_lower is not None and extraction.ci_upper is not None:
            ci_low = extraction.normalized_ci_lower if extraction.normalized_ci_lower else extraction.ci_lower
            ci_high = extraction.normalized_ci_upper if extraction.normalized_ci_upper else extraction.ci_upper

            if extraction.measure_type in [DiagnosticMeasureType.SENSITIVITY,
                                           DiagnosticMeasureType.SPECIFICITY,
                                           DiagnosticMeasureType.PPV,
                                           DiagnosticMeasureType.NPV,
                                           DiagnosticMeasureType.AUC,
                                           DiagnosticMeasureType.ACCURACY]:
                check_val = norm_val
            else:
                check_val = extraction.point_estimate
                ci_low = extraction.ci_lower
                ci_high = extraction.ci_upper

            if not (ci_low <= check_val <= ci_high):
                warnings.append(f"Point estimate {check_val} not within CI [{ci_low}, {ci_high}]")
                extraction.is_verified = False

        extraction.warnings = warnings
        return extraction

    def extract(self, text: str) -> List[DiagnosticExtraction]:
        """
        Extract all diagnostic accuracy measures from text.

        Args:
            text: Clinical text to analyze

        Returns:
            List of DiagnosticExtraction objects
        """
        extractions = []

        for measure_type, patterns in self.pattern_map.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    # Skip if in negative context
                    if self._is_negative_context(text, match.start()):
                        continue

                    try:
                        groups = match.groups()
                        if len(groups) >= 3:
                            point_estimate = float(groups[0].replace(',', '.'))
                            ci_lower = float(groups[1].replace(',', '.'))
                            ci_upper = float(groups[2].replace(',', '.'))

                            extraction = DiagnosticExtraction(
                                measure_type=measure_type,
                                point_estimate=point_estimate,
                                ci_lower=ci_lower,
                                ci_upper=ci_upper,
                                source_text=match.group(),
                                char_start=match.start(),
                                char_end=match.end()
                            )

                            # Verify and add
                            extraction = self._verify_extraction(extraction)
                            extractions.append(extraction)

                    except (ValueError, IndexError):
                        continue

        # Remove duplicates (same measure at same position)
        seen = set()
        unique_extractions = []
        for ext in extractions:
            key = (ext.measure_type, ext.char_start)
            if key not in seen:
                seen.add(key)
                unique_extractions.append(ext)

        return unique_extractions

    def extract_all_types(self, text: str) -> dict:
        """
        Extract all diagnostic measures and return organized by type.

        Returns:
            Dict mapping measure type to list of extractions
        """
        all_extractions = self.extract(text)

        result = {mt: [] for mt in DiagnosticMeasureType}
        for ext in all_extractions:
            result[ext.measure_type].append(ext)

        return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def extract_diagnostic_accuracy(text: str) -> List[DiagnosticExtraction]:
    """
    Convenience function to extract diagnostic accuracy measures.

    Args:
        text: Clinical text to analyze

    Returns:
        List of DiagnosticExtraction objects
    """
    extractor = DiagnosticAccuracyExtractor()
    return extractor.extract(text)


def get_diagnostic_measure_count() -> int:
    """Return count of supported diagnostic measure types."""
    return len(DiagnosticMeasureType)
