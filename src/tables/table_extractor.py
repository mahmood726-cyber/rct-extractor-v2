"""
Table Extraction Module
Detects, classifies, and extracts tables from PDFs.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import re
import logging

from ..core.models import TableType, Provenance, BoundingBox
from ..pdf.pdf_parser import PDFContent, PageContent, TextBlock, BBox

logger = logging.getLogger(__name__)

# Optional imports
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from transformers import TableTransformerForObjectDetection, DetrImageProcessor
    import torch
    from PIL import Image
    HAS_TABLE_TRANSFORMER = True
except ImportError:
    HAS_TABLE_TRANSFORMER = False
    logger.info("Table Transformer not available. Using fallback methods.")


@dataclass
class TableCell:
    """Single cell in a table"""
    text: str
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    bbox: Optional[BBox] = None
    is_header: bool = False
    confidence: float = 1.0


@dataclass
class TableStructure:
    """Extracted table structure"""
    cells: List[TableCell]
    num_rows: int
    num_cols: int
    bbox: BBox
    page_num: int
    table_type: TableType = TableType.OTHER
    type_confidence: float = 0.0
    header_rows: int = 1
    raw_image_path: Optional[str] = None

    def get_cell(self, row: int, col: int) -> Optional[TableCell]:
        """Get cell at position"""
        for cell in self.cells:
            if cell.row == row and cell.col == col:
                return cell
        return None

    def get_row(self, row: int) -> List[TableCell]:
        """Get all cells in a row"""
        return sorted([c for c in self.cells if c.row == row], key=lambda c: c.col)

    def get_col(self, col: int) -> List[TableCell]:
        """Get all cells in a column"""
        return sorted([c for c in self.cells if c.col == col], key=lambda c: c.row)

    def get_headers(self) -> List[List[str]]:
        """Get header rows as text"""
        headers = []
        for r in range(self.header_rows):
            row_cells = self.get_row(r)
            headers.append([c.text for c in row_cells])
        return headers

    def to_dict(self) -> List[Dict[str, str]]:
        """Convert to list of dicts (one per data row)"""
        if self.header_rows == 0:
            return []

        # Get header names
        header_cells = self.get_row(0)
        headers = [c.text.strip() for c in header_cells]

        # Get data rows
        data = []
        for r in range(self.header_rows, self.num_rows):
            row_cells = self.get_row(r)
            row_dict = {}
            for i, cell in enumerate(row_cells):
                if i < len(headers):
                    row_dict[headers[i]] = cell.text.strip()
            data.append(row_dict)

        return data


class TableExtractor:
    """
    Extract tables from PDF pages.

    Strategy:
    1. Try pdfplumber's table detection (best for born-digital)
    2. Fall back to Table Transformer (ML-based) for complex layouts
    3. Use heuristic detection as last resort
    """

    def __init__(self, use_ml: bool = True, min_rows: int = 2, min_cols: int = 2):
        self.use_ml = use_ml and HAS_TABLE_TRANSFORMER
        self.min_rows = min_rows
        self.min_cols = min_cols

        if self.use_ml:
            self._load_table_transformer()

    def _load_table_transformer(self):
        """Load Table Transformer model"""
        try:
            self.processor = DetrImageProcessor.from_pretrained(
                "microsoft/table-transformer-detection"
            )
            self.model = TableTransformerForObjectDetection.from_pretrained(
                "microsoft/table-transformer-detection"
            )
            self.model.eval()
            logger.info("Table Transformer loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load Table Transformer: {e}")
            self.use_ml = False

    def extract_tables(self, pdf_path: str, page_content: PageContent) -> List[TableStructure]:
        """Extract all tables from a page"""
        tables = []

        # Method 1: pdfplumber (best for digital PDFs)
        if HAS_PDFPLUMBER:
            try:
                pdfplumber_tables = self._extract_with_pdfplumber(pdf_path, page_content.page_num)
                tables.extend(pdfplumber_tables)
            except Exception as e:
                logger.warning(f"pdfplumber table extraction failed: {e}")

        # Method 2: ML-based detection
        if self.use_ml and page_content.image_path:
            try:
                ml_tables = self._extract_with_transformer(page_content.image_path, page_content)
                # Merge with existing tables (avoid duplicates)
                tables = self._merge_tables(tables, ml_tables)
            except Exception as e:
                logger.warning(f"ML table extraction failed: {e}")

        # Method 3: Heuristic fallback
        if not tables:
            heuristic_tables = self._extract_with_heuristics(page_content)
            tables.extend(heuristic_tables)

        # Classify each table
        for table in tables:
            table.table_type, table.type_confidence = self._classify_table(table)

        return tables

    def _extract_with_pdfplumber(self, pdf_path: str, page_num: int) -> List[TableStructure]:
        """Extract tables using pdfplumber"""
        tables = []

        with pdfplumber.open(pdf_path) as pdf:
            if page_num > len(pdf.pages):
                return tables

            page = pdf.pages[page_num - 1]

            # Find tables
            found_tables = page.find_tables()

            for i, table_obj in enumerate(found_tables):
                # Extract table data
                table_data = table_obj.extract()
                if not table_data or len(table_data) < self.min_rows:
                    continue

                # Get bounding box
                bbox = table_obj.bbox
                table_bbox = BBox(x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3])

                # Convert to cells
                cells = []
                num_cols = max(len(row) for row in table_data) if table_data else 0

                for row_idx, row in enumerate(table_data):
                    for col_idx, cell_text in enumerate(row):
                        cell = TableCell(
                            text=cell_text or "",
                            row=row_idx,
                            col=col_idx,
                            is_header=(row_idx == 0)
                        )
                        cells.append(cell)

                table = TableStructure(
                    cells=cells,
                    num_rows=len(table_data),
                    num_cols=num_cols,
                    bbox=table_bbox,
                    page_num=page_num
                )
                tables.append(table)

        return tables

    def _extract_with_transformer(self, image_path: str, page_content: PageContent) -> List[TableStructure]:
        """Extract tables using Table Transformer"""
        tables = []

        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")

        with torch.no_grad():
            outputs = self.model(**inputs)

        # Post-process
        target_sizes = torch.tensor([image.size[::-1]])
        results = self.processor.post_process_object_detection(
            outputs, threshold=0.7, target_sizes=target_sizes
        )[0]

        for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
            if self.model.config.id2label[label.item()] == "table":
                x0, y0, x1, y1 = box.tolist()

                # Scale back to PDF coordinates
                scale_x = page_content.width / image.width
                scale_y = page_content.height / image.height

                table_bbox = BBox(
                    x0=x0 * scale_x,
                    y0=y0 * scale_y,
                    x1=x1 * scale_x,
                    y1=y1 * scale_y
                )

                # Get text blocks within table region
                table_blocks = [
                    b for b in page_content.text_blocks
                    if table_bbox.intersection(b.bbox) is not None
                ]

                # Convert to grid structure (simplified)
                cells, num_rows, num_cols = self._blocks_to_grid(table_blocks)

                if num_rows >= self.min_rows and num_cols >= self.min_cols:
                    table = TableStructure(
                        cells=cells,
                        num_rows=num_rows,
                        num_cols=num_cols,
                        bbox=table_bbox,
                        page_num=page_content.page_num,
                        confidence=score.item()
                    )
                    tables.append(table)

        return tables

    def _extract_with_heuristics(self, page_content: PageContent) -> List[TableStructure]:
        """Heuristic table detection based on text alignment"""
        tables = []

        # Group blocks by y-position (rows)
        y_groups = {}
        y_tolerance = 5.0

        for block in page_content.text_blocks:
            y_center = (block.bbox.y0 + block.bbox.y1) / 2
            found_group = False
            for y_key in y_groups:
                if abs(y_center - y_key) <= y_tolerance:
                    y_groups[y_key].append(block)
                    found_group = True
                    break
            if not found_group:
                y_groups[y_center] = [block]

        # Find rows with multiple aligned columns (potential table)
        aligned_rows = []
        for y_key, blocks in sorted(y_groups.items()):
            if len(blocks) >= self.min_cols:
                aligned_rows.append((y_key, blocks))

        # Group consecutive aligned rows into tables
        if len(aligned_rows) >= self.min_rows:
            # Simple: treat all aligned rows as one table
            all_blocks = []
            for _, blocks in aligned_rows:
                all_blocks.extend(blocks)

            if all_blocks:
                min_x = min(b.bbox.x0 for b in all_blocks)
                min_y = min(b.bbox.y0 for b in all_blocks)
                max_x = max(b.bbox.x1 for b in all_blocks)
                max_y = max(b.bbox.y1 for b in all_blocks)

                cells, num_rows, num_cols = self._blocks_to_grid(all_blocks)

                table = TableStructure(
                    cells=cells,
                    num_rows=num_rows,
                    num_cols=num_cols,
                    bbox=BBox(x0=min_x, y0=min_y, x1=max_x, y1=max_y),
                    page_num=page_content.page_num
                )
                tables.append(table)

        return tables

    def _blocks_to_grid(self, blocks: List[TextBlock]) -> Tuple[List[TableCell], int, int]:
        """Convert text blocks to grid cells"""
        if not blocks:
            return [], 0, 0

        # Find unique y positions (rows) and x positions (columns)
        y_positions = sorted(set((b.bbox.y0 + b.bbox.y1) / 2 for b in blocks))
        x_positions = sorted(set(b.bbox.x0 for b in blocks))

        # Cluster similar positions
        y_clusters = self._cluster_positions(y_positions, tolerance=10)
        x_clusters = self._cluster_positions(x_positions, tolerance=20)

        # Assign each block to a cell
        cells = []
        for block in blocks:
            y_center = (block.bbox.y0 + block.bbox.y1) / 2
            row = self._find_cluster(y_center, y_clusters)
            col = self._find_cluster(block.bbox.x0, x_clusters)

            cell = TableCell(
                text=block.text,
                row=row,
                col=col,
                bbox=block.bbox,
                is_header=(row == 0)
            )
            cells.append(cell)

        num_rows = len(y_clusters)
        num_cols = len(x_clusters)

        return cells, num_rows, num_cols

    def _cluster_positions(self, positions: List[float], tolerance: float) -> List[float]:
        """Cluster nearby positions"""
        if not positions:
            return []

        clusters = [positions[0]]
        for pos in positions[1:]:
            if pos - clusters[-1] > tolerance:
                clusters.append(pos)

        return clusters

    def _find_cluster(self, value: float, clusters: List[float]) -> int:
        """Find which cluster a value belongs to"""
        for i, cluster in enumerate(clusters):
            if abs(value - cluster) <= 20:  # tolerance
                return i
        return len(clusters) - 1

    def _merge_tables(self, tables1: List[TableStructure], tables2: List[TableStructure]) -> List[TableStructure]:
        """Merge tables from different methods, avoiding duplicates"""
        result = tables1.copy()

        for t2 in tables2:
            is_duplicate = False
            for t1 in result:
                # Check for significant overlap
                overlap = t1.bbox.intersection(t2.bbox)
                if overlap and overlap.area() > 0.5 * min(t1.bbox.area(), t2.bbox.area()):
                    is_duplicate = True
                    break
            if not is_duplicate:
                result.append(t2)

        return result

    def _classify_table(self, table: TableStructure) -> Tuple[TableType, float]:
        """Classify table type based on content"""
        # Get all text in table
        all_text = " ".join(c.text.lower() for c in table.cells)
        headers = " ".join(c.text.lower() for c in table.cells if c.is_header)

        # Classification rules
        scores = {
            TableType.OUTCOMES: 0,
            TableType.BASELINE: 0,
            TableType.SAFETY: 0,
            TableType.SUBGROUP: 0,
            TableType.OTHER: 0.1  # Default
        }

        # OUTCOMES indicators
        outcomes_keywords = [
            "primary endpoint", "primary outcome", "hazard ratio", "hr ",
            "95% ci", "confidence interval", "events", "p-value", "p value",
            "relative risk", "odds ratio", "death", "mortality", "hospitalization",
            "mace", "composite", "time to", "incidence"
        ]
        for kw in outcomes_keywords:
            if kw in all_text:
                scores[TableType.OUTCOMES] += 0.15

        # BASELINE indicators
        baseline_keywords = [
            "baseline", "characteristic", "demographics", "age", "sex", "male",
            "female", "mean", "median", "sd", "iqr", "n (%)", "bmi", "weight",
            "race", "ethnicity", "history", "prior", "nyha", "ef", "egfr"
        ]
        for kw in baseline_keywords:
            if kw in all_text:
                scores[TableType.BASELINE] += 0.1

        # SAFETY indicators
        safety_keywords = [
            "adverse", "safety", "serious adverse", "sae", "discontinu",
            "side effect", "tolerability", "bleeding", "renal", "hypotension"
        ]
        for kw in safety_keywords:
            if kw in all_text:
                scores[TableType.SAFETY] += 0.15

        # SUBGROUP indicators
        subgroup_keywords = [
            "subgroup", "stratified", "interaction", "forest", "prespecified"
        ]
        for kw in subgroup_keywords:
            if kw in all_text:
                scores[TableType.SUBGROUP] += 0.2

        # Get best classification
        best_type = max(scores, key=scores.get)
        confidence = min(scores[best_type], 1.0)

        return best_type, confidence


# ============================================================
# TABLE ANALYSIS UTILITIES
# ============================================================

def find_arm_columns(table: TableStructure, arm_names: List[str]) -> Dict[str, int]:
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


def find_hr_column(table: TableStructure) -> Optional[int]:
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


def find_ci_column(table: TableStructure) -> Optional[int]:
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
