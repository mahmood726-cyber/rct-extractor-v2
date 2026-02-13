"""
Results Table Extractor for RCT Extractor v2
=============================================

STATUS: ORPHANED — This module is never imported by production code.
The main extraction pipeline (enhanced_extractor_v3.py) handles table
text inline. Consider integrating or removing.

Extracts effect estimates (HR, OR, RR, RD, MD) from tables in PDF documents
using OCR and structural analysis.

Features:
- PDF table detection using heuristics or YOLOv8
- OCR with Tesseract
- Pattern matching for effect estimates within tables
- Multi-column alignment for treatment vs control

Dependencies:
- pytesseract (pip install pytesseract)
- opencv-python (pip install opencv-python)
- pdf2image (pip install pdf2image) or PyMuPDF (pip install PyMuPDF)

Author: RCT Extractor v2 Team
Version: 1.0.0
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

import numpy as np

# Conditional imports
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TableCell:
    """Represents a single table cell"""
    text: str
    row: int
    col: int
    bbox: Tuple[int, int, int, int] = None  # x1, y1, x2, y2
    confidence: float = 0.0


@dataclass
class ExtractedResult:
    """Extracted effect estimate from table"""
    measure_type: str  # HR, OR, RR, RD, MD
    value: float
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    outcome: Optional[str] = None
    comparison: Optional[str] = None
    source: str = "table"
    confidence: float = 0.0
    raw_text: str = ""
    page_num: int = 0


class ResultsTableExtractor:
    """
    Extract effect estimates from tables in PDF documents.

    Strategy:
    1. Convert PDF pages to images
    2. Detect table regions using line detection
    3. Extract text using OCR
    4. Parse cells for effect estimates using regex patterns
    5. Align results with outcome/treatment columns
    """

    # Patterns for effect estimates in tables
    HR_TABLE_PATTERNS = [
        # "0.74 (0.65-0.85)" format
        r'(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)\s*\)',
        # "0.74 [0.65, 0.85]" bracket format
        r'(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[,;]\s*(\d+\.?\d*)\s*\]',
        # "0.74 (0.65, 0.85)" comma format
        r'(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)',
    ]

    # Keywords indicating HR/OR columns
    COLUMN_KEYWORDS = {
        'HR': ['hazard', 'hr', 'hazard ratio'],
        'OR': ['odds', 'or', 'odds ratio'],
        'RR': ['risk ratio', 'rr', 'relative risk'],
        'RD': ['risk difference', 'rd', 'absolute'],
        'MD': ['mean diff', 'md', 'difference', 'mean'],
        'CI': ['ci', 'confidence', '95%', '95 %'],
    }

    # Keywords indicating outcome rows
    OUTCOME_KEYWORDS = [
        'primary', 'secondary', 'endpoint', 'outcome',
        'death', 'mortality', 'survival', 'progression',
        'response', 'event', 'composite'
    ]

    def __init__(self, dpi: int = 300):
        """
        Initialize the extractor.

        Args:
            dpi: DPI for PDF rasterization
        """
        self.dpi = dpi

        if not HAS_CV2:
            logger.warning("OpenCV not available - table detection disabled")
        if not HAS_TESSERACT:
            logger.warning("Tesseract not available - OCR disabled")
        if not HAS_FITZ:
            logger.warning("PyMuPDF not available - PDF rendering disabled")

    def extract_from_pdf(
        self,
        pdf_path: str,
        pages: Optional[List[int]] = None
    ) -> List[ExtractedResult]:
        """
        Extract effect estimates from tables in PDF.

        Args:
            pdf_path: Path to PDF file
            pages: Optional list of page numbers (0-indexed)

        Returns:
            List of extracted results
        """
        if not HAS_FITZ:
            logger.error("PyMuPDF required for PDF processing")
            return []

        results = []

        try:
            doc = fitz.open(pdf_path)

            if pages is None:
                pages = range(len(doc))

            for page_num in pages:
                if page_num >= len(doc):
                    continue

                # Render page to image
                page = doc[page_num]
                mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
                pix = page.get_pixmap(matrix=mat)

                # Convert to numpy array
                img = np.frombuffer(pix.samples, dtype=np.uint8)
                img = img.reshape(pix.height, pix.width, pix.n)

                if pix.n == 4:  # RGBA
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                elif pix.n == 1:  # Grayscale
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

                # Extract from this page
                page_results = self._extract_from_image(img, page_num)
                results.extend(page_results)

            doc.close()

        except Exception as e:
            logger.error(f"Error processing PDF: {e}")

        return results

    def _extract_from_image(
        self,
        image: np.ndarray,
        page_num: int = 0
    ) -> List[ExtractedResult]:
        """
        Extract effect estimates from a page image.

        Args:
            image: BGR image
            page_num: Page number for reference

        Returns:
            List of extracted results
        """
        if not HAS_CV2 or not HAS_TESSERACT:
            return []

        results = []

        # Step 1: Detect table regions
        table_regions = self._detect_tables(image)

        for region in table_regions:
            x1, y1, x2, y2 = region
            table_img = image[y1:y2, x1:x2]

            # Step 2: Extract text with position
            cells = self._extract_cells(table_img)

            # Step 3: Parse for effect estimates
            region_results = self._parse_table(cells, page_num)
            results.extend(region_results)

        # Also try full-page OCR for inline tables
        full_text = pytesseract.image_to_string(image)
        inline_results = self._parse_inline_text(full_text, page_num)
        results.extend(inline_results)

        return results

    def _detect_tables(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect table regions in image using line detection.

        Returns:
            List of bounding boxes (x1, y1, x2, y2)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect horizontal and vertical lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

        # Threshold
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        # Detect lines
        horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel)
        vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel)

        # Combine
        table_mask = cv2.add(horizontal, vertical)

        # Find contours
        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions = []
        h, w = image.shape[:2]
        min_area = (h * w) * 0.01  # At least 1% of image

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                x, y, cw, ch = cv2.boundingRect(contour)
                # Expand slightly
                x1 = max(0, x - 10)
                y1 = max(0, y - 10)
                x2 = min(w, x + cw + 10)
                y2 = min(h, y + ch + 10)
                regions.append((x1, y1, x2, y2))

        # If no tables detected, try heuristic regions
        if not regions:
            # Common table locations: middle and bottom of page
            regions = [
                (0, int(h * 0.3), w, int(h * 0.7)),  # Middle
                (0, int(h * 0.5), w, h),  # Bottom half
            ]

        return regions

    def _extract_cells(self, table_img: np.ndarray) -> List[TableCell]:
        """
        Extract cells from table image using OCR.

        Returns:
            List of TableCell objects
        """
        cells = []

        # Get OCR data with bounding boxes
        data = pytesseract.image_to_data(table_img, output_type=pytesseract.Output.DICT)

        current_row = -1
        current_col = 0
        last_top = -1

        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if not text:
                continue

            x = data['left'][i]
            y = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]
            conf = data['conf'][i]

            # Determine row based on vertical position
            if last_top < 0 or abs(y - last_top) > 20:
                current_row += 1
                current_col = 0
            else:
                current_col += 1

            last_top = y

            cells.append(TableCell(
                text=text,
                row=current_row,
                col=current_col,
                bbox=(x, y, x + w, y + h),
                confidence=conf / 100.0
            ))

        return cells

    def _parse_table(
        self,
        cells: List[TableCell],
        page_num: int
    ) -> List[ExtractedResult]:
        """
        Parse table cells for effect estimates.
        """
        results = []

        # Group cells by row
        rows = {}
        for cell in cells:
            if cell.row not in rows:
                rows[cell.row] = []
            rows[cell.row].append(cell)

        # Find header row to identify columns
        header_row = None
        hr_col = None
        ci_col = None

        for row_idx, row_cells in rows.items():
            row_text = ' '.join(c.text.lower() for c in row_cells)

            # Check for HR/OR column headers
            for measure, keywords in self.COLUMN_KEYWORDS.items():
                for kw in keywords:
                    if kw in row_text:
                        header_row = row_idx
                        # Find column index
                        for i, cell in enumerate(row_cells):
                            if kw in cell.text.lower():
                                if measure in ['HR', 'OR', 'RR', 'RD', 'MD']:
                                    hr_col = i
                                elif measure == 'CI':
                                    ci_col = i

        # Parse data rows
        for row_idx, row_cells in rows.items():
            if header_row is not None and row_idx <= header_row:
                continue

            row_text = ' '.join(c.text for c in row_cells)

            # Try to extract effect estimates
            for pattern in self.HR_TABLE_PATTERNS:
                match = re.search(pattern, row_text)
                if match:
                    try:
                        value = float(match.group(1))
                        ci_low = float(match.group(2))
                        ci_high = float(match.group(3))

                        # Determine measure type from context
                        measure_type = self._infer_measure_type(row_text)

                        # Get outcome name from first column
                        outcome = row_cells[0].text if row_cells else None

                        results.append(ExtractedResult(
                            measure_type=measure_type,
                            value=value,
                            ci_low=ci_low,
                            ci_high=ci_high,
                            outcome=outcome,
                            source="table",
                            confidence=0.8,
                            raw_text=row_text,
                            page_num=page_num
                        ))
                    except (ValueError, IndexError):
                        continue

        return results

    def _parse_inline_text(
        self,
        text: str,
        page_num: int
    ) -> List[ExtractedResult]:
        """
        Parse full-page text for effect estimates not in formal tables.
        """
        results = []

        # Look for patterns with measure type context
        patterns = [
            (r'hazard\s*ratio[,:\s]*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)\s*\)', 'HR'),
            (r'odds\s*ratio[,:\s]*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)\s*\)', 'OR'),
            (r'risk\s*ratio[,:\s]*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)\s*\)', 'RR'),
        ]

        for pattern, measure_type in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = float(match.group(1))
                    ci_low = float(match.group(2))
                    ci_high = float(match.group(3))

                    results.append(ExtractedResult(
                        measure_type=measure_type,
                        value=value,
                        ci_low=ci_low,
                        ci_high=ci_high,
                        source="inline_text",
                        confidence=0.7,
                        raw_text=match.group(0),
                        page_num=page_num
                    ))
                except (ValueError, IndexError):
                    continue

        return results

    def _infer_measure_type(self, text: str) -> str:
        """Infer measure type from context text."""
        text_lower = text.lower()

        if any(kw in text_lower for kw in ['hazard', 'survival', 'time-to']):
            return 'HR'
        elif any(kw in text_lower for kw in ['odds', 'logistic']):
            return 'OR'
        elif any(kw in text_lower for kw in ['risk ratio', 'relative risk']):
            return 'RR'
        elif any(kw in text_lower for kw in ['risk difference', 'absolute']):
            return 'RD'
        elif any(kw in text_lower for kw in ['mean diff', 'change from']):
            return 'MD'

        # Default to HR (most common)
        return 'HR'


def main():
    """Test the table extractor."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python results_table_extractor.py <pdf_path>")
        return

    pdf_path = sys.argv[1]

    extractor = ResultsTableExtractor()
    results = extractor.extract_from_pdf(pdf_path)

    print(f"\nExtracted {len(results)} results from {pdf_path}:")
    for r in results:
        print(f"  {r.measure_type}: {r.value} ({r.ci_low}-{r.ci_high}) - {r.outcome}")


if __name__ == "__main__":
    main()
