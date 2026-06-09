"""
Provenance Metadata Extractor for RCT Extractor v2.16
======================================================

Extracts contextual metadata for each effect estimate:
1. Source location (character offset, context)
2. Comparison arm labels (treatment vs control)
3. Analysis population (ITT, mITT, per-protocol)
4. Timepoint extraction
5. Subgroup flagging
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum


class AnalysisPopulation(Enum):
    """Analysis population types"""
    ITT = "intention-to-treat"
    MITT = "modified intention-to-treat"
    PER_PROTOCOL = "per-protocol"
    SAFETY = "safety population"
    UNKNOWN = "unknown"


class EndpointType(Enum):
    """Endpoint classification"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EXPLORATORY = "exploratory"
    SAFETY = "safety"
    SUBGROUP = "subgroup"
    UNKNOWN = "unknown"


@dataclass
class SourceLocation:
    """Location of extraction in source text"""
    char_start: int
    char_end: int
    line_number: Optional[int] = None
    context_before: str = ""  # 100 chars before
    context_after: str = ""   # 100 chars after
    matched_text: str = ""    # Exact matched text


@dataclass
class ComparisonArms:
    """Treatment comparison details"""
    treatment_arm: str
    control_arm: str
    treatment_n: Optional[int] = None
    control_n: Optional[int] = None
    comparison_type: str = "parallel"  # parallel, crossover, etc.


@dataclass
class Timepoint:
    """Timepoint information"""
    value: Optional[float] = None
    unit: str = ""  # weeks, months, years
    description: str = ""
    is_primary: bool = False
    is_interim: bool = False
    is_final: bool = False


