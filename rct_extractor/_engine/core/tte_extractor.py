"""
Time-to-Event (HR) Extractor with Validation
=============================================

Implements robust HR extraction with:
- CI consistency checks (lower < HR < upper, all > 0)
- Timepoint capture (landmark vs overall)
- Log-rank p-value extraction
- Multiple analyses detection and ambiguity flags
- Follow-up duration capture
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any
from enum import Enum
import math


class AnalysisType(Enum):
    """Type of survival analysis"""
    OVERALL = "overall"           # Overall/final analysis
    LANDMARK = "landmark"         # Landmark analysis at specific timepoint
    INTERIM = "interim"           # Interim analysis
    SUBGROUP = "subgroup"         # Subgroup analysis
    SENSITIVITY = "sensitivity"   # Sensitivity analysis
    PER_PROTOCOL = "per_protocol"  # Per-protocol population
    ITT = "itt"                   # Intention-to-treat
    MODIFIED_ITT = "mitt"         # Modified ITT
    UNKNOWN = "unknown"


class EndpointCategory(Enum):
    """Category of time-to-event endpoint"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    COMPOSITE = "composite"
    SAFETY = "safety"
    EXPLORATORY = "exploratory"
    UNKNOWN = "unknown"


@dataclass
class TimeToEventOutcome:
    """A time-to-event outcome extraction"""
    # Core values
    hr: float
    ci_lower: float
    ci_upper: float

    # Optional values
    p_value: Optional[float] = None
    log_rank_p: Optional[float] = None

    # Timepoint information
    timepoint: Optional[str] = None  # e.g., "12 months", "median 3.5 years"
    timepoint_type: AnalysisType = AnalysisType.UNKNOWN
    follow_up_duration: Optional[str] = None

    # Endpoint information
    endpoint_name: Optional[str] = None
    endpoint_category: EndpointCategory = EndpointCategory.UNKNOWN
    composite_components: List[str] = field(default_factory=list)

    # Events (if reported)
    events_treatment: Optional[int] = None
    events_control: Optional[int] = None
    n_treatment: Optional[int] = None
    n_control: Optional[int] = None

    # Provenance
    source_text: str = ""
    source_context: str = ""  # Surrounding text for disambiguation
    pre_context: str = ""     # Text immediately BEFORE the HR (for timepoint detection)
    pattern_matched: str = ""

    # Validation
    validation_passed: bool = True
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)

    # Ambiguity flags
    is_ambiguous: bool = False
    ambiguity_reasons: List[str] = field(default_factory=list)


@dataclass
class TTEExtractionReport:
    """Full extraction report for time-to-event outcomes"""
    outcomes: List[TimeToEventOutcome] = field(default_factory=list)

    # Multiple analyses detection
    multiple_timepoints_detected: bool = False
    multiple_populations_detected: bool = False
    primary_analysis_identified: bool = False

    # Trial-level information
    trial_name: Optional[str] = None
    publication_count: int = 1  # >1 suggests multiple publications

    # Review flags
    requires_manual_review: bool = False
    review_reasons: List[str] = field(default_factory=list)


