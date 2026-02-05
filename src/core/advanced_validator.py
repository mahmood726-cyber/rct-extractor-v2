"""
Advanced Validator for RCT Extractor v2.13
==========================================

Implements:
1. SE/SD confusion detection
2. Statistical consistency validation
3. Timepoint priority scoring
4. Multi-arm trial detection
5. Cross-validation checks
"""

import re
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    ERROR = "error"          # Must not extract
    WARNING = "warning"      # Extract with caution
    INFO = "info"            # Informational note


@dataclass
class ValidationIssue:
    """A validation issue found during extraction"""
    severity: ValidationSeverity
    code: str
    message: str
    suggestion: Optional[str] = None
    corrected_value: Optional[float] = None


@dataclass
class ValidationResult:
    """Result of validation checks"""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    confidence: float = 1.0  # 0.0 to 1.0


# =============================================================================
# SE/SD CONFUSION DETECTOR
# =============================================================================

class SESDConfusionDetector:
    """
    Detect when SE is misreported as SD (most common meta-analysis error).

    Reference: https://onlinelibrary.wiley.com/doi/full/10.1002/cesm.70013
    "75% of influential meta-analyses contain at least one error"
    """

    # Typical coefficient of variation ranges by outcome type
    CV_RANGES = {
        "ldl": (0.15, 0.40),       # LDL cholesterol
        "hdl": (0.15, 0.40),       # HDL cholesterol
        "hba1c": (0.08, 0.20),     # HbA1c
        "sbp": (0.10, 0.20),       # Systolic BP
        "dbp": (0.10, 0.25),       # Diastolic BP
        "weight": (0.10, 0.25),    # Body weight
        "bmi": (0.10, 0.25),       # BMI
        "egfr": (0.20, 0.40),      # eGFR
        "creatinine": (0.15, 0.35),
        "bnp": (0.50, 1.50),       # BNP (high variability)
        "troponin": (0.50, 2.00),  # Troponin (high variability)
        "crp": (0.50, 1.50),       # CRP
        "default": (0.10, 0.50),   # Default range
    }

    def detect_confusion(self, mean: float, reported_sd: float, n: int,
                        outcome_type: str = "default") -> ValidationResult:
        """
        Detect if reported SD is likely misreported SE.

        Logic:
        - SE = SD / sqrt(n)
        - If reported_sd * sqrt(n) gives more plausible CV, it's likely SE
        """
        issues = []

        if mean == 0 or reported_sd <= 0:
            return ValidationResult(is_valid=True, confidence=0.5)

        # Calculate CV with reported value
        reported_cv = reported_sd / abs(mean)

        # Get expected CV range
        cv_range = self.CV_RANGES.get(outcome_type.lower(), self.CV_RANGES["default"])
        cv_min, cv_max = cv_range

        # Calculate what CV would be if this were SE converted to SD
        potential_sd = reported_sd * math.sqrt(n)
        potential_cv = potential_sd / abs(mean)

        # Decision logic
        if reported_cv < cv_min * 0.3:  # Suspiciously small CV
            # Check if SE->SD conversion gives plausible CV
            if cv_min <= potential_cv <= cv_max * 1.5:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="SE_AS_SD",
                    message=f"Reported SD ({reported_sd:.2f}) gives implausibly low CV ({reported_cv:.3f}). "
                            f"If this is SE, SD would be {potential_sd:.2f} (CV={potential_cv:.3f})",
                    suggestion="Verify if reported dispersion is SE or SD",
                    corrected_value=potential_sd
                ))
                return ValidationResult(
                    is_valid=True,
                    issues=issues,
                    confidence=0.4  # Low confidence in extraction
                )

        # Also check if CV is implausibly high (might indicate other issues)
        if reported_cv > cv_max * 3:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="HIGH_CV",
                message=f"Unusually high CV ({reported_cv:.3f}) for {outcome_type}",
                suggestion="Verify data entry and units"
            ))
            return ValidationResult(is_valid=True, issues=issues, confidence=0.7)

        return ValidationResult(is_valid=True, confidence=1.0)


