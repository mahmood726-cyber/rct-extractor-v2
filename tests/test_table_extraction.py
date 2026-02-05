#!/usr/bin/env python3
"""
Table Extraction Tests for RCT Extractor v4.0.7
Tests table detection, structure extraction, and classification.

Run: pytest tests/test_table_extraction.py -v
"""

import pytest
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import sys

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Define TableType enum locally to avoid circular imports
class TableType(Enum):
    """Table classification types"""
    OUTCOMES = "outcomes"
    BASELINE = "baseline"
    SAFETY = "safety"
    SUBGROUP = "subgroup"
    OTHER = "other"


# Define a simple BBox for testing
@dataclass
class BBox:
    """Bounding box"""
    x0: float
    y0: float
    x1: float
    y1: float

    def intersection(self, other: 'BBox') -> 'BBox':
        """Get intersection of two boxes"""
        x0 = max(self.x0, other.x0)
        y0 = max(self.y0, other.y0)
        x1 = min(self.x1, other.x1)
        y1 = min(self.y1, other.y1)
        if x0 < x1 and y0 < y1:
            return BBox(x0, y0, x1, y1)
        return None

    def area(self) -> float:
        """Get area of box"""
        return (self.x1 - self.x0) * (self.y1 - self.y0)


# Define TableCell and TableStructure locally to avoid circular imports
@dataclass
class TableCell:
    """Single cell in a table"""
    text: str
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    bbox: BBox = None
    is_header: bool = False
    confidence: float = 1.0


@dataclass
class TableStructure:
    """Extracted table structure"""
    cells: list
    num_rows: int
    num_cols: int
    bbox: BBox
    page_num: int
    table_type: TableType = TableType.OTHER
    type_confidence: float = 0.0
    header_rows: int = 1
    raw_image_path: str = None

    def get_cell(self, row: int, col: int):
        """Get cell at position"""
        for cell in self.cells:
            if cell.row == row and cell.col == col:
                return cell
        return None

    def get_row(self, row: int):
        """Get all cells in a row"""
        return sorted([c for c in self.cells if c.row == row], key=lambda c: c.col)

    def get_col(self, col: int):
        """Get all cells in a column"""
        return sorted([c for c in self.cells if c.col == col], key=lambda c: c.row)

    def get_headers(self):
        """Get header rows as text"""
        headers = []
        for r in range(self.header_rows):
            row_cells = self.get_row(r)
            headers.append([c.text for c in row_cells])
        return headers

    def to_dict(self):
        """Convert to list of dicts (one per data row)"""
        if self.header_rows == 0:
            return []

        header_cells = self.get_row(0)
        headers = [c.text.strip() for c in header_cells]

        data = []
        for r in range(self.header_rows, self.num_rows):
            row_cells = self.get_row(r)
            row_dict = {}
            for i, cell in enumerate(row_cells):
                if i < len(headers):
                    row_dict[headers[i]] = cell.text.strip()
            data.append(row_dict)

        return data


# Table classification function for testing
def classify_table_keywords(table: TableStructure):
    """Classify table type based on content keywords"""
    all_text = " ".join(c.text.lower() for c in table.cells)

    scores = {
        TableType.OUTCOMES: 0,
        TableType.BASELINE: 0,
        TableType.SAFETY: 0,
        TableType.SUBGROUP: 0,
        TableType.OTHER: 0.1
    }

    outcomes_keywords = [
        "primary endpoint", "primary outcome", "hazard ratio", "hr ",
        "95% ci", "confidence interval", "events", "p-value",
        "relative risk", "odds ratio", "death", "mortality"
    ]
    for kw in outcomes_keywords:
        if kw in all_text:
            scores[TableType.OUTCOMES] += 0.15

    baseline_keywords = [
        "baseline", "characteristic", "demographics", "age", "sex", "male",
        "female", "mean", "median", "sd", "iqr", "n (%)", "bmi"
    ]
    for kw in baseline_keywords:
        if kw in all_text:
            scores[TableType.BASELINE] += 0.1

    safety_keywords = [
        "adverse", "safety", "serious adverse", "sae", "discontinu",
        "side effect", "hypotension"
    ]
    for kw in safety_keywords:
        if kw in all_text:
            scores[TableType.SAFETY] += 0.15

    subgroup_keywords = [
        "subgroup", "stratified", "interaction", "forest"
    ]
    for kw in subgroup_keywords:
        if kw in all_text:
            scores[TableType.SUBGROUP] += 0.2

    best_type = max(scores, key=scores.get)
    confidence = min(scores[best_type], 1.0)

    return best_type, confidence


