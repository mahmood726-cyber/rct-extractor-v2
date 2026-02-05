"""
Massive RCT Extractor Validation - 77,000+ PDFs
================================================
Tests extraction across all available PDF collections.
"""
import sys
import json
import re
import random
import time
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
from dataclasses import dataclass
import warnings
import logging

warnings.filterwarnings('ignore')
logging.disable(logging.WARNING)

sys.path.insert(0, str(Path(__file__).parent / 'src'))

import fitz  # PyMuPDF
from src.core.extractor import NumericParser


# PDF Collections
COLLECTIONS = {
    'cardiology': Path('C:/Users/user/cardiology_rcts'),
    'diabetes': Path('C:/Users/user/diabetes_rcts'),
    'oncology': Path('C:/Users/user/oncology_rcts'),
    'neurology': Path('C:/Users/user/neurology_rcts'),
    'infectious': Path('C:/Users/user/infectious_rcts'),
    'respiratory': Path('C:/Users/user/respiratory_rcts'),
    'rheumatology': Path('C:/Users/user/rheumatology_rcts'),
    'downloads': Path('C:/Users/user/Downloads'),
}

# Sample size per collection
SAMPLE_PER_COLLECTION = 500


@dataclass
class ExtractionStats:
    """Stats for a single PDF"""
    pdf_name: str
    collection: str
    parsed: bool = False
    text_length: int = 0
    num_pages: int = 0
    hr_count: int = 0
    or_count: int = 0
    rr_count: int = 0
    rd_count: int = 0
    md_count: int = 0
    with_ci: int = 0
    sample_hr: str = ""


