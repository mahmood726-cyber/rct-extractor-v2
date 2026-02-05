#!/usr/bin/env python3
"""
Subgroup Analysis and Heterogeneity Extractor
==============================================

Extracts subgroup analysis results, p-for-interaction values,
and heterogeneity statistics from clinical trial publications.

Features:
- P-for-interaction pattern matching
- Heterogeneity measures (I², tau², Q)
- Subgroup category detection
- Effect modification assessment

Author: RCT Extractor Team
Version: 4.1.1
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class SubgroupCategory(Enum):
    """Categories of subgroup analyses"""
    AGE = "age"
    SEX = "sex"
    RACE = "race"
    GEOGRAPHY = "geography"
    BIOMARKER = "biomarker"
    DISEASE_SEVERITY = "disease_severity"
    COMORBIDITY = "comorbidity"
    PRIOR_TREATMENT = "prior_treatment"
    BASELINE_CHARACTERISTIC = "baseline_characteristic"
    OTHER = "other"


class InteractionType(Enum):
    """Types of interaction tests"""
    QUALITATIVE = "qualitative"  # Direction of effect differs
    QUANTITATIVE = "quantitative"  # Magnitude differs but same direction
    NONE = "none"  # No significant interaction


@dataclass
class SubgroupDefinition:
    """Definition of a subgroup"""
    category: SubgroupCategory
    name: str
    levels: List[str] = field(default_factory=list)
    threshold: Optional[float] = None  # For continuous variables (e.g., age >= 65)
    description: str = ""


@dataclass
class InteractionTest:
    """P-for-interaction test result"""
    subgroup: SubgroupDefinition
    p_value: float
    is_significant: bool  # Typically p < 0.05
    interaction_type: InteractionType
    source_text: str = ""
    confidence: float = 1.0


@dataclass
class HeterogeneityMeasure:
    """Heterogeneity statistics"""
    i_squared: Optional[float] = None  # I² (0-100%)
    tau_squared: Optional[float] = None  # tau² (variance)
    q_statistic: Optional[float] = None  # Cochran's Q
    q_df: Optional[int] = None  # Degrees of freedom for Q
    q_p_value: Optional[float] = None  # P-value for Q test
    h_squared: Optional[float] = None  # H² statistic
    prediction_interval: Optional[Tuple[float, float]] = None
    source_text: str = ""

    def heterogeneity_level(self) -> str:
        """Classify heterogeneity level based on I²"""
        if self.i_squared is None:
            return "unknown"
        if self.i_squared < 25:
            return "low"
        if self.i_squared < 50:
            return "moderate"
        if self.i_squared < 75:
            return "substantial"
        return "considerable"


@dataclass
class SubgroupResult:
    """Complete subgroup analysis result"""
    subgroup: SubgroupDefinition
    effect_type: str  # HR, OR, RR, MD, etc.
    point_estimate: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    p_value: Optional[float] = None
    interaction_test: Optional[InteractionTest] = None
    n_subjects: Optional[int] = None
    n_events: Optional[int] = None
    source_text: str = ""


class SubgroupExtractor:
    """
    Extracts subgroup analysis results and heterogeneity measures.

    Capabilities:
    - P-for-interaction patterns
    - Heterogeneity statistics (I², tau², Q)
    - Subgroup category detection
    - Effect estimates within subgroups
    """

    # P-for-interaction patterns
    P_INTERACTION_PATTERNS = [
        # Standard formats
        r'[pP]\s*(?:for|of)\s*interaction[:\s]*([<>=]?\s*\d+\.?\d*)',
        r'[pP]\s*(?:for|of)\s*heterogeneity[:\s]*([<>=]?\s*\d+\.?\d*)',
        r'interaction\s+[pP][:\s]*([<>=]?\s*\d+\.?\d*)',
        r'[pP][\s-]*interaction[:\s]*([<>=]?\s*\d+\.?\d*)',
        r'[pP]\s*=?\s*(\d+\.?\d*)\s*(?:for\s+)?interaction',

        # Parenthetical formats
        r'\([pP]\s*(?:for\s+)?interaction\s*[=:]\s*([<>=]?\s*\d+\.?\d*)\)',
        r'\([pP]\s*(?:for\s+)?heterogeneity\s*[=:]\s*([<>=]?\s*\d+\.?\d*)\)',

        # Test for interaction
        r'test\s+for\s+interaction[:\s]+[pP]\s*[=:]\s*([<>=]?\s*\d+\.?\d*)',
        r'test\s+for\s+heterogeneity[:\s]+[pP]\s*[=:]\s*([<>=]?\s*\d+\.?\d*)',

        # NS (not significant) patterns
        r'[pP]\s*(?:for|of)\s*interaction[:\s]*(NS|ns|not\s+significant)',

        # Subgroup interaction specific
        r'subgroup\s+interaction[:\s]+[pP]\s*[=:]\s*([<>=]?\s*\d+\.?\d*)',
        r'treatment[\s-]+(?:by[\s-]+)?subgroup\s+interaction[:\s]+[pP]\s*[=:]\s*([<>=]?\s*\d+\.?\d*)',
    ]

    # Heterogeneity measure patterns
    HETEROGENEITY_PATTERNS = {
        'i_squared': [
            r'[Ii][²2]\s*[=:]\s*(\d+\.?\d*)%?',
            r'[Ii]-?squared\s*[=:]\s*(\d+\.?\d*)%?',
            r'I-?statistic\s*[=:]\s*(\d+\.?\d*)%?',
            r'heterogeneity[^.]*[Ii][²2]\s*[=:]\s*(\d+\.?\d*)%?',
            r'inconsistency\s*[=:]\s*(\d+\.?\d*)%?',
        ],
        'tau_squared': [
            r'[Tt]au[²2]\s*[=:]\s*(\d+\.?\d*)',
            r'[Tt]au-?squared\s*[=:]\s*(\d+\.?\d*)',
            r'between-?study\s+variance\s*[=:]\s*(\d+\.?\d*)',
            r'τ[²2]\s*[=:]\s*(\d+\.?\d*)',
        ],
        'q_statistic': [
            r'[Qq]\s*(?:statistic)?[=:]\s*(\d+\.?\d*)',
            r"Cochran'?s?\s+[Qq]\s*[=:]\s*(\d+\.?\d*)",
            r'heterogeneity\s+[Qq]\s*[=:]\s*(\d+\.?\d*)',
            r'chi-?squared?\s+(?:for\s+)?heterogeneity\s*[=:]\s*(\d+\.?\d*)',
        ],
        'q_df': [
            r'[Qq]\s*\(\s*df\s*[=:]\s*(\d+)\s*\)',
            r'[Qq]\s*[=:]\s*\d+\.?\d*\s*,?\s*df\s*[=:]\s*(\d+)',
            r'degrees?\s+of\s+freedom\s*[=:]\s*(\d+)',
        ],
        'q_p_value': [
            r'[Qq]\s*[=:][^,;]+,?\s*[pP]\s*[=:]\s*([<>=]?\s*\d+\.?\d*)',
            r'heterogeneity[^.]*[pP]\s*[=:]\s*([<>=]?\s*\d+\.?\d*)',
        ],
        'prediction_interval': [
            r'prediction\s+interval[:\s]+(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
            r'95%\s*PI[:\s]+(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
        ],
    }

    # Subgroup category detection patterns
    SUBGROUP_PATTERNS = {
        SubgroupCategory.AGE: [
            r'age\s*[<>=≥≤]+\s*(\d+)',
            r'(?:older|younger)\s+(?:than\s+)?(\d+)',
            r'elderly\s*\(?\s*(?:age\s*)?[<>=≥≤]?\s*(\d+)',
            r'(\d+)\s*years?\s+(?:or\s+)?(?:older|younger)',
            r'age\s+(?:group|category|subgroup)',
            r'(?:pediatric|geriatric|adult)',
        ],
        SubgroupCategory.SEX: [
            r'\b(?:male|female|men|women)\b',
            r'\bsex\s*(?:subgroup|analysis)',
            r'\bgender\s*(?:subgroup|analysis)',
        ],
        SubgroupCategory.RACE: [
            r'\b(?:white|black|asian|hispanic|caucasian|african)\b',
            r'\b(?:race|ethnicity)\s*(?:subgroup|analysis)',
        ],
        SubgroupCategory.GEOGRAPHY: [
            r'\b(?:region|country|continent)\s*(?:subgroup|analysis)',
            r'\b(?:north\s+america|europe|asia|latin\s+america)\b',
            r'\b(?:western|eastern|northern|southern)\s+(?:countries|regions?)\b',
        ],
        SubgroupCategory.BIOMARKER: [
            r'\b(?:HER2|PD-?L1|BRCA|EGFR|ALK|KRAS|BRAF)\s*[+-]?\b',
            r'\b(?:biomarker|mutation|expression)\s*(?:positive|negative|status)\b',
            r'\b(?:receptor|hormone)\s*(?:positive|negative)\b',
            r'\b(?:high|low)\s+(?:risk|expression)\b',
            r'\bCRP\s*[<>=]',
            r'\beGFR\s*[<>=]',
            r'\bNT-?proBNP\s*[<>=]',
        ],
        SubgroupCategory.DISEASE_SEVERITY: [
            r'\b(?:NYHA|CCS)\s+(?:class|stage)\s*(?:I{1,4}|[1-4])',
            r'\b(?:stage|grade)\s*(?:I{1,4}|[1-4]|[A-D])\b',
            r'\b(?:mild|moderate|severe)\s+(?:disease|illness)',
            r'\b(?:EF|ejection\s+fraction)\s*[<>=]?\s*(\d+)%?',
        ],
        SubgroupCategory.COMORBIDITY: [
            r'\b(?:diabetes|hypertension|CKD|CAD|AF|atrial\s+fibrillation)\b',
            r'\b(?:with|without)\s+(?:diabetes|hypertension|CKD|history)',
            r'\bcomorbid(?:ity|ities)?\b',
        ],
        SubgroupCategory.PRIOR_TREATMENT: [
            r'\b(?:treatment|therapy)\s*[-–]?\s*(?:naive|experienced)\b',
            r'\bprior\s+(?:treatment|therapy|medication)',
            r'\b(?:first|second|third)\s*[-–]?\s*line\b',
            r'\bprevious(?:ly)?\s+(?:treated|untreated)\b',
        ],
    }

    def __init__(self):
        """Initialize extractor with compiled patterns"""
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency"""
        self._p_interaction_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.P_INTERACTION_PATTERNS
        ]

        self._heterogeneity_compiled = {
            key: [re.compile(p, re.IGNORECASE) for p in patterns]
            for key, patterns in self.HETEROGENEITY_PATTERNS.items()
        }

        self._subgroup_compiled = {
            cat: [re.compile(p, re.IGNORECASE) for p in patterns]
            for cat, patterns in self.SUBGROUP_PATTERNS.items()
        }

    def extract_p_interaction(self, text: str) -> List[InteractionTest]:
        """
        Extract p-for-interaction values from text.

        Args:
            text: Input text containing interaction tests

        Returns:
            List of InteractionTest results
        """
        results = []
        seen_values = set()

        for pattern in self._p_interaction_compiled:
            for match in pattern.finditer(text):
                p_str = match.group(1).strip()

                # Parse p-value
                p_value = self._parse_p_value(p_str)
                if p_value is None:
                    continue

                # Avoid duplicates
                if p_value in seen_values:
                    continue
                seen_values.add(p_value)

                # Get surrounding context for subgroup detection
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 50)
                context = text[start:end]

                # Detect subgroup category
                subgroup = self._detect_subgroup_from_context(context)

                # Determine significance
                is_significant = p_value < 0.05

                # Determine interaction type
                interaction_type = InteractionType.QUANTITATIVE if is_significant else InteractionType.NONE

                results.append(InteractionTest(
                    subgroup=subgroup,
                    p_value=p_value,
                    is_significant=is_significant,
                    interaction_type=interaction_type,
                    source_text=match.group(0),
                ))

        return results

    def extract_heterogeneity(self, text: str) -> HeterogeneityMeasure:
        """
        Extract heterogeneity statistics from text.

        Args:
            text: Input text containing heterogeneity measures

        Returns:
            HeterogeneityMeasure with extracted values
        """
        result = HeterogeneityMeasure()

        # Extract I²
        for pattern in self._heterogeneity_compiled['i_squared']:
            match = pattern.search(text)
            if match:
                try:
                    value = float(match.group(1))
                    # Normalize to percentage if needed
                    if value > 1 and value <= 100:
                        result.i_squared = value
                    elif value <= 1:
                        result.i_squared = value * 100
                    result.source_text = match.group(0)
                    break
                except ValueError:
                    pass

        # Extract tau²
        for pattern in self._heterogeneity_compiled['tau_squared']:
            match = pattern.search(text)
            if match:
                try:
                    result.tau_squared = float(match.group(1))
                    break
                except ValueError:
                    pass

        # Extract Q statistic
        for pattern in self._heterogeneity_compiled['q_statistic']:
            match = pattern.search(text)
            if match:
                try:
                    result.q_statistic = float(match.group(1))
                    break
                except ValueError:
                    pass

        # Extract Q degrees of freedom
        for pattern in self._heterogeneity_compiled['q_df']:
            match = pattern.search(text)
            if match:
                try:
                    result.q_df = int(match.group(1))
                    break
                except ValueError:
                    pass

        # Extract Q p-value
        for pattern in self._heterogeneity_compiled['q_p_value']:
            match = pattern.search(text)
            if match:
                p_value = self._parse_p_value(match.group(1))
                if p_value is not None:
                    result.q_p_value = p_value
                    break

        # Extract prediction interval
        for pattern in self._heterogeneity_compiled['prediction_interval']:
            match = pattern.search(text)
            if match:
                try:
                    lower = float(match.group(1))
                    upper = float(match.group(2))
                    result.prediction_interval = (lower, upper)
                    break
                except ValueError:
                    pass

        return result

    def detect_subgroup_categories(self, text: str) -> List[SubgroupDefinition]:
        """
        Detect subgroup categories mentioned in text.

        Args:
            text: Input text containing subgroup descriptions

        Returns:
            List of detected SubgroupDefinition
        """
        results = []
        seen_categories = set()

        for category, patterns in self._subgroup_compiled.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match and category not in seen_categories:
                    seen_categories.add(category)

                    # Extract threshold if present (for age, biomarkers)
                    threshold = None
                    try:
                        groups = match.groups()
                        if groups and groups[0]:
                            threshold = float(groups[0])
                    except (ValueError, IndexError):
                        pass

                    results.append(SubgroupDefinition(
                        category=category,
                        name=match.group(0),
                        threshold=threshold,
                    ))

        return results

    def _detect_subgroup_from_context(self, context: str) -> SubgroupDefinition:
        """Detect subgroup from surrounding context"""
        categories = self.detect_subgroup_categories(context)
        if categories:
            return categories[0]
        return SubgroupDefinition(
            category=SubgroupCategory.OTHER,
            name="unspecified",
        )

    def _parse_p_value(self, p_str: str) -> Optional[float]:
        """
        Parse p-value string to float.

        Handles formats like:
        - "0.02"
        - "<0.001"
        - "< 0.05"
        - "NS" (returns 1.0)
        """
        if not p_str:
            return None

        p_str = p_str.strip().lower()

        # Handle "not significant"
        if p_str in ('ns', 'not significant'):
            return 1.0

        # Remove comparison operators
        p_str = re.sub(r'^[<>=≤≥]\s*', '', p_str)

        try:
            value = float(p_str)
            if 0 <= value <= 1:
                return value
            elif value > 1:
                # Might be percentage, convert
                return value / 100
        except ValueError:
            pass

        return None

    def extract_all(self, text: str) -> Dict[str, Any]:
        """
        Extract all subgroup-related information from text.

        Args:
            text: Input text to analyze

        Returns:
            Dictionary with:
            - interaction_tests: List of InteractionTest
            - heterogeneity: HeterogeneityMeasure
            - subgroups: List of SubgroupDefinition
        """
        return {
            'interaction_tests': self.extract_p_interaction(text),
            'heterogeneity': self.extract_heterogeneity(text),
            'subgroups': self.detect_subgroup_categories(text),
        }


# Convenience functions
def extract_p_interaction(text: str) -> List[InteractionTest]:
    """Extract p-for-interaction values from text."""
    extractor = SubgroupExtractor()
    return extractor.extract_p_interaction(text)


def extract_heterogeneity(text: str) -> HeterogeneityMeasure:
    """Extract heterogeneity measures from text."""
    extractor = SubgroupExtractor()
    return extractor.extract_heterogeneity(text)


def detect_subgroups(text: str) -> List[SubgroupDefinition]:
    """Detect subgroup categories in text."""
    extractor = SubgroupExtractor()
    return extractor.detect_subgroup_categories(text)
