#!/usr/bin/env python3
"""
RCT Extractor v4.3.6 - Full Validation Pipeline

Runs extraction on curated corpus with:
1. Text preprocessing (Unicode, dehyphenation, column reorder)
2. Enhanced extraction patterns
3. Tightened CI proximity search (v4.3.5)
4. Extraction validators
5. Comparison to ground truth

Usage:
    python scripts/run_full_validation_v435.py
    python scripts/run_full_validation_v435.py --pdf-dir test_pdfs/validated_rcts
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.enhanced_extractor_v3 import EnhancedExtractor, Extraction
from src.core.text_preprocessor import TextPreprocessor, TextLine
from src.pdf.pdf_parser import PDFParser
from scripts.ci_proximity_search import CIProximitySearch, _ci_key


def extract_from_pdf(pdf_path: Path, extractor: EnhancedExtractor,
                     preprocessor: TextPreprocessor,
                     proximity_searcher: CIProximitySearch) -> dict:
    """Extract effects from a single PDF with full pipeline."""
    parser = PDFParser()

    result = {
        "filename": pdf_path.name,
        "pmc_id": pdf_path.stem,
        "parse_success": False,
        "text_length": 0,
        "is_two_column": False,
        "extractions": [],
        "ci_complete_count": 0,
        "ci_recovered_count": 0,
        "total_count": 0,
        "errors": [],
    }

    try:
        # Step 1: Parse PDF
        pdf_content = parser.parse(str(pdf_path))
        raw_text = "\n".join(page.full_text for page in pdf_content.pages)
        result["parse_success"] = True
        result["text_length"] = len(raw_text)

        # Step 2: Preprocess text
        raw_lines = raw_text.split('\n')
        text_lines = [
            TextLine(text=line, page_num=0, line_num=i)
            for i, line in enumerate(raw_lines)
        ]

        if text_lines:
            doc = preprocessor.process(text_lines)
            processed_text = doc.reading_order_text
            result["is_two_column"] = doc.is_two_column
        else:
            processed_text = raw_text

        # Step 3: Extract effects
        extractions = extractor.extract(processed_text)

        # Step 4: Convert to serializable format
        extraction_dicts = []
        for e in extractions:
            d = {
                "effect_type": str(e.effect_type.value) if hasattr(e.effect_type, 'value') else str(e.effect_type),
                "value": e.point_estimate,
                "ci_lower": e.ci.lower if e.ci else None,
                "ci_upper": e.ci.upper if e.ci else None,
                "ci_complete": e.has_complete_ci,
                "confidence": e.calibrated_confidence,
                "source_text": e.source_text[:200] if e.source_text else None,
            }
            extraction_dicts.append(d)

        # Step 5: CI proximity search for missing CIs
        # v4.3.6: Track used CIs to prevent same CI assigned to multiple extractions
        ci_recovered = 0
        used_cis = set()

        # First, register CIs from direct extraction
        for ext_dict in extraction_dicts:
            if ext_dict["ci_complete"] and ext_dict["ci_lower"] is not None:
                used_cis.add(_ci_key(ext_dict["ci_lower"], ext_dict["ci_upper"]))

        for ext_dict in extraction_dicts:
            if ext_dict["ci_complete"]:
                continue

            ci_result = proximity_searcher.search_ci_near_value(
                processed_text,
                ext_dict["value"],
                ext_dict["effect_type"],
                exclude_cis=used_cis
            )

            if ci_result:
                ext_dict["ci_lower"] = ci_result.ci_lower
                ext_dict["ci_upper"] = ci_result.ci_upper
                ext_dict["ci_complete"] = True
                ext_dict["ci_source"] = "proximity_search_v4.3.6"
                ext_dict["ci_confidence"] = ci_result.confidence
                ext_dict["ci_method"] = ci_result.method
                ci_recovered += 1
                # Register as used
                used_cis.add(_ci_key(ci_result.ci_lower, ci_result.ci_upper))

        result["extractions"] = extraction_dicts
        result["total_count"] = len(extraction_dicts)
        result["ci_complete_count"] = sum(1 for e in extraction_dicts if e.get("ci_complete"))
        result["ci_recovered_count"] = ci_recovered

    except Exception as e:
        result["errors"].append(str(e))

    return result


def compare_to_ground_truth(extractions: list, ground_truth_effects: list) -> dict:
    """Compare extractions to ground truth effects."""
    if not ground_truth_effects:
        return {"status": "no_ground_truth"}

    matched = 0
    value_correct = 0
    ci_correct = 0

    for gt in ground_truth_effects:
        gt_value = gt.get("value")
        gt_type = gt.get("effect_type", "").upper()

        # Find matching extraction
        best_match = None
        best_diff = float('inf')

        for ext in extractions:
            ext_type = ext.get("effect_type", "").upper()
            if ext_type == gt_type or (ext_type in ["HR", "OR", "RR"] and gt_type in ["HR", "OR", "RR"]):
                diff = abs(ext["value"] - gt_value)
                if diff < best_diff:
                    best_diff = diff
                    best_match = ext

        if best_match and best_diff < 0.05:  # Allow 0.05 tolerance for rounding
            matched += 1
            if abs(best_match["value"] - gt_value) < 0.02:
                value_correct += 1
            if (best_match.get("ci_complete") and gt.get("ci_lower") is not None):
                ci_diff_lower = abs(best_match.get("ci_lower", 0) - gt["ci_lower"])
                ci_diff_upper = abs(best_match.get("ci_upper", 0) - gt["ci_upper"])
                if ci_diff_lower < 0.05 and ci_diff_upper < 0.05:
                    ci_correct += 1

    return {
        "ground_truth_count": len(ground_truth_effects),
        "matched": matched,
        "value_correct": value_correct,
        "ci_correct": ci_correct,
        "recall": matched / len(ground_truth_effects) if ground_truth_effects else 0,
        "value_accuracy": value_correct / len(ground_truth_effects) if ground_truth_effects else 0,
        "ci_accuracy": ci_correct / len(ground_truth_effects) if ground_truth_effects else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="RCT Extractor v4.3.5 Full Validation")
    parser.add_argument("--pdf-dir", type=Path, nargs="+",
                       default=[Path("test_pdfs/open_access_rcts"), Path("test_pdfs/validated_rcts")],
                       help="Directories containing PDFs")
    parser.add_argument("--ground-truth", type=Path,
                       default=Path("data/ground_truth/external_validation_ground_truth.json"),
                       help="Ground truth file")
    parser.add_argument("--curated-manifest", type=Path,
                       default=Path("data/curated_rct_manifest.json"),
                       help="Curated manifest (to exclude non-RCTs)")
    parser.add_argument("--output", type=Path,
                       default=Path("output/validation_v435.json"),
                       help="Output validation results")

    args = parser.parse_args()

    # Initialize components
    print("Initializing extraction pipeline...")
    extractor = EnhancedExtractor()
    preprocessor = TextPreprocessor()
    proximity_searcher = CIProximitySearch()  # v4.3.5 defaults

    # Load ground truth
    ground_truth = {}
    if args.ground_truth.exists():
        with open(args.ground_truth) as f:
            gt_data = json.load(f)
        for trial in gt_data.get("trials", []):
            pmc_id = trial.get("pmc_id", "")
            if pmc_id:
                ground_truth[pmc_id] = trial
        print(f"Loaded ground truth for {len(ground_truth)} trials")

    # Load exclusion list
    excluded_pdfs = set()
    if args.curated_manifest.exists():
        with open(args.curated_manifest) as f:
            manifest = json.load(f)
        excluded_pdfs = set(manifest.get("excluded_pdfs", []))
        print(f"Excluding {len(excluded_pdfs)} non-RCT PDFs")

    # Collect PDFs
    pdf_files = []
    for pdf_dir in args.pdf_dir:
        if pdf_dir.exists():
            for pdf_path in sorted(pdf_dir.glob("PMC*.pdf")):
                if pdf_path.name not in excluded_pdfs:
                    pdf_files.append(pdf_path)

    # Deduplicate by PMC ID
    seen_pmc = set()
    unique_pdfs = []
    for pdf_path in pdf_files:
        pmc_id = pdf_path.stem
        if pmc_id not in seen_pmc:
            seen_pmc.add(pmc_id)
            unique_pdfs.append(pdf_path)

    print(f"\nProcessing {len(unique_pdfs)} unique PDFs...")

    # Process each PDF
    all_results = []
    total_extractions = 0
    total_ci_complete = 0
    total_ci_recovered = 0
    pdfs_with_extractions = 0
    gt_comparisons = []

    for i, pdf_path in enumerate(unique_pdfs):
        print(f"[{i+1}/{len(unique_pdfs)}] {pdf_path.name}...", end=" ")

        result = extract_from_pdf(pdf_path, extractor, preprocessor, proximity_searcher)

        if result["extractions"]:
            pdfs_with_extractions += 1
            print(f"{result['total_count']} effects, {result['ci_complete_count']} CI, "
                  f"{result['ci_recovered_count']} recovered")
        else:
            if result["errors"]:
                print(f"ERROR: {result['errors'][0][:80]}")
            else:
                print("no extractions")

        total_extractions += result["total_count"]
        total_ci_complete += result["ci_complete_count"]
        total_ci_recovered += result["ci_recovered_count"]

        # Compare to ground truth if available
        pmc_id = result["pmc_id"]
        if pmc_id in ground_truth:
            gt_effects = ground_truth[pmc_id].get("effects", [])
            comparison = compare_to_ground_truth(result["extractions"], gt_effects)
            comparison["pmc_id"] = pmc_id
            comparison["trial_name"] = ground_truth[pmc_id].get("trial_name", "")
            gt_comparisons.append(comparison)
            result["ground_truth_comparison"] = comparison

        all_results.append(result)

    # Calculate overall metrics
    ci_completion = total_ci_complete / total_extractions * 100 if total_extractions > 0 else 0
    extraction_rate = pdfs_with_extractions / len(unique_pdfs) * 100 if unique_pdfs else 0

    # Ground truth aggregate
    gt_recall = 0
    gt_value_acc = 0
    gt_ci_acc = 0
    if gt_comparisons:
        gt_recall = sum(c["recall"] for c in gt_comparisons) / len(gt_comparisons)
        gt_value_acc = sum(c["value_accuracy"] for c in gt_comparisons) / len(gt_comparisons)
        gt_ci_acc = sum(c["ci_accuracy"] for c in gt_comparisons) / len(gt_comparisons)

    # Print summary
    print("\n" + "=" * 60)
    print("RCT Extractor v4.3.6 - Validation Results")
    print("=" * 60)
    print(f"Total PDFs: {len(unique_pdfs)}")
    print(f"PDFs with extractions: {pdfs_with_extractions} ({extraction_rate:.1f}%)")
    print(f"Total extractions: {total_extractions}")
    print(f"CI complete (direct): {total_ci_complete - total_ci_recovered}")
    print(f"CI recovered (proximity): {total_ci_recovered}")
    print(f"CI complete (total): {total_ci_complete} ({ci_completion:.1f}%)")
    print(f"CI missing: {total_extractions - total_ci_complete}")

    if gt_comparisons:
        print(f"\nGround Truth Comparison ({len(gt_comparisons)} trials):")
        print(f"  Recall: {gt_recall:.1%}")
        print(f"  Value accuracy: {gt_value_acc:.1%}")
        print(f"  CI accuracy: {gt_ci_acc:.1%}")
    print("=" * 60)

    # Save results
    output = {
        "version": "v4.3.6",
        "date": datetime.now().isoformat(),
        "pipeline": {
            "text_preprocessor": True,
            "proximity_search_window": 150,
            "ci_label_required": True,
            "negative_validation": True,
        },
        "corpus": {
            "total_pdfs": len(unique_pdfs),
            "pdfs_with_extractions": pdfs_with_extractions,
            "excluded_non_rct": len(excluded_pdfs),
            "pdf_dirs": [str(d) for d in args.pdf_dir],
        },
        "metrics": {
            "extraction_rate": extraction_rate / 100,
            "total_extractions": total_extractions,
            "ci_complete_direct": total_ci_complete - total_ci_recovered,
            "ci_recovered_proximity": total_ci_recovered,
            "ci_complete_total": total_ci_complete,
            "ci_completion_rate": ci_completion / 100,
            "ci_missing": total_extractions - total_ci_complete,
        },
        "ground_truth": {
            "trials_compared": len(gt_comparisons),
            "avg_recall": gt_recall,
            "avg_value_accuracy": gt_value_acc,
            "avg_ci_accuracy": gt_ci_acc,
            "per_trial": gt_comparisons,
        },
        "pdfs": all_results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
