#!/usr/bin/env python3
"""
Full PDF Extraction Validation
===============================

Runs end-to-end validation: PDF → Text → Effect Extraction → Metrics

This measures REAL extraction performance, not snippet-based validation.

Usage:
    python scripts/validate_full_pdf_extraction.py
    python scripts/validate_full_pdf_extraction.py --sample 10
    python scripts/validate_full_pdf_extraction.py --verbose
"""

import argparse
import json
import sys
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import PDF parser
try:
    from src.pdf.pdf_parser import PDFParser, PDFContent
    HAS_PDF_PARSER = True
except ImportError:
    HAS_PDF_PARSER = False
    PDFParser = None

# Import extractor
try:
    from src.core.enhanced_extractor_v3 import EnhancedExtractor, EffectType, Extraction
    HAS_EXTRACTOR = True
except ImportError:
    HAS_EXTRACTOR = False
    EnhancedExtractor = None

# Import ground truth
try:
    from data.external_validation_dataset import ALL_EXTERNAL_VALIDATION_TRIALS
    HAS_GROUND_TRUTH = True
except ImportError:
    HAS_GROUND_TRUTH = False


PROJECT_ROOT = Path(__file__).parent.parent
PDF_DIR = PROJECT_ROOT / "test_pdfs" / "real_pdfs"
OUTPUT_DIR = PROJECT_ROOT / "output"


@dataclass
class PDFExtractionResult:
    """Result of extracting from a single PDF"""
    pdf_path: str
    pdf_hash: str
    parse_success: bool
    parse_method: str
    num_pages: int
    total_chars: int

    # Extractions
    extractions: List[Dict[str, Any]]
    extraction_count: int

    # By type
    by_type: Dict[str, int]

    # Quality indicators
    has_tables: bool
    has_figures: bool
    ocr_used: bool
    ocr_confidence: Optional[float]

    # Errors
    errors: List[str]
    warnings: List[str]


@dataclass
class PDFValidationSummary:
    """Summary of PDF extraction validation"""
    timestamp: str
    pdfs_attempted: int
    pdfs_parsed: int
    pdfs_with_extractions: int

    total_extractions: int
    extractions_with_ci: int

    parse_success_rate: float
    extraction_rate: float
    ci_completion_rate: float

    by_effect_type: Dict[str, int]
    by_therapeutic_area: Dict[str, int]

    common_errors: List[Dict[str, Any]]

    # Comparison to snippet validation (if available)
    snippet_recall: Optional[float]
    full_pdf_extraction_rate: Optional[float]


def hash_file(path: Path) -> str:
    """Calculate SHA-256 hash of file"""
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()[:16]


def extract_from_pdf(pdf_path: Path) -> PDFExtractionResult:
    """Extract effects from a single PDF"""
    errors = []
    warnings = []

    # Hash file for tracking
    try:
        pdf_hash = hash_file(pdf_path)
    except Exception as e:
        pdf_hash = "error"
        errors.append(f"Hash error: {e}")

    # Parse PDF
    parse_success = False
    parse_method = "none"
    num_pages = 0
    total_chars = 0
    full_text = ""
    has_tables = False
    has_figures = False
    ocr_used = False
    ocr_confidence = None

    if HAS_PDF_PARSER:
        try:
            parser = PDFParser()
            content = parser.parse(str(pdf_path))

            parse_success = True
            parse_method = content.extraction_method
            num_pages = content.num_pages

            # Concatenate all page text
            full_text = "\n\n".join(page.full_text for page in content.pages)
            total_chars = len(full_text)

            # Check for OCR
            for page in content.pages:
                if page.is_ocr:
                    ocr_used = True
                    if page.ocr_confidence:
                        ocr_confidence = page.ocr_confidence

        except Exception as e:
            errors.append(f"Parse error: {e}")
    else:
        errors.append("PDF parser not available")

    # Extract effects
    extractions = []
    by_type = {}

    if parse_success and HAS_EXTRACTOR and full_text:
        try:
            extractor = EnhancedExtractor()
            raw_extractions = extractor.extract(full_text)

            for ext in raw_extractions:
                ext_type = ext.effect_type.value
                by_type[ext_type] = by_type.get(ext_type, 0) + 1

                extractions.append({
                    "type": ext_type,
                    "value": ext.point_estimate,
                    "ci_lower": ext.ci.lower if ext.ci else None,
                    "ci_upper": ext.ci.upper if ext.ci else None,
                    "has_ci": ext.ci is not None and ext.ci.lower is not None,
                    "confidence": ext.calibrated_confidence,
                    "source_snippet": ext.source_text[:100] if ext.source_text else "",
                })
        except Exception as e:
            errors.append(f"Extraction error: {e}")

    return PDFExtractionResult(
        pdf_path=str(pdf_path),
        pdf_hash=pdf_hash,
        parse_success=parse_success,
        parse_method=parse_method,
        num_pages=num_pages,
        total_chars=total_chars,
        extractions=extractions,
        extraction_count=len(extractions),
        by_type=by_type,
        has_tables=has_tables,
        has_figures=has_figures,
        ocr_used=ocr_used,
        ocr_confidence=ocr_confidence,
        errors=errors,
        warnings=warnings,
    )