class HRValidator:
    """Validates HR and CI consistency"""

    @staticmethod
    def validate_ci_contains_hr(hr: float, ci_lower: float, ci_upper: float) -> Tuple[bool, str]:
        """Check if CI contains the HR point estimate"""
        if ci_lower <= hr <= ci_upper:
            return True, ""
        else:
            return False, f"CI [{ci_lower}, {ci_upper}] does not contain HR {hr}"

    @staticmethod
    def validate_ci_order(ci_lower: float, ci_upper: float) -> Tuple[bool, str]:
        """Check if lower < upper"""
        if ci_lower < ci_upper:
            return True, ""
        else:
            return False, f"CI lower ({ci_lower}) >= upper ({ci_upper})"

    @staticmethod
    def validate_positive_values(hr: float, ci_lower: float, ci_upper: float) -> Tuple[bool, str]:
        """Check if all values are positive"""
        if hr > 0 and ci_lower > 0 and ci_upper > 0:
            return True, ""
        else:
            negatives = []
            if hr <= 0:
                negatives.append(f"HR={hr}")
            if ci_lower <= 0:
                negatives.append(f"CI_lower={ci_lower}")
            if ci_upper <= 0:
                negatives.append(f"CI_upper={ci_upper}")
            return False, f"Non-positive values: {', '.join(negatives)}"

    @staticmethod
    def validate_plausibility(hr: float, ci_lower: float, ci_upper: float) -> Tuple[bool, List[str]]:
        """Check if values are plausible for clinical trials"""
        warnings = []

        # HR typically between 0.1 and 10 in clinical trials
        if hr < 0.05 or hr > 20:
            warnings.append(f"Extreme HR value ({hr}) - verify if correct")

        # CI width check
        ci_ratio = ci_upper / ci_lower if ci_lower > 0 else float('inf')
        if ci_ratio > 10:
            warnings.append(f"Very wide CI (ratio {ci_ratio:.1f}) - may indicate small sample/events")

        # Very narrow CI might indicate reporting error
        if ci_ratio < 1.05:
            warnings.append(f"Suspiciously narrow CI (ratio {ci_ratio:.3f}) - verify data")

        return len(warnings) == 0, warnings

    @staticmethod
    def validate_consistency_with_p(hr: float, ci_lower: float, ci_upper: float,
                                     p_value: Optional[float]) -> Tuple[bool, List[str]]:
        """Check consistency between CI and p-value"""
        warnings = []

        if p_value is not None:
            # If p < 0.05, CI should not cross 1.0
            if p_value < 0.05 and ci_lower < 1.0 < ci_upper:
                warnings.append(
                    f"Inconsistency: p={p_value} suggests significance but CI [{ci_lower}, {ci_upper}] crosses 1.0"
                )

            # If p >= 0.05, CI should cross 1.0 (for 95% CI)
            if p_value >= 0.05 and not (ci_lower < 1.0 < ci_upper):
                if hr != 1.0:  # Unless HR is exactly 1.0
                    warnings.append(
                        f"Possible inconsistency: p={p_value} but CI [{ci_lower}, {ci_upper}] does not cross 1.0"
                    )

        return len(warnings) == 0, warnings


