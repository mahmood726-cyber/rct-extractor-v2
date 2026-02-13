#!/usr/bin/env python3
"""
OCR Quality Assessment Tool
===========================

Assesses OCR quality for scanned PDFs and provides quality metrics.

Usage:
    python scripts/assess_ocr_quality.py path/to/scanned.pdf
    python scripts/assess_ocr_quality.py --all  # Assess all scanned PDFs
    python scripts/assess_ocr_quality.py --compare expected.txt actual.txt

Metrics:
    - Character Error Rate (CER)
    - Word Error Rate (WER)
    - OCR Confidence Score
    - Numeric Preservation Rate
"""

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import difflib

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Directories
PROJECT_ROOT = Path(__file__).parent.parent
SCANNED_PDFS_DIR = PROJECT_ROOT / "test_pdfs" / "pmc_open_access" / "scanned"
OUTPUT_DIR = PROJECT_ROOT / "output"


@dataclass
class OCRQualityMetrics:
    """OCR quality assessment metrics"""
    pdf_file: str
    total_characters: int
    total_words: int
    avg_confidence: float
    min_confidence: float
    max_confidence: float
    quality_level: str  # EXCELLENT, ACCEPTABLE, MARGINAL, UNACCEPTABLE
    cer: Optional[float] = None  # Character Error Rate (if reference available)
    wer: Optional[float] = None  # Word Error Rate (if reference available)
    numeric_count: int = 0
    numeric_preserved_rate: float = 1.0
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


def calculate_cer(reference: str, hypothesis: str) -> float:
    """Calculate Character Error Rate using Levenshtein distance"""
    if not reference:
        return 0.0 if not hypothesis else 1.0

    # Simple Levenshtein-based CER
    matcher = difflib.SequenceMatcher(None, reference, hypothesis)
    distance = len(reference) + len(hypothesis) - 2 * sum(
        block.size for block in matcher.get_matching_blocks()
    )
    return distance / len(reference)


