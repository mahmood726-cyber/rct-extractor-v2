#!/usr/bin/env python3
"""
Real PDF Validation for RCT Extractor v4.0.6
Tests extraction on 105 actual PDF files across 7 therapeutic areas.

Validates:
- Text extraction success rate
- Effect estimate detection rate
- Effect type distribution (HR, OR, RR, MD)
- Per-category accuracy

Usage:
    python run_105_pdf_validation.py
"""
import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import traceback

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.extractor import NumericParser
from src.pdf.pdf_parser import PDFParser


# Plausibility filters for effect estimates
def is_plausible_hr(value: float) -> bool:
    """HR should typically be between 0.1 and 10"""
    return 0.05 <= value <= 20

def is_plausible_or(value: float) -> bool:
    """OR should typically be between 0.1 and 50"""
    return 0.05 <= value <= 50

def is_plausible_rr(value: float) -> bool:
    """RR should typically be between 0.1 and 10"""
    return 0.05 <= value <= 20


def extract_all_matches(text: str, patterns: List[str], measure_key: str) -> List[Dict]:
    """Extract all matches for a set of patterns"""
    results = []
    seen_values = set()

    # Normalize text (handle middle dots, unicode)
    text = text.replace('·', '.').replace('−', '-').replace('–', '-')

    def is_plausible(value: float) -> bool:
        if measure_key == 'HR':
            return is_plausible_hr(value)
        elif measure_key == 'OR':
            return is_plausible_or(value)
        elif measure_key == 'RR':
            return is_plausible_rr(value)
        return True

    for pattern in patterns:
        try:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                groups = match.groups()
                try:
                    value = float(groups[0])
                    ci_low = float(groups[2]) if len(groups) > 2 and groups[2] else None
                    ci_high = float(groups[3]) if len(groups) > 3 and groups[3] else None

                    if value <= 0:
                        continue
                    if ci_low and ci_high and ci_low >= ci_high:
                        continue
                    if not is_plausible(value):
                        continue
                    if ci_low and ci_low > 100:
                        continue
                    if ci_high and ci_high > 100:
                        continue

                    key = (round(value, 3), round(ci_low or 0, 3), round(ci_high or 0, 3))
                    if key in seen_values:
                        continue
                    seen_values.add(key)

                    results.append({
                        'measure_type': measure_key,
                        'value': value,
                        'ci_low': ci_low,
                        'ci_high': ci_high,
                        'text_match': match.group(0)[:100]
                    })
                except (ValueError, IndexError):
                    continue
        except re.error:
            continue

    return results


def extract_from_pdf(pdf_path: Path) -> Tuple[str, List[Dict], Dict]:
    """Extract text and effect estimates from PDF"""
    parser = PDFParser()
    metrics = {
        'pages': 0,
        'chars': 0,
        'parse_time_ms': 0,
        'error': None
    }

    start_time = time.time()

    try:
        content = parser.parse(str(pdf_path))
        metrics['parse_time_ms'] = int((time.time() - start_time) * 1000)
    except Exception as e:
        metrics['error'] = str(e)
        return "", [], metrics

    # Combine all page text
    full_text = "\n".join(page.full_text for page in content.pages)
    metrics['pages'] = len(content.pages)
    metrics['chars'] = len(full_text)

    # Extract all effect estimates
    extracted = []

    # HR patterns
    extracted.extend(extract_all_matches(full_text, NumericParser.HR_PATTERNS, 'HR'))

    # OR patterns
    extracted.extend(extract_all_matches(full_text, NumericParser.OR_PATTERNS, 'OR'))

    # RR patterns
    extracted.extend(extract_all_matches(full_text, NumericParser.RR_PATTERNS, 'RR'))

    return full_text, extracted, metrics


