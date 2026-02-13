"""
Full PDF Validation - 500+ PDFs with Text + Table Extraction
=============================================================
Tests both inline text extraction and table extraction from PDFs.
"""
import sys
import json
import re
import warnings
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
import time

# Suppress warnings
warnings.filterwarnings('ignore')
logging.disable(logging.WARNING)

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.extractor import NumericParser

# Import dependencies
import fitz  # PyMuPDF
import cv2
import numpy as np
import pytesseract


@dataclass
class ExtractionResult:
    """Single extraction result"""
    measure_type: str
    value: float
    ci_low: float = None
    ci_high: float = None
    source: str = "text"  # "text", "table", "ocr"
    page: int = 0


def extract_text_from_pdf(pdf_path: str) -> Tuple[str, int]:
    """Extract text using PyMuPDF"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        num_pages = len(doc)
        doc.close()
        return text, num_pages
    except:
        return "", 0


def extract_tables_from_pdf(pdf_path: str, max_pages: int = 10) -> List[ExtractionResult]:
    """Extract effect estimates from tables using OCR"""
    results = []

    try:
        doc = fitz.open(pdf_path)
        num_pages = min(len(doc), max_pages)

        for page_num in range(num_pages):
            page = doc[page_num]

            # Render page to image at 150 DPI (balance speed/quality)
            mat = fitz.Matrix(150/72, 150/72)
            pix = page.get_pixmap(matrix=mat)

            # Convert to numpy array
            img = np.frombuffer(pix.samples, dtype=np.uint8)
            img = img.reshape(pix.height, pix.width, pix.n)

            if pix.n == 4:  # RGBA
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 1:  # Grayscale
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

            # Detect table regions
            table_regions = detect_tables(img)

            for region in table_regions:
                x1, y1, x2, y2 = region
                table_img = img[y1:y2, x1:x2]

                # OCR the table region
                try:
                    table_text = pytesseract.image_to_string(table_img)

                    # Parse for effect estimates
                    table_results = parse_table_text(table_text, page_num)
                    results.extend(table_results)
                except:
                    pass

        doc.close()
    except:
        pass

    return results


def detect_tables(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detect table regions using line detection"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Detect horizontal and vertical lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel)

    table_mask = cv2.add(horizontal, vertical)

    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    min_area = (h * w) * 0.02  # At least 2% of image

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_area:
            x, y, cw, ch = cv2.boundingRect(contour)
            regions.append((max(0, x-5), max(0, y-5),
                          min(w, x+cw+5), min(h, y+ch+5)))

    return regions


def parse_table_text(text: str, page_num: int) -> List[ExtractionResult]:
    """Parse OCR'd table text for effect estimates"""
    results = []
    text = text.replace('\xb7', '.').replace('\u2212', '-').replace('\u2013', '-')

    # Pattern: value (CI_low - CI_high) or value (CI_low, CI_high)
    patterns = [
        r'(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–to,]+\s*(\d+\.?\d*)\s*\)',
        r'(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–to,]+\s*(\d+\.?\d*)\s*\]',
    ]

    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            try:
                value = float(match.group(1))
                ci_low = float(match.group(2))
                ci_high = float(match.group(3))

                # Plausibility checks
                if not (0.05 <= value <= 20):
                    continue
                if ci_low >= ci_high:
                    continue
                if ci_low > 100 or ci_high > 100:
                    continue

                key = (round(value, 2), round(ci_low, 2), round(ci_high, 2))
                if key in seen:
                    continue
                seen.add(key)

                results.append(ExtractionResult(
                    measure_type="HR",  # Default, context would refine
                    value=value,
                    ci_low=ci_low,
                    ci_high=ci_high,
                    source="table",
                    page=page_num
                ))
            except:
                continue

    return results


def extract_from_text(text: str) -> List[ExtractionResult]:
    """Extract effect estimates from text using regex patterns"""
    text = text.replace('\xb7', '.').replace('\u2212', '-').replace('\u2013', '-')
    results = []

    patterns = {
        'HR': NumericParser.HR_PATTERNS[:15],
        'OR': NumericParser.OR_PATTERNS[:10],
        'RR': NumericParser.RR_PATTERNS[:10],
    }

    plausibility = {
        'HR': lambda v: 0.05 <= v <= 20,
        'OR': lambda v: 0.05 <= v <= 50,
        'RR': lambda v: 0.05 <= v <= 20,
    }

    for measure_type, pattern_list in patterns.items():
        seen = set()
        for pattern in pattern_list:
            try:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    groups = match.groups()
                    try:
                        value = float(groups[0])
                        ci_low = float(groups[2]) if len(groups) > 2 and groups[2] else None
                        ci_high = float(groups[3]) if len(groups) > 3 and groups[3] else None

                        if not plausibility[measure_type](value):
                            continue
                        if ci_low and ci_high and ci_low >= ci_high:
                            continue

                        key = (measure_type, round(value, 2),
                               round(ci_low or 0, 2), round(ci_high or 0, 2))
                        if key in seen:
                            continue
                        seen.add(key)

                        results.append(ExtractionResult(
                            measure_type=measure_type,
                            value=value,
                            ci_low=ci_low,
                            ci_high=ci_high,
                            source="text"
                        ))
                    except:
                        continue
            except:
                continue

    return results


