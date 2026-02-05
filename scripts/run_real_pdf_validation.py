#!/usr/bin/env python3
"""
End-to-End Real PDF Validation Runner
======================================

Validates extraction accuracy against real PDFs with gold standard annotations.

Usage:
    python scripts/run_real_pdf_validation.py --all
    python scripts/run_real_pdf_validation.py --area cardiology
    python scripts/run_real_pdf_validation.py --pdf PMC7890123.pdf
    python scripts/run_real_pdf_validation.py --ci-mode  # For CI/CD pipelines

Outputs:
    - Console summary with accuracy metrics
    - output/pdf_validation_report.json - Detailed results
    - output/pdf_validation_report.html - Interactive report
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import traceback

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
TEST_PDFS_DIR = PROJECT_ROOT / "test_pdfs"
PMC_DIR = TEST_PDFS_DIR / "pmc_open_access"
REAL_PDFS_DIR = TEST_PDFS_DIR / "real_pdfs"
GOLD_STANDARD_DIR = TEST_PDFS_DIR / "gold_standard"
OUTPUT_DIR = PROJECT_ROOT / "output"
BASELINE_PATH = PROJECT_ROOT / "data" / "baselines" / "pdf_validation_baseline.json"
MANIFEST_PATH = TEST_PDFS_DIR / "manifest.json"


@dataclass
class ExtractionResult:
    """Result of extracting from a single PDF"""
    pdf_file: str
    trial_name: str
    therapeutic_area: str
    total_expected: int
    total_extracted: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    extraction_time_ms: float
    errors: List[str] = field(default_factory=list)
    mismatches: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Complete validation report"""
    generated: str
    total_pdfs: int
    pdfs_processed: int
    pdfs_failed: int
    overall_precision: float
    overall_recall: float
    overall_f1: float
    by_therapeutic_area: Dict[str, Dict[str, float]]
    by_effect_type: Dict[str, Dict[str, float]]
    results: List[ExtractionResult]
    errors: List[str]


