#!/usr/bin/env python3
"""
Phase 1: Ground Truth Creation Script

For each Class A PDF, creates ground truth annotations:
- Primary endpoint effect (type, value, CI)
- Page number and exact source text
- Metadata flags (in_table, in_figure, multi_column)

Usage:
    python scripts/create_ground_truth_phase1.py --classification data/pdf_classification.json
    python scripts/create_ground_truth_phase1.py --merge-external  # Merge with external_validation_ground_truth
"""

import argparse
import json
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.enhanced_extractor_v3 import EnhancedExtractor
from src.pdf.pdf_parser import PDFParser


def extract_context_around_value(text: str, value: float, window: int = 200) -> List[str]:
    """Find all occurrences of a value in text and return context."""
    contexts = []
    value_str = str(value)

    # Try different formats of the value
    formats_to_try = [
        value_str,
        f"{value:.2f}",
        f"{value:.1f}",
        value_str.replace(".", r"\."),
    ]

    for fmt in formats_to_try:
        pattern = re.compile(re.escape(fmt) if '\\' not in fmt else fmt)
        for match in pattern.finditer(text):
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            context = text[start:end]
            if context not in contexts:
                contexts.append(context)

    return contexts[:5]  # Return max 5 contexts


def create_ground_truth_entry(pdf_info: dict, extraction: dict, source_text: str = None) -> dict:
    """Create a ground truth entry from PDF info and extraction."""
    return {
        "pdf": pdf_info["filename"],
        "pmc_id": pdf_info.get("pmc_id"),
        "therapeutic_area": pdf_info.get("therapeutic_area"),
        "effect_type": extraction.get("effect_type"),
        "value": extraction.get("value"),
        "ci_lower": extraction.get("ci_lower"),
        "ci_upper": extraction.get("ci_upper"),
        "ci_complete": extraction.get("ci_complete", False),
        "source_text": source_text,
        "source_pattern": extraction.get("source_pattern"),
        "is_primary_endpoint": True,  # Default for Class A
        "location": {
            "in_table": False,
            "in_figure_caption": False,
            "multi_column": False,
            "page_number": None,
        },
        "verified": False,
        "notes": "",
    }


def auto_generate_ground_truth(classification_path: Path, output_path: Path) -> dict:
    """
    Auto-generate ground truth from Class A PDFs using existing extractions.
    This creates a starting point for manual verification.
    """
    with open(classification_path) as f:
        classification = json.load(f)

    ground_truth = {
        "version": "phase1-auto",
        "date": datetime.now().isoformat(),
        "description": "Auto-generated ground truth from Class A PDFs - requires manual verification",
        "source": "classify_pdfs_phase1.py extractions",
        "stats": {
            "total_pdfs": 0,
            "total_effects": 0,
            "ci_complete": 0,
            "verified": 0,
        },
        "entries": []
    }

    # Get Class A PDFs
    class_a_pdfs = [p for p in classification["pdfs"] if p.get("classification") == "A"]
    ground_truth["stats"]["total_pdfs"] = len(class_a_pdfs)

    print(f"Processing {len(class_a_pdfs)} Class A PDFs...")

    for pdf_info in class_a_pdfs:
        extractions = pdf_info.get("extractions", [])

        if not extractions:
            continue

        # For each PDF, take the first extraction with CI as likely primary endpoint
        # (This is a heuristic - manual verification needed)
        ci_complete_extractions = [e for e in extractions if e.get("ci_complete")]

        if ci_complete_extractions:
            # Prioritize HR > OR > RR > MD for primary endpoints
            priority_order = ["HR", "OR", "RR", "MD", "RRR", "SMD", "IRR", "ARD"]
            sorted_extractions = sorted(
                ci_complete_extractions,
                key=lambda e: priority_order.index(e["effect_type"]) if e["effect_type"] in priority_order else 99
            )
            primary = sorted_extractions[0]
        elif extractions:
            primary = extractions[0]
        else:
            continue

        entry = create_ground_truth_entry(pdf_info, primary, primary.get("source_pattern"))
        ground_truth["entries"].append(entry)
        ground_truth["stats"]["total_effects"] += 1

        if entry["ci_complete"]:
            ground_truth["stats"]["ci_complete"] += 1

    # Save ground truth
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"\nGround truth summary:")
    print(f"  Total PDFs: {ground_truth['stats']['total_pdfs']}")
    print(f"  Total effects: {ground_truth['stats']['total_effects']}")
    print(f"  CI complete: {ground_truth['stats']['ci_complete']}")
    print(f"  Verified: {ground_truth['stats']['verified']}")
    print(f"\nSaved to: {output_path}")

    return ground_truth


