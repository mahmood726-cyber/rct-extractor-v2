#!/usr/bin/env python3
"""
PDF Corpus Classification Script - Phase 1 of IMPROVEMENT_PLAN_V8

Classifies all PDFs in the corpus as RCT results vs other study types
(protocols, letters, reviews, observational studies).

Usage:
    python scripts/classify_pdf_corpus.py test_pdfs/real_pdfs/ --output output/pdf_classifications.json
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.rct_classifier import RCTClassifier, StudyType, classify_pdf_text


def extract_text_from_pdf(pdf_path: str, max_pages: int = 10) -> str:
    """Extract text from PDF for classification."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages]):
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        # Try PyMuPDF as fallback
        try:
            import fitz
            doc = fitz.open(pdf_path)
            text_parts = []
            for i in range(min(max_pages, len(doc))):
                text_parts.append(doc[i].get_text())
            doc.close()
            return "\n".join(text_parts)
        except Exception as e2:
            print(f"  Error extracting text from {pdf_path}: {e2}")
            return ""


def extract_title_from_pdf(pdf_path: str) -> str:
    """Extract title from first page of PDF."""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.pages:
                text = pdf.pages[0].extract_text() or ""
                # Title is usually the first substantial line
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                for line in lines[:5]:  # Check first 5 lines
                    # Skip short lines and page numbers
                    if len(line) > 20 and not line.isdigit():
                        return line
        return ""
    except Exception:
        return ""


