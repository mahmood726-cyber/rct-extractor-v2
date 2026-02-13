#!/usr/bin/env python3
"""
Deep PDF Analysis for RCT Extractor v4.0.7
Performs detailed analysis of PDF extraction results including:
- Effect estimate quality assessment
- CI completeness analysis
- Pattern coverage statistics
- Cross-validation with known trials

Usage:
    python run_deep_pdf_analysis.py
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import re

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.enhanced_extractor_v3 import EnhancedExtractor, EffectType
from src.pdf.pdf_parser import PDFParser


# Known trial effect estimates for validation
KNOWN_TRIALS = {
    # Format: PMC_ID -> {effect_type, value, ci_low, ci_high}
    'PMC6893803': {'trial': 'DAPA-HF', 'hr': 0.74, 'ci': (0.65, 0.85)},
    'PMC4159808': {'trial': 'PARADIGM-HF', 'hr': 0.80, 'ci': (0.73, 0.87)},
    'PMC5624340': {'trial': 'EMPA-REG', 'hr': 0.62, 'ci': (0.49, 0.77)},
    'PMC7190947': {'trial': 'EMPEROR-Reduced', 'hr': 0.75, 'ci': (0.65, 0.86)},
    'PMC8592006': {'trial': 'EMPEROR-Preserved', 'hr': 0.79, 'ci': (0.69, 0.90)},
}


def analyze_effect_quality(effect: dict) -> dict:
    """Analyze quality of extracted effect"""
    quality = {
        'has_ci': False,
        'ci_complete': False,
        'value_plausible': False,
        'ci_plausible': False,
        'quality_score': 0.0
    }

    value = effect.get('value', 0)
    ci_low = effect.get('ci_low')
    ci_high = effect.get('ci_high')
    effect_type = effect.get('measure_type', 'HR')

    # Check CI presence
    if ci_low is not None and ci_high is not None:
        quality['has_ci'] = True
        quality['ci_complete'] = True

        # Check CI plausibility
        if ci_low < value < ci_high:
            quality['ci_plausible'] = True

    # Check value plausibility
    if effect_type in ['HR', 'RR']:
        quality['value_plausible'] = 0.05 <= value <= 20
    elif effect_type == 'OR':
        quality['value_plausible'] = 0.05 <= value <= 50
    else:
        quality['value_plausible'] = True

    # Calculate quality score
    score = 0.0
    if quality['value_plausible']:
        score += 0.3
    if quality['has_ci']:
        score += 0.3
    if quality['ci_complete']:
        score += 0.2
    if quality['ci_plausible']:
        score += 0.2

    quality['quality_score'] = score

    return quality


def analyze_pdf_effects(pdf_result: dict) -> dict:
    """Analyze all effects from a PDF"""
    analysis = {
        'pdf': pdf_result['pdf'],
        'category': pdf_result['category'],
        'total_effects': pdf_result['total_effects'],
        'high_quality': 0,
        'with_complete_ci': 0,
        'by_type': defaultdict(int),
        'quality_scores': [],
        'best_effect': None
    }

    effects = pdf_result.get('effects', [])

    for effect in effects:
        quality = analyze_effect_quality(effect)
        analysis['quality_scores'].append(quality['quality_score'])
        analysis['by_type'][effect.get('measure_type', 'unknown')] += 1

        if quality['quality_score'] >= 0.8:
            analysis['high_quality'] += 1

        if quality['ci_complete']:
            analysis['with_complete_ci'] += 1

        # Track best effect
        if analysis['best_effect'] is None or quality['quality_score'] > analysis['best_effect']['score']:
            analysis['best_effect'] = {
                'type': effect.get('measure_type'),
                'value': effect.get('value'),
                'ci': (effect.get('ci_low'), effect.get('ci_high')),
                'score': quality['quality_score']
            }

    # Calculate average quality
    if analysis['quality_scores']:
        analysis['avg_quality'] = sum(analysis['quality_scores']) / len(analysis['quality_scores'])
    else:
        analysis['avg_quality'] = 0.0

    return analysis


def run_deep_analysis():
    """Run deep analysis on all PDF results"""
    print("=" * 70)
    print("RCT EXTRACTOR v4.0.7 - DEEP PDF ANALYSIS")
    print("=" * 70)

    # Load validation results
    results_file = Path(__file__).parent / 'output' / 'real_pdf_validation_105.json'

    if not results_file.exists():
        print("ERROR: Run run_105_pdf_validation.py first")
        return

    with open(results_file) as f:
        data = json.load(f)

    print(f"\nLoaded {data['summary']['total_pdfs']} PDF results")
    print(f"Total effects: {data['summary']['total_effects']}")

    # Analyze each PDF
    all_analyses = []
    category_stats = defaultdict(lambda: {
        'pdfs': 0,
        'effects': 0,
        'high_quality': 0,
        'with_ci': 0,
        'avg_quality': []
    })

    print("\n" + "=" * 70)
    print("DETAILED PDF ANALYSIS")
    print("=" * 70)

    for result in data['results']:
        analysis = analyze_pdf_effects(result)
        all_analyses.append(analysis)

        cat = result['category']
        category_stats[cat]['pdfs'] += 1
        category_stats[cat]['effects'] += result['total_effects']
        category_stats[cat]['high_quality'] += analysis['high_quality']
        category_stats[cat]['with_ci'] += analysis['with_complete_ci']
        category_stats[cat]['avg_quality'].append(analysis['avg_quality'])

        # Print PDFs with high-quality effects
        if analysis['high_quality'] > 0:
            print(f"\n{result['pdf']} ({cat})")
            print(f"  Effects: {result['total_effects']} total, {analysis['high_quality']} high-quality")
            if analysis['best_effect']:
                be = analysis['best_effect']
                ci_str = ""
                if be['ci'][0] and be['ci'][1]:
                    ci_str = f" ({be['ci'][0]:.2f}-{be['ci'][1]:.2f})"
                print(f"  Best: {be['type']} {be['value']:.2f}{ci_str} [score: {be['score']:.2f}]")

    # Category summary
    print("\n" + "=" * 70)
    print("CATEGORY QUALITY SUMMARY")
    print("=" * 70)

    print(f"\n{'Category':<15} {'PDFs':<6} {'Effects':<10} {'HQ':<6} {'%HQ':<8} {'W/CI':<8} {'AvgQ':<8}")
    print("-" * 70)

    total_effects = 0
    total_hq = 0
    total_ci = 0

    for cat in sorted(category_stats.keys()):
        stats = category_stats[cat]
        pct_hq = (stats['high_quality'] / stats['effects'] * 100) if stats['effects'] > 0 else 0
        avg_q = sum(stats['avg_quality']) / len(stats['avg_quality']) if stats['avg_quality'] else 0

        print(f"{cat:<15} {stats['pdfs']:<6} {stats['effects']:<10} {stats['high_quality']:<6} "
              f"{pct_hq:>5.1f}%  {stats['with_ci']:<8} {avg_q:.2f}")

        total_effects += stats['effects']
        total_hq += stats['high_quality']
        total_ci += stats['with_ci']

    print("-" * 70)
    pct_total_hq = (total_hq / total_effects * 100) if total_effects > 0 else 0
    pct_total_ci = (total_ci / total_effects * 100) if total_effects > 0 else 0
    print(f"{'TOTAL':<15} {data['summary']['total_pdfs']:<6} {total_effects:<10} {total_hq:<6} "
          f"{pct_total_hq:>5.1f}%  {total_ci:<8}")

    # Effect type distribution
    print("\n" + "=" * 70)
    print("EFFECT TYPE DISTRIBUTION")
    print("=" * 70)

    type_counts = defaultdict(lambda: {'total': 0, 'with_ci': 0})

    for result in data['results']:
        for effect in result.get('effects', []):
            etype = effect.get('measure_type', 'unknown')
            type_counts[etype]['total'] += 1
            if effect.get('ci_low') and effect.get('ci_high'):
                type_counts[etype]['with_ci'] += 1

    print(f"\n{'Type':<10} {'Count':<10} {'With CI':<10} {'% CI':<10}")
    print("-" * 40)

    for etype in ['HR', 'OR', 'RR']:
        counts = type_counts[etype]
        pct = (counts['with_ci'] / counts['total'] * 100) if counts['total'] > 0 else 0
        print(f"{etype:<10} {counts['total']:<10} {counts['with_ci']:<10} {pct:.1f}%")

    # CI completeness by value range
    print("\n" + "=" * 70)
    print("CI COMPLETENESS BY VALUE RANGE")
    print("=" * 70)

    ranges = {
        '<0.5': {'total': 0, 'with_ci': 0},
        '0.5-0.8': {'total': 0, 'with_ci': 0},
        '0.8-1.2': {'total': 0, 'with_ci': 0},
        '1.2-2.0': {'total': 0, 'with_ci': 0},
        '>2.0': {'total': 0, 'with_ci': 0},
    }

    for result in data['results']:
        for effect in result.get('effects', []):
            value = effect.get('value', 0)
            has_ci = effect.get('ci_low') and effect.get('ci_high')

            if value < 0.5:
                key = '<0.5'
            elif value < 0.8:
                key = '0.5-0.8'
            elif value < 1.2:
                key = '0.8-1.2'
            elif value < 2.0:
                key = '1.2-2.0'
            else:
                key = '>2.0'

            ranges[key]['total'] += 1
            if has_ci:
                ranges[key]['with_ci'] += 1

    print(f"\n{'Range':<12} {'Count':<10} {'With CI':<10} {'% CI':<10}")
    print("-" * 42)

    for range_name, counts in ranges.items():
        pct = (counts['with_ci'] / counts['total'] * 100) if counts['total'] > 0 else 0
        print(f"{range_name:<12} {counts['total']:<10} {counts['with_ci']:<10} {pct:.1f}%")

    # Top PDFs by effect count
    print("\n" + "=" * 70)
    print("TOP 10 PDFs BY EFFECT COUNT")
    print("=" * 70)

    sorted_results = sorted(data['results'], key=lambda x: x['total_effects'], reverse=True)

    print(f"\n{'PDF':<25} {'Category':<15} {'HR':<6} {'OR':<6} {'RR':<6} {'Total':<8}")
    print("-" * 70)

    for result in sorted_results[:10]:
        print(f"{result['pdf'][:24]:<25} {result['category']:<15} "
              f"{result['hrs']:<6} {result['ors']:<6} {result['rrs']:<6} {result['total_effects']:<8}")

    # Summary metrics
    print("\n" + "=" * 70)
    print("FINAL METRICS")
    print("=" * 70)

    print(f"""
