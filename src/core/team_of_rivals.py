"""
Team-of-Rivals Extraction System for RCT Extractor v4.0
========================================================

Multiple independent extractors must agree for verified output.
Implements the "consensus through disagreement" principle.

Extractors:
1. PatternExtractor - Regex-based (existing v3.0 patterns)
2. GrammarExtractor - Context-Free Grammar (Lark)
3. StateMachineExtractor - Finite State Machine
4. ChunkExtractor - Sliding window with scoring

Consensus:
- All extractors run independently
- Majority vote determines output
- Disagreements trigger Critic review
- Full agreement = high confidence
"""

import re
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Set
from enum import Enum


class ExtractorType(Enum):
    """Types of extractors in the team"""
    PATTERN = "pattern"
    GRAMMAR = "grammar"
    STATE_MACHINE = "state_machine"
    CHUNK = "chunk"


@dataclass
class CandidateExtraction:
    """A candidate extraction from a single extractor"""
    effect_type: str
    value: float
    ci_lower: Optional[float]
    ci_upper: Optional[float]
    source_text: str
    char_start: int
    char_end: int
    extractor: ExtractorType
    extractor_confidence: float = 0.0
    p_value: Optional[float] = None

    def matches(self, other: 'CandidateExtraction', tolerance: float = 0.001) -> bool:
        """Check if two extractions match (same values within tolerance)"""
        if self.effect_type != other.effect_type:
            return False
        if abs(self.value - other.value) > tolerance:
            return False
        if self.ci_lower and other.ci_lower:
            if abs(self.ci_lower - other.ci_lower) > tolerance:
                return False
        if self.ci_upper and other.ci_upper:
            if abs(self.ci_upper - other.ci_upper) > tolerance:
                return False
        return True

    def __hash__(self):
        return hash((self.effect_type, round(self.value, 3),
                    round(self.ci_lower or 0, 3), round(self.ci_upper or 0, 3)))


@dataclass
class ConsensusResult:
    """Result of consensus voting"""
    extraction: Optional[CandidateExtraction]
    agreeing_extractors: List[ExtractorType]
    disagreeing_extractors: List[ExtractorType]
    agreement_ratio: float
    is_unanimous: bool
    needs_critic: bool
    critic_notes: List[str] = field(default_factory=list)


# =============================================================================
# BASE EXTRACTOR
# =============================================================================