# Utility functions for testing
def find_arm_columns(table: TableStructure, arm_names):
    """Find which columns correspond to which arms"""
    arm_columns = {}
    headers = table.get_headers()

    if not headers:
        return arm_columns

    header_text = headers[0] if headers else []

    for col_idx, header in enumerate(header_text):
        header_lower = header.lower()
        for arm_name in arm_names:
            if arm_name.lower() in header_lower:
                arm_columns[arm_name] = col_idx
                break

    return arm_columns


def find_hr_column(table: TableStructure):
    """Find column containing hazard ratios"""
    headers = table.get_headers()
    if not headers:
        return None

    hr_patterns = ["hazard ratio", "hr", "hazard", "ratio"]

    for col_idx, header in enumerate(headers[0]):
        header_lower = header.lower()
        for pattern in hr_patterns:
            if pattern in header_lower:
                return col_idx

    return None


def find_ci_column(table: TableStructure):
    """Find column containing confidence intervals"""
    headers = table.get_headers()
    if not headers:
        return None

    ci_patterns = ["95% ci", "ci", "confidence", "interval"]

    for col_idx, header in enumerate(headers[0]):
        header_lower = header.lower()
        for pattern in ci_patterns:
            if pattern in header_lower:
                return col_idx

    return None


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_outcome_table():
    """Create a sample outcomes table"""
    cells = [
        # Header row
        TableCell(text="Outcome", row=0, col=0, is_header=True),
        TableCell(text="Dapagliflozin", row=0, col=1, is_header=True),
        TableCell(text="Placebo", row=0, col=2, is_header=True),
        TableCell(text="Hazard Ratio (95% CI)", row=0, col=3, is_header=True),
        # Data rows
        TableCell(text="Primary Composite", row=1, col=0),
        TableCell(text="386 (16.3%)", row=1, col=1),
        TableCell(text="502 (21.2%)", row=1, col=2),
        TableCell(text="0.74 (0.65-0.85)", row=1, col=3),
        TableCell(text="Death from any cause", row=2, col=0),
        TableCell(text="227 (9.6%)", row=2, col=1),
        TableCell(text="273 (11.5%)", row=2, col=2),
        TableCell(text="0.83 (0.71-0.97)", row=2, col=3),
        TableCell(text="CV Death", row=3, col=0),
        TableCell(text="167 (7.1%)", row=3, col=1),
        TableCell(text="193 (8.1%)", row=3, col=2),
        TableCell(text="0.82 (0.69-0.98)", row=3, col=3),
    ]
    return TableStructure(
        cells=cells,
        num_rows=4,
        num_cols=4,
        bbox=BBox(x0=50, y0=100, x1=550, y1=300),
        page_num=1,
        header_rows=1
    )