class TimeToEventExtractor:
    """
    Extract time-to-event outcomes with full validation and ambiguity detection.
    """

    # Analysis type keywords (patterns should be regex-safe)
    ANALYSIS_KEYWORDS = {
        AnalysisType.OVERALL: ['overall', 'final', 'primary analysis', 'full cohort', 'overall hr'],
        AnalysisType.LANDMARK: ['landmark', r'\d+.month landmark', r'\d+.year landmark'],
        AnalysisType.INTERIM: ['interim', 'planned analysis', 'futility'],
        AnalysisType.SUBGROUP: ['subgroup', 'subset', r'aged?\s*[≥<>\d]', 'by age', 'by sex', 'by region', r'years,?\s+hr'],
        AnalysisType.SENSITIVITY: ['sensitivity', 'as-treated'],
        AnalysisType.PER_PROTOCOL: ['per.protocol', 'per protocol', 'pp population'],
        AnalysisType.ITT: ['intention.to.treat', 'itt population', 'full analysis'],
        AnalysisType.MODIFIED_ITT: ['modified.itt', 'mitt'],
    }

    # Endpoint category keywords
    ENDPOINT_KEYWORDS = {
        EndpointCategory.PRIMARY: ['primary', 'main outcome', 'principal'],
        EndpointCategory.SECONDARY: ['secondary', 'key secondary'],
        EndpointCategory.COMPOSITE: ['composite', 'combined endpoint', 'MACE'],
        EndpointCategory.SAFETY: ['safety', 'adverse', 'serious adverse'],
        EndpointCategory.EXPLORATORY: ['exploratory', 'post.hoc', 'hypothesis.generating'],
    }

    # Composite endpoint component keywords
    COMPOSITE_COMPONENTS = [
        'death', 'mortality', 'MI', 'myocardial infarction', 'stroke',
        'hospitalization', 'heart failure', 'cardiovascular death',
        'revascularization', 'urgent revascularization',
        'stent thrombosis', 'all-cause death', 'CV death'
    ]

    def __init__(self):
        self.validator = HRValidator()

        # HR extraction patterns (from v7 + fixes for "was" format)
        self.hr_patterns = [
            # "hazard ratio for X was" format
            r'hazard\s*ratio\s+for\s+[^(]+?\s+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|confidence\s*interval)[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

            # "hazard ratio of X" format
            r'hazard\s*ratio\s+of\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

            # "hazard ratio was X" format (simple was)
            r'hazard\s*ratio\s+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

            # "the overall HR was X" format
            r'(?:the\s+)?(?:overall\s+)?HR\s+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

            # HR with comma after CI
            r'\bHR\b\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

            # Standard patterns
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',

            # NEJM format
            r'hazard\s*ratio[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*to\s*(\d+\.?\d*)',

            # With p-value capture
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*[\)\]]\s*[,;]?\s*[Pp]\s*[=<]\s*(\d+\.?\d*)',
        ]

        # P-value patterns
        self.p_value_patterns = [
            r'[Pp]\s*[=<]\s*(\d+\.?\d*)',
            r'[Pp]\s*value[:\s]*[=<]?\s*(\d+\.?\d*)',
            r'log.rank\s*[Pp][:\s]*[=<]?\s*(\d+\.?\d*)',
        ]

        # Timepoint patterns
        self.timepoint_patterns = [
            r'at\s+(\d+)\s*(months?|years?|weeks?)',
            r'(\d+)[-.](months?|years?)\s+follow.?up',
            r'median\s+follow.?up\s+(?:of\s+)?(\d+\.?\d*)\s*(months?|years?)',
            r'(\d+)[-.](year|month)\s+landmark',
            # "12-month" or "24 months"
            r'(\d+)[-.](month|year)s?',
            # "follow-up of 3.5 years"
            r'follow.?up\s+(?:of\s+)?(\d+\.?\d*)\s*(months?|years?)',
        ]

    def extract(self, text: str, context: str = "") -> TTEExtractionReport:
        """
        Extract time-to-event outcomes from text.

        Args:
            text: Source text to parse
            context: Additional context (e.g., surrounding paragraphs)

        Returns:
            TTEExtractionReport with outcomes and validation
        """
        report = TTEExtractionReport()
        text = self._normalize_text(text)
        full_context = text + " " + context

        outcomes = []

        # Extract HRs
        for pattern in self.hr_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                outcome = self._parse_hr_match(match, text, full_context)
                if outcome:
                    # Validate
                    self._validate_outcome(outcome)

                    # Detect analysis type and timepoint
                    self._detect_analysis_type(outcome, full_context)
                    self._detect_endpoint_category(outcome, full_context)
                    self._detect_timepoint(outcome, full_context)

                    outcomes.append(outcome)

        # Deduplicate
        outcomes = self._deduplicate(outcomes)

        # Detect ambiguity
        self._detect_ambiguity(outcomes, report, full_context)

        report.outcomes = outcomes

        return report

    def _normalize_text(self, text: str) -> str:
        """Normalize unicode and special characters"""
        replacements = {
            '\u00b7': '.',
            '\u2013': '-',
            '\u2014': '-',
            '\u2212': '-',
            '–': '-',
            '—': '-',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        # European decimal format
        text = re.sub(r'(\d),(\d)', r'\1.\2', text)

        return text

    def _parse_hr_match(self, match: re.Match, text: str,
                        context: str) -> Optional[TimeToEventOutcome]:
        """Parse a regex match for HR"""
        try:
            hr = float(match.group(1))
            ci_lower = float(match.group(2))
            ci_upper = float(match.group(3))

            # Try to get p-value from match groups or surrounding text
            p_value = None
            if len(match.groups()) >= 4:
                try:
                    p_value = float(match.group(4))
                except (ValueError, IndexError):
                    pass

            if p_value is None:
                p_value = self._extract_p_value(text, match.end())

            # Get surrounding context for this extraction
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            source_context = text[start:end]

            # Get text BEFORE this HR match (for timepoint detection)
            pre_start = max(0, match.start() - 60)
            pre_context = text[pre_start:match.start()]

            return TimeToEventOutcome(
                hr=hr,
                ci_lower=ci_lower,
                ci_upper=ci_upper,
                p_value=p_value,
                source_text=match.group(0),
                source_context=source_context,
                pre_context=pre_context,
                pattern_matched=match.re.pattern[:50]
            )

        except (ValueError, IndexError):
            return None

    def _extract_p_value(self, text: str, start_pos: int) -> Optional[float]:
        """Extract p-value near the HR"""
        # Look in the next 50 characters
        following_text = text[start_pos:start_pos + 50]

        for pattern in self.p_value_patterns:
            match = re.search(pattern, following_text, re.IGNORECASE)
            if match:
                try:
                    p_str = match.group(1)
                    # Handle "P < 0.001" as 0.001
                    return float(p_str)
                except ValueError:
                    pass

        return None

    def _validate_outcome(self, outcome: TimeToEventOutcome) -> None:
        """Run all validation checks on an outcome"""
        errors = []
        warnings = []

        # 1. CI contains HR
        valid, msg = self.validator.validate_ci_contains_hr(
            outcome.hr, outcome.ci_lower, outcome.ci_upper
        )
        if not valid:
            errors.append(msg)

        # 2. CI order
        valid, msg = self.validator.validate_ci_order(
            outcome.ci_lower, outcome.ci_upper
        )
        if not valid:
            errors.append(msg)

        # 3. Positive values
        valid, msg = self.validator.validate_positive_values(
            outcome.hr, outcome.ci_lower, outcome.ci_upper
        )
        if not valid:
            errors.append(msg)

        # 4. Plausibility
        valid, plausibility_warnings = self.validator.validate_plausibility(
            outcome.hr, outcome.ci_lower, outcome.ci_upper
        )
        warnings.extend(plausibility_warnings)

        # 5. P-value consistency
        valid, p_warnings = self.validator.validate_consistency_with_p(
            outcome.hr, outcome.ci_lower, outcome.ci_upper, outcome.p_value
        )
        warnings.extend(p_warnings)

        outcome.validation_errors = errors
        outcome.validation_warnings = warnings
        outcome.validation_passed = len(errors) == 0

    def _detect_analysis_type(self, outcome: TimeToEventOutcome,
                               context: str) -> None:
        """Detect the type of analysis"""
        context_lower = context.lower()

        # First check for landmark (more specific)
        if 'landmark' in context_lower:
            outcome.timepoint_type = AnalysisType.LANDMARK
            return

        # Then check other types
        for analysis_type, keywords in self.ANALYSIS_KEYWORDS.items():
            for keyword in keywords:
                try:
                    if re.search(keyword, context_lower, re.IGNORECASE):
                        outcome.timepoint_type = analysis_type
                        return
                except re.error:
                    # If regex fails, try literal match
                    if keyword in context_lower:
                        outcome.timepoint_type = analysis_type
                        return

        outcome.timepoint_type = AnalysisType.UNKNOWN

    def _detect_endpoint_category(self, outcome: TimeToEventOutcome,
                                   context: str) -> None:
        """Detect the endpoint category"""
        context_lower = context.lower()

        # First check for MACE explicitly
        if 'mace' in context_lower:
            outcome.endpoint_category = EndpointCategory.COMPOSITE

        for category, keywords in self.ENDPOINT_KEYWORDS.items():
            for keyword in keywords:
                try:
                    if re.search(keyword, context_lower):
                        outcome.endpoint_category = category
                        break
                except re.error:
                    if keyword in context_lower:
                        outcome.endpoint_category = category
                        break

        # Detect composite components
        for component in self.COMPOSITE_COMPONENTS:
            if component.lower() in context_lower:
                if component not in outcome.composite_components:
                    outcome.composite_components.append(component)

        # Also check for component patterns like "CV death, MI, or stroke"
        component_pattern = r'(cv death|mi|stroke|myocardial infarction|death|hospitalization)'
        matches = re.findall(component_pattern, context_lower)
        for match in matches:
            # Normalize component names
            normalized = match.upper() if len(match) <= 3 else match.title()
            if normalized not in outcome.composite_components:
                outcome.composite_components.append(normalized)

        if len(outcome.composite_components) >= 2:
            outcome.endpoint_category = EndpointCategory.COMPOSITE

    def _detect_timepoint(self, outcome: TimeToEventOutcome,
                          context: str) -> None:
        """Detect timepoint and follow-up duration"""
        # First, look for timepoint in the pre_context (text immediately before the HR)
        # This is the most accurate for associating timepoints with specific HRs
        pre_context = outcome.pre_context if outcome.pre_context else ""

        for pattern in self.timepoint_patterns:
            match = re.search(pattern, pre_context, re.IGNORECASE)
            if match:
                try:
                    value = match.group(1)
                    unit = match.group(2)
                    outcome.timepoint = f"{value} {unit}"

                    # Check if this is a landmark analysis
                    if 'landmark' in pre_context.lower():
                        outcome.timepoint_type = AnalysisType.LANDMARK

                    return  # Found in pre_context, done
                except IndexError:
                    pass

        # Fallback: use source_context (surrounding text)
        local_context = outcome.source_context if outcome.source_context else context

        for pattern in self.timepoint_patterns:
            match = re.search(pattern, local_context, re.IGNORECASE)
            if match:
                try:
                    value = match.group(1)
                    unit = match.group(2)
                    outcome.timepoint = f"{value} {unit}"

                    if 'landmark' in local_context.lower():
                        outcome.timepoint_type = AnalysisType.LANDMARK

                    return
                except IndexError:
                    pass

        # Final fallback: full context
        if local_context != context:
            for pattern in self.timepoint_patterns:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    try:
                        value = match.group(1)
                        unit = match.group(2)
                        outcome.timepoint = f"{value} {unit}"
                        break
                    except IndexError:
                        pass

    def _deduplicate(self, outcomes: List[TimeToEventOutcome]) -> List[TimeToEventOutcome]:
        """Remove duplicate extractions"""
        seen = set()
        unique = []

        for outcome in outcomes:
            # Use HR and CI as the key
            key = (round(outcome.hr, 3),
                   round(outcome.ci_lower, 3),
                   round(outcome.ci_upper, 3))

            if key not in seen:
                seen.add(key)
                unique.append(outcome)

        return unique

    def _detect_ambiguity(self, outcomes: List[TimeToEventOutcome],
                          report: TTEExtractionReport,
                          context: str) -> None:
        """Detect sources of ambiguity"""

        # 1. Multiple timepoints detected
        timepoints = set()
        for o in outcomes:
            if o.timepoint:
                timepoints.add(o.timepoint)

        if len(timepoints) > 1:
            report.multiple_timepoints_detected = True
            report.requires_manual_review = True
            report.review_reasons.append(
                f"Multiple timepoints detected: {timepoints}"
            )

            for o in outcomes:
                o.is_ambiguous = True
                o.ambiguity_reasons.append("Multiple timepoints reported")

        # 2. Multiple analysis populations
        populations = set()
        for o in outcomes:
            if o.timepoint_type != AnalysisType.UNKNOWN:
                populations.add(o.timepoint_type)

        if len(populations) > 1:
            report.multiple_populations_detected = True
            report.requires_manual_review = True
            report.review_reasons.append(
                f"Multiple analysis populations: {[p.value for p in populations]}"
            )

        # 3. Check for "primary" designation
        primary_found = False
        for o in outcomes:
            if o.endpoint_category == EndpointCategory.PRIMARY:
                primary_found = True
                break

        report.primary_analysis_identified = primary_found

        if not primary_found and len(outcomes) > 1:
            report.requires_manual_review = True
            report.review_reasons.append(
                "Multiple outcomes but no clear 'primary' designation"
            )

        # 4. Check for composite endpoint ambiguity
        for o in outcomes:
            if len(o.composite_components) >= 2:
                # MACE variants differ - flag for review
                if 'MACE' in context.upper():
                    o.is_ambiguous = True
                    o.ambiguity_reasons.append(
                        f"Composite endpoint with components: {o.composite_components}. "
                        "MACE definitions vary - verify exact definition."
                    )

        # 5. Detect multiple publications hint
        publication_hints = [
            'previously reported', 'initial publication', 'primary publication',
            'extended follow-up', 'long-term results', 'updated analysis'
        ]
        for hint in publication_hints:
            if hint in context.lower():
                report.publication_count += 1
                report.requires_manual_review = True
                report.review_reasons.append(
                    f"Multiple publications likely: '{hint}' detected"
                )
                break


# Convenience function
def extract_tte(text: str, context: str = "") -> TTEExtractionReport:
    """Extract time-to-event outcomes from text"""
    extractor = TimeToEventExtractor()
    return extractor.extract(text, context)


if __name__ == "__main__":
    # Test examples
    test_cases = [
        # Standard case
        "The hazard ratio for the primary composite endpoint was 0.72 (95% CI, 0.63 to 0.82; P<0.001)",

        # Multiple timepoints
        """At 12 months, the HR was 0.68 (95% CI 0.55-0.84).
           At 24 months, the HR was 0.75 (95% CI 0.62-0.91).
           The overall HR was 0.72 (95% CI 0.63-0.82).""",

        # Invalid CI
        "HR 0.85 (95% CI 0.90-0.75)",

        # MACE composite
        "For the primary endpoint of MACE (CV death, MI, or stroke), HR was 0.80 (95% CI 0.70-0.92)",

        # Landmark analysis
        "In the 12-month landmark analysis, the hazard ratio was 0.65 (95% CI 0.50-0.85)",

        # Subgroup
        "In the subgroup aged ≥65 years, HR was 0.78 (95% CI 0.64-0.95)",
    ]

    extractor = TimeToEventExtractor()

    for text in test_cases:
        print("\n" + "=" * 60)
        print(f"Input: {text[:80]}...")

        report = extractor.extract(text)

        for i, outcome in enumerate(report.outcomes):
            print(f"\n  Outcome {i + 1}:")
            print(f"    HR: {outcome.hr} ({outcome.ci_lower}-{outcome.ci_upper})")
            print(f"    P-value: {outcome.p_value}")
            print(f"    Analysis: {outcome.timepoint_type.value}")
            print(f"    Endpoint: {outcome.endpoint_category.value}")
            print(f"    Timepoint: {outcome.timepoint}")
            print(f"    Valid: {outcome.validation_passed}")

            if outcome.validation_errors:
                print(f"    ERRORS: {outcome.validation_errors}")
            if outcome.validation_warnings:
                print(f"    Warnings: {outcome.validation_warnings}")
            if outcome.is_ambiguous:
                print(f"    AMBIGUOUS: {outcome.ambiguity_reasons}")
            if outcome.composite_components:
                print(f"    Components: {outcome.composite_components}")

        if report.requires_manual_review:
            print(f"\n  REQUIRES REVIEW: {report.review_reasons}")
