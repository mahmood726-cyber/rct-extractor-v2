"""
Composite Endpoint Standardization for RCT Extractor v2.14
==========================================================

Implements:
1. Composite endpoint parsing (MACE, MAKE, etc.)
2. Component extraction with individual effects
3. Standardized endpoint classification
4. Hierarchical endpoint mapping
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum


class EndpointCategory(Enum):
    """Standard endpoint categories"""
    CARDIOVASCULAR = "cardiovascular"
    RENAL = "renal"
    MORTALITY = "mortality"
    SAFETY = "safety"
    EFFICACY = "efficacy"
    QUALITY_OF_LIFE = "qol"
    COMPOSITE = "composite"
    OTHER = "other"


@dataclass
class EndpointComponent:
    """A single component of a composite endpoint"""
    name: str
    standardized_name: str
    category: EndpointCategory
    effect_type: Optional[str] = None
    effect_size: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    events_treatment: Optional[int] = None
    events_control: Optional[int] = None


@dataclass
class CompositeEndpoint:
    """A composite endpoint with its components"""
    name: str
    standardized_name: str
    abbreviation: Optional[str]
    components: List[EndpointComponent]
    category: EndpointCategory
    is_hierarchical: bool = False
    hierarchy_method: Optional[str] = None  # "win ratio", "time to first event", etc.

    # Overall composite effect
    effect_type: Optional[str] = None
    effect_size: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None


# =============================================================================
# STANDARD ENDPOINT DEFINITIONS
# =============================================================================

STANDARD_COMPOSITES = {
    # Cardiovascular composites
    "MACE": {
        "full_name": "Major Adverse Cardiovascular Events",
        "category": EndpointCategory.CARDIOVASCULAR,
        "components": ["cardiovascular death", "myocardial infarction", "stroke"],
        "variants": ["3-point MACE", "3P-MACE", "three-point MACE"]
    },
    "MACE-4": {
        "full_name": "4-Point Major Adverse Cardiovascular Events",
        "category": EndpointCategory.CARDIOVASCULAR,
        "components": ["cardiovascular death", "myocardial infarction", "stroke",
                      "hospitalization for unstable angina"],
        "variants": ["4-point MACE", "4P-MACE", "four-point MACE", "expanded MACE"]
    },
    "MACE-5": {
        "full_name": "5-Point Major Adverse Cardiovascular Events",
        "category": EndpointCategory.CARDIOVASCULAR,
        "components": ["cardiovascular death", "myocardial infarction", "stroke",
                      "hospitalization for unstable angina", "coronary revascularization"],
        "variants": ["5-point MACE", "5P-MACE"]
    },

    # Heart failure composites
    "HF-COMPOSITE": {
        "full_name": "Heart Failure Composite",
        "category": EndpointCategory.CARDIOVASCULAR,
        "components": ["cardiovascular death", "hospitalization for heart failure"],
        "variants": ["CV death or HHF", "worsening heart failure"]
    },
    "HF-COMPOSITE-3": {
        "full_name": "Heart Failure Composite (3-point)",
        "category": EndpointCategory.CARDIOVASCULAR,
        "components": ["cardiovascular death", "hospitalization for heart failure",
                      "urgent heart failure visit"],
        "variants": ["CV death, HHF, or urgent HF visit"]
    },

    # Renal composites
    "MAKE": {
        "full_name": "Major Adverse Kidney Events",
        "category": EndpointCategory.RENAL,
        "components": ["sustained eGFR decline 40% or more", "end-stage kidney disease", "renal death"],
        "variants": ["kidney composite", "renal composite"]
    },
    "MAKE-40": {
        "full_name": "Major Adverse Kidney Events (40% decline)",
        "category": EndpointCategory.RENAL,
        "components": ["sustained eGFR decline 40% or more", "ESKD", "renal death"],
        "variants": ["MAKE40"]
    },
    "MAKE-50": {
        "full_name": "Major Adverse Kidney Events (50% decline)",
        "category": EndpointCategory.RENAL,
        "components": ["sustained eGFR decline 50% or more", "ESKD", "renal death"],
        "variants": ["MAKE50", "doubling of creatinine"]
    },

    # Cardiorenal composites
    "CARDIO-RENAL": {
        "full_name": "Cardiorenal Composite",
        "category": EndpointCategory.COMPOSITE,
        "components": ["cardiovascular death", "hospitalization for heart failure",
                      "sustained eGFR decline", "end-stage kidney disease"],
        "variants": ["cardiorenal endpoint", "combined CV and renal"]
    },

    # Safety composites
    "MALE": {
        "full_name": "Major Adverse Limb Events",
        "category": EndpointCategory.SAFETY,
        "components": ["major amputation", "acute limb ischemia"],
        "variants": ["limb events"]
    },
    "MABE": {
        "full_name": "Major Adverse Bleeding Events",
        "category": EndpointCategory.SAFETY,
        "components": ["ISTH major bleeding", "intracranial hemorrhage", "fatal bleeding"],
        "variants": ["major bleeding composite"]
    },

    # Net clinical benefit
    "NCB": {
        "full_name": "Net Clinical Benefit",
        "category": EndpointCategory.COMPOSITE,
        "components": ["MACE components", "major bleeding"],
        "variants": ["net adverse clinical events", "NACE"]
    },
}

# Component standardization mapping
COMPONENT_STANDARDIZATION = {
    # Mortality
    "cv death": "cardiovascular death",
    "cardiac death": "cardiovascular death",
    "cardiovascular mortality": "cardiovascular death",
    "death from cardiovascular causes": "cardiovascular death",
    "all-cause death": "all-cause mortality",
    "all-cause mortality": "all-cause mortality",
    "death from any cause": "all-cause mortality",
    "total mortality": "all-cause mortality",
    "renal death": "renal death",
    "death from renal causes": "renal death",

    # Myocardial infarction
    "mi": "myocardial infarction",
    "heart attack": "myocardial infarction",
    "nonfatal mi": "non-fatal myocardial infarction",
    "non-fatal mi": "non-fatal myocardial infarction",
    "fatal mi": "fatal myocardial infarction",
    "type 1 mi": "type 1 myocardial infarction",

    # Stroke
    "cva": "stroke",
    "cerebrovascular accident": "stroke",
    "stroke": "stroke",
    "nonfatal stroke": "non-fatal stroke",
    "non-fatal stroke": "non-fatal stroke",
    "fatal stroke": "fatal stroke",
    "ischemic stroke": "ischemic stroke",
    "hemorrhagic stroke": "hemorrhagic stroke",

    # Heart failure
    "hhf": "hospitalization for heart failure",
    "hf hospitalization": "hospitalization for heart failure",
    "heart failure hospitalization": "hospitalization for heart failure",
    "worsening hf": "worsening heart failure",
    "worsening heart failure": "worsening heart failure",
    "urgent hf visit": "urgent heart failure visit",

    # Renal
    "eskd": "end-stage kidney disease",
    "esrd": "end-stage kidney disease",
    "end-stage renal disease": "end-stage kidney disease",
    "dialysis": "dialysis initiation",
    "renal replacement therapy": "dialysis initiation",
    "rrt": "dialysis initiation",
    "doubling of creatinine": "sustained doubling of serum creatinine",
    "egfr decline 40%": "sustained eGFR decline 40% or more",
    "egfr decline 50%": "sustained eGFR decline 50% or more",
    "egfr decline 57%": "sustained eGFR decline 57% or more",

    # Revascularization
    "pci": "percutaneous coronary intervention",
    "cabg": "coronary artery bypass grafting",
    "coronary revascularization": "coronary revascularization",
    "revascularization": "coronary revascularization",

    # Bleeding
    "major bleeding": "major bleeding",
    "isth major bleeding": "ISTH major bleeding",
    "timi major bleeding": "TIMI major bleeding",
    "barc 3-5": "BARC type 3-5 bleeding",
    "ich": "intracranial hemorrhage",
    "intracranial bleeding": "intracranial hemorrhage",
    "gi bleeding": "gastrointestinal bleeding",
}


# =============================================================================
# COMPOSITE ENDPOINT PARSER
# =============================================================================

class CompositeEndpointParser:
    """
    Parse and standardize composite endpoints from clinical trial text.
    """

    # Patterns for detecting composite endpoint definitions
    COMPOSITE_PATTERNS = [
        # "MACE (cardiovascular death, MI, or stroke)"
        r'(\b[A-Z]{3,6}\b)\s*\(\s*([^)]+(?:,\s*(?:or\s+)?[^)]+)+)\)',

        # "CV death/HHF composite" - must come before generic patterns
        r'(CV\s+death)\s*/\s*(HHF)\s+composite',

        # "composite endpoint of death, MI, stroke, and urgent revascularization"
        r'composite\s+endpoint\s+of\s+((?:[^,]+,\s*)+(?:and\s+)?[^,.]+)',

        # "composite of cardiovascular death, MI, and stroke"
        r'composite\s+of\s+((?:[^,]+,\s*)+(?:and\s+|or\s+)?[^,.]+)',

        # "primary outcome: composite of all-cause mortality or hospitalization"
        r'(?:primary|secondary)\s+(?:outcome|endpoint)[:\s]+(?:composite\s+of\s+)?([^.;]+(?:\s+(?:and|or)\s+[^.;]+)+)',

        # "the composite outcome of death or hospitalization"
        r'composite\s+outcome\s+of\s+([^.;]+)',

        # "CV death or HHF"
        r'((?:CV|cardiovascular)\s+death)\s+or\s+(HHF|(?:hospitalization[^,;.]+))',
    ]

    # Patterns for extracting component effects
    COMPONENT_EFFECT_PATTERNS = [
        # "CV death: HR 0.62 (0.49-0.77)"
        r'([A-Za-z][^:;,\n]{2,30}?):\s*(?:HR|OR|RR)\s*(\d+\.?\d*)\s*\((\d+\.?\d*)\s*[-\u2013\u2014]\s*(\d+\.?\d*)\)',

        # "For cardiovascular death, HR was 0.82 (95% CI 0.69-0.98)"
        r'[Ff]or\s+([A-Za-z][^,]{2,40}?),\s*(?:HR|OR|RR)\s+(?:was\s+)?(\d+\.?\d*)\s*\((?:95%?\s*CI\s*)?(\d+\.?\d*)\s*[-\u2013\u2014]\s*(\d+\.?\d*)',

        # "MI: HR 0.87 (0.70-1.07)"
        r'\b(MI|stroke|death|HHF)\b:\s*(?:HR|OR|RR)\s*(\d+\.?\d*)\s*\((\d+\.?\d*)\s*[-\u2013\u2014]\s*(\d+\.?\d*)',

        # "CV death (HR 0.75, 95% CI 0.65-0.86)"
        r'([A-Za-z][^(]{2,30}?)\s*\(\s*(?:HR|OR|RR)\s*(\d+\.?\d*)[,;]\s*(?:95%?\s*CI\s*)?(\d+\.?\d*)\s*[-\u2013\u2014]\s*(\d+\.?\d*)',
    ]

    def __init__(self):
        self.standard_composites = STANDARD_COMPOSITES
        self.component_mapping = COMPONENT_STANDARDIZATION

    def parse(self, text: str) -> List[CompositeEndpoint]:
        """
        Parse composite endpoints from text.

        Returns list of CompositeEndpoint objects with standardized components.
        """
        results = []
        found_abbrevs = set()

        # Check for N-point MACE variants first (before generic MACE)
        mace_point_match = re.search(r'(\d)-?point\s+MACE', text, re.IGNORECASE)
        if mace_point_match:
            n_points = mace_point_match.group(1)
            if n_points == "4":
                definition = self.standard_composites.get("MACE-4")
                if definition:
                    endpoint = self._create_standard_endpoint("MACE-4", definition, text)
                    if endpoint:
                        results.append(endpoint)
                        found_abbrevs.add("MACE-4")
                        found_abbrevs.add("MACE")  # Don't also match generic MACE
            elif n_points == "5":
                definition = self.standard_composites.get("MACE-5")
                if definition:
                    endpoint = self._create_standard_endpoint("MACE-5", definition, text)
                    if endpoint:
                        results.append(endpoint)
                        found_abbrevs.add("MACE-5")
                        found_abbrevs.add("MACE")

        # Check for standard composite abbreviations
        for abbrev, definition in self.standard_composites.items():
            if abbrev in found_abbrevs:
                continue

            # Check direct abbreviation
            pattern = rf'\b{re.escape(abbrev)}\b'
            if re.search(pattern, text, re.IGNORECASE):
                endpoint = self._create_standard_endpoint(abbrev, definition, text)
                if endpoint:
                    results.append(endpoint)
                    found_abbrevs.add(abbrev)
                continue

            # Check variants
            for variant in definition.get("variants", []):
                if variant.lower() in text.lower():
                    endpoint = self._create_standard_endpoint(abbrev, definition, text)
                    if endpoint:
                        results.append(endpoint)
                        found_abbrevs.add(abbrev)
                    break

        # Also look for custom composite definitions
        for pattern in self.COMPOSITE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                endpoint = self._parse_custom_composite(match, text)
                if endpoint and not self._is_duplicate(endpoint, results):
                    results.append(endpoint)

        return results

    def _create_standard_endpoint(self, abbrev: str, definition: dict,
                                   text: str) -> Optional[CompositeEndpoint]:
        """Create a CompositeEndpoint from a standard definition."""

        # Create component objects
        components = []
        for comp_name in definition["components"]:
            std_name = self._standardize_component(comp_name)
            category = self._categorize_component(std_name)
            components.append(EndpointComponent(
                name=comp_name,
                standardized_name=std_name,
                category=category
            ))

        # Try to extract effect for the composite
        effect_type, effect_size, ci_lower, ci_upper = self._extract_composite_effect(
            abbrev, text
        )

        # Try to extract component-level effects
        components = self._extract_component_effects(components, text)

        return CompositeEndpoint(
            name=definition["full_name"],
            standardized_name=definition["full_name"],
            abbreviation=abbrev,
            components=components,
            category=definition["category"],
            effect_type=effect_type,
            effect_size=effect_size,
            ci_lower=ci_lower,
            ci_upper=ci_upper
        )

    def _parse_custom_composite(self, match: re.Match, text: str) -> Optional[CompositeEndpoint]:
        """Parse a custom composite endpoint from regex match."""

        abbrev = None
        component_text = match.group(0)  # Default to full match

        # Check if this is a slash-separated pattern (both groups are components)
        matched_text = match.group(0)
        if '/' in matched_text and len(match.groups()) == 2:
            # Both groups are components (e.g., "CV death" and "HHF")
            component_names = [match.group(1).strip(), match.group(2).strip()]
            component_text = f"{match.group(1)} or {match.group(2)}"
        elif len(match.groups()) >= 2:
            # First group might be abbreviation
            first_group = match.group(1)
            abbrev = first_group if (first_group.isupper() and len(first_group) <= 6) else None
            component_text = match.group(2) if abbrev else match.group(1)
            if not abbrev and len(match.groups()) >= 2:
                # Could be two component groups like "CV death or HHF"
                if match.group(2) and not match.group(1).isupper():
                    component_names = [match.group(1).strip(), match.group(2).strip()]
                    component_text = f"{match.group(1)} or {match.group(2)}"
                else:
                    component_names = self._split_components(component_text)
            else:
                component_names = self._split_components(component_text)
        else:
            component_text = match.group(1)
            component_names = self._split_components(component_text)

        if len(component_names) < 2:
            return None

        # Create component objects
        components = []
        for name in component_names:
            std_name = self._standardize_component(name)
            category = self._categorize_component(std_name)
            components.append(EndpointComponent(
                name=name.strip(),
                standardized_name=std_name,
                category=category
            ))

        # Determine overall category
        categories = [c.category for c in components]
        if all(c == EndpointCategory.CARDIOVASCULAR for c in categories):
            overall_cat = EndpointCategory.CARDIOVASCULAR
        elif all(c == EndpointCategory.RENAL for c in categories):
            overall_cat = EndpointCategory.RENAL
        else:
            overall_cat = EndpointCategory.COMPOSITE

        # Try to extract effect
        effect_type, effect_size, ci_lower, ci_upper = None, None, None, None
        if abbrev:
            effect_type, effect_size, ci_lower, ci_upper = self._extract_composite_effect(
                abbrev, text
            )

        # Generate standardized name
        std_name = self._generate_composite_name(components)

        return CompositeEndpoint(
            name=component_text.strip(),
            standardized_name=std_name,
            abbreviation=abbrev,
            components=components,
            category=overall_cat,
            effect_type=effect_type,
            effect_size=effect_size,
            ci_lower=ci_lower,
            ci_upper=ci_upper
        )

    def _split_components(self, text: str) -> List[str]:
        """Split component list text into individual components."""
        # Protect "X% or more" patterns from being split
        text = re.sub(r'(\d+%)\s+or\s+more', r'\1_OR_MORE', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+%)\s+or\s+greater', r'\1_OR_GREATER', text, flags=re.IGNORECASE)

        # Handle "X, Y, and Z" or "X, Y, or Z" patterns
        text = re.sub(r'\s*,\s*(?:and|or)\s+', ', ', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+(?:and|or)\s+', ', ', text, flags=re.IGNORECASE)

        # Split on comma
        parts = [p.strip() for p in text.split(',')]

        # Restore protected patterns and filter
        result = []
        for p in parts:
            if p and len(p) > 2:
                p = p.replace('_OR_MORE', ' or more')
                p = p.replace('_OR_GREATER', ' or greater')
                result.append(p)

        return result

    def _standardize_component(self, name: str) -> str:
        """Standardize a component name."""
        name_lower = name.lower().strip()

        # Direct mapping lookup
        if name_lower in self.component_mapping:
            return self.component_mapping[name_lower]

        # Partial matching
        for key, std_name in self.component_mapping.items():
            if key in name_lower or name_lower in key:
                return std_name

        # Return cleaned original if no match
        return name.strip().lower()

    def _categorize_component(self, std_name: str) -> EndpointCategory:
        """Categorize a standardized component."""
        mortality_terms = ["death", "mortality"]
        cv_terms = ["cardiovascular", "myocardial", "stroke", "heart failure",
                    "hospitalization for heart", "angina", "revascularization"]
        renal_terms = ["kidney", "renal", "egfr", "creatinine", "dialysis", "eskd"]
        safety_terms = ["bleeding", "hemorrhage", "amputation", "limb"]

        std_lower = std_name.lower()

        if any(term in std_lower for term in renal_terms):
            return EndpointCategory.RENAL
        if any(term in std_lower for term in safety_terms):
            return EndpointCategory.SAFETY
        if any(term in std_lower for term in cv_terms):
            return EndpointCategory.CARDIOVASCULAR
        if any(term in std_lower for term in mortality_terms):
            return EndpointCategory.MORTALITY

        return EndpointCategory.OTHER

    def _extract_composite_effect(self, abbrev: str, text: str) -> Tuple[
            Optional[str], Optional[float], Optional[float], Optional[float]]:
        """Extract effect estimate for a composite endpoint."""

        # Pattern: "MACE: HR 0.75 (0.65-0.86)" or "MACE, HR 0.75 (95% CI 0.65-0.86)"
        patterns = [
            rf'{re.escape(abbrev)}[:\s,]+(?:HR|OR|RR)\s*[=:]?\s*(\d+\.?\d*)\s*\([^)]*?(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            rf'(?:HR|OR|RR)\s+(?:for\s+)?{re.escape(abbrev)}[:\s,]+(\d+\.?\d*)\s*\([^)]*?(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return (
                    "HR",  # Default to HR for composites
                    float(match.group(1)),
                    float(match.group(2)),
                    float(match.group(3))
                )

        return None, None, None, None

    def _extract_component_effects(self, components: List[EndpointComponent],
                                   text: str) -> List[EndpointComponent]:
        """Extract individual effects for each component."""

        for component in components:
            for pattern in self.COMPONENT_EFFECT_PATTERNS:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    comp_name = match.group(1).strip().lower()

                    # Check if this match is for this component
                    if (comp_name in component.name.lower() or
                        comp_name in component.standardized_name.lower() or
                        component.name.lower() in comp_name):

                        try:
                            component.effect_type = "HR"
                            component.effect_size = float(match.group(2))
                            component.ci_lower = float(match.group(3))
                            component.ci_upper = float(match.group(4))
                        except (ValueError, IndexError):
                            continue

        return components

    def _generate_composite_name(self, components: List[EndpointComponent]) -> str:
        """Generate a standardized name for the composite."""
        std_names = [c.standardized_name for c in components]

        if len(std_names) == 2:
            return f"{std_names[0]} or {std_names[1]}"
        else:
            return ", ".join(std_names[:-1]) + f", or {std_names[-1]}"

    def _is_duplicate(self, new_endpoint: CompositeEndpoint,
                      existing: List[CompositeEndpoint]) -> bool:
        """Check if endpoint is a duplicate."""
        for ep in existing:
            if ep.abbreviation == new_endpoint.abbreviation:
                return True
            if set(c.standardized_name for c in ep.components) == \
               set(c.standardized_name for c in new_endpoint.components):
                return True
        return False

    def get_standard_definition(self, abbrev: str) -> Optional[dict]:
        """Get the standard definition for a composite abbreviation."""
        return self.standard_composites.get(abbrev.upper())

    def standardize_endpoint_name(self, name: str) -> Tuple[str, Optional[str]]:
        """
        Standardize an endpoint name and return abbreviation if known.

        Returns: (standardized_name, abbreviation)
        """
        name_upper = name.upper().strip()

        # Check direct match
        if name_upper in self.standard_composites:
            defn = self.standard_composites[name_upper]
            return defn["full_name"], name_upper

        # Check variants
        for abbrev, defn in self.standard_composites.items():
            for variant in defn.get("variants", []):
                if variant.upper() == name_upper or name.lower() == variant.lower():
                    return defn["full_name"], abbrev

        # No match found
        return name, None


# =============================================================================
# HIERARCHICAL ENDPOINT ANALYZER
# =============================================================================

class HierarchicalEndpointAnalyzer:
    """
    Analyze hierarchical composite endpoints (win ratio, etc.).
    """

    HIERARCHY_PATTERNS = [
        # "using a hierarchical composite with death ranked first"
        r'hierarchical\s+(?:composite|analysis)',

        # "components were ranked: death > HHF > change in symptoms"
        r'(?:components|endpoints)\s+(?:were\s+)?ranked',

        # "win ratio analysis"
        r'win\s+ratio\s+(?:analysis|was)',

        # "Win ratio 1.28"
        r'[Ww]in\s+ratio\s+\d',
    ]

    TIME_TO_FIRST_PATTERNS = [
        r'time\s+to\s+first\s+event',
        r'first\s+occurrence\s+of',
    ]

    def analyze(self, text: str, composite: CompositeEndpoint) -> CompositeEndpoint:
        """
        Analyze if a composite uses hierarchical analysis and determine hierarchy.
        """
        text_lower = text.lower()

        # Check for win ratio
        if re.search(r'win\s+ratio', text_lower):
            composite.is_hierarchical = True
            composite.hierarchy_method = "win ratio"
            return composite

        # Check for time to first event
        for pattern in self.TIME_TO_FIRST_PATTERNS:
            if re.search(pattern, text_lower):
                composite.is_hierarchical = True
                composite.hierarchy_method = "time to first event"
                return composite

        # Check for hierarchy indicators
        for pattern in self.HIERARCHY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                composite.is_hierarchical = True
                if not composite.hierarchy_method:
                    composite.hierarchy_method = "hierarchical"
                return composite

        return composite

    def _order_components(self, components: List[EndpointComponent],
                          hierarchy_text: str) -> List[EndpointComponent]:
        """Order components based on hierarchy text."""
        ordered = []
        remaining = list(components)

        # Parse hierarchy text for order
        hierarchy_lower = hierarchy_text.lower()

        # Standard hierarchy: death > HF > other
        priority_terms = [
            ("death", "mortality"),
            ("hospitalization", "hhf", "heart failure"),
            ("stroke", "mi", "infarction"),
        ]

        for terms in priority_terms:
            for comp in remaining[:]:
                if any(term in comp.standardized_name.lower() for term in terms):
                    ordered.append(comp)
                    remaining.remove(comp)
                    break

        # Add any remaining components
        ordered.extend(remaining)

        return ordered


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def parse_composite_endpoints(text: str) -> List[CompositeEndpoint]:
    """Parse all composite endpoints from text."""
    parser = CompositeEndpointParser()
    return parser.parse(text)


def standardize_endpoint(name: str) -> Tuple[str, Optional[str]]:
    """Standardize an endpoint name."""
    parser = CompositeEndpointParser()
    return parser.standardize_endpoint_name(name)


def get_mace_definition(variant: str = "3-point") -> dict:
    """Get MACE definition by variant."""
    if "4" in variant:
        return STANDARD_COMPOSITES["MACE-4"]
    elif "5" in variant:
        return STANDARD_COMPOSITES["MACE-5"]
    return STANDARD_COMPOSITES["MACE"]