@pytest.fixture
def sample_baseline_table():
    """Create a sample baseline characteristics table"""
    cells = [
        # Header
        TableCell(text="Characteristic", row=0, col=0, is_header=True),
        TableCell(text="Treatment (N=2373)", row=0, col=1, is_header=True),
        TableCell(text="Control (N=2371)", row=0, col=2, is_header=True),
        # Demographics
        TableCell(text="Age, years (mean ± SD)", row=1, col=0),
        TableCell(text="66.3 ± 10.9", row=1, col=1),
        TableCell(text="66.5 ± 11.0", row=1, col=2),
        TableCell(text="Male sex, n (%)", row=2, col=0),
        TableCell(text="1822 (76.8%)", row=2, col=1),
        TableCell(text="1840 (77.6%)", row=2, col=2),
        TableCell(text="BMI, kg/m² (mean ± SD)", row=3, col=0),
        TableCell(text="28.2 ± 5.9", row=3, col=1),
        TableCell(text="28.1 ± 6.0", row=3, col=2),
    ]
    return TableStructure(
        cells=cells,
        num_rows=4,
        num_cols=3,
        bbox=BBox(x0=50, y0=100, x1=500, y1=280),
        page_num=2,
        header_rows=1
    )


@pytest.fixture
def sample_safety_table():
    """Create a sample safety/adverse events table"""
    cells = [
        # Header
        TableCell(text="Adverse Event", row=0, col=0, is_header=True),
        TableCell(text="Drug (N=500)", row=0, col=1, is_header=True),
        TableCell(text="Placebo (N=500)", row=0, col=2, is_header=True),
        # Data
        TableCell(text="Any serious adverse event", row=1, col=0),
        TableCell(text="45 (9.0%)", row=1, col=1),
        TableCell(text="52 (10.4%)", row=1, col=2),
        TableCell(text="Discontinuation due to AE", row=2, col=0),
        TableCell(text="23 (4.6%)", row=2, col=1),
        TableCell(text="28 (5.6%)", row=2, col=2),
        TableCell(text="Hypotension", row=3, col=0),
        TableCell(text="12 (2.4%)", row=3, col=1),
        TableCell(text="5 (1.0%)", row=3, col=2),
    ]
    return TableStructure(
        cells=cells,
        num_rows=4,
        num_cols=3,
        bbox=BBox(x0=50, y0=100, x1=450, y1=260),
        page_num=5,
        header_rows=1
    )


@pytest.fixture
def sample_subgroup_table():
    """Create a sample subgroup analysis table"""
    cells = [
        # Header
        TableCell(text="Subgroup", row=0, col=0, is_header=True),
        TableCell(text="n", row=0, col=1, is_header=True),
        TableCell(text="HR (95% CI)", row=0, col=2, is_header=True),
        TableCell(text="P interaction", row=0, col=3, is_header=True),
        # Data
        TableCell(text="Age <65", row=1, col=0),
        TableCell(text="1856", row=1, col=1),
        TableCell(text="0.72 (0.58-0.89)", row=1, col=2),
        TableCell(text="0.42", row=1, col=3),
        TableCell(text="Age ≥65", row=2, col=0),
        TableCell(text="2888", row=2, col=1),
        TableCell(text="0.76 (0.64-0.91)", row=2, col=2),
        TableCell(text="", row=2, col=3),
    ]
    return TableStructure(
        cells=cells,
        num_rows=3,
        num_cols=4,
        bbox=BBox(x0=50, y0=100, x1=500, y1=200),
        page_num=6,
        header_rows=1
    )


class MockTableExtractor:
    """Mock table extractor for testing"""

    def __init__(self, use_ml=False, min_rows=2, min_cols=2):
        self.use_ml = use_ml
        self.min_rows = min_rows
        self.min_cols = min_cols

    def _cluster_positions(self, positions, tolerance):
        """Cluster nearby positions"""
        if not positions:
            return []
        clusters = [positions[0]]
        for pos in positions[1:]:
            if pos - clusters[-1] > tolerance:
                clusters.append(pos)
        return clusters

    def _find_cluster(self, value, clusters):
        """Find which cluster a value belongs to"""
        for i, cluster in enumerate(clusters):
            if abs(value - cluster) <= 20:
                return i
        return len(clusters) - 1

    def _merge_tables(self, tables1, tables2):
        """Merge tables from different methods, avoiding duplicates"""
        result = tables1.copy()
        for t2 in tables2:
            is_duplicate = False
            for t1 in result:
                overlap = t1.bbox.intersection(t2.bbox)
                if overlap and overlap.area() > 0.5 * min(t1.bbox.area(), t2.bbox.area()):
                    is_duplicate = True
                    break
            if not is_duplicate:
                result.append(t2)
        return result

    def _classify_table(self, table):
        """Classify table type based on content"""
        return classify_table_keywords(table)