def classify_corpus(pdf_dir: str, output_path: str = None, verbose: bool = True):
    """
    Classify all PDFs in a directory.

    Args:
        pdf_dir: Directory containing PDFs
        output_path: Path for JSON output
        verbose: Print progress

    Returns:
        dict with classification results
    """
    classifier = RCTClassifier()
    results = {
        "classification_date": datetime.now().isoformat(),
        "source_directory": str(pdf_dir),
        "summary": {
            "total_pdfs": 0,
            "rct_results": 0,
            "rct_secondary": 0,
            "protocols": 0,
            "meta_analyses": 0,
            "observational": 0,
            "letters": 0,
            "reviews": 0,
            "other": 0,
            "recommended_include": 0,
            "recommended_exclude": 0,
            "recommended_review": 0,
        },
        "by_category": {},
        "classifications": []
    }

    # Find all PDFs
    pdf_dir = Path(pdf_dir)
    pdf_files = []

    # Handle both flat and nested directory structures
    for pattern in ['*.pdf', '*/*.pdf', '*/*/*.pdf']:
        pdf_files.extend(pdf_dir.glob(pattern))

    pdf_files = sorted(set(pdf_files))
    results["summary"]["total_pdfs"] = len(pdf_files)

    if verbose:
        print(f"Found {len(pdf_files)} PDFs in {pdf_dir}")
        print("=" * 60)

    for i, pdf_path in enumerate(pdf_files):
        if verbose:
            print(f"[{i+1}/{len(pdf_files)}] Classifying {pdf_path.name}...")

        # Extract text
        text = extract_text_from_pdf(str(pdf_path))
        title = extract_title_from_pdf(str(pdf_path))

        if not text:
            classification = {
                "pdf": pdf_path.name,
                "path": str(pdf_path.relative_to(pdf_dir)),
                "study_type": "other",
                "is_rct": False,
                "has_results": False,
                "confidence": 0.0,
                "recommendation": "review",
                "signals_found": [],
                "signals_against": [],
                "error": "Could not extract text"
            }
        else:
            # Classify
            result = classifier.classify(text, title)

            classification = {
                "pdf": pdf_path.name,
                "path": str(pdf_path.relative_to(pdf_dir)),
                "title": title[:200] if title else "",
                "study_type": result.study_type.value,
                "is_rct": result.is_rct,
                "has_results": result.has_results,
                "confidence": round(result.confidence, 3),
                "recommendation": result.recommendation,
                "signals_found": result.signals_found,
                "signals_against": result.signals_against,
            }

            # Update summary counts
            type_key = result.study_type.value
            if type_key in ["rct_results", "rct_secondary", "protocol", "meta_analysis",
                           "observational", "letter", "review", "other"]:
                # Map to summary keys
                key_map = {
                    "rct_results": "rct_results",
                    "rct_secondary": "rct_secondary",
                    "protocol": "protocols",
                    "meta_analysis": "meta_analyses",
                    "observational": "observational",
                    "letter": "letters",
                    "review": "reviews",
                    "other": "other"
                }
                results["summary"][key_map.get(type_key, "other")] += 1

            # Update recommendation counts
            if result.recommendation == "include":
                results["summary"]["recommended_include"] += 1
            elif result.recommendation == "exclude":
                results["summary"]["recommended_exclude"] += 1
            else:
                results["summary"]["recommended_review"] += 1

        # Determine category from path
        category = "unknown"
        path_parts = pdf_path.relative_to(pdf_dir).parts
        if len(path_parts) > 1:
            category = path_parts[0]
        classification["category"] = category

        # Update category breakdown
        if category not in results["by_category"]:
            results["by_category"][category] = {
                "total": 0,
                "rct_results": 0,
                "include": 0,
                "exclude": 0,
                "review": 0
            }
        results["by_category"][category]["total"] += 1
        if classification.get("study_type") == "rct_results":
            results["by_category"][category]["rct_results"] += 1
        if classification.get("recommendation") == "include":
            results["by_category"][category]["include"] += 1
        elif classification.get("recommendation") == "exclude":
            results["by_category"][category]["exclude"] += 1
        else:
            results["by_category"][category]["review"] += 1

        results["classifications"].append(classification)

        if verbose:
            symbols = {"include": "[+]", "exclude": "[-]", "review": "[?]"}
            rec = classification.get("recommendation", "review")
            print(f"  {symbols.get(rec, '[?]')} {classification.get('study_type', 'unknown')} "
                  f"(conf: {classification.get('confidence', 0):.2f}) -> {rec}")

    # Print summary
    if verbose:
        print("\n" + "=" * 60)
        print("CLASSIFICATION SUMMARY")
        print("=" * 60)
        print(f"Total PDFs: {results['summary']['total_pdfs']}")
        print(f"\nBy Study Type:")
        print(f"  RCT Results:    {results['summary']['rct_results']}")
        print(f"  RCT Secondary:  {results['summary']['rct_secondary']}")
        print(f"  Protocols:      {results['summary']['protocols']}")
        print(f"  Meta-analyses:  {results['summary']['meta_analyses']}")
        print(f"  Observational:  {results['summary']['observational']}")
        print(f"  Letters:        {results['summary']['letters']}")
        print(f"  Reviews:        {results['summary']['reviews']}")
        print(f"  Other:          {results['summary']['other']}")
        print(f"\nRecommendations:")
        print(f"  Include: {results['summary']['recommended_include']}")
        print(f"  Exclude: {results['summary']['recommended_exclude']}")
        print(f"  Review:  {results['summary']['recommended_review']}")
        print(f"\nBy Category:")
        for cat, stats in sorted(results["by_category"].items()):
            rct_pct = (stats['rct_results'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {cat}: {stats['total']} PDFs, {stats['rct_results']} RCTs ({rct_pct:.0f}%)")

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
    parser = argparse.ArgumentParser(description="Classify PDF corpus by study type")
    parser.add_argument("pdf_dir", help="Directory containing PDFs")
    parser.add_argument("--output", "-o", default="output/pdf_classifications.json",
                       help="Output JSON path")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Suppress verbose output")

    args = parser.parse_args()

    if not os.path.isdir(args.pdf_dir):
        print(f"Error: {args.pdf_dir} is not a directory")
        sys.exit(1)

    classify_corpus(args.pdf_dir, args.output, verbose=not args.quiet)


if __name__ == "__main__":
    main()