# =============================================================================
# STATISTICAL CONSISTENCY VALIDATOR
# =============================================================================

class StatisticalConsistencyValidator:
    """
    Cross-validate extracted values for statistical consistency.
    """

    def validate_hr_consistency(self, hr: float, ci_lower: float, ci_upper: float,
                                p_value: Optional[float] = None,
                                events_tx: Optional[int] = None,
                                events_ctrl: Optional[int] = None,
                                n_tx: Optional[int] = None,
                                n_ctrl: Optional[int] = None) -> ValidationResult:
        """Validate HR extraction for consistency"""
        issues = []

        # 1. CI must contain HR
        if not (ci_lower < hr < ci_upper):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="HR_OUTSIDE_CI",
                message=f"HR {hr} is outside CI [{ci_lower}, {ci_upper}]"
            ))
            return ValidationResult(is_valid=False, issues=issues, confidence=0.0)

        # 2. CI order
        if ci_lower >= ci_upper:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="CI_ORDER",
                message=f"CI lower ({ci_lower}) >= upper ({ci_upper})"
            ))
            return ValidationResult(is_valid=False, issues=issues, confidence=0.0)

        # 3. P-value consistency (if provided)
        if p_value is not None:
            ci_crosses_one = ci_lower <= 1.0 <= ci_upper

            if p_value < 0.05 and ci_crosses_one:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="PVALUE_CI_MISMATCH",
                    message=f"P={p_value} but 95% CI [{ci_lower}, {ci_upper}] crosses 1.0"
                ))

            if p_value >= 0.05 and not ci_crosses_one:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="PVALUE_CI_MISMATCH",
                    message=f"P={p_value} but 95% CI [{ci_lower}, {ci_upper}] doesn't cross 1.0"
                ))

        # 4. Event validation (if provided)
        if all(v is not None for v in [events_tx, events_ctrl, n_tx, n_ctrl]):
            if events_tx > n_tx:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="EVENTS_EXCEED_N",
                    message=f"Treatment events ({events_tx}) > sample size ({n_tx})"
                ))
                return ValidationResult(is_valid=False, issues=issues, confidence=0.0)

            if events_ctrl > n_ctrl:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="EVENTS_EXCEED_N",
                    message=f"Control events ({events_ctrl}) > sample size ({n_ctrl})"
                ))
                return ValidationResult(is_valid=False, issues=issues, confidence=0.0)

        # 5. Plausibility bounds
        if hr < 0.01 or hr > 100:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="IMPLAUSIBLE_HR",
                message=f"HR {hr} is outside typical range [0.01, 100]"
            ))

        # 6. CI width check (suspiciously narrow or wide)
        ci_ratio = ci_upper / ci_lower if ci_lower > 0 else float('inf')
        if ci_ratio < 1.05:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="NARROW_CI",
                message=f"Unusually narrow CI (ratio={ci_ratio:.3f})"
            ))
        elif ci_ratio > 20:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="WIDE_CI",
                message=f"Unusually wide CI (ratio={ci_ratio:.3f})"
            ))

        confidence = 1.0 - (len(issues) * 0.1)
        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
            issues=issues,
            confidence=max(0.3, confidence)
        )


# =============================================================================
# TIMEPOINT PRIORITY SCORER
# =============================================================================