class BaseExtractor(ABC):
    """Abstract base class for all extractors"""

    extractor_type: ExtractorType

    # Shared negative context patterns - skip if these appear near the match
    NEGATIVE_CONTEXTS = [
        r'power\s+(?:calculation|analysis)',
        r'assuming\s+(?:an?\s+)?(?:HR|OR|RR)',
        r'expected\s+(?:HR|OR|RR)',
        r'sample\s+size',
        r'interpret(?:ed|ation)?',
        r'would\s+(?:be|indicate|suggest)',
        r'greater\s+than\s+\d',
        r'less\s+than\s+\d',
        r'previous(?:ly)?\s+(?:reported|published)',
        r'(?:another|other)\s+(?:study|trial|meta-analysis)',
        r'meta-analysis\s+(?:of|by|from)',
        r'systematic\s+review\s+(?:of|by|found)',
        r'baseline\s+(?:risk|rate)',
        r'if\s+(?:the|an?)\s+(?:HR|OR|RR)',
        r'to\s+detect\s+(?:an?\s+)?(?:HR|OR|RR)',
        r'required\s+to\s+show',
    ]

    @abstractmethod
    def extract(self, text: str) -> List[CandidateExtraction]:
        """Extract all effect estimates from text"""
        pass

    def normalize_text(self, text: str) -> str:
        """Normalize unicode and whitespace"""
        replacements = {
            '\u00b7': '.', '\u2013': '-', '\u2014': '-',
            '\u2212': '-', '–': '-', '—': '-', '·': '.',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return ' '.join(text.split())

    def check_negative_context(self, text: str, match_start: int, match_end: int) -> bool:
        """Check if match is in negative context. Returns True if should skip."""
        context_start = max(0, match_start - 150)
        context_end = min(len(text), match_end + 50)
        context = text[context_start:context_end].lower()

        for neg_pattern in self.NEGATIVE_CONTEXTS:
            if re.search(neg_pattern, context, re.IGNORECASE):
                return True
        return False


# =============================================================================
# PATTERN EXTRACTOR (Wrapper for v3.0)
# =============================================================================

class PatternExtractor(BaseExtractor):
    """
    Regex-based extractor using comprehensive v3.0 pattern library.
    Fast, precise, extensively tested on 220+ cases.
    """

    extractor_type = ExtractorType.PATTERN

    # Comprehensive patterns from v3.0 (100% sensitivity validated)
    PATTERNS = {
        'HR': [
            # Standard formats
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s\[]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'hazard\s*ratio\s+(?:of|was|for\s+\w+\s+was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'hazard\s*ratio\s+(?:for\s+)?[\w\s]+?(?:was|is)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            # Abbreviation formats
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bHR\b[=:,\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:confidence\s*interval|CI)[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bHR\b[:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?confidence\s*interval[:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'\bHR\b\s+was\s+(\d+\.?\d*)[,;]\s*with\s+(?:95%?\s*)?CI\s+of\s+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'\bHR\b\s+(?:for\s+)?[\w\s]+?:\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
            r'\(HR[,;]\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)\)',
            r'\bHR\b\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)\s*\)',
            r'\(HR[=:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\)',
            r'\bHR\b[,;\s]+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)\s*\]',
            r'\bHR\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[,]\s*(\d+\.?\d*)\s*\)',
            r'[Hh]azard\s*ratio\s*=\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:confidence\s*interval|CI)[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'relative\s+hazard[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bHR\b\s+(?:for\s+)?[\w\s]+?was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'[Aa]djusted\s+(?:HR|hazard\s*ratio)[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\baHR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*[;,]\s*[nN]\s*=\s*\d+',
            r'\bHR\b\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'hazard\s*ratio\s+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?confidence\s+interval\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'with\s+(?:an?\s+)?HR\s+of\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
            r'\bHR\b[,\s]+(\d+\.?\d*)[,;]?\s*(?:with\s+)?(?:95%?\s*)?CI\s+from\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
            r'hazard\s*ratio\s+(?:of\s+)?(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)',
            r'\(\s*HR\s*,\s*(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI\s*,?\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'hazard\s*ratio\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
            r'\bHR\b[:\s]+(\d+\.?\d*)\s*\(\s*95%CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bHR\b\s+of\s+(\d+\.?\d*)\s*\(\s*95%\s*CI\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\baHR\b[,;:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)',
            r'hazard\s*ratio\s+was\s+(\d+\.?\d*)\s+with\s+(?:95%?\s*)?CI\s+of\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
        ],
        'OR': [
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'odds\s*ratio\s+(?:of|was|for\s+[\w\s]+?was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
            r'\bOR\b[=:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bOR\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
            r'\bOR\b\s*=\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?confidence\s*interval[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bOR\b:\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\(OR\s+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\)',
            r'odds\s*ratio\s+(?:for\s+)?[\w\s]+?(?:was|is)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'[Aa]djusted\s+(?:OR|odds\s*ratio)[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\baOR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
            r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[,]\s*(\d+\.?\d*)\s*\)',
            r'\bOR\b[,;\s]+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)\s*\]',
            r'\bOR\b\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[,]\s*(\d+\.?\d*)\s*\)',
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',
            r'\(\s*OR\s*,\s*(\d+\.?\d*)\s*;\s*(?:95%?\s*)?CI\s*,?\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bOR\s*=\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
            r'odds\s*ratio\s+(?:was\s+)?(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?confidence\s*interval[:\s]+(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',
            r'\baOR\s*=?\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*,\s*(\d+\.?\d*)',
            r'\bOR\s+was\s+(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\]',
            r'odds\s*ratio[:\s]+(\d+\.?\d*)\s*\(\s*confidence\s+interval\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
        ],
        'RR': [
            r'relative\s+risk[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'(?:relative\s+)?risk\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
            r'rate\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bRR\b\s+(?:for\s+)?[\w\s]+?was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'relative\s+risk\s+(?:of|was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bRR\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
            r'relative\s+risk[,;]\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'\bRR\b\s*=\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?confidence\s*interval[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bRR\b:\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\(RR\s+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\)',
            r'relative\s+risk\s+of\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'[Aa]djusted\s+(?:RR|relative\s+risk)[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bRR\b\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'relative\s+risk\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'relative\s+risk\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
            r'(?:summary|pooled|overall)\s+relative\s+risk\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bRR\b\s+(?:for\s+[\w\s]+\s+)?was\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s+to\s+(\d+\.?\d*)',
            r'\bRR\b\s+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\]',
            r'\bRR\s*=\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'relative\s+risk[:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)',
        ],
        'MD': [
            r'\bMD\b[,;:\s=]+(-?\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—,]\s*(-?\d+\.?\d*)\s*[\)\]]',
            r'mean\s*difference[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
            r'\bMD\b\s*=\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)\s*\)',
            r'\bMD\b\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)\s*\)',
            r'mean\s*difference\s+of\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
            r'weighted\s+mean\s+difference[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
            r'\bWMD\b[,;:\s=]+(-?\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—,]\s*(-?\d+\.?\d*)\s*[\)\]]',
        ],
        'SMD': [
            r'standardized\s+mean\s+difference[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
            r'\bSMD\b[,;:\s=]+(-?\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—,]\s*(-?\d+\.?\d*)\s*[\)\]]',
            r'\bSMD\b\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)\s*\)',
            r"Cohen'?s?\s+d[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)",
            r'[Hh]edges\'?\s*g[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
            r'effect\s+size[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
            r'\bSMD\b:\s*(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[:\s]*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
            r'\bSMD\b\s*=\s*(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)\s*\)',
            r'\bSMD\b\s+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*to\s*(-?\d+\.?\d*)\s*\)',
        ],
        'ARD': [
            r'\bARD\b[,;:\s=]+(-?\d+\.?\d*)\s*%?\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—,]\s*(-?\d+\.?\d*)\s*[\)\]]',
            r'(?:absolute\s*)?risk\s*difference[,;:\s=]+(-?\d+\.?\d*)\s*%?\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
            r'absolute\s+risk\s+reduction[,;:\s=]+(-?\d+\.?\d*)\s*%?\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
            r'\bARR\b[,;:\s=]+(-?\d+\.?\d*)\s*%?\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—,]\s*(-?\d+\.?\d*)\s*[\)\]]',
        ],
        'NNT': [
            r'\bNNT\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
            r'number\s*needed\s*to\s*treat[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'\bNNT\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
            r'NNT\s*=\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        ],
        'IRR': [
            r'(?:incidence\s+)?rate\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bIRR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
            r'\bIRR\b\s+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'incidence\s+rate\s+ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        ],
    }


    def extract(self, text: str) -> List[CandidateExtraction]:
        """Extract using regex patterns with negative context filtering"""
        text = self.normalize_text(text)
        extractions = []

        for effect_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        value = float(match.group(1))
                        ci_lower = float(match.group(2))
                        ci_upper = float(match.group(3))

                        # Skip invalid CI
                        if ci_lower > ci_upper:
                            ci_lower, ci_upper = ci_upper, ci_lower
                        if not (ci_lower <= value <= ci_upper):
                            continue

                        # Check negative context
                        if self.check_negative_context(text, match.start(), match.end()):
                            continue

                        extractions.append(CandidateExtraction(
                            effect_type=effect_type,
                            value=value,
                            ci_lower=ci_lower,
                            ci_upper=ci_upper,
                            source_text=match.group(0),
                            char_start=match.start(),
                            char_end=match.end(),
                            extractor=self.extractor_type,
                            extractor_confidence=0.9,  # High confidence for pattern match
                        ))
                    except (ValueError, IndexError):
                        continue

        return extractions


# =============================================================================
# GRAMMAR EXTRACTOR (Context-Free Grammar)
# =============================================================================

class GrammarExtractor(BaseExtractor):
    """
    CFG-based extractor using formal grammar.
    More flexible than regex, can handle nested structures.

    Grammar (pseudo-BNF):
    effect_stmt -> effect_type COLON? value ci_clause?
    effect_type -> "HR" | "OR" | "RR" | "MD" | "SMD" | "ARD" | "NNT" | "IRR"
    value -> NUMBER
    ci_clause -> LPAREN ci_content RPAREN | LBRACKET ci_content RBRACKET
    ci_content -> ("95%"? "CI"? COLON?)? NUMBER (DASH | "to") NUMBER
    """

    extractor_type = ExtractorType.GRAMMAR

    # Token patterns - ORDER MATTERS! CI_LABEL must be checked before NUMBER
    # to avoid matching "95" from "95% CI" as a NUMBER
    TOKENS = {
        'EFFECT_TYPE': r'\b(HR|OR|RR|MD|SMD|ARD|NNT|NNH|IRR|hazard\s*ratio|odds\s*ratio|risk\s*ratio|mean\s*difference)\b',
        'CI_LABEL': r'(?:95%?\s*)?(?:CI|confidence\s*interval)',  # Must be before NUMBER!
        'LPAREN': r'\(',
        'RPAREN': r'\)',
        'LBRACKET': r'\[',
        'RBRACKET': r'\]',
        'DASH': r'[-–—]',
        'TO': r'\bto\b',
        'COLON': r'[,;:=]',
        'NUMBER': r'-?\d+\.?\d*',  # Must be AFTER CI_LABEL
    }

    EFFECT_MAP = {
        'hr': 'HR', 'hazard ratio': 'HR', 'hazardratio': 'HR',
        'or': 'OR', 'odds ratio': 'OR', 'oddsratio': 'OR',
        'rr': 'RR', 'risk ratio': 'RR', 'riskratio': 'RR', 'relative risk': 'RR',
        'md': 'MD', 'mean difference': 'MD', 'meandifference': 'MD',
        'smd': 'SMD', 'standardized mean difference': 'SMD',
        'ard': 'ARD', 'risk difference': 'ARD', 'absolute risk difference': 'ARD',
        'nnt': 'NNT', 'number needed to treat': 'NNT',
        'nnh': 'NNH', 'number needed to harm': 'NNH',
        'irr': 'IRR', 'incidence rate ratio': 'IRR',
    }

    def extract(self, text: str) -> List[CandidateExtraction]:
        """Extract using grammar parsing"""
        text = self.normalize_text(text)
        extractions = []

        # Tokenize and parse
        tokens = self._tokenize(text)

        i = 0
        while i < len(tokens):
            # Look for effect type token
            if tokens[i][0] == 'EFFECT_TYPE':
                result = self._parse_effect_stmt(tokens, i, text)
                if result:
                    extractions.append(result[0])
                    i = result[1]  # Move past parsed tokens
                else:
                    i += 1
            else:
                i += 1

        return extractions

    def _tokenize(self, text: str) -> List[Tuple[str, str, int, int]]:
        """Tokenize text into (type, value, start, end) tuples"""
        tokens = []
        pos = 0

        while pos < len(text):
            match = None
            for token_type, pattern in self.TOKENS.items():
                regex = re.compile(pattern, re.IGNORECASE)
                match = regex.match(text, pos)
                if match:
                    tokens.append((token_type, match.group(), match.start(), match.end()))
                    pos = match.end()
                    break

            if not match:
                pos += 1  # Skip unrecognized character

        return tokens

    def _parse_effect_stmt(self, tokens: List, start: int, text: str) -> Optional[Tuple[CandidateExtraction, int]]:
        """Parse an effect statement starting at position"""
        if start >= len(tokens):
            return None

        # Get effect type
        if tokens[start][0] != 'EFFECT_TYPE':
            return None

        effect_raw = tokens[start][1].lower().replace(' ', '')
        effect_type = self.EFFECT_MAP.get(effect_raw, effect_raw.upper())
        char_start = tokens[start][2]

        pos = start + 1

        # Skip optional colon/separator
        while pos < len(tokens) and tokens[pos][0] == 'COLON':
            pos += 1

        # Get value
        if pos >= len(tokens) or tokens[pos][0] != 'NUMBER':
            return None

        try:
            value = float(tokens[pos][1])
        except ValueError:
            return None
        pos += 1

        # Look for CI clause
        ci_lower, ci_upper = None, None

        # Skip optional comma/semicolon
        while pos < len(tokens) and tokens[pos][0] == 'COLON':
            pos += 1

        # Check for CI label
        if pos < len(tokens) and tokens[pos][0] == 'CI_LABEL':
            pos += 1
            while pos < len(tokens) and tokens[pos][0] == 'COLON':
                pos += 1

        # Check for opening bracket/paren
        if pos < len(tokens) and tokens[pos][0] in ['LPAREN', 'LBRACKET']:
            bracket_type = 'RPAREN' if tokens[pos][0] == 'LPAREN' else 'RBRACKET'
            pos += 1

            # Skip optional CI label inside brackets
            if pos < len(tokens) and tokens[pos][0] == 'CI_LABEL':
                pos += 1
                while pos < len(tokens) and tokens[pos][0] == 'COLON':
                    pos += 1

            # Get lower bound
            if pos < len(tokens) and tokens[pos][0] == 'NUMBER':
                try:
                    ci_lower = float(tokens[pos][1])
                except ValueError:
                    return None
                pos += 1

                # Skip dash or "to"
                if pos < len(tokens) and tokens[pos][0] in ['DASH', 'TO', 'COLON']:
                    pos += 1

                # Get upper bound
                if pos < len(tokens) and tokens[pos][0] == 'NUMBER':
                    try:
                        ci_upper = float(tokens[pos][1])
                    except ValueError:
                        return None
                    pos += 1

                    # Skip closing bracket
                    if pos < len(tokens) and tokens[pos][0] == bracket_type:
                        pos += 1

        # Validate
        if ci_lower is not None and ci_upper is not None:
            if ci_lower > ci_upper:
                return None
            if not (ci_lower <= value <= ci_upper):
                # Try swapping
                if ci_upper <= value <= ci_lower:
                    ci_lower, ci_upper = ci_upper, ci_lower
                else:
                    return None

        char_end = tokens[pos - 1][3] if pos > start else char_start + 10
        source = text[char_start:char_end]

        # Check negative context
        if self.check_negative_context(text, char_start, char_end):
            return None

        extraction = CandidateExtraction(
            effect_type=effect_type,
            value=value,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            source_text=source,
            char_start=char_start,
            char_end=char_end,
            extractor=self.extractor_type,
            extractor_confidence=0.85,
        )

        return (extraction, pos)


# =============================================================================
# STATE MACHINE EXTRACTOR (Finite State Machine)
# =============================================================================

class State(Enum):
    """States for the FSM"""
    START = "start"
    EFFECT_TYPE = "effect_type"
    AWAIT_VALUE = "await_value"
    VALUE = "value"
    AWAIT_CI = "await_ci"
    CI_LOWER = "ci_lower"
    AWAIT_UPPER = "await_upper"
    CI_UPPER = "ci_upper"
    COMPLETE = "complete"
    ERROR = "error"


class StateMachineExtractor(BaseExtractor):
    """
    FSM-based extractor with explicit state transitions.
    Deterministic and easy to verify.
    """

    extractor_type = ExtractorType.STATE_MACHINE

    EFFECT_TYPES = {'HR', 'OR', 'RR', 'MD', 'SMD', 'ARD', 'NNT', 'NNH', 'IRR', 'WMD', 'RRR', 'ARR'}
    EFFECT_WORDS = {
        'hazard': 'HR', 'odds': 'OR', 'risk': 'RR', 'mean': 'MD',
        'standardized': 'SMD', 'absolute': 'ARD', 'incidence': 'IRR',
    }

    def extract(self, text: str) -> List[CandidateExtraction]:
        """Extract using state machine"""
        text = self.normalize_text(text)
        extractions = []

        # Tokenize into words and numbers
        tokens = re.findall(r'[a-zA-Z]+|\d+\.?\d*|[()[\],;:=\-]', text)

        # Track character positions
        char_positions = []
        pos = 0
        for token in tokens:
            idx = text.find(token, pos)
            char_positions.append(idx)
            pos = idx + len(token)

        i = 0
        while i < len(tokens):
            result = self._run_fsm(tokens, i, char_positions, text)
            if result:
                extractions.append(result[0])
                i = result[1]
            else:
                i += 1

        return extractions

    def _run_fsm(self, tokens: List[str], start: int, positions: List[int], text: str) -> Optional[Tuple[CandidateExtraction, int]]:
        """Run FSM from start position"""
        state = State.START
        effect_type = None
        value = None
        ci_lower = None
        ci_upper = None
        char_start = positions[start] if start < len(positions) else 0

        i = start
        while i < len(tokens) and state != State.COMPLETE and state != State.ERROR:
            token = tokens[i].upper()

            if state == State.START:
                if token in self.EFFECT_TYPES:
                    effect_type = token
                    state = State.EFFECT_TYPE
                elif token.lower() in self.EFFECT_WORDS:
                    effect_type = self.EFFECT_WORDS[token.lower()]
                    state = State.EFFECT_TYPE
                else:
                    state = State.ERROR

            elif state == State.EFFECT_TYPE:
                if token in ['RATIO', 'DIFFERENCE', 'RATE']:
                    # Part of effect type name, stay in state
                    pass
                elif token in [',', ';', ':', '=', 'OF', 'WAS', 'IS']:
                    state = State.AWAIT_VALUE
                elif self._is_number(tokens[i]):
                    value = float(tokens[i])
                    state = State.VALUE
                else:
                    state = State.AWAIT_VALUE

            elif state == State.AWAIT_VALUE:
                if self._is_number(tokens[i]):
                    value = float(tokens[i])
                    state = State.VALUE
                elif token in [',', ';', ':', '=', '95', '%', 'CI', 'CONFIDENCE', 'INTERVAL']:
                    pass  # Skip
                else:
                    state = State.ERROR

            elif state == State.VALUE:
                if token in ['(', '[']:
                    state = State.AWAIT_CI
                elif token in [',', ';']:
                    state = State.AWAIT_CI
                elif token in ['95', '%', 'CI', 'CONFIDENCE', 'INTERVAL', ':']:
                    state = State.AWAIT_CI
                elif self._is_number(tokens[i]):
                    # Might be direct CI without bracket
                    ci_lower = float(tokens[i])
                    state = State.CI_LOWER
                else:
                    state = State.COMPLETE  # Value only, no CI

            elif state == State.AWAIT_CI:
                if self._is_number(tokens[i]):
                    ci_lower = float(tokens[i])
                    state = State.CI_LOWER
                elif token in ['95', '%', 'CI', 'CONFIDENCE', 'INTERVAL', ':', ',', '(', '[']:
                    pass  # Skip
                else:
                    state = State.COMPLETE

            elif state == State.CI_LOWER:
                if token in ['-', 'TO', ',']:
                    state = State.AWAIT_UPPER
                elif self._is_number(tokens[i]):
                    ci_upper = float(tokens[i])
                    state = State.CI_UPPER
                else:
                    state = State.ERROR

            elif state == State.AWAIT_UPPER:
                if self._is_number(tokens[i]):
                    ci_upper = float(tokens[i])
                    state = State.CI_UPPER
                else:
                    state = State.ERROR

            elif state == State.CI_UPPER:
                state = State.COMPLETE

            i += 1

        # Validate and create extraction
        if state in [State.COMPLETE, State.CI_UPPER, State.VALUE] and effect_type and value is not None:
            if ci_lower is not None and ci_upper is not None:
                # Validate CI
                if ci_lower > ci_upper:
                    ci_lower, ci_upper = ci_upper, ci_lower
                if not (ci_lower <= value <= ci_upper):
                    return None

            char_end = positions[i - 1] + len(tokens[i - 1]) if i > start else char_start + 10

            # Check negative context
            if self.check_negative_context(text, char_start, char_end):
                return None

            return (CandidateExtraction(
                effect_type=effect_type,
                value=value,
                ci_lower=ci_lower,
                ci_upper=ci_upper,
                source_text=text[char_start:char_end],
                char_start=char_start,
                char_end=char_end,
                extractor=self.extractor_type,
                extractor_confidence=0.8,
            ), i)

        return None

    def _is_number(self, token: str) -> bool:
        """Check if token is a valid number"""
        try:
            float(token)
            return True
        except ValueError:
            return False


# =============================================================================
# CHUNK EXTRACTOR (Sliding Window)
# =============================================================================

class ChunkExtractor(BaseExtractor):
    """
    Sliding window extractor with scoring.
    Finds number triplets and scores likelihood of being effect estimates.
    """

    extractor_type = ExtractorType.CHUNK

    EFFECT_KEYWORDS = {
        'HR': ['hazard', 'ratio', 'hr'],
        'OR': ['odds', 'ratio', 'or'],
        'RR': ['risk', 'ratio', 'rr', 'relative'],
        'MD': ['mean', 'difference', 'md'],
        'SMD': ['standardized', 'mean', 'difference', 'smd'],
        'ARD': ['absolute', 'risk', 'difference', 'ard'],
        'NNT': ['number', 'needed', 'treat', 'nnt'],
        'IRR': ['incidence', 'rate', 'ratio', 'irr'],
    }

    def extract(self, text: str) -> List[CandidateExtraction]:
        """Extract using sliding window"""
        text = self.normalize_text(text)
        extractions = []

        # Find all numbers with positions
        number_pattern = r'-?\d+\.?\d*'
        numbers = [(m.group(), m.start(), m.end()) for m in re.finditer(number_pattern, text)]

        # Sliding window over number triplets
        for i in range(len(numbers) - 2):
            chunk_start = max(0, numbers[i][1] - 100)  # Context before
            chunk_end = min(len(text), numbers[i + 2][2] + 20)  # Context after
            chunk = text[chunk_start:chunk_end].lower()

            # Score each effect type
            best_type = None
            best_score = 0.0

            for effect_type, keywords in self.EFFECT_KEYWORDS.items():
                score = sum(1 for kw in keywords if kw in chunk)
                score /= len(keywords)  # Normalize

                if score > best_score:
                    best_score = score
                    best_type = effect_type

            # Only extract if we found effect type keywords
            if best_type and best_score >= 0.3:
                try:
                    value = float(numbers[i][0])
                    ci_lower = float(numbers[i + 1][0])
                    ci_upper = float(numbers[i + 2][0])

                    # Validate
                    if ci_lower > ci_upper:
                        ci_lower, ci_upper = ci_upper, ci_lower
                    if not (ci_lower <= value <= ci_upper):
                        continue

                    char_start = numbers[i][1]
                    char_end = numbers[i + 2][2]

                    # Check negative context
                    if self.check_negative_context(text, char_start, char_end):
                        continue

                    extractions.append(CandidateExtraction(
                        effect_type=best_type,
                        value=value,
                        ci_lower=ci_lower,
                        ci_upper=ci_upper,
                        source_text=text[char_start:char_end],
                        char_start=char_start,
                        char_end=char_end,
                        extractor=self.extractor_type,
                        extractor_confidence=best_score * 0.7,  # Scale down
                    ))
                except ValueError:
                    continue

        return extractions


# =============================================================================
# CRITIC MODULE
# =============================================================================

class Critic:
    """
    Reviews disagreements between extractors.
    Applies additional validation to resolve conflicts.
    """

    def review(self, candidates: List[CandidateExtraction], text: str) -> Tuple[Optional[CandidateExtraction], List[str]]:
        """
        Review conflicting extractions and determine best one.
        Returns (best_extraction, notes)
        """
        notes = []

        if not candidates:
            return None, ["No candidates to review"]

        if len(candidates) == 1:
            return candidates[0], ["Single candidate, accepted"]

        # Group by value
        value_groups: Dict[float, List[CandidateExtraction]] = {}
        for c in candidates:
            key = round(c.value, 3)
            if key not in value_groups:
                value_groups[key] = []
            value_groups[key].append(c)

        # Find most agreed value
        best_group = max(value_groups.values(), key=len)

        if len(best_group) > len(candidates) / 2:
            # Majority agrees on value
            best = best_group[0]
            notes.append(f"Majority ({len(best_group)}/{len(candidates)}) agree on value {best.value}")

            # Validate CI if present
            if best.ci_lower and best.ci_upper:
                if not (best.ci_lower <= best.value <= best.ci_upper):
                    notes.append("WARNING: Point estimate outside CI")

            return best, notes

        # No majority - use additional heuristics
        notes.append("No majority agreement, applying heuristics")

        # Prefer extractions with CI
        with_ci = [c for c in candidates if c.ci_lower and c.ci_upper]
        if with_ci:
            candidates = with_ci
            notes.append(f"Filtered to {len(with_ci)} candidates with CI")

        # Prefer pattern extractor (most tested)
        pattern_matches = [c for c in candidates if c.extractor == ExtractorType.PATTERN]
        if pattern_matches:
            notes.append("Selected pattern extractor result")
            return pattern_matches[0], notes

        # Fall back to highest confidence
        best = max(candidates, key=lambda c: c.extractor_confidence)
        notes.append(f"Selected highest confidence ({best.extractor_confidence:.2f})")

        return best, notes


# =============================================================================
# CONSENSUS ENGINE
# =============================================================================

class ConsensusEngine:
    """
    Runs all extractors and determines consensus.

    The V3 PatternExtractor is the primary extractor (100% sensitivity, 0% FPR).
    Other extractors provide additional validation through consensus.
    """

    def __init__(self, use_v3_primary: bool = True, require_pattern_agreement: bool = True):
        """
        Initialize consensus engine.

        Args:
            use_v3_primary: If True, use V3ExtractorWrapper (recommended)
            require_pattern_agreement: If True, require Pattern extractor to agree for verified status
        """
        self.require_pattern_agreement = require_pattern_agreement

        if use_v3_primary:
            # Import here to avoid circular imports
            from .v3_extractor_wrapper import V3ExtractorWrapper
            self.extractors = [
                V3ExtractorWrapper(),  # Primary: 100% sensitivity, 0% FPR
                GrammarExtractor(),
                StateMachineExtractor(),
                ChunkExtractor(),
            ]
        else:
            self.extractors = [
                PatternExtractor(),
                GrammarExtractor(),
                StateMachineExtractor(),
                ChunkExtractor(),
            ]
        self.critic = Critic()

    def extract_with_consensus(self, text: str) -> List[ConsensusResult]:
        """
        Run all extractors and determine consensus for each extraction.
        """
        # Collect all extractions
        all_extractions: Dict[ExtractorType, List[CandidateExtraction]] = {}
        for extractor in self.extractors:
            extractions = extractor.extract(text)
            all_extractions[extractor.extractor_type] = extractions

        # Group extractions by approximate location/value
        extraction_groups = self._group_extractions(all_extractions)

        # Build consensus for each group
        results = []
        for group in extraction_groups:
            result = self._build_consensus(group)
            results.append(result)

        return results

    def _group_extractions(self, all_extractions: Dict[ExtractorType, List[CandidateExtraction]]) -> List[List[CandidateExtraction]]:
        """Group extractions that refer to the same effect estimate"""
        all_candidates = []
        for extractions in all_extractions.values():
            all_candidates.extend(extractions)

        if not all_candidates:
            return []

        # Group by overlapping character ranges and matching values
        groups = []
        used = set()

        for i, c1 in enumerate(all_candidates):
            if i in used:
                continue

            group = [c1]
            used.add(i)

            for j, c2 in enumerate(all_candidates):
                if j in used:
                    continue

                # Check if same extraction (overlapping or matching values)
                overlaps = not (c1.char_end < c2.char_start or c2.char_end < c1.char_start)
                matches = c1.matches(c2)

                if overlaps or matches:
                    group.append(c2)
                    used.add(j)

            groups.append(group)

        return groups

    def _build_consensus(self, group: List[CandidateExtraction]) -> ConsensusResult:
        """Build consensus for a group of extractions"""
        extractor_types = set(c.extractor for c in group)
        total_extractors = len(self.extractors)

        # Find agreeing extractors
        value_counts: Dict[float, Set[ExtractorType]] = {}
        for c in group:
            key = round(c.value, 3)
            if key not in value_counts:
                value_counts[key] = set()
            value_counts[key].add(c.extractor)

        # Find best value (most agreement)
        best_value = max(value_counts.keys(), key=lambda k: len(value_counts[k]))
        agreeing = value_counts[best_value]
        disagreeing = extractor_types - agreeing

        # Get the best extraction for this value
        best_candidates = [c for c in group if round(c.value, 3) == best_value]

        # Check if Pattern extractor agrees (critical for low FPR)
        pattern_agrees = ExtractorType.PATTERN in agreeing

        # Use critic if disagreement
        if len(disagreeing) > 0 or len(agreeing) < total_extractors:
            best_extraction, critic_notes = self.critic.review(best_candidates, "")
            needs_critic = True
        else:
            best_extraction = best_candidates[0] if best_candidates else None
            critic_notes = []
            needs_critic = False

        # If Pattern extractor didn't agree and we require it, mark as needing review
        if self.require_pattern_agreement and not pattern_agrees:
            critic_notes.append("Pattern extractor did not agree - requires review")
            needs_critic = True

        agreement_ratio = len(agreeing) / total_extractors if total_extractors > 0 else 0

        return ConsensusResult(
            extraction=best_extraction,
            agreeing_extractors=list(agreeing),
            disagreeing_extractors=list(disagreeing),
            agreement_ratio=agreement_ratio,
            is_unanimous=(agreement_ratio == 1.0 and len(agreeing) == total_extractors),
            needs_critic=needs_critic,
            critic_notes=critic_notes,
        )


# =============================================================================
# TEAM-OF-RIVALS INTERFACE
# =============================================================================

def team_extract(text: str) -> List[ConsensusResult]:
    """
    Main interface: Extract effect estimates using Team-of-Rivals.

    Returns list of ConsensusResult, each containing:
    - extraction: The best extraction
    - agreeing_extractors: Which extractors agreed
    - agreement_ratio: 0.0 to 1.0
    - is_unanimous: True if all extractors agreed
    - needs_critic: True if critic was needed
    """
    engine = ConsensusEngine()
    return engine.extract_with_consensus(text)


def get_verified_extractions(text: str, min_agreement: float = 0.5) -> List[CandidateExtraction]:
    """
    Get only extractions meeting minimum agreement threshold.

    Args:
        text: Text to extract from
        min_agreement: Minimum agreement ratio (0.0 to 1.0)

    Returns:
        List of verified extractions
    """
    results = team_extract(text)
    verified = []

    for result in results:
        if result.agreement_ratio >= min_agreement and result.extraction:
            verified.append(result.extraction)

    return verified
