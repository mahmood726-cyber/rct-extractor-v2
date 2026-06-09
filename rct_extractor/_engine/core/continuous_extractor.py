"""
Continuous Outcomes Extractor (Mean/SD)
========================================

Handles the "boss fight" of meta-analysis extraction:
- Mean ± SD, Mean (SD), columnar tables
- Unit detection and validation
- SE/IQR/CI conversion with explicit assumption tracking
- Numeric sanity checks and N consistency
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any
from enum import Enum
import math


class DispersionType(Enum):
    """Type of dispersion measure"""
    SD = "SD"           # Standard deviation
    SE = "SE"           # Standard error
    CI_95 = "CI_95"     # 95% confidence interval
    CI_99 = "CI_99"     # 99% confidence interval
    IQR = "IQR"         # Interquartile range
    RANGE = "RANGE"     # Min-max range
    UNKNOWN = "UNKNOWN"


class ConversionMethod(Enum):
    """Method used for SD conversion"""
    NONE = "none"
    SE_TO_SD = "se_to_sd"           # SD = SE * sqrt(n)
    CI_TO_SD = "ci_to_sd"           # SD = sqrt(n) * (upper - lower) / 3.92
    IQR_TO_SD = "iqr_to_sd"         # SD = IQR / 1.35 (normal assumption)
    RANGE_TO_SD = "range_to_sd"     # SD = range / 4 (rough approximation)
    MANUAL_REQUIRED = "manual_required"


@dataclass
class ConversionResult:
    """Result of dispersion conversion"""
    original_type: DispersionType
    original_lower: float
    original_upper: Optional[float]
    converted_sd: Optional[float]
    method: ConversionMethod
    assumptions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: float = 1.0  # 1.0 = high confidence, 0.0 = low


@dataclass
class ContinuousOutcome:
    """A continuous outcome extraction"""
    arm_name: str
    n: int
    mean: float
    dispersion_value: float
    dispersion_type: DispersionType
    sd: Optional[float] = None  # Converted or direct SD
    conversion: Optional[ConversionResult] = None
    unit: Optional[str] = None
    timepoint: Optional[str] = None

    # Provenance
    source_text: str = ""
    pattern_matched: str = ""

    # Validation
    validation_passed: bool = True
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)


@dataclass
class ContinuousExtractionReport:
    """Full extraction report for continuous outcomes"""
    outcomes: List[ContinuousOutcome] = field(default_factory=list)
    mean_difference: Optional[float] = None
    mean_difference_ci: Optional[Tuple[float, float]] = None
    pooled_sd: Optional[float] = None
    effect_size_d: Optional[float] = None  # Cohen's d

    # Overall validation
    n_consistency_check: bool = True
    unit_consistency_check: bool = True

    # Flags for manual review
    requires_manual_review: bool = False
    review_reasons: List[str] = field(default_factory=list)


class DispersionConverter:
    """
    Convert between dispersion measures with explicit assumptions.

    CRITICAL: Does NOT convert unless all required assumptions are explicit.
    Flags "manual_required" otherwise.
    """

    @staticmethod
    def se_to_sd(se: float, n: int) -> ConversionResult:
        """
        Convert SE to SD: SD = SE * sqrt(n)

        Assumptions:
        - SE was calculated as SD/sqrt(n)
        - n is the sample size for this arm
        """
        if n <= 0:
            return ConversionResult(
                original_type=DispersionType.SE,
                original_lower=se,
                original_upper=None,
                converted_sd=None,
                method=ConversionMethod.MANUAL_REQUIRED,
                assumptions=[],
                warnings=["Invalid n: must be > 0"]
            )

        sd = se * math.sqrt(n)

        return ConversionResult(
            original_type=DispersionType.SE,
            original_lower=se,
            original_upper=None,
            converted_sd=sd,
            method=ConversionMethod.SE_TO_SD,
            assumptions=[
                "SE was calculated as SD/sqrt(n)",
                f"n={n} is the sample size for this arm"
            ],
            confidence=0.95
        )

    @staticmethod
    def ci_to_sd(ci_lower: float, ci_upper: float, n: int,
                  confidence_level: float = 0.95) -> ConversionResult:
        """
        Convert 95% CI to SD.

        For 95% CI: SD = sqrt(n) * (upper - lower) / 3.92
        For 99% CI: SD = sqrt(n) * (upper - lower) / 5.15

        Assumptions:
        - Normal distribution
        - CI is for the mean (not median or other)
        - CI was calculated as mean ± z*SE
        """
        if n <= 0:
            return ConversionResult(
                original_type=DispersionType.CI_95 if confidence_level == 0.95 else DispersionType.CI_99,
                original_lower=ci_lower,
                original_upper=ci_upper,
                converted_sd=None,
                method=ConversionMethod.MANUAL_REQUIRED,
                assumptions=[],
                warnings=["Invalid n: must be > 0"]
            )

        if ci_lower >= ci_upper:
            return ConversionResult(
                original_type=DispersionType.CI_95,
                original_lower=ci_lower,
                original_upper=ci_upper,
                converted_sd=None,
                method=ConversionMethod.MANUAL_REQUIRED,
                assumptions=[],
                warnings=["Invalid CI: lower >= upper"]
            )

        # Z-values for different confidence levels
        z_values = {0.95: 1.96, 0.99: 2.576, 0.90: 1.645}
        z = z_values.get(confidence_level, 1.96)
        divisor = 2 * z  # 3.92 for 95% CI

        ci_width = ci_upper - ci_lower
        se = ci_width / divisor
        sd = se * math.sqrt(n)

        return ConversionResult(
            original_type=DispersionType.CI_95 if confidence_level == 0.95 else DispersionType.CI_99,
            original_lower=ci_lower,
            original_upper=ci_upper,
            converted_sd=sd,
            method=ConversionMethod.CI_TO_SD,
            assumptions=[
                "Normal distribution assumed",
                "CI is for the mean",
                f"CI was calculated as mean ± {z}*SE",
                f"n={n} is the sample size"
            ],
            confidence=0.85,
            warnings=["Conversion assumes normal distribution - verify in source"]
        )

    @staticmethod
    def iqr_to_sd(q1: float, q3: float, distribution_assumed: str = "normal") -> ConversionResult:
        """
        Convert IQR to SD.

        For normal distribution: SD ≈ IQR / 1.35

        WARNING: This is a rough approximation. Only valid for normal distributions.
        For skewed data, this will be inaccurate.
        """
        if q1 >= q3:
            return ConversionResult(
                original_type=DispersionType.IQR,
                original_lower=q1,
                original_upper=q3,
                converted_sd=None,
                method=ConversionMethod.MANUAL_REQUIRED,
                assumptions=[],
                warnings=["Invalid IQR: Q1 >= Q3"]
            )

        iqr = q3 - q1

        if distribution_assumed != "normal":
            return ConversionResult(
                original_type=DispersionType.IQR,
                original_lower=q1,
                original_upper=q3,
                converted_sd=None,
                method=ConversionMethod.MANUAL_REQUIRED,
                assumptions=[],
                warnings=[
                    "IQR-to-SD conversion requires normal distribution assumption",
                    f"Distribution reported as '{distribution_assumed}' - manual conversion required"
                ]
            )

        sd = iqr / 1.35

        return ConversionResult(
            original_type=DispersionType.IQR,
            original_lower=q1,
            original_upper=q3,
            converted_sd=sd,
            method=ConversionMethod.IQR_TO_SD,
            assumptions=[
                "Normal distribution explicitly assumed",
                "IQR/1.35 approximation used"
            ],
            confidence=0.70,
            warnings=[
                "IQR-to-SD conversion is approximate",
                "May be inaccurate for skewed data",
                "Consider using median/IQR directly if available"
            ]
        )

    @staticmethod
    def range_to_sd(min_val: float, max_val: float, n: int) -> ConversionResult:
        """
        Convert range to SD (very rough approximation).

        Common approximations:
        - SD ≈ range / 4 (for n < 25)
        - SD ≈ range / 6 (for n > 200)
        - See Hozo et al. (2005) for n-specific formulas

        WARNING: This is VERY approximate. Flag for manual review.
        """
        if min_val >= max_val:
            return ConversionResult(
                original_type=DispersionType.RANGE,
                original_lower=min_val,
                original_upper=max_val,
                converted_sd=None,
                method=ConversionMethod.MANUAL_REQUIRED,
                assumptions=[],
                warnings=["Invalid range: min >= max"]
            )

        range_val = max_val - min_val

        # Hozo et al. (2005) approximation based on sample size
        if n <= 15:
            divisor = 4.0
        elif n <= 70:
            divisor = 4.5
        elif n <= 200:
            divisor = 5.0
        else:
            divisor = 6.0

        sd = range_val / divisor

        return ConversionResult(
            original_type=DispersionType.RANGE,
            original_lower=min_val,
            original_upper=max_val,
            converted_sd=sd,
            method=ConversionMethod.RANGE_TO_SD,
            assumptions=[
                "Normal distribution assumed",
                f"Using range/{divisor} approximation for n={n}",
                "Based on Hozo et al. (2005) method"
            ],
            confidence=0.50,
            warnings=[
                "Range-to-SD conversion is VERY approximate",
                "High uncertainty - consider obtaining original SD",
                "Recommended: flag for sensitivity analysis"
            ]
        )


class ContinuousOutcomeExtractor:
    """
    Extract continuous outcomes (mean/SD) with strict validation.
    """

    # Common units for continuous outcomes
    UNITS = {
        # Cardiovascular
        'mmHg', 'mm Hg', 'bpm', 'beats/min',
        # Metabolic
        'mg/dL', 'mg/dl', 'mmol/L', 'mmol/l', 'μmol/L',
        '%', 'percent',
        # Renal
        'mL/min', 'ml/min', 'mL/min/1.73m2', 'mL/min/1.73 m²',
        # Body measurements
        'kg', 'lb', 'kg/m2', 'kg/m²', 'cm', 'm', 'mm',
        # Lab values
        'g/dL', 'g/dl', 'U/L', 'IU/L', 'ng/mL', 'pg/mL', 'μg/L',
        # Time
        'days', 'weeks', 'months', 'years',
        # Scores
        'points', 'score', 'units'
    }

    # Patterns for mean (SD) format
    PATTERNS_MEAN_SD = [
        # mean (SD) format: "72.3 (12.4)"
        r'(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*\)',
        # mean ± SD format: "72.3 ± 12.4"
        r'(\d+\.?\d*)\s*[±\+]\s*(\d+\.?\d*)',
        # mean (SD=X) format: "72.3 (SD=12.4)" or "72.3 (SD 12.4)"
        r'(\d+\.?\d*)\s*\(\s*SD\s*[=:\s]\s*(\d+\.?\d*)\s*\)',
    ]

    # Patterns for mean (SE) format - ALL support negative values
    PATTERNS_MEAN_SE = [
        # "Change in LDL was -52.3 (SE 2.8)" format
        r'([-+]?\d+\.?\d*)\s*\(\s*SE\s*[=:\s]?\s*(\d+\.?\d*)\s*\)',
        r'([-+]?\d+\.?\d*)\s*\(SE\s+(\d+\.?\d*)\)',
        # With explicit SE= label
        r'([-+]?\d+\.?\d*)\s*\(\s*SE\s*=\s*(\d+\.?\d*)\s*\)',
    ]

    # Patterns for mean (95% CI) format
    PATTERNS_MEAN_CI = [
        r'(\d+\.?\d*)\s*%?\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)\s*\)',
        r'(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*(?:to|[-–—,])\s*(\d+\.?\d*)\s*\]',
    ]

    # Patterns for median (IQR) format
    PATTERNS_MEDIAN_IQR = [
        # Explicit IQR: "45.3 (IQR 38.1-52.7)"
        r'(\d+\.?\d*)\s*\(\s*IQR[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # Without IQR label: "523 (312-891)"
        r'(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
        # Square brackets
        r'(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*\]',
    ]

    def __init__(self):
        self.converter = DispersionConverter()

    def extract(self, text: str, arm_name: str = "unknown",
                n: Optional[int] = None) -> ContinuousExtractionReport:
        """
        Extract continuous outcomes from text.

        Args:
            text: Source text to parse
            arm_name: Name of the treatment arm
            n: Sample size (required for conversions)

        Returns:
            ContinuousExtractionReport with outcomes and validation
        """
        report = ContinuousExtractionReport()
        text = self._normalize_text(text)

        # Try different patterns
        outcomes = []

        # 1. Try mean (SD) patterns
        for pattern in self.PATTERNS_MEAN_SD:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                outcome = self._parse_mean_sd(match, text, arm_name, n)
                if outcome:
                    outcomes.append(outcome)

        # 2. Try mean (SE) patterns - needs conversion
        for pattern in self.PATTERNS_MEAN_SE:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                outcome = self._parse_mean_se(match, text, arm_name, n)
                if outcome:
                    outcomes.append(outcome)

        # 3. Try mean (CI) patterns - needs conversion
        for pattern in self.PATTERNS_MEAN_CI:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                outcome = self._parse_mean_ci(match, text, arm_name, n)
                if outcome:
                    outcomes.append(outcome)

        # 4. Try median (IQR) patterns - flag for manual review
        for pattern in self.PATTERNS_MEDIAN_IQR:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                outcome = self._parse_median_iqr(match, text, arm_name, n)
                if outcome:
                    outcomes.append(outcome)
                    report.requires_manual_review = True
                    report.review_reasons.append(
                        "Median/IQR detected - consider if conversion is appropriate"
                    )

        # Deduplicate and validate
        outcomes = self._deduplicate(outcomes)
        for outcome in outcomes:
            self._validate_outcome(outcome, n)

        report.outcomes = outcomes

        # Check consistency
        if len(outcomes) >= 2:
            self._check_consistency(report)

        return report

    def _normalize_text(self, text: str) -> str:
        """Normalize unicode and special characters"""
        replacements = {
            '±': '±',
            '\u00b1': '±',
            '\u2013': '-',
            '\u2014': '-',
            '\u2212': '-',
            '–': '-',
            '—': '-',
            '\xb7': '.',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _parse_mean_sd(self, match: re.Match, text: str,
                       arm_name: str, n: Optional[int]) -> Optional[ContinuousOutcome]:
        """Parse mean (SD) format"""
        try:
            mean = float(match.group(1))
            sd = float(match.group(2))

            # Detect unit
            unit = self._detect_unit(text, match.end())

            return ContinuousOutcome(
                arm_name=arm_name,
                n=n or 0,
                mean=mean,
                dispersion_value=sd,
                dispersion_type=DispersionType.SD,
                sd=sd,
                unit=unit,
                source_text=match.group(0),
                pattern_matched="mean_sd"
            )
        except (ValueError, IndexError):
            return None

    def _parse_mean_se(self, match: re.Match, text: str,
                       arm_name: str, n: Optional[int]) -> Optional[ContinuousOutcome]:
        """Parse mean (SE) format with conversion"""
        try:
            mean = float(match.group(1))
            se = float(match.group(2))

            # Attempt conversion if n is provided
            conversion = None
            sd = None

            if n and n > 0:
                conversion = self.converter.se_to_sd(se, n)
                sd = conversion.converted_sd
            else:
                conversion = ConversionResult(
                    original_type=DispersionType.SE,
                    original_lower=se,
                    original_upper=None,
                    converted_sd=None,
                    method=ConversionMethod.MANUAL_REQUIRED,
                    warnings=["Sample size (n) required for SE-to-SD conversion"]
                )

            unit = self._detect_unit(text, match.end())

            return ContinuousOutcome(
                arm_name=arm_name,
                n=n or 0,
                mean=mean,
                dispersion_value=se,
                dispersion_type=DispersionType.SE,
                sd=sd,
                conversion=conversion,
                unit=unit,
                source_text=match.group(0),
                pattern_matched="mean_se"
            )
        except (ValueError, IndexError):
            return None

    def _parse_mean_ci(self, match: re.Match, text: str,
                       arm_name: str, n: Optional[int]) -> Optional[ContinuousOutcome]:
        """Parse mean (95% CI) format with conversion"""
        try:
            mean = float(match.group(1))
            ci_lower = float(match.group(2))
            ci_upper = float(match.group(3))

            # Attempt conversion if n is provided
            conversion = None
            sd = None

            if n and n > 0:
                conversion = self.converter.ci_to_sd(ci_lower, ci_upper, n)
                sd = conversion.converted_sd
            else:
                conversion = ConversionResult(
                    original_type=DispersionType.CI_95,
                    original_lower=ci_lower,
                    original_upper=ci_upper,
                    converted_sd=None,
                    method=ConversionMethod.MANUAL_REQUIRED,
                    warnings=["Sample size (n) required for CI-to-SD conversion"]
                )

            # Store CI midpoint as dispersion value
            ci_width = ci_upper - ci_lower

            unit = self._detect_unit(text, match.end())

            return ContinuousOutcome(
                arm_name=arm_name,
                n=n or 0,
                mean=mean,
                dispersion_value=ci_width / 2,  # Half-width
                dispersion_type=DispersionType.CI_95,
                sd=sd,
                conversion=conversion,
                unit=unit,
                source_text=match.group(0),
                pattern_matched="mean_ci"
            )
        except (ValueError, IndexError):
            return None

    def _parse_median_iqr(self, match: re.Match, text: str,
                          arm_name: str, n: Optional[int]) -> Optional[ContinuousOutcome]:
        """Parse median (IQR) format - flags for manual review"""
        try:
            median = float(match.group(1))
            q1 = float(match.group(2))
            q3 = float(match.group(3))

            # IQR conversion is risky - flag for manual review
            conversion = ConversionResult(
                original_type=DispersionType.IQR,
                original_lower=q1,
                original_upper=q3,
                converted_sd=None,
                method=ConversionMethod.MANUAL_REQUIRED,
                warnings=[
                    "Median/IQR detected - data may be skewed",
                    "IQR-to-SD conversion not recommended without distribution assessment",
                    "Consider: use median/IQR directly or request raw data"
                ]
            )

            unit = self._detect_unit(text, match.end())

            outcome = ContinuousOutcome(
                arm_name=arm_name,
                n=n or 0,
                mean=median,  # Note: this is actually median
                dispersion_value=q3 - q1,  # IQR
                dispersion_type=DispersionType.IQR,
                sd=None,
                conversion=conversion,
                unit=unit,
                source_text=match.group(0),
                pattern_matched="median_iqr"
            )
            outcome.validation_warnings.append(
                "This is MEDIAN (IQR), not mean (SD)"
            )

            return outcome
        except (ValueError, IndexError):
            return None

    def _detect_unit(self, text: str, start_pos: int) -> Optional[str]:
        """Detect unit after the numeric value"""
        # Look at the next 20 characters
        following_text = text[start_pos:start_pos + 30]

        for unit in sorted(self.UNITS, key=len, reverse=True):
            if re.search(r'\b' + re.escape(unit) + r'\b', following_text, re.IGNORECASE):
                return unit

        return None

    def _validate_outcome(self, outcome: ContinuousOutcome,
                          expected_n: Optional[int]) -> None:
        """Validate a single outcome"""
        errors = []
        warnings = []

        # 1. Check mean is reasonable
        if outcome.mean < 0 and outcome.unit not in ['%', 'score', 'points']:
            warnings.append(f"Negative mean ({outcome.mean}) - verify if correct")

        # 2. Check SD is positive
        if outcome.sd is not None and outcome.sd <= 0:
            errors.append(f"SD must be positive, got {outcome.sd}")

        # 3. Check SD vs mean ratio (coefficient of variation)
        if outcome.sd is not None and outcome.mean != 0:
            cv = outcome.sd / abs(outcome.mean)
            if cv > 2.0:
                warnings.append(
                    f"High CV ({cv:.2f}) - SD larger than 2x mean - verify data"
                )

        # 4. Check n consistency
        if expected_n is not None and outcome.n > 0:
            if outcome.n != expected_n:
                warnings.append(
                    f"N mismatch: expected {expected_n}, extracted {outcome.n}"
                )

        # 5. Check conversion assumptions
        if outcome.conversion:
            if outcome.conversion.method == ConversionMethod.MANUAL_REQUIRED:
                errors.append("Conversion to SD requires manual intervention")
            elif outcome.conversion.warnings:
                warnings.extend(outcome.conversion.warnings)

        outcome.validation_errors.extend(errors)
        outcome.validation_warnings.extend(warnings)
        outcome.validation_passed = len(errors) == 0

    def _deduplicate(self, outcomes: List[ContinuousOutcome]) -> List[ContinuousOutcome]:
        """Remove duplicate extractions"""
        seen = set()
        unique = []

        for outcome in outcomes:
            key = (outcome.mean, outcome.dispersion_value, outcome.dispersion_type)
            if key not in seen:
                seen.add(key)
                unique.append(outcome)

        return unique

    def _check_consistency(self, report: ContinuousExtractionReport) -> None:
        """Check consistency across multiple outcomes"""
        # Check unit consistency
        units = [o.unit for o in report.outcomes if o.unit]
        if len(set(units)) > 1:
            report.unit_consistency_check = False
            report.review_reasons.append(
                f"Multiple units detected: {set(units)}"
            )

        # Check N consistency
        ns = [o.n for o in report.outcomes if o.n > 0]
        if len(set(ns)) > 1:
            # Different N values - might be OK for different arms
            pass

        # Calculate mean difference if we have 2 arms
        if len(report.outcomes) == 2:
            o1, o2 = report.outcomes
            if o1.sd is not None and o2.sd is not None:
                report.mean_difference = o1.mean - o2.mean

                # Calculate pooled SD
                if o1.n > 0 and o2.n > 0:
                    pooled_var = ((o1.n - 1) * o1.sd**2 + (o2.n - 1) * o2.sd**2) / \
                                 (o1.n + o2.n - 2)
                    report.pooled_sd = math.sqrt(pooled_var)

                    # Calculate Cohen's d
                    if report.pooled_sd > 0:
                        report.effect_size_d = report.mean_difference / report.pooled_sd


# Convenience function for testing
def extract_continuous(text: str, arm_name: str = "unknown",
                       n: Optional[int] = None) -> ContinuousExtractionReport:
    """Extract continuous outcomes from text"""
    extractor = ContinuousOutcomeExtractor()
    return extractor.extract(text, arm_name, n)


if __name__ == "__main__":
    # Test examples
    test_cases = [
        ("Mean blood pressure was 120.5 (15.2) mmHg", 100),
        ("SBP: 135.2 ± 18.4 mm Hg in the treatment group", 50),
        ("LDL-C was 82.3 (SE 2.4) mg/dL", 200),
        ("HbA1c 7.2% (95% CI 6.8 to 7.6)", 150),
        ("Median eGFR 45.3 (IQR 38.1-52.7) mL/min/1.73m2", 80),
    ]

    extractor = ContinuousOutcomeExtractor()

    for text, n in test_cases:
        print(f"\nInput: {text}")
        print(f"N: {n}")

        report = extractor.extract(text, "treatment", n)

        for outcome in report.outcomes:
            print(f"  Mean: {outcome.mean}")
            print(f"  Dispersion: {outcome.dispersion_value} ({outcome.dispersion_type.value})")
            print(f"  SD: {outcome.sd}")
            print(f"  Unit: {outcome.unit}")
            if outcome.conversion:
                print(f"  Conversion: {outcome.conversion.method.value}")
                if outcome.conversion.warnings:
                    print(f"  Warnings: {outcome.conversion.warnings}")
            if outcome.validation_errors:
                print(f"  ERRORS: {outcome.validation_errors}")
            if outcome.validation_warnings:
                print(f"  Warnings: {outcome.validation_warnings}")
