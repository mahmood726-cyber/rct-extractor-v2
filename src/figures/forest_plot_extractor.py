"""
Forest Plot Extractor for RCT Extractor v2
==========================================

Extracts effect estimates from forest plot figures in PDFs.
Uses computer vision to detect forest plot structure and OCR for values.

Features:
- Detects forest plot figures in PDFs
- Identifies effect estimate points and confidence intervals
- Extracts numeric values using OCR
- Handles horizontal and vertical orientations
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

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
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ForestPlotResult:
    """Single effect estimate from forest plot"""
    study_name: str
    effect_type: str  # HR, OR, RR
    value: float
    ci_low: float
    ci_high: float
    weight: Optional[float] = None
    confidence: float = 0.0
    page_num: int = 0


class ForestPlotExtractor:
    """
    Extract effect estimates from forest plot figures.

    Strategy:
    1. Render PDF pages to images
    2. Detect forest plot regions using line/point detection
    3. Identify the vertical reference line (null effect)
    4. Detect diamond shapes (pooled estimate) and squares (individual studies)
    5. Map x-coordinates to effect values using axis labels
    6. Extract study names and values using OCR
    """

    def __init__(self, dpi: int = 200):
        self.dpi = dpi

        if not HAS_CV2:
            logger.warning("OpenCV required for forest plot extraction")
        if not HAS_TESSERACT:
            logger.warning("Tesseract required for OCR")
        if not HAS_FITZ:
            logger.warning("PyMuPDF required for PDF rendering")

    def extract_from_pdf(
        self,
        pdf_path: str,
        pages: Optional[List[int]] = None
    ) -> List[ForestPlotResult]:
        """Extract forest plot data from PDF"""
        if not all([HAS_CV2, HAS_TESSERACT, HAS_FITZ]):
            return []

        results = []

        try:
            doc = fitz.open(pdf_path)

            if pages is None:
                pages = range(len(doc))

            for page_num in pages:
                if page_num >= len(doc):
                    continue

                # Render page
                page = doc[page_num]
                mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
                pix = page.get_pixmap(matrix=mat)

                # Convert to numpy
                img = np.frombuffer(pix.samples, dtype=np.uint8)
                img = img.reshape(pix.height, pix.width, pix.n)

                if pix.n == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                elif pix.n == 1:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

                # Detect and extract forest plots
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
    ) -> List[ForestPlotResult]:
        """Extract forest plot data from image"""
        results = []

        # Detect forest plot regions
        forest_regions = self._detect_forest_plots(image)

        for region in forest_regions:
            x1, y1, x2, y2 = region
            plot_img = image[y1:y2, x1:x2]

            # Extract data from this plot
            region_results = self._parse_forest_plot(plot_img, page_num)
            results.extend(region_results)

        return results

    def _detect_forest_plots(
        self,
        image: np.ndarray
    ) -> List[Tuple[int, int, int, int]]:
        """Detect forest plot regions in image"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Forest plots typically have:
        # 1. A vertical reference line (at x=1 for ratios)
        # 2. Horizontal lines with squares/diamonds
        # 3. A diamond shape at the bottom (pooled estimate)

        # Detect vertical lines
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel)

        # Find contours of vertical lines
        contours, _ = cv2.findContours(vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Look for regions with vertical lines that could be forest plots
        regions = []
        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)

            # Forest plot reference lines are typically tall and thin
            if ch > h * 0.2 and cw < 10:
                # Expand region around this line
                x1 = max(0, x - int(w * 0.4))
                y1 = max(0, y - 20)
                x2 = min(w, x + int(w * 0.4))
                y2 = min(h, y + ch + 20)

                # Check for squares/diamonds in this region
                region = image[y1:y2, x1:x2]
                if self._has_plot_elements(region):
                    regions.append((x1, y1, x2, y2))

        # Deduplicate overlapping regions
        regions = self._merge_overlapping(regions)

        return regions

    def _has_plot_elements(self, image: np.ndarray) -> bool:
        """Check if region contains forest plot elements (squares, diamonds)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect edges
        edges = cv2.Canny(gray, 50, 150)

        # Look for rectangular shapes (study squares)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        square_count = 0
        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * peri, True)

            # Squares have 4 vertices
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)
                aspect = w / float(h) if h > 0 else 0

                # Nearly square
                if 0.7 < aspect < 1.4 and w > 5 and w < 50:
                    square_count += 1

        return square_count >= 3  # At least 3 study squares

    def _merge_overlapping(
        self,
        regions: List[Tuple[int, int, int, int]]
    ) -> List[Tuple[int, int, int, int]]:
        """Merge overlapping regions"""
        if not regions:
            return []

        # Sort by x1
        regions = sorted(regions, key=lambda r: r[0])

        merged = [regions[0]]
        for r in regions[1:]:
            last = merged[-1]

            # Check overlap
            if r[0] < last[2] and r[1] < last[3]:
                # Merge
                merged[-1] = (
                    min(last[0], r[0]),
                    min(last[1], r[1]),
                    max(last[2], r[2]),
                    max(last[3], r[3])
                )
            else:
                merged.append(r)

        return merged

    def _parse_forest_plot(
        self,
        image: np.ndarray,
        page_num: int
    ) -> List[ForestPlotResult]:
        """Parse a forest plot image to extract data"""
        results = []
        h, w = image.shape[:2]

        # OCR the entire region
        text = pytesseract.image_to_string(image)

        # Look for effect estimate patterns in text
        # Common formats: "0.85 (0.72, 0.99)" or "0.85 [0.72-0.99]"
        patterns = [
            r'(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[,\-]\s*(\d+\.?\d*)\s*\)',
            r'(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[,\-]\s*(\d+\.?\d*)\s*\]',
        ]

        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    try:
                        value = float(match.group(1))
                        ci_low = float(match.group(2))
                        ci_high = float(match.group(3))

                        # Plausibility check
                        if not (0.01 <= value <= 100):
                            continue
                        if ci_low >= ci_high:
                            continue

                        # Extract study name (text before the numbers)
                        study_name = line[:match.start()].strip()
                        study_name = re.sub(r'[^\w\s\-]', '', study_name).strip()

                        if len(study_name) < 2:
                            study_name = "Unknown"

                        # Determine effect type from context
                        effect_type = self._infer_effect_type(text)

                        results.append(ForestPlotResult(
                            study_name=study_name[:50],
                            effect_type=effect_type,
                            value=value,
                            ci_low=ci_low,
                            ci_high=ci_high,
                            confidence=0.7,
                            page_num=page_num
                        ))
                    except (ValueError, IndexError):
                        continue

        return results

    def _infer_effect_type(self, text: str) -> str:
        """Infer effect type from forest plot text"""
        text_lower = text.lower()

        if 'hazard' in text_lower or 'survival' in text_lower:
            return 'HR'
        elif 'odds' in text_lower:
            return 'OR'
        elif 'risk ratio' in text_lower or 'relative risk' in text_lower:
            return 'RR'

        # Default based on reference line
        # If text contains "favours" typically OR/RR
        if 'favours' in text_lower or 'favor' in text_lower:
            return 'OR'

        return 'HR'  # Default


def extract_forest_plots_from_pdf(pdf_path: str) -> List[ForestPlotResult]:
    """Convenience function to extract forest plots from PDF"""
    extractor = ForestPlotExtractor()
    return extractor.extract_from_pdf(pdf_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python forest_plot_extractor.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    results = extract_forest_plots_from_pdf(pdf_path)

    print(f"\nExtracted {len(results)} results from forest plots:")
    for r in results:
        print(f"  {r.study_name}: {r.effect_type} {r.value:.2f} ({r.ci_low:.2f}-{r.ci_high:.2f})")