def extract_all_effects(text: str) -> Dict[str, List[Dict]]:
    """Extract all effect estimates from text"""
    text = text.replace('\xb7', '.').replace('\u2212', '-').replace('\u2013', '-').replace('\u2014', '-')
    results = {'HR': [], 'OR': [], 'RR': [], 'RD': [], 'MD': []}

    # Simplified but robust patterns
    patterns = {
        'HR': [
            r'hazard\s*ratio[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'hazard\s*ratio[,;:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'hazard\s*ratio\s+(?:of|was|for\s+\w+\s+was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bHR\b[,;:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)\s*\)',
            r'hazard\s*ratio[,;:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)\s*\)',
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
        'RD': [
            r'risk\s*difference[,;:\s]+([+-]?\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+([+-]?\d+\.?\d*)\s*(?:to|[-])\s*([+-]?\d+\.?\d*)',
            r'absolute\s*(?:risk)?\s*(?:reduction|difference)[,;:\s]+([+-]?\d+\.?\d*)\s*\(\s*([+-]?\d+\.?\d*)\s*(?:to|[-])\s*([+-]?\d+\.?\d*)',
        ],
        'MD': [
            r'mean\s*difference[,;:\s]+([+-]?\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+([+-]?\d+\.?\d*)\s*(?:to|[-])\s*([+-]?\d+\.?\d*)',
            r'difference[,;:\s]+([+-]?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*([+-]?\d+\.?\d*)\s*(?:to|[-])\s*([+-]?\d+\.?\d*)',
        ],
    }

    plausibility = {
        'HR': lambda v: 0.05 <= v <= 30,
        'OR': lambda v: 0.01 <= v <= 100,
        'RR': lambda v: 0.05 <= v <= 30,
        'RD': lambda v: -100 <= v <= 100,
        'MD': lambda v: -1000 <= v <= 1000,
    }

    for measure_type, pattern_list in patterns.items():
        seen = set()
        for pattern in pattern_list:
            try:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        value = float(match.group(1))
                        ci_low = float(match.group(2)) if len(match.groups()) > 1 else None
                        ci_high = float(match.group(3)) if len(match.groups()) > 2 else None

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


def process_pdf(pdf_path: Path, collection: str) -> ExtractionStats:
    """Process a single PDF and return stats"""
    stats = ExtractionStats(pdf_name=pdf_path.name[:60], collection=collection)

    try:
        doc = fitz.open(str(pdf_path))
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        stats.num_pages = len(doc)
        doc.close()

        stats.parsed = True
        stats.text_length = len(text)

        if len(text) < 100:
            return stats

        effects = extract_all_effects(text)

        stats.hr_count = len(effects['HR'])
        stats.or_count = len(effects['OR'])
        stats.rr_count = len(effects['RR'])
        stats.rd_count = len(effects['RD'])
        stats.md_count = len(effects['MD'])

        stats.with_ci = sum(
            sum(1 for e in effects[t] if e['has_ci'])
            for t in effects
        )

        # Sample HR for display
        if effects['HR']:
            h = effects['HR'][0]
            if h['has_ci']:
                stats.sample_hr = f"HR {h['value']:.2f} ({h['ci_low']:.2f}-{h['ci_high']:.2f})"
            else:
                stats.sample_hr = f"HR {h['value']:.2f}"

    except Exception as e:
        pass

    return stats


def main():
    print("=" * 80)
    print("MASSIVE RCT EXTRACTOR VALIDATION - 77,000+ PDFs")
    print("=" * 80)

    random.seed(42)

    # Collect PDFs from each collection
    all_samples = []

    print("\nPhase 1: Sampling PDFs from collections...")
    print("-" * 80)

    for name, path in COLLECTIONS.items():
        if not path.exists():
            print(f"  {name}: NOT FOUND")
            continue

        pdfs = list(path.rglob("*.pdf"))
        print(f"  {name}: {len(pdfs):,} PDFs available")

        # Sample
        sample_size = min(SAMPLE_PER_COLLECTION, len(pdfs))
        if sample_size > 0:
            sampled = random.sample(pdfs, sample_size)
            for pdf in sampled:
                all_samples.append((pdf, name))

    print(f"\n  Total sampled: {len(all_samples)} PDFs")

    # Process
    print("\nPhase 2: Processing PDFs...")
    print("-" * 80)

    results = []
    start_time = time.time()

    for i, (pdf_path, collection) in enumerate(all_samples):
        if (i + 1) % 200 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            eta = (len(all_samples) - i - 1) / rate
            print(f"  Progress: {i + 1}/{len(all_samples)} ({rate:.1f} PDFs/sec, ETA: {eta:.0f}s)")

        stats = process_pdf(pdf_path, collection)
        results.append(stats)

    elapsed = time.time() - start_time

    # Aggregate stats
    print("\n" + "=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)

    total_parsed = sum(1 for r in results if r.parsed)
    total_with_effects = sum(1 for r in results if r.hr_count + r.or_count + r.rr_count > 0)
    total_hrs = sum(r.hr_count for r in results)
    total_ors = sum(r.or_count for r in results)
    total_rrs = sum(r.rr_count for r in results)
    total_rds = sum(r.rd_count for r in results)
    total_mds = sum(r.md_count for r in results)
    total_with_ci = sum(r.with_ci for r in results)
    total_pages = sum(r.num_pages for r in results)

    print(f"""
OVERALL STATISTICS:
  PDFs processed: {len(results):,}
  Successfully parsed: {total_parsed:,} ({total_parsed/len(results)*100:.1f}%)
  Total pages scanned: {total_pages:,}
  Processing time: {elapsed:.1f}s ({len(results)/elapsed:.1f} PDFs/sec)

EXTRACTION RESULTS:
  PDFs with effect estimates: {total_with_effects:,} ({total_with_effects/total_parsed*100:.1f}%)

  By measure type:
    Hazard Ratios (HR): {total_hrs:,}
    Odds Ratios (OR): {total_ors:,}
    Relative Risks (RR): {total_rrs:,}
    Risk Differences (RD): {total_rds:,}
    Mean Differences (MD): {total_mds:,}

  TOTAL EFFECTS: {total_hrs + total_ors + total_rrs + total_rds + total_mds:,}
  With confidence intervals: {total_with_ci:,}
""")

    # By collection
    print("BY COLLECTION:")
    print("-" * 80)
    print(f"{'Collection':<15} {'PDFs':<8} {'Parsed':<8} {'w/Effects':<10} {'HRs':<8} {'ORs':<8} {'RRs':<8}")
    print("-" * 80)

    for name in COLLECTIONS.keys():
        coll_results = [r for r in results if r.collection == name]
        if not coll_results:
            continue

        parsed = sum(1 for r in coll_results if r.parsed)
        with_effects = sum(1 for r in coll_results if r.hr_count + r.or_count + r.rr_count > 0)
        hrs = sum(r.hr_count for r in coll_results)
        ors = sum(r.or_count for r in coll_results)
        rrs = sum(r.rr_count for r in coll_results)

        print(f"{name:<15} {len(coll_results):<8} {parsed:<8} {with_effects:<10} {hrs:<8} {ors:<8} {rrs:<8}")

    print("-" * 80)

    # Top PDFs
    results_with_effects = [r for r in results if r.hr_count > 0]
    results_with_effects.sort(key=lambda x: x.hr_count, reverse=True)

    print("\nTOP 30 PDFs BY HR COUNT:")
    for r in results_with_effects[:30]:
        sample = f" [{r.sample_hr}]" if r.sample_hr else ""
        print(f"  {r.collection}/{r.pdf_name}: {r.hr_count} HRs{sample}")

    # Save results
    output = {
        'summary': {
            'total_pdfs': len(results),
            'parsed': total_parsed,
            'with_effects': total_with_effects,
            'total_hrs': total_hrs,
            'total_ors': total_ors,
            'total_rrs': total_rrs,
            'total_rds': total_rds,
            'total_mds': total_mds,
            'total_with_ci': total_with_ci,
            'total_pages': total_pages,
            'elapsed_seconds': elapsed,
        },
        'by_collection': {},
        'top_pdfs': [
            {'pdf': r.pdf_name, 'collection': r.collection, 'hrs': r.hr_count, 'sample': r.sample_hr}
            for r in results_with_effects[:100]
        ]
    }

    for name in COLLECTIONS.keys():
        coll_results = [r for r in results if r.collection == name]
        if coll_results:
            output['by_collection'][name] = {
                'total': len(coll_results),
                'parsed': sum(1 for r in coll_results if r.parsed),
                'with_effects': sum(1 for r in coll_results if r.hr_count + r.or_count + r.rr_count > 0),
                'hrs': sum(r.hr_count for r in coll_results),
                'ors': sum(r.or_count for r in coll_results),
                'rrs': sum(r.rr_count for r in coll_results),
            }

    output_file = Path(__file__).parent / 'output' / 'massive_validation.json'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