def merge_with_external_validation(ground_truth_path: Path, external_path: Path, output_path: Path) -> dict:
    """
    Merge auto-generated ground truth with external validation dataset.
    External validation is considered already verified.
    """
    with open(ground_truth_path) as f:
        ground_truth = json.load(f)

    with open(external_path) as f:
        external = json.load(f)

    # Create lookup by PMC ID
    existing_pmc_ids = {e.get("pmc_id") for e in ground_truth["entries"] if e.get("pmc_id")}

    # Add external validation entries
    added = 0
    for trial in external.get("trials", []):
        pmc_id = trial.get("pmc_id")

        if not pmc_id:
            continue

        # Skip if already in ground truth
        if pmc_id in existing_pmc_ids:
            continue

        for effect in trial.get("effects", []):
            entry = {
                "pdf": f"{pmc_id}.pdf",
                "pmc_id": pmc_id,
                "trial_name": trial.get("trial_name"),
                "therapeutic_area": trial.get("therapeutic_area"),
                "effect_type": effect.get("effect_type"),
                "value": effect.get("value"),
                "ci_lower": effect.get("ci_lower"),
                "ci_upper": effect.get("ci_upper"),
                "ci_complete": effect.get("ci_lower") is not None and effect.get("ci_upper") is not None,
                "source_text": effect.get("source_text"),
                "outcome": effect.get("outcome"),
                "comparison": effect.get("comparison"),
                "is_primary_endpoint": effect.get("outcome", "").lower().find("primary") >= 0 or True,
                "location": {
                    "in_table": False,
                    "in_figure_caption": False,
                    "multi_column": False,
                    "page_number": None,
                },
                "verified": True,  # External validation is pre-verified
                "verification_source": "external_validation_dataset",
                "notes": f"From {trial.get('journal', 'unknown')} {trial.get('year', 'unknown')}",
            }
            ground_truth["entries"].append(entry)
            added += 1

    # Update stats
    ground_truth["stats"]["total_effects"] = len(ground_truth["entries"])
    ground_truth["stats"]["ci_complete"] = sum(1 for e in ground_truth["entries"] if e.get("ci_complete"))
    ground_truth["stats"]["verified"] = sum(1 for e in ground_truth["entries"] if e.get("verified"))
    ground_truth["description"] = "Merged ground truth: auto-generated + external validation"
    ground_truth["merged_date"] = datetime.now().isoformat()

    # Save merged
    with open(output_path, "w") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"Added {added} entries from external validation")
    print(f"Total entries: {ground_truth['stats']['total_effects']}")
    print(f"Verified: {ground_truth['stats']['verified']}")
    print(f"Saved to: {output_path}")

    return ground_truth


def generate_verification_checklist(ground_truth_path: Path, output_path: Path):
    """Generate a markdown checklist for manual verification."""
    with open(ground_truth_path) as f:
        ground_truth = json.load(f)

    lines = [
        "# Ground Truth Verification Checklist",
        f"\nGenerated: {datetime.now().isoformat()}",
        f"Total entries: {len(ground_truth['entries'])}",
        "",
        "## Instructions",
        "For each entry, verify:",
        "1. Effect type is correct (HR/OR/RR/MD/etc)",
        "2. Value matches source text",
        "3. CI bounds are correct",
        "4. This is the PRIMARY endpoint (not secondary)",
        "",
        "Mark as verified by changing `[ ]` to `[x]`",
        "",
        "---",
        "",
    ]

    # Group by therapeutic area
    by_area = {}
    for entry in ground_truth["entries"]:
        area = entry.get("therapeutic_area", "unknown")
        if area not in by_area:
            by_area[area] = []
        by_area[area].append(entry)

    for area, entries in sorted(by_area.items()):
        lines.append(f"## {area.title()}")
        lines.append("")

        for entry in entries:
            verified = "[x]" if entry.get("verified") else "[ ]"
            ci_str = f"({entry.get('ci_lower')}, {entry.get('ci_upper')})" if entry.get("ci_complete") else "(no CI)"

            lines.append(f"- {verified} **{entry['pdf']}**")
            lines.append(f"  - {entry.get('effect_type')} = {entry.get('value')} {ci_str}")
            if entry.get("trial_name"):
                lines.append(f"  - Trial: {entry.get('trial_name')}")
            if entry.get("source_text"):
                source = entry.get("source_text", "")[:100].replace("\n", " ")
                lines.append(f"  - Source: \"{source}...\"")
            lines.append("")

    report = "\n".join(lines)

    with open(output_path, "w") as f:
        f.write(report)

    print(f"Verification checklist saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Create ground truth annotations for RCT PDFs")
    parser.add_argument("--classification", type=Path, default=Path("data/pdf_classification.json"),
                       help="Path to classification JSON")
    parser.add_argument("--output", type=Path, default=Path("data/pdf_ground_truth.json"),
                       help="Output ground truth file")
    parser.add_argument("--merge-external", action="store_true",
                       help="Merge with external validation dataset")
    parser.add_argument("--external-path", type=Path,
                       default=Path("data/ground_truth/external_validation_ground_truth.json"),
                       help="Path to external validation ground truth")
    parser.add_argument("--generate-checklist", action="store_true",
                       help="Generate verification checklist")
    parser.add_argument("--checklist-output", type=Path,
                       default=Path("output/ground_truth_verification.md"),
                       help="Output path for verification checklist")

    args = parser.parse_args()

    if args.classification.exists():
        # Auto-generate ground truth
        auto_generate_ground_truth(args.classification, args.output)

        # Optionally merge with external validation
        if args.merge_external and args.external_path.exists():
            merged_output = args.output.with_name("pdf_ground_truth_merged.json")
            merge_with_external_validation(args.output, args.external_path, merged_output)
            args.output = merged_output

        # Generate verification checklist
        if args.generate_checklist:
            generate_verification_checklist(args.output, args.checklist_output)
    else:
        print(f"Classification file not found: {args.classification}")
        print("Run classify_pdfs_phase1.py first")


if __name__ == "__main__":
    main()
