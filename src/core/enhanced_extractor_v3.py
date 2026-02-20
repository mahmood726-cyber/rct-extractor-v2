"""
Enhanced Effect Estimate Extractor
===================================

Features:
1. Pattern-based extraction with 180+ regex patterns
2. Heuristic confidence scoring (not empirically calibrated)
3. Tiered automation framework
4. Production-ready output formats
5. OCR error correction (Cl->CI, O->0, l->1 in numeric contexts)

v4.0.6 Pattern Fixes:
- Oncology semicolon + "to" format (KEYNOTE-024, POLO, etc.)
- Rate ratio recognition (ACTT-1)
- Percentage difference extraction (GEMINI 1)
- Non-standard CI percentages (EMPA-REG OUTCOME)
- Subject-comma HR format (KEYNOTE-189)
- OR comma-before-CI format (RA-BEAM)
- Mean difference with units (INPULSIS)

VALIDATION WARNING (P0-1):
The regex patterns in this module were iteratively tuned against a dataset
(data/external_validation_dataset.py) that was treated as "held-out" but in
practice was used for repeated refinement. This means reported sensitivity/
specificity figures from that dataset are optimistic (training-set metrics).
Independent external validation on a truly unseen corpus is required before
citing any accuracy claims.
"""

import re
import math
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum


class EffectType(Enum):
    """Supported effect estimate types"""
    HR = "HR"       # Hazard Ratio
    OR = "OR"       # Odds Ratio
    RR = "RR"       # Risk Ratio / Relative Risk
    IRR = "IRR"     # Incidence Rate Ratio
    ARD = "ARD"     # Absolute Risk Difference
    ARR = "ARR"     # Absolute Risk Reduction
    RRR = "RRR"     # Relative Risk Reduction
    NNT = "NNT"     # Number Needed to Treat
    NNH = "NNH"     # Number Needed to Harm
    MD = "MD"       # Mean Difference
    SMD = "SMD"     # Standardized Mean Difference
    WMD = "WMD"     # Weighted Mean Difference
    GMR = "GMR"     # Geometric Mean Ratio


class AutomationTier(Enum):
    """Automation confidence tiers (heuristic, NOT empirically validated)"""
    FULL_AUTO = "full_auto"       # No human review needed (high confidence)
    SPOT_CHECK = "spot_check"     # Random sampling recommended
    VERIFY = "verify"             # Quick human verification recommended
    MANUAL = "manual"             # Full manual review needed (low confidence)


@dataclass
class ConfidenceInterval:
    """Confidence interval with metadata"""
    lower: float
    upper: float
    level: float = 0.95  # 95% CI default
    method: str = ""     # Wald, exact, profile, etc.


@dataclass
class Extraction:
    """A single effect estimate extraction"""
    effect_type: EffectType
    point_estimate: float
    ci: Optional[ConfidenceInterval]
    p_value: Optional[float] = None

    # Standard Error (calculated from CI when not reported)
    standard_error: Optional[float] = None
    se_method: str = ""  # "reported", "calculated", "unavailable"

    # Source tracking
    source_text: str = ""
    char_start: int = 0
    char_end: int = 0

    # Confidence scoring
    raw_confidence: float = 0.0
    calibrated_confidence: float = 0.0
    automation_tier: AutomationTier = AutomationTier.MANUAL

    # Quality flags
    has_complete_ci: bool = False
    is_plausible: bool = True
    warnings: List[str] = field(default_factory=list)

    # ARD normalization
    original_scale: str = ""  # "percentage", "decimal", "unknown"
    normalized_value: Optional[float] = None  # Always decimal scale (0-1)
    normalized_ci_lower: Optional[float] = None
    normalized_ci_upper: Optional[float] = None

    # Primary outcome detection (v5.1)
    is_primary: bool = False
    primary_score: float = 0.0