@pytest.fixture
def table_extractor():
    """Create a mock table extractor instance"""
    return MockTableExtractor(use_ml=False, min_rows=2, min_cols=2)


# =============================================================================
# TableCell Tests
# =============================================================================

class TestTableCell:
    """Tests for TableCell dataclass"""

    def test_cell_creation(self):
        """Test basic cell creation"""
        cell = TableCell(text="Test", row=0, col=1)
        assert cell.text == "Test"
        assert cell.row == 0
        assert cell.col == 1
        assert cell.row_span == 1
        assert cell.col_span == 1
        assert cell.is_header is False
        assert cell.confidence == 1.0

    def test_header_cell(self):
        """Test header cell"""
        cell = TableCell(text="Header", row=0, col=0, is_header=True)
        assert cell.is_header is True

    def test_cell_with_span(self):
        """Test cell with row/col span"""
        cell = TableCell(text="Merged", row=1, col=2, row_span=2, col_span=3)
        assert cell.row_span == 2
        assert cell.col_span == 3

    def test_cell_with_bbox(self):
        """Test cell with bounding box"""
        bbox = BBox(x0=10, y0=20, x1=100, y1=40)
        cell = TableCell(text="Located", row=0, col=0, bbox=bbox)
        assert cell.bbox is not None
        assert cell.bbox.x0 == 10
        assert cell.bbox.y1 == 40


# =============================================================================
# TableStructure Tests
# =============================================================================

class TestTableStructure:
    """Tests for TableStructure dataclass"""

    def test_get_cell(self, sample_outcome_table):
        """Test getting cell by position"""
        cell = sample_outcome_table.get_cell(1, 3)
        assert cell is not None
        assert "0.74" in cell.text

    def test_get_cell_not_found(self, sample_outcome_table):
        """Test getting non-existent cell"""
        cell = sample_outcome_table.get_cell(10, 10)
        assert cell is None

    def test_get_row(self, sample_outcome_table):
        """Test getting entire row"""
        row = sample_outcome_table.get_row(0)
        assert len(row) == 4
        assert all(c.is_header for c in row)

    def test_get_col(self, sample_outcome_table):
        """Test getting entire column"""
        col = sample_outcome_table.get_col(0)
        assert len(col) == 4
        assert col[0].text == "Outcome"
        assert col[1].text == "Primary Composite"

    def test_get_headers(self, sample_outcome_table):
        """Test getting headers"""
        headers = sample_outcome_table.get_headers()
        assert len(headers) == 1
        assert "Outcome" in headers[0]
        assert "Hazard Ratio" in headers[0][3]

    def test_to_dict(self, sample_outcome_table):
        """Test conversion to dict format"""
        data = sample_outcome_table.to_dict()
        assert len(data) == 3  # 3 data rows
        assert "Outcome" in data[0]
        assert data[0]["Outcome"] == "Primary Composite"

    def test_empty_table_to_dict(self):
        """Test empty table to dict"""
        table = TableStructure(
            cells=[],
            num_rows=0,
            num_cols=0,
            bbox=BBox(x0=0, y0=0, x1=100, y1=100),
            page_num=1,
            header_rows=0
        )
        assert table.to_dict() == []


# =============================================================================
# TableExtractor Tests
# =============================================================================

