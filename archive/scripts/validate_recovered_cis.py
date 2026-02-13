#!/usr/bin/env python3
"""
Validate Recovered CIs Against Source PDFs

Addresses biostatistician critique: "The 52 recovered CIs haven't been
verified as correct - just that they pass plausibility checks"

This script:
1. Samples N recovered CIs
2. Extracts context from source PDFs
3. Outputs a verification checklist
4. Tracks manual verification results

Usage:
    python scripts/validate_recovered_cis.py --sample 20
"""

import argparse
import json
import random
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf.pdf_parser import PDFParser


def load_results(proximity_results_path: Path, enhanced_classification_path: Path) -> tuple:
    """Load proximity search results and enhanced classification."""
    with open(proximity_results_path) as f:
        proximity_results = json.load(f)

    with open(enhanced_classification_path) as f:
        enhanced = json.load(f)

    return proximity_results, enhanced


def extract_context_for_ci(pdf_path: Path, value: float, ci_lower: float, ci_upper: float, window: int = 300) -> str:
    """Extract text context around a CI from the PDF."""
    parser = PDFParser()

    try:
        pdf_content = parser.parse(str(pdf_path))
        text = "\n".join(page.full_text for page in pdf_content.pages)

        # Search for the CI pattern
        import re

        # Try to find the exact CI
        patterns = [
            f"{ci_lower}.*?{ci_upper}",
            f"{ci_lower:.2f}.*?{ci_upper:.2f}",
            f"{value}.*?{ci_lower}.*?{ci_upper}",
        ]

        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                match = matches[0]
                start = max(0, match.start() - window)
                end = min(len(text), match.end() + window)
                context = text[start:end]
                # Highlight the match
                context = context[:match.start()-start] + ">>>" + context[match.start()-start:match.end()-start] + "<<<" + context[match.end()-start:]
                return context

        # Fallback: search for value
        value_str = str(value)
        pos = text.find(value_str)
        if pos >= 0:
            start = max(0, pos - window)
            end = min(len(text), pos + len(value_str) + window)
            return text[start:end]

        return "CONTEXT NOT FOUND"

    except Exception as e:
        return f"ERROR: {e}"


def sample_and_validate(
    proximity_results: dict,
    pdf_dir: Path,
    sample_size: int,
    output_path: Path
) -> dict:
    """Sample recovered CIs and prepare validation checklist."""

    recovery_details = proximity_results.get("recovery_details", [])

    if not recovery_details:
        print("No recovered CIs to validate")
        return {}

    # Sample
    sample_size = min(sample_size, len(recovery_details))
    sample = random.sample(recovery_details, sample_size)

    print(f"Sampling {sample_size} of {len(recovery_details)} recovered CIs for validation...")

    validation_items = []

    for i, item in enumerate(sample):
        print(f"[{i+1}/{sample_size}] {item['pdf']}: {item['effect_type']}={item['value']}...")

        pdf_path = pdf_dir / item["pdf"]

        context = extract_context_for_ci(
            pdf_path,
            item["value"],
            item["ci_lower"],
            item["ci_upper"]
        )

        validation_items.append({
            "id": i + 1,
            "pdf": item["pdf"],
            "effect_type": item["effect_type"],
            "value": item["value"],
            "ci_lower": item["ci_lower"],
            "ci_upper": item["ci_upper"],
            "method": item["method"],
            "confidence": item["confidence"],
            "context": context,
            "verified": None,  # To be filled manually
            "correct_ci_lower": None,
            "correct_ci_upper": None,
            "notes": ""
        })

    results = {
        "date": datetime.now().isoformat(),
        "sample_size": sample_size,
        "total_recovered": len(recovery_details),
        "items": validation_items,
        "summary": {
            "verified_correct": 0,
            "verified_incorrect": 0,
            "unverified": sample_size
        }
    }

    # Save
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nValidation checklist saved to: {output_path}")

    return results


