#!/usr/bin/env python3
"""
Enhanced PDF Validation for RCT Extractor v4.0.7
Uses the full EnhancedExtractor pipeline for better CI extraction.

Usage:
    python run_enhanced_pdf_validation.py
"""

import json
import time
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.enhanced_extractor_v3 import EnhancedExtractor, EffectType
from src.pdf.pdf_parser import PDFParser


def run_enhanced_validation():
    """Run validation using EnhancedExtractor"""
    print("=" * 70)
    print("RCT EXTRACTOR v4.0.7 - ENHANCED PDF VALIDATION")
    print("=" * 70)

    base_dir = Path(__file__).parent / 'test_pdfs' / 'real_pdfs'

    if not base_dir.exists():
        print(f"ERROR: Directory not found: {base_dir}")
        return

    # Initialize extractors
    parser = PDFParser()
    extractor = EnhancedExtractor()

    # Get all categories
    categories = [d.name for d in base_dir.iterdir() if d.is_dir()]
    print(f"\nCategories: {', '.join(categories)}")

    # Results storage
    all_results = []
    category_stats = defaultdict(lambda: {
        'total': 0,
        'parsed': 0,
        'with_effects': 0,
        'total_effects': 0,
        'full_auto': 0,
        'spot_check': 0,
        'verify': 0,
        'manual': 0,
        'with_complete_ci': 0,
        'by_type': defaultdict(int)
    })

    total_processed = 0
    total_pdf_count = sum(len(list((base_dir / cat).glob("*.pdf"))) for cat in categories)

    # Process each category (limit for speed)
    for category in sorted(categories):
        category_dir = base_dir / category
        pdf_files = list(category_dir.glob("*.pdf"))  # All PDFs

        print(f"\n{'='*70}")
        print(f"CATEGORY: {category.upper()} (processing {len(pdf_files)} of {len(list(category_dir.glob('*.pdf')))})")
        print(f"{'='*70}")

        for pdf_path in pdf_files:
            total_processed += 1
            category_stats[category]['total'] += 1

            print(f"\n  [{total_processed}] {pdf_path.name}")

            try:
                start_time = time.time()

                # Parse PDF
                content = parser.parse(str(pdf_path))
                full_text = "\n".join(page.full_text for page in content.pages)

                parse_time = int((time.time() - start_time) * 1000)

                # Extract with EnhancedExtractor
                extractions = extractor.extract(full_text)

                category_stats[category]['parsed'] += 1

                print(f"    -> {len(content.pages)} pages, {len(full_text):,} chars, {parse_time}ms")

                if extractions:
                    category_stats[category]['with_effects'] += 1
                    category_stats[category]['total_effects'] += len(extractions)

                    # Count by type and automation tier
                    for ext in extractions:
                        etype = ext.effect_type.value if hasattr(ext.effect_type, 'value') else str(ext.effect_type)
                        category_stats[category]['by_type'][etype] += 1

                        tier = ext.automation_tier.value if hasattr(ext.automation_tier, 'value') else str(ext.automation_tier)
                        if tier == 'full_auto':
                            category_stats[category]['full_auto'] += 1
                        elif tier == 'spot_check':
                            category_stats[category]['spot_check'] += 1
                        elif tier == 'verify':
                            category_stats[category]['verify'] += 1
                        else:
                            category_stats[category]['manual'] += 1

                        if ext.has_complete_ci:
                            category_stats[category]['with_complete_ci'] += 1

                    # Show summary
                    type_counts = defaultdict(int)
                    for ext in extractions:
                        etype = ext.effect_type.value if hasattr(ext.effect_type, 'value') else str(ext.effect_type)
                        type_counts[etype] += 1

                    print(f"    -> Found: {dict(type_counts)}")

                    # Show best extractions
                    best = sorted(extractions, key=lambda x: x.calibrated_confidence, reverse=True)[:3]
                    for ext in best:
                        etype = ext.effect_type.value if hasattr(ext.effect_type, 'value') else str(ext.effect_type)
                        ci_str = ""
                        if ext.ci:
                            ci_str = f" ({ext.ci.lower:.2f}-{ext.ci.upper:.2f})"
                        tier = ext.automation_tier.value if hasattr(ext.automation_tier, 'value') else str(ext.automation_tier)
                        print(f"       {etype}: {ext.point_estimate:.2f}{ci_str} [{tier}, conf={ext.calibrated_confidence:.2f}]")

                    # Store result
                    all_results.append({
                        'pdf': pdf_path.name,
                        'category': category,
                        'pages': len(content.pages),
                        'chars': len(full_text),
                        'extractions': len(extractions),
                        'by_type': dict(type_counts),
                        'full_auto': sum(1 for e in extractions if (e.automation_tier.value if hasattr(e.automation_tier, 'value') else str(e.automation_tier)) == 'full_auto'),
                        'with_ci': sum(1 for e in extractions if e.has_complete_ci),
                        'best_effects': [
                            {
                                'type': e.effect_type.value if hasattr(e.effect_type, 'value') else str(e.effect_type),
                                'value': e.point_estimate,
                                'ci_low': e.ci.lower if e.ci else None,
                                'ci_high': e.ci.upper if e.ci else None,
                                'confidence': e.calibrated_confidence,
                                'tier': e.automation_tier.value if hasattr(e.automation_tier, 'value') else str(e.automation_tier)
                            }
                            for e in best
                        ]
                    })
                else:
                    print(f"    -> No effect estimates found")
                    all_results.append({
                        'pdf': pdf_path.name,
                        'category': category,
                        'pages': len(content.pages),
                        'chars': len(full_text),
                        'extractions': 0
                    })

            except Exception as e:
                print(f"    -> ERROR: {str(e)[:50]}")

    # Print summary
    print("\n" + "=" * 70)
    print("ENHANCED VALIDATION SUMMARY")
    print("=" * 70)

    print(f"\n{'Category':<15} {'PDFs':<6} {'Effects':<10} {'W/CI':<8} {'FullAuto':<10} {'Avg Conf':<10}")
    print("-" * 70)

    grand_effects = 0
    grand_with_ci = 0
    grand_full_auto = 0

    for cat in sorted(category_stats.keys()):
        stats = category_stats[cat]
        grand_effects += stats['total_effects']
        grand_with_ci += stats['with_complete_ci']
        grand_full_auto += stats['full_auto']

        pct_ci = (stats['with_complete_ci'] / stats['total_effects'] * 100) if stats['total_effects'] > 0 else 0
        pct_auto = (stats['full_auto'] / stats['total_effects'] * 100) if stats['total_effects'] > 0 else 0

        print(f"{cat:<15} {stats['parsed']:<6} {stats['total_effects']:<10} "
              f"{stats['with_complete_ci']:<8} {stats['full_auto']:<10}")

    print("-" * 70)

    pct_ci_total = (grand_with_ci / grand_effects * 100) if grand_effects > 0 else 0
    pct_auto_total = (grand_full_auto / grand_effects * 100) if grand_effects > 0 else 0

    print(f"{'TOTAL':<15} {total_processed:<6} {grand_effects:<10} "
          f"{grand_with_ci:<8} {grand_full_auto:<10}")

    # Effect type breakdown
    print("\n" + "=" * 70)
    print("EFFECT TYPE BREAKDOWN")
    print("=" * 70)

    total_by_type = defaultdict(int)
    for cat, stats in category_stats.items():
        for etype, count in stats['by_type'].items():
            total_by_type[etype] += count

    print(f"\n{'Type':<10} {'Count':<10} {'Percentage':<15}")
    print("-" * 35)

    for etype in ['HR', 'OR', 'RR', 'MD', 'SMD']:
        if etype in total_by_type:
            pct = (total_by_type[etype] / grand_effects * 100) if grand_effects > 0 else 0
            print(f"{etype:<10} {total_by_type[etype]:<10} {pct:.1f}%")

    # Final metrics
    print("\n" + "=" * 70)
    print("FINAL METRICS")
    print("=" * 70)

    print(f"""
PDFs Processed:              {total_processed}
PDFs with Effects:           {sum(1 for r in all_results if r.get('extractions', 0) > 0)}
Total Effects Extracted:     {grand_effects}
Effects with Complete CI:    {grand_with_ci} ({pct_ci_total:.1f}%)
Full-Auto Tier:              {grand_full_auto} ({pct_auto_total:.1f}%)

By Effect Type:
  - Hazard Ratios (HR):      {total_by_type.get('HR', 0)}
  - Odds Ratios (OR):        {total_by_type.get('OR', 0)}
  - Risk Ratios (RR):        {total_by_type.get('RR', 0)}
  - Mean Differences (MD):   {total_by_type.get('MD', 0)}
  - Standardized MD (SMD):   {total_by_type.get('SMD', 0)}
""")

    # Save results
    output_file = Path(__file__).parent / 'output' / 'enhanced_pdf_validation.json'

    with open(output_file, 'w') as f:
        json.dump({
            'validation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'version': '4.0.7',
            'summary': {
                'pdfs_processed': total_processed,
                'total_effects': grand_effects,
                'with_complete_ci': grand_with_ci,
                'pct_with_ci': round(pct_ci_total, 1),
                'full_auto': grand_full_auto,
                'pct_full_auto': round(pct_auto_total, 1)
            },
            'by_category': {cat: dict(stats) for cat, stats in category_stats.items()},
            'by_effect_type': dict(total_by_type),
            'results': all_results
        }, f, indent=2, default=str)

    print(f"Results saved to: {output_file}")

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_enhanced_validation()