PDFs Processed:              {data['summary']['total_pdfs']}
PDFs with Effects:           {data['summary']['with_effects']} ({data['summary']['effect_rate']:.1f}%)
Total Effects Extracted:     {total_effects}
High-Quality Effects:        {total_hq} ({pct_total_hq:.1f}%)
Effects with Complete CI:    {total_ci} ({pct_total_ci:.1f}%)

By Effect Type:
  - Hazard Ratios (HR):      {data['summary']['total_hrs']}
  - Odds Ratios (OR):        {data['summary']['total_ors']}
  - Relative Risks (RR):     {data['summary']['total_rrs']}

Average Effects per PDF:     {data['summary']['avg_effects_per_pdf']:.1f}
Parse Success Rate:          {data['summary']['parse_rate']:.1f}%
""")

    # Save detailed analysis
    output_file = Path(__file__).parent / 'output' / 'deep_pdf_analysis.json'

    with open(output_file, 'w') as f:
        json.dump({
            'summary': {
                'total_pdfs': data['summary']['total_pdfs'],
                'total_effects': total_effects,
                'high_quality': total_hq,
                'with_ci': total_ci,
                'pct_high_quality': round(pct_total_hq, 1),
                'pct_with_ci': round(pct_total_ci, 1)
            },
            'by_category': {cat: {
                'pdfs': stats['pdfs'],
                'effects': stats['effects'],
                'high_quality': stats['high_quality'],
                'avg_quality': round(sum(stats['avg_quality']) / len(stats['avg_quality']), 2) if stats['avg_quality'] else 0
            } for cat, stats in category_stats.items()},
            'effect_type_distribution': dict(type_counts),
            'value_range_distribution': ranges
        }, f, indent=2)

    print(f"Detailed analysis saved to: {output_file}")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_deep_analysis()