class TimepointPriorityScorer:
    """
    Score and rank timepoints to identify primary endpoint timepoint.
    """

    PRIORITY_KEYWORDS = [
        # High priority - primary designations
        (r"primary\s+(endpoint|outcome|analysis)", 10),
        (r"primary\s+efficacy", 10),
        (r"co-?primary", 9),

        # Medium-high - final/overall
        (r"final\s+analysis", 8),
        (r"overall\s+(survival|analysis)", 8),
        (r"end\s+of\s+(study|treatment|follow-?up)", 7),
        (r"median\s+follow-?up", 7),

        # Medium - specific timepoints
        (r"at\s+\d+\s+(months?|years?|weeks?)", 5),
        (r"\d+-?(month|year|week)\s+(follow-?up|analysis)", 5),

        # Lower priority - secondary/exploratory
        (r"secondary\s+(endpoint|outcome)", 3),
        (r"exploratory", 2),
        (r"post-?hoc", 1),

        # Negative priority - interim
        (r"interim\s+analysis", -3),
        (r"first\s+interim", -5),
        (r"planned\s+interim", -4),
        (r"early\s+termination", -2),
    ]

    def score_timepoint(self, timepoint: str, context: str) -> Tuple[float, str]:
        """
        Score a timepoint based on context keywords.

        Returns: (score, explanation)
        """
        context_lower = context.lower()
        score = 0
        matched_keywords = []

        for pattern, points in self.PRIORITY_KEYWORDS:
            if re.search(pattern, context_lower):
                score += points
                matched_keywords.append((pattern, points))

        # Bonus for numeric timepoint (more specific)
        if re.search(r'\d+', timepoint):
            score += 1

        # Penalty for "not" or "excluding" nearby
        if re.search(r'\b(not|excluding|except)\b.*' + re.escape(timepoint.lower()), context_lower):
            score -= 3

        explanation = "; ".join([f"{p}: {pts:+d}" for p, pts in matched_keywords]) if matched_keywords else "no keywords"

        return score, explanation

    def rank_timepoints(self, timepoints: List[Tuple[str, str]]) -> List[Tuple[str, float, str]]:
        """
        Rank multiple timepoints by priority score.

        Args:
            timepoints: List of (timepoint_value, context_text) tuples

        Returns:
            List of (timepoint, score, explanation) sorted by score descending
        """
        scored = []
        for tp, context in timepoints:
            score, explanation = self.score_timepoint(tp, context)
            scored.append((tp, score, explanation))

        return sorted(scored, key=lambda x: x[1], reverse=True)


# =============================================================================
# MULTI-ARM TRIAL DETECTOR
# =============================================================================