def generate_verification_report(validation_path: Path, output_path: Path):
    """Generate a markdown verification report for manual review."""

    with open(validation_path) as f:
        data = json.load(f)

    lines = [
        "# CI Recovery Verification Checklist",
        f"\nGenerated: {data['date']}",
        f"Sample: {data['sample_size']} of {data['total_recovered']} recovered CIs",
        "",
        "## Instructions",
        "",
        "For each item below:",
        "1. Read the extracted context (CI is marked with >>> <<<)",
        "2. Verify the CI bounds match what's in the text",
        "3. Check if the CI belongs to the correct effect value",
        "4. Mark as CORRECT or INCORRECT",
        "",
        "---",
        "",
    ]

    for item in data["items"]:
        status = "[ ]"  # Unchecked
        if item.get("verified") is True:
            status = "[x] CORRECT"
        elif item.get("verified") is False:
            status = "[!] INCORRECT"

        lines.append(f"## Item {item['id']}: {item['pdf']}")
        lines.append("")
        lines.append(f"**Effect:** {item['effect_type']} = {item['value']}")
        lines.append(f"**Recovered CI:** ({item['ci_lower']}, {item['ci_upper']})")
        lines.append(f"**Method:** {item['method']} (confidence: {item['confidence']:.2f})")
        lines.append("")
        lines.append("**Context from PDF:**")
        lines.append("```")
        # Truncate very long contexts
        context = item.get("context", "")[:1000]
        if len(item.get("context", "")) > 1000:
            context += "\n... (truncated)"
        lines.append(context)
        lines.append("```")
        lines.append("")
        lines.append(f"**Verification:** {status}")
        if item.get("notes"):
            lines.append(f"**Notes:** {item['notes']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Summary
    verified_correct = sum(1 for i in data["items"] if i.get("verified") is True)
    verified_incorrect = sum(1 for i in data["items"] if i.get("verified") is False)
    unverified = sum(1 for i in data["items"] if i.get("verified") is None)

    lines.extend([
        "## Summary",
        "",
        f"- Verified Correct: {verified_correct}",
        f"- Verified Incorrect: {verified_incorrect}",
        f"- Unverified: {unverified}",
        "",
    ])

    if verified_correct + verified_incorrect > 0:
        accuracy = verified_correct / (verified_correct + verified_incorrect) * 100
        lines.append(f"**Accuracy: {accuracy:.1f}%**")

    report = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Verification report saved to: {output_path}")


def update_summary(validation_path: Path):
    """Update summary counts based on verification status."""
    with open(validation_path) as f:
        data = json.load(f)

    data["summary"]["verified_correct"] = sum(1 for i in data["items"] if i.get("verified") is True)
    data["summary"]["verified_incorrect"] = sum(1 for i in data["items"] if i.get("verified") is False)
    data["summary"]["unverified"] = sum(1 for i in data["items"] if i.get("verified") is None)

    with open(validation_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Summary updated: {data['summary']}")


def main():
    parser = argparse.ArgumentParser(description="Validate recovered CIs against source PDFs")
    parser.add_argument("--proximity-results", type=Path,
                       default=Path("output/ci_proximity_results.json"),
                       help="Path to CI proximity search results")
    parser.add_argument("--enhanced-classification", type=Path,
                       default=Path("data/pdf_classification_enhanced.json"),
                       help="Path to enhanced classification")
    parser.add_argument("--pdf-dir", type=Path,
                       default=Path("test_pdfs/open_access_rcts"),
                       help="Directory containing PDFs")
    parser.add_argument("--output", type=Path,
                       default=Path("output/ci_validation_checklist.json"),
                       help="Output validation checklist")
    parser.add_argument("--sample", type=int, default=20,
                       help="Number of CIs to sample for validation")
    parser.add_argument("--report", action="store_true",
                       help="Generate markdown report from existing checklist")
    parser.add_argument("--report-output", type=Path,
                       default=Path("output/ci_verification_report.md"),
                       help="Output path for markdown report")
    parser.add_argument("--update-summary", action="store_true",
                       help="Update summary counts after manual verification")

    args = parser.parse_args()

    if args.update_summary:
        update_summary(args.output)
    elif args.report:
        if args.output.exists():
            generate_verification_report(args.output, args.report_output)
        else:
            print(f"Validation checklist not found: {args.output}")
    else:
        proximity_results, enhanced = load_results(
            args.proximity_results,
            args.enhanced_classification
        )

        sample_and_validate(
            proximity_results,
            args.pdf_dir,
            args.sample,
            args.output
        )

        generate_verification_report(args.output, args.report_output)


if __name__ == "__main__":
    main()
