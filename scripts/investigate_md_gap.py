#!/usr/bin/env python3
"""Investigate MD CI gap and zero-extraction PDFs."""

import os
import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def extract_text_from_pdf(pdf_path: str, max_pages: int = 20) -> str:
    """Extract text from PDF."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages]):
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception:
        try:
            import fitz
            doc = fitz.open(pdf_path)
            text_parts = []
            for i in range(min(max_pages, len(doc))):
                text_parts.append(doc[i].get_text())
            doc.close()
            return "\n".join(text_parts)
        except Exception as e:
            return ""


def main():
    # Load validation results
    with open('output/rct_results_validation.json') as f:
        data = json.load(f)

    print("=" * 60)
    print("INVESTIGATING MD CI GAP")
    print("=" * 60)

    # Find PDFs with MD effects
    print("\nPDFs with MD effects:")
    md_pdfs = []
    for d in data['details']:
        if 'MD' in d['types']:
            md_pdfs.append(d)
            print(f"  {d['pdf']}: {d['effects']} effects, {d['with_ci']} CI, types: {d['types']}")

    # Check what MD patterns are in text
    pdf_base = "test_pdfs/real_pdfs"

    for pdf_info in md_pdfs:
        pdf_name = pdf_info['pdf']
        print(f"\n--- Investigating {pdf_name} ---")

        # Find PDF
        pdf_path = None
        for root, dirs, files in os.walk(pdf_base):
            if pdf_name in files:
                pdf_path = os.path.join(root, pdf_name)
                break

        if not pdf_path:
            print("  PDF not found")
            continue

        text = extract_text_from_pdf(pdf_path)
        if not text:
            print("  No text extracted")
            continue

        # Search for MD-related patterns
        md_patterns = [
            (r'mean\s+difference[:\s]+(-?\d+\.?\d*)', 'mean difference X'),
            (r'\bMD\b[:\s=]+(-?\d+\.?\d*)', 'MD X'),
            (r'difference\s+(-?\d+\.?\d*)\s*\(', 'difference X ('),
            (r'(-?\d+\.?\d*)\s*\(\s*95%?\s*CI', 'X (95% CI'),
            (r'(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-to]+\s*(-?\d+\.?\d*)\s*\)', 'X (Y-Z)'),
        ]

        print("  Pattern matches in text:")
        for pattern, name in md_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                print(f"    {name}: {len(matches)} matches")
                # Show first few
                for m in matches[:3]:
                    print(f"      -> {m}")

        # Look for actual MD mentions with context
        md_mentions = list(re.finditer(r'.{0,50}(?:mean\s+difference|\bMD\b).{0,100}', text, re.IGNORECASE))
        if md_mentions:
            print(f"  MD context snippets ({len(md_mentions)} found):")
            for m in md_mentions[:5]:
                snippet = m.group(0).replace('\n', ' ')[:120]
                # Remove problematic unicode chars
                snippet = snippet.encode('ascii', 'replace').decode('ascii')
                print(f"    \"{snippet}...\"")

    # PDFs with 0 effects
    print("\n" + "=" * 60)
    print("PDFs WITH 0 EFFECTS (need investigation)")
    print("=" * 60)

    zero_pdfs = [d for d in data['details'] if d['effects'] == 0]
    for pdf_info in zero_pdfs:
        pdf_name = pdf_info['pdf']
        category = pdf_info['category']
        print(f"\n--- {pdf_name} ({category}) ---")

        # Find PDF
        pdf_path = None
        for root, dirs, files in os.walk(pdf_base):
            if pdf_name in files:
                pdf_path = os.path.join(root, pdf_name)
                break

        if not pdf_path:
            print("  PDF not found")
            continue

        text = extract_text_from_pdf(pdf_path)
        if not text:
            print("  No text extracted")
            continue

        print(f"  Text length: {len(text)} chars")

        # Look for any effect-like patterns
        effect_patterns = [
            (r'\bHR\b', 'HR'),
            (r'\bOR\b', 'OR'),
            (r'\bRR\b', 'RR'),
            (r'hazard\s+ratio', 'hazard ratio'),
            (r'odds\s+ratio', 'odds ratio'),
            (r'mean\s+difference', 'mean difference'),
            (r'\bMD\b', 'MD'),
            (r'95%?\s*CI', '95% CI'),
            (r'p\s*[<>=]\s*0\.\d+', 'p-value'),
        ]

        found = []
        for pattern, name in effect_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found.append(f"{name}({len(matches)})")

        if found:
            print(f"  Effect terms found: {', '.join(found)}")
        else:
            print("  NO effect terms found - likely not RCT results")


if __name__ == "__main__":
    main()