@dataclass
class ProvenanceMetadata:
    """Complete provenance metadata for an extraction"""
    source_location: SourceLocation
    comparison_arms: Optional[ComparisonArms] = None
    analysis_population: AnalysisPopulation = AnalysisPopulation.UNKNOWN
    timepoint: Optional[Timepoint] = None
    endpoint_type: EndpointType = EndpointType.UNKNOWN
    outcome_description: str = ""
    is_subgroup: bool = False
    subgroup_variable: Optional[str] = None
    is_adjusted: bool = False
    adjustment_variables: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class ProvenanceExtractor:
    """
    Extract provenance metadata from clinical trial text.
    """

    # Patterns for treatment arms
    TREATMENT_PATTERNS = [
        # Drug vs placebo
        r"(\w+(?:\s+\d+\s*mg)?)\s+(?:vs\.?|versus|compared\s+(?:to|with))\s+(placebo)",
        # Treatment vs control
        r"(treatment|intervention|active)\s+(?:arm|group)?\s*(?:vs\.?|versus)\s*(control|placebo|standard\s+care)",
        # Specific drug names (common)
        r"(dapagliflozin|empagliflozin|canagliflozin|semaglutide|liraglutide|"
        r"evolocumab|alirocumab|pembrolizumab|nivolumab|atezolizumab|durvalumab|"
        r"rivaroxaban|apixaban|dabigatran|sacubitril.valsartan)\s+"
        r"(?:vs\.?|versus|compared\s+(?:to|with))\s+"
        r"(placebo|warfarin|standard|enalapril|control|chemotherapy|docetaxel|platinum)",
        # Arm 1 vs Arm 2
        r"(arm\s*[A1]|group\s*[A1])\s+(?:vs\.?|versus)\s+(arm\s*[B2]|group\s*[B2]|placebo)",
        # Additional pattern for drug name + compared with
        r"(pembrolizumab|nivolumab|atezolizumab)\s+compared\s+with\s+"
        r"(platinum[\s-]?based\s+chemotherapy|chemotherapy|docetaxel)",
    ]

    # Patterns for analysis population
    # NOTE: Order matters! MITT must be checked BEFORE ITT since "modified ITT" contains "ITT"
    POPULATION_PATTERNS = {
        AnalysisPopulation.MITT: [
            r"\bmodified\s+intention[\s-]?to[\s-]?treat\b",
            r"\bmitt\b",
            r"\bmodified\s+itt\b",
            r"\bm[\s-]?itt\b",
        ],
        AnalysisPopulation.ITT: [
            r"\b(?:intention[\s-]?to[\s-]?treat|itt)\b",
            r"\ball\s+(?:randomized|enrolled)\s+(?:patients|subjects|participants)\b",
            r"\bitt\s+population\b",
            r"\bin\s+the\s+itt\b",
        ],
        AnalysisPopulation.PER_PROTOCOL: [
            r"\bper[\s-]?protocol\b",
            r"\bPP\s+(?:analysis|population)\b",
            r"\bcompleters?\s+(?:analysis|population)\b",
        ],
        AnalysisPopulation.SAFETY: [
            r"\bsafety\s+(?:analysis|population)\b",
            r"\ball\s+treated\s+(?:patients|subjects)\b",
        ],
    }

    # Patterns for timepoints
    TIMEPOINT_PATTERNS = [
        # Numeric timepoints
        r"(?:at|after|through|over)\s+(\d+(?:\.\d+)?)\s*(weeks?|months?|years?|days?)",
        r"(\d+(?:\.\d+)?)\s*[-–]\s*(week|month|year|day)",
        r"(?:median|mean)\s+(?:follow[\s-]?up|duration)(?:\s+(?:of|was))?\s*"
        r"(\d+(?:\.\d+)?)\s*(weeks?|months?|years?)",
        # Descriptive timepoints
        r"(primary|final|end[\s-]?of[\s-]?study)\s+(?:analysis|endpoint|assessment)",
        r"(interim)\s+analysis",
    ]

    # Patterns for subgroups
    SUBGROUP_PATTERNS = [
        r"\bsubgroup\s+(?:analysis|of)\b",
        r"\bamong\s+(?:patients|subjects)\s+(?:with|who)\b",
        r"\bin\s+(?:patients|subjects)\s+(?:with|who)\b",
        r"\bstratified\s+by\b",
        r"\baccording\s+to\b",
        r"\binteraction\s+(?:test|p[\s-]?value)\b",
        r"\bp\s*(?:for|=)\s*interaction\b",
    ]

    # Patterns for adjusted analyses
    ADJUSTMENT_PATTERNS = [
        r"\badjusted\s+(?:for|by|analysis)\b",
        r"\bmultivariable\b",
        r"\bmultivariate\b",
        r"\bCox\s+(?:proportional\s+hazards?|regression|model)\b",
        r"\blogistic\s+regression\b",
        r"\bcontrolling\s+for\b",
    ]

    # Patterns for endpoint type
    ENDPOINT_PATTERNS = {
        EndpointType.PRIMARY: [
            r"\bprimary\s+(?:endpoint|outcome|end[\s-]?point|composite)\b",
            r"\bprimary\s+efficacy\b",
            r"\bco[\s-]?primary\b",
        ],
        EndpointType.SECONDARY: [
            r"\bsecondary\s+(?:endpoint|outcome|end[\s-]?point)\b",
            r"\bkey\s+secondary\b",
        ],
        EndpointType.EXPLORATORY: [
            r"\bexploratory\s+(?:endpoint|outcome|analysis)\b",
            r"\bpost[\s-]?hoc\b",
            r"\bad[\s-]?hoc\b",
        ],
        EndpointType.SAFETY: [
            r"\bsafety\s+(?:endpoint|outcome)\b",
            r"\badverse\s+events?\b",
            r"\bserious\s+adverse\b",
        ],
    }

    def extract_provenance(
        self,
        text: str,
        match_start: int,
        match_end: int
    ) -> ProvenanceMetadata:
        """
        Extract provenance metadata for a specific match location.

        Args:
            text: Full source text
            match_start: Start position of the effect estimate match
            match_end: End position of the effect estimate match

        Returns:
            ProvenanceMetadata with all extracted context
        """
        # Get context window (500 chars before/after)
        context_start = max(0, match_start - 500)
        context_end = min(len(text), match_end + 500)
        context = text[context_start:context_end]

        # Calculate line number
        line_number = text[:match_start].count('\n') + 1

        # Build source location
        source_location = SourceLocation(
            char_start=match_start,
            char_end=match_end,
            line_number=line_number,
            context_before=text[max(0, match_start - 100):match_start],
            context_after=text[match_end:min(len(text), match_end + 100)],
            matched_text=text[match_start:match_end]
        )

        # Extract comparison arms
        comparison_arms = self._extract_comparison_arms(context)

        # Extract analysis population
        analysis_population = self._extract_population(context)

        # Extract timepoint
        timepoint = self._extract_timepoint(context)

        # Determine endpoint type
        endpoint_type = self._extract_endpoint_type(context)

        # Check for subgroup
        is_subgroup, subgroup_var = self._check_subgroup(context)

        # Check for adjusted analysis
        is_adjusted, adjustment_vars = self._check_adjusted(context)

        # Extract outcome description
        outcome_description = self._extract_outcome_description(context)

        return ProvenanceMetadata(
            source_location=source_location,
            comparison_arms=comparison_arms,
            analysis_population=analysis_population,
            timepoint=timepoint,
            endpoint_type=endpoint_type,
            outcome_description=outcome_description,
            is_subgroup=is_subgroup,
            subgroup_variable=subgroup_var,
            is_adjusted=is_adjusted,
            adjustment_variables=adjustment_vars
        )

    def _extract_comparison_arms(self, context: str) -> Optional[ComparisonArms]:
        """Extract treatment vs control comparison"""
        context_lower = context.lower()

        for pattern in self.TREATMENT_PATTERNS:
            match = re.search(pattern, context_lower)
            if match:
                treatment = match.group(1).strip()
                control = match.group(2).strip()

                # Normalize names
                treatment = self._normalize_arm_name(treatment)
                control = self._normalize_arm_name(control)

                # Try to extract sample sizes
                treatment_n = self._extract_arm_n(context, treatment)
                control_n = self._extract_arm_n(context, control)

                return ComparisonArms(
                    treatment_arm=treatment,
                    control_arm=control,
                    treatment_n=treatment_n,
                    control_n=control_n
                )

        return None

    def _normalize_arm_name(self, name: str) -> str:
        """Normalize arm name to standard format"""
        # Common abbreviations
        normalizations = {
            "plac": "placebo",
            "std": "standard care",
            "soc": "standard of care",
            "ctrl": "control",
        }

        name_lower = name.lower().strip()
        for abbrev, full in normalizations.items():
            if abbrev in name_lower:
                return full

        return name.title()

    def _extract_arm_n(self, context: str, arm_name: str) -> Optional[int]:
        """Extract sample size for an arm"""
        patterns = [
            rf"{arm_name}\s*\(?\s*n\s*=\s*(\d+)",
            rf"(\d+)\s+(?:patients?|subjects?)\s+(?:in|on|received?)\s+{arm_name}",
        ]

        for pattern in patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def _extract_population(self, context: str) -> AnalysisPopulation:
        """Extract analysis population type"""
        context_lower = context.lower()

        for population, patterns in self.POPULATION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, context_lower):
                    return population

        return AnalysisPopulation.UNKNOWN

    def _extract_timepoint(self, context: str) -> Optional[Timepoint]:
        """Extract timepoint information"""
        context_lower = context.lower()

        for pattern in self.TIMEPOINT_PATTERNS:
            match = re.search(pattern, context_lower)
            if match:
                groups = match.groups()

                # Handle numeric timepoints
                if len(groups) >= 2:
                    try:
                        value = float(groups[0])
                        unit = groups[1].rstrip('s')  # Remove plural
                        return Timepoint(
                            value=value,
                            unit=unit,
                            description=match.group(0),
                            is_primary="primary" in context_lower or "final" in context_lower,
                            is_interim="interim" in context_lower,
                            is_final="final" in context_lower or "end" in context_lower
                        )
                    except (ValueError, IndexError):
                        pass

                # Handle descriptive timepoints
                if groups:
                    desc = groups[0]
                    return Timepoint(
                        description=desc,
                        is_primary="primary" in desc,
                        is_interim="interim" in desc,
                        is_final="final" in desc or "end" in desc
                    )

        return None

    def _extract_endpoint_type(self, context: str) -> EndpointType:
        """Determine endpoint type from context"""
        context_lower = context.lower()

        for endpoint_type, patterns in self.ENDPOINT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, context_lower):
                    return endpoint_type

        return EndpointType.UNKNOWN

    def _check_subgroup(self, context: str) -> Tuple[bool, Optional[str]]:
        """Check if this is a subgroup analysis"""
        context_lower = context.lower()

        for pattern in self.SUBGROUP_PATTERNS:
            match = re.search(pattern, context_lower)
            if match:
                # Try to extract subgroup variable
                subgroup_var = self._extract_subgroup_variable(context)
                return True, subgroup_var

        return False, None

    def _extract_subgroup_variable(self, context: str) -> Optional[str]:
        """Extract the subgroup variable"""
        patterns = [
            r"(?:stratified|subgroup)\s+(?:by|of)\s+(\w+(?:\s+\w+)?)",
            r"(?:patients|subjects)\s+with\s+(\w+(?:\s+\w+)?)",
            r"(?:age|sex|gender|diabetes|hypertension|history\s+of\s+\w+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                return match.group(1) if match.lastindex else match.group(0)

        return None

    def _check_adjusted(self, context: str) -> Tuple[bool, List[str]]:
        """Check if analysis is adjusted and for what"""
        context_lower = context.lower()
        adjustment_vars = []

        for pattern in self.ADJUSTMENT_PATTERNS:
            if re.search(pattern, context_lower):
                # Try to extract adjustment variables
                var_pattern = r"adjusted\s+for\s+([^.]+)"
                match = re.search(var_pattern, context_lower)
                if match:
                    vars_text = match.group(1)
                    # Split by common delimiters
                    vars_list = re.split(r',\s*|\s+and\s+', vars_text)
                    adjustment_vars = [v.strip() for v in vars_list if v.strip()]

                return True, adjustment_vars

        return False, []

    def _extract_outcome_description(self, context: str) -> str:
        """Extract the outcome description"""
        # Common outcome patterns
        patterns = [
            r"(?:primary|secondary|key)\s+(?:endpoint|outcome)[:\s]+([^.]+)",
            r"(?:hazard|odds|risk)\s+ratio\s+(?:for|of)\s+([^,(]+)",
            r"(?:CV|cardiovascular)\s+death(?:\s+or\s+[^,]+)?",
            r"(?:HF|heart\s+failure)\s+hospitalization",
            r"(?:all-?cause|overall)\s+mortality",
            r"MACE|major\s+adverse\s+cardiovascular\s+events?",
        ]

        for pattern in patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                if match.lastindex:
                    return match.group(1).strip()
                return match.group(0).strip()

        return ""


def format_provenance(metadata: ProvenanceMetadata) -> str:
    """Format provenance metadata as readable string"""
    lines = []

    lines.append("PROVENANCE METADATA")
    lines.append("-" * 40)

    # Source location
    loc = metadata.source_location
    lines.append(f"Location: chars {loc.char_start}-{loc.char_end}, line {loc.line_number}")
    lines.append(f"Matched: '{loc.matched_text[:50]}...'")

    # Comparison arms
    if metadata.comparison_arms:
        arms = metadata.comparison_arms
        lines.append(f"Comparison: {arms.treatment_arm} vs {arms.control_arm}")
        if arms.treatment_n:
            lines.append(f"  Treatment N: {arms.treatment_n}")
        if arms.control_n:
            lines.append(f"  Control N: {arms.control_n}")

    # Analysis population
    lines.append(f"Population: {metadata.analysis_population.value}")

    # Timepoint
    if metadata.timepoint:
        tp = metadata.timepoint
        if tp.value:
            lines.append(f"Timepoint: {tp.value} {tp.unit}")
        elif tp.description:
            lines.append(f"Timepoint: {tp.description}")

    # Endpoint type
    lines.append(f"Endpoint: {metadata.endpoint_type.value}")

    # Outcome
    if metadata.outcome_description:
        lines.append(f"Outcome: {metadata.outcome_description}")

    # Flags
    flags = []
    if metadata.is_subgroup:
        flags.append(f"SUBGROUP ({metadata.subgroup_variable})")
    if metadata.is_adjusted:
        flags.append(f"ADJUSTED ({', '.join(metadata.adjustment_variables[:3])})")

    if flags:
        lines.append(f"Flags: {', '.join(flags)}")

    return "\n".join(lines)
