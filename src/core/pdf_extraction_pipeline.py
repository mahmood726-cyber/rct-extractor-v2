"""
PDF Extraction Pipeline
=======================

Integrated pipeline for end-to-end extraction from PDF files.
Combines PDF parsing, OCR preprocessing, and effect estimate extraction.

Addresses FDA observation: "PDF parsing limitation (text input only)"

Features:
- Direct PDF file input support
- Automatic OCR fallback for scanned documents
- OCR quality assessment with regulatory thresholds
- Integrated preprocessing and extraction
- Complete audit trail
"""

import os
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Union

# Import PDF parser
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pdf.pdf_parser import PDFParser, PDFContent, PageContent
    HAS_PDF_PARSER = True
except ImportError:
    HAS_PDF_PARSER = False

# Import OCR preprocessor
from .ocr_preprocessor import (
    OCRPreprocessor,
    OCRCorrection,
    OCRQualityAssessment,
    OCRQualityLevel,
    assess_ocr_quality
)

# Import extractors
from .enhanced_extractor_v3 import EnhancedExtractor, Extraction, EffectType
from .diagnostic_accuracy_extractor import (
    DiagnosticAccuracyExtractor,
    DiagnosticExtraction,
    DiagnosticMeasureType
)

# Import text preprocessor (v4.3.5)
from .text_preprocessor import TextPreprocessor, TextLine, ProcessedDocument

logger = logging.getLogger(__name__)


@dataclass
class PDFExtractionResult:
    """Complete extraction result from a PDF file"""
    # Source information
    file_path: str
    file_hash: str  # SHA-256 hash for audit trail
    num_pages: int
    extraction_timestamp: str

    # PDF processing info
    extraction_method: str  # "pdfplumber", "pymupdf", "ocr"
    is_born_digital: bool
    total_characters: int

    # OCR quality (if applicable)
    ocr_quality: Optional[OCRQualityAssessment] = None

    # Extractions
    effect_estimates: List[Extraction] = field(default_factory=list)
    diagnostic_measures: List[DiagnosticExtraction] = field(default_factory=list)

    # Per-page details
    page_extractions: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    # Quality metrics
    extraction_confidence: float = 0.0
    requires_manual_review: bool = False

    # Warnings and errors
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Full text (for debugging/verification)
    full_text: str = ""


