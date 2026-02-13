#!/usr/bin/env python3
"""
Full PDF Validation Suite for RCT Extractor v4.0.5
==================================================

Comprehensive PDF validation against the full test collection.
Generates detailed accuracy reports for all categories.

Usage:
    python run_pdf_validation_suite.py
    python run_pdf_validation_suite.py --category cardiovascular
    python run_pdf_validation_suite.py --gold-standard
    python run_pdf_validation_suite.py --verbose --output report.json

Targets:
    - Born-digital accuracy: >98%
    - Scanned PDF accuracy: >90%
    - Table extraction: >95%
    - Forest plot extraction: >80%
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pdf.pdf_parser import PDFParser, PDFContent
from src.core.ocr_preprocessor import OCRPreprocessor
from src.core.enhanced_extractor_v3 import EnhancedExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PDFValidationResult:
    """Result of validating one PDF"""
    pdf_path: str
    trial_name: str
    category: str
    extraction_method: str
    page_count: int
    text_length: int
    effects_found: int
    effects_expected: int
    effects_matched: int
    accuracy: float
    processing_time: float
    errors: List[str] = field(default_factory=list)


@dataclass
class CategoryMetrics:
    """Metrics for one category"""
    pdfs_tested: int = 0
    total_effects_expected: int = 0
    total_effects_matched: int = 0
    accuracy: float = 0.0
    avg_processing_time: float = 0.0


class PDFValidationSuite:
    """Full PDF validation suite"""

    def __init__(self, test_pdfs_dir: Optional[Path] = None):
        self.test_pdfs_dir = test_pdfs_dir or (Path(__file__).parent / "test_pdfs")
        self.parser = PDFParser()
        self.preprocessor = OCRPreprocessor()
        self.extractor = EnhancedExtractor()
        self.results: List[PDFValidationResult] = []
        self.gold_standard = self._load_gold_standard()

    def _load_gold_standard(self) -> Dict[str, Dict]:
        """Load gold standard annotations"""
        gold = {}
        annotations_dir = self.test_pdfs_dir / "gold_standard" / "annotations"

        for f in annotations_dir.glob("*.gold.jsonl"):
            try:
                with open(f) as file:
                    data = json.loads(file.read())
                    trial_name = data.get("trial_name", f.stem.replace(".gold", ""))
                    gold[trial_name] = data
            except (json.JSONDecodeError, IOError):
                continue

        return gold

    def _get_expected_effects(self, pdf_path: Path) -> List[Dict]:
        """Get expected effects for a PDF"""
        # Try to match with gold standard
        trial_name = pdf_path.stem.replace("_", "-").upper()

        for name, data in self.gold_standard.items():
            if name.upper() in trial_name or trial_name in name.upper():
                return data.get("effects", [])

        # Try to match with external validation dataset
        try:
            from data.external_validation_dataset import get_trial_by_name

            # Try various name formats
            for try_name in [pdf_path.stem, pdf_path.stem.replace("_", "-"),
                           pdf_path.stem.replace("PMC", "")]:
                trial = get_trial_by_name(try_name)
                if trial and trial.extractor_a:
                    return [
                        {
                            "effect_type": e.effect_type,
                            "value": e.effect_size,
                            "ci_lower": e.ci_lower,
                            "ci_upper": e.ci_upper,
                        }
                        for e in trial.extractor_a
                    ]
        except ImportError:
            pass

        return []

    def validate_pdf(self, pdf_path: Path, category: str = "unknown") -> PDFValidationResult:
        """Validate a single PDF"""
        logger.info(f"Validating: {pdf_path.name}")

        start_time = time.time()
        errors = []

        try:
            # Parse PDF
            content = self.parser.parse(str(pdf_path))

            # Get full text
            full_text = "\n\n".join(page.full_text for page in content.pages)

            # Preprocess if OCR
            if content.extraction_method == "ocr":
                full_text = self.preprocessor.preprocess(full_text)

            # Extract effects
            extracted = self.extractor.extract(full_text)

            # Get expected effects
            expected = self._get_expected_effects(pdf_path)

            # Match effects
            matched = 0
            for exp in expected:
                exp_value = exp.get("value", 0)
                for ext in extracted:
                    ext_value = getattr(ext, "effect_size", getattr(ext, "value", 0))
                    if abs(ext_value - exp_value) < 0.02:
                        matched += 1
                        break

            accuracy = matched / len(expected) if expected else 1.0 if extracted else 0.0

            return PDFValidationResult(
                pdf_path=str(pdf_path),
                trial_name=pdf_path.stem,
                category=category,
                extraction_method=content.extraction_method,
                page_count=len(content.pages),
                text_length=len(full_text),
                effects_found=len(extracted),
                effects_expected=len(expected),
                effects_matched=matched,
                accuracy=accuracy,
                processing_time=time.time() - start_time,
                errors=errors,
            )

        except Exception as e:
            return PDFValidationResult(
                pdf_path=str(pdf_path),
                trial_name=pdf_path.stem,
                category=category,
                extraction_method="error",
                page_count=0,
                text_length=0,
                effects_found=0,
                effects_expected=0,
                effects_matched=0,
                accuracy=0.0,
                processing_time=time.time() - start_time,
                errors=[str(e)],
            )

    def validate_category(self, category: str, pdfs: List[Path]) -> CategoryMetrics:
        """Validate all PDFs in a category"""
        logger.info(f"\n{'='*60}")
        logger.info(f"VALIDATING CATEGORY: {category}")
        logger.info(f"PDFs: {len(pdfs)}")
        logger.info(f"{'='*60}")

        metrics = CategoryMetrics()
        processing_times = []

        for pdf in pdfs:
            result = self.validate_pdf(pdf, category)
            self.results.append(result)

            metrics.pdfs_tested += 1
            metrics.total_effects_expected += result.effects_expected
            metrics.total_effects_matched += result.effects_matched
            processing_times.append(result.processing_time)

            status = "PASS" if result.accuracy >= 0.8 else "WARN" if result.accuracy >= 0.5 else "FAIL"
            logger.info(f"  [{status}] {pdf.name}: {result.accuracy:.1%} "
                       f"({result.effects_matched}/{result.effects_expected}) "
                       f"in {result.processing_time:.1f}s")

        if metrics.total_effects_expected > 0:
            metrics.accuracy = metrics.total_effects_matched / metrics.total_effects_expected
        metrics.avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0

        return metrics

    def run_full_validation(self, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run full validation suite"""
        logger.info("\n" + "=" * 70)
        logger.info("RCT EXTRACTOR - PDF VALIDATION SUITE")
        logger.info("=" * 70)

        # Define category paths
        pmc_dir = self.test_pdfs_dir / "pmc_open_access"

        category_paths = {
            "cardiovascular": pmc_dir / "born_digital" / "cardiovascular",
            "oncology": pmc_dir / "born_digital" / "oncology",
            "other": pmc_dir / "born_digital" / "other",
            "scanned": pmc_dir / "scanned",
        }

        # Add edge cases
        edge_cases_dir = self.test_pdfs_dir / "edge_cases"
        category_paths["multi_column"] = edge_cases_dir / "multi_column"
        category_paths["forest_plots"] = edge_cases_dir / "forest_plots"
        category_paths["tables"] = edge_cases_dir / "tables_spanning_pages"

        # Filter categories if specified
        if categories:
            category_paths = {k: v for k, v in category_paths.items() if k in categories}

        # Validate each category
        all_metrics = {}
        for category, path in category_paths.items():
            if path.exists():
                pdfs = list(path.glob("*.pdf"))
                if pdfs:
                    all_metrics[category] = self.validate_category(category, pdfs)

        return self.generate_report(all_metrics)

    def validate_gold_standard(self) -> Dict[str, Any]:
        """Validate against gold standard only"""
        logger.info("\n" + "=" * 70)
        logger.info("GOLD STANDARD VALIDATION")
        logger.info("=" * 70)

        gold_pdfs_dir = self.test_pdfs_dir / "gold_standard" / "pdfs"
        pdfs = list(gold_pdfs_dir.glob("*.pdf"))

        if not pdfs:
            logger.warning("No gold standard PDFs found")
            return {"error": "No gold standard PDFs"}

        metrics = self.validate_category("gold_standard", pdfs)

        return self.generate_report({"gold_standard": metrics})

    def generate_report(self, metrics: Dict[str, CategoryMetrics]) -> Dict[str, Any]:
        """Generate validation report"""
        # Calculate overall metrics
        total_tested = sum(m.pdfs_tested for m in metrics.values())
        total_expected = sum(m.total_effects_expected for m in metrics.values())
        total_matched = sum(m.total_effects_matched for m in metrics.values())
        overall_accuracy = total_matched / total_expected if total_expected > 0 else 0

        # Categorize by type
        born_digital_metrics = {k: v for k, v in metrics.items()
                                if k in ["cardiovascular", "oncology", "other"]}
        scanned_metrics = {k: v for k, v in metrics.items() if k == "scanned"}

        # Calculate type-specific accuracy
        bd_expected = sum(m.total_effects_expected for m in born_digital_metrics.values())
        bd_matched = sum(m.total_effects_matched for m in born_digital_metrics.values())
        bd_accuracy = bd_matched / bd_expected if bd_expected > 0 else 0

        sc_expected = sum(m.total_effects_expected for m in scanned_metrics.values())
        sc_matched = sum(m.total_effects_matched for m in scanned_metrics.values())
        sc_accuracy = sc_matched / sc_expected if sc_expected > 0 else 0

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_pdfs_tested": total_tested,
                "total_effects_expected": total_expected,
                "total_effects_matched": total_matched,
                "overall_accuracy": overall_accuracy,
                "born_digital_accuracy": bd_accuracy,
                "scanned_accuracy": sc_accuracy,
            },
            "targets": {
                "born_digital": {"target": 0.98, "actual": bd_accuracy, "passed": bd_accuracy >= 0.98},
                "scanned": {"target": 0.90, "actual": sc_accuracy, "passed": sc_accuracy >= 0.90},
            },
            "by_category": {
                name: {
                    "pdfs_tested": m.pdfs_tested,
                    "effects_expected": m.total_effects_expected,
                    "effects_matched": m.total_effects_matched,
                    "accuracy": m.accuracy,
                    "avg_processing_time": m.avg_processing_time,
                }
                for name, m in metrics.items()
            },
            "results": [asdict(r) for r in self.results],
            "errors": [asdict(r) for r in self.results if r.errors],
        }

        return report


