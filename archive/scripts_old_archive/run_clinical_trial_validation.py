# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Clinical Trial PDF Validation
Focused test on NEJM/Lancet/JAMA clinical trial publications
"""
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent / 'src'))

import fitz  # PyMuPDF


def extract_hrs_simple(text: str) -> List[Dict]:
    """Simple, reliable HR extraction"""
    text = text.replace('\xb7', '.').replace('\u2212', '-').replace('\u2013', '-')
    results = []
    seen = set()

    # Simpler patterns that work
    patterns = [
        # hazard ratio, 0.82; 95% CI, 0.73 to 0.92
        r'hazard\s*ratio[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-\u2013])\s*(\d+\.?\d*)',
        # hazard ratio, 0.82 (95% CI, 0.73 to 0.92)
        r'hazard\s*ratio[,;:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-\u2013])\s*(\d+\.?\d*)',
        # hazard ratio of 0.82 (95% CI, 0.73 to 0.92)
        r'hazard\s*ratio\s+(?:of|was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-\u2013])\s*(\d+\.?\d*)',
        # HR 0.82 (0.73-0.92)
        r'\bHR\b[,;:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-\u2013]\s*(\d+\.?\d*)\s*\)',
        # hazard ratio 0.82 (0.73-0.92)
        r'hazard\s*ratio[,;:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-\u2013]\s*(\d+\.?\d*)\s*\)',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                hr = float(match.group(1))
                ci_low = float(match.group(2))
                ci_high = float(match.group(3))

                # Plausibility
                if not (0.05 <= hr <= 20):
                    continue
                if ci_low >= ci_high:
                    continue

                key = (round(hr, 2), round(ci_low, 2), round(ci_high, 2))
                if key in seen:
                    continue
                seen.add(key)

                results.append({
                    'hr': hr,
                    'ci_low': ci_low,
                    'ci_high': ci_high,
                    'match': match.group(0)[:80]
                })
            except:
                continue

    return results


def main():
    print("=" * 70)
    print("CLINICAL TRIAL PDF VALIDATION")
    print("=" * 70)

    downloads = Path("C:/Users/user/Downloads")

    # Find clinical trial PDFs
    trial_patterns = ['nejm', 'lancet', 'jama', 'trial', 'nct', 'et-al']
    all_pdfs = []

    for pdf in downloads.rglob("*.pdf"):
        name = pdf.name.lower()
        if any(p in name for p in trial_patterns):
            all_pdfs.append(pdf)

    print(f"\nFound {len(all_pdfs)} clinical trial PDFs")
    print("-" * 70)

    total_hrs = 0
    pdfs_with_hrs = 0
    all_results = []

    for pdf_path in all_pdfs:
        try:
            doc = fitz.open(str(pdf_path))
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
        except:
            continue

        hrs = extract_hrs_simple(text)

        if hrs:
            pdfs_with_hrs += 1
            total_hrs += len(hrs)

            print(f"\n{pdf_path.name}")
            for h in hrs[:5]:
                print(f"  HR {h['hr']:.2f} ({h['ci_low']:.2f}-{h['ci_high']:.2f})")
            if len(hrs) > 5:
                print(f"  ... and {len(hrs) - 5} more")

            all_results.append({
                'pdf': pdf_path.name,
                'hr_count': len(hrs),
                'sample': hrs[0] if hrs else None
            })

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nPDFs processed: {len(all_pdfs)}")
    print(f"PDFs with HRs: {pdfs_with_hrs} ({pdfs_with_hrs/len(all_pdfs)*100:.1f}%)")
    print(f"Total HRs extracted: {total_hrs}")

    # Top PDFs
    all_results.sort(key=lambda x: x['hr_count'], reverse=True)
    print("\nTop 20 PDFs by HR count:")
    for r in all_results[:20]:
        s = r['sample']
        sample_str = f" [HR {s['hr']:.2f} ({s['ci_low']:.2f}-{s['ci_high']:.2f})]" if s else ""
        print(f"  {r['pdf'][:50]}: {r['hr_count']} HRs{sample_str}")

    print("=" * 70)


if __name__ == "__main__":
    main()
