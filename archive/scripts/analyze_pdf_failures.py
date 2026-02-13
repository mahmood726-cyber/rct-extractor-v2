#!/usr/bin/env python3
"""
Analyze PDF Extraction Failures
===============================

Investigates why some PDFs have 0 extractions or missing CIs.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf.pdf_parser import PDFParser
from src.core.enhanced_extractor_v3 import EnhancedExtractor

PROJECT_ROOT = Path(__file__).parent.parent
VALIDATION_FILE = PROJECT_ROOT / "output" / "expanded_rct_validation.json"


def analyze_zero_extraction_pdfs():
    """Find why PDFs have 0 extractions"""
    with open(VALIDATION_FILE) as f:
        data = json.load(f)

    parser = PDFParser()
    extractor = EnhancedExtractor()

    print("=" * 70)
    print("ANALYZING ZERO-EXTRACTION PDFs")
    print("=" * 70)

    zero_pdfs = [r for r in data["results"] if r["extraction_count"] == 0]
    print(f"\nPDFs with 0 extractions: {len(zero_pdfs)}")

    for result in zero_pdfs[:5]:  # Analyze first 5
        pdf_path = result["pdf_path"]
        pdf_name = Path(pdf_path).name

        print(f"\n{'='*60}")
        print(f"PDF: {pdf_name}")
        print(f"{'='*60}")

        try:
            content = parser.parse(pdf_path)
            full_text = "\n".join(p.full_text for p in content.pages)

            # Check for effect keywords
            hr_count = len(re.findall(r'hazard\s+ratio', full_text, re.IGNORECASE))
            or_count = len(re.findall(r'odds\s+ratio', full_text, re.IGNORECASE))
            rr_count = len(re.findall(r'relative\s+risk|risk\s+ratio', full_text, re.IGNORECASE))
            md_count = len(re.findall(r'mean\s+difference', full_text, re.IGNORECASE))
            ci_count = len(re.findall(r'95%|confidence\s+interval', full_text, re.IGNORECASE))

            print(f"HR mentions: {hr_count}")
            print(f"OR mentions: {or_count}")
            print(f"RR mentions: {rr_count}")
            print(f"MD mentions: {md_count}")
            print(f"95%/CI mentions: {ci_count}")

            # Show examples of effect mentions
            if hr_count > 0:
                matches = re.findall(r'.{20}hazard\s+ratio.{100}', full_text, re.IGNORECASE)
                if matches:
                    print(f"\nHR context:")
                    ctx = matches[0].replace('\n', ' ')[:120]
                    print(f"  {ctx}...")

            if or_count > 0:
                matches = re.findall(r'.{20}odds\s+ratio.{100}', full_text, re.IGNORECASE)
                if matches:
                    print(f"\nOR context:")
                    ctx = matches[0].replace('\n', ' ')[:120]
                    print(f"  {ctx}...")

            if rr_count > 0:
                matches = re.findall(r'.{20}(?:relative\s+risk|risk\s+ratio).{100}', full_text, re.IGNORECASE)
                if matches:
                    print(f"\nRR context:")
                    ctx = matches[0].replace('\n', ' ')[:120]
                    print(f"  {ctx}...")

            # Look for number patterns that might be effects
            ci_patterns = re.findall(r'(\d+\.\d+)\s*\(\s*(\d+\.\d+)\s*[-–,]\s*(\d+\.\d+)\s*\)', full_text)
            if ci_patterns:
                print(f"\nPotential CI patterns found: {len(ci_patterns)}")
                for p in ci_patterns[:3]:
                    print(f"  {p[0]} ({p[1]}-{p[2]})")

        except Exception as e:
            print(f"Error: {e}")


def analyze_missing_cis():
    """Analyze extractions without CIs"""
    with open(VALIDATION_FILE) as f:
        data = json.load(f)

    print("\n" + "=" * 70)
    print("ANALYZING MISSING CIs")
    print("=" * 70)

    no_ci_extractions = []
    for result in data["results"]:
        for ext in result["extractions"]:
            if not ext["has_ci"]:
                no_ci_extractions.append({
                    "pdf": Path(result["pdf_path"]).name,
                    "type": ext["type"],
                    "value": ext["value"],
                    "source": ext["source_snippet"]
                })

    print(f"\nExtractions without CI: {len(no_ci_extractions)}")

    # Group by type
    by_type = {}
    for ext in no_ci_extractions:
        t = ext["type"]
        by_type[t] = by_type.get(t, 0) + 1

    print("\nBy effect type:")
    for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    # Show examples
    print("\nExamples of extractions without CI:")
    for ext in no_ci_extractions[:10]:
        print(f"  {ext['type']} {ext['value']}: {ext['source'][:60]}...")


if __name__ == "__main__":
    analyze_zero_extraction_pdfs()
    analyze_missing_cis()
