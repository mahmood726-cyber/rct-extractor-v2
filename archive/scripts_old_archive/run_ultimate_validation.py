# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Ultimate RCT Extractor Validation
=================================
Combines ALL extraction methods:
- Text pattern matching
- Table OCR extraction
- Forest plot detection

Tests on highest-yield PDFs from massive validation.
"""
import sys
import re
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'src'))

import fitz  # PyMuPDF
import cv2
import numpy as np
import pytesseract

from figures.forest_plot_extractor import ForestPlotExtractor


@dataclass
class EffectEstimate:
    """Unified effect estimate from any source"""
    measure_type: str  # HR, OR, RR, RD, MD
    value: float
    ci_low: float
    ci_high: float
    source: str  # text, table, forest_plot
    context: str = ""
    confidence: float = 0.8


@dataclass
class PDFExtractionResult:
    """Complete extraction results for a PDF"""
    pdf_name: str
    text_effects: List[EffectEstimate] = field(default_factory=list)
    table_effects: List[EffectEstimate] = field(default_factory=list)
    forest_effects: List[EffectEstimate] = field(default_factory=list)

    @property
    def total_effects(self) -> int:
        return len(self.text_effects) + len(self.table_effects) + len(self.forest_effects)

    @property
    def total_hrs(self) -> int:
        all_effects = self.text_effects + self.table_effects + self.forest_effects
        return sum(1 for e in all_effects if e.measure_type == 'HR')


def extract_text_effects(text: str) -> List[EffectEstimate]:
    """Extract effect estimates from text using regex patterns"""
    text = text.replace('\xb7', '.').replace('\u2212', '-').replace('\u2013', '-').replace('\u2014', '-')
    results = []
    seen = set()

    patterns = {
        'HR': [
            r'hazard\s*ratio[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'hazard\s*ratio[,;:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'hazard\s*ratio\s+(?:of|was|for\s+\w+\s+was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bHR\b[,;:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)\s*\)',
        ],
        'OR': [
            r'odds\s*ratio[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'odds\s*ratio[,;:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bOR\b[,;:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)\s*\)',
        ],
        'RR': [
            r'(?:relative|risk)\s*ratio[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'(?:relative|risk)\s*ratio[,;:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bRR\b[,;:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)\s*\)',
        ],
        'MD': [
            r'mean\s*difference[,;:\s]+([+-]?\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+([+-]?\d+\.?\d*)\s*(?:to|[-])\s*([+-]?\d+\.?\d*)',
        ],
    }

    plausibility = {
        'HR': lambda v: 0.05 <= v <= 30,
        'OR': lambda v: 0.01 <= v <= 100,
        'RR': lambda v: 0.05 <= v <= 30,
        'MD': lambda v: -1000 <= v <= 1000,
    }

    for measure_type, pattern_list in patterns.items():
        for pattern in pattern_list:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = float(match.group(1))
                    ci_low = float(match.group(2))
                    ci_high = float(match.group(3))

                    if not plausibility[measure_type](value):
                        continue
                    if ci_low >= ci_high:
                        continue

                    key = (measure_type, round(value, 2), round(ci_low, 2), round(ci_high, 2))
                    if key in seen:
                        continue
                    seen.add(key)

                    results.append(EffectEstimate(
                        measure_type=measure_type,
                        value=value,
                        ci_low=ci_low,
                        ci_high=ci_high,
                        source='text',
                        context=match.group(0)[:80]
                    ))
                except (ValueError, IndexError):
                    continue

    return results


def extract_table_effects(pdf_path: str, max_pages: int = 10) -> List[EffectEstimate]:
    """Extract effect estimates from tables using OCR"""
    results = []
    seen = set()

    try:
        doc = fitz.open(pdf_path)

        for page_idx in range(min(max_pages, len(doc))):
            page = doc[page_idx]
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)

            img = np.frombuffer(pix.samples, dtype=np.uint8)
            img = img.reshape(pix.height, pix.width, pix.n)

            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 1:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Detect tables using line detection
            edges = cv2.Canny(gray, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)

            if lines is not None and len(lines) > 10:
                # OCR the page
                text = pytesseract.image_to_string(img)

                # Look for effect estimates in table-like format
                pattern = r'(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*\)'

                for match in re.finditer(pattern, text):
                    try:
                        value = float(match.group(1))
                        ci_low = float(match.group(2))
                        ci_high = float(match.group(3))

                        if not (0.05 <= value <= 30):
                            continue
                        if ci_low >= ci_high:
                            continue

                        key = (round(value, 2), round(ci_low, 2), round(ci_high, 2))
                        if key in seen:
                            continue
                        seen.add(key)

                        results.append(EffectEstimate(
                            measure_type='HR',  # Infer from context
                            value=value,
                            ci_low=ci_low,
                            ci_high=ci_high,
                            source='table',
                            confidence=0.6
                        ))
                    except (ValueError, IndexError):
                        continue

        doc.close()

    except Exception as e:
        pass

    return results


def extract_forest_effects(pdf_path: str) -> List[EffectEstimate]:
    """Extract effect estimates from forest plots"""
    results = []
    seen = set()

    try:
        extractor = ForestPlotExtractor(dpi=150)
        forest_results = extractor.extract_from_pdf(pdf_path)

        for r in forest_results:
            key = (r.effect_type, round(r.value, 2), round(r.ci_low, 2), round(r.ci_high, 2))
            if key in seen:
                continue
            seen.add(key)

            results.append(EffectEstimate(
                measure_type=r.effect_type,
                value=r.value,
                ci_low=r.ci_low,
                ci_high=r.ci_high,
                source='forest_plot',
                context=r.study_name,
                confidence=r.confidence
            ))
    except Exception as e:
        pass

    return results


def process_pdf(pdf_path: Path) -> PDFExtractionResult:
    """Process a single PDF with all extraction methods"""
    result = PDFExtractionResult(pdf_name=pdf_path.name)

    # 1. Text extraction
    try:
        doc = fitz.open(str(pdf_path))
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()

        result.text_effects = extract_text_effects(text)
    except:
        pass

    # 2. Table extraction
    result.table_effects = extract_table_effects(str(pdf_path))

    # 3. Forest plot extraction
    result.forest_effects = extract_forest_effects(str(pdf_path))

    return result


def main():
    print("=" * 80)
    print("ULTIMATE RCT EXTRACTOR VALIDATION")
    print("=" * 80)
    print("Combining: Text + Table OCR + Forest Plot Detection")

    # Test PDFs - prioritize high-yield clinical trials
    test_pdfs = []

    # Known high-yield NEJM trials
    nejm_trials = [
        "NEJMoa2206286.pdf",      # DELIVER
        "NEJMoa1611925.pdf",      # EMPA-REG
        "NEJMoa2400685.pdf",
        "NEJMoa1811744.pdf",      # DECLARE
        "NEJMoa1812389.pdf",
        "NEJMoa1310907.pdf",
        "NEJMoa1612917.pdf",
        "NEJMoa0802987.pdf",
        "NEJMoa1814052.pdf",
        "NEJMoa1509225.pdf",
        "NEJMoa1603827.pdf",
        "NEJMoa1708454.pdf",
        "NEJMoa1107039.pdf",      # SHIFT
        "NEJMoa1904143.pdf",
        "NEJMoa2022190.pdf",
    ]

    downloads = Path("C:/Users/user/Downloads")

    for name in nejm_trials:
        pdf = downloads / name
        if pdf.exists():
            test_pdfs.append(pdf)

    # Add more from downloads
    for pdf in downloads.glob("*.pdf"):
        if pdf not in test_pdfs:
            test_pdfs.append(pdf)
        if len(test_pdfs) >= 50:
            break

    print(f"\nTesting {len(test_pdfs)} PDFs")
    print("-" * 80)

    results = []
    start_time = time.time()

    for i, pdf_path in enumerate(test_pdfs):
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{len(test_pdfs)}")

        result = process_pdf(pdf_path)
        results.append(result)

    elapsed = time.time() - start_time

    # Summary
    print("\n" + "=" * 80)
    print("ULTIMATE VALIDATION RESULTS")
    print("=" * 80)

    total_text = sum(len(r.text_effects) for r in results)
    total_table = sum(len(r.table_effects) for r in results)
    total_forest = sum(len(r.forest_effects) for r in results)
    total_effects = total_text + total_table + total_forest

    total_hrs = sum(r.total_hrs for r in results)
    pdfs_with_effects = sum(1 for r in results if r.total_effects > 0)

    print(f"""
