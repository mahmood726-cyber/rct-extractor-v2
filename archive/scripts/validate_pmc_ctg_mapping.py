#!/usr/bin/env python3
"""
PMC-CTG Mapping Validation Script - Phase 4 of IMPROVEMENT_PLAN_V8

Validates PDF extractions against ClinicalTrials.gov ground truth
for PDFs that have known NCT IDs.

Usage:
    python scripts/validate_pmc_ctg_mapping.py --mapping output/nct_pmc_mapping.json
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.ctg_scraper import CTGScraper
from src.core.enhanced_extractor_v3 import EnhancedExtractor


def extract_text_from_pdf(pdf_path: str, max_pages: int = 50) -> str:
    """Extract text from PDF."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages]):
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        try:
            import fitz
            doc = fitz.open(pdf_path)
            text_parts = []
            for i in range(min(max_pages, len(doc))):
                text_parts.append(doc[i].get_text())
            doc.close()
            return "\n".join(text_parts)
        except Exception as e2:
            print(f"  Error extracting: {e2}")
            return ""


def compare_values(extracted_val, ctg_val, tolerance_pct=10):
    """Compare two numeric values with tolerance."""
    if extracted_val is None or ctg_val is None:
        return False, None

    try:
        ext_float = float(str(extracted_val).replace(',', '.'))
        ctg_float = float(str(ctg_val).replace(',', '.'))

        if ctg_float == 0:
            return ext_float == 0, 0 if ext_float == 0 else 100

        pct_diff = abs(ext_float - ctg_float) / abs(ctg_float) * 100
        return pct_diff <= tolerance_pct, pct_diff
    except (ValueError, TypeError):
        return False, None