def run_validation():
    """Run validation on all 105 PDFs"""
    print("=" * 70)
    print("RCT EXTRACTOR v4.0.6 - REAL PDF VALIDATION (105 PDFs)")
    print("=" * 70)

    base_dir = Path(__file__).parent / 'test_pdfs' / 'real_pdfs'

    if not base_dir.exists():
        print(f"ERROR: Directory not found: {base_dir}")
        return

    # Get all categories
    categories = [d.name for d in base_dir.iterdir() if d.is_dir()]
    print(f"\nCategories found: {', '.join(categories)}")

    # Results storage
    all_results = []
    category_stats = defaultdict(lambda: {
        'total': 0,
        'parsed': 0,
        'with_effects': 0,
        'hrs': 0,
        'ors': 0,
        'rrs': 0,
        'total_effects': 0,
        'avg_chars': 0,
        'errors': []
    })

    # Process each category
    for category in sorted(categories):
        category_dir = base_dir / category
        pdf_files = list(category_dir.glob("*.pdf"))

        print(f"\n{'='*70}")
        print(f"CATEGORY: {category.upper()} ({len(pdf_files)} PDFs)")
        print(f"{'='*70}")

        for pdf_path in pdf_files:
            category_stats[category]['total'] += 1

            print(f"\n  [{category_stats[category]['total']}/{len(pdf_files)}] {pdf_path.name}")

            # Extract from PDF
            full_text, extracted, metrics = extract_from_pdf(pdf_path)

            if metrics['error']:
                print(f"    -> ERROR: {metrics['error'][:50]}")
                category_stats[category]['errors'].append(pdf_path.name)
                continue

            category_stats[category]['parsed'] += 1
            category_stats[category]['avg_chars'] += metrics['chars']

            print(f"    -> {metrics['pages']} pages, {metrics['chars']:,} chars, {metrics['parse_time_ms']}ms")

            # Count by type
            hrs = [e for e in extracted if e['measure_type'] == 'HR']
            ors = [e for e in extracted if e['measure_type'] == 'OR']
            rrs = [e for e in extracted if e['measure_type'] == 'RR']

            category_stats[category]['hrs'] += len(hrs)
            category_stats[category]['ors'] += len(ors)
            category_stats[category]['rrs'] += len(rrs)
            category_stats[category]['total_effects'] += len(extracted)

            if extracted:
                category_stats[category]['with_effects'] += 1
                print(f"    -> Found: {len(hrs)} HR, {len(ors)} OR, {len(rrs)} RR")

                # Show first 2 examples
                for e in extracted[:2]:
                    ci_str = ""
                    if e['ci_low'] and e['ci_high']:
                        ci_str = f" (95% CI: {e['ci_low']:.2f}-{e['ci_high']:.2f})"
                    print(f"       {e['measure_type']}: {e['value']:.2f}{ci_str}")
            else:
                print(f"    -> No effect estimates found")

            # Store result
            all_results.append({
                'category': category,
                'pdf': pdf_path.name,
                'pages': metrics['pages'],
                'chars': metrics['chars'],
                'parse_time_ms': metrics['parse_time_ms'],
                'hrs': len(hrs),
                'ors': len(ors),
                'rrs': len(rrs),
                'total_effects': len(extracted),
                'effects': extracted[:10]  # Store first 10 effects
            })

    # Compute averages
    for cat in category_stats:
        if category_stats[cat]['parsed'] > 0:
            category_stats[cat]['avg_chars'] //= category_stats[cat]['parsed']

    # Print summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY BY CATEGORY")
    print("=" * 70)

    print(f"\n{'Category':<15} {'PDFs':<6} {'Parsed':<8} {'W/Effects':<10} {'HR':<6} {'OR':<6} {'RR':<6} {'Total':<8}")
    print("-" * 70)

    grand_total = 0
    grand_parsed = 0
    grand_with_effects = 0
    grand_hrs = 0
    grand_ors = 0
    grand_rrs = 0
    grand_effects = 0

    for cat in sorted(category_stats.keys()):
        stats = category_stats[cat]
        print(f"{cat:<15} {stats['total']:<6} {stats['parsed']:<8} {stats['with_effects']:<10} "
              f"{stats['hrs']:<6} {stats['ors']:<6} {stats['rrs']:<6} {stats['total_effects']:<8}")

        grand_total += stats['total']
        grand_parsed += stats['parsed']
        grand_with_effects += stats['with_effects']
        grand_hrs += stats['hrs']
        grand_ors += stats['ors']
        grand_rrs += stats['rrs']
        grand_effects += stats['total_effects']

    print("-" * 70)
    print(f"{'TOTAL':<15} {grand_total:<6} {grand_parsed:<8} {grand_with_effects:<10} "
          f"{grand_hrs:<6} {grand_ors:<6} {grand_rrs:<6} {grand_effects:<8}")

    # Compute key metrics
    parse_rate = grand_parsed / grand_total * 100 if grand_total > 0 else 0
    effect_rate = grand_with_effects / grand_parsed * 100 if grand_parsed > 0 else 0
    avg_effects = grand_effects / grand_with_effects if grand_with_effects > 0 else 0

    print(f"\n{'='*70}")
    print("KEY METRICS")
    print("=" * 70)
    print(f"""
PDFs Processed:          {grand_total}
Successfully Parsed:     {grand_parsed} ({parse_rate:.1f}%)
PDFs with Effects:       {grand_with_effects} ({effect_rate:.1f}% of parsed)

Effects Extracted:
  - Hazard Ratios (HR):  {grand_hrs}
  - Odds Ratios (OR):    {grand_ors}
  - Relative Risks (RR): {grand_rrs}
  - TOTAL:               {grand_effects}

Avg Effects per PDF:     {avg_effects:.1f}
""")

    # Save detailed results
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / 'real_pdf_validation_105.json'

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'validation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'version': '4.0.6',
            'summary': {
                'total_pdfs': grand_total,
                'parsed': grand_parsed,
                'parse_rate': round(parse_rate, 1),
                'with_effects': grand_with_effects,
                'effect_rate': round(effect_rate, 1),
                'total_hrs': grand_hrs,
                'total_ors': grand_ors,
                'total_rrs': grand_rrs,
                'total_effects': grand_effects,
                'avg_effects_per_pdf': round(avg_effects, 1)
            },
            'by_category': {cat: dict(stats) for cat, stats in category_stats.items()},
            'results': all_results
        }, f, indent=2, default=str)

    print(f"Detailed results saved to: {output_file}")

    # Print any errors
    all_errors = []
    for cat, stats in category_stats.items():
        for err in stats['errors']:
            all_errors.append(f"{cat}/{err}")

    if all_errors:
        print(f"\n{'='*70}")
        print(f"PARSING ERRORS ({len(all_errors)} PDFs)")
        print("=" * 70)
        for err in all_errors[:10]:
            print(f"  - {err}")
        if len(all_errors) > 10:
            print(f"  ... and {len(all_errors) - 10} more")

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)

    return {
        'total': grand_total,
        'parsed': grand_parsed,
        'with_effects': grand_with_effects,
        'total_effects': grand_effects
    }


if __name__ == "__main__":
    run_validation()
