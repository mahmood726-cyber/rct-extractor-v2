#!/usr/bin/env python3
"""
Apply CI Proximity Search to PDF corpus and measure improvement.

This script:
1. Loads the classification results with extractions
2. For each extraction missing CI, runs proximity search
3. Reports how many CIs were recovered
4. Outputs enhanced classification JSON

Usage:
    python scripts/apply_ci_proximity_search.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.ci_proximity_search import CIProximitySearch
from src.pdf.pdf_parser import PDFParser


def load_classification(path: Path) -> dict:
    """Load classification results."""
    with open(path) as f:
        return json.load(f)


def apply_proximity_search(classification: dict, pdf_dir: Path) -> dict:
    """Apply CI proximity search to all extractions missing CI."""
    searcher = CIProximitySearch()  # v4.3.5: defaults to 150 chars window
    parser = PDFParser()

    results = {
        "date": datetime.now().isoformat(),
        "input_classification": classification["date"],
        "total_extractions": 0,
        "missing_ci_before": 0,
        "missing_ci_after": 0,
        "cis_recovered": 0,
        "recovery_details": [],
        "enhanced_pdfs": []
    }

    for pdf_info in classification["pdfs"]:
        extractions = pdf_info.get("extractions", [])
        if not extractions:
            results["enhanced_pdfs"].append(pdf_info)
            continue

        results["total_extractions"] += len(extractions)

        # Count missing CIs before
        missing_before = sum(1 for e in extractions if not e.get("ci_complete"))
        results["missing_ci_before"] += missing_before

        if missing_before == 0:
            results["enhanced_pdfs"].append(pdf_info)
            continue

        # Load PDF text
        pdf_path = pdf_dir / pdf_info["filename"]
        if not pdf_path.exists():
            results["enhanced_pdfs"].append(pdf_info)
            continue

        try:
            pdf_content = parser.parse(str(pdf_path))
            text = "\n".join(page.full_text for page in pdf_content.pages)
        except Exception as e:
            print(f"  Error reading {pdf_info['filename']}: {e}")
            results["enhanced_pdfs"].append(pdf_info)
            continue

        # Try to recover CIs for each extraction
        enhanced_extractions = []
        recovered = 0

        for ext in extractions:
            if ext.get("ci_complete"):
                enhanced_extractions.append(ext)
                continue

            # Search for CI
            value = ext.get("value")
            effect_type = ext.get("effect_type")

            ci_result = searcher.search_ci_near_value(text, value, effect_type)

            if ci_result:
                ext["ci_lower"] = ci_result.ci_lower
                ext["ci_upper"] = ci_result.ci_upper
                ext["ci_complete"] = True
                ext["ci_source"] = "proximity_search"
                ext["ci_confidence"] = ci_result.confidence
                ext["ci_method"] = ci_result.method
                recovered += 1

                results["recovery_details"].append({
                    "pdf": pdf_info["filename"],
                    "effect_type": effect_type,
                    "value": value,
                    "ci_lower": ci_result.ci_lower,
                    "ci_upper": ci_result.ci_upper,
                    "method": ci_result.method,
                    "confidence": ci_result.confidence
                })

            enhanced_extractions.append(ext)

        # Update extraction counts
        missing_after = sum(1 for e in enhanced_extractions if not e.get("ci_complete"))
        results["missing_ci_after"] += missing_after
        results["cis_recovered"] += recovered

        # Update PDF info
        pdf_info["extractions"] = enhanced_extractions
        pdf_info["ci_complete_count"] = sum(1 for e in enhanced_extractions if e.get("ci_complete"))
        results["enhanced_pdfs"].append(pdf_info)

        if recovered > 0:
            print(f"  {pdf_info['filename']}: Recovered {recovered} CIs")

    return results


def main():
    # v4.3.5: Use curated manifest (non-RCTs removed)
    curated_path = Path("data/curated_rct_manifest.json")
    classification_path = Path("data/pdf_classification.json")
    pdf_dir = Path("test_pdfs/open_access_rcts")
    output_path = Path("output/ci_proximity_results_v435.json")
    enhanced_classification_path = Path("data/pdf_classification_enhanced_v435.json")

    # Prefer curated manifest
    if curated_path.exists():
        classification_path = curated_path
        print("Using curated manifest (non-RCTs excluded)")
    else:
        print("WARNING: No curated manifest found, using raw classification")

    print("Loading classification...")
    classification = load_classification(classification_path)

    print(f"Processing {len(classification['pdfs'])} PDFs...")
    results = apply_proximity_search(classification, pdf_dir)

    # Calculate metrics
    total_extractions = results["total_extractions"]
    missing_before = results["missing_ci_before"]
    missing_after = results["missing_ci_after"]
    recovered = results["cis_recovered"]

    ci_before = (total_extractions - missing_before) / total_extractions * 100
    ci_after = (total_extractions - missing_after) / total_extractions * 100

    print("\n" + "=" * 50)
    print("CI Proximity Search Results")
    print("=" * 50)
    print(f"Total extractions: {total_extractions}")
    print(f"Missing CI before: {missing_before}")
    print(f"Missing CI after: {missing_after}")
    print(f"CIs recovered: {recovered}")
    print(f"\nCI completion before: {ci_before:.1f}%")
    print(f"CI completion after: {ci_after:.1f}%")
    print(f"Improvement: +{ci_after - ci_before:.1f} percentage points")

    # Save results
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    # Save enhanced classification
    enhanced_classification = classification.copy()
    enhanced_classification["pdfs"] = results["enhanced_pdfs"]
    enhanced_classification["enhancement"] = {
        "date": results["date"],
        "method": "ci_proximity_search",
        "cis_recovered": recovered,
        "ci_completion_before": ci_before,
        "ci_completion_after": ci_after
    }

    with open(enhanced_classification_path, "w") as f:
        json.dump(enhanced_classification, f, indent=2)
    print(f"Enhanced classification saved to: {enhanced_classification_path}")


if __name__ == "__main__":
    main()