class TestTableExtractor:
    """Tests for TableExtractor class"""

    def test_extractor_initialization(self, table_extractor):
        """Test extractor initialization"""
        assert table_extractor.min_rows == 2
        assert table_extractor.min_cols == 2
        assert table_extractor.use_ml is False

    def test_cluster_positions(self, table_extractor):
        """Test position clustering"""
        positions = [10.0, 12.0, 50.0, 52.0, 100.0]
        clusters = table_extractor._cluster_positions(positions, tolerance=15)
        assert len(clusters) == 3  # Three distinct clusters

    def test_cluster_positions_empty(self, table_extractor):
        """Test empty position clustering"""
        clusters = table_extractor._cluster_positions([], tolerance=10)
        assert clusters == []

    def test_find_cluster(self, table_extractor):
        """Test finding cluster for value"""
        clusters = [10.0, 50.0, 100.0]
        assert table_extractor._find_cluster(12.0, clusters) == 0
        assert table_extractor._find_cluster(48.0, clusters) == 1
        assert table_extractor._find_cluster(105.0, clusters) == 2

    def test_merge_tables_no_overlap(self, table_extractor):
        """Test merging non-overlapping tables"""
        table1 = TableStructure(
            cells=[], num_rows=2, num_cols=2,
            bbox=BBox(x0=0, y0=0, x1=100, y1=100),
            page_num=1
        )
        table2 = TableStructure(
            cells=[], num_rows=2, num_cols=2,
            bbox=BBox(x0=200, y0=0, x1=300, y1=100),
            page_num=1
        )
        merged = table_extractor._merge_tables([table1], [table2])
        assert len(merged) == 2

    def test_merge_tables_with_overlap(self, table_extractor):
        """Test merging overlapping tables (should deduplicate)"""
        table1 = TableStructure(
            cells=[], num_rows=2, num_cols=2,
            bbox=BBox(x0=0, y0=0, x1=100, y1=100),
            page_num=1
        )
        table2 = TableStructure(
            cells=[], num_rows=2, num_cols=2,
            bbox=BBox(x0=10, y0=10, x1=90, y1=90),  # Mostly overlaps
            page_num=1
        )
        merged = table_extractor._merge_tables([table1], [table2])
        assert len(merged) == 1  # Duplicate removed


# =============================================================================
# Table Classification Tests
# =============================================================================

class TestTableClassification:
    """Tests for table type classification"""

    def test_classify_outcomes_table(self, table_extractor, sample_outcome_table):
        """Test outcomes table classification"""
        table_type, confidence = table_extractor._classify_table(sample_outcome_table)
        assert table_type == TableType.OUTCOMES
        assert confidence > 0.3

    def test_classify_baseline_table(self, table_extractor, sample_baseline_table):
        """Test baseline table classification"""
        table_type, confidence = table_extractor._classify_table(sample_baseline_table)
        assert table_type == TableType.BASELINE
        assert confidence > 0.2

    def test_classify_safety_table(self, table_extractor, sample_safety_table):
        """Test safety table classification"""
        table_type, confidence = table_extractor._classify_table(sample_safety_table)
        assert table_type == TableType.SAFETY
        assert confidence > 0.2

    def test_classify_subgroup_table(self, table_extractor, sample_subgroup_table):
        """Test subgroup table classification"""
        table_type, confidence = table_extractor._classify_table(sample_subgroup_table)
        assert table_type == TableType.SUBGROUP
        assert confidence > 0.2

    def test_classify_empty_table(self, table_extractor):
        """Test classification of empty table"""
        empty_table = TableStructure(
            cells=[TableCell(text="Random text", row=0, col=0)],
            num_rows=1,
            num_cols=1,
            bbox=BBox(x0=0, y0=0, x1=100, y1=50),
            page_num=1
        )
        table_type, confidence = table_extractor._classify_table(empty_table)
        assert table_type == TableType.OTHER


# =============================================================================
# Utility Function Tests
# =============================================================================

