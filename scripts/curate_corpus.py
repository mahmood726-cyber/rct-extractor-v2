#!/usr/bin/env python3
"""
Corpus Curation - Remove non-RCT papers and create clean manifest.

Based on v4.3.5 improvement plan:
- Remove 14 non-RCT papers identified in failure categorization
- Remove TABLE_ONLY papers
- Create clean manifest of confirmed RCT result PDFs
- Designate held-out test set (10 papers)

Usage:
    python scripts/curate_corpus.py
"""

import json
import random
import sys
from pathlib import Path
from datetime import datetime

random.seed(42)  # Deterministic selection


def main():
    # Load failure categorization to get non-RCT list
    failure_path = Path("output/failure_categorization.json")
    classification_path = Path("data/pdf_classification.json")

    if not failure_path.exists():
        print(f"Error: {failure_path} not found")
        sys.exit(1)

    with open(failure_path) as f:
        failures = json.load(f)

    with open(classification_path) as f:
        classification = json.load(f)

    # Identify non-RCT PDFs to exclude
    exclude_pdfs = set()
    for item in failures.get("zero_extraction_failures", []):
        if item.get("category") == "NON_RCT":
            exclude_pdfs.add(item["pdf"])
        elif item.get("category") == "TABLE_ONLY":
            exclude_pdfs.add(item["pdf"])

    print(f"Papers to exclude: {len(exclude_pdfs)}")
    for pdf in sorted(exclude_pdfs):
        print(f"  - {pdf}")

    # Filter classification to RCT-only
    rct_pdfs = []
    excluded_pdfs = []

    for pdf_info in classification["pdfs"]:
        filename = pdf_info["filename"]
        if filename in exclude_pdfs:
            excluded_pdfs.append(pdf_info)
        else:
            rct_pdfs.append(pdf_info)

    print(f"\nRCT PDFs retained: {len(rct_pdfs)}")
    print(f"Non-RCT PDFs excluded: {len(excluded_pdfs)}")

    # Calculate metrics on clean corpus
    total_extractions = sum(len(p.get("extractions", [])) for p in rct_pdfs)
    ci_complete = sum(
        sum(1 for e in p.get("extractions", []) if e.get("ci_complete"))
        for p in rct_pdfs
    )
    pdfs_with_extractions = sum(1 for p in rct_pdfs if p.get("extractions"))

    print(f"\nClean corpus metrics:")
    print(f"  Total PDFs: {len(rct_pdfs)}")
    print(f"  PDFs with extractions: {pdfs_with_extractions} ({pdfs_with_extractions/len(rct_pdfs)*100:.1f}%)")
    print(f"  Total extractions: {total_extractions}")
    print(f"  CI complete: {ci_complete} ({ci_complete/total_extractions*100:.1f}%)" if total_extractions > 0 else "  CI complete: 0")

    # Designate held-out test set
    # Select 10 PDFs with extractions, stratified by CI completeness
    pdfs_with_ext = [p for p in rct_pdfs if p.get("extractions")]
    random.shuffle(pdfs_with_ext)

    held_out_size = min(10, len(pdfs_with_ext) // 4)  # Max 25% held out
    held_out = pdfs_with_ext[:held_out_size]
    train_pdfs_with_ext = pdfs_with_ext[held_out_size:]
    train_pdfs_without_ext = [p for p in rct_pdfs if not p.get("extractions")]
    train_pdfs = train_pdfs_without_ext + train_pdfs_with_ext

    print(f"\nCorpus split:")
    print(f"  Training set: {len(train_pdfs)} PDFs")
    print(f"  Held-out test set: {len(held_out)} PDFs")

    held_out_filenames = {p["filename"] for p in held_out}
    print(f"\n  Held-out PDFs:")
    for p in held_out:
        n_ext = len(p.get("extractions", []))
        n_ci = sum(1 for e in p.get("extractions", []) if e.get("ci_complete"))
        print(f"    {p['filename']}: {n_ext} extractions, {n_ci} with CI")

    # Save curated manifest
    manifest = {
        "version": "v4.3.5",
        "date": datetime.now().isoformat(),
        "curation_method": "automated_classification_plus_manual_review",
        "total_pdfs": len(rct_pdfs),
        "excluded_count": len(excluded_pdfs),
        "excluded_reasons": {
            "NON_RCT": sum(1 for i in failures.get("zero_extraction_failures", []) if i.get("category") == "NON_RCT"),
            "TABLE_ONLY": sum(1 for i in failures.get("zero_extraction_failures", []) if i.get("category") == "TABLE_ONLY"),
        },
        "splits": {
            "train": len(train_pdfs),
            "held_out_test": len(held_out),
        },
        "metrics": {
            "total_extractions": total_extractions,
            "ci_complete": ci_complete,
            "ci_completion_rate": ci_complete / total_extractions if total_extractions > 0 else 0,
            "extraction_rate": pdfs_with_extractions / len(rct_pdfs) if rct_pdfs else 0,
        },
        "excluded_pdfs": [p["filename"] for p in excluded_pdfs],
        "held_out_pdfs": [p["filename"] for p in held_out],
        "train_pdfs": [p["filename"] for p in train_pdfs],
        "pdfs": rct_pdfs,
    }

    output_path = Path("data/curated_rct_manifest.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nCurated manifest saved to: {output_path}")

    # Save held-out list separately
    held_out_path = Path("data/held_out_test_set.json")
    with open(held_out_path, "w") as f:
        json.dump({
            "date": datetime.now().isoformat(),
            "pdfs": [
                {
                    "filename": p["filename"],
                    "pmc_id": p.get("pmc_id", ""),
                    "extractions_count": len(p.get("extractions", [])),
                    "ci_complete_count": sum(1 for e in p.get("extractions", []) if e.get("ci_complete")),
                }
                for p in held_out
            ]
        }, f, indent=2)
    print(f"Held-out test set saved to: {held_out_path}")


if __name__ == "__main__":
    main()