class PDFExtractionPipeline:
    """
    End-to-end pipeline for extracting effect estimates from PDF files.

    Integrates:
    1. PDF parsing (pdfplumber, PyMuPDF, OCR fallback)
    2. OCR preprocessing with quality assessment
    3. Effect estimate extraction
    4. Diagnostic accuracy extraction
    5. Complete audit trail generation
    """

    def __init__(
        self,
        extract_diagnostics: bool = True,
        ocr_threshold: float = 100.0,
        aggressive_ocr_correction: bool = True
    ):
        """
        Initialize the PDF extraction pipeline.

        Args:
            extract_diagnostics: Also extract diagnostic accuracy measures
            ocr_threshold: Minimum chars per page before triggering OCR
            aggressive_ocr_correction: Apply aggressive OCR error correction
        """
        self.extract_diagnostics = extract_diagnostics
        self.ocr_threshold = ocr_threshold
        self.aggressive_ocr_correction = aggressive_ocr_correction

        # Initialize components
        self.effect_extractor = EnhancedExtractor()
        self.diagnostic_extractor = DiagnosticAccuracyExtractor() if extract_diagnostics else None
        self.ocr_preprocessor = OCRPreprocessor(aggressive=aggressive_ocr_correction)
        self.text_preprocessor = TextPreprocessor()  # v4.3.5: Unicode, columns, dehyphenation

        if HAS_PDF_PARSER:
            self.pdf_parser = PDFParser(ocr_threshold=ocr_threshold)
        else:
            self.pdf_parser = None
            logger.warning("PDF parser not available. Install pymupdf and pdfplumber.")

    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of file for audit trail."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _extract_from_text(
        self,
        text: str,
        preprocess: bool = True
    ) -> Tuple[List[Extraction], List[DiagnosticExtraction], str, List[OCRCorrection]]:
        """
        Extract from text with optional OCR preprocessing.

        Returns:
            Tuple of (effect_extractions, diagnostic_extractions, processed_text, corrections)
        """
        corrections = []
        processed_text = text

        # Apply OCR preprocessing if requested
        if preprocess:
            processed_text, corrections = self.ocr_preprocessor.preprocess(text)

        # v4.3.5: Apply text preprocessing (Unicode normalization, dehyphenation)
        # Convert raw text to TextLine objects for the preprocessor
        raw_lines = processed_text.split('\n')
        text_lines = [
            TextLine(text=line, page_num=0, line_num=i)
            for i, line in enumerate(raw_lines)
        ]
        if text_lines:
            doc = self.text_preprocessor.process(text_lines)
            processed_text = doc.reading_order_text

        # Extract effect estimates
        effect_extractions = self.effect_extractor.extract(processed_text)

        # Extract diagnostic measures if enabled
        diagnostic_extractions = []
        if self.extract_diagnostics and self.diagnostic_extractor:
            diagnostic_extractions = self.diagnostic_extractor.extract(processed_text)

        return effect_extractions, diagnostic_extractions, processed_text, corrections

    def extract_from_pdf(self, pdf_path: str) -> PDFExtractionResult:
        """
        Extract all effect estimates and diagnostic measures from a PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            PDFExtractionResult with all extractions and metadata
        """
        if not HAS_PDF_PARSER:
            raise RuntimeError(
                "PDF parsing requires pymupdf and pdfplumber. "
                "Install with: pip install pymupdf pdfplumber"
            )

        pdf_path = str(Path(pdf_path).resolve())

        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Initialize result
        result = PDFExtractionResult(
            file_path=pdf_path,
            file_hash=self._compute_file_hash(pdf_path),
            num_pages=0,
            extraction_timestamp=datetime.now().isoformat(),
            extraction_method="unknown",
            is_born_digital=True,
            total_characters=0
        )

        try:
            # Parse PDF
            logger.info(f"Parsing PDF: {pdf_path}")
            pdf_content = self.pdf_parser.parse(pdf_path)

            result.num_pages = pdf_content.num_pages
            result.extraction_method = pdf_content.extraction_method
            result.is_born_digital = pdf_content.is_born_digital

            # Combine all page text
            all_text_parts = []
            total_chars = 0

            for page in pdf_content.pages:
                all_text_parts.append(page.full_text)
                total_chars += len(page.full_text)

            full_text = "\n\n".join(all_text_parts)
            result.total_characters = total_chars
            result.full_text = full_text

            # Assess OCR quality if applicable
            if not pdf_content.is_born_digital or pdf_content.extraction_method == "ocr":
                # Get average OCR confidence from pages
                ocr_confidences = [
                    p.ocr_confidence for p in pdf_content.pages
                    if p.ocr_confidence is not None
                ]
                avg_ocr_confidence = (
                    sum(ocr_confidences) / len(ocr_confidences)
                    if ocr_confidences else None
                )

                result.ocr_quality = assess_ocr_quality(full_text, avg_ocr_confidence)

                if result.ocr_quality.quality_level == OCRQualityLevel.UNACCEPTABLE:
                    result.warnings.append("OCR quality below acceptable threshold")
                    result.requires_manual_review = True

                if result.ocr_quality.requires_manual_review:
                    result.requires_manual_review = True

            # Extract from full text
            effect_extractions, diagnostic_extractions, processed_text, corrections = \
                self._extract_from_text(full_text, preprocess=True)

            result.effect_estimates = effect_extractions
            result.diagnostic_measures = diagnostic_extractions

            # Process per-page for detailed audit trail
            for page in pdf_content.pages:
                page_effects, page_diagnostics, _, _ = self._extract_from_text(
                    page.full_text, preprocess=True
                )

                result.page_extractions[page.page_num] = {
                    "effect_count": len(page_effects),
                    "diagnostic_count": len(page_diagnostics),
                    "char_count": len(page.full_text),
                    "is_ocr": page.is_ocr,
                    "ocr_confidence": page.ocr_confidence
                }

            # Calculate overall confidence
            if effect_extractions:
                confidences = [e.calibrated_confidence for e in effect_extractions if e.calibrated_confidence > 0]
                if confidences:
                    result.extraction_confidence = sum(confidences) / len(confidences)
                else:
                    result.extraction_confidence = 0.8  # Default for valid extractions

            # Add warnings
            if not pdf_content.is_born_digital:
                result.warnings.append("Document processed with OCR - verify extractions")

            if len(corrections) > 0:
                result.warnings.append(f"{len(corrections)} OCR corrections applied")

            logger.info(
                f"Extraction complete: {len(effect_extractions)} effects, "
                f"{len(diagnostic_extractions)} diagnostics"
            )

        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"PDF extraction failed: {e}")

        return result

    def extract_from_text(self, text: str) -> PDFExtractionResult:
        """
        Extract from plain text (for backward compatibility).

        Args:
            text: Plain text to extract from

        Returns:
            PDFExtractionResult (without PDF-specific metadata)
        """
        result = PDFExtractionResult(
            file_path="<text_input>",
            file_hash=hashlib.sha256(text.encode()).hexdigest(),
            num_pages=1,
            extraction_timestamp=datetime.now().isoformat(),
            extraction_method="text_input",
            is_born_digital=True,
            total_characters=len(text),
            full_text=text
        )

        effect_extractions, diagnostic_extractions, processed_text, corrections = \
            self._extract_from_text(text, preprocess=True)

        result.effect_estimates = effect_extractions
        result.diagnostic_measures = diagnostic_extractions

        # Assess quality
        if corrections:
            result.ocr_quality = assess_ocr_quality(text)

        # Calculate confidence
        if effect_extractions:
            confidences = [e.calibrated_confidence for e in effect_extractions if e.calibrated_confidence > 0]
            if confidences:
                result.extraction_confidence = sum(confidences) / len(confidences)

        return result

    def batch_extract_from_pdfs(
        self,
        pdf_paths: List[str],
        continue_on_error: bool = True
    ) -> List[PDFExtractionResult]:
        """
        Extract from multiple PDF files.

        Args:
            pdf_paths: List of PDF file paths
            continue_on_error: Continue processing if one file fails

        Returns:
            List of PDFExtractionResult objects
        """
        results = []

        for pdf_path in pdf_paths:
            try:
                result = self.extract_from_pdf(pdf_path)
                results.append(result)
            except Exception as e:
                if continue_on_error:
                    error_result = PDFExtractionResult(
                        file_path=pdf_path,
                        file_hash="",
                        num_pages=0,
                        extraction_timestamp=datetime.now().isoformat(),
                        extraction_method="failed",
                        is_born_digital=True,
                        total_characters=0
                    )
                    error_result.errors.append(str(e))
                    results.append(error_result)
                else:
                    raise

        return results


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def extract_from_pdf(pdf_path: str, include_diagnostics: bool = True) -> PDFExtractionResult:
    """
    Extract effect estimates and diagnostic measures from a PDF file.

    Args:
        pdf_path: Path to PDF file
        include_diagnostics: Also extract diagnostic accuracy measures

    Returns:
        PDFExtractionResult with all extractions
    """
    pipeline = PDFExtractionPipeline(extract_diagnostics=include_diagnostics)
    return pipeline.extract_from_pdf(pdf_path)


def extract_from_text(text: str, include_diagnostics: bool = True) -> PDFExtractionResult:
    """
    Extract effect estimates and diagnostic measures from text.

    Args:
        text: Plain text to extract from
        include_diagnostics: Also extract diagnostic accuracy measures

    Returns:
        PDFExtractionResult with all extractions
    """
    pipeline = PDFExtractionPipeline(extract_diagnostics=include_diagnostics)
    return pipeline.extract_from_text(text)


def get_supported_effect_types() -> List[str]:
    """Return list of supported effect estimate types."""
    return [et.value for et in EffectType]


def get_supported_diagnostic_types() -> List[str]:
    """Return list of supported diagnostic accuracy measure types."""
    return [dt.value for dt in DiagnosticMeasureType]


def get_all_supported_measure_types() -> Dict[str, List[str]]:
    """Return all supported measure types organized by category."""
    return {
        "effect_estimates": get_supported_effect_types(),
        "diagnostic_accuracy": get_supported_diagnostic_types()
    }
