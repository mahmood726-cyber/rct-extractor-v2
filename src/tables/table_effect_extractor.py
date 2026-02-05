"""
Table-to-Effect Extraction Pipeline
====================================

Specialized module for extracting effect estimates (HR, OR, RR, MD, SMD)
directly from RCT result tables.

Features:
1. Detect outcome/results tables vs baseline/safety tables
2. Identify effect estimate columns (HR, OR, RR, MD columns)
3. Extract values with CIs from table cells
4. Link effects to outcome names from row headers

Usage:
    from src.tables.table_effect_extractor import TableEffectExtractor

    extractor = TableEffectExtractor()
    effects = extractor.extract_from_table(table_structure)
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any
from enum import Enum

# Import from parent modules
try:
    from .table_extractor import TableStructure, TableCell
    from ..core.models import TableType
except ImportError:
    # For standalone testing
    TableStructure = Any
    TableCell = Any
    class TableType(Enum):
        OUTCOMES = "outcomes"
        BASELINE = "baseline"
        SAFETY = "safety"
        OTHER = "other"


class EffectColumnType(Enum):
    """Types of effect columns in tables"""
    HR = "HR"
    OR = "OR"
    RR = "RR"
    MD = "MD"
    SMD = "SMD"
    IRR = "IRR"
    ARD = "ARD"
    CI = "CI"
    P_VALUE = "P_VALUE"
    EVENTS = "EVENTS"
    N = "N"
    UNKNOWN = "UNKNOWN"


@dataclass
class TableEffect:
    """Effect estimate extracted from a table"""
    effect_type: str
    point_estimate: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    ci_level: float = 0.95
    p_value: Optional[float] = None
    outcome_name: str = ""
    subgroup: str = ""
    comparison: str = ""
    row_index: int = 0
    col_index: int = 0
    source_cells: List[str] = field(default_factory=list)
    confidence: float = 0.8


@dataclass
class ColumnClassification:
    """Classification of a table column"""
    index: int
    header: str
    column_type: EffectColumnType
    confidence: float


# Column header patterns for classification
COLUMN_PATTERNS = {
    EffectColumnType.HR: [
        r'\bHR\b', r'[Hh]azard\s*[Rr]atio', r'[Hh]azard\s*[Rr]ate',
        r'\baHR\b', r'[Aa]djusted\s+HR',
    ],
    EffectColumnType.OR: [
        r'\bOR\b', r'[Oo]dds\s*[Rr]atio', r'\baOR\b',
        r'[Aa]djusted\s+OR', r'\bDOR\b',
    ],
    EffectColumnType.RR: [
        r'\bRR\b', r'[Rr]isk\s*[Rr]atio', r'[Rr]elative\s*[Rr]isk',
        r'\baRR\b', r'[Rr]ate\s*[Rr]atio',
    ],
    EffectColumnType.MD: [
        r'\bMD\b', r'[Mm]ean\s*[Dd]iff(?:erence)?', r'\bWMD\b',
        r'[Ww]eighted\s+[Mm]ean', r'[Dd]ifference',
    ],
    EffectColumnType.SMD: [
        r'\bSMD\b', r'[Ss]tandardized\s*[Mm]ean',
        r"[Cc]ohen'?s?\s*d", r"[Hh]edges'?\s*g",
        r'[Ee]ffect\s*[Ss]ize',
    ],
    EffectColumnType.IRR: [
        r'\bIRR\b', r'[Ii]ncidence\s*[Rr]ate\s*[Rr]atio',
    ],
    EffectColumnType.ARD: [
        r'\bARD\b', r'\bRD\b', r'[Rr]isk\s*[Dd]ifference',
        r'[Aa]bsolute\s*[Rr]isk',
    ],
    EffectColumnType.CI: [
        r'\b95%?\s*CI\b', r'[Cc]onfidence\s*[Ii]nterval',
        r'\bCI\b', r'\bKI\b', r'\bIC\b',
    ],
    EffectColumnType.P_VALUE: [
        r'\bp[\s-]*[Vv]alue\b', r'\bP\b', r'\bp\b',
        r'[Ss]ignificance',
    ],
    EffectColumnType.EVENTS: [
        r'[Ee]vents?', r'[Nn]\s*\(\s*%\s*\)', r'[Cc]ases?',
        r'[Ii]ncidence',
    ],
    EffectColumnType.N: [
        r'\bN\b', r'\bn\b', r'[Ss]ample\s*[Ss]ize',
        r'[Pp]atients?', r'[Pp]articipants?',
    ],
}

# Outcome table indicators (positive)
OUTCOME_TABLE_KEYWORDS = [
    r'[Pp]rimary\s*[Oo]utcome', r'[Ss]econdary\s*[Oo]utcome',
    r'[Ee]fficacy', r'[Ee]ffectiveness', r'[Rr]esults?',
    r'[Ee]ndpoint', r'[Hh]azard\s*[Rr]atio', r'[Oo]dds\s*[Rr]atio',
    r'[Rr]isk\s*[Rr]atio', r'[Mm]ean\s*[Dd]ifference',
    r'[Mm]ortality', r'[Ss]urvival', r'[Pp]rogression',
    r'[Rr]esponse\s*[Rr]ate', r'[Rr]emission',
]

# Non-outcome table indicators (negative)
NON_OUTCOME_KEYWORDS = [
    r'[Bb]aseline', r'[Dd]emographic', r'[Cc]haracteristic',
    r'[Aa]dverse\s*[Ee]vent', r'[Ss]afety', r'[Ss]ide\s*[Ee]ffect',
    r'[Dd]iscontinuation', r'[Ww]ithdrawal',
    r'[Dd]osing', r'[Dd]ose', r'[Mm]edication',
]


class TableEffectExtractor:
    """
    Extracts effect estimates from RCT result tables.

    Identifies outcome tables, classifies columns, and extracts
    effect estimates with confidence intervals.
    """

    def __init__(self):
        self.column_patterns = COLUMN_PATTERNS
        self.outcome_keywords = OUTCOME_TABLE_KEYWORDS
        self.non_outcome_keywords = NON_OUTCOME_KEYWORDS

    def is_outcome_table(self, table: TableStructure) -> Tuple[bool, float]:
        """
        Determine if a table contains outcome/results data.

        Args:
            table: TableStructure to analyze

        Returns:
            Tuple of (is_outcome_table, confidence)
        """
        # Get all text from table
        all_text = ' '.join(cell.text for cell in table.cells)

        # Count positive indicators
        positive_count = 0
        for pattern in self.outcome_keywords:
            if re.search(pattern, all_text, re.IGNORECASE):
                positive_count += 1

        # Count negative indicators
        negative_count = 0
        for pattern in self.non_outcome_keywords:
            if re.search(pattern, all_text, re.IGNORECASE):
                negative_count += 1

        # Check for effect type columns
        headers = table.get_headers()
        header_text = ' '.join(' '.join(row) for row in headers)

        effect_columns = 0
        for effect_type in [EffectColumnType.HR, EffectColumnType.OR,
                           EffectColumnType.RR, EffectColumnType.MD,
                           EffectColumnType.SMD]:
            for pattern in self.column_patterns[effect_type]:
                if re.search(pattern, header_text, re.IGNORECASE):
                    effect_columns += 1

        # Calculate score
        score = positive_count * 2 + effect_columns * 3 - negative_count * 2

        # Determine if outcome table
        is_outcome = score > 0 or effect_columns > 0

        # Calculate confidence
        if effect_columns > 0:
            confidence = min(0.7 + effect_columns * 0.1, 0.95)
        elif positive_count > negative_count:
            confidence = min(0.5 + positive_count * 0.1, 0.8)
        else:
            confidence = max(0.3, 0.5 - negative_count * 0.1)

        return is_outcome, confidence

    def classify_columns(self, table: TableStructure) -> List[ColumnClassification]:
        """
        Classify each column by its content type.

        Args:
            table: TableStructure to analyze

        Returns:
            List of ColumnClassification objects
        """
        classifications = []
        headers = table.get_headers()

        if not headers:
            return classifications

        # Use first header row for classification
        header_row = headers[0] if headers else []

        for col_idx, header_text in enumerate(header_row):
            best_type = EffectColumnType.UNKNOWN
            best_confidence = 0.0

            for col_type, patterns in self.column_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, header_text, re.IGNORECASE):
                        # Higher confidence for exact matches
                        confidence = 0.9 if re.fullmatch(pattern, header_text.strip(), re.IGNORECASE) else 0.7
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_type = col_type
                        break

            classifications.append(ColumnClassification(
                index=col_idx,
                header=header_text,
                column_type=best_type,
                confidence=best_confidence
            ))

        return classifications

    def extract_from_table(self, table: TableStructure) -> List[TableEffect]:
        """
        Extract effect estimates from a table.

        Args:
            table: TableStructure to extract from

        Returns:
            List of TableEffect objects
        """
        effects = []

        # Check if this is an outcome table
        is_outcome, table_confidence = self.is_outcome_table(table)
        if not is_outcome:
            return effects

        # Classify columns
        columns = self.classify_columns(table)

        # Find effect columns
        effect_cols = [c for c in columns if c.column_type in
                      [EffectColumnType.HR, EffectColumnType.OR,
                       EffectColumnType.RR, EffectColumnType.MD,
                       EffectColumnType.SMD, EffectColumnType.IRR,
                       EffectColumnType.ARD]]

        # Find CI columns
        ci_cols = [c for c in columns if c.column_type == EffectColumnType.CI]

        # Find P-value columns
        p_cols = [c for c in columns if c.column_type == EffectColumnType.P_VALUE]

        # Find outcome name column (usually first column)
        outcome_col = 0  # Default to first column

        # Process each effect column
        for effect_col in effect_cols:
            # Process each data row
            for row_idx in range(table.header_rows, table.num_rows):
                row_cells = table.get_row(row_idx)

                # Get outcome name
                outcome_name = ""
                if outcome_col < len(row_cells):
                    outcome_name = row_cells[outcome_col].text.strip()

                # Get effect value
                effect_cell = table.get_cell(row_idx, effect_col.index)
                if not effect_cell:
                    continue

                cell_text = effect_cell.text.strip()

                # Try to extract effect from cell
                extracted = self._extract_effect_from_cell(
                    cell_text,
                    effect_col.column_type.value
                )

                if extracted:
                    value, ci_lower, ci_upper = extracted

                    # If CI not in same cell, try CI column
                    if ci_lower is None and ci_cols:
                        ci_col = ci_cols[0]
                        ci_cell = table.get_cell(row_idx, ci_col.index)
                        if ci_cell:
                            ci_extracted = self._extract_ci_from_cell(ci_cell.text)
                            if ci_extracted:
                                ci_lower, ci_upper = ci_extracted

                    # Try to get P-value
                    p_value = None
                    if p_cols:
                        p_col = p_cols[0]
                        p_cell = table.get_cell(row_idx, p_col.index)
                        if p_cell:
                            p_value = self._extract_pvalue(p_cell.text)

                    effect = TableEffect(
                        effect_type=effect_col.column_type.value,
                        point_estimate=value,
                        ci_lower=ci_lower,
                        ci_upper=ci_upper,
                        p_value=p_value,
                        outcome_name=outcome_name,
                        row_index=row_idx,
                        col_index=effect_col.index,
                        source_cells=[cell_text],
                        confidence=effect_col.confidence * table_confidence
                    )
                    effects.append(effect)

        return effects

    def _extract_effect_from_cell(
        self,
        text: str,
        effect_type: str
    ) -> Optional[Tuple[float, Optional[float], Optional[float]]]:
        """
        Extract effect value and CI from a cell.

        Args:
            text: Cell text
            effect_type: Expected effect type

        Returns:
            Tuple of (value, ci_lower, ci_upper) or None
        """
        # Pattern: "0.74 (0.65-0.85)" or "0.74 (0.65, 0.85)" or "0.74 (0.65 to 0.85)"
        patterns = [
            # Value with CI in parentheses (dash)
            r'(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)\s*\)',
            # Value with CI in parentheses (comma)
            r'(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)',
            # Value with CI in parentheses (to)
            r'(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',
            # Value with CI in brackets
            r'(-?\d+\.?\d*)\s*\[\s*(-?\d+\.?\d*)\s*[-–—,]\s*(-?\d+\.?\d*)\s*\]',
            # Value only
            r'^(-?\d+\.?\d*)$',
        ]

        for pattern in patterns:
            match = re.search(pattern, text.strip())
            if match:
                groups = match.groups()
                try:
                    value = float(groups[0])
                    ci_lower = float(groups[1]) if len(groups) > 1 else None
                    ci_upper = float(groups[2]) if len(groups) > 2 else None
                    return (value, ci_lower, ci_upper)
                except (ValueError, IndexError):
                    continue

        return None

    def _extract_ci_from_cell(self, text: str) -> Optional[Tuple[float, float]]:
        """
        Extract CI bounds from a CI column cell.

        Args:
            text: Cell text

        Returns:
            Tuple of (ci_lower, ci_upper) or None
        """
        patterns = [
            # "0.65-0.85" or "0.65 to 0.85"
            r'(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)',
            r'(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
            # "(0.65, 0.85)"
            r'\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text.strip())
            if match:
                try:
                    ci_lower = float(match.group(1))
                    ci_upper = float(match.group(2))
                    return (ci_lower, ci_upper)
                except (ValueError, IndexError):
                    continue

        return None

    def _extract_pvalue(self, text: str) -> Optional[float]:
        """
        Extract P-value from text.

        Args:
            text: Cell text

        Returns:
            P-value as float or None
        """
        patterns = [
            # "<0.001" or "< 0.001"
            r'<\s*(\d+\.?\d*)',
            # "0.023" or "P = 0.023"
            r'(?:P\s*[=:]\s*)?(\d+\.?\d*)',
            # "P<0.05"
            r'P\s*<\s*(\d+\.?\d*)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text.strip(), re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    if 0 <= value <= 1:
                        return value
                except (ValueError, IndexError):
                    continue

        return None


def extract_effects_from_tables(tables: List[TableStructure]) -> List[TableEffect]:
    """
    Convenience function to extract effects from multiple tables.

    Args:
        tables: List of TableStructure objects

    Returns:
        List of all extracted TableEffect objects
    """
    extractor = TableEffectExtractor()
    all_effects = []

    for table in tables:
        effects = extractor.extract_from_table(table)
        all_effects.extend(effects)

    return all_effects
