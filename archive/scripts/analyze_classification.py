#!/usr/bin/env python3
"""Quick analysis of classification results."""

import json
from pathlib import Path

def main():
    with open(Path("data/pdf_classification.json")) as f:
        data = json.load(f)

    # Calculate metrics
    total_extractions = sum(p['extraction_count'] for p in data['pdfs'])
    total_ci_complete = sum(p['ci_complete_count'] for p in data['pdfs'])
    pdfs_with_extractions = sum(1 for p in data['pdfs'] if p['extraction_count'] > 0)

    ci_completion = total_ci_complete / total_extractions * 100 if total_extractions > 0 else 0
    extraction_rate = pdfs_with_extractions / data['total_pdfs'] * 100

    print("=== PDF Corpus Analysis ===")
    print(f"Total PDFs: {data['total_pdfs']}")
    print(f"PDFs with extractions: {pdfs_with_extractions} ({extraction_rate:.1f}%)")
    print(f"Total extractions: {total_extractions}")
    print(f"CI complete: {total_ci_complete} ({ci_completion:.1f}%)")
    print()
    print("Classification:")
    print(f"  Class A: {data['by_class']['A']}")
    print(f"  Class B: {data['by_class']['B']}")
    print(f"  Class C: {data['by_class']['C']}")
    print()

    # Effect type distribution
    effect_counts = {}
    for p in data['pdfs']:
        for t in p.get('effect_types', []):
            effect_counts[t] = effect_counts.get(t, 0) + 1

    print("Effect type distribution:")
    for t, c in sorted(effect_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    # Papers with most extractions
    print()
    print("Top 10 PDFs by extractions:")
    sorted_pdfs = sorted(data['pdfs'], key=lambda x: x['extraction_count'], reverse=True)
    for p in sorted_pdfs[:10]:
        print(f"  {p['filename']}: {p['extraction_count']} extractions, {p['ci_complete_count']} CI, class={p['classification']}")

    # CI gap analysis
    print()
    print("=== CI Gap Analysis ===")
    incomplete_ci = total_extractions - total_ci_complete
    print(f"Extractions missing CI: {incomplete_ci} ({incomplete_ci/total_extractions*100:.1f}%)")

    # Zero-extraction PDFs
    zero_extract = [p for p in data['pdfs'] if p['extraction_count'] == 0]
    print(f"Zero-extraction PDFs: {len(zero_extract)}")
    for p in zero_extract[:5]:
        print(f"  {p['filename']}: {p.get('title_snippet', '')[:60]}...")


if __name__ == "__main__":
    main()
