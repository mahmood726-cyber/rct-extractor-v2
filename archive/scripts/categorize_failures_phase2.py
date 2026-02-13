#!/usr/bin/env python3
"""
Phase 2: Failure Categorization Script

Categorizes extraction failures into:
- NOT_REPORTED: Source paper doesn't report CI
- IN_TABLE: CI exists but in table format
- PATTERN_GAP: CI in text but pattern missed
- TEXT_FRAGMENTED: CI split across columns/pages
- OCR_ERROR: Text extraction corrupted

For zero-extraction PDFs:
- NON_RCT: Not an RCT results paper
- TABLE_ONLY: All effects in tables
- UNUSUAL_FORMAT: Effects in non-standard format
- PARSE_FAILURE: PDF text extraction failed

Usage:
    python scripts/categorize_failures_phase2.py --ground-truth data/pdf_ground_truth_merged.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.enhanced_extractor_v3 import EnhancedExtractor
from src.pdf.pdf_parser import PDFParser


# Failure categories
MISSING_CI_CATEGORIES = [
    "NOT_REPORTED",     # Paper doesn't report CI for this effect
    "IN_TABLE",         # CI is in a table (values separated)
    "PATTERN_GAP",      # CI in text but our patterns miss it
    "TEXT_FRAGMENTED",  # CI split across columns/pages
    "OCR_ERROR",        # Text extraction corrupted the CI
    "VALUE_MISMATCH",   # Wrong value extracted, CI belongs to different effect
    "UNKNOWN",          # Unable to determine cause
]

ZERO_EXTRACTION_CATEGORIES = [
    "NON_RCT",          # Not an RCT paper (review, methods, etc)
    "TABLE_ONLY",       # All effects in tables only
    "UNUSUAL_FORMAT",   # Non-standard effect reporting format
    "PARSE_FAILURE",    # PDF text extraction failed
    "NO_EFFECTS",       # Paper genuinely doesn't report relevant effects
    "UNKNOWN",          # Unable to determine cause
]


class FailureCategorizer:
    def __init__(self):
        self.parser = PDFParser()
        self.extractor = EnhancedExtractor()

        # Patterns to detect CI in text (even if not extracted)
        self.ci_patterns = [
            r'95%?\s*(?:CI|confidence\s+interval)[:\s,]*[\[(]?\s*(\d+\.?\d*)\s*[-–—to]+\s*(\d+\.?\d*)',
            r'[\[(]\s*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\])]',
            r'CI[:\s]+(\d+\.?\d*)\s*[-–—to]+\s*(\d+\.?\d*)',
        ]

        # Patterns to detect table indicators
        self.table_indicators = [
            r'\|.*\|.*\|',           # Pipe-separated columns
            r'\t.*\t.*\t',           # Tab-separated
            r'^\s*\d+\.?\d*\s+\d+\.?\d*\s+\d+\.?\d*',  # Space-separated numbers
        ]

    def find_ci_in_text(self, text: str, value: float, window: int = 300) -> Optional[Tuple[float, float, str]]:
        """Search for CI around a value in text."""
        value_patterns = [
            str(value),
            f"{value:.2f}",
            f"{value:.1f}",
            f"{value:.3f}",
        ]

        for val_pat in value_patterns:
            for match in re.finditer(re.escape(val_pat), text):
                # Get context around the value
                start = max(0, match.start() - window)
                end = min(len(text), match.end() + window)
                context = text[start:end]

                # Look for CI in context
                for ci_pat in self.ci_patterns:
                    ci_match = re.search(ci_pat, context, re.IGNORECASE)
                    if ci_match:
                        try:
                            ci_lower = float(ci_match.group(1))
                            ci_upper = float(ci_match.group(2))
                            # Sanity check: CI should bracket the value
                            if ci_lower <= value <= ci_upper or ci_lower >= value >= ci_upper:
                                return (ci_lower, ci_upper, context)
                        except (ValueError, IndexError):
                            continue

        return None

    def detect_table_format(self, text: str, value: float) -> bool:
        """Check if value appears to be in a table."""
        lines = text.split('\n')

        for i, line in enumerate(lines):
            if str(value) in line or f"{value:.2f}" in line:
                # Check if line looks like table row
                for pattern in self.table_indicators:
                    if re.search(pattern, line):
                        return True
                # Check for multiple numbers in line (table-like)
                numbers = re.findall(r'\d+\.?\d*', line)
                if len(numbers) >= 3:
                    return True

        return False

    def detect_multi_column(self, text: str) -> bool:
        """Detect if text shows signs of multi-column fragmentation."""
        lines = text.split('\n')

        # Check for short lines alternating (sign of columns)
        short_lines = sum(1 for l in lines if 10 < len(l.strip()) < 50)
        if short_lines > len(lines) * 0.4:
            return True

        # Check for sentence fragments
        fragments = sum(1 for l in lines if l.strip() and not l.strip().endswith(('.', ':', ';', ',')))
        if fragments > len(lines) * 0.3:
            return True

        return False

    def categorize_missing_ci(self, pdf_path: Path, gt_entry: dict, extraction: Optional[dict]) -> dict:
        """Categorize why CI is missing for an extraction."""
        result = {
            "pdf": pdf_path.name,
            "ground_truth": gt_entry,
            "extraction": extraction,
            "category": "UNKNOWN",
            "evidence": "",
            "context": "",
        }

        try:
            pdf_content = self.parser.parse(str(pdf_path))
            text = "\n".join(page.full_text for page in pdf_content.pages)
            if not text or len(text) < 100:
                result["category"] = "PARSE_FAILURE"
                result["evidence"] = "Unable to extract text from PDF"
                return result

            gt_value = gt_entry.get("value")
            gt_ci_lower = gt_entry.get("ci_lower")
            gt_ci_upper = gt_entry.get("ci_upper")

            # Check if ground truth CI exists in text
            ci_found = self.find_ci_in_text(text, gt_value)

            if ci_found:
                ci_lower, ci_upper, context = ci_found
                result["context"] = context[:500]

                # CI exists in text but wasn't extracted
                if self.detect_table_format(text, gt_value):
                    result["category"] = "IN_TABLE"
                    result["evidence"] = f"Found CI ({ci_lower}, {ci_upper}) in table-like format"
                elif self.detect_multi_column(context):
                    result["category"] = "TEXT_FRAGMENTED"
                    result["evidence"] = f"Found CI ({ci_lower}, {ci_upper}) but text appears fragmented"
                else:
                    result["category"] = "PATTERN_GAP"
                    result["evidence"] = f"Found CI ({ci_lower}, {ci_upper}) in text but pattern didn't match"
            else:
                # CI not found in text
                if gt_ci_lower is not None and gt_ci_upper is not None:
                    # Ground truth has CI but we can't find it
                    if self.detect_table_format(text, gt_value):
                        result["category"] = "IN_TABLE"
                        result["evidence"] = "Value appears in table, CI may be in separate cell"
                    else:
                        result["category"] = "NOT_REPORTED"
                        result["evidence"] = "CI not found in extracted text"
                else:
                    result["category"] = "NOT_REPORTED"
                    result["evidence"] = "Ground truth indicates no CI reported"

        except Exception as e:
            result["category"] = "PARSE_FAILURE"
            result["evidence"] = str(e)

        return result

    def categorize_zero_extraction(self, pdf_path: Path, classification: dict = None) -> dict:
        """Categorize why a PDF has zero extractions."""
        result = {
            "pdf": pdf_path.name,
            "category": "UNKNOWN",
            "evidence": "",
            "text_sample": "",
            "classification": classification.get("classification") if classification else None,
        }

        try:
            pdf_content = self.parser.parse(str(pdf_path))
            text = "\n".join(page.full_text for page in pdf_content.pages)
            if not text or len(text) < 100:
                result["category"] = "PARSE_FAILURE"
                result["evidence"] = f"Text extraction failed or very short ({len(text) if text else 0} chars)"
                return result

            result["text_sample"] = text[:500]
            text_lower = text.lower()

            # Check for non-RCT indicators
            non_rct_keywords = [
                "systematic review", "meta-analysis", "pooled analysis",
                "editorial", "commentary", "perspective", "guideline",
                "consensus statement", "methodological", "protocol"
            ]

            non_rct_count = sum(1 for kw in non_rct_keywords if kw in text_lower)
            if non_rct_count >= 2:
                result["category"] = "NON_RCT"
                result["evidence"] = f"Found {non_rct_count} non-RCT keywords"
                return result

            # Check for table-only format
            table_lines = sum(1 for line in text.split('\n')
                            if re.search(r'\d+\.?\d*\s+\d+\.?\d*', line))
            if table_lines > 10:
                result["category"] = "TABLE_ONLY"
                result["evidence"] = f"Found {table_lines} table-like lines"
                return result

            # Check for unusual effect formats
            has_effect_words = any(w in text_lower for w in
                                   ["hazard ratio", "odds ratio", "relative risk", "mean difference"])
            has_numbers = bool(re.search(r'\d+\.\d+', text))

            if has_effect_words and has_numbers:
                result["category"] = "UNUSUAL_FORMAT"
                result["evidence"] = "Has effect terminology and numbers but no extractions"
            else:
                result["category"] = "NO_EFFECTS"
                result["evidence"] = "No recognizable effect terminology found"

        except Exception as e:
            result["category"] = "PARSE_FAILURE"
            result["evidence"] = str(e)

        return result


def run_failure_analysis(
    pdf_dir: Path,
    classification_path: Path,
    ground_truth_path: Optional[Path],
    output_path: Path
) -> dict:
    """Run comprehensive failure analysis."""
    categorizer = FailureCategorizer()
    extractor = EnhancedExtractor()
    parser = PDFParser()

    # Load classification
    with open(classification_path) as f:
        classification = json.load(f)

    # Load ground truth if available
    ground_truth = None
    if ground_truth_path and ground_truth_path.exists():
        with open(ground_truth_path) as f:
            ground_truth = json.load(f)

    # Create lookup tables
    pdf_classification = {p["filename"]: p for p in classification["pdfs"]}
    gt_by_pdf = defaultdict(list)
    if ground_truth:
        for entry in ground_truth.get("entries", []):
            gt_by_pdf[entry["pdf"]].append(entry)

    results = {
        "date": datetime.now().isoformat(),
        "classification_file": str(classification_path),
        "ground_truth_file": str(ground_truth_path) if ground_truth_path else None,
        "summary": {
            "total_pdfs": 0,
            "zero_extraction_pdfs": 0,
            "missing_ci_extractions": 0,
            "by_missing_ci_category": defaultdict(int),
            "by_zero_extraction_category": defaultdict(int),
        },
        "missing_ci_failures": [],
        "zero_extraction_failures": [],
    }

    # Find all PDFs
    pdf_files = list(pdf_dir.rglob("*.pdf"))
    results["summary"]["total_pdfs"] = len(pdf_files)

    print(f"Analyzing {len(pdf_files)} PDFs for failure categorization...")
    print("-" * 60)

    for i, pdf_path in enumerate(sorted(pdf_files)):
        print(f"[{i+1}/{len(pdf_files)}] {pdf_path.name}...", end=" ")

        cls_info = pdf_classification.get(pdf_path.name, {})
        extractions = cls_info.get("extractions", [])

        if not extractions:
            # Zero-extraction PDF
            results["summary"]["zero_extraction_pdfs"] += 1
            failure = categorizer.categorize_zero_extraction(pdf_path, cls_info)
            results["zero_extraction_failures"].append(failure)
            results["summary"]["by_zero_extraction_category"][failure["category"]] += 1
            print(f"ZERO: {failure['category']}")

        else:
            # Check for missing CIs
            missing_ci = [e for e in extractions if not e.get("ci_complete")]

            for ext in missing_ci:
                results["summary"]["missing_ci_extractions"] += 1

                # Find corresponding ground truth if available
                gt_entries = gt_by_pdf.get(pdf_path.name, [])
                matching_gt = None
                for gt in gt_entries:
                    if gt.get("effect_type") == ext.get("effect_type"):
                        if abs(gt.get("value", 0) - ext.get("value", 0)) < 0.01:
                            matching_gt = gt
                            break

                failure = categorizer.categorize_missing_ci(pdf_path, matching_gt or ext, ext)
                results["missing_ci_failures"].append(failure)
                results["summary"]["by_missing_ci_category"][failure["category"]] += 1

            ci_count = sum(1 for e in extractions if e.get("ci_complete"))
            print(f"OK: {len(extractions)} extractions, {ci_count} with CI")

    # Convert defaultdicts to regular dicts for JSON
    results["summary"]["by_missing_ci_category"] = dict(results["summary"]["by_missing_ci_category"])
    results["summary"]["by_zero_extraction_category"] = dict(results["summary"]["by_zero_extraction_category"])

    # Save results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print("-" * 60)
    print("\nFailure Analysis Summary")
    print("=" * 40)
    print(f"Total PDFs: {results['summary']['total_pdfs']}")
    print(f"\nZero-Extraction PDFs: {results['summary']['zero_extraction_pdfs']}")
    for cat, count in sorted(results["summary"]["by_zero_extraction_category"].items()):
        pct = count / max(results["summary"]["zero_extraction_pdfs"], 1) * 100
        print(f"  {cat}: {count} ({pct:.1f}%)")

    print(f"\nMissing CI Extractions: {results['summary']['missing_ci_extractions']}")
    for cat, count in sorted(results["summary"]["by_missing_ci_category"].items()):
        pct = count / max(results["summary"]["missing_ci_extractions"], 1) * 100
        print(f"  {cat}: {count} ({pct:.1f}%)")

    print(f"\nResults saved to: {output_path}")

    return results


def generate_failure_report(failure_path: Path, output_path: Path):
    """Generate a detailed markdown report of failures."""
    with open(failure_path) as f:
        data = json.load(f)

    lines = [
        "# Extraction Failure Analysis Report",
        f"\nGenerated: {datetime.now().isoformat()}",
        "",
        "## Summary",
        f"- Total PDFs analyzed: {data['summary']['total_pdfs']}",
        f"- Zero-extraction PDFs: {data['summary']['zero_extraction_pdfs']}",
        f"- Extractions missing CI: {data['summary']['missing_ci_extractions']}",
        "",
        "## Zero-Extraction Categories",
        "",
    ]

    # Zero extraction breakdown
    for cat, count in sorted(data["summary"]["by_zero_extraction_category"].items(), key=lambda x: -x[1]):
        lines.append(f"### {cat}: {count} PDFs")
        failures = [f for f in data["zero_extraction_failures"] if f["category"] == cat]
        for f in failures[:5]:  # Show first 5 examples
            lines.append(f"- **{f['pdf']}**: {f['evidence']}")
        if len(failures) > 5:
            lines.append(f"- ... and {len(failures) - 5} more")
        lines.append("")

    lines.append("## Missing CI Categories")
    lines.append("")

    # Missing CI breakdown
    for cat, count in sorted(data["summary"]["by_missing_ci_category"].items(), key=lambda x: -x[1]):
        lines.append(f"### {cat}: {count} extractions")
        failures = [f for f in data["missing_ci_failures"] if f["category"] == cat]
        for f in failures[:5]:
            ext = f.get("extraction", {})
            lines.append(f"- **{f['pdf']}**: {ext.get('effect_type')} = {ext.get('value')}")
            lines.append(f"  - Evidence: {f['evidence']}")
        if len(failures) > 5:
            lines.append(f"- ... and {len(failures) - 5} more")
        lines.append("")

    # Recommendations
    lines.extend([
        "## Recommendations",
        "",
        "### High Priority Fixes",
    ])

    # Prioritize by count
    if data["summary"]["by_missing_ci_category"].get("PATTERN_GAP", 0) > 5:
        lines.append("1. **PATTERN_GAP**: Add new regex patterns for unmatched CI formats")
    if data["summary"]["by_missing_ci_category"].get("IN_TABLE", 0) > 5:
        lines.append("2. **IN_TABLE**: Implement table extraction using pdfplumber")
    if data["summary"]["by_missing_ci_category"].get("TEXT_FRAGMENTED", 0) > 5:
        lines.append("3. **TEXT_FRAGMENTED**: Add multi-column reordering in PDF parser")
    if data["summary"]["by_zero_extraction_category"].get("NON_RCT", 0) > 5:
        lines.append("4. **NON_RCT**: Improve corpus curation to exclude non-RCT papers")

    report = "\n".join(lines)

    with open(output_path, "w") as f:
        f.write(report)

    print(f"Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Categorize extraction failures")
    parser.add_argument("--pdf-dir", type=Path, default=Path("test_pdfs/real_pdfs"),
                       help="Directory containing PDFs")
    parser.add_argument("--classification", type=Path, default=Path("data/pdf_classification.json"),
                       help="Path to classification JSON")
    parser.add_argument("--ground-truth", type=Path, default=None,
                       help="Path to ground truth JSON (optional)")
    parser.add_argument("--output", type=Path, default=Path("output/failure_categorization.json"),
                       help="Output failure analysis file")
    parser.add_argument("--report", action="store_true",
                       help="Generate markdown report")
    parser.add_argument("--report-output", type=Path, default=Path("output/failure_analysis_report.md"),
                       help="Output path for markdown report")

    args = parser.parse_args()

    if args.report and args.output.exists():
        generate_failure_report(args.output, args.report_output)
    elif args.classification.exists():
        run_failure_analysis(args.pdf_dir, args.classification, args.ground_truth, args.output)
        if args.report:
            generate_failure_report(args.output, args.report_output)
    else:
        print(f"Classification file not found: {args.classification}")
        print("Run classify_pdfs_phase1.py first")


if __name__ == "__main__":
    main()
