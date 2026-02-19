"""
PDF Parser - Extract text and structure from PDFs.
Handles born-digital and scanned (OCR) PDFs with fallback.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
import io
import tempfile
import logging

logger = logging.getLogger(__name__)

# Optional imports with graceful fallback
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logger.warning("PyMuPDF not installed. Install with: pip install pymupdf")

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    logger.warning("pdfplumber not installed. Install with: pip install pdfplumber")

try:
    from PIL import Image
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    logger.warning("OCR dependencies not installed. Install with: pip install pytesseract pillow")


@dataclass
class BBox:
    """Bounding box in PDF coordinates"""
    x0: float
    y0: float
    x1: float
    y1: float

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)

    def area(self) -> float:
        return (self.x1 - self.x0) * (self.y1 - self.y0)

    def intersection(self, other: 'BBox') -> Optional['BBox']:
        """Get intersection of two bboxes"""
        x0 = max(self.x0, other.x0)
        y0 = max(self.y0, other.y0)
        x1 = min(self.x1, other.x1)
        y1 = min(self.y1, other.y1)
        if x0 < x1 and y0 < y1:
            return BBox(x0, y0, x1, y1)
        return None


@dataclass
class TextBlock:
    """Block of text with position"""
    text: str
    bbox: BBox
    page_num: int
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    is_bold: bool = False
    line_num: Optional[int] = None
    block_type: str = "text"  # text, heading, table_cell, etc.
    confidence: float = 1.0  # OCR confidence if applicable


@dataclass
class PageContent:
    """All content from a single page"""
    page_num: int
    width: float
    height: float
    text_blocks: List[TextBlock] = field(default_factory=list)
    full_text: str = ""
    image_path: Optional[str] = None  # Path to page image for debugging/review
    is_ocr: bool = False
    ocr_confidence: Optional[float] = None


@dataclass
class PDFContent:
    """Complete parsed PDF content"""
    file_path: str
    num_pages: int
    pages: List[PageContent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    extraction_method: str = "unknown"
    is_born_digital: bool = True


class PDFParser:
    """
    Main PDF parser with fallback strategies.

    Strategy:
    1. Try PyMuPDF for born-digital PDFs (more robust on malformed streams)
    2. Fall back to pdfplumber if PyMuPDF yields insufficient text
    3. Fall back to OCR if text extraction yields little content
    """

    def __init__(self, ocr_threshold: float = 100.0, output_images: bool = False):
        """
        Args:
            ocr_threshold: Minimum chars per page before triggering OCR
            output_images: Save page images for debugging/review
        """
        self.ocr_threshold = ocr_threshold
        self.output_images = output_images
        self.temp_dir = None

    def parse(self, pdf_path: str) -> PDFContent:
        """Parse PDF and extract all text with positions"""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        result = PDFContent(
            file_path=str(pdf_path),
            num_pages=0
        )

        # Try PyMuPDF first because some malformed PDFs can hang in pdfminer/pdfplumber.
        if HAS_PYMUPDF:
            try:
                result = self._parse_with_pymupdf(pdf_path)
                if self._has_sufficient_text(result):
                    result.extraction_method = "pymupdf"
                    result.is_born_digital = True
                    logger.info(f"Successfully parsed with PyMuPDF: {pdf_path}")
                    return result
            except Exception as e:
                logger.warning(f"PyMuPDF failed: {e}")

        # Try pdfplumber as fallback (still useful for some layout edge cases)
        if HAS_PDFPLUMBER:
            try:
                result = self._parse_with_pdfplumber(pdf_path)
                if self._has_sufficient_text(result):
                    result.extraction_method = "pdfplumber"
                    result.is_born_digital = True
                    logger.info(f"Successfully parsed with pdfplumber: {pdf_path}")
                    return result
            except Exception as e:
                logger.warning(f"pdfplumber failed: {e}")

        # Fall back to OCR
        if HAS_OCR and HAS_PYMUPDF:
            logger.info(f"Falling back to OCR for: {pdf_path}")
            result = self._parse_with_ocr(pdf_path)
            result.extraction_method = "ocr"
            result.is_born_digital = False
            return result

        raise RuntimeError(f"No parsing method available for: {pdf_path}")

    def _has_sufficient_text(self, result: PDFContent) -> bool:
        """Check if we extracted enough text"""
        total_chars = sum(len(p.full_text) for p in result.pages)
        avg_chars_per_page = total_chars / max(result.num_pages, 1)
        return avg_chars_per_page >= self.ocr_threshold

    def _parse_with_pdfplumber(self, pdf_path: Path) -> PDFContent:
        """Parse using pdfplumber (best for tables)"""
        pages = []

        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_content = PageContent(
                    page_num=i + 1,
                    width=page.width,
                    height=page.height
                )

                # Extract words with positions
                words = page.extract_words(
                    keep_blank_chars=True,
                    x_tolerance=3,
                    y_tolerance=3,
                    extra_attrs=["fontname", "size"]
                )

                for word in words:
                    block = TextBlock(
                        text=word.get("text", ""),
                        bbox=BBox(
                            x0=word["x0"],
                            y0=word["top"],
                            x1=word["x1"],
                            y1=word["bottom"]
                        ),
                        page_num=i + 1,
                        font_name=word.get("fontname"),
                        font_size=word.get("size")
                    )
                    page_content.text_blocks.append(block)

                # Get full text
                page_content.full_text = page.extract_text() or ""

                pages.append(page_content)

        return PDFContent(
            file_path=str(pdf_path),
            num_pages=len(pages),
            pages=pages,
            metadata={}
        )

    def _parse_with_pymupdf(self, pdf_path: Path) -> PDFContent:
        """Parse using PyMuPDF"""
        pages = []

        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            rect = page.rect
            page_content = PageContent(
                page_num=i + 1,
                width=rect.width,
                height=rect.height
            )

            # Extract text blocks with positions
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

            for block in blocks:
                if block["type"] == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            bbox = span["bbox"]
                            text_block = TextBlock(
                                text=span["text"],
                                bbox=BBox(x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3]),
                                page_num=i + 1,
                                font_name=span.get("font"),
                                font_size=span.get("size"),
                                is_bold="bold" in span.get("font", "").lower()
                            )
                            page_content.text_blocks.append(text_block)

            # Get full text
            page_content.full_text = page.get_text()

            # Optionally save page image
            if self.output_images:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale
                img_path = f"/tmp/page_{i+1}.png"
                pix.save(img_path)
                page_content.image_path = img_path

            pages.append(page_content)

        doc.close()

        return PDFContent(
            file_path=str(pdf_path),
            num_pages=len(pages),
            pages=pages,
            metadata={}
        )

    def _parse_with_ocr(self, pdf_path: Path) -> PDFContent:
        """Parse using OCR (for scanned PDFs)"""
        pages = []

        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            rect = page.rect
            page_content = PageContent(
                page_num=i + 1,
                width=rect.width,
                height=rect.height,
                is_ocr=True
            )

            # Render page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for better OCR
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            # OCR with position data
            ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

            # Convert OCR data to TextBlocks
            scale = rect.width / (pix.width / 2)  # Account for 2x rendering
            confidences = []

            for j in range(len(ocr_data["text"])):
                text = ocr_data["text"][j].strip()
                conf = ocr_data["conf"][j]

                if text and conf > 0:  # Skip empty and low-confidence
                    x = ocr_data["left"][j] * scale / 2
                    y = ocr_data["top"][j] * scale / 2
                    w = ocr_data["width"][j] * scale / 2
                    h = ocr_data["height"][j] * scale / 2

                    block = TextBlock(
                        text=text,
                        bbox=BBox(x0=x, y0=y, x1=x+w, y1=y+h),
                        page_num=i + 1,
                        confidence=conf / 100.0
                    )
                    page_content.text_blocks.append(block)
                    confidences.append(conf)

            # Full text from OCR
            page_content.full_text = pytesseract.image_to_string(img)
            page_content.ocr_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Save image for review
            if self.output_images:
                img_path = f"/tmp/ocr_page_{i+1}.png"
                img.save(img_path)
                page_content.image_path = img_path

            pages.append(page_content)

        doc.close()

        return PDFContent(
            file_path=str(pdf_path),
            num_pages=len(pages),
            pages=pages,
            extraction_method="ocr",
            is_born_digital=False
        )

    def extract_page_image(self, pdf_path: str, page_num: int, output_path: str, dpi: int = 150) -> str:
        """Extract single page as image"""
        if not HAS_PYMUPDF:
            raise RuntimeError("PyMuPDF required for image extraction")

        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]  # 0-indexed

        # Calculate matrix for desired DPI
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        pix = page.get_pixmap(matrix=mat)
        pix.save(output_path)
        doc.close()

        return output_path

    def extract_region_image(
        self,
        pdf_path: str,
        page_num: int,
        bbox: BBox,
        output_path: str,
        padding: int = 10,
        dpi: int = 150
    ) -> str:
        """Extract specific region as image (for review crops)"""
        if not HAS_PYMUPDF:
            raise RuntimeError("PyMuPDF required for image extraction")

        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]

        # Add padding
        clip = fitz.Rect(
            max(0, bbox.x0 - padding),
            max(0, bbox.y0 - padding),
            min(page.rect.width, bbox.x1 + padding),
            min(page.rect.height, bbox.y1 + padding)
        )

        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        pix = page.get_pixmap(matrix=mat, clip=clip)
        pix.save(output_path)
        doc.close()

        return output_path


# ============================================================
# TEXT UTILITIES
# ============================================================

def find_text_near_position(
    blocks: List[TextBlock],
    target_bbox: BBox,
    max_distance: float = 50.0
) -> List[TextBlock]:
    """Find text blocks near a target position"""
    results = []

    for block in blocks:
        # Calculate distance (simple center-to-center)
        block_cx = (block.bbox.x0 + block.bbox.x1) / 2
        block_cy = (block.bbox.y0 + block.bbox.y1) / 2
        target_cx = (target_bbox.x0 + target_bbox.x1) / 2
        target_cy = (target_bbox.y0 + target_bbox.y1) / 2

        distance = ((block_cx - target_cx)**2 + (block_cy - target_cy)**2)**0.5

        if distance <= max_distance:
            results.append(block)

    return results


def reconstruct_lines(blocks: List[TextBlock], y_tolerance: float = 5.0) -> List[str]:
    """Reconstruct text lines from blocks"""
    if not blocks:
        return []

    # Sort by y then x
    sorted_blocks = sorted(blocks, key=lambda b: (b.bbox.y0, b.bbox.x0))

    lines = []
    current_line = [sorted_blocks[0]]
    current_y = sorted_blocks[0].bbox.y0

    for block in sorted_blocks[1:]:
        if abs(block.bbox.y0 - current_y) <= y_tolerance:
            # Same line
            current_line.append(block)
        else:
            # New line
            current_line.sort(key=lambda b: b.bbox.x0)
            lines.append(" ".join(b.text for b in current_line))
            current_line = [block]
            current_y = block.bbox.y0

    # Don't forget last line
    if current_line:
        current_line.sort(key=lambda b: b.bbox.x0)
        lines.append(" ".join(b.text for b in current_line))

    return lines