class MultiArmTrialDetector:
    """
    Detect and structure multi-arm trial comparisons.
    """

    ARM_PATTERNS = [
        # "Drug A 10mg vs Drug B vs placebo" - 3 arms with optional dosing
        r'([A-Za-z]+(?:\s+[A-Za-z])?(?:\s+\d+\s*mg)?)\s+vs\.?\s+([A-Za-z]+(?:\s+[A-Za-z])?(?:\s+\d+\s*mg)?)\s+vs\.?\s+([A-Za-z]+)',

        # "Drug A 10mg vs Drug B" captures both arms
        r'([\w\s]+\d+\s*mg)\s+vs\.?\s+([\w\s]+)',

        # "Treatment arm 1, arm 2, and placebo"
        r'(\w+)\s*,\s*(\w+)\s*,?\s+and\s+(\w+)',

        # "Group A (n=100), Group B (n=100), Group C (n=100)"
        r'[Gg]roup\s+(\w)\s*\([^)]+\)\s*,\s*[Gg]roup\s+(\w)\s*\([^)]+\)\s*,\s*[Gg]roup\s+(\w)',
    ]

    COMPARISON_PATTERNS = [
        # "For Drug A versus placebo, the hazard ratio was 0.75" or "For Drug B versus placebo, HR was 0.82"
        r'[Ff]or\s+(Drug\s+[A-Za-z])\s+(?:vs\.?|versus)\s+(\w+),.*?(?:hazard\s+ratio|HR)\s+(?:was\s+)?(\d+\.?\d*)',

        # "Drug A vs placebo: HR 0.75"
        r'(\w+(?:\s+\d+\s*mg)?)\s+vs\.?\s+(\w+)[\s:,]+(?:HR|OR|RR)\s*[=:]?\s*(\d+\.?\d*)',

        # "Drug A showed HR 0.75" or "Drug A: HR 0.75"
        r'(Drug\s+[A-Za-z])\s+(?:showed|:)\s*(?:HR|OR|RR)\s*[=:]?\s*(\d+\.?\d*)',

        # "Treatment vs control: HR 0.75"
        r'(\w+)\s+vs\.?\s+(\w+)\s*:\s*(?:HR|OR|RR)\s*(\d+\.?\d*)',
    ]

    @dataclass
    class ArmComparison:
        treatment: str
        comparator: str
        effect_type: str
        effect_size: float
        ci_lower: Optional[float] = None
        ci_upper: Optional[float] = None

    @dataclass
    class MultiArmResult:
        arms: List[str]
        comparisons: List['MultiArmTrialDetector.ArmComparison']
        reference_arm: Optional[str] = None
        is_multiarm: bool = False

    def detect(self, text: str) -> MultiArmResult:
        """Detect multi-arm trial structure"""
        arms = set()
        comparisons = []

        # Find arm mentions
        for pattern in self.ARM_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                arms.update([m.strip() for m in match if m.strip()])

        # Find comparisons - each pattern may have different group counts
        for i, pattern in enumerate(self.COMPARISON_PATTERNS):
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    groups = match.groups()
                    if len(groups) >= 3:
                        # Pattern with treatment, comparator, effect
                        comp = self.ArmComparison(
                            treatment=groups[0].strip(),
                            comparator=groups[1].strip(),
                            effect_type="HR",
                            effect_size=float(groups[2])
                        )
                        comparisons.append(comp)
                        arms.add(comp.treatment)
                        arms.add(comp.comparator)
                    elif len(groups) == 2:
                        # Pattern with only treatment and effect (e.g., "Drug A showed HR 0.75")
                        arms.add(groups[0].strip())
                except (ValueError, IndexError):
                    continue

        # Identify reference arm (most common comparator)
        reference = None
        if comparisons:
            comparator_counts = {}
            for c in comparisons:
                comparator_counts[c.comparator] = comparator_counts.get(c.comparator, 0) + 1
            reference = max(comparator_counts, key=comparator_counts.get)

        return self.MultiArmResult(
            arms=list(arms),
            comparisons=comparisons,
            reference_arm=reference,
            is_multiarm=len(arms) > 2
        )


# =============================================================================
# ADDITIONAL EFFECT TYPE PATTERNS
# =============================================================================

