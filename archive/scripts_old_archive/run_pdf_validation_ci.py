#!/usr/bin/env python3
"""
PDF Validation CI Runner for RCT Extractor v4.0.5
=================================================

Lightweight validation script for CI/CD pipelines.
Runs a subset of PDF validation tests suitable for automated testing.

Features:
- Downloads small subset of test PDFs
- Runs critical validation tests
- Generates CI-friendly output
- Fast execution (<5 minutes target)

Usage:
    python run_pdf_validation_ci.py
    python run_pdf_validation_ci.py --max-pdfs 5
    python run_pdf_validation_ci.py --skip-download
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are available"""
    deps = {}

    # Check pdfplumber
    try:
        import pdfplumber
        deps["pdfplumber"] = True
    except ImportError:
        deps["pdfplumber"] = False

    # Check PyMuPDF
    try:
        import fitz
        deps["pymupdf"] = True
    except ImportError:
        deps["pymupdf"] = False

    # Check pytesseract
    try:
        import pytesseract
        deps["pytesseract"] = True
    except ImportError:
        deps["pytesseract"] = False

    # Check Pillow
    try:
        from PIL import Image
        deps["pillow"] = True
    except ImportError:
        deps["pillow"] = False

    # Check pytest
    try:
        import pytest
        deps["pytest"] = True
    except ImportError:
        deps["pytest"] = False

    return deps


def download_test_pdfs(max_pdfs: int = 5) -> int:
    """Download a small subset of test PDFs for CI"""
    logger.info(f"Downloading up to {max_pdfs} test PDFs...")

    try:
        from scripts.download_pmc_pdfs import PMCDownloader, PMC_DIR
        from data.external_validation_dataset import ALL_EXTERNAL_VALIDATION_TRIALS

        downloader = PMCDownloader(PMC_DIR)
        downloader.download_all(max_count=max_pdfs)
        downloader.save_manifest()

        return len(downloader.downloaded)

    except Exception as e:
        logger.warning(f"PDF download failed: {e}")
        return 0


def count_available_pdfs() -> Dict[str, int]:
    """Count available PDF files"""
    test_pdfs_dir = Path(__file__).parent / "test_pdfs"

    counts = {
        "total": 0,
        "born_digital": 0,
        "scanned": 0,
        "gold_standard": 0,
    }

    if not test_pdfs_dir.exists():
        return counts

    counts["total"] = len(list(test_pdfs_dir.glob("**/*.pdf")))

    born_digital = test_pdfs_dir / "pmc_open_access" / "born_digital"
    counts["born_digital"] = len(list(born_digital.glob("**/*.pdf")))

    scanned = test_pdfs_dir / "pmc_open_access" / "scanned"
    counts["scanned"] = len(list(scanned.glob("*.pdf")))

    gold = test_pdfs_dir / "gold_standard" / "pdfs"
    counts["gold_standard"] = len(list(gold.glob("*.pdf")))

    return counts


def run_text_validation() -> Dict[str, Any]:
    """Run text-based validation (no PDF required)"""
    logger.info("Running text-based validation...")

    try:
        from src.core.enhanced_extractor_v3 import EnhancedExtractor
        from data.external_validation_dataset import ALL_EXTERNAL_VALIDATION_TRIALS

        extractor = EnhancedExtractor()

        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
        }

        for trial in ALL_EXTERNAL_VALIDATION_TRIALS[:20]:  # Test first 20
            results["total"] += 1

            try:
                # Extract from source text
                extracted = extractor.extract(trial.source_text)

                # Check if primary effect was found
                if trial.extractor_a:
                    expected = trial.extractor_a[0]
                    found = False

                    for ext in extracted:
                        ext_value = getattr(ext, "effect_size", getattr(ext, "value", 0))
                        if abs(ext_value - expected.effect_size) < 0.02:
                            found = True
                            break

                    if found:
                        results["passed"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"{trial.trial_name}: primary effect not found")
                else:
                    results["passed"] += 1  # No expectation

            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{trial.trial_name}: {str(e)}")

        results["accuracy"] = results["passed"] / results["total"] if results["total"] > 0 else 0

        return results

    except Exception as e:
        return {"error": str(e), "total": 0, "passed": 0, "failed": 0, "accuracy": 0}


def run_pdf_validation(max_pdfs: int = 10) -> Dict[str, Any]:
    """Run PDF validation tests"""
    logger.info(f"Running PDF validation (max {max_pdfs} PDFs)...")

    try:
        from src.pdf.pdf_parser import PDFParser
        from src.core.enhanced_extractor_v3 import EnhancedExtractor

        parser = PDFParser()
        extractor = EnhancedExtractor()

        test_pdfs_dir = Path(__file__).parent / "test_pdfs"
        pdfs = list(test_pdfs_dir.glob("pmc_open_access/**/*.pdf"))[:max_pdfs]

        results = {
            "total": len(pdfs),
            "parsed": 0,
            "extracted": 0,
            "errors": [],
        }

        for pdf in pdfs:
            try:
                # Parse PDF
                content = parser.parse(str(pdf))
                results["parsed"] += 1

                # Extract text
                full_text = "\n".join(p.full_text for p in content.pages)

                # Extract effects
                effects = extractor.extract(full_text)
                if effects:
                    results["extracted"] += 1

            except Exception as e:
                results["errors"].append(f"{pdf.name}: {str(e)}")

        results["parse_rate"] = results["parsed"] / results["total"] if results["total"] > 0 else 0
        results["extraction_rate"] = results["extracted"] / results["total"] if results["total"] > 0 else 0

        return results

    except Exception as e:
        return {"error": str(e), "total": 0, "parsed": 0, "extracted": 0}


