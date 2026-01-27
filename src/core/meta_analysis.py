"""
Meta-Analysis Support Module
Carries over advanced features from RCTExtractor_v4_8_AI.js

Features:
- SE calculation from CI bounds (for meta-analysis)
- Primary/Secondary outcome detection
- Subgroup analysis detection
- Continuous outcomes (Mean ± SD)
- Effect direction classification
- Derived measures (NNT from RD)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
import re
import math
from enum import Enum


class EffectDirection(Enum):
    FAVORS_TREATMENT = "favors_treatment"
    FAVORS_CONTROL = "favors_control"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


@dataclass
class MetaAnalysisFields:
    """Additional fields needed for meta-analysis"""
    # Log-transformed values (for ratio measures)
    log_value: Optional[float] = None
    se: Optional[float] = None  # Standard error
    variance: Optional[float] = None

    # Effect interpretation
    direction: EffectDirection = EffectDirection.UNKNOWN
    statistically_significant: bool = False
    clinically_meaningful: bool = False

    # Outcome classification
    is_primary: bool = False
    is_secondary: bool = False
    text_position: Optional[int] = None  # Position in text for tiebreaking


# ============================================================
# SE CALCULATION (from v4.8)
# ============================================================

def calculate_se_from_ci(
    value: float,
    ci_low: float,
    ci_high: float,
    ci_level: float = 0.95,
    measure_type: str = "ratio"
) -> Optional[float]:
    """
    Calculate standard error from confidence interval bounds.

    For ratio measures (HR, RR, OR):
    SE = (ln(CI_upper) - ln(CI_lower)) / (2 * Z)

    For difference measures (MD, RD):
    SE = (CI_upper - CI_lower) / (2 * Z)

    Args:
        value: Point estimate
        ci_low: Lower CI bound
        ci_high: Upper CI bound
        ci_level: Confidence level (default 0.95)
        measure_type: "ratio" or "difference"

    Returns:
        Standard error, or None if cannot calculate
    """
    # Z value for CI level (e.g., 1.96 for 95% CI)
    z_values = {
        0.90: 1.645,
        0.95: 1.96,
        0.975: 2.24,
        0.99: 2.576,
        0.999: 3.291
    }
    z = z_values.get(ci_level, 1.96)

    try:
        if measure_type == "ratio":
            # For ratio measures, use log scale
            if value > 0 and ci_low > 0 and ci_high > 0:
                log_ci_width = math.log(ci_high) - math.log(ci_low)
                se = log_ci_width / (2 * z)
                return se
        else:
            # For difference measures, use natural scale
            ci_width = ci_high - ci_low
            se = ci_width / (2 * z)
            return se
    except (ValueError, ZeroDivisionError):
        return None

    return None


def calculate_log_transform(value: float, se: float) -> Tuple[float, float]:
    """
    Calculate log-transformed value and SE.

    Args:
        value: Point estimate (e.g., HR)
        se: Standard error on log scale

    Returns:
        (log_value, variance)
    """
    if value > 0:
        log_value = math.log(value)
        variance = se * se
        return (log_value, variance)
    return (None, None)


# ============================================================
# PRIMARY OUTCOME DETECTION (from v4.8)
# ============================================================

PRIMARY_INDICATORS = [
    "primary outcome",
    "primary endpoint",
    "main outcome",
    "principal outcome",
    "primary composite",
    "primary efficacy",
    "coprimary"
]

SECONDARY_INDICATORS = [
    "secondary outcome",
    "secondary endpoint",
    "exploratory",
    "key secondary",
    "prespecified secondary"
]


def detect_outcome_priority(
    text: str,
    match_position: int,
    context_window: int = 400
) -> Tuple[bool, bool]:
    """
    Detect if an extraction is from primary or secondary outcome.

    Uses wide context search (400 chars before match) like v4.8.

    Args:
        text: Full document text
        match_position: Position of the match in text
        context_window: Characters to search before match

    Returns:
        (is_primary, is_secondary)
    """
    # Get wide context BEFORE the match
    start = max(0, match_position - context_window)
    end = min(len(text), match_position + 100)
    context = text[start:end].lower()

    # Also find the containing paragraph
    para_start = text.rfind('\n\n', 0, match_position)
    para_end = text.find('\n\n', match_position)
    paragraph = text[
        para_start if para_start >= 0 else 0:
        para_end if para_end >= 0 else len(text)
    ].lower()

    # Check for primary indicators
    has_primary = any(ind in context or ind in paragraph for ind in PRIMARY_INDICATORS)
    has_secondary = any(ind in context or ind in paragraph for ind in SECONDARY_INDICATORS)

    # Primary wins unless explicitly secondary
    if has_primary and not has_secondary:
        return (True, False)
    elif has_secondary:
        return (False, True)
    else:
        return (False, False)


# ============================================================
# EFFECT DIRECTION CLASSIFICATION (from v4.8)
# ============================================================

def classify_effect_direction(
    value: float,
    ci_low: Optional[float] = None,
    ci_high: Optional[float] = None,
    measure_type: str = "ratio"
) -> MetaAnalysisFields:
    """
    Classify effect direction and significance.

    For ratio measures (HR, RR, OR):
    - < 1 favors treatment
    - > 1 favors control
    - CI excludes 1 = statistically significant
    - CI < 0.8 or > 1.25 = clinically meaningful

    For difference measures (MD, RD):
    - < 0 favors treatment (usually)
    - > 0 favors control
    - CI excludes 0 = statistically significant

    Returns:
        MetaAnalysisFields with direction and significance
    """
    result = MetaAnalysisFields()

    if measure_type == "ratio":
        null_value = 1.0
        if value < 1:
            result.direction = EffectDirection.FAVORS_TREATMENT
        elif value > 1:
            result.direction = EffectDirection.FAVORS_CONTROL
        else:
            result.direction = EffectDirection.NEUTRAL

        if ci_low is not None and ci_high is not None:
            # Statistical significance: CI excludes 1
            result.statistically_significant = ci_high < 1.0 or ci_low > 1.0
            # Clinical meaningfulness: CI entirely < 0.8 or > 1.25
            result.clinically_meaningful = ci_high < 0.8 or ci_low > 1.25
    else:
        # Difference measures
        null_value = 0.0
        if value < 0:
            result.direction = EffectDirection.FAVORS_TREATMENT
        elif value > 0:
            result.direction = EffectDirection.FAVORS_CONTROL
        else:
            result.direction = EffectDirection.NEUTRAL

        if ci_low is not None and ci_high is not None:
            # Statistical significance: CI excludes 0
            result.statistically_significant = ci_high < 0 or ci_low > 0

    return result


# ============================================================
# SUBGROUP ANALYSIS DETECTION (from v4.8)
# ============================================================

@dataclass
class SubgroupAnalysis:
    """Detected subgroup analysis"""
    subgroup_type: str  # explicit, stratified, subset, prespecified, exploratory
    variable: Optional[str] = None
    interaction_p: Optional[float] = None
    is_prespecified: bool = False
    is_exploratory: bool = False
    position: Optional[int] = None


SUBGROUP_PATTERNS = [
    (r'subgroup\s+(?:analysis|analyses)\s+(?:by|of)\s+(\w+)', 'explicit'),
    (r'stratified\s+by\s+(\w+(?:\s+\w+)?)', 'stratified'),
    (r'among\s+(?:patients|those|subjects)\s+with\s+([^,\.]+)', 'subset'),
    (r'in\s+(?:the\s+)?(\w+)\s+subgroup', 'named'),
    (r'(?:pre-?specified|planned)\s+subgroup', 'prespecified'),
    (r'(?:exploratory|post-?hoc)\s+(?:subgroup|analysis)', 'exploratory'),
    (r'interaction\s+(?:p[- ]?value|test)', 'interaction'),
    (r'\(?interaction\s+p\s*[=<>]\s*(0?\.\d+)\)?', 'interaction_pvalue'),
    (r'forest\s+plot', 'forest_plot'),
    (r'heterogeneity\s+(?:across|between)\s+subgroups', 'heterogeneity')
]

COMMON_SUBGROUP_VARIABLES = [
    'age', 'sex', 'gender', 'diabetes', 'renal', 'kidney', 'egfr',
    'ejection fraction', 'lvef', 'nyha', 'prior', 'baseline',
    'region', 'geographic', 'race', 'ethnicity', 'bmi', 'weight'
]


def detect_subgroup_analyses(text: str) -> List[SubgroupAnalysis]:
    """
    Detect subgroup analyses in text.

    Returns:
        List of detected subgroup analyses
    """
    results = []
    text_lower = text.lower()
    has_prespecified = 'prespecified' in text_lower or 'pre-specified' in text_lower
    has_exploratory = 'exploratory' in text_lower or 'post-hoc' in text_lower

    for pattern, subgroup_type in SUBGROUP_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            subgroup = SubgroupAnalysis(
                subgroup_type=subgroup_type,
                variable=match.group(1) if match.lastindex and match.lastindex >= 1 else None,
                position=match.start(),
                is_prespecified=has_prespecified,
                is_exploratory=has_exploratory
            )

            # Extract interaction p-value if present
            if subgroup_type == 'interaction_pvalue':
                try:
                    subgroup.interaction_p = float(match.group(1))
                except (ValueError, IndexError):
                    pass

            results.append(subgroup)

    # Also check for common subgroup variables
    for variable in COMMON_SUBGROUP_VARIABLES:
        if f'by {variable}' in text_lower or f'{variable} subgroup' in text_lower:
            if not any(s.variable and variable in s.variable.lower() for s in results):
                results.append(SubgroupAnalysis(
                    subgroup_type='common',
                    variable=variable,
                    is_prespecified=has_prespecified
                ))

    return results


# ============================================================
# CONTINUOUS OUTCOMES (Mean ± SD) - from v4.8
# ============================================================

@dataclass
class ContinuousOutcome:
    """Continuous outcome (mean ± SD)"""
    mean: float
    sd: Optional[float] = None
    n: Optional[int] = None
    se: Optional[float] = None
    variance: Optional[float] = None
    label: str = "Continuous measure"
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    raw_text: Optional[str] = None
    position: Optional[int] = None


CONTINUOUS_PATTERNS = [
    # Mean [variable] was/= X ± SD format
    r'(?:mean|average)\s+(?:[A-Za-z]+\s+)?(?:was|is|=|of|:)?\s*(-?\d+\.?\d*)\s*%?\s*(?:±|\+\/?-|plus\/minus)\s*(\d+\.?\d*)',
    # Simple mean ± SD
    r'(?:mean|average)\s*(?:of|:)?\s*(-?\d+\.?\d*)\s*(?:±|\+\/?-|plus\/minus)\s*(\d+\.?\d*)',
    # Value ± SD with common variable names
    r'(?:age|weight|bmi|lvef|ef|gfr|egfr|hba1c|bp|sbp|dbp|hr)\s*(?:was|of|:)?\s*(-?\d+\.?\d*)\s*(?:±|\+\/?-|plus\/minus)\s*(\d+\.?\d*)',
    # Mean (SD) format
    r'(-?\d+\.?\d*)\s*\(\s*(?:SD|sd)\s*[=:]?\s*(\d+\.?\d*)\s*\)',
    # Mean (±SD) format
    r'(-?\d+\.?\d*)\s*\(\s*[±\+\-]\s*(\d+\.?\d*)\s*\)',
    # Change from baseline
    r'(?:change|difference|reduction)\s*(?:from\s*baseline)?[:\s]*(-?\d+\.?\d*)\s*\((\d+\.?\d*)\)',
]


def extract_continuous_outcomes(text: str) -> List[ContinuousOutcome]:
    """
    Extract continuous outcomes (Mean ± SD) from text.

    For meta-analysis of continuous outcomes.

    Returns:
        List of extracted continuous outcomes
    """
    outcomes = []
    seen_values = set()  # Deduplicate by mean+sd

    for pattern in CONTINUOUS_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                mean_val = float(match.group(1))
                sd_val = float(match.group(2)) if match.lastindex >= 2 else None

                # Deduplicate
                key = f"{mean_val:.2f}-{sd_val:.2f}" if sd_val else f"{mean_val:.2f}"
                if key in seen_values:
                    continue
                seen_values.add(key)

                # Extract label from context
                context_start = max(0, match.start() - 40)
                context = text[context_start:match.start()]
                label = extract_variable_label(context) or "Continuous measure"

                outcome = ContinuousOutcome(
                    mean=mean_val,
                    sd=sd_val,
                    label=label,
                    raw_text=match.group(0),
                    position=match.start()
                )

                # Calculate SE if we have SD and can find N
                if sd_val:
                    full_context = text[max(0, match.start() - 100):min(len(text), match.end() + 100)]
                    n_match = re.search(r'[Nn]\s*=\s*(\d+)', full_context)
                    if n_match:
                        outcome.n = int(n_match.group(1))
                        outcome.se = sd_val / math.sqrt(outcome.n)
                        outcome.variance = outcome.se * outcome.se

                outcomes.append(outcome)

            except (ValueError, IndexError):
                continue

    return outcomes


def extract_variable_label(context: str) -> Optional[str]:
    """Extract variable name from context preceding a value"""
    # Common patterns
    patterns = [
        r'(?:mean|median|average)\s+([A-Za-z][A-Za-z0-9\-]{0,15})\s*(?:was|is|=|:)?$',
        r'([A-Za-z][A-Za-z0-9\-]{2,15})\s*(?:was|of|:)\s*$',
    ]

    for pattern in patterns:
        match = re.search(pattern, context, re.IGNORECASE)
        if match and match.group(1):
            return match.group(1).strip()

    return None


# ============================================================
# DERIVED MEASURES (NNT from RD) - from v4.8
# ============================================================

def calculate_nnt_from_rd(rd: float, rd_ci_low: Optional[float] = None, rd_ci_high: Optional[float] = None) -> Dict[str, Any]:
    """
    Calculate NNT from Risk Difference.

    NNT = 100 / |RD| (when RD is in percentage points)
    or NNT = 1 / |RD| (when RD is a proportion)

    Args:
        rd: Risk difference (as percentage points, e.g., -5.2)
        rd_ci_low: Lower CI bound
        rd_ci_high: Upper CI bound

    Returns:
        Dict with NNT and CI if calculable
    """
    if rd == 0:
        return {'nnt': float('inf'), 'derived': True, 'source_rd': rd}

    # Assume RD is in percentage points if |RD| > 1
    if abs(rd) > 1:
        nnt = abs(100 / rd)
    else:
        nnt = abs(1 / rd)

    result = {
        'nnt': round(nnt),
        'derived': True,
        'derived_from': 'RD',
        'source_rd': rd
    }

    # Calculate CI for NNT (note: bounds swap because 1/x is monotonically decreasing)
    if rd_ci_low is not None and rd_ci_high is not None:
        if rd_ci_low != 0 and rd_ci_high != 0:
            if abs(rd) > 1:
                nnt_high = abs(100 / rd_ci_low) if rd_ci_low != 0 else float('inf')
                nnt_low = abs(100 / rd_ci_high) if rd_ci_high != 0 else float('inf')
            else:
                nnt_high = abs(1 / rd_ci_low) if rd_ci_low != 0 else float('inf')
                nnt_low = abs(1 / rd_ci_high) if rd_ci_high != 0 else float('inf')

            result['nnt_ci_low'] = round(min(nnt_low, nnt_high))
            result['nnt_ci_high'] = round(max(nnt_low, nnt_high))

    return result


# ============================================================
# ENHANCE EXTRACTION WITH META-ANALYSIS FIELDS
# ============================================================

def enhance_extraction(
    value: float,
    ci_low: float,
    ci_high: float,
    measure_type: str,
    full_text: str,
    match_position: int,
    ci_level: float = 0.95
) -> MetaAnalysisFields:
    """
    Enhance an extraction with all meta-analysis fields.

    Combines:
    - SE calculation
    - Log transformation (for ratios)
    - Effect direction classification
    - Primary/secondary detection

    Returns:
        MetaAnalysisFields with all computed values
    """
    result = MetaAnalysisFields()

    # SE and log transform
    if measure_type in ['HR', 'RR', 'OR']:
        result.se = calculate_se_from_ci(value, ci_low, ci_high, ci_level, 'ratio')
        if result.se:
            result.log_value, result.variance = calculate_log_transform(value, result.se)
    else:
        result.se = calculate_se_from_ci(value, ci_low, ci_high, ci_level, 'difference')
        if result.se:
            result.variance = result.se * result.se

    # Effect direction
    effect_class = classify_effect_direction(
        value, ci_low, ci_high,
        'ratio' if measure_type in ['HR', 'RR', 'OR'] else 'difference'
    )
    result.direction = effect_class.direction
    result.statistically_significant = effect_class.statistically_significant
    result.clinically_meaningful = effect_class.clinically_meaningful

    # Primary/secondary detection
    result.is_primary, result.is_secondary = detect_outcome_priority(full_text, match_position)
    result.text_position = match_position

    return result