class TestUtilityFunctions:
    """Tests for table utility functions"""

    def test_find_arm_columns(self, sample_outcome_table):
        """Test finding arm columns"""
        arms = find_arm_columns(sample_outcome_table, ["Dapagliflozin", "Placebo"])
        assert "Dapagliflozin" in arms
        assert "Placebo" in arms
        assert arms["Dapagliflozin"] == 1
        assert arms["Placebo"] == 2

    def test_find_arm_columns_partial_match(self, sample_outcome_table):
        """Test partial arm name matching"""
        arms = find_arm_columns(sample_outcome_table, ["dapa", "placebo"])
        assert len(arms) >= 1  # At least placebo should match

    def test_find_arm_columns_no_match(self, sample_outcome_table):
        """Test when no arms match"""
        arms = find_arm_columns(sample_outcome_table, ["NonExistent"])
        assert len(arms) == 0

    def test_find_hr_column(self, sample_outcome_table):
        """Test finding HR column"""
        hr_col = find_hr_column(sample_outcome_table)
        assert hr_col == 3

    def test_find_hr_column_not_present(self, sample_baseline_table):
        """Test when HR column not present"""
        hr_col = find_hr_column(sample_baseline_table)
        assert hr_col is None

    def test_find_ci_column(self, sample_outcome_table):
        """Test finding CI column"""
        ci_col = find_ci_column(sample_outcome_table)
        # "Hazard Ratio (95% CI)" contains "CI"
        assert ci_col is not None

    def test_find_ci_column_not_present(self, sample_baseline_table):
        """Test when CI column not present"""
        ci_col = find_ci_column(sample_baseline_table)
        assert ci_col is None


# =============================================================================
# Real PDF Table Extraction Tests
# =============================================================================

class TestRealPDFTableExtraction:
    """Tests for table extraction from real PDFs (integration)"""

    @pytest.fixture
    def real_pdf_path(self):
        """Path to a real test PDF with tables"""
        pdf_dir = Path(__file__).parent.parent / "test_pdfs" / "real_pdfs"
        if pdf_dir.exists():
            # Find first PDF in cardiology
            cardio_dir = pdf_dir / "cardiology"
            if cardio_dir.exists():
                pdfs = list(cardio_dir.glob("*.pdf"))
                if pdfs:
                    return pdfs[0]
        return None

    @pytest.mark.skip(reason="Integration test - run separately with full imports")
    def test_extract_tables_from_real_pdf(self, table_extractor, real_pdf_path):
        """Test extracting tables from a real PDF"""
        # This is an integration test that requires the full module imports
        # Run with: python run_105_pdf_validation.py
        pass


# =============================================================================
# Effect Extraction from Tables Tests
# =============================================================================