def run_unit_tests() -> Dict[str, Any]:
    """Run pytest unit tests"""
    logger.info("Running unit tests...")

    try:
        import pytest

        # Run with minimal output
        result = pytest.main([
            "tests/",
            "-v",
            "--tb=line",
            "-m", "not slow and not pdf",
            "--timeout=60",
            "-q",
        ])

        return {
            "exit_code": result,
            "passed": result == 0,
        }

    except Exception as e:
        return {"error": str(e), "passed": False}


def generate_report(
    deps: Dict[str, bool],
    pdf_counts: Dict[str, int],
    text_results: Dict[str, Any],
    pdf_results: Dict[str, Any],
    test_results: Dict[str, Any],
    elapsed: float
) -> Dict[str, Any]:
    """Generate CI validation report"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": elapsed,
        "dependencies": deps,
        "pdf_files": pdf_counts,
        "text_validation": text_results,
        "pdf_validation": pdf_results,
        "unit_tests": test_results,
        "overall_status": "PASS",
    }

    # Determine overall status
    if text_results.get("accuracy", 0) < 0.80:
        report["overall_status"] = "FAIL"
        report["failure_reason"] = "Text validation accuracy below 80%"
    elif pdf_results.get("parse_rate", 0) < 0.90 and pdf_counts["total"] > 0:
        report["overall_status"] = "FAIL"
        report["failure_reason"] = "PDF parse rate below 90%"
    elif not test_results.get("passed", True):
        report["overall_status"] = "FAIL"
        report["failure_reason"] = "Unit tests failed"

    return report


def print_report(report: Dict[str, Any]):
    """Print CI-friendly report"""
    print("\n" + "=" * 70)
    print("RCT EXTRACTOR - CI VALIDATION REPORT")
    print("=" * 70)

    print(f"\nTimestamp: {report['timestamp']}")
    print(f"Elapsed: {report['elapsed_seconds']:.1f}s")

    print("\n--- Dependencies ---")
    for dep, available in report['dependencies'].items():
        status = "OK" if available else "MISSING"
        print(f"  {dep}: {status}")

    print("\n--- PDF Files ---")
    for category, count in report['pdf_files'].items():
        print(f"  {category}: {count}")

    print("\n--- Text Validation ---")
    tv = report['text_validation']
    if "error" in tv:
        print(f"  Error: {tv['error']}")
    else:
        print(f"  Total: {tv['total']}")
        print(f"  Passed: {tv['passed']}")
        print(f"  Accuracy: {tv.get('accuracy', 0):.1%}")

    print("\n--- PDF Validation ---")
    pv = report['pdf_validation']
    if "error" in pv:
        print(f"  Error: {pv['error']}")
    else:
        print(f"  Total PDFs: {pv['total']}")
        print(f"  Parse rate: {pv.get('parse_rate', 0):.1%}")
        print(f"  Extraction rate: {pv.get('extraction_rate', 0):.1%}")

    print("\n--- Unit Tests ---")
    ut = report['unit_tests']
    if "error" in ut:
        print(f"  Error: {ut['error']}")
    else:
        print(f"  Passed: {ut.get('passed', False)}")

    print("\n" + "=" * 70)
    status = report['overall_status']
    if status == "PASS":
        print(f"OVERALL STATUS: {status}")
    else:
        print(f"OVERALL STATUS: {status}")
        print(f"Reason: {report.get('failure_reason', 'Unknown')}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Run PDF validation for CI/CD"
    )
    parser.add_argument(
        "--max-pdfs", type=int, default=5,
        help="Maximum PDFs to download/test"
    )
    parser.add_argument(
        "--skip-download", action="store_true",
        help="Skip PDF download step"
    )
    parser.add_argument(
        "--skip-tests", action="store_true",
        help="Skip unit tests"
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        help="Output JSON report file"
    )

    args = parser.parse_args()

    start_time = time.time()

    # Check dependencies
    logger.info("Checking dependencies...")
    deps = check_dependencies()

    # Download PDFs if needed
    if not args.skip_download and deps.get("pdfplumber"):
        download_test_pdfs(args.max_pdfs)

    # Count PDFs
    pdf_counts = count_available_pdfs()

    # Run text validation
    text_results = run_text_validation()

    # Run PDF validation if PDFs available
    if pdf_counts["total"] > 0 and deps.get("pdfplumber"):
        pdf_results = run_pdf_validation(args.max_pdfs)
    else:
        pdf_results = {"skipped": True, "reason": "No PDFs available"}

    # Run unit tests
    if not args.skip_tests and deps.get("pytest"):
        test_results = run_unit_tests()
    else:
        test_results = {"skipped": True}

    elapsed = time.time() - start_time

    # Generate report
    report = generate_report(
        deps, pdf_counts, text_results, pdf_results, test_results, elapsed
    )

    # Print report
    print_report(report)

    # Save report
    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to: {args.output}")

    # Exit code
    if report["overall_status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