def main():
    print("=" * 70)
    print("FULL PDF VALIDATION - 500+ PDFs")
    print("Text Extraction + Table Extraction + OCR")
    print("=" * 70)

    downloads = Path("C:/Users/user/Downloads")
    all_pdfs = list(downloads.rglob("*.pdf"))

    print(f"\nFound {len(all_pdfs)} PDFs")
    print("-" * 70)

    stats = {
        'processed': 0,
        'parsed_ok': 0,
        'with_text_effects': 0,
        'with_table_effects': 0,
        'text_hrs': 0,
        'text_ors': 0,
        'text_rrs': 0,
        'text_with_ci': 0,
        'table_effects': 0,
        'table_with_ci': 0,
        'total_pages': 0,
    }

    top_pdfs = []
    start_time = time.time()

    for i, pdf_path in enumerate(all_pdfs):
        stats['processed'] += 1

        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            print(f"  Progress: {i + 1}/{len(all_pdfs)} ({rate:.1f} PDFs/sec)")

        # Text extraction
        text, num_pages = extract_text_from_pdf(str(pdf_path))
        if not text or len(text) < 100:
            continue

        stats['parsed_ok'] += 1
        stats['total_pages'] += num_pages

        # Extract from text
        text_results = extract_from_text(text)

        # Count by type
        hrs = [r for r in text_results if r.measure_type == 'HR']
        ors = [r for r in text_results if r.measure_type == 'OR']
        rrs = [r for r in text_results if r.measure_type == 'RR']

        if text_results:
            stats['with_text_effects'] += 1
            stats['text_hrs'] += len(hrs)
            stats['text_ors'] += len(ors)
            stats['text_rrs'] += len(rrs)
            stats['text_with_ci'] += sum(1 for r in text_results if r.ci_low and r.ci_high)

        # Table extraction (only for PDFs with few text results)
        table_results = []
        if len(hrs) < 3:  # Try table extraction if few HRs found
            table_results = extract_tables_from_pdf(str(pdf_path), max_pages=5)
            if table_results:
                stats['with_table_effects'] += 1
                stats['table_effects'] += len(table_results)
                stats['table_with_ci'] += sum(1 for r in table_results if r.ci_low and r.ci_high)

        # Track top PDFs
        total_effects = len(text_results) + len(table_results)
        if total_effects > 0:
            sample_hr = None
            for r in text_results:
                if r.measure_type == 'HR' and r.ci_low and r.ci_high:
                    sample_hr = r
                    break

            top_pdfs.append({
                'pdf': pdf_path.name[:55],
                'text_effects': len(text_results),
                'table_effects': len(table_results),
                'hrs': len(hrs),
                'sample': f"HR {sample_hr.value:.2f} ({sample_hr.ci_low:.2f}-{sample_hr.ci_high:.2f})" if sample_hr else None
            })

    elapsed = time.time() - start_time

    # Summary
    print("\n" + "=" * 70)
    print("FULL VALIDATION RESULTS")
    print("=" * 70)

    total_text = stats['text_hrs'] + stats['text_ors'] + stats['text_rrs']

    print(f"""
PDFs Processed: {stats['processed']}
  - Successfully parsed: {stats['parsed_ok']} ({stats['parsed_ok']/stats['processed']*100:.1f}%)
  - Total pages scanned: {stats['total_pages']}
  - Processing time: {elapsed:.1f}s ({stats['processed']/elapsed:.1f} PDFs/sec)

TEXT EXTRACTION:
  - PDFs with effects: {stats['with_text_effects']} ({stats['with_text_effects']/stats['parsed_ok']*100:.1f}%)
  - Hazard Ratios: {stats['text_hrs']}
  - Odds Ratios: {stats['text_ors']}
  - Relative Risks: {stats['text_rrs']}
  - Total: {total_text}
  - With CI: {stats['text_with_ci']} ({stats['text_with_ci']/max(total_text,1)*100:.1f}%)

TABLE EXTRACTION (OCR):
  - PDFs with table effects: {stats['with_table_effects']}
  - Effects from tables: {stats['table_effects']}
  - With CI: {stats['table_with_ci']}

COMBINED TOTAL: {total_text + stats['table_effects']} effects
""")

    # Top PDFs
    top_pdfs.sort(key=lambda x: x['text_effects'] + x['table_effects'], reverse=True)
    print("Top 20 PDFs by effect count:")
    for r in top_pdfs[:20]:
        total = r['text_effects'] + r['table_effects']
        sample = f" [{r['sample']}]" if r['sample'] else ""
        print(f"  {r['pdf']}: {total} ({r['hrs']} HRs){sample}")

    # Save results
    output_file = Path(__file__).parent / 'output' / 'full_pdf_validation.json'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'summary': stats,
            'elapsed_seconds': elapsed,
            'top_pdfs': top_pdfs[:100]
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
