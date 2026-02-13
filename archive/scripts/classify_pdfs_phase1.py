#!/usr/bin/env python3
"""
Phase 1: PDF Classification Script

Classifies PDFs into:
- A: Primary RCT Results - Reports primary endpoint with HR/OR/RR/MD
- B: Secondary Analysis - Post-hoc, subgroup analyses
- C: Non-RCT - Methods, reviews, educational studies

Usage:
    python scripts/classify_pdfs_phase1.py --pdf-dir test_pdfs/real_pdfs
    python scripts/classify_pdfs_phase1.py --auto  # Auto-classify based on extraction results
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.enhanced_extractor_v3 import EnhancedExtractor
from src.pdf.pdf_parser import PDFParser


def extract_pdf_info(pdf_path: Path) -> dict:
    """Extract basic info and effects from a PDF."""
    parser = PDFParser()
    extractor = EnhancedExtractor()

    info = {
        "pdf_path": str(pdf_path),
        "filename": pdf_path.name,
        "pmc_id": pdf_path.stem,
        "therapeutic_area": pdf_path.parent.name,
        "parse_success": False,
        "text_length": 0,
        "extractions": [],
        "extraction_count": 0,
        "ci_complete_count": 0,
        "effect_types": [],
        "has_abstract": False,
        "has_results_section": False,
        "title_snippet": "",
        "suggested_class": "C",  # Default to non-RCT
    }

    try:
        pdf_content = parser.parse(str(pdf_path))
        text = "\n".join(page.full_text for page in pdf_content.pages)
        if not text or len(text) < 100:
            return info

        info["parse_success"] = True
        info["text_length"] = len(text)

        # Extract title (usually first 200 chars of first page)
        first_page_text = text[:2000]
        lines = [l.strip() for l in first_page_text.split('\n') if l.strip()]
        if lines:
            info["title_snippet"] = lines[0][:200]

        # Check for common sections
        text_lower = text.lower()
        info["has_abstract"] = "abstract" in text_lower[:5000]
        info["has_results_section"] = "results" in text_lower

        # Check for RCT indicators
        rct_indicators = [
            "randomized" in text_lower or "randomised" in text_lower,
            "placebo" in text_lower,
            "double-blind" in text_lower or "double blind" in text_lower,
            "intention-to-treat" in text_lower or "intention to treat" in text_lower,
            "primary endpoint" in text_lower or "primary outcome" in text_lower,
        ]
        info["rct_indicator_count"] = sum(rct_indicators)

        # Check for non-RCT indicators
        non_rct_indicators = [
            "meta-analysis" in text_lower or "systematic review" in text_lower,
            "pooled analysis" in text_lower,
            "post hoc" in text_lower or "post-hoc" in text_lower,
            "subgroup analysis" in text_lower,
            "secondary analysis" in text_lower,
            "retrospective" in text_lower,
            "observational" in text_lower,
            "guideline" in text_lower,
            "consensus" in text_lower,
            "editorial" in text_lower,
            "commentary" in text_lower,
        ]
        info["non_rct_indicator_count"] = sum(non_rct_indicators)

        # Extract effects
        extractions = extractor.extract(text)
        info["extractions"] = [
            {
                "effect_type": str(e.effect_type.value) if hasattr(e.effect_type, 'value') else str(e.effect_type),
                "value": e.point_estimate,
                "ci_lower": e.ci.lower if e.ci else None,
                "ci_upper": e.ci.upper if e.ci else None,
                "ci_complete": e.has_complete_ci,
                "source_pattern": e.source_text[:100] if e.source_text else None,
            }
            for e in extractions
        ]
        info["extraction_count"] = len(extractions)
        info["ci_complete_count"] = sum(1 for e in extractions if e.has_complete_ci)
        info["effect_types"] = list(set(
            str(e.effect_type.value) if hasattr(e.effect_type, 'value') else str(e.effect_type)
            for e in extractions
        ))

        # Auto-suggest classification
        if info["non_rct_indicator_count"] >= 2:
            if "post hoc" in text_lower or "subgroup" in text_lower or "secondary analysis" in text_lower:
                info["suggested_class"] = "B"  # Secondary analysis
            else:
                info["suggested_class"] = "C"  # Non-RCT
        elif info["rct_indicator_count"] >= 3 and info["extraction_count"] > 0:
            info["suggested_class"] = "A"  # Primary RCT
        elif info["extraction_count"] > 0 and info["rct_indicator_count"] >= 2:
            info["suggested_class"] = "A"  # Likely RCT
        elif info["extraction_count"] > 0:
            info["suggested_class"] = "B"  # Has effects but uncertain
        else:
            info["suggested_class"] = "C"  # No extractions

    except Exception as e:
        info["error"] = str(e)

    return info


def classify_pdfs(pdf_dir: Path, output_path: Path, auto_mode: bool = False) -> dict:
    """Classify all PDFs in a directory."""
    results = {
        "version": "phase1",
        "date": datetime.now().isoformat(),
        "pdf_dir": str(pdf_dir),
        "total_pdfs": 0,
        "by_class": {"A": 0, "B": 0, "C": 0, "unclassified": 0},
        "pdfs": []
    }

    # Find all PDFs
    pdf_files = list(pdf_dir.rglob("*.pdf"))
    results["total_pdfs"] = len(pdf_files)

    print(f"Found {len(pdf_files)} PDFs to classify")
    print("-" * 60)

    for i, pdf_path in enumerate(sorted(pdf_files)):
        print(f"[{i+1}/{len(pdf_files)}] Processing {pdf_path.name}...", end=" ")

        info = extract_pdf_info(pdf_path)

        # In auto mode, use suggested class
        if auto_mode:
            info["classification"] = info["suggested_class"]
            info["classification_method"] = "auto"
        else:
            info["classification"] = None
            info["classification_method"] = "pending"

        results["pdfs"].append(info)

        if info["classification"]:
            results["by_class"][info["classification"]] += 1
        else:
            results["by_class"]["unclassified"] += 1

        status = f"class={info.get('classification', '?')}, extractions={info['extraction_count']}, CI={info['ci_complete_count']}"
        print(status)

    # Save results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print("-" * 60)
    print(f"\nClassification Summary:")
    print(f"  Class A (Primary RCT): {results['by_class']['A']}")
    print(f"  Class B (Secondary): {results['by_class']['B']}")
    print(f"  Class C (Non-RCT): {results['by_class']['C']}")
    print(f"  Unclassified: {results['by_class']['unclassified']}")
    print(f"\nResults saved to: {output_path}")

    return results


def generate_classification_report(classification_path: Path, output_path: Path):
    """Generate a detailed classification report for manual review."""
    with open(classification_path) as f:
        data = json.load(f)

    report_lines = [
        "# PDF Classification Report",
        f"\nGenerated: {datetime.now().isoformat()}",
        f"Total PDFs: {data['total_pdfs']}",
        "",
        "## Classification Summary",
        f"- **Class A (Primary RCT Results)**: {data['by_class']['A']}",
        f"- **Class B (Secondary Analysis)**: {data['by_class']['B']}",
        f"- **Class C (Non-RCT)**: {data['by_class']['C']}",
        f"- **Unclassified**: {data['by_class']['unclassified']}",
        "",
        "## PDFs Requiring Manual Review",
        "",
    ]

    # Group by classification
    for cls in ["A", "B", "C"]:
        pdfs = [p for p in data["pdfs"] if p.get("classification") == cls]
        if pdfs:
            report_lines.append(f"### Class {cls}")
            report_lines.append("")

            for pdf in sorted(pdfs, key=lambda x: x["filename"]):
                report_lines.append(f"#### {pdf['filename']}")
                report_lines.append(f"- **Area**: {pdf.get('therapeutic_area', 'unknown')}")
                report_lines.append(f"- **Extractions**: {pdf['extraction_count']} (CI complete: {pdf['ci_complete_count']})")
                report_lines.append(f"- **Effect types**: {', '.join(pdf.get('effect_types', []))}")
                report_lines.append(f"- **RCT indicators**: {pdf.get('rct_indicator_count', 0)}")
                report_lines.append(f"- **Non-RCT indicators**: {pdf.get('non_rct_indicator_count', 0)}")
                if pdf.get("title_snippet"):
                    report_lines.append(f"- **Title**: {pdf['title_snippet'][:100]}...")
                report_lines.append("")

    # Unclassified section
    unclassified = [p for p in data["pdfs"] if not p.get("classification")]
    if unclassified:
        report_lines.append("### Unclassified (Need Manual Review)")
        for pdf in sorted(unclassified, key=lambda x: x["filename"]):
            report_lines.append(f"- {pdf['filename']}: {pdf['extraction_count']} extractions, suggested={pdf.get('suggested_class', '?')}")

    report = "\n".join(report_lines)

    with open(output_path, "w") as f:
        f.write(report)

    print(f"Report saved to: {output_path}")
    return report


def main():
    parser = argparse.ArgumentParser(description="Classify RCT PDFs for ground truth creation")
    parser.add_argument("--pdf-dir", type=Path, default=Path("test_pdfs/real_pdfs"),
                       help="Directory containing PDFs to classify")
    parser.add_argument("--output", type=Path, default=Path("data/pdf_classification.json"),
                       help="Output classification file")
    parser.add_argument("--auto", action="store_true",
                       help="Auto-classify based on extraction results")
    parser.add_argument("--report", action="store_true",
                       help="Generate markdown report from existing classification")
    parser.add_argument("--report-output", type=Path, default=Path("output/pdf_classification_report.md"),
                       help="Output path for markdown report")

    args = parser.parse_args()

    if args.report:
        if args.output.exists():
            generate_classification_report(args.output, args.report_output)
        else:
            print(f"Classification file not found: {args.output}")
            print("Run without --report first to generate classification")
            return
    else:
        classify_pdfs(args.pdf_dir, args.output, auto_mode=args.auto)
        generate_classification_report(args.output, args.report_output)


if __name__ == "__main__":
    main()