def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate"""
    ref_words = reference.split()
    hyp_words = hypothesis.split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    # Word-level Levenshtein
    matcher = difflib.SequenceMatcher(None, ref_words, hyp_words)
    distance = len(ref_words) + len(hyp_words) - 2 * sum(
        block.size for block in matcher.get_matching_blocks()
    )
    return distance / len(ref_words)


def extract_numbers(text: str) -> List[str]:
    """Extract all numeric values from text"""
    # Match decimal numbers, integers, percentages
    pattern = r'\d+\.?\d*%?'
    return re.findall(pattern, text)


def assess_numeric_preservation(ocr_text: str, expected_numbers: List[str] = None) -> Tuple[int, float]:
    """Assess how well numbers are preserved in OCR"""
    ocr_numbers = extract_numbers(ocr_text)

    if expected_numbers:
        # Compare against expected
        found = sum(1 for n in expected_numbers if n in ocr_numbers)
        rate = found / len(expected_numbers) if expected_numbers else 1.0
        return len(ocr_numbers), rate
    else:
        # Just count - assume all found numbers are valid
        return len(ocr_numbers), 1.0


def determine_quality_level(avg_confidence: float) -> str:
    """Determine quality level from confidence score"""
    if avg_confidence >= 95:
        return "EXCELLENT"
    elif avg_confidence >= 85:
        return "ACCEPTABLE"
    elif avg_confidence >= 70:
        return "MARGINAL"
    else:
        return "UNACCEPTABLE"


def identify_issues(text: str, confidence: float) -> Tuple[List[str], List[str]]:
    """Identify potential OCR issues and provide recommendations"""
    issues = []
    recommendations = []

    # Check for common OCR errors
    if re.search(r'[0O](?:\.[0O])', text):
        issues.append("Potential O/0 confusion detected")
        recommendations.append("Review all decimal values manually")

    if re.search(r'(?:l|I)(?=\d)', text):
        issues.append("Potential l/1/I confusion near numbers")
        recommendations.append("Check numeric values starting with 1")

    if re.search(r'Cl\b', text):
        issues.append("Possible 'CI' misread as 'Cl'")
        recommendations.append("Verify confidence interval notation")

    # Check for garbled text
    if re.search(r'[^\x00-\x7F]{3,}', text):
        issues.append("Non-ASCII character sequences detected")
        recommendations.append("Check for encoding issues")

    # Check for repeated characters (common OCR artifact)
    if re.search(r'(.)\1{4,}', text):
        issues.append("Repeated character artifacts detected")
        recommendations.append("Review for scanning artifacts")

    # Confidence-based issues
    if confidence < 70:
        issues.append("Low overall confidence")
        recommendations.append("Consider re-scanning at higher resolution")

    if confidence < 85 and "table" in text.lower():
        issues.append("Tables may have alignment issues at this confidence level")
        recommendations.append("Manually verify table data")

    return issues, recommendations


class OCRQualityAssessor:
    """Assesses OCR quality for PDFs"""

    def __init__(self):
        self.results: List[OCRQualityMetrics] = []

    def assess_pdf(self, pdf_path: Path, reference_text: str = None) -> OCRQualityMetrics:
        """Assess OCR quality for a single PDF"""
        logger.info(f"Assessing: {pdf_path.name}")

        try:
            # Parse PDF with OCR
            from src.pdf.pdf_parser import PDFParser
            parser = PDFParser()
            content = parser.parse(str(pdf_path))

            # Collect text and confidence
            all_text = []
            confidences = []

            for page in content.pages:
                all_text.append(page.full_text)
                for block in page.text_blocks:
                    if hasattr(block, "ocr_confidence") and block.ocr_confidence:
                        confidences.append(block.ocr_confidence)

            full_text = "\n".join(all_text)

            # Calculate metrics
            total_chars = len(full_text)
            total_words = len(full_text.split())

            if confidences:
                avg_conf = sum(confidences) / len(confidences)
                min_conf = min(confidences)
                max_conf = max(confidences)
            else:
                # Default if no confidence scores available
                avg_conf = 85.0
                min_conf = 85.0
                max_conf = 85.0

            quality_level = determine_quality_level(avg_conf)

            # Calculate error rates if reference available
            cer = calculate_cer(reference_text, full_text) if reference_text else None
            wer = calculate_wer(reference_text, full_text) if reference_text else None

            # Assess numeric preservation
            num_count, num_rate = assess_numeric_preservation(full_text)

            # Identify issues
            issues, recommendations = identify_issues(full_text, avg_conf)

            metrics = OCRQualityMetrics(
                pdf_file=pdf_path.name,
                total_characters=total_chars,
                total_words=total_words,
                avg_confidence=avg_conf,
                min_confidence=min_conf,
                max_confidence=max_conf,
                quality_level=quality_level,
                cer=cer,
                wer=wer,
                numeric_count=num_count,
                numeric_preserved_rate=num_rate,
                issues=issues,
                recommendations=recommendations,
            )

            self.results.append(metrics)
            return metrics

        except Exception as e:
            logger.error(f"Assessment failed for {pdf_path.name}: {e}")
            return OCRQualityMetrics(
                pdf_file=pdf_path.name,
                total_characters=0,
                total_words=0,
                avg_confidence=0.0,
                min_confidence=0.0,
                max_confidence=0.0,
                quality_level="ERROR",
                issues=[str(e)],
                recommendations=["Check PDF file integrity"]
            )

    def assess_all_scanned(self, scan_dir: Path = SCANNED_PDFS_DIR) -> List[OCRQualityMetrics]:
        """Assess all scanned PDFs in directory"""
        pdf_files = list(scan_dir.glob("*.pdf"))

        if not pdf_files:
            logger.warning(f"No PDF files found in {scan_dir}")
            return []

        logger.info(f"Assessing {len(pdf_files)} scanned PDFs...")

        for pdf_path in pdf_files:
            self.assess_pdf(pdf_path)

        return self.results

    def generate_report(self, output_dir: Path = OUTPUT_DIR) -> Path:
        """Generate OCR quality report"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Summary statistics
        if not self.results:
            logger.warning("No results to report")
            return None

        excellent = len([r for r in self.results if r.quality_level == "EXCELLENT"])
        acceptable = len([r for r in self.results if r.quality_level == "ACCEPTABLE"])
        marginal = len([r for r in self.results if r.quality_level == "MARGINAL"])
        unacceptable = len([r for r in self.results if r.quality_level == "UNACCEPTABLE"])

        avg_confidence = sum(r.avg_confidence for r in self.results) / len(self.results)

        report = {
            "generated": datetime.now().isoformat(),
            "total_pdfs": len(self.results),
            "summary": {
                "excellent": excellent,
                "acceptable": acceptable,
                "marginal": marginal,
                "unacceptable": unacceptable,
                "average_confidence": avg_confidence,
            },
            "quality_thresholds": {
                "EXCELLENT": ">=95% confidence",
                "ACCEPTABLE": "85-94% confidence",
                "MARGINAL": "70-84% confidence",
                "UNACCEPTABLE": "<70% confidence",
            },
            "results": [asdict(r) for r in self.results],
        }

        # Save JSON report
        report_path = output_dir / "ocr_quality_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Report saved: {report_path}")
        return report_path