def validate_pdf_corpus(
    pdf_dir: Path,
    sample_size: Optional[int] = None,
    verbose: bool = False
) -> Tuple[List[PDFExtractionResult], PDFValidationSummary]:
    """Validate extraction across PDF corpus"""

    # Find all PDFs
    pdf_files = list(pdf_dir.rglob("*.pdf"))

    if sample_size and sample_size < len(pdf_files):
        import random
        pdf_files = random.sample(pdf_files, sample_size)

    print(f"Validating {len(pdf_files)} PDFs...")

    results = []
    by_area = {}
    total_by_type = {}
    error_counts = {}

    for i, pdf_path in enumerate(pdf_files, 1):
        if verbose:
            print(f"[{i}/{len(pdf_files)}] {pdf_path.name}...")

        result = extract_from_pdf(pdf_path)
        results.append(result)

        # Track by area (from path)
        area = pdf_path.parent.name
        by_area[area] = by_area.get(area, 0) + 1

        # Track effect types
        for etype, count in result.by_type.items():
            total_by_type[etype] = total_by_type.get(etype, 0) + count

        # Track errors
        for error in result.errors:
            error_type = error.split(":")[0]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        if verbose:
            status = "[OK]" if result.parse_success else "[FAIL]"
            print(f"  {status} {result.extraction_count} extractions, {result.total_chars} chars")

    # Calculate summary
    pdfs_parsed = sum(1 for r in results if r.parse_success)
    pdfs_with_extractions = sum(1 for r in results if r.extraction_count > 0)
    total_extractions = sum(r.extraction_count for r in results)
    extractions_with_ci = sum(
        sum(1 for e in r.extractions if e.get("has_ci"))
        for r in results
    )

    summary = PDFValidationSummary(
        timestamp=datetime.now().isoformat(),
        pdfs_attempted=len(pdf_files),
        pdfs_parsed=pdfs_parsed,
        pdfs_with_extractions=pdfs_with_extractions,
        total_extractions=total_extractions,
        extractions_with_ci=extractions_with_ci,
        parse_success_rate=pdfs_parsed / len(pdf_files) if pdf_files else 0,
        extraction_rate=pdfs_with_extractions / len(pdf_files) if pdf_files else 0,
        ci_completion_rate=extractions_with_ci / total_extractions if total_extractions > 0 else 0,
        by_effect_type=total_by_type,
        by_therapeutic_area=by_area,
        common_errors=[
            {"error": e, "count": c}
            for e, c in sorted(error_counts.items(), key=lambda x: -x[1])[:5]
        ],
        snippet_recall=0.903,  # From snippet validation
        full_pdf_extraction_rate=pdfs_with_extractions / len(pdf_files) if pdf_files else 0,
    )

    return results, summary


def print_summary(summary: PDFValidationSummary):
    """Print validation summary"""
    print("\n" + "=" * 70)
    print("FULL PDF EXTRACTION VALIDATION")
    print("=" * 70)

    print(f"\n--- Corpus ---")
    print(f"PDFs attempted: {summary.pdfs_attempted}")
    print(f"PDFs parsed successfully: {summary.pdfs_parsed} ({summary.parse_success_rate:.1%})")
    print(f"PDFs with extractions: {summary.pdfs_with_extractions} ({summary.extraction_rate:.1%})")

    print(f"\n--- Extractions ---")
    print(f"Total extractions: {summary.total_extractions}")
    print(f"With complete CI: {summary.extractions_with_ci} ({summary.ci_completion_rate:.1%})")
    print(f"Avg per PDF: {summary.total_extractions / summary.pdfs_parsed:.1f}" if summary.pdfs_parsed > 0 else "N/A")

    print(f"\n--- By Effect Type ---")
    for etype, count in sorted(summary.by_effect_type.items(), key=lambda x: -x[1]):
        print(f"  {etype}: {count}")

    print(f"\n--- By Therapeutic Area ---")
    for area, count in sorted(summary.by_therapeutic_area.items(), key=lambda x: -x[1]):
        print(f"  {area}: {count}")

    if summary.common_errors:
        print(f"\n--- Common Errors ---")
        for err in summary.common_errors:
            print(f"  {err['error']}: {err['count']}")

    print(f"\n--- Comparison to Snippet Validation ---")
    print(f"Snippet-based recall: {summary.snippet_recall:.1%}")
    print(f"Full PDF extraction rate: {summary.full_pdf_extraction_rate:.1%}")

    gap = summary.snippet_recall - summary.full_pdf_extraction_rate
    if gap > 0.1:
        print(f"  [WARNING] {gap:.1%} gap suggests PDF parsing issues")

    print("=" * 70)


def save_results(
    results: List[PDFExtractionResult],
    summary: PDFValidationSummary,
    output_path: Path
):
    """Save validation results"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "summary": asdict(summary),
        "results": [asdict(r) for r in results],
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate effect extraction from full PDFs"
    )
    parser.add_argument(
        "--pdf-dir", type=Path, default=PDF_DIR,
        help="Directory containing PDFs"
    )
    parser.add_argument(
        "--sample", type=int,
        help="Sample size (default: all)"
    )
    parser.add_argument(
        "--output", type=Path,
        default=OUTPUT_DIR / "full_pdf_validation.json",
        help="Output file"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if not HAS_PDF_PARSER:
        print("Error: PDF parser not available. Install with:")
        print("  pip install pdfplumber pymupdf")
        sys.exit(1)

    if not HAS_EXTRACTOR:
        print("Error: Effect extractor not available")
        sys.exit(1)

    if not args.pdf_dir.exists():
        print(f"Error: PDF directory not found: {args.pdf_dir}")
        sys.exit(1)

    # Run validation
    results, summary = validate_pdf_corpus(
        args.pdf_dir,
        sample_size=args.sample,
        verbose=args.verbose
    )

    # Print summary
    print_summary(summary)

    # Save results
    save_results(results, summary, args.output)


if __name__ == "__main__":
    main()
