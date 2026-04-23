# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Large-Scale Real PDF Validation for RCT Extractor v2

Tests extraction on 300 actual PDF files.
"""
import sys
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.extractor import NumericParser
from src.pdf.pdf_parser import PDFParser


def extract_effects(text: str) -> Dict[str, List[Dict]]:
    """Extract all effect estimates from text"""
    text = text.replace('\xb7', '.').replace('\u2212', '-').replace('\u2013', '-')
    results = {'HR': [], 'OR': [], 'RR': []}

    patterns = {
        'HR': NumericParser.HR_PATTERNS,
        'OR': NumericParser.OR_PATTERNS,
        'RR': NumericParser.RR_PATTERNS,
    }

    plausibility = {
        'HR': lambda v: 0.05 <= v <= 20,
        'OR': lambda v: 0.05 <= v <= 50,
        'RR': lambda v: 0.05 <= v <= 20,
    }

    for measure_type, pattern_list in patterns.items():
        seen = set()
        for pattern in pattern_list:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                groups = match.groups()
                try:
                    value = float(groups[0])
                    ci_low = float(groups[2]) if len(groups) > 2 and groups[2] else None
                    ci_high = float(groups[3]) if len(groups) > 3 and groups[3] else None

                    # Plausibility checks
                    if not plausibility[measure_type](value):
                        continue
                    if ci_low and ci_high and ci_low >= ci_high:
                        continue
                    if ci_low and ci_low > 100:
                        continue
                    if ci_high and ci_high > 100:
                        continue

                    key = (round(value, 3), round(ci_low or 0, 3), round(ci_high or 0, 3))
                    if key in seen:
                        continue
                    seen.add(key)

                    results[measure_type].append({
                        'value': value,
                        'ci_low': ci_low,
                        'ci_high': ci_high,
                        'has_ci': ci_low is not None and ci_high is not None
                    })
                except (ValueError, IndexError):
                    continue

    return results


def main():
    print("=" * 70)
    print("RCT EXTRACTOR v2 - 300 PDF VALIDATION")
    print("=" * 70)

    parser = PDFParser()
    downloads = Path("C:/Users/user/Downloads")

    # Collect all PDFs
    all_pdfs = list(downloads.rglob("*.pdf"))
    print(f"\nFound {len(all_pdfs)} PDFs in Downloads")

    # Limit to 300
    target = 300
    pdfs_to_process = all_pdfs[:target]
    print(f"Processing {len(pdfs_to_process)} PDFs...")

    # Stats
    stats = {
        'processed': 0,
        'parsed_ok': 0,
        'parse_failed': 0,
        'with_effects': 0,
        'total_hrs': 0,
        'total_ors': 0,
        'total_rrs': 0,
        'hrs_with_ci': 0,
        'ors_with_ci': 0,
        'rrs_with_ci': 0,
    }

    results_by_pdf = []

    print("\n" + "-" * 70)

    for i, pdf_path in enumerate(pdfs_to_process):
        stats['processed'] += 1

        if (i + 1) % 50 == 0:
            print(f"  Progress: {i + 1}/{len(pdfs_to_process)} PDFs processed...")

        try:
            content = parser.parse(str(pdf_path))
            full_text = "\n".join(page.full_text for page in content.pages)
            stats['parsed_ok'] += 1
        except Exception as e:
            stats['parse_failed'] += 1
            continue

        if len(full_text) < 100:
            continue

        effects = extract_effects(full_text)

        hr_count = len(effects['HR'])
        or_count = len(effects['OR'])
        rr_count = len(effects['RR'])

        if hr_count + or_count + rr_count > 0:
            stats['with_effects'] += 1

        stats['total_hrs'] += hr_count
        stats['total_ors'] += or_count
        stats['total_rrs'] += rr_count

        stats['hrs_with_ci'] += sum(1 for e in effects['HR'] if e['has_ci'])
        stats['ors_with_ci'] += sum(1 for e in effects['OR'] if e['has_ci'])
        stats['rrs_with_ci'] += sum(1 for e in effects['RR'] if e['has_ci'])

        if hr_count + or_count + rr_count > 0:
            results_by_pdf.append({
                'pdf': pdf_path.name,
                'chars': len(full_text),
                'hr': hr_count,
                'or': or_count,
                'rr': rr_count,
                'sample_hr': effects['HR'][0] if effects['HR'] else None
            })

    # Summary
    print("\n" + "=" * 70)
    print("300 PDF VALIDATION SUMMARY")
    print("=" * 70)

    print(f"""
PDFs Processed: {stats['processed']}
  - Successfully parsed: {stats['parsed_ok']} ({stats['parsed_ok']/stats['processed']*100:.1f}%)
  - Parse failed: {stats['parse_failed']}
  - With effect estimates: {stats['with_effects']} ({stats['with_effects']/stats['parsed_ok']*100:.1f}% of parsed)

Effect Estimates Extracted:
  - Hazard Ratios (HR): {stats['total_hrs']} ({stats['hrs_with_ci']} with CI)
  - Odds Ratios (OR): {stats['total_ors']} ({stats['ors_with_ci']} with CI)
  - Relative Risks (RR): {stats['total_rrs']} ({stats['rrs_with_ci']} with CI)
  - Total: {stats['total_hrs'] + stats['total_ors'] + stats['total_rrs']}

Average per PDF (with effects): {(stats['total_hrs'] + stats['total_ors'] + stats['total_rrs']) / max(stats['with_effects'], 1):.1f} effects
""")

    # Top PDFs by effect count
    results_by_pdf.sort(key=lambda x: x['hr'] + x['or'] + x['rr'], reverse=True)
    print("Top 10 PDFs by effect count:")
    for r in results_by_pdf[:10]:
        total = r['hr'] + r['or'] + r['rr']
        print(f"  {r['pdf'][:50]}: {total} effects (HR={r['hr']}, OR={r['or']}, RR={r['rr']})")

    # Sample extracted values
    print("\nSample extracted HRs with CI:")
    shown = 0
    for r in results_by_pdf:
        if r['sample_hr'] and r['sample_hr']['has_ci']:
            hr = r['sample_hr']
            print(f"  {r['pdf'][:40]}: HR {hr['value']:.2f} ({hr['ci_low']:.2f}-{hr['ci_high']:.2f})")
            shown += 1
            if shown >= 10:
                break

    # Save results
    output_file = Path(__file__).parent / 'output' / 'pdf_300_validation.json'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'summary': stats,
            'top_pdfs': results_by_pdf[:50]
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
