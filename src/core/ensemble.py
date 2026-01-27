"""
Ensemble Merger for Multiple Extractors
Combines outputs from different extraction methods with weighted voting.

Extractors:
- E1: v2 Python (structure-based, tables)
- E2: v4.8 JavaScript (text patterns, comprehensive)
- E3: Wasserstein (survival curves, IPD reconstruction)
- E4: TruthCert (CTGov verification)

Confidence Grading:
- A: 3+ agree + TruthCert verified + provenance
- B: 2+ agree + provenance OR TruthCert verified
- C: 2+ agree OR provenance complete
- D: Single extractor only
- F: Disagreement OR validation fails

Enhanced with:
- OutcomeTextMatcher for better endpoint matching
- ValueValidator for plausibility checking
- Adaptive CI tolerance based on outcome match
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import math
import logging
import re

logger = logging.getLogger(__name__)


# ============================================================
# OUTCOME TEXT MATCHING (NEW)
# ============================================================

class OutcomeTextMatcher:
    """
    Match outcome text between different sources.
    Improves merging accuracy by identifying matching endpoints.
    """

    # Key phrases for outcome matching
    OUTCOME_KEYWORDS = {
        # Oncology endpoints
        'os': ['overall survival', 'os ', 'death from any cause', 'all-cause mortality', 'all cause death'],
        'pfs': ['progression-free', 'pfs', 'progression free', 'time to progression'],
        'dfs': ['disease-free', 'dfs', 'disease free', 'recurrence-free', 'relapse-free'],
        'dor': ['duration of response', 'dor', 'response duration'],
        'orr': ['overall response rate', 'orr', 'objective response', 'response rate'],
        'ttp': ['time to progression', 'ttp'],

        # Cardiology endpoints
        'mace': ['mace', 'major adverse cardiovascular', 'cv death', 'cardiovascular death'],
        'hf': ['heart failure', 'hf hospitalization', 'whf', 'worsening heart failure'],
        'cv_death': ['cardiovascular death', 'cv death', 'cardiac death'],
        'mi': ['myocardial infarction', 'heart attack', 'mi '],
        'stroke': ['stroke', 'cerebrovascular', 'cva'],

        # Composite endpoints
        'composite': ['composite', 'primary composite', 'co-primary'],
    }

    @classmethod
    def extract_outcome_type(cls, text: str) -> Optional[str]:
        """Extract outcome type from text"""
        if not text:
            return None
        text_lower = text.lower()
        for outcome_type, keywords in cls.OUTCOME_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return outcome_type
        return None

    @classmethod
    def outcomes_match(cls, text1: Optional[str], text2: Optional[str]) -> float:
        """
        Return match score between 0-1 for two outcome texts.

        1.0 = Exact outcome type match
        0.5 = Unknown (can't determine)
        0.0 = Clear mismatch
        """
        if not text1 or not text2:
            return 0.5  # Unknown match

        type1 = cls.extract_outcome_type(text1)
        type2 = cls.extract_outcome_type(text2)

        if type1 and type2:
            return 1.0 if type1 == type2 else 0.0

        # Fallback: word overlap using Jaccard similarity
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))

        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'in', 'of', 'for', 'and', 'or', 'to', 'with'}
        words1 = words1 - stop_words
        words2 = words2 - stop_words

        if not words1 or not words2:
            return 0.5

        overlap = len(words1 & words2)
        total = len(words1 | words2)
        return overlap / max(total, 1)


# ============================================================
# VALUE VALIDATION (NEW)
# ============================================================

class ValueValidator:
    """
    Validate extracted effect measure values for plausibility.
    Filters out unlikely HRs and identifies potential false positives.
    """

    # Typical ranges for different effect measures
    PLAUSIBLE_RANGES = {
        'HR': (0.05, 15.0),   # Hazard ratios
        'RR': (0.05, 15.0),   # Relative risks
        'OR': (0.02, 50.0),   # Odds ratios (can be larger)
        'MD': (-100, 100),    # Mean differences (depends on scale)
        'RD': (-1.0, 1.0),    # Risk differences
    }

    # Typical (common) ranges - values outside get lower confidence
    TYPICAL_RANGES = {
        'HR': (0.3, 3.0),
        'RR': (0.3, 3.0),
        'OR': (0.3, 5.0),
    }

    @classmethod
    def is_plausible(
        cls,
        value: float,
        ci_low: float,
        ci_high: float,
        measure_type: str = "HR"
    ) -> Tuple[bool, float]:
        """
        Check if value is plausible for the given measure type.

        Args:
            value: Point estimate
            ci_low: Lower CI bound
            ci_high: Upper CI bound
            measure_type: HR, RR, OR, MD, RD

        Returns:
            (is_plausible, confidence_multiplier)
            confidence_multiplier: 1.0 = typical, 0.7 = unusual, 0.5 = very unusual
        """
        # Get ranges
        plausible_range = cls.PLAUSIBLE_RANGES.get(measure_type, (0.01, 100))
        typical_range = cls.TYPICAL_RANGES.get(measure_type)

        # Check if value is within plausible range
        if not (plausible_range[0] <= value <= plausible_range[1]):
            return False, 0.0

        # Check CI ordering (allow small tolerance)
        if ci_low > ci_high + 0.001:
            return False, 0.0

        # Check if value is within CI (with tolerance)
        if not (ci_low - 0.05 <= value <= ci_high + 0.05):
            return False, 0.5

        # Calculate confidence multiplier based on how typical the value is
        confidence = 1.0

        if typical_range:
            if value < typical_range[0] or value > typical_range[1]:
                confidence = 0.7  # Unusual but possible
            if value < plausible_range[0] * 2 or value > plausible_range[1] / 2:
                confidence = 0.5  # Very unusual

        return True, confidence

    @classmethod
    def detect_measure_type(cls, value: float, context: Optional[str] = None) -> str:
        """
        Detect likely measure type from value and context.

        Values > 3.0 with no HR/hazard context may be ORs or RRs.
        """
        if context:
            context_lower = context.lower()
            if 'hazard' in context_lower or 'survival' in context_lower:
                return 'HR'
            if 'odds' in context_lower:
                return 'OR'
            if 'risk ratio' in context_lower or 'relative risk' in context_lower:
                return 'RR'
            if 'difference' in context_lower:
                return 'MD' if abs(value) > 1 else 'RD'

        # Heuristic based on value
        if value > 5.0:
            return 'OR'  # Large values more likely OR
        return 'HR'  # Default


class ConfidenceGrade(Enum):
    """Ensemble confidence grades"""
    A = "A"  # Auto-accept (3+ agree + verified)
    B = "B"  # Accept with note (2+ agree OR verified)
    C = "C"  # Spot-check (2+ agree)
    D = "D"  # Review required (single source)
    F = "F"  # Expert review (disagreement/failure)


@dataclass
class ExtractorResult:
    """Result from a single extractor"""
    extractor_id: str  # E1, E2, E3, E4
    endpoint: str
    value: Optional[float] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    measure_type: str = "HR"  # HR, RR, OR, MD, RD

    # Quality indicators
    has_provenance: bool = False
    provenance_page: Optional[int] = None
    provenance_text: Optional[str] = None
    is_verified: bool = False  # TruthCert verified
    wasserstein_grade: Optional[str] = None  # A/B/C/D from Wasserstein

    # Raw extraction
    raw_match: Optional[str] = None
    confidence_score: float = 0.5

    # NEW: Outcome text for better matching
    outcome_text: Optional[str] = None  # Full outcome description
    is_primary: bool = False  # Is this a primary endpoint?


@dataclass
class MergedResult:
    """Merged result from ensemble"""
    endpoint: str
    measure_type: str

    # Best value (selected by voting)
    value: Optional[float] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None

    # Ensemble metadata
    confidence_grade: ConfidenceGrade = ConfidenceGrade.D
    agreement_count: int = 0
    sources: List[str] = field(default_factory=list)
    is_verified: bool = False

    # Provenance (from best source)
    provenance_page: Optional[int] = None
    provenance_text: Optional[str] = None

    # All individual results
    individual_results: List[ExtractorResult] = field(default_factory=list)

    # Disagreement details (if any)
    disagreement_details: Optional[str] = None


# ============================================================
# AGREEMENT CALCULATION
# ============================================================

def values_agree(
    v1: Optional[float],
    v2: Optional[float],
    rel_tolerance: float = 0.02,
    abs_tolerance: float = 0.01
) -> bool:
    """
    Check if two values agree within tolerance.

    Args:
        v1, v2: Values to compare
        rel_tolerance: Relative tolerance (default 2%)
        abs_tolerance: Absolute tolerance (default 0.01)

    Returns:
        True if values agree
    """
    if v1 is None or v2 is None:
        return False

    # Check absolute tolerance first
    if abs(v1 - v2) <= abs_tolerance:
        return True

    # Check relative tolerance
    if v1 != 0:
        rel_diff = abs(v1 - v2) / abs(v1)
        return rel_diff <= rel_tolerance

    return False


def values_agree_with_outcome(
    r1: ExtractorResult,
    r2: ExtractorResult,
    hr_tolerance: float = 0.05,
    ci_tolerance: float = 0.15
) -> Tuple[bool, str]:
    """
    Check if two ExtractorResults agree, considering outcome text.

    Uses adaptive tolerance based on outcome match quality:
    - If outcomes clearly match: more lenient CI tolerance
    - If outcomes clearly mismatch: reject even if values close

    Args:
        r1, r2: Results to compare
        hr_tolerance: Tolerance for HR matching (default 5%)
        ci_tolerance: Tolerance for CI matching (default 15%)

    Returns:
        (matches, match_type)
        match_type: 'exact', 'hr_match', 'close', None
    """
    if r1.value is None or r2.value is None:
        return False, None

    # Calculate HR difference
    hr_diff = abs(r1.value - r2.value) / max(r1.value, 0.01)

    # Check outcome text match
    outcome_score = OutcomeTextMatcher.outcomes_match(
        r1.outcome_text or r1.endpoint,
        r2.outcome_text or r2.endpoint
    )

    # If outcomes clearly don't match, reject even if values are close
    if outcome_score < 0.2 and hr_diff > 0.03:
        return False, None

    # If HR differs too much, no match
    if hr_diff > 0.20:  # 20% max tolerance
        return False, None

    # Calculate CI differences
    ci_low_diff = 0
    ci_high_diff = 0
    if r1.ci_low and r2.ci_low:
        ci_low_diff = abs(r1.ci_low - r2.ci_low) / max(r1.ci_low, 0.01)
    if r1.ci_high and r2.ci_high:
        ci_high_diff = abs(r1.ci_high - r2.ci_high) / max(r1.ci_high, 0.01)

    # Adaptive CI tolerance based on outcome match
    effective_ci_tol = ci_tolerance
    if outcome_score > 0.8:
        effective_ci_tol = ci_tolerance * 1.5  # More lenient if outcomes match

    # Determine match type
    if hr_diff <= hr_tolerance:
        if ci_low_diff <= effective_ci_tol and ci_high_diff <= effective_ci_tol:
            return True, 'exact'
        return True, 'hr_match'

    if hr_diff <= 0.15:
        return True, 'close'

    return False, None


def count_agreement(results: List[ExtractorResult]) -> int:
    """
    Count how many extractors agree on the value.

    Uses pairwise comparison with majority voting.

    Returns:
        Number of extractors in the largest agreeing group
    """
    if not results:
        return 0

    values = [(r.extractor_id, r.value) for r in results if r.value is not None]
    if len(values) <= 1:
        return len(values)

    # Build agreement matrix
    n = len(values)
    agree_matrix = [[False] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                agree_matrix[i][j] = True
            else:
                agree_matrix[i][j] = values_agree(values[i][1], values[j][1])

    # Find largest agreeing cluster (greedy)
    used = [False] * n
    max_cluster = 0

    for start in range(n):
        if used[start]:
            continue

        cluster = [start]
        for j in range(start + 1, n):
            if not used[j] and all(agree_matrix[c][j] for c in cluster):
                cluster.append(j)

        if len(cluster) > max_cluster:
            max_cluster = len(cluster)

    return max_cluster


# ============================================================
# VALUE SELECTION
# ============================================================

def select_best_value(
    results: List[ExtractorResult],
    prefer_verified: bool = True
) -> Optional[ExtractorResult]:
    """
    Select the best value from multiple extractors.

    Priority:
    1. TruthCert verified
    2. Has provenance
    3. Wasserstein Grade A/B
    4. Highest confidence score
    5. First in list (E1 > E2 > E3)

    Returns:
        Best ExtractorResult, or None
    """
    if not results:
        return None

    candidates = [r for r in results if r.value is not None]
    if not candidates:
        return None

    # Sort by priority
    def priority_key(r: ExtractorResult) -> Tuple:
        verified_score = 1 if r.is_verified else 0
        provenance_score = 1 if r.has_provenance else 0
        wasserstein_score = {'A': 4, 'B': 3, 'C': 2, 'D': 1}.get(r.wasserstein_grade or '', 0)
        extractor_priority = {'E1': 3, 'E2': 2, 'E3': 1, 'E4': 0}.get(r.extractor_id, 0)

        return (
            -verified_score,
            -provenance_score,
            -wasserstein_score,
            -r.confidence_score,
            -extractor_priority
        )

    candidates.sort(key=priority_key)
    return candidates[0]


# ============================================================
# CONFIDENCE GRADING
# ============================================================

def calculate_confidence_grade(
    agreement_count: int,
    total_extractors: int,
    is_verified: bool,
    has_provenance: bool,
    wasserstein_grade: Optional[str],
    has_disagreement: bool
) -> ConfidenceGrade:
    """
    Calculate ensemble confidence grade.

    Grade A: 3+ agree + TruthCert verified + provenance
    Grade B: 2+ agree + provenance OR TruthCert verified
    Grade C: 2+ agree OR provenance complete
    Grade D: Single extractor only
    Grade F: Disagreement OR validation fails

    Returns:
        ConfidenceGrade
    """
    # Check for failures first
    if has_disagreement:
        return ConfidenceGrade.F

    # Grade A: 3+ agree + verified + provenance
    if agreement_count >= 3 and is_verified and has_provenance:
        return ConfidenceGrade.A

    # Grade B: 2+ agree + provenance OR verified
    if agreement_count >= 2 and (has_provenance or is_verified):
        return ConfidenceGrade.B

    # Wasserstein Grade A/B counts as verification
    if wasserstein_grade in ['A', 'B'] and agreement_count >= 2:
        return ConfidenceGrade.B

    # Grade C: 2+ agree OR provenance complete
    if agreement_count >= 2 or has_provenance:
        return ConfidenceGrade.C

    # Grade D: Single extractor only
    if agreement_count == 1:
        return ConfidenceGrade.D

    # Grade F: Nothing reliable
    return ConfidenceGrade.F


# ============================================================
# MAIN MERGER
# ============================================================

class EnsembleMerger:
    """
    Merge results from multiple extractors using weighted voting.

    Enhanced with:
    - OutcomeTextMatcher for better endpoint matching
    - ValueValidator for plausibility filtering
    - Adaptive CI tolerance
    """

    def __init__(
        self,
        agreement_tolerance: float = 0.02,
        prefer_verified: bool = True,
        use_outcome_matching: bool = True,
        filter_implausible: bool = True
    ):
        self.agreement_tolerance = agreement_tolerance
        self.prefer_verified = prefer_verified
        self.use_outcome_matching = use_outcome_matching
        self.filter_implausible = filter_implausible

    def _normalize_endpoint(self, endpoint: str) -> str:
        """
        Normalize endpoint names for matching across extractors.

        Only normalizes primary/unknown to PRIMARY_OUTCOME.
        Keeps specific endpoints as-is to avoid over-merging.
        """
        if not endpoint:
            return "UNKNOWN"

        endpoint_lower = endpoint.lower()

        # Primary/Unknown endpoints -> PRIMARY (these are the general extractions)
        if any(x in endpoint_lower for x in ['primary', 'unknown']):
            return "PRIMARY_OUTCOME"

        # Keep specific endpoints as-is
        return endpoint.upper()

    def merge(
        self,
        e1_results: List[ExtractorResult] = None,
        e2_results: List[ExtractorResult] = None,
        e3_results: List[ExtractorResult] = None,
        e4_results: List[ExtractorResult] = None
    ) -> List[MergedResult]:
        """
        Merge results from all extractors.

        Args:
            e1_results: Results from v2 Python extractor
            e2_results: Results from v4.8 JS extractor
            e3_results: Results from Wasserstein extractor
            e4_results: Results from TruthCert verification

        Returns:
            List of merged results
        """
        # Combine all results
        all_results = []
        for results, extractor_id in [
            (e1_results, 'E1'),
            (e2_results, 'E2'),
            (e3_results, 'E3'),
            (e4_results, 'E4')
        ]:
            if results:
                for r in results:
                    r.extractor_id = extractor_id
                    all_results.append(r)

        # Filter implausible values if enabled
        if self.filter_implausible:
            all_results = self._filter_implausible(all_results)

        # Group by endpoint (with normalization and outcome matching)
        by_endpoint: Dict[str, List[ExtractorResult]] = {}
        for r in all_results:
            # Normalize endpoint names
            endpoint = self._normalize_endpoint(r.endpoint)

            # Use outcome matching to find best group
            if self.use_outcome_matching and by_endpoint:
                best_match = self._find_best_endpoint_match(r, by_endpoint)
                if best_match:
                    endpoint = best_match

            if endpoint not in by_endpoint:
                by_endpoint[endpoint] = []
            by_endpoint[endpoint].append(r)

        # Merge each endpoint
        merged = []
        for endpoint, results in by_endpoint.items():
            merged_result = self._merge_endpoint(endpoint, results)
            merged.append(merged_result)

        return merged

    def _filter_implausible(self, results: List[ExtractorResult]) -> List[ExtractorResult]:
        """Filter out implausible values and adjust confidence"""
        filtered = []
        for r in results:
            if r.value is not None and r.ci_low is not None and r.ci_high is not None:
                plausible, conf_mult = ValueValidator.is_plausible(
                    r.value, r.ci_low, r.ci_high, r.measure_type
                )
                if plausible:
                    # Adjust confidence based on plausibility
                    r.confidence_score *= conf_mult
                    filtered.append(r)
                else:
                    logger.debug(f"Filtered implausible {r.measure_type}={r.value} from {r.extractor_id}")
            else:
                filtered.append(r)
        return filtered

    def _find_best_endpoint_match(
        self,
        result: ExtractorResult,
        existing_groups: Dict[str, List[ExtractorResult]]
    ) -> Optional[str]:
        """Find best matching endpoint group using outcome text"""
        if not result.outcome_text:
            return None

        best_match = None
        best_score = 0.0

        for endpoint, group in existing_groups.items():
            # Compare with first result in group that has outcome_text
            for existing in group:
                if existing.outcome_text:
                    score = OutcomeTextMatcher.outcomes_match(
                        result.outcome_text, existing.outcome_text
                    )
                    if score > best_score and score > 0.7:  # Require >70% match
                        best_score = score
                        best_match = endpoint
                    break

        return best_match

    def _merge_endpoint(
        self,
        endpoint: str,
        results: List[ExtractorResult]
    ) -> MergedResult:
        """Merge results for a single endpoint"""
        merged = MergedResult(
            endpoint=endpoint,
            measure_type=results[0].measure_type if results else "HR",
            individual_results=results
        )

        if not results:
            merged.confidence_grade = ConfidenceGrade.F
            return merged

        # Calculate agreement
        merged.agreement_count = count_agreement(results)
        merged.sources = list(set(r.extractor_id for r in results))

        # Check for TruthCert verification
        e4_verified = any(r.is_verified and r.extractor_id == 'E4' for r in results)
        merged.is_verified = e4_verified

        # Get best Wasserstein grade
        wasserstein_grades = [r.wasserstein_grade for r in results if r.wasserstein_grade]
        best_wasserstein = min(wasserstein_grades, default=None) if wasserstein_grades else None

        # Check for provenance
        has_provenance = any(r.has_provenance for r in results)

        # Check for disagreement (values differ significantly)
        values = [r.value for r in results if r.value is not None]
        has_disagreement = False
        if len(values) >= 2:
            # Check if any pair disagrees
            for i in range(len(values)):
                for j in range(i + 1, len(values)):
                    if not values_agree(values[i], values[j], self.agreement_tolerance):
                        has_disagreement = True
                        merged.disagreement_details = f"Values differ: {values}"
                        break

        # Select best value
        best = select_best_value(results, self.prefer_verified)
        if best:
            merged.value = best.value
            merged.ci_low = best.ci_low
            merged.ci_high = best.ci_high
            merged.provenance_page = best.provenance_page
            merged.provenance_text = best.provenance_text

        # Calculate confidence grade
        merged.confidence_grade = calculate_confidence_grade(
            agreement_count=merged.agreement_count,
            total_extractors=len(set(r.extractor_id for r in results)),
            is_verified=merged.is_verified,
            has_provenance=has_provenance,
            wasserstein_grade=best_wasserstein,
            has_disagreement=has_disagreement
        )

        return merged

    def merge_with_truthcert(
        self,
        extractions: List[ExtractorResult],
        truthcert_data: Dict[str, Any]
    ) -> List[MergedResult]:
        """
        Merge extractions with TruthCert verification data.

        Args:
            extractions: Combined extractions from E1/E2/E3
            truthcert_data: Ground truth from CTGov via TruthCert

        Returns:
            Verified merged results
        """
        # Convert TruthCert data to ExtractorResult format
        e4_results = []
        for endpoint, data in truthcert_data.get('effect_measures', {}).items():
            e4_results.append(ExtractorResult(
                extractor_id='E4',
                endpoint=endpoint,
                value=data.get('value'),
                ci_low=data.get('ci_low'),
                ci_high=data.get('ci_high'),
                measure_type=data.get('type', 'HR'),
                is_verified=True,
                has_provenance=True,
                provenance_text=f"CTGov: {truthcert_data.get('nct_id', 'unknown')}"
            ))

        return self.merge(
            e1_results=[r for r in extractions if r.extractor_id == 'E1'],
            e2_results=[r for r in extractions if r.extractor_id == 'E2'],
            e3_results=[r for r in extractions if r.extractor_id == 'E3'],
            e4_results=e4_results
        )


# ============================================================
# REPORTING
# ============================================================

def generate_ensemble_report(merged_results: List[MergedResult]) -> str:
    """Generate human-readable ensemble report"""
    lines = [
        "=" * 60,
        "ENSEMBLE EXTRACTION REPORT",
        "=" * 60,
        ""
    ]

    # Summary by grade
    grade_counts = {}
    for r in merged_results:
        grade = r.confidence_grade.value
        grade_counts[grade] = grade_counts.get(grade, 0) + 1

    lines.append("CONFIDENCE GRADE DISTRIBUTION:")
    for grade in ['A', 'B', 'C', 'D', 'F']:
        count = grade_counts.get(grade, 0)
        bar = '█' * count
        lines.append(f"  Grade {grade}: {count:3d} {bar}")

    lines.append("")
    lines.append("DETAILED RESULTS:")
    lines.append("-" * 60)

    for r in sorted(merged_results, key=lambda x: x.confidence_grade.value):
        grade_emoji = {'A': '✓', 'B': '○', 'C': '△', 'D': '?', 'F': '✗'}
        emoji = grade_emoji.get(r.confidence_grade.value, '?')

        value_str = f"{r.value:.2f}" if r.value else "N/A"
        ci_str = f"[{r.ci_low:.2f}-{r.ci_high:.2f}]" if r.ci_low and r.ci_high else ""

        lines.append(f"{emoji} [{r.confidence_grade.value}] {r.endpoint}")
        lines.append(f"    Value: {value_str} {ci_str}")
        lines.append(f"    Sources: {', '.join(r.sources)} (agreement: {r.agreement_count})")
        if r.is_verified:
            lines.append(f"    ✓ TruthCert verified")
        if r.disagreement_details:
            lines.append(f"    ⚠ {r.disagreement_details}")
        lines.append("")

    lines.append("=" * 60)
    total = len(merged_results)
    high_conf = grade_counts.get('A', 0) + grade_counts.get('B', 0)
    lines.append(f"Total endpoints: {total}")
    lines.append(f"High confidence (A+B): {high_conf} ({100*high_conf/total:.1f}%)" if total > 0 else "")
    lines.append("=" * 60)

    return "\n".join(lines)
