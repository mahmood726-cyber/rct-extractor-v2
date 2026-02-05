#!/usr/bin/env python3
"""
Filter PDF corpus to RCT results papers only and run validation.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

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
    except Exception:
        try:
            import fitz
            doc = fitz.open(pdf_path)
            text_parts = []
            for i in range(min(max_pages, len(doc))):
                text_parts.append(doc[i].get_text())
            doc.close()
            return "\n".join(text_parts)
        except Exception as e:
            print(f"  Error: {e}")
            return ""


def main():
    # Load classifications
    with open('output/pdf_classifications.json') as f:
        data = json.load(f)

    # Filter to RCT results only (has results)
    rct_results = [c for c in data['classifications']
                   if c.get('study_type') == 'rct_results'
                   or (c.get('study_type') == 'rct_secondary' and c.get('has_results'))]

    print(f"Found {len(rct_results)} RCT results PDFs:")
    print("=" * 60)
    for r in rct_results:
        print(f"  {r['pdf']:35} | {r['category']:12} | conf: {r['confidence']:.2f}")

    # Run extraction on filtered PDFs
    print("\n" + "=" * 60)
    print("RUNNING EXTRACTION ON RCT RESULTS ONLY")
    print("=" * 60)

    extractor = EnhancedExtractor()
    pdf_base = "test_pdfs/real_pdfs"

    results = {
        "validation_date": datetime.now().isoformat(),
        "corpus": "RCT results only",
        "total_pdfs": len(rct_results),
        "summary": {
            "pdfs_processed": 0,
            "pdfs_with_effects": 0,
            "total_effects": 0,
            "with_complete_ci": 0,
            "full_auto": 0,
            "spot_check": 0,
            "verify": 0,
            "manual": 0,
        },
        "by_type": {},
        "by_category": {},
        "details": []
    }

    for i, rct in enumerate(rct_results):
        pdf_name = rct['pdf']
        category = rct['category']

        # Find PDF
        pdf_path = None
        for root, dirs, files in os.walk(pdf_base):
            if pdf_name in files:
                pdf_path = os.path.join(root, pdf_name)
                break

        if not pdf_path:
            print(f"[{i+1}/{len(rct_results)}] {pdf_name} - NOT FOUND")
            continue

        print(f"[{i+1}/{len(rct_results)}] {pdf_name}...", end=" ")

        # Extract text
        text = extract_text_from_pdf(pdf_path)
        if not text:
            print("NO TEXT")
            continue

        # Run extraction
        extractions = extractor.extract(text)
        results["summary"]["pdfs_processed"] += 1

        if extractions:
            results["summary"]["pdfs_with_effects"] += 1

        # Count effects
        for e in extractions:
            results["summary"]["total_effects"] += 1

            if e.has_complete_ci:
                results["summary"]["with_complete_ci"] += 1

            tier = e.automation_tier.value
            if tier == "full_auto":
                results["summary"]["full_auto"] += 1
            elif tier == "spot_check":
                results["summary"]["spot_check"] += 1
            elif tier == "verify":
                results["summary"]["verify"] += 1
            else:
                results["summary"]["manual"] += 1

            # By type
            etype = e.effect_type.value
            if etype not in results["by_type"]:
                results["by_type"][etype] = {"count": 0, "with_ci": 0, "full_auto": 0}
            results["by_type"][etype]["count"] += 1
            if e.has_complete_ci:
                results["by_type"][etype]["with_ci"] += 1
            if tier == "full_auto":
                results["by_type"][etype]["full_auto"] += 1

        # By category
        if category not in results["by_category"]:
            results["by_category"][category] = {"pdfs": 0, "effects": 0, "with_ci": 0}
        results["by_category"][category]["pdfs"] += 1
        results["by_category"][category]["effects"] += len(extractions)
        results["by_category"][category]["with_ci"] += sum(1 for e in extractions if e.has_complete_ci)

        # Store detail
        results["details"].append({
            "pdf": pdf_name,
            "category": category,
            "effects": len(extractions),
            "with_ci": sum(1 for e in extractions if e.has_complete_ci),
            "types": [e.effect_type.value for e in extractions]
        })

        print(f"{len(extractions)} effects, {sum(1 for e in extractions if e.has_complete_ci)} with CI")

    # Calculate rates
    total = results["summary"]["total_effects"]
    if total > 0:
        results["summary"]["ci_rate"] = round(results["summary"]["with_complete_ci"] / total * 100, 1)
        results["summary"]["full_auto_rate"] = round(results["summary"]["full_auto"] / total * 100, 1)
    else:
        results["summary"]["ci_rate"] = 0
        results["summary"]["full_auto_rate"] = 0

    pdfs = results["summary"]["pdfs_processed"]
    if pdfs > 0:
        results["summary"]["pdfs_with_effects_rate"] = round(results["summary"]["pdfs_with_effects"] / pdfs * 100, 1)
        results["summary"]["effects_per_pdf"] = round(total / pdfs, 1)
    else:
        results["summary"]["pdfs_with_effects_rate"] = 0
        results["summary"]["effects_per_pdf"] = 0

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY (RCT RESULTS ONLY)")
    print("=" * 60)
    print(f"PDFs processed:     {results['summary']['pdfs_processed']}")
    print(f"PDFs with effects:  {results['summary']['pdfs_with_effects']} ({results['summary']['pdfs_with_effects_rate']}%)")
    print(f"Total effects:      {results['summary']['total_effects']}")
    print(f"Effects per PDF:    {results['summary']['effects_per_pdf']}")
    print(f"With complete CI:   {results['summary']['with_complete_ci']} ({results['summary']['ci_rate']}%)")
    print(f"Full-auto tier:     {results['summary']['full_auto']} ({results['summary']['full_auto_rate']}%)")

    print("\nBy Effect Type:")
    for etype, stats in sorted(results["by_type"].items(), key=lambda x: x[1]["count"], reverse=True):
        ci_rate = round(stats["with_ci"] / stats["count"] * 100, 1) if stats["count"] > 0 else 0
        print(f"  {etype:6}: {stats['count']:3} effects, {ci_rate:5.1f}% with CI")

    print("\nBy Category:")
    for cat, stats in sorted(results["by_category"].items()):
        ci_rate = round(stats["with_ci"] / stats["effects"] * 100, 1) if stats["effects"] > 0 else 0
        eff_per_pdf = round(stats["effects"] / stats["pdfs"], 1) if stats["pdfs"] > 0 else 0
        print(f"  {cat:12}: {stats['pdfs']} PDFs, {stats['effects']:3} effects ({eff_per_pdf}/PDF), {ci_rate:.1f}% CI")

    # Save results
    with open('output/rct_results_validation.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: output/rct_results_validation.json")


if __name__ == "__main__":
    main()