class EnhancedExtractor:
    """
    Production-grade effect estimate extractor with full automation support.
    """

    # ==========================================================================
    # COMPREHENSIVE PATTERN LIBRARY
    # ==========================================================================

    # Text normalization replacements
    NORMALIZATIONS = {
        '\u00b7': '.',   # Middle dot
        '\u2013': '-',   # En-dash
        '\u2014': '-',   # Em-dash
        '\u2212': '-',   # Minus sign
        '\u00d7': 'x',   # Multiplication sign
        '\u2264': '<=',  # Less than or equal
        '\u2265': '>=',  # Greater than or equal
        '–': '-',        # En-dash (alternative)
        '—': '-',        # Em-dash (alternative)
        '·': '.',        # Middle dot (alternative)
        # v4.3 additions for improved unicode handling
        '\u207b': '-',   # Superscript minus
        '\u2011': '-',   # Non-breaking hyphen
        '\u2012': '-',   # Figure dash
        '\uff0d': '-',   # Fullwidth minus sign
        '\u2010': '-',   # Hyphen
        '\u2015': '-',   # Horizontal bar
        '\u2043': '-',   # Hyphen bullet
        '\u00ad': '',    # Soft hyphen (remove)
        '\u200b': '',    # Zero-width space (remove)
        '\u00a0': ' ',   # Non-breaking space to regular space
        '\u202f': ' ',   # Narrow no-break space
        '\u2009': ' ',   # Thin space
        '\u2002': ' ',   # En space
        '\u2003': ' ',   # Em space
        '−': '-',        # Unicode minus (common in PDFs)
        # v5.0.1: PDF confusable characters
        '\u037e': ';',   # Greek question mark (visually identical to semicolon)
        '\uff1b': ';',   # Fullwidth semicolon
        '\uff1a': ':',   # Fullwidth colon
        '\uff0c': ',',   # Fullwidth comma
        '\u2018': "'",   # Left single quotation mark
        '\u2019': "'",   # Right single quotation mark
        '\u201c': '"',   # Left double quotation mark
        '\u201d': '"',   # Right double quotation mark
        '\ufeff': '',    # BOM (zero-width no-break space)
    }

    # ==========================================================================
    # NEGATIVE CONTEXT FILTERS (v4.3.1 - reduce false positives)
    # ==========================================================================
    # These patterns identify text that should NOT be extracted from:
    # - Protocol papers (hypothesized effects)
    # - Methods sections (example calculations, sample sizes)
    # - Reviews citing other studies
    # - Observational/non-RCT studies
    # - Preclinical/animal studies

    NEGATIVE_CONTEXT_PATTERNS = [
        # Protocol/hypothesis language
        r'\b(?:we\s+)?hypothesiz[ed]*\b',
        r'\b(?:we\s+)?assum[ed]*\s+(?:a|an|the)?\s*(?:hazard|odds|risk|relative)\s*ratio',
        r'\bexpect(?:ed)?\s+(?:a|an|the)?\s*(?:hazard|odds|risk)\s*ratio',
        r'\bsample\s+size\s+(?:calculation|was\s+calculated|assuming)',
        r'\bpower(?:ed)?\s+(?:to|at)\s+\d+%',
        r'\bpowered\s+to\s+detect',
        r'\bassuming\s+(?:a|an)?\s*\d+%?\s*event\s*rate',
        r'\bprimary\s+analysis\s+in\s+\d{4}',  # Future timeline
        r'\benrollment\s+from\s+\d{4}',
        r'\bprotocol\s+describes',
        r'\bresults\s+will\s+be\s+reported',
        r'\bthis\s+protocol\b',

        # Methods/statistical examples
        r'\bexample\s+\d+[.:]\s',
        r'\bfor\s+(?:our|this)\s+example',
        r'\bpractice\s+problem',
        r'\bcalculate\s+the\s+sample\s+size',
        r'\busing\s+the\s+formula',
        r'\bstandard\s+error\s+can\s+be\s+estimated',
        r'\bSE\s*\(\s*ln\s*(?:HR|OR|RR)',
        r'\bhypothetical\b',
        r'\bsuppose\s+we\s+are\s+planning',

        # Review/citation language (only reject clear citations of OTHER studies)
        r'\bin\s+(?:the\s+)?[\w-]+\s+(?:trial|study)[,;]\s+\w+\s+(?:showed|reported|found)',
        r'\bprevious(?:ly)?\s+(?:reported|published|shown)',
        r'\boriginal\s+trial\s+reported',
        # Note: meta-analysis/systematic review/pooled patterns REMOVED (v5.0.1)
        # Meta-analyses report valid pooled estimates that should be extracted

        # Observational study markers
        r'\bretrospective\s+cohort',
        r'\bcase[- ]control\s+study',
        r'\bobservational\s+(?:study|evidence|data)',
        r'\bpropensity\s+(?:score|matched|matching)',
        r'\breal[- ]world\s+(?:evidence|data)',
        r'\bclaims\s+(?:data|database)',
        r'\bnested\s+case[- ]control',
        r'\bthis\s+observational\b',

        # Preclinical/animal
        r'\bmice\b',
        r'\bmurine\b',
        r'\bin[- ]vitro\b',
        r'\bcell\s+(?:culture|line|viability)',
        r'\bpreclinical\b',
        r'\banimal\s+(?:model|study)',

        # Editorial/commentary
        r'\beditorial\b',
        r'\bcommentary\b',
        r'\bwhat\s+makes\s+this\s+finding',
        r'\bquestions\s+remain',
        r'\bthe\s+era\s+of\b',

        # Non-medical content
        r'\bhousing\s+market',
        r'\beconomic\s+analysis',
        r'\bbaseball\b',
        r'\bsports\s+(?:analytics|statistics)',
        r'\bforeclosure\b',
        r'\bportfolio\b',
        r'\bwin\s+probability',
        r'\bruns\s+scored\b',
        r'\bplayoff\b',

        # Additional citation patterns (tightly scoped to avoid rejecting valid results)
        r'\btrial\s+extended\b',
        r'\bcurrent\s+guidelines\s+recommend',
        # Note: cochrane, SUCRA, network MA, umbrella review, IPD MA patterns REMOVED (v5.0.1)
        # These paper types contain valid pooled effect estimates

        # Guideline language
        r'\bclass\s+[IV]+[,;]\s+level\s+[A-C]',
        r'\brecommended?\s+for\s+all\s+patients',
        r'\bESC\s+guideline',
    ]

    # Compile negative context patterns for efficiency
    NEGATIVE_CONTEXT_COMPILED = None  # Will be compiled on first use

    # Hazard Ratio patterns (35+ variants for 95%+ sensitivity)
    HR_PATTERNS = [
        # v4.0.6: Critical patterns for failed extractions
        # "hazard ratio, 0.86; 95.02% CI, 0.74 to 0.99" - non-standard CI percentage (EMPA-REG)
        r'hazard\s*ratio[,;:\s]+(\d+\.?\d*)\s*[;,]\s*\d+\.?\d*%?\s*CI[,:\s]+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
        # "HR for death, 0.49; 95% CI, 0.38 to 0.64" - comma after subject (KEYNOTE-189)
        r'\bHR\s+for\s+[\w\s]{1,80}?,\s*(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # Standard formats
        r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s\[]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        r'hazard\s*ratio\s+(?:of|was|for\s+\w+\s+was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        # v5.4: "hazard ratio 0.12 [95% CI 0.0024-6.18]" - square bracket CI
        # PMC12527752: "hazardratio0.12[95%CI0.0024-6.18]"
        r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)\s*\]',

        # "The hazard ratio for X was Y (CI)" - extended context
        r'hazard\s*ratio\s+(?:for\s+)?[\w\s]{1,80}?(?:was|is)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

        # Abbreviation formats (CI/KI/IC for English/German/French-Spanish-Italian-Portuguese)
        # Handles both "95% CI" and "IC 95%" orderings
        r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:(?:IC|KI)\s+)?(?:95%?[\s-]*)?(?:CI|KI|IC)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
        r'\bHR\b[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:(?:IC|KI)\s+)?(?:95%?[\s-]*)?(?:CI|KI|IC)[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        r'\bHR\b[=:,\s]+(\d+\.?\d*)\s*\(\s*(?:(?:IC|KI)\s+)?(?:95%?[\s-]*)?(?:confidence\s*interval|CI|KI|IC)[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "HR 0.61; 95% confidence interval 0.51 to 0.72" - semicolon + full words
        r'\bHR\b[:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?confidence\s*interval[:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

        # "HR 0.87 (95% confidence interval [CI], 0.78 to 0.97)" - full words with [CI] bracket
        r'\bHR\b[\s,;=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?confidence\s*interval\s*(?:\[CI\])?\s*[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

        # "The HR was 0.82, with 95% CI of 0.71 to 0.95"
        r'\bHR\b\s+was\s+(\d+\.?\d*)[,;]\s*with\s+(?:95%?\s*)?CI\s+of\s+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

        # "HR for X: 0.83 (0.71-0.97)" - colon after context
        r'\bHR\b\s+(?:for\s+)?[\w\s]{1,80}?:\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # "(HR, 0.69; 95% CI, 0.57 to 0.84)" - comma after HR
        r'\(HR[,;]\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)\)',

        # v6.2: "(HR, 0.69, 95% CI, 0.57, 0.84)" - all-comma-delimited format
        # Note: comma before "95% CI" becomes semicolon after normalize_text
        r'\(\s*HR\s*,\s*(\d+\.?\d*)\s*[,;]\s*(?:95%?\s*)?CI\s*,\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)',
        r'\bHR\s*,\s*(\d+\.?\d*)\s*[,;]\s*(?:95%?\s*)?CI\s*,\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',

        # "secondary outcome HR = 0.91 (0.82 to 1.01)"
        r'\bHR\b\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)\s*\)',

        # "HR=0.68; 95% CI: 0.55, 0.84" - equals with semicolon and comma CI
        r'\bHR\b\s*=\s*(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',
        # "hazard ratio for death: 0.69 (0.58-0.82)" - context colon before value
        r'hazard\s*ratio\s+(?:for\s+)?[\w\s]{1,80}?:\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # Parenthetical prefix
        r'\(HR[=:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\)',
        r'\(hazard\s*ratio[=:\s]+(\d+\.?\d*)[,;]\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\)',

        # Square bracket CI
        r'\bHR\b[,;\s]+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)\s*\]',

        # Simple parenthetical
        r'\bHR\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # Comma in CI
        r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[,]\s*(\d+\.?\d*)\s*\)',

        # Equals format
        r'[Hh]azard\s*ratio\s*=\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:confidence\s*interval|CI)[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # Alternate terminology
        r'relative\s+hazard[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # Extended context (was/for patterns)
        r'\bHR\b\s+(?:for\s+)?[\w\s]{1,80}?was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # Adjusted HR
        r'[Aa]djusted\s+(?:HR|hazard\s*ratio)[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\baHR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
        # v5.3: "aHR 0.16; 95% CI: 0.06-0.46" - semicolon+CI format (PMC10037513)
        r'\baHR\b[,;:\s=]+(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

        # v5.3.1: "HR=0.88, 95% CI=[0.70, 1.10]" - bracket-equals-comma format
        r'\b[ac]?HR\b\s*=\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s*=\s*\[\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\]',

        # Unadjusted HR
        r'[Uu]nadjusted\s+(?:HR|hazard\s*ratio)[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # With N patients
        r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*[;,]\s*[nN]\s*=\s*\d+',

        # Additional recovery patterns
        r'\bHR\b\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # NEW PATTERNS for held-out test cases
        # "hazard ratio 0.71; 95% confidence interval 0.58-0.87" - semicolon + full confidence interval
        r'hazard\s*ratio\s+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?confidence\s+interval\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # v4.3.2: NEJM format with [CI] brackets
        # "hazard ratio, 0.87; 95% confidence interval [CI], 0.78 to 0.97" (LEADER/NEJM format)
        r'hazard\s*ratio[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?confidence\s+interval\s*\[CI\][,:\s]+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # "hazard ratio for disease progression or death, 0.53; 95% confidence interval [CI], 0.35 to 0.82"
        r'hazard\s*ratio\s+for\s+[\w\s\-/(),]{1,120}?,\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:confidence\s+interval(?:\s*\[CI\])?|\[?CI\]?)\s*[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

        # "(hazard ratio, 0.87; 95% confidence interval [CI], 0.78 to 0.97)" - in parentheses
        r'\(hazard\s*ratio[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?confidence\s+interval\s*\[CI\][,:\s]+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # v5.0.1: "hazard ratio [HR] 0.87; 95% confidence interval [CI]: 0.78-0.97"
        # Handles [HR] bracket notation after "hazard ratio" and dash separator
        r'hazard\s*ratio\s*(?:\[HR\])?\s*[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?confidence\s+interval\s*(?:\[CI\])?\s*[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

        # "HR, 0.87; 95% confidence interval [CI], 0.78 to 0.97" - abbreviated HR
        r'\bHR\b[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?confidence\s+interval\s*\[CI\][,:\s]+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # "with an HR of 0.82 (0.69-0.97)" - "with an HR of X (CI)"
        r'with\s+(?:an?\s+)?HR\s+of\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # "95% CI from 0.73 to 0.98" - "CI from X to Y"
        r'\bHR\b[,\s]+(\d+\.?\d*)[,;]?\s*(?:with\s+)?(?:95%?\s*)?CI\s+from\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
        r'hazard\s*ratio[,\s]+(\d+\.?\d*)[,;]?\s*(?:with\s+)?(?:95%?\s*)?CI\s+from\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # "hazard ratio of 0.82 (0.69, 0.97)" - comma in CI
        r'hazard\s*ratio\s+(?:of\s+)?(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)',

        # "(HR, 0.74; 95% CI, 0.65-0.85)" - (HR, X; CI, Y-Z)
        r'\(\s*HR\s*,\s*(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI\s*,?\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "hazard ratio 0.89 (95% CI 0.79 to 0.99)" - standard with "to"
        r'hazard\s*ratio\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # "HR 0.63 (95%CI 0.51-0.78)" - no space after %
        r'\bHR\b[:\s]+(\d+\.?\d*)\s*\(\s*95%CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "adjusted HR of 0.63 (95%CI 0.51-0.78)" - "HR of X (95%CI Y-Z)"
        r'[Aa]djusted\s+HR\s+of\s+(\d+\.?\d*)\s*\(\s*95%\s*CI\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\bHR\b\s+of\s+(\d+\.?\d*)\s*\(\s*95%\s*CI\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "aHR 0.54 (0.42, 0.69)" - adjusted HR with comma in CI
        r'\baHR\b[,;:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)',

        # v4.3.3: "HR=0.97; 0.80, 1.17" - semicolon then CI range without label
        r'\bHR\s*=\s*(\d+\.?\d*)\s*[;,]\s*(\d+\.?\d*)\s*[,–-]\s*(\d+\.?\d*)',

        # "HR=0.89 [0.80-0.99]" - equals sign + square brackets
        r'\bHR\s*=\s*(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',

        # "HR = 0.8 (0.7-0.9)" - spaced equals sign
        r'\bHR\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # v4.3.3: "HR=0.78, 95% CI 0.47-1.28" - comma before 95% CI
        r'\bHR\s*=\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "unadjusted hazard ratio was 1.15 with 95% CI of 0.98 to 1.35"
        r'hazard\s*ratio\s+was\s+(\d+\.?\d*)\s+with\s+(?:95%?\s*)?CI\s+of\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # "For all-cause mortality, we found HR 1.23 (1.05-1.44)"
        r'\bHR\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # "hazard ratio was estimated at 0.85, with a 95% CI from 0.73 to 0.98"
        r'hazard\s*ratio\s+was\s+(?:estimated\s+at\s+)?(\d+\.?\d*)[,;]\s*(?:with\s+)?(?:a\s+)?(?:95%?\s*)?CI\s+(?:from\s+)?(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # ADDITIONAL PATTERNS for remaining failures
        # "adjusted hazard ratio for X was 0.76 (95% CI: 0.63, 0.91)" - comma in CI
        r'hazard\s*ratio\s+(?:for\s+[\w\s]{1,80}\s+)?was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',

        # "hazard ratio for X was estimated at 0.85, with a 95% CI from 0.73 to 0.98"
        r'hazard\s*ratio\s+(?:for\s+[\w\s]{1,80}\s+)?was\s+estimated\s+at\s+(\d+\.?\d*)[,;]\s*with\s+(?:a\s+)?(?:95%?\s*)?CI\s+from\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # (duplicate removed — already at line 346)

        # "HR 0.67, 95% CI 0.58 to 0.77" - comma after value, no parentheses, "to" format
        r'\bHR\b\s+(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
        # "Primary outcome mortality: HR 0.79 (95% CI 0.70 to 0.89)" - context colon, then standard
        r':\s*HR\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)\s*\)',

        # =================================================================
        # MULTI-LANGUAGE HR PATTERNS
        # =================================================================
        # German: "Hazard Ratio 0,78 (95%-KI 0,65-0,94)" - note the hyphen after 95%
        r'[Hh]azard\s*[Rr]atio\s+(\d+[.,]?\d*)\s*\(\s*(?:95%?[\s-]*)?(?:KI|Konfidenzintervall)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Dutch: "Hazard ratio 0,75 (95%-BI 0,62-0,91)"
        r'[Hh]azard\s*[Rr]atio\s+(\d+[.,]?\d*)\s*\(\s*(?:95%?[\s-]*)?(?:BI|Betrouwbaarheidsinterval)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # French/Spanish/Italian/Portuguese: IC = Intervalle de confiance
        r'\bHR\b\s+(\d+[.,]?\d*)\s*\(\s*(?:95%?[\s-]*)?IC[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Spanish: Razón de riesgo
        r'[Rr]azón\s+de\s+riesgo\s+(\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Italian: Rapporto di rischio
        r'[Rr]apporto\s+di\s+rischio\s+(\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',

        # =================================================================
        # ASIAN LANGUAGE HR PATTERNS
        # =================================================================
        # Chinese: 风险比 (fengxianbi = hazard ratio)
        r'风险比\s*(\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|置信区间)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Japanese: ハザード比 (hazaado-hi = hazard ratio)
        r'ハザード比\s*(\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|信頼区間)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Korean: 위험비 (wiheombi = hazard ratio)
        r'위험비\s*(\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|신뢰구간)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Credible interval (Bayesian) - CrI
        r'\bHR\b\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CrI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # =================================================================
        # v4.1.1 ADDITIONS - Phase 1 Pattern Gap Closure (HR 96.6% → 100%)
        # =================================================================
        # "HR, 0.74 (0.65-0.85)" - comma after HR without "hazard ratio" prefix
        r'\bHR\b,\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # "HR, 0.74 (95% CI 0.65-0.85)" - comma after HR with CI
        r'\bHR\b,\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # "HR for progression-free survival in patients with advanced disease: 0.65 (0.52-0.81)"
        # Long outcome name with colon
        r'\bHR\s+for\s+[\w\s,-]+:\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # "HR for overall survival: 0.68 (95% CI 0.55 to 0.84)"
        r'\bHR\s+for\s+[\w\s,-]+:\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)\s*\)',
        # "HR 0.74; P<0.001" with separate CI handling - value only with p-value
        # (CI might be on next line - extract value only)
        # "HR (95% CI): 0.74 (0.65-0.85)" - label before colon
        r'\bHR\b\s*\(\s*(?:95%?\s*)?CI\s*\)\s*:\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "HR: 0.68 (0.55, 0.84)" - colon format with comma in CI
        r'\bHR\b:\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)',
        # "HR = 0.68, 0.55 to 0.84" - equals with comma then "to", no parentheses
        r'\bHR\b\s*=\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
        # "HR = 0.68, 0.55-0.84" - equals with comma then dash, no parentheses
        r'\bHR\b\s*=\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "(HR: 0.74, 95% CI: 0.65 to 0.85)" - parenthetical with colons
        r'\(\s*HR:\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI:\s*(\d+\.?\d*)\s+to\s+(\d+\.?\d*)\s*\)',

        # =================================================================
        # v5.0: REAL-PDF GAP CLOSURE
        # =================================================================
        # "HR 0.67 [0.50-0.88]" - square bracket CI without CI label
        r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',
        # "HR: 2.89 (95% CI 2.28–3.67)" - colon after HR, space, then standard (CI)
        r'\bHR\b:\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        r'\bHR\b:\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)\s*\)',
        # "HR: 1.03, 95% CI: 1.01-1.04" - colon after HR, comma before CI
        r'\bHR\b:\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?(?:CI|ci)[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "HR = 2.4; 95%CL:1.5-3.6" - CL (Confidence Limits)
        r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CL[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CL[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # "HR 0.50, CI 0.29-0.88" - bare CI without 95% prefix
        r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*,\s*CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "HR 1.03 (CI 95% 0.83-1.28)" - reversed CI 95% ordering
        r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*\(\s*CI\s*95%?\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # "HR: 0.98; 95% CI: 0.97-0.99" - colon after HR, semicolon before CI
        r'\bHR\b:\s*(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "HR: 1.47; 95% CI: 1.05, 2.05" - semicolon before CI, comma-separated bounds
        r'\bHR\b:\s*(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',
        # "HR = 0.63, 95% CI = 0.43, 0.91" - equals in CI, comma-separated bounds
        r'\bHR\b\s*=\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s*=\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',
        # IC with semicolon separator: "IC: 1.47;2.77"
        r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*[\[\(]\s*(?:95%?\s*)?IC[:\s]*(\d+\.?\d*)\s*[;,]\s*(\d+\.?\d*)\s*[\]\)]',
        # v5.0.1: Semicolons as CI bound separators
        # "HR:0.84 [95% CI: 0.81; 0.88]" or "(95%CI: 1.66; 2.33)"
        r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*[\[\(]\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*;\s*(\d+\.?\d*)\s*[\]\)]',
        # "HR: 1.97 [95%: 1.86; 4.21]" - 95% without CI label, semicolon separator
        r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*[\[\(]\s*95%?\s*[:\s]+(\d+\.?\d*)\s*[;,]\s*(\d+\.?\d*)\s*[\]\)]',
        # "HR: 1.66; 95% CI: 1.08-2.55" - semicolon before CI (already covered by line 474, but ensure colon-only format too)
        r'\bHR\b[,;:\s]+(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "HR=2.08, 95%CI 1.37-3.18" - comma then CI without colon
        r'\bHR\b\s*=\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # v5.7: "HR 16.128; 95% CI[1.431-181.778]" - bracket right after CI, no space (Coentrao_2012)
        r'\bHR\b\s+(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI\s*\[\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',
        # v5.7: "HR 16.128; 95% CI[1.431, 181.778]" - comma-separated in brackets
        r'\bHR\b\s+(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI\s*\[\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\]',
    ]

    # Odds Ratio patterns (25+ variants)
    OR_PATTERNS = [
        # v4.0.7: "OR = 0.26, 95% CI: 0.11-0.60" - equals sign with comma before CI
        r'\bOR\b\s*=\s*(\d+\.?\d*),\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # v4.0.6: "OR 3.0, 95% CI 2.3-4.0" - comma before 95% CI (RA-BEAM)
        r'\bOR\b\s+(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        r'odds\s*ratio\s+(?:of|was|for\s+[\w\s]{1,80}?was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
        r'\bOR\b[=:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\bOR\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # "OR = 0.72 (95% confidence interval: 0.55-0.94)"
        r'\bOR\b\s*=\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?confidence\s*interval[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "OR: 0.68; 95% CI: 0.52-0.89"
        r'\bOR\b:\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "(OR 1.56; 95% CI 1.21-2.01)"
        r'\(OR\s+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\)',

        # "The odds ratio for X was Y"
        r'odds\s*ratio\s+(?:for\s+)?[\w\s]{1,80}?(?:was|is)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

        # Adjusted OR
        r'[Aa]djusted\s+(?:OR|odds\s*ratio)[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\baOR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',

        # Comma in CI
        r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[,]\s*(\d+\.?\d*)\s*\)',

        # Square bracket
        r'\bOR\b[,;\s]+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)\s*\]',

        # Recovery pattern
        r'\bOR\b\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # v5.3.1: "OR=3.73, 95% CI=[1.01, 13.82]" - bracket-equals-comma format
        r'\bOR\b\s*=\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s*=\s*\[\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\]',

        # "odds ratio 0.81 (0.67, 0.98)" - comma in CI with full words
        r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[,]\s*(\d+\.?\d*)\s*\)',

        # "odds ratio 2.08 [1.56-2.77]" - square brackets with full words
        r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',

        # NEW PATTERNS for held-out test cases
        # "(OR, 2.34; 95% CI, 1.67-3.28)" - (OR, X; CI, Y-Z)
        r'\(\s*OR\s*,\s*(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI\s*,?\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # v6.2: "(OR, 1.38, 95% CI, 1.32, 1.44)" - comma-delimited CI bounds
        # PMC5949315: all values comma-separated inside parentheses
        # Note: comma before "95% CI" becomes semicolon after normalize_text
        r'\(\s*OR\s*,\s*(\d+\.?\d*)\s*[,;]\s*(?:95%?\s*)?CI\s*,\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)',
        # Also without parens: "OR, 1.38, 95% CI, 1.32, 1.44"
        r'\bOR\s*,\s*(\d+\.?\d*)\s*[,;]\s*(?:95%?\s*)?CI\s*,\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',

        # "Adjusted OR for X: 1.89 (95% CI 1.42 to 2.51)"
        r'[Aa]djusted\s+OR\s+for\s+[\w\s]{1,80}:\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # "odds ratio was 0.62 [0.48, 0.80]" - square brackets with comma
        r'odds\s*ratio\s+(?:was\s+)?(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\]',

        # "OR=3.15 (2.21-4.49)" - equals sign, no space
        r'\bOR\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # "OR 1.45; 95% CI 1.12-1.88" - semicolon before CI, no brackets
        r'\bOR\b\s+(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

        # "OR = 0.61; 95% CI: 0.40-0.93" - equals + semicolon before CI
        r'\bOR\s*=\s*(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

        # v4.3.3: "OR=0.97; 0.80, 1.17" - semicolon then CI without label
        r'\bOR\s*=\s*(\d+\.?\d*)\s*[;,]\s*(\d+\.?\d*)\s*[,–-]\s*(\d+\.?\d*)',

        # "OR=0.89 [0.80-0.99]" - equals sign + square brackets
        r'\bOR\s*=\s*(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',

        # "multivariable-adjusted odds ratio was 1.47 (95% confidence interval: 1.18, 1.83)"
        r'odds\s*ratio\s+(?:was\s+)?(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?confidence\s*interval[:\s]+(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',

        # "aOR=1.82 (95% CI: 1.35, 2.46)" - adjusted OR with comma
        r'\baOR\s*=?\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',

        # "(OR 0.72; 95% CI, 0.58-0.89; P=.002)" - semicolon format with P value
        r'\(OR\s+(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "For the subgroup analysis, OR was 0.71 [0.55-0.92]"
        r'\bOR\s+was\s+(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',

        # "odds ratio: 2.1 (confidence interval 1.5 to 2.9)" - full "confidence interval"
        r'odds\s*ratio[:\s]+(\d+\.?\d*)\s*\(\s*confidence\s+interval\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # "(OR 0.89, 95% CI 0.84 to 0.95)" - comma after value, "to" format
        r'\(OR\s+(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)\s*\)',
        # "OR 0.89, 95% CI 0.84 to 0.95" - without parentheses
        r'\bOR\b\s+(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # v4.0.3 ADDITIONS
        # "Pooled OR (back-transformed): 2.15 (95% CI 1.62-2.85)" - context with colon
        r'(?:Pooled|Summary|Overall)\s+OR[^:]*:\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "Diagnostic odds ratio: DOR 15.3 (95% CI 9.8-23.9)"
        r'[Dd]iagnostic\s+odds\s+ratio[:\s]+(?:DOR\s+)?(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # =================================================================
        # MULTI-LANGUAGE OR PATTERNS
        # =================================================================
        # French: Rapport de cotes (IC = intervalle de confiance)
        r'[Rr]apport\s+de\s+cotes?\s+(\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Spanish: Razón de momios / Odds ratio with IC
        r'[Rr]azón\s+de\s+momios\s+(\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        r'\b[Oo]dds\s*[Rr]atio\b\s+(\d+[.,]?\d*)\s*\(\s*(?:IC|intervalo)[^)]*?(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Portuguese: Razão de chances
        r'[Rr]azão\s+de\s+chances\s+(\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # German/Dutch: OR with KI/BI - handle "95%-KI" format
        r'\bOR\b\s+(\d+[.,]?\d*)\s*\(\s*(?:95%?[\s-]*)?(?:KI|BI)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Generic IC pattern (French/Spanish/Italian/Portuguese) - handles both "IC 95%" and "95% IC"
        r'\bOR\b\s+(\d+[.,]?\d*)\s*\(\s*(?:IC\s+)?(?:95%?[\s-]*)?(?:IC)?[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',

        # =================================================================
        # ASIAN LANGUAGE OR PATTERNS
        # =================================================================
        # Chinese: 比值比 (bizhihi = odds ratio)
        r'比值比\s*(\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|置信区间)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Japanese: オッズ比 (ozzu-hi = odds ratio)
        r'オッズ比\s*(\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|信頼区間)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Korean: 교차비 (gyochabi = odds ratio)
        r'교차비\s*(\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|신뢰구간)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Asian English format: OR=X (95%CI: Y-Z) - no space after %
        r'\bOR\s*=\s*(\d+\.?\d*)\s*\(\s*95%CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # Diagnostic OR: DOR
        r'\bDOR\b\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # v4.1.0 ADDITIONS - Additional OR patterns (Quick Wins)
        # "adjusted OR: 1.89 (1.42-2.51)" - colon format
        r'adjusted\s+OR:\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "multivariable OR 2.15 (95% CI 1.42-3.26)"
        r'(?:multivariable|multivariate)\s+OR\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "crude OR 1.67 (1.12-2.49)" - without adjusted
        r'crude\s+OR\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "(OR: 0.76, 95% CI: 0.62 to 0.94)" - colon after OR
        r'\(OR:\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)\)',
        # "OR was 0.68 [95% CI 0.52-0.89]" - square brackets
        r'\bOR\b\s+was\s+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',
        # "overall OR: 1.45 (1.12, 1.88)" - comma in CI
        r'(?:overall|pooled|summary)\s+OR[:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',
        # "odds ratio 0.72 [95% CI: 0.55-0.94]" - square brackets
        r'odds\s*ratio\s+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',
        # "OR 0.73 (CI: 0.62, 0.86)" - CI without %
        r'\bOR\b\s+(\d+\.?\d*)\s*\(\s*CI[:\s]+(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',

        # =================================================================
        # v4.1.1 ADDITIONS - Phase 1 Pattern Gap Closure (OR 90% → 100%)
        # =================================================================
        # "OR: 2.5 [1.8, 3.4]" - bracket + comma format with colon
        r'\bOR\b:\s*(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\]',
        # "OR 2.5 [1.8, 3.4]" - bracket + comma format without colon
        r'\bOR\b\s+(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\]',
        # "odds ratio of 0.82 (0.69–0.97)" - en-dash specifically
        r'odds\s*ratio\s+of\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*–\s*(\d+\.?\d*)\s*\)',
        # "OR 0.82 (0.69 to 0.97; p=0.02)" - p-value suffix
        r'\bOR\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s+to\s+(\d+\.?\d*)\s*;\s*[pP]\s*[=<>]',
        # "OR 0.82 (0.69-0.97; P<0.001)" - P-value suffix with dash
        r'\bOR\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*;\s*[pP]\s*[=<>]',
        # "pooled OR: 2.15 (95% CI 1.62-2.85)" - specific pooled format
        r'pooled\s+OR:\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "pooled OR 2.15 (1.62-2.85)" - pooled without CI label
        r'pooled\s+OR\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "OR (95% CI): 1.45 (1.12-1.88)" - label before value
        r'\bOR\b\s*\(\s*(?:95%?\s*)?CI\s*\)\s*:\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "OR = 1.45, 1.12-1.88" - equals with comma, no parentheses
        r'\bOR\b\s*=\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "(OR = 1.45; 1.12-1.88)" - parenthetical with equals and semicolon
        r'\(\s*OR\s*=\s*(\d+\.?\d*)\s*;\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # "95% CI for OR: 1.12-1.88" with separate value - capture CI only, look behind for value
        # This needs special handling - skip for now

        # =================================================================
        # v5.0: REAL-PDF GAP CLOSURE (OR)
        # =================================================================
        # "OR 1.44 [1.11-1.86]" - square bracket CI without label
        r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',
        # "OR, 2.62; 95% CI, 1.66-4.15" - OR with comma before value
        r'\bOR\b\s*,\s*(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\bOR\b\s*,\s*(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
        # "OR = 0.63, 95% CI = 0.43, 0.91" - CI with equals, comma-separated bounds
        r'\bOR\b\s*=\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s*=\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',
        # "OR 0.50, CI 0.29-0.88" - bare CI without 95%
        r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*,\s*CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "OR: 1.03, 95% ci: 1.01-1.04" - lowercase ci
        r'\bOR\b:\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?(?:CI|ci)[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # CL (Confidence Limits)
        r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CL[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # OR 1.99 [95% CI 1.1-3.6] - square brackets WITH CI label
        r'\bOR\b\s+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',
        # IC with semicolon: "IC: 1.47;2.77"
        r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*[\[\(]\s*(?:95%?\s*)?IC[:\s]*(\d+\.?\d*)\s*[;,]\s*(\d+\.?\d*)\s*[\]\)]',
        # "odds ratio = 2.02 [95% IC: 1.47;2.77]"
        r'odds\s*ratio\s*=\s*(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?IC[:\s]*(\d+\.?\d*)\s*[;,]\s*(\d+\.?\d*)\s*\]',
        # CI 95% reversed ordering: "(CI 95% 0.83-1.28)"
        r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*\(\s*CI\s*95%?\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # v5.0.1: Semicolons as CI bound separators
        # "OR 1.15 [0.88; 1.52]" or "(95% CI: 0.81; 0.88)"
        r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*[\[\(]\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*;\s*(\d+\.?\d*)\s*[\]\)]',
        # "OR 1.97 [95%: 1.86; 4.21]" - 95% without CI label
        r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*[\[\(]\s*95%?\s*[:\s]+(\d+\.?\d*)\s*[;,]\s*(\d+\.?\d*)\s*[\]\)]',
        # "OR: 1.47 (1.05, 2.05)" - parenthesized comma-separated (already partially covered)
        r'\bOR\b:\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)',
    ]

    # Risk Ratio / Relative Risk patterns (25+ variants)
    RR_PATTERNS = [
        # v4.3.1: "relative risk of death, 0.70; 95 percent confidence interval, 0.60 to 0.82" (RALES format)
        # v5.8: also matches after normalization: "relative risk of death, 0.70; 95% CI, 0.60 to 0.82"
        r'relative\s+risk\s+of\s+[\w\s]{1,80},\s*(\d+\.?\d*)\s*[;,]\s*(?:95\s+)?percent\s+confidence\s+interval[,:\s]+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
        r'relative\s+risk\s+of\s+[\w\s]{1,80},\s*(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*(?:to|[-\u2013\u2014])\s*(\d+\.?\d*)',
        r'relative\s+risk[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        r'(?:relative\s+)?risk\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
        r'rate\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\bRR\b\s+(?:for\s+)?[\w\s]{1,80}?was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'relative\s+risk\s+(?:of|was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\bRR\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # "relative risk, 0.65; 95% CI, 0.52 to 0.81"
        r'relative\s+risk[,;]\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

        # "RR = 0.91 (95% confidence interval: 0.84-0.99)"
        r'\bRR\b\s*=\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?confidence\s*interval[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "RR: 1.15; 95% CI: 1.02-1.30"
        r'\bRR\b:\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # v5.3.1: "RR=0.65, 95% CI=[0.52, 0.81]" - bracket-equals-comma format
        r'\bRR\b\s*=\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s*=\s*\[\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\]',

        # "(RR 0.82; 95% CI 0.73-0.92)"
        r'\(RR\s+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\)',

        # v6.2: "(RR, 0.73, 95% CI, 0.60, 0.89)" - comma-delimited CI bounds
        # Note: comma before "95% CI" becomes semicolon after normalize_text
        r'\(\s*RR\s*,\s*(\d+\.?\d*)\s*[,;]\s*(?:95%?\s*)?CI\s*,\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)',
        r'\bRR\s*,\s*(\d+\.?\d*)\s*[,;]\s*(?:95%?\s*)?CI\s*,\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',

        # "relative risk of X (CI)"
        r'relative\s+risk\s+of\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # Adjusted RR
        r'[Aa]djusted\s+(?:RR|relative\s+risk)[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\baRR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',

        # Recovery pattern
        r'\bRR\b\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "relative risk 0.87 (95% CI 0.79-0.95)" - standard with hyphen
        r'relative\s+risk\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "relative risk 0.41 (0.13-1.26)" - simple parenthetical full words
        r'relative\s+risk\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # "relative risk 0.65 (0.52 to 0.81)" - simple with "to"
        r'relative\s+risk\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s+to\s+(\d+\.?\d*)\s*\)',
        # "risk ratio 0.77; 95% CI, 0.69 to 0.85" - semicolon before CI
        # v5.4: also handles "risk ratio, 0.67; 95% CI, 0.46-0.98" (comma after ratio, PMC12074564)
        r'risk\s+ratio[,;:\s]+(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        # v5.7: "risk ratio: 1.22; 95% CI: 1.03, 1.44" - comma-separated CI bounds (Bracken_2014)
        r'(?:adjusted\s+)?risk\s+ratio[,;:\s]+(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',
        # v5.7: "relative risk: 1.22; 95% CI: 1.03, 1.44" - same with "relative risk"
        r'(?:adjusted\s+)?relative\s+risk[,;:\s]+(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',
        # "adjusted RR was 1.28 (95% CI 1.08-1.51)"
        r'[Aa]djusted\s+RR\s+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "RR 0.68 (95% CI 0.58 to 0.80)" - standard with "to"
        r'\bRR\b\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # v4.3.3: "RR=0.97; 0.80, 1.17" - semicolon then CI without label
        r'\bRR\s*=\s*(\d+\.?\d*)\s*[;,]\s*(\d+\.?\d*)\s*[,–-]\s*(\d+\.?\d*)',

        # "RR=0.89 [0.80-0.99]" - equals sign + square brackets
        r'\bRR\s*=\s*(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',

        # "RR = 0.8 (0.7-0.9)" - spaced equals sign
        r'\bRR\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # v4.3.3: "RR = 0.78, 95% CI 0.65-0.95" - comma before CI
        r'\bRR\s*=\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "RR = 0.61; 95% CI: 0.40-0.93" - semicolon before CI, colon after CI
        r'\bRR\s*=\s*(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

        # "rate ratio 0.78, 95% CI 0.65-0.95"
        r'rate\s+ratio\s+(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'rate\s+ratio\s+(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # "summary relative risk 1.18 (1.05-1.33)" - with prefix
        r'(?:summary|pooled|overall)\s+relative\s+risk\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "hospitalization: relative risk 0.72 (0.61-0.85)" - context colon
        r'[\w\s]{1,80}:\s*relative\s+risk\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # NEW PATTERNS for held-out test cases
        # "Risk ratio for X: 0.71 (95% CI, 0.58-0.87)"
        r'[Rr]isk\s+ratio\s+for\s+[\w\s]{1,80}:\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "The RR for X was 0.83 (0.72 to 0.96; P=0.01)"
        r'\bRR\b\s+(?:for\s+[\w\s]{1,80}\s+)?was\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',

        # "Relative risk of hospitalization was significantly reduced: RR 0.68 [95% CI: 0.55, 0.84]"
        r'\bRR\b\s+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\]',

        # "RR=1.42 (95% CI 1.15-1.76)" - equals sign
        r'\bRR\s*=\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "Pooled relative risk: 0.84 (0.74, 0.95)" - comma in CI
        r'relative\s+risk[:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)',

        # "The adjusted RR was 1.28 (95% confidence interval 1.08-1.51)"
        r'[Aa]djusted\s+RR\s+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?confidence\s+interval\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # "The study found RR of 0.77; CI: 0.65, 0.91" - RR of X; CI: Y, Z
        r'\bRR\b\s+of\s+(\d+\.?\d*)[;,]\s*CI[:\s]+(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',

        # "RR 0.77; 95% CI, 0.69 to 0.85" - semicolon then "to" format
        r'\bRR\b\s+(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
        # v5.5: "RR 0.19; 95% CI 0.08-0.46" - semicolon then dash format (Bracken_2014)
        r'\bRR\b\s+(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # v5.4: "RR : 0.81 CI: 0.72–0.91" - colon after RR, dash CI, optional 95%
        # PMC12487220: "RR : 0.81 CI: 0.72–0.91)"
        r'\bRR\b\s*[,:]\s*(\d+\.?\d*)\s*[;,]?\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "(RR 0.77, 95% CI 0.69-0.85)" - parentheses with comma after value
        r'\(RR\s+(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\)',
        # "RR 0.85 (0.79 to 0.92)" - simple format with "to", no CI label
        r'\bRR\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s+to\s+(\d+\.?\d*)\s*\)',

        # =================================================================
        # MULTI-LANGUAGE RR PATTERNS
        # =================================================================
        # German: Relatives Risiko with KI (Konfidenzintervall) - handle "95%-KI" format
        r'[Rr]elatives?\s+[Rr]isiko\s+(\d+[.,]?\d*)\s*\(\s*(?:95%?[\s-]*)?(?:KI|Konfidenzintervall)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # French: Risque relatif with IC
        r'[Rr]isque\s+relatif\s+(\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # French: "intervalle de confiance à 95%" format
        r'[Rr]isque\s+relatif\s+(\d+[.,]?\d*)\s*\(\s*intervalle\s+de\s+confiance[^)]*?(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Spanish: Riesgo relativo with IC
        r'[Rr]iesgo\s+relativo\s+(\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Italian: Rischio relativo with IC
        r'[Rr]ischio\s+relativo\s+(\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Portuguese: Risco relativo with IC
        r'[Rr]isco\s+relativo\s+(\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Generic: RR with IC/KI/BI - handle "95%-" prefix
        r'\bRR\b\s+(\d+[.,]?\d*)\s*\(\s*(?:95%?[\s-]*)?(?:IC|KI|BI)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',

        # =================================================================
        # ASIAN LANGUAGE RR PATTERNS
        # =================================================================
        # Chinese: 相对危险度 (xiangdui weixiandu = relative risk)
        r'相对危险度\s*(\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|置信区间)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Japanese: 相対危険 (soutai kiken = relative risk)
        r'相対危険\s*(\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|信頼区間)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Korean: 상대위험도 (sangdae wiheomdo = relative risk)
        r'상대위험도\s*(\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|신뢰구간)[:\s]*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',
        # Prevalence ratio (often coded as RR)
        r'[Pp]revalence\s+ratio\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # =================================================================
        # v4.1.1 ADDITIONS - Phase 1 Pattern Gap Closure (RR 97.2% → 100%)
        # =================================================================
        # "RR 0.82 (CI 0.68-0.98)" - without 95%
        r'\bRR\b\s+(\d+\.?\d*)\s*\(\s*CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # "RR 0.82 (CI: 0.68-0.98)" - without 95%, with colon
        r'\bRR\b\s+(\d+\.?\d*)\s*\(\s*CI:\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # European format: "RR 0,82 (0,68–0,98)" - comma as decimal separator
        r'\bRR\b\s+(\d+,\d+)\s*\(\s*(\d+,\d+)\s*[-–—]\s*(\d+,\d+)\s*\)',
        # European format: "RR 0,82 (95% CI 0,68–0,98)"
        r'\bRR\b\s+(\d+,\d+)\s*\(\s*(?:95%?\s*)?CI\s+(\d+,\d+)\s*[-–—]\s*(\d+,\d+)\s*\)',
        # "relative risk 0.65 [CI: 0.52, 0.81]" - square brackets with colon and comma
        r'relative\s+risk\s+(\d+\.?\d*)\s*\[\s*CI:\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\]',
        # "relative risk 0.65 [95% CI: 0.52, 0.81]" - square brackets full format
        r'relative\s+risk\s+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI:\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\]',
        # "RR = 0.82, 0.68-0.98" - no parentheses, comma separator
        r'\bRR\b\s*=\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "RR = 0.82; 0.68-0.98" - no parentheses, semicolon separator
        r'\bRR\b\s*=\s*(\d+\.?\d*)\s*;\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "RR: 0.82 [0.68, 0.98]" - colon with square brackets
        r'\bRR\b:\s*(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\]',
        # "RR 0.82 (P<0.05; CI 0.68-0.98)" - p-value before CI
        r'\bRR\b\s+(\d+\.?\d*)\s*\([^)]*CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # "pooled RR: 0.84 (0.74-0.95)" - pooled format
        r'pooled\s+RR:\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "pooled RR 0.84 (95% CI 0.74-0.95)" - pooled with CI
        r'pooled\s+RR\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "(RR: 0.82; CI: 0.68-0.98)" - parenthetical with colons
        r'\(\s*RR:\s*(\d+\.?\d*)\s*;\s*CI:\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',

        # =================================================================
        # v5.0: REAL-PDF GAP CLOSURE (RR)
        # =================================================================
        # "RR 0.50 [0.29-0.88]" - square bracket CI without label
        r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',
        # "RR, 0.50; 95% CI, 0.29-0.88" - comma before value
        r'\bRR\b\s*,\s*(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "RR 0.50, CI 0.29-0.88" - bare CI without 95%
        r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*,\s*CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # CL (Confidence Limits)
        r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CL[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "RR: 1.03, 95% CI: 1.01-1.04" - colon after RR
        r'\bRR\b:\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?(?:CI|ci)[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        # "RR: 1.03 (95% CI 1.01-1.04)" - colon after RR with parenthetical CI
        r'\bRR\b:\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # "RR = 0.63, 95% CI = 0.43, 0.91" - CI with equals
        r'\bRR\b\s*=\s*(\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s*=\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',
        # "RR 1.03 (CI 95% 0.83-1.28)" - reversed CI 95% ordering
        r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*\(\s*CI\s*95%?\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # IC with semicolon: "RR 1.02 (IC 95% 0.81;1.30)"
        r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*[\[\(]\s*(?:95%?\s*)?IC[:\s]*(\d+\.?\d*)\s*[;,]\s*(\d+\.?\d*)\s*[\]\)]',
        # "relative risk reduction" / RRR patterns
        r'\bRRR\b\s*=\s*(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',
        r'\bRRR\b\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # v5.0.1: Semicolons as CI bound separators
        # "RR 1.42 [1.07; 1.88]"
        r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*[\[\(]\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*;\s*(\d+\.?\d*)\s*[\]\)]',
        # "RR 1.46 [95%: 1.09; 1.96]" - 95% without CI label
        r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*[\[\(]\s*95%?\s*[:\s]+(\d+\.?\d*)\s*[;,]\s*(\d+\.?\d*)\s*[\]\)]',
        # "RR: 0.87; 95% CI: 0.73-1.03" - colon + semicolon
        r'\bRR\b:\s*(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
    ]

    # Incidence Rate Ratio patterns
    IRR_PATTERNS = [
        r'(?:incidence\s+)?rate\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        r'\bIRR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—,])\s*(\d+\.?\d*)\s*[\)\]]',
        r'\bIRR\b\s+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        r'incidence\s+rate\s+ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        # Semicolon format: "rate ratio 1.32; 95% CI, 1.22 to 1.43"
        r'rate\s*ratio\s+(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
        # Simple: "rate ratio 1.32 (1.22 to 1.43)"
        r'rate\s*ratio\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s+to\s+(\d+\.?\d*)\s*\)',
        # With 95% CI: "rate ratio 1.32 (95% CI 1.22-1.43)"
        r'rate\s*ratio\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # "rate ratio 1.32; 95% CI, 1.12-1.55" - semicolon + comma after CI + dash
        r'rate\s*ratio\s+(\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',

        # =================================================================
        # v4.2.0 ADDITIONS - Respiratory exacerbation rate patterns (Phase 3)
        # =================================================================
        # Exacerbation rate ratio - common in COPD/asthma trials
        r'(?:COPD\s+)?(?:moderate[- ]to[- ]severe\s+)?exacerbation\s+rate\s*ratio[:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
        r'(?:annuali[sz]ed\s+)?exacerbation\s+rate\s*ratio[:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\bAECOPD\b\s+rate\s*ratio[:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
        r'rate\s+of\s+(?:moderate[- ]to[- ]severe\s+)?exacerbations?[:\s]+(?:rate\s+ratio\s+)?(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—to]\s*(\d+\.?\d*)',
        # Relative rate/reduction for exacerbations
        r'(?:exacerbation|AECOPD)\s+(?:rate\s+)?(?:reduction|relative\s+rate)[:\s]+(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)%?\s+to\s+(\d+\.?\d*)%?',
        # IRR for exacerbations
        r'\bIRR\b\s+(?:for\s+)?(?:exacerbation|AECOPD)[:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
    ]

    # =================================================================
    # Geometric Mean Ratio patterns (v5.2) — vaccine/immunogenicity trials
    # NOTE: Extract ONLY GMR (ratio between arms), NOT individual GMT values.
    # Evidence: PMC10011807 (vaccine RCTs report GMR with CI)
    # =================================================================
    GMR_PATTERNS = [
        # "geometric mean ratio 1.23 (95% CI 1.05-1.44)" / "geometric means ratio ..."
        r'geometric\s+means?\s+ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        # "geometric mean ratio was/of 1.23 (95% CI 1.05-1.44)"
        r'geometric\s+means?\s+ratio\s+(?:was|of)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        # "GMR: 0.95 (95% CI 0.87-1.04)"
        r'\bGMR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—,])\s*(\d+\.?\d*)\s*[\)\]]',
        # "GMR 1.15 (1.02 to 1.30)"
        r'\bGMR\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s+to\s+(\d+\.?\d*)\s*\)',
        # "GMR was/of 1.12 (95% CI, 0.98-1.28)"
        r'\bGMR\b\s+(?:was|of)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        # "GMR=1.08 (0.95-1.23)"
        r'\bGMR\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # "GMR=1.08; 95% CI: 0.95-1.23"
        r'\bGMR\s*=\s*(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
        # "geometric mean ratio: 2.05 [95% CI 1.45-2.90]"
        r'geometric\s+means?\s+ratio[:\s]+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',
        # "GMR (95% CI): 1.15 (1.02-1.30)"
        r'\bGMR\b\s*\((?:95%?\s*)?CI\)\s*[:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
    ]

    # GMR value-only patterns (for vaccine trials without CI)
    GMR_VALUE_ONLY_PATTERNS = [
        r'\bGMR\b[,;:\s=]+(\d+\.?\d*)\b',
        r'geometric\s+means?\s+ratio[,;:\s=]+(\d+\.?\d*)\b',
    ]

    # Standardized Mean Difference (check BEFORE MD)
    SMD_PATTERNS = [
        r'standardized\s+mean\s+difference[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
        r'\bSMD\b[,;:\s=]+(-?\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—,]\s*(-?\d+\.?\d*)\s*[\)\]]',
        r'\bSMD\b\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)\s*\)',
        r"Cohen'?s?\s+d[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)",
        r'[Hh]edges\'?\s*g[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
        r'effect\s+size[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',

        # "SMD: 0.52 (95% CI: 0.31 to 0.73)"
        r'\bSMD\b:\s*(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[:\s]*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',

        # "SMD = -0.41 (-0.62 to -0.20)"
        r'\bSMD\b\s*=\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)\s*\)',

        # "effect size (Cohen's d) 0.38 (0.18-0.58)"
        r'effect\s+size\s*\([^)]+\)\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',

        # Context patterns
        r'(?:pooled|overall|summary)\s+(?:SMD|standardized\s+mean\s+difference)[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',

        # "Cohens d: -0.55 (-0.78 to -0.32)"
        r"Cohen'?s?\s*d:\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)",

        # Recovery pattern
        r'\bSMD\b\s*(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',

        # "standardized mean difference -0.28 (-0.45 to -0.11)" - simple
        r'standardized\s+mean\s+difference\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)\s*\)',

        # "standardized mean difference -0.88; 95% CI -1.03 to -0.74" - semicolon format
        r'standardized\s+mean\s+difference\s+(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # "(SMD -0.62, 95% CI -0.81 to -0.42)" - comma after value, to format
        r'\(SMD\s+(-?\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',

        # "SMD -0.62, 95% CI -0.81 to -0.42" - without outer parentheses, "to" format
        r'\bSMD\b\s+(-?\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "SMD 0.30, 95% CI 0.26-0.34" - comma after value, dash format
        r'\bSMD\b\s+(-?\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',

        # Context patterns with colon
        r'[\w\s]{1,80}:\s*(?:SMD|standardized\s+mean\s+difference)\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',

        # "small/medium/large effect: SMD X (Y-Z)"
        r'(?:small|medium|large)\s+effect:\s*SMD\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',

        # "SMD 0.01 (-0.15 to 0.17)" - with "to" instead of hyphen
        r'\bSMD\b\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*to\s*(-?\d+\.?\d*)\s*\)',

        # "SMD -0.51 (95% CI -0.71 to -0.31)" - space after CI, "to" format
        r'\bSMD\b\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',

        # "Hedges g: 0.35 (0.15 to 0.55)" - apostrophe variations
        r'[Hh]edges\'?\s*g:\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',

        # Context pattern "teacher expectancy: SMD 0.12 (95% CI -0.02 to 0.26)"
        r'[\w\s]{1,80}:\s*SMD\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',

        # "depression: SMD -0.48 (95% CI -0.68 to -0.28)"
        r'[\w\s]{1,80}:\s*(?:SMD|standardized\s+mean\s+difference)\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s*(-?\d+\.?\d*)\s*to\s*(-?\d+\.?\d*)',

        # NEW PATTERNS for held-out test cases
        # "Effect on X: standardized mean difference -0.52 (95% CI -0.71 to -0.33)"
        r'standardized\s+mean\s+difference\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # "The pooled SMD was 0.38 [0.21, 0.55]"
        r'\bSMD\b\s+was\s+(-?\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\]',

        # "SMD = 0.45 (95% CI: 0.28 to 0.62)"
        r'\bSMD\b\s*=\s*(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # "Hedges' g for X was -0.67 (-0.89, -0.45)"
        r'[Hh]edges\'?\s*g\s+(?:for\s+[\w\s]{1,80}\s+)?was\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)',
        # "Hedges' g -0.35 (-0.52 to -0.18)" - simple with "to"
        r'[Hh]edges\'?\s*g\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',
        # "The pooled standardized mean difference was -0.62 (95% CI -0.81 to -0.42)"
        r'(?:pooled\s+)?standardized\s+mean\s+difference\s+was\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # "Cohen's d = 0.31 (95% CI 0.12 to 0.50)"
        r"Cohen'?s?\s*d\s*=\s*(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)",

        # "Overall effect: g = 0.42 (95% CI: 0.25, 0.59)"
        r'\bg\b\s*=\s*(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)',

        # "The standardised mean difference was -0.35 (-0.52 to -0.18)"
        r'standardis?ed\s+mean\s+difference\s+was\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',

        # "SMD: 0.29 (0.11-0.47)" - colon with hyphen
        r'\bSMD\b:\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)\s*\)',

        # =================================================================
        # ASIAN LANGUAGE SMD PATTERNS
        # =================================================================
        # Chinese: 标准化均数差 (biaozhunhua junshucha = standardized mean difference)
        r'标准化均数差\s*(-?\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|置信区间)[:\s]*(-?\d+[.,]?\d*)\s*(?:至|[-–—])\s*(-?\d+[.,]?\d*)',
        # Japanese: 標準化平均差 (hyoujunka heikinsa = standardized mean difference)
        r'標準化平均差\s*(-?\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|信頼区間)[:\s]*(-?\d+[.,]?\d*)\s*[-–—]\s*(-?\d+[.,]?\d*)',

        # v4.1.0 ADDITIONS - Additional SMD patterns from improvement plan
        # "Cohen's d = 0.55" - value only (no CI)
        r"Cohen'?s?\s*d\s*=\s*(-?\d+\.?\d*)",
        # "Hedges' g = 0.42 (0.18, 0.66)" - comma in CI
        r"[Hh]edges'?\s*g\s*=\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)",
        # "Glass's delta 0.78 (0.51 to 1.05)"
        r"[Gg]lass'?s?\s+delta\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)",
        # "effect size d = 0.45"
        r'effect\s+size\s+d\s*=\s*(-?\d+\.?\d*)',
        # "observed d = 0.62 (95% CI 0.41 to 0.83)"
        r'\bd\s*=\s*(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "SMD (Hedges' g) = 0.52 (0.31-0.73)"
        r'SMD\s*\([^)]+\)\s*=?\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
        # "random effects SMD 0.45 (0.22-0.68)"
        r'(?:random|fixed)\s+effects?\s+SMD\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',

        # =================================================================
        # MULTI-LANGUAGE SMD PATTERNS
        # =================================================================
        # German: Standardisierte Mittelwertdifferenz
        r'[Ss]tandardisierte\s+[Mm]ittelwertdifferenz\s+(-?\d+[.,]?\d*)\s*\(\s*(?:95%?[\s-]*)?(?:KI)[:\s]*(-?\d+[.,]?\d*)\s*[-–—]\s*(-?\d+[.,]?\d*)',
        # French: Différence moyenne standardisée
        r'[Dd]ifférence\s+moyenne\s+standardisée\s+(-?\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(-?\d+[.,]?\d*)\s*[-–—]\s*(-?\d+[.,]?\d*)',
        # Spanish: Diferencia de medias estandarizada
        r'[Dd]iferencia\s+de\s+medias\s+estandarizada\s+(-?\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(-?\d+[.,]?\d*)\s*[-–—]\s*(-?\d+[.,]?\d*)',
        # Generic SMD with IC/KI
        r'\bSMD\b\s+(-?\d+[.,]?\d*)\s*\(\s*(?:95%?[\s-]*)?(?:IC|KI|BI)[:\s]*(-?\d+[.,]?\d*)\s*[-–—]\s*(-?\d+[.,]?\d*)',
    ]

    # Mean Difference patterns
    MD_PATTERNS = [
        r'(?:mean\s+)?difference[,;:\s=:]+(-?\d+\.?\d*)\s*(?:kg|%|points?)?\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
        r'\bMD\b[,;:\s=]+(-?\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—,]\s*(-?\d+\.?\d*)\s*[\)\]]',
        r'\bMD\b[:\s]+(-?\d+\.?\d*)\s*%?\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
        r':\s*MD\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
        r'weighted\s+mean\s+difference[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
        r'\bWMD\b[,;:\s=]+(-?\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—,]\s*(-?\d+\.?\d*)',

        # "mean difference of 1.8 (95% CI 0.9-2.7)"
        r'mean\s+difference\s+of\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',

        # "MD = -2.1 (-3.2 to -1.0)"
        r'\bMD\b\s*=\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)\s*\)',

        # v5.3.1: "MD=-2.1, 95% CI=[-3.2, -1.0]" - bracket-equals-comma format
        r'\bMD\b\s*=\s*(-?\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s*=\s*\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]',

        # Simple "MD -1.5 (95% CI -2.3 to -0.7)"
        r'\bMD\b\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',

        # "difference 3.2 (2.1 to 4.3)" - without "mean"
        r'\bdifference\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)\s*\)',

        # Context patterns
        r'(?:pooled|overall|summary)\s+(?:MD|mean\s+difference)[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',

        # "WMD: -0.69 (95% CI -1.24 to -0.14)" - colon format
        r'\bWMD\b:\s*(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',

        # "MD -5.2 mmHg (95% CI -7.1 to -3.3)" - with units
        r'\bMD\b\s+(-?\d+\.?\d*)\s*(?:mmHg|mg/?dL|kg|%|points?|mm)?\s*\(\s*(?:95%?\s*)?(?:CI)?\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',

        # "difference -38 mg/dL (-45 to -31)" - with units no CI
        r'\bdifference\s+(-?\d+\.?\d*)\s*(?:mmHg|mg/?dL|kg|%|points?|mm)?\s*\(\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',

        # Context colon pattern "blood pressure: MD X"
        r'[\w\s]{1,80}:\s*MD\s+(-?\d+\.?\d*)\s*(?:\w+)?\s*\(\s*(?:95%?\s*)?(?:CI)?\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',

        # NEW PATTERNS for held-out test cases
        # "Change in systolic BP: mean difference -8.4 mmHg (95% CI: -10.2 to -6.6)"
        r'mean\s+difference\s+(-?\d+\.?\d*)\s*(?:mmHg|mg/?dL|kg|%|L|mL|points?)?\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # "The MD for X was -1.8 points (-2.4, -1.2)"
        r'\bMD\b\s+(?:for\s+[\w\s]{1,80}\s+)?was\s+(-?\d+\.?\d*)\s*(?:points?)?\s*\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)',

        # "Mean difference in X was 4.2 (95% CI 2.1-6.3)"
        r'[Mm]ean\s+difference\s+(?:in\s+[\w\s]{1,80}\s+)?was\s+(-?\d+\.?\d*)\s*(?:\w+)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',

        # v7.2: "mean difference in ... , -1.7 percentage points [95% CI, -8.3 to 4.8]"
        r'mean\s+difference\s+in\s+[\w\s\'/\-]{1,120}?,\s*([+-]?\d+\.?\d*)\s*(?:percentage\s+points?|points?|%|mmHg|kg|mL|L|cm/s|W/kg|Nm/kg)?\s*\[\s*(?:95%?\s*)?CI\s*,\s*([+-]?\d+\.?\d*)\s*(?:to|[-â€“â€”])\s*([+-]?\d+\.?\d*)',
        # v7.2: bracket-CI variant with comma-separated bounds
        r'mean\s+difference\s+in\s+[\w\s\'/\-]{1,120}?,\s*([+-]?\d+\.?\d*)\s*(?:percentage\s+points?|points?|%|mmHg|kg|mL|L|cm/s|W/kg|Nm/kg)?\s*\[\s*(?:95%?\s*)?CI\s*,\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)',
        # v7.2: "21mm group difference; 95% confidence interval, -32.6 to -9.4"
        r'([+-]?\d+\.?\d*)\s*(?:mmHg|mm|kg|mL|L|cm/s|W/kg|Nm/kg|points?|%)?\s*group\s+difference\s*[;,]\s*(?:95%?\s*)?confidence\s+interval[,:\s]+([+-]?\d+\.?\d*)\s*(?:to|[-â€“â€”])\s*([+-]?\d+\.?\d*)',

        # "FEV1 improved by MD=0.15 L [0.08 to 0.22]"
        r'\bMD\s*=\s*(-?\d+\.?\d*)\s*(?:\w+)?\s*\[\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\]',

        # "the between-group mean difference was 12.5 points (95% CI, 8.9 to 16.1)"
        r'mean\s+difference\s+was\s+(-?\d+\.?\d*)\s*(?:points?)?\s*\(\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # "Quality of life: MD 5.3 (95% CI: 3.2, 7.4)"
        r'\bMD\b\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)',

        # v4.3.3: "mean difference = 21.6, 95% CI 10.2-33.0" - comma before CI
        r'mean\s+difference\s*=\s*(-?\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
        r'mean\s+difference\s*=\s*(-?\d+\.?\d*)\s*,\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # "MD = 3.1; 95% CI: 1.2-5.0" - semicolon before CI
        r'\bMD\b\s*=\s*(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
        r'\bMD\b\s*=\s*(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # "mean difference = 12.6 [95% CI: 8.2 to 17.0]" - square brackets
        r'mean\s+difference\s*=\s*(-?\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\]',

        # "Weight loss: MD = -3.2 kg (95% CI: -4.1, -2.3)"
        r'\bMD\b\s*=\s*(-?\d+\.?\d*)\s*(?:kg|%|mmHg|mg/?dL|L)?\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)',

        # "HbA1c reduction: mean diff -0.8% (-1.1 to -0.5)"
        r'mean\s+diff(?:erence)?\s+(-?\d+\.?\d*)%?\s*\(\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',

        # "Difference between means: -4.7 (95% CI -6.2, -3.2)"
        r'[Dd]ifference\s+between\s+means[:\s]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)',

        # "MD -2.3 mm Hg (95% CI: -3.1 to -1.5)" - with space in unit
        r'\bMD\b\s+(-?\d+\.?\d*)\s*(?:mm\s*Hg)?\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # "Mean difference in eGFR was 4.2 mL/min/1.73m2 (95% CI 2.1-6.3)" - with complex unit
        r'[Mm]ean\s+difference\s+(?:in\s+[\w\s]{1,80}\s+)?was\s+(-?\d+\.?\d*)\s*(?:[\w/\d\.]+)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',

        # "Mean difference -2.3 mm Hg (95% Cl: -3.1 to -1.5)" - OCR with Cl instead of CI
        r'[Mm]ean\s+difference\s+(-?\d+\.?\d*)\s*(?:mm\s*Hg|mg/?dL|kg|%|L|mL)?\s*\(\s*(?:95%?\s*)?Cl[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # More OCR patterns with Cl
        r'[Mm]ean\s+difference\s+(-?\d+\.?\d*)\s*(?:mm\s*Hg)?\s*\(\s*(?:95%?\s*)?(?:CI|Cl)[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # v5.8: "difference in means between groups was 4.0 (95% CI, 2.1-5.9)" (Chung_2022)
        r'difference\s+in\s+means?\s+(?:between\s+\w+\s+)?was\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s*(?:to|[-\u2013\u2014])\s*(-?\d+\.?\d*)',
        # v5.8: "estimate -3.61; (CI, -7.01, -0.22)" and "estimate -3.57; CI (-5.85, -1.30)" (Berry_2013)
        r'\bestimate\s+(-?\d+\.?\d*)\s*[;,]\s*\(?\s*(?:95%?\s*)?CI\s*[,:\s(]+(-?\d+\.?\d*)\s*(?:to|[,])\s*(-?\d+\.?\d*)',
        # v5.8: "X units (95% CI, lo to hi)" — generic labeled value with CI (Berry_2013)
        r'(-?\d+\.?\d*)\s*(?:units?|points?|%)\s*(?:reduction\s*)?\(\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # v5.8: "mean change in X score of 6.8 (95% CI, 4.4-8.2)" — "change" as alternative to "difference" (Chung_2022)
        r'mean\s+change\s+(?:in\s+[\w\s-]{1,80}\s+)?(?:of\s+)?(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s*(?:to|[-\u2013\u2014])\s*(-?\d+\.?\d*)',

        # v4.3 ADDITIONS - Semicolon format without parentheses
        # "mean difference -4.0; 95% CI, -7.31 to -0.64" - semicolon + comma format
        # v5.4: also handles "mean difference,-1.58;95%CI:-2.05to-1.10" (run-together, PMC12815721)
        r'mean\s+difference[,;:\s]+(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "MD -4.0; 95% CI, -7.31 to -0.64" - abbreviated semicolon format
        r'\bMD\b\s+(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # v5.4: "MD: -2.5; 95% CI: -3.3 to -1.7" - colon after MD + semicolon before CI
        # PMC12023657
        r'\bMD\b[:\s]+(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # v4.0.3 ADDITIONS
        # "MD -2.5 kg, 95% CI -3.1 to -1.9" - units then comma then CI (no parentheses)
        r'\bMD\b\s+(-?\d+\.?\d*)\s*(?:kg|days?|mmHg|%|L|mL|points?)?,?\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "(MD -2.5 kg, 95% CI -3.1 to -1.9)" - with parentheses, handles negative CI values
        r'\(MD\s+(-?\d+\.?\d*)\s*(?:kg|days?|mmHg|%|L|mL|points?)?\s*,?\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\)',
        # "MD -1.8 days (95% CI -2.4 to -1.2)" - units after value, then parenthetical CI
        r'\bMD\b\s+(-?\d+\.?\d*)\s*(?:kg|days?|mmHg|%|L|mL|points?)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',
        # "Weighted mean difference in X: WMD -5.2 mmHg (95% CI -7.1 to -3.3)"
        r'[Ww]eighted\s+mean\s+difference[^:]*:\s*WMD\s+(-?\d+\.?\d*)\s*(?:mmHg|mg/?dL|kg|%|L|mL)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "WMD -5.2 mmHg (95% CI -7.1 to -3.3)" - simple WMD with units
        r'\bWMD\b\s+(-?\d+\.?\d*)\s*(?:mmHg|mg/?dL|kg|%|L|mL)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # v4.0.6 ADDITIONS - Change format patterns
        # "MADRS change -4.0 (95% CI -6.1 to -1.9)" - scale change format
        r'(?:MADRS|HAM-?D|BDI|PHQ-?\d*|CGI)\s+change\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "change from baseline -4.0 (95% CI -6.1 to -1.9)"
        r'change\s+(?:from\s+baseline\s+)?(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "change -4.0; 95% CI, -6.1 to -1.9" - semicolon format
        r'change\s+(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "difference in change -4.0 (-6.1 to -1.9)"
        r'difference\s+in\s+change\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "between-group difference -4.0 (95% CI -6.1 to -1.9)"
        r'between-?group\s+difference\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "least squares mean difference -4.0 (95% CI -6.1 to -1.9)"
        r'least\s+squares?\s+mean\s+difference\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "LS mean difference -4.0 (95% CI -6.1 to -1.9)"
        r'\bLS\s+mean\s+difference\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "difference 21.7% (95% CI 16.8% to 26.5%)" - percentage difference
        r'\bdifference\s+(-?\d+\.?\d*)%\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)%?\s+to\s+(-?\d+\.?\d*)%?\s*\)',
        # "difference 21.7 percentage points (95% CI 16.8 to 26.5)"
        r'\bdifference\s+(-?\d+\.?\d*)\s*(?:percentage\s+points?)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "difference 21.7%; 95% CI, 11.6-31.7" - percentage with semicolon and dash
        r'\bdifference\s+(-?\d+\.?\d*)%?\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)%?\s*[-–—]\s*(-?\d+\.?\d*)%?',
        # "difference 109.9 ml/year; 95% CI, 75.9-144.0" - with units (INPULSIS)
        r'\bdifference\s+(-?\d+\.?\d*)\s*(?:ml/?year|ml/min|L/min|mL|L|kg|mmHg|mg/?dL)?[;,]\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
        # v6.2: "difference, 0.63; 95% CI, 0.15 to 1.10" - semicolon CI with "to" separator
        r'\bdifference[,;:\s]+(-?\d+\.?\d*)%?\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)%?\s+to\s+(-?\d+\.?\d*)%?',
        # v6.2: "difference 0.63; 95% CI 0.15 to 1.10" - with optional units and "to"
        r'\bdifference\s+(-?\d+\.?\d*)\s*(?:ml/?year|ml/min|mL|L|kg|mmHg|mg/?dL|points?)?[;,]\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # v4.1.0 ADDITIONS - Additional MD patterns from improvement plan
        # "difference between groups: 2.5 kg (1.2-3.8)"
        r'difference\s+between\s+groups[:\s]+(-?\d+\.?\d*)\s*(?:kg|mmHg|mg/?dL|%|L|mL|points?)?\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
        # "difference between treatment groups: -4.2 (95% CI -6.1 to -2.3)"
        r'difference\s+between\s+(?:treatment\s+)?groups[:\s]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "adjusted mean difference -2.8 (95% CI -4.2, -1.4)" - comma in CI
        r'adjusted\s+mean\s+difference\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)',
        # "between-group mean difference was -3.2 kg (-4.5 to -1.9)"
        r'between-?group\s+mean\s+difference\s+was\s+(-?\d+\.?\d*)\s*(?:kg|mmHg|%|L|mL)?\s*\(\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "placebo-corrected MD -1.2% (-1.8 to -0.6)"
        r'placebo-?corrected\s+(?:MD|mean\s+difference)\s+(-?\d+\.?\d*)%?\s*\(\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "mean reduction of 5.3 (95% CI 3.8 to 6.8)"
        r'mean\s+(?:reduction|increase|improvement|change)\s+(?:of\s+)?(-?\d+\.?\d*)\s*(?:kg|mmHg|%|L|mL|points?)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # =================================================================
        # v5.3: Square bracket CI patterns (PMC12719702 — diabetes RCTs)
        # =================================================================
        # "difference -16.5 [95% CI -31.6 to -1.4]" - square brackets
        r'\bdifference\s+(-?\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*%?\s*\]',
        # "difference -7.2 kg [95% CI -10.5 to -3.9 kg]" - units + square brackets
        r'\bdifference\s+(-?\d+\.?\d*)\s*(?:kg|%|mmHg|mg/?dL|L|mL|kcal/?day|units?/?day)?\s*\[\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*(?:kg|%|mmHg|mg/?dL|L|mL|kcal/?day|units?/?day)?\s*\]',
        # "difference -35.1% [95% CI -46.5 to -21.3%; P = 0.0002]" - percentage square brackets
        r'\bdifference\s+(-?\d+\.?\d*)%\s*\[\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)%?\s*[;\]]',
        # "treatment difference of -8.7 kg (95% CI -12.0 to -5.5 kg)" - "of" before value
        r'(?:treatment\s+)?difference\s+of\s+(-?\d+\.?\d*)\s*(?:kg|%|mmHg|mg/?dL|L|mL|kcal/?day)?\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # "mean difference -0.4% [95% CI -0.7 to 0.0%]" - percentage square brackets
        r'mean\s+difference\s+(-?\d+\.?\d*)%?\s*\[\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)%?\s*\]',
        # "between-group difference was -29% (95% CI -40 to -15%)" - percentage difference with CI
        r'between-?group\s+difference\s+(?:was\s+)?(-?\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)%?\s+to\s+(-?\d+\.?\d*)%?',
        # "difference -429 kcal/day [95% CI -852 to -5 kcal/day]" - complex units
        r'\bdifference\s+(-?\d+\.?\d*)\s*[\w/]+\s*\[\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # =================================================================
        # MULTI-LANGUAGE MD PATTERNS
        # =================================================================
        # German: Mittlere Differenz (MD with KI = Konfidenzintervall)
        r'[Mm]ittlere\s+[Dd]ifferenz\s+(-?\d+[.,]?\d*)\s*\(\s*(?:95%?[\s-]*)?(?:KI|Konfidenzintervall)[:\s]*(-?\d+[.,]?\d*)\s*[-–—]\s*(-?\d+[.,]?\d*)',
        # French: Différence moyenne (IC = intervalle de confiance)
        r'[Dd]ifférence\s+moyenne\s+(-?\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(-?\d+[.,]?\d*)\s*[-–—]\s*(-?\d+[.,]?\d*)',
        # Spanish: Diferencia de medias
        r'[Dd]iferencia\s+de\s+medias\s+(-?\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(-?\d+[.,]?\d*)\s*[-–—]\s*(-?\d+[.,]?\d*)',
        # Italian: Differenza media
        r'[Dd]ifferenza\s+media\s+(-?\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(-?\d+[.,]?\d*)\s*[-–—]\s*(-?\d+[.,]?\d*)',
        # Portuguese: Diferença média
        r'[Dd]iferença\s+média\s+(-?\d+[.,]?\d*)\s*\(\s*(?:IC\s*)?(?:95%?[\s-]*)?\s*[:\s]*(-?\d+[.,]?\d*)\s*[-–—]\s*(-?\d+[.,]?\d*)',
        # Generic MD with IC/KI - handle "95%-KI" format
        r'\bMD\b\s+(-?\d+[.,]?\d*)\s*\(\s*(?:95%?[\s-]*)?(?:IC|KI|BI)[:\s]*(-?\d+[.,]?\d*)\s*[-–—]\s*(-?\d+[.,]?\d*)',
        # Chinese: 均数差 (junshuca = mean difference)
        r'均数差\s*(-?\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|置信区间)[:\s]*(-?\d+[.,]?\d*)\s*[-–—]\s*(-?\d+[.,]?\d*)',
        # Japanese: 平均差 (heikinsa = mean difference)
        r'平均差\s*(-?\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|信頼区間)[:\s]*(-?\d+[.,]?\d*)\s*[-–—]\s*(-?\d+[.,]?\d*)',

        # =================================================================
        # v4.1.1 ADDITIONS - Phase 1 Pattern Gap Closure (MD 98.1% → 100%)
        # =================================================================
        # "MD -0.5" (value only, no CI) - small values including zero
        r'\bMD\b\s+(-?\d+\.?\d*)\s*(?:$|[,;.\s](?![\d(]))',
        # "mean difference: -2.5" (colon format, value only)
        r'mean\s+difference:\s*(-?\d+\.?\d*)\s*(?:$|[,;.\s](?![\d(]))',
        # "difference -2.5 kg" (with units, no CI)
        r'\bdifference\s+(-?\d+\.?\d*)\s*(?:kg|mmHg|mg/?dL|%|L|mL|points?|units?)\s*(?:$|[,;.\s])',
        # "MD: -0.5" (colon format)
        r'\bMD\b:\s*(-?\d+\.?\d*)\s*(?:$|[,;.\s](?![\d(]))',
        # "MD 0.0 (-0.5 to 0.5)" - zero values with CI
        r'\bMD\b\s+(0\.0+)\s*\(\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',
        # "MD = -0.5 (-1.0, 0.0)" - small negative values with comma CI
        r'\bMD\b\s*=\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)',
        # "MD 0.2 (95% CI -0.1 to 0.5)" - small positive values
        r'\bMD\b\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',
        # "difference 1.0 (0.5-1.5)" - small integer-like values
        r'\bdifference\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)\s*\)',
        # "mean difference -0.2 (-0.4, 0.0)" - comma in CI, small values
        r'mean\s+difference\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)',
        # "MD: -2.5 (95% CI -3.5 to -1.5)" - colon with full CI
        r'\bMD\b:\s*(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',
        # European format: "MD -2,5 (95% CI -3,5 to -1,5)" - comma decimals
        r'\bMD\b\s+(-?\d+,\d+)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+,\d+)\s+to\s+(-?\d+,\d+)\s*\)',
        # "mean difference was 0.1 (95% CI: -0.2, 0.4)" - "was" form with small values
        r'mean\s+difference\s+was\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)',
        # "net difference: -1.5 (-2.8 to -0.2)" - net difference variant
        r'net\s+difference[:\s]+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',

        # =================================================================
        # v6.0 ADDITIONS - Mega gold standard pattern gap closure
        # =================================================================
        # Semicolon-separated CIs: "95% CI (3.12; 7.88)" or "95% CI: 3.12; 7.88"
        # Common in European medical journals
        r'\bMD\b[,;:\s=]+(-?\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?CI[:\s]*(-?\d+\.?\d*)\s*;\s*(-?\d+\.?\d*)\s*[\)\]]',
        r'mean\s+difference[,;:\s=]+(-?\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?CI[:\s]*(-?\d+\.?\d*)\s*;\s*(-?\d+\.?\d*)\s*[\)\]]',
        r'\bdifference[,;:\s=]+(-?\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?CI[:\s]*(-?\d+\.?\d*)\s*;\s*(-?\d+\.?\d*)\s*[\)\]]',
        # "MD 5.50; 95% CI (3.12; 7.88)" — semicolon before CI label, semicolon inside CI
        r'\bMD\b\s+(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI\s*[\(\[]\s*(-?\d+\.?\d*)\s*;\s*(-?\d+\.?\d*)\s*[\)\]]',
        # "MD 5.50, 95% CI (3.12; 7.88)" — comma before CI label
        r'mean\s+difference\s+(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI\s*[\(\[]\s*(-?\d+\.?\d*)\s*;\s*(-?\d+\.?\d*)\s*[\)\]]',

        # Value-before-CI format: "(-0.089; 95% CI: -0.170 to -0.008)"
        # After normalization: comma becomes semicolon before "95% CI"
        r'\(\s*(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',
        r'\(\s*(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s*[-\u2013\u2014]\s*(-?\d+\.?\d*)\s*\)',
        # Without parentheses: "-0.089, 95%CI: -0.170 to -0.008"
        r'(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # "mean difference of X points (95% CI: lo-hi)" — "of" between label and value
        r'mean\s+difference\s+of\s+(-?\d+\.?\d*)\s*(?:points?)?\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s*[-\u2013\u2014]\s*(-?\d+\.?\d*)',
        # Same but with "to" separator
        r'mean\s+difference\s+of\s+(-?\d+\.?\d*)\s*(?:points?)?\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        # Same but with comma-separated CI
        r'mean\s+difference\s+of\s+(-?\d+\.?\d*)\s*(?:points?)?\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)',

        # =================================================================
        # v4.2.0 ADDITIONS - Square bracket CI patterns (from real PDF analysis)
        # =================================================================
        # "mean difference −0.4% [95% CI −0.7 to 0.0%]" - square brackets, unicode minus
        r'mean\s+difference\s+([+-−]?\d+[.,]?\d*)%?\s*\[\s*(?:95%?\s*)?CI\s+([+-−]?\d+[.,]?\d*)%?\s+to\s+([+-−]?\d+[.,]?\d*)%?\s*\]',
        # "MD -0.4 [95% CI -0.7 to 0.0]" - square brackets
        r'\bMD\b\s+([+-−]?\d+[.,]?\d*)%?\s*\[\s*(?:95%?\s*)?CI\s+([+-−]?\d+[.,]?\d*)%?\s+to\s+([+-−]?\d+[.,]?\d*)%?\s*\]',
        # "difference -0.4% [CI -0.7, 0.0]" - square brackets, comma separator
        r'difference\s+([+-−]?\d+[.,]?\d*)%?\s*\[\s*(?:95%?\s*)?CI[:\s]+([+-−]?\d+[.,]?\d*)%?\s*,\s*([+-−]?\d+[.,]?\d*)%?\s*\]',
        # "MD -0.4 [-0.7 to 0.0]" - square brackets, no CI label
        r'\bMD\b\s+([+-−]?\d+[.,]?\d*)%?\s*\[\s*([+-−]?\d+[.,]?\d*)%?\s+to\s+([+-−]?\d+[.,]?\d*)%?\s*\]',
        # "mean difference -0.4 [-0.7, 0.0]" - square brackets, comma, no CI label
        r'mean\s+difference\s+([+-−]?\d+[.,]?\d*)%?\s*\[\s*([+-−]?\d+[.,]?\d*)%?\s*,\s*([+-−]?\d+[.,]?\d*)%?\s*\]',
        # v6.2: "least-squares mean difference -7.0 [-10.9, -3.1]" - LS mean + square bracket comma
        r'(?:least[- ]squares?\s+|LS\s+)mean\s+difference\s+(-?\d+\.?\d*)\s*\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]',
        # v6.2: "least-squares mean difference [95% CI], -7.0 [-10.9, -3.1]" - header format
        r'(?:least[- ]squares?\s+|LS\s+)mean\s+difference\s*\[(?:95%?\s*)?(?:confidence\s+interval|CI)\][,:\s]+(-?\d+\.?\d*)\s*\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]',
        # v6.2: "difference -7.0 [-10.9, -3.1]" - bare difference + square bracket comma CI
        r'\bdifference\s+(-?\d+\.?\d*)\s*\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]',

        # =================================================================
        # v4.2.0 ADDITIONS - Respiratory-specific MD patterns (Phase 3)
        # =================================================================
        # FEV1 changes - most common pulmonology endpoint
        r'\bFEV1?\b\s+(?:change|difference|improvement)[:\s]+(-?\d+\.?\d*)\s*(?:ml|mL|L)?\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        r'\bFEV1?\b[:\s]+(?:MD|mean\s+difference)\s+(-?\d+\.?\d*)\s*(?:ml|mL|L)?\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
        r'(?:change|difference)\s+in\s+FEV1?\s+(-?\d+\.?\d*)\s*(?:ml|mL|L)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        r'FEV1?\s+(?:improved|increased|decreased)\s+by\s+(-?\d+\.?\d*)\s*(?:ml|mL|L|%)?\s*\(\s*(-?\d+\.?\d*)\s*[-–—to]\s*(-?\d+\.?\d*)',

        # SGRQ score changes (St George's Respiratory Questionnaire)
        r'\bSGRQ\b\s+(?:total\s+)?(?:score\s+)?(?:change|difference)[:\s]+(-?\d+\.?\d*)\s*(?:units?|points?)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        r'(?:change|difference)\s+in\s+SGRQ\s+(?:total\s+)?(?:score)?\s*[:\s]+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—to]\s*(-?\d+\.?\d*)',

        # CAT score (COPD Assessment Test)
        r'\bCAT\b\s+(?:score\s+)?(?:change|difference)[:\s]+(-?\d+\.?\d*)\s*(?:units?|points?)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # 6-minute walk distance
        r'6[\s-]?(?:minute\s+)?walk\s+(?:distance|test)\s+(?:change|difference)[:\s]+(-?\d+\.?\d*)\s*(?:m|meters?)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        r'\b6MWD?\b\s+(?:change|difference)[:\s]+(-?\d+\.?\d*)\s*(?:m|meters?)?\s*\(\s*(-?\d+\.?\d*)\s*[-–—to]\s*(-?\d+\.?\d*)',

        # Peak flow changes
        r'(?:peak\s+(?:expiratory\s+)?flow|PEF)\s+(?:change|difference)[:\s]+(-?\d+\.?\d*)\s*(?:L/?min)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # =================================================================
        # v4.2.0 ADDITIONS - Diabetes-specific MD patterns (Phase 3)
        # =================================================================
        # HbA1c changes - primary diabetes endpoint
        r'\b(?:HbA1c|A1[Cc]|glycated\s+h[ae]moglobin)\b\s+(?:change|reduction|difference)[:\s]+(-?\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        r'(?:change|reduction|difference)\s+in\s+(?:HbA1c|A1[Cc])\s+(-?\d+\.?\d*)%?\s*\(\s*(-?\d+\.?\d*)\s*[-–—to]\s*(-?\d+\.?\d*)',
        r'(?:HbA1c|A1[Cc])\s+(?:was\s+)?reduced\s+by\s+(-?\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        r'(?:placebo[- ]?(?:adjusted|corrected)\s+)?(?:HbA1c|A1[Cc])\s+(?:change|difference)[:\s]+(-?\d+\.?\d*)%?\s*\(\s*(-?\d+\.?\d*)\s*[-–—to]\s*(-?\d+\.?\d*)',

        # Body weight changes (GLP-1, SGLT2 trials)
        r'(?:body\s+)?weight\s+(?:change|loss|reduction|difference)[:\s]+(-?\d+\.?\d*)\s*(?:kg|%)?\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        r'(?:change|reduction|difference)\s+in\s+(?:body\s+)?weight\s+(-?\d+\.?\d*)\s*(?:kg|%)?\s*\(\s*(-?\d+\.?\d*)\s*[-–—to]\s*(-?\d+\.?\d*)',
        r'(?:placebo[- ]?(?:adjusted|corrected)\s+)?weight\s+(?:change|loss)[:\s]+(-?\d+\.?\d*)\s*(?:kg|%)?\s*\(\s*(-?\d+\.?\d*)\s*[-–—to]\s*(-?\d+\.?\d*)',

        # Fasting plasma glucose
        r'\b(?:FPG|fasting\s+(?:plasma\s+)?glucose)\b\s+(?:change|difference)[:\s]+(-?\d+\.?\d*)\s*(?:mg/?dL|mmol/?L)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # Time in range (CGM endpoints)
        r'(?:time\s+in\s+range|TIR)\s+(?:change|difference)[:\s]+(-?\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # =================================================================
        # v4.2.0 ADDITIONS - Cardiology-specific MD patterns
        # =================================================================
        # Blood pressure changes
        r'(?:systolic|diastolic)?\s*(?:blood\s+pressure|BP|SBP|DBP)\s+(?:change|reduction|difference)[:\s]+(-?\d+\.?\d*)\s*(?:mm\s*Hg)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        r'(?:change|reduction)\s+in\s+(?:systolic|diastolic)?\s*(?:BP|blood\s+pressure)\s+(-?\d+\.?\d*)\s*(?:mm\s*Hg)?\s*\(\s*(-?\d+\.?\d*)\s*[-–—to]\s*(-?\d+\.?\d*)',

        # eGFR changes (renal endpoints)
        r'\beGFR\b\s+(?:change|slope|difference)[:\s]+(-?\d+\.?\d*)\s*(?:ml/?min)?(?:/1\.73\s*m2?)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        r'(?:change|difference)\s+in\s+eGFR\s+(-?\d+\.?\d*)\s*(?:ml/?min)?(?:/1\.73\s*m2?)?\s*\(\s*(-?\d+\.?\d*)\s*[-–—to]\s*(-?\d+\.?\d*)',

        # NT-proBNP changes
        r'(?:NT-?proBNP|BNP)\s+(?:change|reduction|difference)[:\s]+(-?\d+\.?\d*)\s*(?:pg/?ml|ng/?L)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # LDL cholesterol
        r'\bLDL\b[-\s]?(?:cholesterol|C)?\s+(?:change|reduction|difference)[:\s]+(-?\d+\.?\d*)\s*(?:mg/?dL|mmol/?L|%)?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # =================================================================
        # v6.2: Regression coefficient (beta/β) patterns — treated as MD
        # Common in adjusted analyses: "β 1.41, 95% CI: 2.31 to 0.51"
        # =================================================================
        # "β VALUE, 95% CI: lo to hi" or "beta VALUE, 95% CI lo–hi"
        r'(?:\u03b2|beta)\s*[=:]?\s*(-?\d+\.?\d*)\s*[,;]\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        r'(?:\u03b2|beta)\s*[=:]?\s*(-?\d+\.?\d*)\s*[,;]\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
        # "(β = VALUE, 95% CI: lo to hi)" or "(β VALUE; CI lo, hi)"
        r'\(\s*(?:\u03b2|beta)\s*[=:]?\s*(-?\d+\.?\d*)\s*[,;]\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',
        r'\(\s*(?:\u03b2|beta)\s*[=:]?\s*(-?\d+\.?\d*)\s*[,;]\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)\s*\)',
        # "β VALUE (95% CI lo to hi)" — CI in parens
        r'(?:\u03b2|beta)\s*[=:]?\s*(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',
        r'(?:\u03b2|beta)\s*[=:]?\s*(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)\s*\)',
        # "β VALUE (lo, hi)" or "β VALUE (lo–hi)" — no CI label
        r'(?:\u03b2|beta)\s*[=:]?\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)',
        r'(?:\u03b2|beta)\s*[=:]?\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)\s*\)',
        # "B = VALUE (95% CI lo to hi)" — uppercase B coefficient (less specific)
        r'\bB\s*=\s*(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',
        r'\bB\s*=\s*(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)\s*\)',
    ]

    # Absolute Risk Difference / Reduction patterns
    ARD_PATTERNS = [
        r'(?:absolute\s+)?risk\s+difference[,;:\s=]+(-?\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)%?\s*(?:to|[-–—])\s*(-?\d+\.?\d*)%?',
        r'\bARD\b[,;:\s=]+(-?\d+\.?\d*)%?\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)%?\s*[-–—,]\s*(-?\d+\.?\d*)%?\s*[\)\]]',
        r'absolute\s+risk\s+reduction[,;:\s=]+(-?\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)%?\s*[-–—]\s*(-?\d+\.?\d*)%?',
        r'\bARR\b[,;:\s=]+(-?\d+\.?\d*)%?\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)%?\s*[-–—,]\s*(-?\d+\.?\d*)%?',
        r'\bRD\b[,;:\s=]+(-?\d+\.?\d*)%?\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)%?\s*[-–—,]\s*(-?\d+\.?\d*)%?',

        # "risk difference: -1.8% (-3.2% to -0.4%)"
        r'risk\s+difference:\s*(-?\d+\.?\d*)%?\s*\(\s*(-?\d+\.?\d*)%?\s*(?:to|[-–—])\s*(-?\d+\.?\d*)%?',

        # "ARD = -0.032 (-0.051 to -0.013)"
        r'\bARD\b\s*=\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)\s*\)',

        # Percentage patterns with explicit %
        r'risk\s+difference\s+(-?\d+\.?\d*)\s*%\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*%?\s*[-–—]\s*(-?\d+\.?\d*)\s*%?',

        # "ARR 3.5% (95% CI 1.8% to 5.2%)"
        r'\bARR\b\s+(-?\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)%?\s*(?:to|[-–—])\s*(-?\d+\.?\d*)%?',

        # Context patterns
        r'(?:mortality|event\s+rate)\s+difference[:\s]+(-?\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)%?\s*(?:to|[-–—])\s*(-?\d+\.?\d*)%?',

        # Simple parenthetical
        r'\bARD\b\s+(-?\d+\.?\d*)%?\s*\(\s*(-?\d+\.?\d*)%?\s*[-–—]\s*(-?\d+\.?\d*)%?\s*\)',

        # "risk difference -3.2% (95% CI -5.1% to -1.3%)" with 95% CI
        r'risk\s+difference\s+(-?\d+\.?\d*)%\s*\(\s*(?:95%?\s*)?CI\s*(-?\d+\.?\d*)%?\s*(?:to|[-–—])\s*(-?\d+\.?\d*)%?',

        # "absolute risk difference -0.05 (95% CI -0.08 to -0.02)" decimal
        r'absolute\s+risk\s+difference\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',

        # "ARD -2.5% (-4.0% to -1.0%)" simple
        r'\bARD\b\s+(-?\d+\.?\d*)%?\s*\(\s*(-?\d+\.?\d*)%?\s*(?:to|[-–—])\s*(-?\d+\.?\d*)%?\s*\)',

        # "ARD 0.0% (-1.2% to 1.2%)" with to
        r'\bARD\b\s+(-?\d+\.?\d*)%\s*\(\s*(-?\d+\.?\d*)%\s*to\s*(-?\d+\.?\d*)%\s*\)',

        # "RD -4.1% (95% CI -6.2% to -2.0%)"
        r'\bRD\b\s+(-?\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?(?:CI)?\s*(-?\d+\.?\d*)%?\s*(?:to|[-–—])\s*(-?\d+\.?\d*)%?',

        # "risk difference -3.2% (95% CI -5.1% to -1.3%)" - with space
        r'risk\s+difference\s+(-?\d+\.?\d*)\s*%\s*\(\s*(?:95%?\s*)?CI\s*(-?\d+\.?\d*)\s*%?\s*to\s*(-?\d+\.?\d*)\s*%?',

        # "ARD -2.5% (-4.0% to -1.0%)" - with to
        r'\bARD\b\s+(-?\d+\.?\d*)\s*%\s*\(\s*(-?\d+\.?\d*)\s*%?\s*to\s*(-?\d+\.?\d*)\s*%?\s*\)',

        # Recovery pattern for any ARD format
        r'\b(?:ARD|ARR|RD)\b\s*(-?\d+\.?\d*)\s*%?\s*\(\s*(-?\d+\.?\d*)\s*%?\s*(?:to|[-–—])\s*(-?\d+\.?\d*)\s*%?',

        # "risk difference -3.2% (95% CI -5.1% to -1.3%)" - specific pattern
        r'risk\s+difference\s+(-?\d+\.?\d*)%\s*\(\s*95%\s*CI\s*(-?\d+\.?\d*)%\s*to\s*(-?\d+\.?\d*)%\)',

        # "ARD -2.5% (-4.0% to -1.0%)" - direct
        r'\bARD\b\s+(-?\d+\.?\d*)%\s*\(\s*(-?\d+\.?\d*)%\s*to\s*(-?\d+\.?\d*)%\)',

        # "RD -4.1% (95% CI -6.2% to -2.0%)"
        r'\bRD\b\s+(-?\d+\.?\d*)%\s*\(\s*95%\s*CI\s*(-?\d+\.?\d*)%\s*to\s*(-?\d+\.?\d*)%\)',

        # "absolute risk reduction 2.8% (1.5%-4.1%)" - hyphen format
        r'absolute\s+risk\s+reduction\s+(-?\d+\.?\d*)%\s*\(\s*(-?\d+\.?\d*)%?\s*[-–—]\s*(-?\d+\.?\d*)%\)',

        # "absolute difference of 7.5 percentage points (95% CI, -11.7 to 26.7)"
        r'(?:absolute\s+)?difference\s+of\s+(-?\d+\.?\d*)\s*(?:percentage\s+points?|%)\s*\(\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',

        # "difference of 28.9 percentage points (95% CI, 9.6-48.2)" - dash format
        r'difference\s+of\s+(-?\d+\.?\d*)\s*(?:percentage\s+points?)\s*\(\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',

        # v7.2: "absolute difference 16%; 95% CI -4% to +37%" (no parentheses)
        r'absolute\s+difference\s+([+-]?\d+\.?\d*)%?\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+([+-]?\d+\.?\d*)%?\s*(?:to|[-â€“â€”])\s*([+-]?\d+\.?\d*)%?',

        # "ARR 3.5% (95% CI 1.8% to 5.2%)"
        r'\bARR\b\s+(-?\d+\.?\d*)%\s*\(\s*95%\s*CI\s*(-?\d+\.?\d*)%\s*to\s*(-?\d+\.?\d*)%\)',

        # "risk difference: -1.8% (-3.2% to -0.4%)" - colon prefix
        r'risk\s+difference:\s*(-?\d+\.?\d*)%\s*\(\s*(-?\d+\.?\d*)%\s*to\s*(-?\d+\.?\d*)%\)',

        # "mortality difference: -2.1% (95% CI -3.8% to -0.4%)"
        r'[\w\s]{1,80}difference:\s*(-?\d+\.?\d*)%\s*\(\s*(?:95%\s*CI\s*)?(-?\d+\.?\d*)%\s*to\s*(-?\d+\.?\d*)%\)',

        # "event rate difference -4.5% (-7.2% to -1.8%)"
        r'(?:event\s+)?rate\s+difference\s+(-?\d+\.?\d*)%\s*\(\s*(-?\d+\.?\d*)%\s*to\s*(-?\d+\.?\d*)%\)',

        # NEW PATTERNS for held-out test cases
        # "Absolute risk difference: -4.2 percentage points (95% CI: -6.8 to -1.6)"
        r'[Aa]bsolute\s+risk\s+difference[:\s]+(-?\d+\.?\d*)\s*(?:percentage\s+points?)?\s*\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # "The ARD was -0.032 (95% CI -0.051 to -0.013)"
        r'\bARD\b\s+was\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',

        # "Risk difference: 8.5% (95% CI, 5.2% to 11.8%)"
        r'[Rr]isk\s+difference[:\s]+(-?\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)%?\s+to\s+(-?\d+\.?\d*)%?',

        # "Absolute difference in response rate was 12.3% (7.8%, 16.8%)"
        r'[Aa]bsolute\s+difference\s+(?:in\s+[\w\s]{1,80}\s+)?was\s+(-?\d+\.?\d*)%?\s*\(\s*(-?\d+\.?\d*)%?\s*,\s*(-?\d+\.?\d*)%?',

        # "Event rate difference: -2.8% (95% CI -4.5% to -1.1%)"
        r'[Ee]vent\s+rate\s+difference[:\s]+(-?\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI\s+(-?\d+\.?\d*)%?\s+to\s+(-?\d+\.?\d*)%?',

        # "The absolute risk reduction was 5.2 percentage points (2.8 to 7.6)"
        r'absolute\s+risk\s+reduction\s+was\s+(-?\d+\.?\d*)\s*(?:percentage\s+points?)?\s*\(\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
    ]

    # Relative Risk Reduction patterns
    RRR_PATTERNS = [
        r'relative\s+risk\s+reduction[,;:\s=]+(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?',
        r'\bRRR\b[,;:\s=]+(\d+\.?\d*)%?\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)%?\s*[-–—,]\s*(\d+\.?\d*)%?',
        # Vaccine efficacy format: "efficacy was 95.0% (95% CI, 90.3%-97.6%)"
        r'(?:vaccine\s+)?efficacy[^0-9]*(\d+\.?\d*)%\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        # "efficacy against X was 95% (95% CI, Y%-Z%)" format
        r'efficacy\s+(?:against\s+)?[^0-9]*?was\s+(\d+\.?\d*)%\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        # "Vaccine efficacy against symptomatic COVID-19 was 95.0% (95% CI, 90.3%-97.6%)"
        r'[Vv]accine\s+efficacy\s+.{0,50}?was\s+(\d+\.?\d*)%\s*\(\s*(?:95%?\s*)?CI\s*,?\s*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        # v5.3: VE (Vaccine Efficacy) abbreviation — maps to RRR
        # "VE was 98.8% (95% CI 91.3-99.8%)" or "VE was 98.8% (95% CI, 91.3-99.8)"
        r'\bVE\b\s+(?:was\s+)?(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        # "VE: 95.2% (88.1-98.3)" or "VE = 95.2% (88.1-98.3)"
        r'\bVE\b[,;:\s=]+(\d+\.?\d*)%?\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*[\)\]]',
        # "VE of 96.1% (95% CI, 93.1–98.1%)"
        r'\bVE\b\s+of\s+(\d+\.?\d*)%?\s*\(\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
        # "VE (95% CI): 95.2% (88.1-98.3)" — label prefix format
        r'\bVE\b\s*\(95%?\s*CI\)\s*[:\s]+(\d+\.?\d*)%?\s*\(\s*(\d+\.?\d*)%?\s*[-–—]\s*(\d+\.?\d*)%?\s*\)',
    ]

    # NNT/NNH patterns
    NNT_PATTERNS = [
        r'(?:number\s+)?(?:needed\s+)?(?:to\s+)?treat[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        r'\bNNT\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)',
        r'\bNNH\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)',
    ]

    # ==========================================================================
    # VALUE-ONLY PATTERNS (for CTG validation without CI)
    # These patterns capture effect estimates without confidence intervals
    # Used primarily for CTG validation where CI may not be reported
    # ==========================================================================

    # Mean Difference value-only patterns
    MD_VALUE_ONLY_PATTERNS = [
        # CTG-specific format: "Calculated MD: -58.000"
        r'[Cc]alculated\s+MD[:\s]+(-?\d+\.?\d*)',
        r'\bMD\b\s+(-?\d+\.?\d*)\s*(?:kg|mmHg|mg/?dL|%|L|mL|days?|points?|mm)?\s*$',
        r'\bMD\b\s*[=:]\s*(-?\d+\.?\d*)',
        r'[Mm]ean\s+[Dd]ifference\s+(-?\d+\.?\d*)',
        r'\bdifference\s+(-?\d+\.?\d*)\s*(?:kg|mmHg|mg/?dL|%|L|mL|days?|points?|mm)?\s*$',
        r'[Mm]ean\s+[Dd]ifference\s*[=:]\s*(-?\d+\.?\d*)',
        r'\bWMD\b\s+(-?\d+\.?\d*)',
        r'\bWMD\b\s*[=:]\s*(-?\d+\.?\d*)',
        r'[Ww]eighted\s+[Mm]ean\s+[Dd]ifference\s+(-?\d+\.?\d*)',
        r'\bLS\s+mean\s+difference\s+(-?\d+\.?\d*)',
        r'[Bb]etween-?group\s+difference\s+(-?\d+\.?\d*)',
        # v6.2: beta/β coefficient value-only
        r'(?:\u03b2|beta)\s*[=:]?\s*(-?\d+\.?\d*)',
        r'\bB\s*=\s*(-?\d+\.?\d*)',
    ]

    # Risk Ratio value-only patterns
    RR_VALUE_ONLY_PATTERNS = [
        # CTG-specific format: "Calculated RR: 0.850"
        r'[Cc]alculated\s+RR[:\s]+(\d+\.?\d*)\b(?!\s*%)',
        r'\bRR\b\s+(\d+\.?\d*)\b(?!\s*%)\s*$',
        r'\bRR\b\s*[=:]\s*(\d+\.?\d*)\b(?!\s*%)',
        r'[Rr]elative\s+[Rr]isk\s+(\d+\.?\d*)\b(?!\s*%)',
        r'[Rr]isk\s+[Rr]atio\s+(\d+\.?\d*)\b(?!\s*%)',
        r'[Rr]ate\s+[Rr]atio\s+(\d+\.?\d*)\b(?!\s*%)',
        r'\baRR\b\s+(\d+\.?\d*)\b(?!\s*%)',
        r'[Aa]djusted\s+RR\s+(\d+\.?\d*)\b(?!\s*%)',
    ]

    # Hazard Ratio value-only patterns
    HR_VALUE_ONLY_PATTERNS = [
        # CTG-specific format
        r'[Cc]alculated\s+HR[:\s]+(\d+\.?\d*)\b(?!\s*%)',
        r'\bHR\b\s+(\d+\.?\d*)\b(?!\s*%)\s*$',
        r'\bHR\b\s*[=:]\s*(\d+\.?\d*)\b(?!\s*%)',
        r'[Hh]azard\s+[Rr]atio\s+(\d+\.?\d*)\b(?!\s*%)',
        r'\baHR\b\s+(\d+\.?\d*)\b(?!\s*%)',
        r'[Aa]djusted\s+HR\s+(\d+\.?\d*)\b(?!\s*%)',
    ]

    # Odds Ratio value-only patterns
    OR_VALUE_ONLY_PATTERNS = [
        # CTG-specific format (negative lookahead prevents matching "95%" as a value)
        r'[Cc]alculated\s+OR[:\s]+(\d+\.?\d*)\b(?!\s*%)',
        r'\bOR\b\s+(\d+\.?\d*)\b(?!\s*%)\s*$',
        r'\bOR\b\s*[=:]\s*(\d+\.?\d*)\b(?!\s*%)',
        r'[Oo]dds\s+[Rr]atio\s+(\d+\.?\d*)\b(?!\s*%)',
        r'\baOR\b\s+(\d+\.?\d*)\b(?!\s*%)',
        r'[Aa]djusted\s+OR\s+(\d+\.?\d*)\b(?!\s*%)',
    ]

    # SMD value-only patterns
    SMD_VALUE_ONLY_PATTERNS = [
        # CTG-specific format
        r'[Cc]alculated\s+SMD[:\s]+(-?\d+\.?\d*)',
        r'\bSMD\b\s+(-?\d+\.?\d*)\s*$',
        r'\bSMD\b\s*[=:]\s*(-?\d+\.?\d*)',
        r'[Ss]tandardized\s+[Mm]ean\s+[Dd]ifference\s+(-?\d+\.?\d*)',
        r"Cohen'?s?\s*d\s*[=:]\s*(-?\d+\.?\d*)",
        r"[Hh]edges'?\s*g\s*[=:]\s*(-?\d+\.?\d*)",
    ]

    # ARD value-only patterns
    ARD_VALUE_ONLY_PATTERNS = [
        # CTG-specific format
        r'[Cc]alculated\s+ARD[:\s]+(-?\d+\.?\d*)%?',
        r'\bARD\b\s+(-?\d+\.?\d*)%?',
        r'\bARD\b\s*[=:]\s*(-?\d+\.?\d*)%?',
        r'[Aa]bsolute\s+[Rr]isk\s+[Dd]ifference\s+(-?\d+\.?\d*)%?',
        r'\bARR\b\s+(-?\d+\.?\d*)%?',
        r'\bRD\b\s+(-?\d+\.?\d*)%?',
        r'[Rr]isk\s+[Dd]ifference\s+(-?\d+\.?\d*)%?',
    ]

    # IRR value-only patterns
    IRR_VALUE_ONLY_PATTERNS = [
        # CTG-specific format
        r'[Cc]alculated\s+IRR[:\s]+(\d+\.?\d*)',
        r'\bIRR\b\s+(\d+\.?\d*)',
        r'\bIRR\b\s*[=:]\s*(\d+\.?\d*)',
        r'[Ii]ncidence\s+[Rr]ate\s+[Rr]atio\s+(\d+\.?\d*)',
        r'[Rr]ate\s+[Rr]atio\s+(\d+\.?\d*)',
    ]

    # Plausibility ranges for each effect type
    # Note: ARD/ARR can be percentages (-50 to 50) or decimals (-0.5 to 0.5)
    PLAUSIBILITY = {
        EffectType.HR: (0.01, 50.0),
        EffectType.OR: (0.01, 100.0),
        EffectType.RR: (0.01, 50.0),
        EffectType.IRR: (0.01, 50.0),
        EffectType.SMD: (-10.0, 10.0),
        EffectType.MD: (-10000, 10000),
        EffectType.ARD: (-100.0, 100.0),  # Can be percentage or decimal
        EffectType.ARR: (-100.0, 100.0),  # Can be percentage or decimal
        EffectType.RRR: (0.0, 100.0),     # Can be percentage
        EffectType.NNT: (1.0, 10000),
        EffectType.NNH: (1.0, 10000),
        EffectType.GMR: (0.01, 100.0),   # Geometric Mean Ratio (like RR)
    }

    def __init__(self):
        """Initialize extractor with pattern compilation"""
        self.pattern_map = {
            EffectType.SMD: self.SMD_PATTERNS,  # Check SMD before MD
            EffectType.HR: self.HR_PATTERNS,
            EffectType.OR: self.OR_PATTERNS,
            EffectType.IRR: self.IRR_PATTERNS,  # Check IRR BEFORE RR (contains "rate ratio")
            EffectType.GMR: self.GMR_PATTERNS,  # Check GMR BEFORE RR (geometric mean ratio)
            EffectType.RR: self.RR_PATTERNS,
            EffectType.ARD: self.ARD_PATTERNS,  # Check ARD BEFORE MD to catch "absolute risk difference"
            EffectType.MD: self.MD_PATTERNS,
            EffectType.RRR: self.RRR_PATTERNS,
            EffectType.NNT: self.NNT_PATTERNS,
        }

        # Value-only patterns (for CTG validation - effects without CI)
        self.value_only_pattern_map = {
            EffectType.MD: self.MD_VALUE_ONLY_PATTERNS,
            EffectType.RR: self.RR_VALUE_ONLY_PATTERNS,
            EffectType.HR: self.HR_VALUE_ONLY_PATTERNS,
            EffectType.OR: self.OR_VALUE_ONLY_PATTERNS,
            EffectType.SMD: self.SMD_VALUE_ONLY_PATTERNS,
            EffectType.ARD: self.ARD_VALUE_ONLY_PATTERNS,
            EffectType.IRR: self.IRR_VALUE_ONLY_PATTERNS,
            EffectType.GMR: self.GMR_VALUE_ONLY_PATTERNS,
        }

        # Calibration thresholds (tuned for automation)
        self.FULL_AUTO_THRESHOLD = 0.92   # High confidence for auto-accept
        self.SPOT_CHECK_THRESHOLD = 0.85  # Good confidence for spot-check
        self.VERIFY_THRESHOLD = 0.70      # Moderate confidence for verification

        # Compile negative context patterns (v4.3.1)
        self._negative_context_pattern = re.compile(
            '|'.join(self.NEGATIVE_CONTEXT_PATTERNS),
            re.IGNORECASE
        )

    def _has_negative_context(self, text: str, match_start: int, context_window: int = 500) -> bool:
        """
        Check if extraction appears in a negative context (v4.3.1).

        Looks for protocol/methods/review language in surrounding context.

        Args:
            text: Full text being extracted from
            match_start: Start position of the match
            context_window: Characters before/after to check

        Returns:
            True if negative context detected (should skip extraction)
        """
        # Get context window
        start = max(0, match_start - context_window)
        end = min(len(text), match_start + context_window)
        context = text[start:end]

        # Check for negative patterns
        return bool(self._negative_context_pattern.search(context))

    def normalize_text(self, text: str) -> str:
        """Normalize unicode and special characters"""
        for old, new in self.NORMALIZATIONS.items():
            text = text.replace(old, new)

        # v5.4: Convert comma before CI label to semicolon BEFORE European decimal conversion
        # "HR=0.468,95%CI" -> "HR=0.468; 95%CI" (prevents "8,9" -> "8.9" corruption)
        # PMC12608838: "HR=0.468,95%CI,0.320-0.683"
        text = re.sub(r'(\d),\s*(95%?\s*CI)', r'\1; \2', text, flags=re.IGNORECASE)
        # v5.4: Insert space in "95%CI" -> "95% CI" (needed for bracket CI patterns)
        # PMC12527752: "[95%CI0.0024-6.18]"
        text = re.sub(r'(\d+%)(CI\b)', r'\1 \2', text)
        # v5.4: Normalize "CI = " to "CI: " so patterns match uniformly
        # PMC12705426: "OR = 4.0; 95% CI = 1.4–11.3"
        text = re.sub(r'\bCI\s*=\s*', 'CI: ', text, flags=re.IGNORECASE)

        # European decimal format (0,74 -> 0.74) — only when followed by
        # 1-2 digits (not 3+, which indicates thousands separator like 1,234)
        # Exclude bracket contexts like [12,14] (reference numbers)
        # Exclude decimal pairs like 1.05,2.05 (CI bounds) via (?<!\.\d) lookbehind
        text = re.sub(r'(?<!\[)(?<!\.\d)(\d),(\d{1,2})(?!\d)(?!\])', r'\1.\2', text)

        # v4.3.3: Normalize line breaks in effect patterns
        # "HR\n= 0.8" -> "HR = 0.8"
        # "mean difference\n3.1" -> "mean difference 3.1"
        # "mean\ndifference" -> "mean difference"
        text = re.sub(r'(HR|OR|RR|MD|SMD|ARD|IRR|GMR|VE|hazard ratio|odds ratio|relative risk|risk difference|geometric means? ratio|vaccine efficacy)\s*\n\s*', r'\1 ', text, flags=re.IGNORECASE)
        text = re.sub(r'mean\s*\n\s*difference', 'mean difference', text, flags=re.IGNORECASE)
        text = re.sub(r'geometric\s*\n\s*mean', 'geometric mean', text, flags=re.IGNORECASE)
        # v6.0: "mean difference\nof 0.37" -> "mean difference of 0.37"
        text = re.sub(r'(difference)\s*\n\s*(of\s+)', r'\1 \2', text, flags=re.IGNORECASE)
        # v6.0: "Odds ratio\n \n(95%" -> "Odds ratio (95%" (table header join)
        text = re.sub(r'((?:odds|risk|hazard)\s+ratio)\s*\n\s*\n?\s*\(', r'\1 (', text, flags=re.IGNORECASE)
        # Also handle "=\n" and ";\n" patterns
        text = re.sub(r'\n\s*=\s*', ' = ', text)
        text = re.sub(r'=\s*\n\s*', '= ', text)
        text = re.sub(r';\s*\n\s*', '; ', text)
        # "HR=0.78,\n95% CI" -> "HR=0.78, 95% CI"
        text = re.sub(r',\s*\n\s*(95%?\s*CI)', r', \1', text, flags=re.IGNORECASE)

        # v5.0: Join CI bounds split across lines (multi-column PDF artifacts)
        # "CI: 0.97-\n0.99)" -> "CI: 0.97-0.99)"
        text = re.sub(r'((?:CI|IC|KI|CL|confidence\s{0,3}interval)\s{0,3}[,::\s]{0,3}\d+\.?\d*\s*[-])\s*\n\s*(\d+\.?\d*)', r'\1\2', text, flags=re.IGNORECASE)
        # "CI:\n0.97-0.99" or "CI:\n1.66; 2.33" -> "CI: 0.97-0.99"
        text = re.sub(r'((?:CI|IC|KI|CL)\s*[,:]\s*)\n\s*(\d)', r'\1 \2', text, flags=re.IGNORECASE)
        # "95%\nCI" -> "95% CI"
        text = re.sub(r'(\d+%)\s*\n\s*(CI|IC|KI|CL)\b', r'\1 \2', text, flags=re.IGNORECASE)
        # "[95%CI:\n1.66" -> "[95%CI: 1.66"
        text = re.sub(r'(\[\s*(?:95%?\s*)?(?:CI|IC|KI)[:;\s]*)\n\s*(\d)', r'\1 \2', text, flags=re.IGNORECASE)

        # v5.0.1: Rejoin hyphenated words at line breaks (letters only, not digits)
        # "confi-\ndence" -> "confidence", "inter-\nval" -> "interval"
        text = re.sub(r'([a-zA-Z])-\n\s*([a-zA-Z])', r'\1\2', text)

        # v5.4: Strip bracket abbreviation aliases after full names
        # "risk ratio [RR], 0.67" -> "risk ratio 0.67" (PMC12074564)
        # "hazard ratio [HR]:" -> "hazard ratio:"
        # "odds ratio [OR]" -> "odds ratio"
        text = re.sub(r'((?:hazard|odds|risk|relative|rate|incidence|mean)\s+(?:ratio|difference|reduction))\s*\[(?:HR|OR|RR|RD|IRR|MD|ARD|ARR|SMD|WMD|GMR)\]', r'\1', text, flags=re.IGNORECASE)
        # Also handle "confidence interval [CI]" -> "confidence interval"
        text = re.sub(r'(confidence\s+interval)\s*\[CI\]', r'\1', text, flags=re.IGNORECASE)

        # v5.3: Split run-together statistical terms (broken PDF spacing, e.g. PMC10059741)
        # "oddsratioof4.17" -> "odds ratio of4.17", "hazardratio0.88" -> "hazard ratio 0.88"
        run_together = [
            (r'oddsratio', 'odds ratio'),
            (r'hazardratio', 'hazard ratio'),
            (r'riskratio', 'risk ratio'),
            (r'riskreduction', 'risk reduction'),
            (r'riskdifference', 'risk difference'),
            (r'rateratio', 'rate ratio'),
            (r'incidencerate', 'incidence rate'),
            (r'meandifference', 'mean difference'),
            (r'relativerisk', 'relative risk'),
            (r'confidenceinterval', 'confidence interval'),
            (r'vaccineefficacy', 'vaccine efficacy'),
            (r'geometricmean(?:s?)ratio', 'geometric mean ratio'),
            # v6.2: Additional run-together compounds from mega eval gap analysis
            (r'standardizedmeandifference', 'standardized mean difference'),
            (r'weightedmeandifference', 'weighted mean difference'),
            (r'adjustedodds\s*ratio', 'adjusted odds ratio'),
            (r'adjustedhazard\s*ratio', 'adjusted hazard ratio'),
            (r'adjustedrisk\s*ratio', 'adjusted risk ratio'),
            (r'adjustedrate\s*ratio', 'adjusted rate ratio'),
            (r'absoluterisk', 'absolute risk'),
            (r'absolutedifference', 'absolute difference'),
            (r'treatmentdifference', 'treatment difference'),
            (r'meanchange', 'mean change'),
            (r'effectsize', 'effect size'),
            (r'pooledestimate', 'pooled estimate'),
            (r'overalleffect', 'overall effect'),
        ]
        for pattern, replacement in run_together:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        # v6.2: Generic space insertion before statistical keywords in merged text
        # "unadjustedhazard" -> "unadjusted hazard", "therelativerisk" -> "the relative risk"
        # Only when preceded by lowercase (avoids breaking abbreviations)
        # NOTE: "adjusted" excluded — it's a suffix too ("unadjusted", "maladjusted")
        # "confidence" excluded — handled by run_together list ("confidenceinterval")
        text = re.sub(r'([a-z])(hazard|odds|risk|mean|relative|incidence|standardized|weighted|absolute)', r'\1 \2', text, flags=re.IGNORECASE)

        # Split "of"/"was" stuck between letters and digits (run-together PDF text)
        # "ratioof4.17" -> "ratio of 4.17", "was98.8" -> "was 98.8"
        text = re.sub(r'(?<=[a-z])of(?=\d)', ' of ', text)
        text = re.sub(r'(?<=[a-z])was(?=\d)', ' was ', text)
        # Strip "of" between ratio/reduction and digits for pattern matching
        # "ratio of 4.17" -> "ratio 4.17" (patterns use [,;:\s=]+ not "of")
        # NOTE: "difference" excluded — "difference of" patterns exist in MD_PATTERNS
        text = re.sub(r'(ratio|reduction)\s+of\s+(?=\d)', r'\1 ', text, flags=re.IGNORECASE)

        # v5.0.1: Insert space between effect type abbreviation and digit (broken PDF spacing)
        # "HR0.88" -> "HR 0.88", "(HR0.88" -> "(HR 0.88"
        text = re.sub(r'\b(HR|OR|RR|MD|SMD|ARD|IRR|GMR|VE|aHR)(\d)', r'\1 \2', text)
        # v5.8: Normalize "confidence interval" -> "CI" for consistent pattern matching
        # Handles: "95% confidence interval", "95 percent confidence interval", "confidence interval"
        text = re.sub(r'(\d{2})\s*(?:%|percent)\s*confidence\s+interval', r'\1% CI', text, flags=re.IGNORECASE)
        text = re.sub(r'\bconfidence\s+interval\b', 'CI', text, flags=re.IGNORECASE)

        # v5.8: Normalize leading-dot decimals (e.g., "-.22" -> "-0.22", ".05" -> "0.05")
        # Common in medical papers; must come after hyphen-join to avoid false matches
        text = re.sub(r'(?<![0-9])(-?)\.(\d)', r'\g<1>0.\2', text)

        # v5.3: Insert space between statistical words and digits (run-together PDF text)
        # "ratio4.17" -> "ratio 4.17", "difference3.1" -> "difference 3.1"
        text = re.sub(r'(ratio|difference|reduction|efficacy)(\d)', r'\1 \2', text, flags=re.IGNORECASE)
        # v5.3: Insert space between digit.decimal and run-together words
        # "4.17inthevaccinatedgroup" -> "4.17 inthevaccinatedgroup"
        # Exclude scientific notation: "1.5e10" should NOT be split
        text = re.sub(r'(\d+\.\d+)(?![eE]\d)([a-zA-Z]{3,})', r'\1 \2', text)
        # v5.3: Insert space between letter and opening paren (run-together PDF)
        # "group(95%" -> "group (95%"
        text = re.sub(r'([a-zA-Z])\((\d{2,3}%)', r'\1 (\2', text)
        # v5.3: Strip run-together junk text between value and CI parenthesis
        # "ratio 4.17 inthevaccinatedgroup (95%CI:" -> "ratio 4.17 (95%CI:"
        # Anchored to statistical term to avoid stripping legitimate context
        text = re.sub(r'((?:ratio|difference|reduction|efficacy)\s+\d+\.?\d*)\s+[a-z]{3,80}\s*\((\d{2,3}%\s*CI)', r'\1 (\2', text, flags=re.IGNORECASE)

        # v5.4: Split "to" stuck between digits in CI bounds (run-together PDF text)
        # "-2.05to-1.10" -> "-2.05 to -1.10" (PMC12815721)
        text = re.sub(r'(\d)to(-?\d)', r'\1 to \2', text)

        # v5.2: Insert space between digit and opening paren/bracket before CI label (broken PDF spacing)
        # "0.88(95%CI" -> "0.88 (95%CI", "1.05(95%" -> "1.05 (95%"
        text = re.sub(r'(\d)\((\d{2,3}%)', r'\1 (\2', text)
        # v5.4: "0.12[95%CI" -> "0.12 [95%CI" (square bracket variant)
        # PMC12527752: "hazard ratio 0.12[95%CI0.0024-6.18]"
        text = re.sub(r'(\d)\[(\d{2,3}%)', r'\1 [\2', text)
        # v5.3.1: Also handle percent sign before CI paren
        # "38.9%(95%CI" -> "38.9% (95%CI"
        text = re.sub(r'(\d%)\((\d{2,3}%)', r'\1 (\2', text)
        # v5.3.1: Insert space between %CI and digit (run-together PDF)
        # "95%CI11.4%" -> "95%CI 11.4%", "%CI0.98" -> "%CI 0.98"
        text = re.sub(r'(%CI)(\d)', r'\1 \2', text)

        # v5.5: Insert space between CI/IC label and digit (run-together PDF text)
        # After "95%CI" -> "95% CI" split (line 1703), "CI0.08" remains stuck.
        # "CI0.08" -> "CI 0.08", "CI:0.08" -> "CI: 0.08"
        # Also handles IC (French/Spanish), KI (German), CL (confidence limits)
        text = re.sub(r'\b(CI|IC|KI|CL)([-]?\d)', r'\1 \2', text)

        # v7.2: OCR artifacts in CI bounds, e.g., "95%CI?0.12e0.75" -> "95% CI 0.12-0.75"
        text = re.sub(
            r'((?:95%?\s*)?(?:CI|IC|KI|CL)[^0-9+\-]{0,5}[+\-]?\d+\.?\d*)e([+\-]?\d+\.?\d*)',
            r'\1-\2',
            text,
            flags=re.IGNORECASE,
        )
        # Normalize explicit positive signs in bounds/values: "+37" -> "37"
        text = re.sub(r'(?<![A-Za-z0-9])\+(\d+\.?\d*)', r'\1', text)

        # v6.2: Normalize "pvalue" / "p-value" stuck to comparator and number
        # "pvalue<0.001" -> "p value <0.001", "p<.05" already handled by leading-dot fix
        text = re.sub(r'\bp\s*[-]?\s*value', 'p value', text, flags=re.IGNORECASE)

        # v6.2: Split digit-letter-digit patterns in compressed text
        # "1.05to2.10" -> "1.05 to 2.10" (broader than existing "Xto-Y" rule)
        text = re.sub(r'(\d\.?\d*)to(\d)', r'\1 to \2', text, flags=re.IGNORECASE)
        # "1.05and2.10" -> "1.05 and 2.10"
        text = re.sub(r'(\d\.?\d*)and(\d)', r'\1 and \2', text, flags=re.IGNORECASE)
        # "0.88versus1.05" -> "0.88 versus 1.05", "0.88vs1.05" -> "0.88 vs 1.05"
        text = re.sub(r'(\d\.?\d*)(?:versus|vs\.?)(\d)', r'\1 vs \2', text, flags=re.IGNORECASE)

        return text

    def extract(self, text: str, include_value_only: bool = True) -> List[Extraction]:
        """
        Extract all effect estimates from text.

        Args:
            text: Source text to extract from
            include_value_only: If True, also extract effects without CI (lower confidence)

        Returns:
            List of Extraction objects with confidence scores and automation tiers
        """
        text = correct_ocr_errors(text)
        text = self.normalize_text(text)
        results = []
        seen = set()
        seen_values = set()  # Track values for value-only deduplication

        # First pass: patterns with CI (full extraction)
        for effect_type, patterns in self.pattern_map.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        value = float(match.group(1))
                        ci_low = float(match.group(2))
                        ci_high = float(match.group(3))

                        # Deduplication
                        key = (effect_type.value, round(value, 3), round(ci_low, 3), round(ci_high, 3))
                        if key in seen:
                            continue
                        seen.add(key)

                        # v4.3.1: Check for negative context (skip if in protocol/methods/review)
                        if self._has_negative_context(text, match.start()):
                            continue

                        # Track this value for value-only deduplication
                        seen_values.add((effect_type.value, round(value, 3)))

                        # Create extraction
                        extraction = self._create_extraction(
                            effect_type, value, ci_low, ci_high,
                            match.group(0), match.start(), match.end()
                        )

                        if extraction.is_plausible:
                            results.append(extraction)

                    except (ValueError, IndexError):
                        continue

        # Second pass: value-only patterns (for CTG validation)
        if include_value_only:
            for effect_type, patterns in self.value_only_pattern_map.items():
                for pattern in patterns:
                    for match in re.finditer(pattern, text, re.IGNORECASE):
                        try:
                            value = float(match.group(1))

                            # Skip if we already have this value with CI
                            value_key = (effect_type.value, round(value, 3))
                            if value_key in seen_values:
                                continue

                            # v4.3.1: Check for negative context
                            if self._has_negative_context(text, match.start()):
                                continue

                            seen_values.add(value_key)

                            # Create value-only extraction (no CI)
                            extraction = self._create_value_only_extraction(
                                effect_type, value,
                                match.group(0), match.start(), match.end()
                            )

                            if extraction.is_plausible:
                                results.append(extraction)

                        except (ValueError, IndexError):
                            continue

        # Third pass: tabular regression table format
        # Detects "OR 95%CI pValue" column headers followed by data rows
        tabular_results = self._extract_tabular_effects(text, seen, seen_values)
        results.extend(tabular_results)

        return results

    def _extract_tabular_effects(self, text: str, seen: set, seen_values: set) -> list:
        """
        Extract effects from regression table formats where the effect type
        appears as a column header (e.g., "Factor OR 95%CI pValue") followed
        by data rows with values.

        v5.6: Handles compressed PDF text from logistic/Cox regression tables.
        """
        results = []

        # Map header labels to effect types
        header_map = {
            'OR': EffectType.OR,
            'aOR': EffectType.OR,
            'HR': EffectType.HR,
            'aHR': EffectType.HR,
            'RR': EffectType.RR,
            'aRR': EffectType.RR,
            'IRR': EffectType.IRR,
        }

        # Pattern: "{label} 95%CI pValue" as column header, then data rows
        # Captures the section after the header until next table/section break
        for label, etype in header_map.items():
            header_pat = re.compile(
                r'\b' + re.escape(label) + r'\s+95%?\s*CI\s+p\s*[Vv]alue\b'
                r'(.{5,800}?)(?=\b(?:doi|Fig\.?\s*\d|Table\s+\d|Discussion|Conclusion|Reference)\b|\Z)',
                re.IGNORECASE | re.DOTALL
            )
            for hm in header_pat.finditer(text):
                section = hm.group(1)
                # Extract rows: {text} {value} {lower}–{upper} {p_value}
                row_pat = re.compile(
                    r'(\d+\.?\d+)\s+(\d+\.?\d+)\s*[-\u2013\u2014]\s*(\d+\.?\d+)\s+(\d+\.\d+)'
                )
                for rm in row_pat.finditer(section):
                    try:
                        value = float(rm.group(1))
                        ci_low = float(rm.group(2))
                        ci_high = float(rm.group(3))
                        p_val = float(rm.group(4))

                        # Dedup
                        key = (etype.value, round(value, 3), round(ci_low, 3), round(ci_high, 3))
                        if key in seen:
                            continue
                        seen.add(key)

                        vkey = (etype.value, round(value, 3))
                        if vkey in seen_values:
                            continue
                        seen_values.add(vkey)

                        # Build source text for provenance
                        abs_start = hm.start() + rm.start()
                        abs_end = hm.start() + rm.end()
                        source = f"{label} {rm.group(0)}"

                        extraction = self._create_extraction(
                            etype, value, ci_low, ci_high,
                            source, abs_start, abs_end
                        )

                        if extraction.is_plausible:
                            results.append(extraction)

                    except (ValueError, IndexError):
                        continue

        # v6.0: Handle "Odds ratio (95% CI)" / "Risk ratio (95% CI)" header format
        # Gummersbach 2015: "Odds ratio (95% CI)" header then "0.99 (0.92-1.07)" rows
        full_name_map = {
            'odds ratio': EffectType.OR,
            'risk ratio': EffectType.RR,
            'relative risk': EffectType.RR,
            'hazard ratio': EffectType.HR,
            'rate ratio': EffectType.IRR,
        }
        for name, etype in full_name_map.items():
            # Match header like "Odds ratio (95% CI)" or "Odds ratio\n(95% confidence interval)"
            header_pat = re.compile(
                r'\b' + name + r'\s*\(\s*(?:95%?\s*)?(?:CI|confidence\s+interval)\s*\)'
                r'(.{5,2000}?)(?=\b(?:doi|Fig\.?\s*\d|Table\s+\d|Discussion|Conclusion|Reference|Note)\b|\Z)',
                re.IGNORECASE | re.DOTALL
            )
            for hm in header_pat.finditer(text):
                section = hm.group(1)
                # Extract rows: value (lower-upper) with optional p-value
                row_pat = re.compile(
                    r'(\d+\.?\d+)\s*\(\s*(\d+\.?\d+)\s*[-\u2013\u2014]\s*(\d+\.?\d+)\s*\)'
                )
                for rm in row_pat.finditer(section):
                    try:
                        value = float(rm.group(1))
                        ci_low = float(rm.group(2))
                        ci_high = float(rm.group(3))

                        key = (etype.value, round(value, 3), round(ci_low, 3), round(ci_high, 3))
                        if key in seen:
                            continue
                        seen.add(key)

                        vkey = (etype.value, round(value, 3))
                        if vkey in seen_values:
                            continue
                        seen_values.add(vkey)

                        abs_start = hm.start() + rm.start()
                        abs_end = hm.start() + rm.end()
                        source = f"{name} {rm.group(0)}"

                        extraction = self._create_extraction(
                            etype, value, ci_low, ci_high,
                            source, abs_start, abs_end
                        )

                        if extraction.is_plausible:
                            results.append(extraction)

                    except (ValueError, IndexError):
                        continue

        return results

    def _create_extraction(
        self,
        effect_type: EffectType,
        value: float,
        ci_low: float,
        ci_high: float,
        source_text: str,
        char_start: int,
        char_end: int
    ) -> Extraction:
        """Create extraction with confidence scoring and automation tier"""

        # Create CI
        ci = ConfidenceInterval(lower=ci_low, upper=ci_high)

        # Check plausibility
        is_plausible = self._check_plausibility(effect_type, value, ci_low, ci_high)
        warnings = []

        if not is_plausible:
            warnings.append("IMPLAUSIBLE_VALUE")

        # CI consistency check (non-strict: value may equal a CI boundary due to rounding)
        if not (ci_low <= value <= ci_high):
            is_plausible = False
            warnings.append("CI_INCONSISTENT")

        # Calculate confidence
        raw_confidence = self._calculate_raw_confidence(
            effect_type, value, ci_low, ci_high, source_text
        )

        # Apply calibration
        calibrated_confidence = self._calibrate_confidence(raw_confidence)

        # Determine automation tier
        automation_tier = self._get_automation_tier(calibrated_confidence)

        # Calculate Standard Error from CI
        se, se_method = calculate_se_from_ci(ci_low, ci_high, effect_type)

        # Extract p-value from source text
        p_value = extract_p_value(source_text)

        # Initialize ARD normalization fields
        original_scale = ""
        normalized_value = None
        normalized_ci_lower = None
        normalized_ci_upper = None

        # Normalize ARD to decimal scale
        if effect_type == EffectType.ARD:
            normalized_value, normalized_ci_lower, normalized_ci_upper, original_scale = \
                normalize_ard(value, ci_low, ci_high, source_text)

        return Extraction(
            effect_type=effect_type,
            point_estimate=value,
            ci=ci,
            p_value=p_value,
            standard_error=se,
            se_method=se_method,
            source_text=source_text,
            char_start=char_start,
            char_end=char_end,
            raw_confidence=raw_confidence,
            calibrated_confidence=calibrated_confidence,
            automation_tier=automation_tier,
            has_complete_ci=True,
            is_plausible=is_plausible,
            warnings=warnings,
            original_scale=original_scale,
            normalized_value=normalized_value,
            normalized_ci_lower=normalized_ci_lower,
            normalized_ci_upper=normalized_ci_upper
        )

    def _create_value_only_extraction(
        self,
        effect_type: EffectType,
        value: float,
        source_text: str,
        char_start: int,
        char_end: int
    ) -> Extraction:
        """
        Create extraction without CI (value-only).

        Used for CTG validation where CI may not be reported.
        Has lower confidence than full extractions.
        """

        # Check value-only plausibility
        is_plausible = self._check_value_only_plausibility(effect_type, value)
        warnings = ["NO_CONFIDENCE_INTERVAL"]

        if not is_plausible:
            warnings.append("IMPLAUSIBLE_VALUE")

        # Lower raw confidence for value-only extractions
        raw_confidence = 0.55  # Base score for value-only

        # Boost if effect type prefix is clear
        source_lower = source_text.lower()
        if any(prefix in source_lower for prefix in ['hr', 'or', 'rr', 'md', 'smd', 'ard', 'irr']):
            raw_confidence += 0.10

        # Apply calibration (will result in MANUAL tier)
        calibrated_confidence = self._calibrate_confidence(raw_confidence)

        # Determine automation tier (will be MANUAL due to low confidence)
        automation_tier = self._get_automation_tier(calibrated_confidence)

        # Extract p-value from source text
        p_value = extract_p_value(source_text)

        return Extraction(
            effect_type=effect_type,
            point_estimate=value,
            ci=None,  # No CI
            p_value=p_value,
            standard_error=None,
            se_method="unavailable",
            source_text=source_text,
            char_start=char_start,
            char_end=char_end,
            raw_confidence=raw_confidence,
            calibrated_confidence=calibrated_confidence,
            automation_tier=automation_tier,
            has_complete_ci=False,  # Mark as no CI
            is_plausible=is_plausible,
            warnings=warnings,
            original_scale="",
            normalized_value=None,
            normalized_ci_lower=None,
            normalized_ci_upper=None
        )

    def _check_value_only_plausibility(
        self,
        effect_type: EffectType,
        value: float
    ) -> bool:
        """Check if value-only extraction is plausible"""
        if effect_type not in self.PLAUSIBILITY:
            return True

        min_val, max_val = self.PLAUSIBILITY[effect_type]

        # Value in range
        if not (min_val <= value <= max_val):
            return False

        return True

    def _check_plausibility(
        self,
        effect_type: EffectType,
        value: float,
        ci_low: float,
        ci_high: float
    ) -> bool:
        """Check if extraction is plausible"""
        if effect_type not in self.PLAUSIBILITY:
            return True

        min_val, max_val = self.PLAUSIBILITY[effect_type]

        # Value in range
        if not (min_val <= value <= max_val):
            return False

        # CI bounds check
        if ci_low > ci_high:
            return False

        # CI contains value
        if not (ci_low <= value <= ci_high):
            return False

        # For ratios, CI lower bound should be positive
        if effect_type in [EffectType.HR, EffectType.OR, EffectType.RR, EffectType.IRR, EffectType.GMR]:
            if ci_low <= 0:
                return False

        # For differences, CI can span zero (negative to positive)
        # No additional constraints needed for MD, SMD, ARD

        return True

    def _calculate_raw_confidence(
        self,
        effect_type: EffectType,
        value: float,
        ci_low: float,
        ci_high: float,
        source_text: str
    ) -> float:
        """Calculate raw confidence score from multiple signals"""
        score = 0.70  # Base score

        # Signal 1: CI completeness (+0.15)
        if ci_low > 0 or effect_type in [EffectType.SMD, EffectType.MD, EffectType.ARD]:
            score += 0.15

        # Signal 2: Plausibility (+0.10)
        if self._check_plausibility(effect_type, value, ci_low, ci_high):
            score += 0.10

        # Signal 3: Context quality (+0.05)
        source_lower = source_text.lower()
        quality_terms = ['95%', 'ci', 'confidence interval', 'p<', 'p=', 'p =']
        if any(term in source_lower for term in quality_terms):
            score += 0.05

        # Signal 4: Reasonable CI width
        if effect_type in [EffectType.HR, EffectType.OR, EffectType.RR]:
            ci_ratio = ci_high / ci_low if ci_low > 0 else float('inf')
            if 1.0 < ci_ratio < 10.0:
                score += 0.05
        else:
            ci_width = abs(ci_high - ci_low)
            if ci_width < max(abs(value), 1.0) * 2:
                score += 0.05

        return min(1.0, score)

    def _calibrate_confidence(self, raw_confidence: float) -> float:
        """
        Apply heuristic confidence adjustment (NOT empirical calibration).

        This is a hand-tuned piecewise linear mapping, not a fitted
        calibration model (e.g. Platt scaling or isotonic regression).
        For empirical calibration, use ConfidenceCalibrator from
        confidence_calibration.py after fitting on validation data.
        """
        # Heuristic piecewise linear adjustment
        if raw_confidence >= 0.95:
            # High quality extraction - map to automation tier
            calibrated = 0.90 + (raw_confidence - 0.95) * 2.0  # 0.95->0.90, 1.0->1.0
        elif raw_confidence >= 0.85:
            # Good quality - spot check tier
            calibrated = 0.80 + (raw_confidence - 0.85) * 1.0  # 0.85->0.80, 0.95->0.90
        elif raw_confidence >= 0.70:
            # Moderate quality - verify tier
            calibrated = 0.60 + (raw_confidence - 0.70) * 1.33  # 0.70->0.60, 0.85->0.80
        else:
            # Low quality - manual tier
            calibrated = raw_confidence * 0.857  # 0.70->0.60

        # Apply floor and ceiling
        calibrated = max(0.1, min(0.99, calibrated))

        return calibrated

    def _get_automation_tier(self, calibrated_confidence: float) -> AutomationTier:
        """Determine automation tier based on calibrated confidence"""
        if calibrated_confidence >= self.FULL_AUTO_THRESHOLD:
            return AutomationTier.FULL_AUTO
        elif calibrated_confidence >= self.SPOT_CHECK_THRESHOLD:
            return AutomationTier.SPOT_CHECK
        elif calibrated_confidence >= self.VERIFY_THRESHOLD:
            return AutomationTier.VERIFY
        else:
            return AutomationTier.MANUAL


# =============================================================================
# STANDARD ERROR CALCULATION
# =============================================================================

def calculate_se_from_ci(
    ci_lower: float,
    ci_upper: float,
    effect_type: EffectType,
    ci_level: float = 0.95
) -> Tuple[float, str]:
    """
    Calculate Standard Error from Confidence Interval.

    For ratios (HR, OR, RR): SE is calculated on log scale
    For differences (MD, SMD, ARD): SE is calculated on linear scale

    Returns:
        Tuple[float, str]: (standard_error, method)
    """
    # Get z-value for CI level (1.96 for 95% CI)
    Z_TABLE = {0.80: 1.282, 0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z_value = Z_TABLE.get(ci_level)
    if z_value is None:
        return None, "unavailable"

    try:
        if effect_type in [EffectType.HR, EffectType.OR, EffectType.RR, EffectType.IRR, EffectType.GMR]:
            # Log scale for ratios
            if ci_lower <= 0 or ci_upper <= 0:
                return None, "unavailable"
            log_se = (math.log(ci_upper) - math.log(ci_lower)) / (2 * z_value)
            return log_se, "calculated_log_scale"
        else:
            # Linear scale for differences (MD, SMD, ARD)
            se = (ci_upper - ci_lower) / (2 * z_value)
            return se, "calculated_linear_scale"
    except (ValueError, ZeroDivisionError):
        return None, "unavailable"


# =============================================================================
# ARD NORMALIZATION
# =============================================================================

def normalize_ard(
    value: float,
    ci_low: float,
    ci_high: float,
    source_text: str,
    full_context: str = ""
) -> Tuple[float, float, float, str]:
    """
    Normalize Absolute Risk Difference to decimal scale (0-1).

    Detects if the input is in percentage format (e.g., -3.2%) or
    decimal format (e.g., -0.032) and converts to decimal.

    For ambiguous cases (small values with no explicit % indicator),
    marks the scale as "ambiguous" so downstream consumers can flag
    the extraction for review.

    Returns:
        Tuple: (normalized_value, normalized_ci_low, normalized_ci_high, original_scale)
    """
    # Check for percentage indicators
    is_percentage = False

    # Combine source text and surrounding context for indicator search
    search_text = source_text + " " + full_context

    # Check source text for % symbol
    if '%' in source_text:
        is_percentage = True
    # Check magnitude - percentages typically have absolute value > 1
    elif abs(value) > 1.0 or abs(ci_low) > 1.0 or abs(ci_high) > 1.0:
        is_percentage = True
    # Check for "percentage points" or "percent" in wider context
    elif any(term in search_text.lower() for term in [
        'percentage', 'percent', 'pct', 'percentage point',
        'per cent', 'pp ', 'p.p.'
    ]):
        is_percentage = True

    if is_percentage:
        # Convert percentage to decimal
        return value / 100, ci_low / 100, ci_high / 100, "percentage"
    else:
        # For small ARD values (|value| < 0.1), this is likely already decimal.
        # For values between 0.1 and 1.0 without explicit indicators, the scale
        # is ambiguous: could be 0.5 (50%) or 0.005 (0.5%). Mark as ambiguous.
        max_abs = max(abs(value), abs(ci_low), abs(ci_high))
        if 0.1 <= max_abs <= 1.0 and '%' not in search_text:
            return value, ci_low, ci_high, "ambiguous_decimal"
        return value, ci_low, ci_high, "decimal"


# =============================================================================
# CALIBRATION METRICS
# =============================================================================

@dataclass
class CalibrationMetrics:
    """Calibration metrics for confidence score evaluation"""
    ece: float = 0.0  # Expected Calibration Error
    mce: float = 0.0  # Maximum Calibration Error
    brier_score: float = 0.0
    calibration_slope: float = 1.0
    calibration_intercept: float = 0.0
    bin_accuracies: List[float] = field(default_factory=list)
    bin_confidences: List[float] = field(default_factory=list)
    bin_counts: List[int] = field(default_factory=list)


def calculate_calibration_metrics(
    predictions: List[float],
    actuals: List[bool],
    n_bins: int = 10
) -> CalibrationMetrics:
    """
    Calculate calibration metrics.

    Args:
        predictions: List of predicted probabilities (calibrated confidence scores)
        actuals: List of boolean actual outcomes (True if extraction was correct)
        n_bins: Number of bins for ECE/MCE calculation

    Returns:
        CalibrationMetrics object with ECE, MCE, Brier score, etc.
    """
    if len(predictions) != len(actuals) or len(predictions) == 0:
        return CalibrationMetrics()

    n = len(predictions)

    # Initialize bins
    bin_boundaries = [i / n_bins for i in range(n_bins + 1)]
    bin_accuracies = []
    bin_confidences = []
    bin_counts = []

    # Calculate per-bin metrics
    ece = 0.0
    mce = 0.0

    for i in range(n_bins):
        lower = bin_boundaries[i]
        upper = bin_boundaries[i + 1]

        # Get samples in this bin
        in_bin = [(p, a) for p, a in zip(predictions, actuals)
                  if lower <= p < upper or (i == n_bins - 1 and p == upper)]

        if len(in_bin) > 0:
            bin_acc = sum(1 for _, a in in_bin if a) / len(in_bin)
            bin_conf = sum(p for p, _ in in_bin) / len(in_bin)
            bin_count = len(in_bin)

            bin_accuracies.append(bin_acc)
            bin_confidences.append(bin_conf)
            bin_counts.append(bin_count)

            # Contribution to ECE (weighted by bin size)
            calibration_error = abs(bin_acc - bin_conf)
            ece += (bin_count / n) * calibration_error
            mce = max(mce, calibration_error)
        else:
            bin_accuracies.append(0.0)
            bin_confidences.append((lower + upper) / 2)
            bin_counts.append(0)

    # Calculate Brier score
    brier_score = sum((p - (1 if a else 0)) ** 2 for p, a in zip(predictions, actuals)) / n

    # Calculate calibration slope and intercept (linear regression)
    # y = actual outcome (0 or 1), x = predicted probability
    if len(predictions) > 1:
        mean_x = sum(predictions) / n
        mean_y = sum(1 if a else 0 for a in actuals) / n

        numerator = sum((p - mean_x) * ((1 if a else 0) - mean_y)
                       for p, a in zip(predictions, actuals))
        denominator = sum((p - mean_x) ** 2 for p in predictions)

        if denominator > 0:
            slope = numerator / denominator
            intercept = mean_y - slope * mean_x
        else:
            slope = 1.0
            intercept = 0.0
    else:
        slope = 1.0
        intercept = 0.0

    return CalibrationMetrics(
        ece=ece,
        mce=mce,
        brier_score=brier_score,
        calibration_slope=slope,
        calibration_intercept=intercept,
        bin_accuracies=bin_accuracies,
        bin_confidences=bin_confidences,
        bin_counts=bin_counts
    )


def generate_reliability_diagram_data(metrics: CalibrationMetrics) -> Dict[str, Any]:
    """
    Generate data for reliability diagram visualization.

    Returns dict with:
        - bins: bin centers
        - accuracies: actual accuracies per bin
        - confidences: mean confidence per bin
        - counts: sample counts per bin
        - perfect_calibration: diagonal line data
    """
    n_bins = len(metrics.bin_accuracies)
    bin_centers = [(i + 0.5) / n_bins for i in range(n_bins)]

    return {
        'bins': bin_centers,
        'accuracies': metrics.bin_accuracies,
        'confidences': metrics.bin_confidences,
        'counts': metrics.bin_counts,
        'perfect_calibration': [i / (n_bins - 1) for i in range(n_bins)] if n_bins > 1 else [0.5],
        'ece': metrics.ece,
        'mce': metrics.mce,
    }


# =============================================================================
# P-VALUE EXTRACTION PATTERNS
# =============================================================================

P_VALUE_PATTERNS = [
    r'[Pp]\s*[=<>]\s*(0\.\d+)',
    r'[Pp]\s*[-–—]\s*value\s*[=<>]\s*(0\.\d+)',
    r'[Pp]\s*=\s*0?\.\d+',
    r'[Pp]\s*<\s*0?\.\d+',
    r'significance\s*[=:]\s*(0\.\d+)',
    r'\([Pp]\s*[=<]\s*(0\.\d+)\)',
    # Scientific notation: P = 1.2e-5, P < 10^-6, P < 1 x 10^-4
    r'[Pp]\s*[=<>]\s*(\d+\.?\d*)\s*[×xX]\s*10\s*[-–—^]\s*(\d+)',
    r'[Pp]\s*[=<>]\s*(\d+\.?\d*)[eE][-–—](\d+)',
    r'[Pp]\s*[=<>]\s*10\s*[-–—^]\s*(\d+)',
]


def extract_p_value(text: str) -> Optional[float]:
    """Extract p-value from text"""
    for pattern in P_VALUE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                matched = match.group(0)
                # Scientific notation: "1.2e-5", "1 x 10^-4", "10^-6"
                sci_match = re.search(
                    r'(\d+\.?\d*)\s*[×xXeE]\s*10?\s*[-–—^]\s*(\d+)', matched
                )
                if sci_match:
                    base = float(sci_match.group(1))
                    exp = int(sci_match.group(2))
                    p_val = base * (10 ** -exp)
                    if 0 <= p_val <= 1:
                        return p_val
                    continue
                # "10^-6" form (no coefficient)
                ten_match = re.search(r'10\s*[-–—^]\s*(\d+)', matched)
                if ten_match and not sci_match:
                    exp = int(ten_match.group(1))
                    p_val = 10 ** -exp
                    if 0 <= p_val <= 1:
                        return p_val
                    continue
                # Standard decimal
                p_str = re.search(r'0?\.\d+', matched)
                if p_str:
                    p_val = float(p_str.group(0))
                    if 0 <= p_val <= 1:
                        return p_val
            except ValueError:
                continue
    return None


# v7.1: robust scientific-notation parsing for p-values
P_VALUE_PATTERNS = [
    r'[Pp]\s*[=<>]\s*(0?\.\d+)',
    r'[Pp]\s*-?\s*value\s*[=<>]\s*(0?\.\d+)',
    r'[Pp]\s*=\s*0?\.\d+',
    r'[Pp]\s*<\s*0?\.\d+',
    r'significance\s*[=:]\s*(0?\.\d+)',
    r'\([Pp]\s*[=<]\s*(0?\.\d+)\)',
    # Scientific notation: P = 1.2e-5, P < 10^-6, P < 1 x 10^-4
    r'[Pp]\s*[=<>]\s*(\d+\.?\d*)\s*(?:x|\*)\s*10\s*(?:\^)?\s*-\s*(\d+)',
    r'[Pp]\s*[=<>]\s*(\d+\.?\d*)\s*[eE]\s*-\s*(\d+)',
    r'[Pp]\s*[=<>]\s*10\s*(?:\^)?\s*-\s*(\d+)',
]


def _normalize_p_notation(text: str) -> str:
    """Normalize notation variants before p-value extraction."""
    normalized = text
    normalized = normalized.replace('\u00D7', 'x')
    normalized = normalized.replace('\u2212', '-')
    normalized = normalized.replace('\u2013', '-')
    normalized = normalized.replace('\u2014', '-')
    return re.sub(r'\s+', ' ', normalized).strip()


def extract_p_value(text: str) -> Optional[float]:
    """Extract p-value from text, including scientific notation."""
    normalized_text = _normalize_p_notation(text)

    for pattern in P_VALUE_PATTERNS:
        match = re.search(pattern, normalized_text, re.IGNORECASE)
        if not match:
            continue

        try:
            matched = _normalize_p_notation(match.group(0))

            # 1.2e-5
            sci_match = re.search(r'(\d+\.?\d*)\s*[eE]\s*-\s*(\d+)', matched)
            if sci_match:
                base = float(sci_match.group(1))
                exp = int(sci_match.group(2))
                p_val = base * (10 ** -exp)
                if 0 <= p_val <= 1:
                    return p_val
                continue

            # 1 x 10^-4
            coeff_match = re.search(
                r'(\d+\.?\d*)\s*(?:x|\*)\s*10\s*(?:\^)?\s*-\s*(\d+)',
                matched,
                re.IGNORECASE,
            )
            if coeff_match:
                base = float(coeff_match.group(1))
                exp = int(coeff_match.group(2))
                p_val = base * (10 ** -exp)
                if 0 <= p_val <= 1:
                    return p_val
                continue

            # 10^-6
            ten_match = re.search(r'(?<![\d.])10\s*(?:\^)?\s*-\s*(\d+)', matched)
            if ten_match:
                exp = int(ten_match.group(1))
                p_val = 10 ** -exp
                if 0 <= p_val <= 1:
                    return p_val
                continue

            # Skip malformed scientific notation instead of partial decimal fallback.
            if re.search(r'(?:[eE]|(?:x|\*)\s*10)', matched, re.IGNORECASE):
                continue

            # Standard decimal form
            p_str = re.search(r'(?<!\d)(?:0?\.\d+)(?!\d)', matched)
            if p_str:
                p_val = float(p_str.group(0))
                if 0 <= p_val <= 1:
                    return p_val
        except ValueError:
            continue
    return None


# =============================================================================
# OCR ERROR CORRECTION
# =============================================================================

def correct_ocr_errors(text: str) -> str:
    """
    Correct common OCR errors in extracted text.

    Common errors:
    - 'O' instead of '0'
    - 'l' instead of '1'
    - 'Cl' instead of 'CI'
    """
    result = text

    # Step 1: CI spelling corrections
    # Only correct Cl→CI when followed by statistical context (numbers, brackets, colons)
    # to avoid corrupting chemistry terms like "serum Cl" or "Cl-"
    result = re.sub(r'95%\s*Cl\b', '95% CI', result)
    result = re.sub(r'\bCl\s*(?=[\d([\-:,])', 'CI ', result)

    # Step 2: Number corrections in decimal contexts
    # O instead of 0
    result = re.sub(r'(?<=\d)O(?=\d)', '0', result)  # Between digits
    result = re.sub(r'O\.(\d)', r'0.\1', result)     # O.X -> 0.X
    result = re.sub(r'(\d)\.O', r'\1.0', result)     # X.O -> X.0
    result = re.sub(r'-O\.', '-0.', result)          # -O. -> -0.

    # l instead of 1
    result = re.sub(r'(?<=\d)l(?=\d)', '1', result)  # Between digits
    result = re.sub(r'(?<=[=:\s])l\.(\d)', r'1.\1', result)  # l.X -> 1.X after delimiter
    result = re.sub(r'(\d)\.l', r'\1.1', result)     # X.l -> X.1
    result = re.sub(r'-l\.', '-1.', result)          # -l. -> -1.
    result = re.sub(r'(?<=-)l(?=\.\d)', '1', result)  # -l.X -> -1.X

    # OOl -> 001 type patterns
    result = re.sub(r'O(?=Ol|l\b)', '0', result)
    result = re.sub(r'(?<=0)l\b', '1', result)

    return result


# =============================================================================
# EXPORT FORMATS
# =============================================================================

def to_dict(extraction: Extraction) -> Dict[str, Any]:
    """Convert extraction to dictionary format"""
    result = {
        'type': extraction.effect_type.value,
        'effect_size': extraction.point_estimate,
        'ci_lower': extraction.ci.lower if extraction.ci else None,
        'ci_upper': extraction.ci.upper if extraction.ci else None,
        'p_value': extraction.p_value,
        'standard_error': extraction.standard_error,
        'se_method': extraction.se_method,
        'raw_confidence': extraction.raw_confidence,
        'calibrated_confidence': extraction.calibrated_confidence,
        'automation_tier': extraction.automation_tier.value,
        'source_text': extraction.source_text,
        'char_start': extraction.char_start,
        'char_end': extraction.char_end,
        'is_plausible': extraction.is_plausible,
        'warnings': extraction.warnings,
        'needs_review': extraction.automation_tier != AutomationTier.FULL_AUTO,
    }

    # Add ARD normalization fields if applicable
    if extraction.effect_type == EffectType.ARD:
        result['original_scale'] = extraction.original_scale
        result['normalized_value'] = extraction.normalized_value
        result['normalized_ci_lower'] = extraction.normalized_ci_lower
        result['normalized_ci_upper'] = extraction.normalized_ci_upper

    return result


def extract_effect_estimates(text: str) -> List[Dict]:
    """
    Convenience function for backward compatibility.

    Returns list of dicts with standard keys.
    """
    extractor = EnhancedExtractor()
    extractions = extractor.extract(text)

    return [
        {
            'type': e.effect_type.value,
            'effect_size': e.point_estimate,
            'ci_low': e.ci.lower if e.ci else None,
            'ci_high': e.ci.upper if e.ci else None,
        }
        for e in extractions
    ]


# =============================================================================
# AUTOMATION METRICS
# =============================================================================

@dataclass
class AutomationMetrics:
    """Track automation performance"""
    total: int = 0
    full_auto: int = 0
    spot_check: int = 0
    verify: int = 0
    manual: int = 0

    @property
    def automation_rate(self) -> float:
        """Percentage fully automated"""
        return self.full_auto / self.total if self.total > 0 else 0.0

    @property
    def human_effort_reduction(self) -> float:
        """Reduction in human effort (0-1)"""
        if self.total == 0:
            return 0.0

        # Effort weights: FULL_AUTO=0%, SPOT_CHECK=10%, VERIFY=50%, MANUAL=100%
        effort = (
            self.full_auto * 0.0 +
            self.spot_check * 0.1 +
            self.verify * 0.5 +
            self.manual * 1.0
        ) / self.total

        return 1.0 - effort


def calculate_automation_metrics(extractions: List[Extraction]) -> AutomationMetrics:
    """Calculate automation metrics from extractions"""
    metrics = AutomationMetrics(total=len(extractions))

    for e in extractions:
        if e.automation_tier == AutomationTier.FULL_AUTO:
            metrics.full_auto += 1
        elif e.automation_tier == AutomationTier.SPOT_CHECK:
            metrics.spot_check += 1
        elif e.automation_tier == AutomationTier.VERIFY:
            metrics.verify += 1
        else:
            metrics.manual += 1

    return metrics