def print_report(report: Dict[str, Any]):
    """Print formatted report"""
    print("\n" + "=" * 70)
    print("PDF VALIDATION REPORT")
    print("=" * 70)

    summary = report["summary"]
    print(f"\nTimestamp: {report['timestamp']}")
    print(f"\nOverall Summary:")
    print(f"  PDFs tested:         {summary['total_pdfs_tested']}")
    print(f"  Effects expected:    {summary['total_effects_expected']}")
    print(f"  Effects matched:     {summary['total_effects_matched']}")
    print(f"  Overall accuracy:    {summary['overall_accuracy']:.1%}")
    print(f"  Born-digital:        {summary['born_digital_accuracy']:.1%}")
    print(f"  Scanned:             {summary['scanned_accuracy']:.1%}")

    print(f"\nTargets:")
    for name, target in report["targets"].items():
        status = "PASS" if target["passed"] else "FAIL"
        print(f"  {name}: {target['actual']:.1%} vs {target['target']:.0%} [{status}]")

    print(f"\nBy Category:")
    for name, stats in report["by_category"].items():
        print(f"  {name}:")
        print(f"    PDFs: {stats['pdfs_tested']}, Accuracy: {stats['accuracy']:.1%}, "
              f"Avg time: {stats['avg_processing_time']:.1f}s")

    if report["errors"]:
        print(f"\nErrors ({len(report['errors'])}):")
        for err in report["errors"][:10]:
            print(f"  - {err['trial_name']}: {err['errors']}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Run full PDF validation suite"
    )
    parser.add_argument(
        "--category", "-c",
        nargs="+",
        help="Validate specific categories only"
    )
    parser.add_argument(
        "--gold-standard", "-g",
        action="store_true",
        help="Validate against gold standard only"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output JSON report file"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    suite = PDFValidationSuite()

    if args.gold_standard:
        report = suite.validate_gold_standard()
    else:
        report = suite.run_full_validation(categories=args.category)

    # Print report
    print_report(report)

    # Save to file
    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to: {args.output}")

    # Check targets
    bd_passed = report["targets"].get("born_digital", {}).get("passed", True)
    sc_passed = report["targets"].get("scanned", {}).get("passed", True)

    if not (bd_passed and sc_passed):
        logger.warning("Some accuracy targets not met")
        sys.exit(1)


if __name__ == "__main__":
    main()
