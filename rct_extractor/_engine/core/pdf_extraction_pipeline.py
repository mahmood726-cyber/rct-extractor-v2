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
import re
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
from .enhanced_extractor_v3 import EnhancedExtractor, Extraction, EffectType, ConfidenceInterval
from .diagnostic_accuracy_extractor import (
    DiagnosticAccuracyExtractor,
    DiagnosticExtraction,
    DiagnosticMeasureType
)

# Import RCT classifier
from ..utils.rct_classifier import RCTClassifier, ClassificationResult, StudyType

# Import table extractor (optional dependency)
try:
    from ..tables.table_extractor import TableExtractor, TableStructure
    from ..tables.table_effect_extractor import TableEffectExtractor, TableEffect
    HAS_TABLE_EXTRACTOR = True
except ImportError:
    HAS_TABLE_EXTRACTOR = False

# Import text preprocessor (v4.3.5)
from .text_preprocessor import TextPreprocessor, TextLine, ProcessedDocument

# Import primary outcome detector (v5.1)
from .primary_outcome_detector import PrimaryOutcomeDetector

# Import raw data extractor + computation engine (v5.9)
from .raw_data_extractor import extract_raw_data
from .effect_calculator import (
    compute_effect_family_from_raw_data,
    compute_effect_from_raw_data,
    ComputedEffect,
)

# Import advanced extraction (v6.3: ML tables, OCR, LLM)
try:
    from .advanced_extraction import AdvancedExtractionPipeline, AdvancedExtraction
    HAS_ADVANCED = True