class RealPDFValidator:
    """Validates extraction against real PDFs with gold standards"""

    def __init__(self, extractor=None):
        """Initialize validator with optional custom extractor"""
        self.extractor = extractor
        self.results: List[ExtractionResult] = []
        self.errors: List[str] = []

        # Lazy-load extractor
        if self.extractor is None:
            try:
                from src.core.enhanced_extractor_v3 import EnhancedExtractor
                self.extractor = EnhancedExtractor()
            except ImportError:
                logger.warning("EnhancedExtractor not available, using fallback")
                self.extractor = None

    def load_manifest(self) -> Dict[str, Any]:
        """Load PDF manifest"""
        if not MANIFEST_PATH.exists():
            return {"pdfs": [], "total_downloaded": 0}

        with open(MANIFEST_PATH, "r") as f:
            return json.load(f)

    def load_gold_standard(self, trial_name: str) -> Optional[List[Dict[str, Any]]]:
        """Load gold standard for a trial"""
        # Check gold_standard/annotations/ directory
        gold_file = GOLD_STANDARD_DIR / "annotations" / f"{trial_name}.gold.jsonl"
        if gold_file.exists():
            with open(gold_file, "r", encoding="utf-8") as f:
                return [json.loads(line) for line in f if line.strip()]

        # Check data/gold/ directory for matching entries
        gold_dir = PROJECT_ROOT / "data" / "gold"
        for jsonl_file in gold_dir.glob("*.jsonl"):
            try:
                with open(jsonl_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        data = json.loads(line)
                        if trial_name.lower() in data.get("trial_name", "").lower():
                            # Found matching entry - return expected extractions
                            return data.get("expected_extractions", [])
            except (json.JSONDecodeError, IOError, UnicodeDecodeError):
                continue

        return None

    def load_external_validation_trial(self, trial_name: str) -> Optional[Dict[str, Any]]:
        """Load trial from external validation dataset"""
        try:
            from data.external_validation_dataset import (
                ALL_EXTERNAL_VALIDATION_TRIALS,
                ExternalValidationTrial,
            )
            for trial in ALL_EXTERNAL_VALIDATION_TRIALS:
                if trial.trial_name.lower() == trial_name.lower():
                    # Convert consensus extractions to gold standard format
                    gold = []
                    for ext in trial.consensus or trial.extractor_a:
                        gold.append({
                            "effect_type": ext.effect_type,
                            "point_estimate": ext.effect_size,
                            "ci_lower": ext.ci_lower,
                            "ci_upper": ext.ci_upper,
                            "p_value": ext.p_value,
                            "outcome": ext.outcome,
                        })
                    return {
                        "trial_name": trial.trial_name,
                        "source_text": trial.source_text,
                        "gold_standard": gold,
                        "therapeutic_area": trial.therapeutic_area,
                    }
        except ImportError:
            pass
        return None

    def extract_from_pdf(self, pdf_path: Path) -> Tuple[List[Dict[str, Any]], float]:
        """Extract effect estimates from a PDF"""
        import time

        if self.extractor is None:
            return [], 0.0

        start_time = time.time()

        try:
            # Parse PDF
            from src.pdf.pdf_parser import PDFParser
            parser = PDFParser()
            pdf_content = parser.parse(str(pdf_path))

            # Extract text
            full_text = "\n".join(page.full_text for page in pdf_content.pages)

            # Run extraction
            results = self.extractor.extract(full_text)

            # Convert to standard format
            extractions = []
            for r in results:
                extractions.append({
                    "effect_type": getattr(r, "effect_type", "Unknown"),
                    "point_estimate": getattr(r, "effect_size", None) or getattr(r, "value", None),
                    "ci_lower": getattr(r, "ci_lower", None),
                    "ci_upper": getattr(r, "ci_upper", None),
                    "p_value": getattr(r, "p_value", None),
                    "outcome": getattr(r, "outcome", ""),
                    "confidence": getattr(r, "confidence", 0.0),
                })

            elapsed_ms = (time.time() - start_time) * 1000
            return extractions, elapsed_ms

        except Exception as e:
            logger.error(f"Extraction failed for {pdf_path.name}: {e}")
            traceback.print_exc()
            return [], (time.time() - start_time) * 1000

    def compare_extractions(
        self,
        extracted: List[Dict[str, Any]],
        expected: List[Dict[str, Any]],
        tolerance: float = 0.02
    ) -> Tuple[int, int, int, List[Dict[str, Any]]]:
        """Compare extracted vs expected effects

        Returns: (true_positives, false_positives, false_negatives, mismatches)
        """
        matched_expected = set()
        mismatches = []
        true_positives = 0

        for ext in extracted:
            found_match = False
            for i, exp in enumerate(expected):
                if i in matched_expected:
                    continue

                # Check effect type match
                if ext.get("effect_type") != exp.get("effect_type"):
                    continue

                # Check value match with tolerance
                ext_val = ext.get("point_estimate")
                exp_val = exp.get("point_estimate")
                if ext_val is None or exp_val is None:
                    continue

                if abs(ext_val - exp_val) <= tolerance * abs(exp_val):
                    # Check CI bounds
                    ext_lower = ext.get("ci_lower")
                    exp_lower = exp.get("ci_lower")
                    ext_upper = ext.get("ci_upper")
                    exp_upper = exp.get("ci_upper")

                    ci_match = True
                    if ext_lower and exp_lower:
                        ci_match = ci_match and abs(ext_lower - exp_lower) <= tolerance * abs(exp_lower)
                    if ext_upper and exp_upper:
                        ci_match = ci_match and abs(ext_upper - exp_upper) <= tolerance * abs(exp_upper)

                    if ci_match:
                        true_positives += 1
                        matched_expected.add(i)
                        found_match = True
                        break

            if not found_match:
                mismatches.append({
                    "type": "false_positive",
                    "extracted": ext,
                    "reason": "No matching expected effect"
                })

        # Find false negatives
        for i, exp in enumerate(expected):
            if i not in matched_expected:
                mismatches.append({
                    "type": "false_negative",
                    "expected": exp,
                    "reason": "Not found in extractions"
                })

        false_positives = len(extracted) - true_positives
        false_negatives = len(expected) - true_positives

        return true_positives, false_positives, false_negatives, mismatches

    def validate_pdf(self, pdf_record: Dict[str, Any]) -> ExtractionResult:
        """Validate a single PDF against gold standard"""
        trial_name = pdf_record.get("trial_name", pdf_record.get("filename", "Unknown"))
        pdf_path = TEST_PDFS_DIR / pdf_record.get("filepath", "")

        # Check PDF exists
        if not pdf_path.exists():
            return ExtractionResult(
                pdf_file=pdf_record.get("filename", "Unknown"),
                trial_name=trial_name,
                therapeutic_area=pdf_record.get("therapeutic_area", "Unknown"),
                total_expected=0,
                total_extracted=0,
                true_positives=0,
                false_positives=0,
                false_negatives=0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                extraction_time_ms=0.0,
                errors=[f"PDF not found: {pdf_path}"]
            )

        # Load gold standard
        gold = self.load_gold_standard(trial_name)
        if gold is None:
            # Try external validation dataset
            ext_trial = self.load_external_validation_trial(trial_name)
            if ext_trial:
                gold = ext_trial.get("gold_standard", [])

        if not gold:
            return ExtractionResult(
                pdf_file=pdf_record.get("filename", "Unknown"),
                trial_name=trial_name,
                therapeutic_area=pdf_record.get("therapeutic_area", "Unknown"),
                total_expected=0,
                total_extracted=0,
                true_positives=0,
                false_positives=0,
                false_negatives=0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                extraction_time_ms=0.0,
                errors=["No gold standard available"]
            )

        # Extract from PDF
        extracted, time_ms = self.extract_from_pdf(pdf_path)

        # Compare
        tp, fp, fn, mismatches = self.compare_extractions(extracted, gold)

        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return ExtractionResult(
            pdf_file=pdf_record.get("filename", "Unknown"),
            trial_name=trial_name,
            therapeutic_area=pdf_record.get("therapeutic_area", "Unknown"),
            total_expected=len(gold),
            total_extracted=len(extracted),
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            extraction_time_ms=time_ms,
            mismatches=mismatches
        )

    def validate_all(
        self,
        area_filter: Optional[str] = None,
        pdf_filter: Optional[str] = None,
        max_pdfs: Optional[int] = None
    ) -> ValidationReport:
        """Validate all PDFs matching filters"""
        manifest = self.load_manifest()
        pdfs = manifest.get("pdfs", [])

        # Apply filters
        if area_filter:
            pdfs = [p for p in pdfs if area_filter.lower() in p.get("therapeutic_area", "").lower()]

        if pdf_filter:
            pdfs = [p for p in pdfs if pdf_filter.lower() in p.get("filename", "").lower()]

        if max_pdfs:
            pdfs = pdfs[:max_pdfs]

        logger.info(f"Validating {len(pdfs)} PDFs...")

        # Validate each PDF
        results = []
        failed = 0
        for i, pdf in enumerate(pdfs, 1):
            logger.info(f"[{i}/{len(pdfs)}] Processing: {pdf.get('trial_name', pdf.get('filename'))}")
            try:
                result = self.validate_pdf(pdf)
                results.append(result)
                if result.errors:
                    failed += 1
            except Exception as e:
                logger.error(f"Validation failed: {e}")
                failed += 1
                self.errors.append(f"{pdf.get('filename')}: {str(e)}")

        # Calculate aggregate metrics
        total_tp = sum(r.true_positives for r in results)
        total_fp = sum(r.false_positives for r in results)
        total_fn = sum(r.false_negatives for r in results)

        overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0

        # By therapeutic area
        by_area = {}
        for r in results:
            area = r.therapeutic_area
            if area not in by_area:
                by_area[area] = {"tp": 0, "fp": 0, "fn": 0}
            by_area[area]["tp"] += r.true_positives
            by_area[area]["fp"] += r.false_positives
            by_area[area]["fn"] += r.false_negatives

        for area in by_area:
            tp = by_area[area]["tp"]
            fp = by_area[area]["fp"]
            fn = by_area[area]["fn"]
            by_area[area]["precision"] = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            by_area[area]["recall"] = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            by_area[area]["f1"] = 2 * by_area[area]["precision"] * by_area[area]["recall"] / (by_area[area]["precision"] + by_area[area]["recall"]) if (by_area[area]["precision"] + by_area[area]["recall"]) > 0 else 0.0

        return ValidationReport(
            generated=datetime.now().isoformat(),
            total_pdfs=len(pdfs),
            pdfs_processed=len(results),
            pdfs_failed=failed,
            overall_precision=overall_precision,
            overall_recall=overall_recall,
            overall_f1=overall_f1,
            by_therapeutic_area=by_area,
            by_effect_type={},  # TODO: implement
            results=[asdict(r) for r in results],
            errors=self.errors
        )

    def save_report(self, report: ValidationReport, output_dir: Path = OUTPUT_DIR) -> Path:
        """Save validation report"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # JSON report
        json_path = output_dir / "pdf_validation_report.json"
        with open(json_path, "w") as f:
            json.dump(asdict(report), f, indent=2)

        logger.info(f"Report saved: {json_path}")
        return json_path

    def generate_html_report(self, report: ValidationReport, output_dir: Path = OUTPUT_DIR) -> Path:
        """Generate interactive HTML report"""
        output_dir.mkdir(parents=True, exist_ok=True)
        html_path = output_dir / "pdf_validation_report.html"

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>PDF Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2196F3; }}
        .metric-label {{ color: #666; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
    </style>
</head>
<body>
    <h1>PDF Validation Report</h1>
    <p>Generated: {report.generated}</p>

    <div class="summary">
        <h2>Overall Metrics</h2>
        <div class="metric">
            <div class="metric-value">{report.overall_precision:.1%}</div>
            <div class="metric-label">Precision</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report.overall_recall:.1%}</div>
            <div class="metric-label">Recall</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report.overall_f1:.1%}</div>
            <div class="metric-label">F1 Score</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report.pdfs_processed}</div>
            <div class="metric-label">PDFs Processed</div>
        </div>
    </div>

    <h2>Results by PDF</h2>
    <table>
        <tr>
            <th>Trial</th>
            <th>Area</th>
            <th>Expected</th>
            <th>Extracted</th>
            <th>TP</th>
            <th>FP</th>
            <th>FN</th>
            <th>Precision</th>
            <th>Recall</th>
            <th>F1</th>
        </tr>
"""
        for r in report.results:
            status_class = "pass" if r.get("f1_score", 0) >= 0.9 else "fail"
            html_content += f"""        <tr class="{status_class}">
            <td>{r.get('trial_name', 'Unknown')}</td>
            <td>{r.get('therapeutic_area', 'Unknown')}</td>
            <td>{r.get('total_expected', 0)}</td>
            <td>{r.get('total_extracted', 0)}</td>
            <td>{r.get('true_positives', 0)}</td>
            <td>{r.get('false_positives', 0)}</td>
            <td>{r.get('false_negatives', 0)}</td>
            <td>{r.get('precision', 0):.1%}</td>
            <td>{r.get('recall', 0):.1%}</td>
            <td>{r.get('f1_score', 0):.1%}</td>
        </tr>
"""

        html_content += """    </table>
</body>
</html>"""

        with open(html_path, "w") as f:
            f.write(html_content)

        logger.info(f"HTML report saved: {html_path}")
        return html_path


def print_summary(report: ValidationReport):
    """Print validation summary to console"""
    print("\n" + "=" * 70)
    print("PDF VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Generated: {report.generated}")
    print(f"PDFs Processed: {report.pdfs_processed}/{report.total_pdfs}")
    print(f"PDFs Failed: {report.pdfs_failed}")
    print("-" * 70)
    print(f"Overall Precision: {report.overall_precision:.1%}")
    print(f"Overall Recall: {report.overall_recall:.1%}")
    print(f"Overall F1 Score: {report.overall_f1:.1%}")
    print("-" * 70)

    if report.by_therapeutic_area:
        print("\nBy Therapeutic Area:")
        for area, metrics in sorted(report.by_therapeutic_area.items()):
            print(f"  {area}: P={metrics.get('precision', 0):.1%}, "
                  f"R={metrics.get('recall', 0):.1%}, "
                  f"F1={metrics.get('f1', 0):.1%}")

    if report.errors:
        print(f"\nErrors ({len(report.errors)}):")
        for error in report.errors[:5]:
            print(f"  - {error}")
        if len(report.errors) > 5:
            print(f"  ... and {len(report.errors) - 5} more")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Validate extraction accuracy against real PDFs"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Validate all available PDFs"
    )
    parser.add_argument(
        "--area", type=str,
        help="Filter by therapeutic area (e.g., 'cardiology', 'oncology')"
    )
    parser.add_argument(
        "--pdf", type=str,
        help="Validate specific PDF by filename"
    )
    parser.add_argument(
        "--max", type=int,
        help="Maximum number of PDFs to validate"
    )
    parser.add_argument(
        "--ci-mode", action="store_true",
        help="CI mode: reduced output, exit code based on results"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.95,
        help="Minimum F1 score threshold for CI pass (default: 0.95)"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=OUTPUT_DIR,
        help="Output directory for reports"
    )
    parser.add_argument(
        "--html", action="store_true",
        help="Generate HTML report"
    )

    args = parser.parse_args()

    validator = RealPDFValidator()

    # Run validation
    report = validator.validate_all(
        area_filter=args.area,
        pdf_filter=args.pdf,
        max_pdfs=args.max
    )

    # Save reports
    validator.save_report(report, args.output_dir)

    if args.html:
        validator.generate_html_report(report, args.output_dir)

    # Print summary
    if not args.ci_mode:
        print_summary(report)

    # CI mode exit code
    if args.ci_mode:
        if report.overall_f1 >= args.threshold:
            print(f"PASS: F1 score {report.overall_f1:.1%} >= {args.threshold:.1%}")
            sys.exit(0)
        else:
            print(f"FAIL: F1 score {report.overall_f1:.1%} < {args.threshold:.1%}")
            sys.exit(1)


if __name__ == "__main__":
    main()