EXTRACTION STATISTICS:
  PDFs processed: {len(results)}
  Processing time: {elapsed:.1f}s ({len(results)/elapsed:.1f} PDFs/sec)
  PDFs with effects: {pdfs_with_effects} ({pdfs_with_effects/len(results)*100:.1f}%)

BY EXTRACTION METHOD:
  Text patterns: {total_text:,} effects
  Table OCR: {total_table:,} effects
  Forest plots: {total_forest:,} effects
  --------------------
  TOTAL: {total_effects:,} effects

HAZARD RATIOS:
  Total HRs: {total_hrs:,}
""")

    # Top PDFs by total effects
    results.sort(key=lambda x: x.total_effects, reverse=True)

    print("TOP 20 PDFs BY TOTAL EFFECTS:")
    print("-" * 80)
    print(f"{'PDF':<45} {'Text':<8} {'Table':<8} {'Forest':<8} {'Total':<8}")
    print("-" * 80)

    for r in results[:20]:
        name = r.pdf_name[:42] + "..." if len(r.pdf_name) > 45 else r.pdf_name
        print(f"{name:<45} {len(r.text_effects):<8} {len(r.table_effects):<8} {len(r.forest_effects):<8} {r.total_effects:<8}")

    print("-" * 80)

    # Source breakdown
    print("\nSOURCE CONTRIBUTION:")
    print(f"  Text patterns: {total_text/max(1,total_effects)*100:.1f}%")
    print(f"  Table OCR: {total_table/max(1,total_effects)*100:.1f}%")
    print(f"  Forest plots: {total_forest/max(1,total_effects)*100:.1f}%")

    # Sample effects from each source
    print("\nSAMPLE EFFECTS BY SOURCE:")

    for r in results[:5]:
        if r.text_effects:
            e = r.text_effects[0]
            print(f"  [TEXT] {r.pdf_name[:30]}: {e.measure_type} {e.value:.2f} ({e.ci_low:.2f}-{e.ci_high:.2f})")
            break

    for r in results:
        if r.table_effects:
            e = r.table_effects[0]
            print(f"  [TABLE] {r.pdf_name[:30]}: {e.measure_type} {e.value:.2f} ({e.ci_low:.2f}-{e.ci_high:.2f})")
            break

    for r in results:
        if r.forest_effects:
            e = r.forest_effects[0]
            print(f"  [FOREST] {r.pdf_name[:30]}: {e.measure_type} {e.value:.2f} ({e.ci_low:.2f}-{e.ci_high:.2f})")
            break

    # Save results
    output = {
        'summary': {
            'pdfs_processed': len(results),
            'pdfs_with_effects': pdfs_with_effects,
            'total_text': total_text,
            'total_table': total_table,
            'total_forest': total_forest,
            'total_effects': total_effects,
            'total_hrs': total_hrs,
            'elapsed_seconds': elapsed,
        },
        'top_pdfs': [
            {
                'pdf': r.pdf_name,
                'text': len(r.text_effects),
                'table': len(r.table_effects),
                'forest': len(r.forest_effects),
                'total': r.total_effects,
            }
            for r in results[:50]
        ]
    }

    output_file = Path(__file__).parent / 'output' / 'ultimate_validation.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
