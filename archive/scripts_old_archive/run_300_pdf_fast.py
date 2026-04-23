# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Fast 300 PDF Validation - Suppresses warnings, uses PyMuPDF directly
"""
import sys
import json
import re
import warnings
import logging
from pathlib import Path
from typing import Dict, List

# Suppress all warnings
warnings.filterwarnings('ignore')
logging.disable(logging.CRITICAL)

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.extractor import NumericParser

# Try to import fitz
try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False
    print("PyMuPDF not available")
    sys.exit(1)


def extract_text_fast(pdf_path: str) -> str:
    """Fast text extraction using PyMuPDF only"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except:
        return ""


def extract_effects(text: str) -> Dict[str, List[Dict]]:
    """Extract all effect estimates from text"""
    text = text.replace('\xb7', '.').replace('\u2212', '-').replace('\u2013', '-')
    results = {'HR': [], 'OR': [], 'RR': []}

    patterns = {
        'HR': NumericParser.HR_PATTERNS[:10],  # Use top 10 patterns for speed
        'OR': NumericParser.OR_PATTERNS[:8],
        'RR': NumericParser.RR_PATTERNS[:8],
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

                        key = (round(value, 2), round(ci_low or 0, 2), round(ci_high or 0, 2))
                        if key in seen:
                            continue
                        seen.add(key)

                        results[measure_type].append({
                            'value': value,
                            'ci_low': ci_low,
                            'ci_high': ci_high,
                            'has_ci': ci_low is not None and ci_high is not None
                        })
                    except:
                        continue
            except:
                continue

    return results


def main():
    print("=" * 70)
    print("RCT EXTRACTOR v2 - 300 PDF FAST VALIDATION")
    print("=" * 70)

    downloads = Path("C:/Users/user/Downloads")
    all_pdfs = list(downloads.rglob("*.pdf"))

    target = min(300, len(all_pdfs))
    print(f"\nProcessing {target} of {len(all_pdfs)} PDFs...")
    print("-" * 70)

    stats = {
        'processed': 0,
        'parsed_ok': 0,
        'with_effects': 0,
        'total_hrs': 0,
        'total_ors': 0,
        'total_rrs': 0,
        'hrs_with_ci': 0,
    }

    top_pdfs = []

    for i, pdf_path in enumerate(all_pdfs[:target]):
        stats['processed'] += 1

        if (i + 1) % 50 == 0:
            print(f"  Progress: {i + 1}/{target} ({stats['with_effects']} with effects)")

        text = extract_text_fast(str(pdf_path))
        if len(text) < 100:
            continue

        stats['parsed_ok'] += 1
        effects = extract_effects(text)

        hr_count = len(effects['HR'])
        or_count = len(effects['OR'])
        rr_count = len(effects['RR'])
        total = hr_count + or_count + rr_count

        if total > 0:
            stats['with_effects'] += 1
            stats['total_hrs'] += hr_count
            stats['total_ors'] += or_count
            stats['total_rrs'] += rr_count
            stats['hrs_with_ci'] += sum(1 for e in effects['HR'] if e['has_ci'])

            if hr_count > 0:
                top_pdfs.append({
                    'pdf': pdf_path.name[:60],
                    'hr': hr_count,
                    'or': or_count,
                    'rr': rr_count,
                    'sample': effects['HR'][0] if effects['HR'] else None
                })

    # Summary
    print("\n" + "=" * 70)
    print("300 PDF VALIDATION RESULTS")
    print("=" * 70)

    total_effects = stats['total_hrs'] + stats['total_ors'] + stats['total_rrs']

    print(f"""
PDFs Processed: {stats['processed']}
  - Successfully parsed: {stats['parsed_ok']}
  - With effect estimates: {stats['with_effects']} ({stats['with_effects']/max(stats['parsed_ok'],1)*100:.1f}%)

Effect Estimates Extracted:
  - Hazard Ratios (HR): {stats['total_hrs']} ({stats['hrs_with_ci']} with CI)
  - Odds Ratios (OR): {stats['total_ors']}
  - Relative Risks (RR): {stats['total_rrs']}
  - TOTAL: {total_effects}

Average per PDF with effects: {total_effects/max(stats['with_effects'],1):.1f}
""")

    # Top PDFs
    top_pdfs.sort(key=lambda x: x['hr'], reverse=True)
    print("Top 15 PDFs by HR count:")
    for r in top_pdfs[:15]:
        ci_str = ""
        if r['sample'] and r['sample']['has_ci']:
            ci_str = f" [e.g. HR {r['sample']['value']:.2f} ({r['sample']['ci_low']:.2f}-{r['sample']['ci_high']:.2f})]"
        print(f"  {r['pdf']}: {r['hr']} HRs{ci_str}")

    # Save
    output_file = Path(__file__).parent / 'output' / 'pdf_300_validation.json'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({'summary': stats, 'top_pdfs': top_pdfs[:50]}, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