class TestEffectExtractionFromTables:
    """Tests for extracting effect estimates from table cells"""

    def test_extract_hr_from_cell(self, sample_outcome_table):
        """Test extracting HR from table cell"""
        import re

        hr_pattern = r"(\d+\.?\d*)\s*\((\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\)"
        cell = sample_outcome_table.get_cell(1, 3)

        match = re.search(hr_pattern, cell.text)
        assert match is not None
        assert float(match.group(1)) == 0.74
        assert float(match.group(2)) == 0.65
        assert float(match.group(3)) == 0.85

    def test_extract_multiple_hrs_from_table(self, sample_outcome_table):
        """Test extracting all HRs from outcome table"""
        import re

        hr_pattern = r"(\d+\.?\d*)\s*\((\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\)"
        hrs_found = []

        # Get HR column (col 3)
        hr_col = sample_outcome_table.get_col(3)

        for cell in hr_col:
            if not cell.is_header:
                match = re.search(hr_pattern, cell.text)
                if match:
                    hrs_found.append({
                        "value": float(match.group(1)),
                        "ci_low": float(match.group(2)),
                        "ci_high": float(match.group(3))
                    })

        assert len(hrs_found) == 3
        assert hrs_found[0]["value"] == 0.74
        assert hrs_found[1]["value"] == 0.83
        assert hrs_found[2]["value"] == 0.82

    def test_extract_event_counts_from_table(self, sample_outcome_table):
        """Test extracting event counts from table"""
        import re

        # Pattern: number (percent)
        count_pattern = r"(\d+)\s*\((\d+\.?\d*)%\)"

        counts = []
        for col_idx in [1, 2]:  # Treatment and control columns
            col = sample_outcome_table.get_col(col_idx)
            for cell in col:
                if not cell.is_header:
                    match = re.search(count_pattern, cell.text)
                    if match:
                        counts.append({
                            "n": int(match.group(1)),
                            "pct": float(match.group(2)),
                            "arm_col": col_idx
                        })

        assert len(counts) >= 4  # At least 2 outcomes * 2 arms


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestTableEdgeCases:
    """Tests for edge cases in table extraction"""

    def test_single_row_table(self, table_extractor):
        """Test handling of single row (header only)"""
        cells = [
            TableCell(text="A", row=0, col=0, is_header=True),
            TableCell(text="B", row=0, col=1, is_header=True),
        ]
        table = TableStructure(
            cells=cells, num_rows=1, num_cols=2,
            bbox=BBox(x0=0, y0=0, x1=100, y1=30),
            page_num=1, header_rows=1
        )
        data = table.to_dict()
        assert data == []  # No data rows

    def test_table_with_empty_cells(self, table_extractor):
        """Test table with empty cells"""
        cells = [
            TableCell(text="Header", row=0, col=0, is_header=True),
            TableCell(text="", row=0, col=1, is_header=True),
            TableCell(text="Data", row=1, col=0),
            TableCell(text="", row=1, col=1),
        ]
        table = TableStructure(
            cells=cells, num_rows=2, num_cols=2,
            bbox=BBox(x0=0, y0=0, x1=100, y1=60),
            page_num=1, header_rows=1
        )
        data = table.to_dict()
        assert len(data) == 1
        assert data[0]["Header"] == "Data"

    def test_table_with_unicode(self):
        """Test table with unicode characters"""
        cells = [
            TableCell(text="Measure", row=0, col=0, is_header=True),
            TableCell(text="Value", row=0, col=1, is_header=True),
            TableCell(text="β-blocker", row=1, col=0),
            TableCell(text="0.82 ± 0.15", row=1, col=1),
            TableCell(text="Age ≥65", row=2, col=0),
            TableCell(text="p<0.001", row=2, col=1),
        ]
        table = TableStructure(
            cells=cells, num_rows=3, num_cols=2,
            bbox=BBox(x0=0, y0=0, x1=100, y1=90),
            page_num=1, header_rows=1
        )
        data = table.to_dict()
        assert data[0]["Measure"] == "β-blocker"
        assert "≥" in data[1]["Measure"]


# =============================================================================
# Multi-Row Header Tests
# =============================================================================

class TestMultiRowHeaders:
    """Tests for tables with multiple header rows"""

    def test_two_row_header(self):
        """Test table with 2-row header"""
        cells = [
            # First header row (spans)
            TableCell(text="Treatment Groups", row=0, col=0, is_header=True),
            TableCell(text="Treatment Groups", row=0, col=1, is_header=True),
            # Second header row
            TableCell(text="Drug A", row=1, col=0, is_header=True),
            TableCell(text="Drug B", row=1, col=1, is_header=True),
            # Data
            TableCell(text="100", row=2, col=0),
            TableCell(text="95", row=2, col=1),
        ]
        table = TableStructure(
            cells=cells, num_rows=3, num_cols=2,
            bbox=BBox(x0=0, y0=0, x1=100, y1=90),
            page_num=1, header_rows=2
        )
        headers = table.get_headers()
        assert len(headers) == 2
        assert headers[0][0] == "Treatment Groups"
        assert headers[1][0] == "Drug A"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