ADDITIONAL_EFFECT_PATTERNS = {
    # Subdistribution Hazard Ratio (competing risks)
    'sHR': [
        r'(?:subdistribution\s+)?hazard\s+ratio\s+(?:was\s+)?(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-\u2013\u2014]\s*(\d+\.?\d*)',
        r'\bsHR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-\u2013\u2014]\s*(\d+\.?\d*)',
    ],

    # Cause-specific Hazard Ratio
    'csHR': [
        r'(?:cause-?specific\s+)?(?:hazard\s+ratio|csHR)[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)',
        r'\bcsHR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
    ],

    # Win Ratio
    'WR': [
        r'win\s+ratio\s+(?:was\s+)?(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-\u2013\u2014]\s*(\d+\.?\d*)',
        r'\bWR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-\u2013\u2014]\s*(\d+\.?\d*)',
    ],

    # Restricted Mean Survival Time difference
    'RMST': [
        r'(?:RMST\s+)?(?:difference|diff)[,;:\s=]+(-?\d+\.?\d*)\s*(?:months?|years?)?\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
        r'\bRMST\b.*?(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
    ],

    # Risk Difference (absolute)
    'RD': [
        r'risk\s+difference\s+(?:was\s+)?(-?\d+\.?\d*)\s*%?\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        r'risk\s+difference[,;:\s=]+(-?\d+\.?\d*)\s*%?\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-\u2013\u2014]\s*(-?\d+\.?\d*)',
        r'\bRD\b[,;:\s=]+(-?\d+\.?\d*)\s*%?\s*[\(\[]\s*(-?\d+\.?\d*)\s*[-\u2013\u2014]\s*(-?\d+\.?\d*)',
        r'absolute\s+(?:risk\s+)?(?:reduction|difference)\s+(-?\d+\.?\d*)\s*%?\s*[\(\[]\s*(-?\d+\.?\d*)\s*[-\u2013\u2014]\s*(-?\d+\.?\d*)',
    ],

    # Diagnostic Odds Ratio
    'DOR': [
        r'diagnostic\s+odds\s+ratio\s+(?:was\s+)?(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-\u2013\u2014]\s*(\d+\.?\d*)',
        r'\bDOR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-\u2013\u2014]\s*(\d+\.?\d*)',
    ],

    # Likelihood Ratio
    'LR': [
        r'(?:positive\s+)?likelihood\s+ratio[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)',
        r'\bLR\+?\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
    ],

    # Correlation coefficient
    'r': [
        r"(?:correlation|Pearson'?s?\s+r)[,;:\s=]+(-?\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-\u2013\u2014]\s*(-?\d+\.?\d*)",
        r'\br\s*=\s*(-?\d+\.?\d*)\s*[\(\[]\s*(-?\d+\.?\d*)\s*[-\u2013\u2014]\s*(-?\d+\.?\d*)',
    ],
}


def extract_additional_effects(text: str) -> List[dict]:
    """Extract additional effect types not in main extractor"""
    results = []
    seen = set()

    for effect_type, patterns in ADDITIONAL_EFFECT_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = float(match.group(1))
                    ci_lower = float(match.group(2))
                    ci_upper = float(match.group(3))

                    # Basic validation
                    if ci_lower >= ci_upper:
                        continue

                    key = (effect_type, round(value, 3))
                    if key in seen:
                        continue
                    seen.add(key)

                    results.append({
                        'type': effect_type,
                        'effect_size': value,
                        'ci_lower': ci_lower,
                        'ci_upper': ci_upper
                    })
                except (ValueError, IndexError):
                    continue

    return results


# =============================================================================
# UNIFIED ADVANCED EXTRACTOR
# =============================================================================

class AdvancedExtractor:
    """
    Unified extractor combining all advanced validation and extraction features.
    """

    def __init__(self):
        self.se_sd_detector = SESDConfusionDetector()
        self.consistency_validator = StatisticalConsistencyValidator()
        self.timepoint_scorer = TimepointPriorityScorer()
        self.multiarm_detector = MultiArmTrialDetector()

    def extract_with_validation(self, text: str) -> dict:
        """
        Extract effect estimates with full validation.
        """
        # Standard extraction
        from run_extended_validation_v8 import extract_effect_estimates
        standard_results = extract_effect_estimates(text)

        # Additional effect types
        additional_results = extract_additional_effects(text)

        # Multi-arm detection
        multiarm = self.multiarm_detector.detect(text)

        # Validate each result
        validated_results = []
        for result in standard_results + additional_results:
            if result['type'] in ['HR', 'sHR', 'csHR']:
                validation = self.consistency_validator.validate_hr_consistency(
                    result['effect_size'],
                    result['ci_lower'],
                    result['ci_upper']
                )
                result['validation'] = {
                    'is_valid': validation.is_valid,
                    'confidence': validation.confidence,
                    'issues': [{'code': i.code, 'message': i.message} for i in validation.issues]
                }
            validated_results.append(result)

        return {
            'results': validated_results,
            'multiarm': {
                'is_multiarm': multiarm.is_multiarm,
                'arms': multiarm.arms,
                'reference_arm': multiarm.reference_arm
            },
            'total_extracted': len(validated_results)
        }