def print_assessment(metrics: OCRQualityMetrics):
    """Print single PDF assessment"""
    print("\n" + "-" * 50)
    print(f"PDF: {metrics.pdf_file}")
    print("-" * 50)
    print(f"Quality Level: {metrics.quality_level}")
    print(f"Confidence: {metrics.avg_confidence:.1f}% (min: {metrics.min_confidence:.1f}%, max: {metrics.max_confidence:.1f}%)")
    print(f"Characters: {metrics.total_characters:,}")
    print(f"Words: {metrics.total_words:,}")
    print(f"Numbers Found: {metrics.numeric_count}")

    if metrics.cer is not None:
        print(f"Character Error Rate: {metrics.cer:.2%}")
    if metrics.wer is not None:
        print(f"Word Error Rate: {metrics.wer:.2%}")

    if metrics.issues:
        print("\nIssues:")
        for issue in metrics.issues:
            print(f"  - {issue}")

    if metrics.recommendations:
        print("\nRecommendations:")
        for rec in metrics.recommendations:
            print(f"  * {rec}")


def print_summary(results: List[OCRQualityMetrics]):
    """Print assessment summary"""
    print("\n" + "=" * 60)
    print("OCR QUALITY ASSESSMENT SUMMARY")
    print("=" * 60)

    excellent = len([r for r in results if r.quality_level == "EXCELLENT"])
    acceptable = len([r for r in results if r.quality_level == "ACCEPTABLE"])
    marginal = len([r for r in results if r.quality_level == "MARGINAL"])
    unacceptable = len([r for r in results if r.quality_level == "UNACCEPTABLE"])

    print(f"Total PDFs Assessed: {len(results)}")
    print(f"  Excellent (>=95%): {excellent}")
    print(f"  Acceptable (85-94%): {acceptable}")
    print(f"  Marginal (70-84%): {marginal}")
    print(f"  Unacceptable (<70%): {unacceptable}")

    if results:
        avg_conf = sum(r.avg_confidence for r in results) / len(results)
        print(f"\nAverage Confidence: {avg_conf:.1f}%")

    # Common issues
    all_issues = []
    for r in results:
        all_issues.extend(r.issues)

    if all_issues:
        print("\nCommon Issues:")
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1])[:5]:
            print(f"  - {issue}: {count} PDFs")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Assess OCR quality for scanned PDFs"
    )
    parser.add_argument(
        "input",
        type=str,
        nargs="?",
        help="PDF file to assess"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Assess all scanned PDFs"
    )
    parser.add_argument(
        "--compare", type=str, nargs=2,
        metavar=("EXPECTED", "ACTUAL"),
        help="Compare expected text with actual OCR output"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=OUTPUT_DIR,
        help="Output directory for reports"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output JSON report"
    )

    args = parser.parse_args()

    assessor = OCRQualityAssessor()

    if args.compare:
        # Compare mode
        expected_path, actual_path = args.compare
        with open(expected_path, "r") as f:
            expected = f.read()
        with open(actual_path, "r") as f:
            actual = f.read()

        cer = calculate_cer(expected, actual)
        wer = calculate_wer(expected, actual)

        print(f"Character Error Rate: {cer:.2%}")
        print(f"Word Error Rate: {wer:.2%}")

    elif args.all:
        # Assess all scanned PDFs
        results = assessor.assess_all_scanned()
        print_summary(results)

        if args.json:
            assessor.generate_report(args.output_dir)

    elif args.input:
        # Assess single PDF
        pdf_path = Path(args.input)
        if not pdf_path.exists():
            logger.error(f"File not found: {pdf_path}")
            sys.exit(1)

        metrics = assessor.assess_pdf(pdf_path)
        print_assessment(metrics)

        if args.json:
            assessor.generate_report(args.output_dir)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