except ImportError:
    HAS_ADVANCED = False

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

    # RCT classification
    classification: Optional[ClassificationResult] = None

    # Extractions
    effect_estimates: List[Extraction] = field(default_factory=list)
    diagnostic_measures: List[DiagnosticExtraction] = field(default_factory=list)

    # Table-sourced effects (before dedup merge)
    table_effects_raw: int = 0

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
        aggressive_ocr_correction: bool = True,
        skip_non_rct: bool = False,
        extract_tables: bool = True,
        enable_advanced: bool = False,
        enable_llm: bool = False,
        run_rct_classification: bool = True,
        score_primary_outcomes: bool = True,
        compute_raw_effects: bool = True,
        include_page_audit: bool = True,
    ):
        """
        Initialize the PDF extraction pipeline.

        Args:
            extract_diagnostics: Also extract diagnostic accuracy measures
            ocr_threshold: Minimum chars per page before triggering OCR
            aggressive_ocr_correction: Apply aggressive OCR error correction
            skip_non_rct: Skip extraction for papers classified as non-RCT (exclude)
            extract_tables: Extract effect estimates from tables and merge with text
            enable_advanced: Enable advanced extraction (Table Transformer + OCR)
            enable_llm: Enable LLM-based extraction (non-deterministic, UNCERTIFIED)
            run_rct_classification: Run RCT classifier on full text
            score_primary_outcomes: Score extracted effects for primary outcome likelihood
            compute_raw_effects: Compute fallback effects from raw data mentions
            include_page_audit: Run per-page extraction pass for detailed audit metadata
        """
        self.extract_diagnostics = extract_diagnostics
        self.ocr_threshold = ocr_threshold
        self.aggressive_ocr_correction = aggressive_ocr_correction
        self.skip_non_rct = skip_non_rct
        self.extract_tables = extract_tables
        self.enable_advanced = enable_advanced
        self.run_rct_classification = run_rct_classification
        self.score_primary_outcomes = score_primary_outcomes
        self.compute_raw_effects = compute_raw_effects
        self.include_page_audit = include_page_audit

        # Initialize components
        self.effect_extractor = EnhancedExtractor()
        self.diagnostic_extractor = DiagnosticAccuracyExtractor() if extract_diagnostics else None
        self.ocr_preprocessor = OCRPreprocessor(aggressive=aggressive_ocr_correction)
        self.text_preprocessor = TextPreprocessor()  # v4.3.5: Unicode, columns, dehyphenation
        self.rct_classifier = RCTClassifier() if run_rct_classification else None
        self.primary_detector = PrimaryOutcomeDetector() if score_primary_outcomes else None

        # Table extraction (optional)
        self.table_effect_extractor = TableEffectExtractor() if (extract_tables and HAS_TABLE_EXTRACTOR) else None

        # v6.3: Advanced extraction (Table Transformer + OCR + LLM)
        self.advanced_pipeline = None
        if enable_advanced and HAS_ADVANCED:
            try:
                self.advanced_pipeline = AdvancedExtractionPipeline(
                    enable_table_transformer=True,
                    enable_ocr=True,
                    enable_llm=enable_llm,
                )
                logger.info("Advanced extraction pipeline initialized")
            except Exception as e:
                logger.warning(f"Failed to init advanced pipeline: {e}")

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

            # Classify the paper (optional in fast paths)
            if self.run_rct_classification and self.rct_classifier:
                classification = self.rct_classifier.classify(full_text)
                result.classification = classification

                if self.skip_non_rct and classification.recommendation == "exclude":
                    result.warnings.append(
                        f"Skipped extraction: classified as {classification.study_type.value} "
                        f"(confidence: {classification.confidence:.2f})"
                    )
                    logger.info(
                        f"Skipping {pdf_path}: classified as {classification.study_type.value}"
                    )
                    return result

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

            # Table extraction phase (v5.1)
            if self.table_effect_extractor and HAS_TABLE_EXTRACTOR:
                try:
                    table_effects = self._extract_table_effects(pdf_path, pdf_content)
                    if table_effects:
                        result.table_effects_raw = len(table_effects)
                        result.effect_estimates = self._merge_text_and_table_effects(
                            result.effect_estimates, table_effects
                        )
                        logger.info(f"Table extraction: {len(table_effects)} raw, "
                                   f"merged to {len(result.effect_estimates)} total")
                except Exception as e:
                    result.warnings.append(f"Table extraction failed: {e}")
                    logger.warning(f"Table extraction failed for {pdf_path}: {e}")

            # Optional raw-data fallback extraction.
            if self.compute_raw_effects:
                try:
                    # Use normalized reading-order text first, then merge with raw full-text pass.
                    # Some PDFs lose critical delimiters during reading-order normalization.
                    computed = self._extract_computed_effects(processed_text)
                    if processed_text != full_text:
                        computed_full_text = self._extract_computed_effects(full_text)
                        if computed:
                            computed = self._merge_extractions(computed, computed_full_text)
                        else:
                            computed = computed_full_text
                    if computed:
                        if result.effect_estimates:
                            result.effect_estimates = self._merge_extractions(
                                result.effect_estimates, computed
                            )
                            result.warnings.append(
                                f"{len(computed)} additional effects computed from raw data"
                            )
                        else:
                            result.effect_estimates = computed
                            result.warnings.append(
                                f"No labeled effects found; {len(computed)} computed from raw data"
                            )
                        logger.info(f"Raw data extraction: {len(computed)} computed effects")
                except Exception as e:
                    result.warnings.append(f"Raw data extraction failed: {e}")
                    logger.warning(f"Raw data extraction failed for {pdf_path}: {e}")

            # v6.3: Advanced extraction (Table Transformer + OCR + LLM)
            if self.advanced_pipeline and not result.effect_estimates:
                try:
                    advanced_results = self.advanced_pipeline.extract_from_pdf(
                        pdf_path, existing_text=full_text
                    )
                    if advanced_results:
                        # Convert AdvancedExtraction to Extraction objects
                        for adv in advanced_results:
                            try:
                                if adv.effect_type and adv.effect_type in EffectType.__members__:
                                    etype = EffectType[adv.effect_type]
                                else:
                                    continue  # Skip unknown effect types
                            except (KeyError, AttributeError):
                                continue
                            ci = ConfidenceInterval(
                                lower=adv.ci_lower,
                                upper=adv.ci_upper,
                                level=0.95
                            ) if adv.ci_lower is not None and adv.ci_upper is not None else None
                            extraction = Extraction(
                                effect_type=etype,
                                point_estimate=adv.point_estimate,
                                ci=ci,
                                source_text=f"[{adv.method.upper()}] {adv.source_text[:150]}",
                                calibrated_confidence=adv.confidence,
                                has_complete_ci=ci is not None,
                            )
                            result.effect_estimates.append(extraction)
                        result.warnings.append(
                            f"Advanced extraction: {len(advanced_results)} from "
                            f"{set(a.method for a in advanced_results)}"
                        )
                        logger.info(f"Advanced extraction: {len(advanced_results)} effects")
                except Exception as e:
                    result.warnings.append(f"Advanced extraction failed: {e}")
                    logger.warning(f"Advanced extraction failed for {pdf_path}: {e}")

            # Final deterministic fallback for sparse reporting formats.
            if not result.effect_estimates:
                try:
                    lax_effects = self._extract_lax_effects(processed_text)
                    if lax_effects:
                        result.effect_estimates.extend(lax_effects)
                        result.warnings.append(
                            f"Lax fallback extraction: {len(lax_effects)} low-confidence effects"
                        )
                        logger.info(f"Lax fallback extraction recovered {len(lax_effects)} effects")
                except Exception as e:
                    result.warnings.append(f"Lax fallback extraction failed: {e}")
                    logger.warning(f"Lax fallback extraction failed for {pdf_path}: {e}")

            # Primary outcome detection (v5.1)
            if self.score_primary_outcomes and self.primary_detector and result.effect_estimates:
                self.primary_detector.score_extractions(
                    result.effect_estimates, full_text
                )

            # Process per-page for detailed audit trail (optional in fast paths)
            if self.include_page_audit:
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

            # Calculate overall confidence on the final merged extraction set.
            final_effects = result.effect_estimates
            if final_effects:
                confidences = [e.calibrated_confidence for e in final_effects if e.calibrated_confidence > 0]
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
                f"Extraction complete: {len(final_effects)} effects, "
                f"{len(diagnostic_extractions)} diagnostics"
            )

        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"PDF extraction failed: {e}")

        return result

    def _extract_table_effects(self, pdf_path: str, pdf_content) -> List:
        """
        Extract effect estimates from tables in the PDF.

        Args:
            pdf_path: Path to PDF file
            pdf_content: Parsed PDF content with page data

        Returns:
            List of TableEffect objects
        """
        all_table_effects = []

        try:
            # Use pdfplumber for table detection
            import pdfplumber
        except ImportError:
            logger.debug("pdfplumber not available for table extraction")
            return all_table_effects

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    try:
                        tables = page.extract_tables()
                        if not tables:
                            continue

                        for table_data in tables:
                            if not table_data or len(table_data) < 2:
                                continue

                            # Convert to TableStructure
                            table_struct = self._raw_table_to_structure(
                                table_data, page_idx
                            )
                            if table_struct is None:
                                continue

                            effects = self.table_effect_extractor.extract_from_table(
                                table_struct
                            )
                            all_table_effects.extend(effects)
                    except Exception as e:
                        logger.debug(f"Table extraction failed on page {page_idx}: {e}")
                        continue
        except Exception as e:
            logger.warning(f"pdfplumber table extraction failed: {e}")

        return all_table_effects

    def _extract_computed_effects(self, full_text: str) -> List:
        """
        v5.9: Extract raw two-group data from text and compute effects.

        Fallback when no labeled effects (OR, RR, HR, MD) are found.
        Finds mean(SD) pairs, events/N comparisons, then computes
        OR/RR/MD/SMD from raw data.

        Returns list of Extraction objects (same type as main extractor).
        """
        raw_extractions = extract_raw_data(full_text)
        computed_effects: List[Extraction] = []
        seen = set()

        for raw_ext in raw_extractions:
            raw_dict = raw_ext.to_raw_data_dict()
            if raw_dict is None:
                # Partial continuous fallback: if means are available but sample sizes
                # are missing, recover point-only MD instead of dropping the signal.
                if raw_ext.data_type == "continuous":
                    mean1 = getattr(raw_ext.arm1, "mean", None)
                    mean2 = getattr(raw_ext.arm2, "mean", None)
                    if mean1 is not None and mean2 is not None:
                        try:
                            md_value = float(mean1) - float(mean2)
                        except (TypeError, ValueError):
                            md_value = None
                        if md_value is not None and abs(md_value) <= 10000:
                            extraction = Extraction(
                                effect_type=EffectType.MD,
                                point_estimate=md_value,
                                ci=None,
                                source_text=f"[COMPUTED partial raw data] {raw_ext.source_text[:150]}",
                                calibrated_confidence=max(0.12, min(0.35, raw_ext.confidence * 0.5)),
                                has_complete_ci=False,
                                se_method="computed_partial",
                                warnings=["Missing sample sizes: point estimate only"],
                            )
                            computed_effects.append(extraction)
                continue

            # Compute all available effect-family variants from the same raw data.
            family_results = compute_effect_family_from_raw_data(raw_dict, raw_ext.data_type)
            if not family_results:
                # Backward-compatible fallback to single-effect path.
                result = compute_effect_from_raw_data(raw_dict, raw_ext.data_type)
                family_results = [result] if result is not None else []
            if not family_results:
                continue

            for result in family_results:
                effect_name = str(getattr(result, "effect_type", "") or "").upper()
                if effect_name == "RD":
                    effect_name = "ARD"

                # Convert ComputedEffect to Extraction (main extractor's type)
                try:
                    if effect_name and effect_name in EffectType.__members__:
                        etype = EffectType[effect_name]
                    else:
                        continue  # Skip unknown effect types
                except (KeyError, AttributeError):
                    continue

                ci = ConfidenceInterval(
                    lower=result.ci_lower,
                    upper=result.ci_upper,
                    level=0.95
                )

                dedupe_key = (
                    etype.value,
                    round(float(result.point_estimate), 6),
                    round(float(result.ci_lower), 6),
                    round(float(result.ci_upper), 6),
                )
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                extraction = Extraction(
                    effect_type=etype,
                    point_estimate=result.point_estimate,
                    ci=ci,
                    source_text=f"[COMPUTED from raw data] {raw_ext.source_text[:150]}",
                    calibrated_confidence=raw_ext.confidence * 0.7,  # Discount for computed
                    has_complete_ci=True,
                    se_method="computed",
                    standard_error=result.se,
                )
                computed_effects.append(extraction)

        return computed_effects

    def _extract_lax_effects(self, text: str) -> List[Extraction]:
        """
        Deterministic low-confidence fallback when strict extraction returns nothing.

        Designed for sparse reporting styles (e.g., "mean difference in score ..., -1.7
        [95% CI, -8.3 to 4.8]") where stricter patterns may miss due extra context tokens.
        """
        if not text:
            return []

        label_patterns = [
            ("HR", r'(?:(?i:hazard\s*ratio)\s*(?:was|=|:|,)?\s*|\bHR\b\s*(?:=|:)?\s*)([0-9]+(?:\.[0-9]+)?)', (0.01, 50.0)),
            ("OR", r'(?:(?i:odds\s*ratio)\s*(?:was|=|:|,)?\s*|\bOR\b\s*(?:=|:)?\s*)([0-9]+(?:\.[0-9]+)?)', (0.01, 100.0)),
            ("RR", r'(?:(?i:(?:risk\s*ratio|relative\s*risk))\s*(?:was|=|:|,)?\s*|\bRR\b\s*(?:=|:)?\s*)([0-9]+(?:\.[0-9]+)?)', (0.01, 50.0)),
            ("MD", r'(?:(?i:mean\s+difference)(?:\s+in\s+[\w\s\'/\-]{1,80})?\s*(?:was|=|:|,)?\s*|\bMD\b\s*(?:=|:)?\s*)([+-]?[0-9]+(?:\.[0-9]+)?)', (-10000.0, 10000.0)),
            ("SMD", r'(?:(?i:standardized\s+mean\s+difference)\s*(?:was|=|:|,)?\s*|\bSMD\b\s*(?:=|:)?\s*)([+-]?[0-9]+(?:\.[0-9]+)?)', (-20.0, 20.0)),
            ("ARD", r'(?:(?i:absolute\s+difference|risk\s+difference)(?:\s+of)?\s*(?:was|=|:|,)?\s*|\b(?:ARD|RD)\b\s*(?:=|:)?\s*)([+-]?[0-9]+(?:\.[0-9]+)?)\s*%?', (-100.0, 100.0)),
        ]
        ci_pattern = re.compile(
            r'(?:95%?\s*)?(?:CI|confidence\s+interval)\s*[,:\[\(]?\s*([+-]?\d+\.?\d*)\s*(?:to|[-–—,])\s*([+-]?\d+\.?\d*)',
            re.IGNORECASE,
        )
        noise_pattern = re.compile(
            r'\b(?:doi|pmid|isbn|nct\d{8}|vol\.?\s*\d{1,3}|;\s*\d+\(\d+\):\d+)\b',
            re.IGNORECASE,
        )

        recovered: List[Extraction] = []
        seen = set()

        for effect_name, pattern, bounds in label_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = float(match.group(1))
                except (TypeError, ValueError):
                    continue

                min_val, max_val = bounds
                if not (min_val <= value <= max_val):
                    continue

                start = max(0, match.start() - 120)
                end = min(len(text), match.end() + 220)
                window = text[start:end]
                if noise_pattern.search(window):
                    continue

                ci = None
                has_complete_ci = False
                confidence = 0.22
                ci_match = ci_pattern.search(window)
                if ci_match:
                    try:
                        low = float(ci_match.group(1))
                        high = float(ci_match.group(2))
                        if low > high:
                            low, high = high, low
                        if effect_name in {"HR", "OR", "RR"} and (low <= 0 or high <= 0):
                            raise ValueError("invalid_ratio_ci")
                        ci = ConfidenceInterval(lower=low, upper=high, level=0.95)
                        has_complete_ci = True
                        confidence = 0.34
                    except (TypeError, ValueError):
                        ci = None
                        has_complete_ci = False

                dedupe_key = (
                    effect_name,
                    round(value, 3),
                    round(ci.lower, 3) if ci else None,
                    round(ci.upper, 3) if ci else None,
                )
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                recovered.append(
                    Extraction(
                        effect_type=EffectType[effect_name],
                        point_estimate=value,
                        ci=ci,
                        source_text=f"[LAX] {window[:180]}",
                        calibrated_confidence=confidence,
                        has_complete_ci=has_complete_ci,
                        warnings=["Low-confidence fallback extraction"],
                    )
                )

                if len(recovered) >= 8:
                    return recovered

        return recovered

    def _merge_extractions(
        self,
        primary: List[Extraction],
        additional: List[Extraction],
    ) -> List[Extraction]:
        """
        Merge two Extraction lists with light deduplication.

        Used for combining computed raw-data effects with existing text/table effects.
        """
        merged = list(primary)
        seen = {
            (
                eff.effect_type.value,
                round(float(eff.point_estimate), 6),
                round(float(eff.ci.lower), 6) if eff.ci else None,
                round(float(eff.ci.upper), 6) if eff.ci else None,
            )
            for eff in merged
            if eff.point_estimate is not None
        }

        for eff in additional:
            if eff.point_estimate is None:
                continue
            key = (
                eff.effect_type.value,
                round(float(eff.point_estimate), 6),
                round(float(eff.ci.lower), 6) if eff.ci else None,
                round(float(eff.ci.upper), 6) if eff.ci else None,
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(eff)
        return merged

    def _raw_table_to_structure(self, table_data: List[List], page_num: int):
        """
        Convert pdfplumber raw table data to TableStructure.

        Args:
            table_data: List of rows, each row is list of cell strings
            page_num: Page number

        Returns:
            TableStructure or None if invalid
        """
        if not HAS_TABLE_EXTRACTOR:
            return None

        from ..tables.table_extractor import TableStructure, TableCell

        # Import BBox from pdf_parser
        try:
            from ..pdf.pdf_parser import BBox
            bbox = BBox(x0=0, y0=0, x1=100, y1=100)
        except ImportError:
            # Fallback: create a minimal namedtuple-like object
            from collections import namedtuple
            _BBox = namedtuple('BBox', ['x0', 'y0', 'x1', 'y1'])
            bbox = _BBox(x0=0, y0=0, x1=100, y1=100)

        cells = []
        num_rows = len(table_data)
        num_cols = max(len(row) for row in table_data) if table_data else 0

        for row_idx, row in enumerate(table_data):
            for col_idx, cell_text in enumerate(row):
                cells.append(TableCell(
                    text=str(cell_text) if cell_text else "",
                    row=row_idx,
                    col=col_idx,
                    is_header=(row_idx == 0),
                ))

        if not cells or num_cols == 0:
            return None

        return TableStructure(
            cells=cells,
            num_rows=num_rows,
            num_cols=num_cols,
            bbox=bbox,
            page_num=page_num,
            header_rows=1,
        )

    def _merge_text_and_table_effects(
        self,
        text_effects: List[Extraction],
        table_effects: List,
    ) -> List[Extraction]:
        """
        Merge text and table extractions with deduplication.

        Rules:
        - If text has CI -> keep text version
        - If text lacks CI, table has CI -> merge table CI onto text extraction
        - Table-only effect -> add with source="table" warning
        - Match on effect_type + value (tolerance 0.01 for ratios, 0.5 for MD/SMD)

        Args:
            text_effects: Extractions from text
            table_effects: TableEffect objects from tables

        Returns:
            Merged list of Extraction objects
        """
        RATIO_TYPES = {"HR", "OR", "RR", "IRR"}
        result = list(text_effects)
        used_text_indices = set()

        for tbl_eff in table_effects:
            tbl_type = tbl_eff.effect_type  # string like "HR", "OR"

            # Find matching text extraction
            best_match_idx = None
            best_error = float('inf')

            for idx, txt_eff in enumerate(result):
                if idx in used_text_indices:
                    continue

                txt_type = txt_eff.effect_type.value

                if txt_type != tbl_type:
                    continue

                # Value tolerance
                if tbl_type in RATIO_TYPES:
                    tolerance = 0.01
                    if txt_eff.point_estimate == 0:
                        continue
                    rel_error = abs(txt_eff.point_estimate - tbl_eff.point_estimate) / abs(txt_eff.point_estimate)
                    if rel_error <= tolerance:
                        if rel_error < best_error:
                            best_error = rel_error
                            best_match_idx = idx
                else:
                    tolerance = 0.5
                    error = abs(txt_eff.point_estimate - tbl_eff.point_estimate)
                    if error <= tolerance:
                        if error < best_error:
                            best_error = error
                            best_match_idx = idx

            if best_match_idx is not None:
                used_text_indices.add(best_match_idx)
                txt_eff = result[best_match_idx]

                # If text lacks CI but table has CI -> merge
                if not txt_eff.has_complete_ci and tbl_eff.ci_lower is not None and tbl_eff.ci_upper is not None:
                    txt_eff.ci = ConfidenceInterval(
                        lower=tbl_eff.ci_lower,
                        upper=tbl_eff.ci_upper,
                        level=tbl_eff.ci_level,
                    )
                    txt_eff.has_complete_ci = True
                    txt_eff.warnings.append("CI merged from table extraction")
                    logger.debug(f"Merged table CI onto text extraction: {tbl_type} {tbl_eff.point_estimate}")
            else:
                # Table-only effect -> convert and add
                new_extraction = self._table_effect_to_extraction(tbl_eff)
                if new_extraction is not None:
                    result.append(new_extraction)

        return result

    def _table_effect_to_extraction(self, table_effect) -> Optional[Extraction]:
        """
        Convert a TableEffect to an Extraction.

        Args:
            table_effect: TableEffect object

        Returns:
            Extraction or None
        """
        # Map table effect type string to EffectType enum
        type_map = {
            "HR": EffectType.HR,
            "OR": EffectType.OR,
            "RR": EffectType.RR,
            "MD": EffectType.MD,
            "SMD": EffectType.SMD,
            "IRR": EffectType.IRR,
            "ARD": EffectType.ARD,
            "GMR": EffectType.GMR,
        }

        effect_type = type_map.get(table_effect.effect_type)
        if effect_type is None:
            return None

        ci = None
        has_complete_ci = False
        if table_effect.ci_lower is not None and table_effect.ci_upper is not None:
            ci = ConfidenceInterval(
                lower=table_effect.ci_lower,
                upper=table_effect.ci_upper,
                level=table_effect.ci_level,
            )
            has_complete_ci = True

        from .enhanced_extractor_v3 import AutomationTier

        warnings = ["Extracted from table (not inline text)"]

        # v5.2: Detect subgroup rows in tables
        outcome = table_effect.outcome_name or ""
        subgroup_patterns = [
            r'\b\d{1,3}\s*[-–—]\s*\d{1,3}\s*(?:years?|yrs?|months?|mos?)\b',  # Age ranges
            r'\b(?:age|aged)\s*[<>≤≥]\s*\d',  # Age thresholds
            r'\b\d+\s*(?:mg|mcg|µg|ml|mL|IU|units?)\b(?!\s*/)',  # Dose levels (exclude mg/dL etc.)
            r'\b(?:male|female|men|women)\b',  # Sex subgroups
            r'\b(?:subgroup|stratum|strata|tertile|quartile|quintile)\b',  # Explicit labels
            r'\b(?:NYHA|stage|grade|class)\s+(?:I{1,4}|[1-4])\b(?!\s+(?:evidence|recommendation|quality|certainty))',  # Clinical stages (not evidence grading)
            r'^\s*(?:≥|>=|<|<=|>)\s*\d',  # Leading comparison
        ]
        for pat in subgroup_patterns:
            if re.search(pat, outcome, re.IGNORECASE):
                warnings.append("Likely subgroup analysis (table row)")
                break

        return Extraction(
            effect_type=effect_type,
            point_estimate=table_effect.point_estimate,
            ci=ci,
            p_value=table_effect.p_value,
            source_text=f"[table] {table_effect.outcome_name}: {', '.join(table_effect.source_cells)}",
            raw_confidence=table_effect.confidence * 0.8,
            calibrated_confidence=table_effect.confidence * 0.7,
            automation_tier=AutomationTier.VERIFY,
            has_complete_ci=has_complete_ci,
            warnings=warnings,
        )

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

        # Classify text (optional)
        if self.run_rct_classification and self.rct_classifier:
            result.classification = self.rct_classifier.classify(text)

            if self.skip_non_rct and result.classification.recommendation == "exclude":
                result.warnings.append(
                    f"Skipped extraction: classified as {result.classification.study_type.value} "
                    f"(confidence: {result.classification.confidence:.2f})"
                )
                return result

        effect_extractions, diagnostic_extractions, processed_text, corrections = \
            self._extract_from_text(text, preprocess=True)

        result.effect_estimates = effect_extractions
        result.diagnostic_measures = diagnostic_extractions

        # Primary outcome detection (v5.1)
        if self.score_primary_outcomes and self.primary_detector and effect_extractions:
            self.primary_detector.score_extractions(effect_extractions, text)

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