def validate_mapping(mapping_path: str, pdf_base_dir: str = "test_pdfs/real_pdfs",
                    output_path: str = None, verbose: bool = True):
    """
    Validate PDF extractions against CTG ground truth.

    Args:
        mapping_path: Path to nct_pmc_mapping.json
        pdf_base_dir: Base directory for PDFs
        output_path: Path for JSON output
        verbose: Print progress

    Returns:
        Validation results dict
    """
    # Load mapping
    with open(mapping_path) as f:
        mapping_data = json.load(f)

    # Filter to single-trial PDFs only
    single_trials = [m for m in mapping_data["mapping"] if m.get("is_single_trial", False)]

    if verbose:
        print(f"Found {len(single_trials)} single-trial PDFs with NCT IDs")
        print("=" * 60)

    results = {
        "validation_date": datetime.now().isoformat(),
        "total_trials": len(single_trials),
        "trials_validated": 0,
        "ctg_effects_found": 0,
        "pdf_effects_found": 0,
        "matches": 0,
        "match_rate": 0.0,
        "validations": []
    }

    extractor = EnhancedExtractor()
    scraper = CTGScraper()

    for i, trial in enumerate(single_trials):
        pdf_name = trial["pdf"]
        nct_id = trial["nct_ids"][0]
        category = trial["category"]

        if verbose:
            print(f"[{i+1}/{len(single_trials)}] {pdf_name} -> {nct_id}")

        # Find PDF path
        pdf_path = None
        for root, dirs, files in os.walk(pdf_base_dir):
            if pdf_name in files:
                pdf_path = os.path.join(root, pdf_name)
                break

        if not pdf_path:
            if verbose:
                print(f"  PDF not found in {pdf_base_dir}")
            continue

        validation = {
            "pdf": pdf_name,
            "nct_id": nct_id,
            "category": category,
            "ctg_effects": [],
            "pdf_effects": [],
            "matches": [],
            "match_count": 0
        }

        # Fetch CTG data
        try:
            ctg_study = scraper.fetch_study(nct_id)
            if ctg_study and ctg_study.effect_estimates:
                validation["ctg_effects"] = [
                    {
                        "type": e.effect_type,
                        "value": e.value,
                        "ci_lower": e.ci_lower,
                        "ci_upper": e.ci_upper,
                        "outcome": e.outcome_title
                    }
                    for e in ctg_study.effect_estimates
                ]
                results["ctg_effects_found"] += len(ctg_study.effect_estimates)
        except Exception as e:
            if verbose:
                print(f"  CTG fetch error: {e}")
            time.sleep(0.5)

        # Extract from PDF
        text = extract_text_from_pdf(pdf_path)
        if text:
            extractions = extractor.extract(text)
            validation["pdf_effects"] = [
                {
                    "type": e.effect_type.value,
                    "value": e.point_estimate,
                    "ci_lower": e.ci.lower if e.ci else None,
                    "ci_upper": e.ci.upper if e.ci else None,
                    "confidence": e.calibrated_confidence,
                    "source": e.source_text[:100] if e.source_text else ""
                }
                for e in extractions
            ]
            results["pdf_effects_found"] += len(extractions)

        # Match CTG effects to PDF extractions
        for ctg_eff in validation["ctg_effects"]:
            best_match = None
            best_diff = float('inf')

            for pdf_eff in validation["pdf_effects"]:
                # Type must match or be compatible
                type_match = (ctg_eff["type"] == pdf_eff["type"] or
                             (ctg_eff["type"] in ["RR", "HR"] and pdf_eff["type"] in ["RR", "HR"]))

                if not type_match:
                    continue

                # Value comparison
                matched, pct_diff = compare_values(pdf_eff["value"], ctg_eff["value"])
                if pct_diff is not None and pct_diff < best_diff:
                    best_diff = pct_diff
                    best_match = {
                        "ctg_type": ctg_eff["type"],
                        "ctg_value": ctg_eff["value"],
                        "pdf_type": pdf_eff["type"],
                        "pdf_value": pdf_eff["value"],
                        "value_diff_pct": round(pct_diff, 2),
                        "matched": matched,
                        "ci_matches": (
                            compare_values(pdf_eff["ci_lower"], ctg_eff["ci_lower"])[0] and
                            compare_values(pdf_eff["ci_upper"], ctg_eff["ci_upper"])[0]
                        ) if ctg_eff["ci_lower"] and pdf_eff["ci_lower"] else None
                    }

            if best_match:
                validation["matches"].append(best_match)
                if best_match["matched"]:
                    validation["match_count"] += 1
                    results["matches"] += 1

        results["validations"].append(validation)
        results["trials_validated"] += 1

        if verbose:
            print(f"  CTG: {len(validation['ctg_effects'])} effects, "
                  f"PDF: {len(validation['pdf_effects'])} effects, "
                  f"Matches: {validation['match_count']}")

        # Rate limit
        time.sleep(0.3)

    # Calculate summary metrics
    if results["ctg_effects_found"] > 0:
        results["match_rate"] = round(results["matches"] / results["ctg_effects_found"] * 100, 1)

    if verbose:
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Trials validated: {results['trials_validated']}/{results['total_trials']}")
        print(f"CTG effects found: {results['ctg_effects_found']}")
        print(f"PDF effects found: {results['pdf_effects_found']}")
        print(f"Matches: {results['matches']}")
        print(f"Match rate: {results['match_rate']}%")

    # Save output
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        if verbose:
            print(f"\nResults saved to: {output_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Validate PDFs against CTG ground truth")
    parser.add_argument("--mapping", "-m", default="output/nct_pmc_mapping.json",
                       help="Path to NCT-PMC mapping JSON")
    parser.add_argument("--pdf-dir", "-p", default="test_pdfs/real_pdfs",
                       help="Base directory for PDFs")
    parser.add_argument("--output", "-o", default="output/ctg_validation_results.json",
                       help="Output JSON path")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Suppress output")

    args = parser.parse_args()

    if not os.path.exists(args.mapping):
        print(f"Error: {args.mapping} not found")
        sys.exit(1)

    validate_mapping(args.mapping, args.pdf_dir, args.output, verbose=not args.quiet)


if __name__ == "__main__":
    main()
