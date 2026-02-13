#!/usr/bin/env python3
"""
Validate Extraction on LEADER Trial PDF
========================================

LEADER (PMC4985288) is the only confirmed correct PDF in validated_rcts.
This script validates extraction against known ground truth.

Ground truth from external_validation_dataset.py:
- HR 0.87 (0.78-0.97) for MACE (CV death, MI, stroke)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf.pdf_parser import PDFParser
from src.core.enhanced_extractor_v3 import EnhancedExtractor

PROJECT_ROOT = Path(__file__).parent.parent
LEADER_PDF = PROJECT_ROOT / "test_pdfs" / "validated_rcts" / "PMC4985288.pdf"

# Ground truth from external validation dataset
GROUND_TRUTH = {
    "trial": "LEADER",
    "effects": [
        {
            "type": "HR",
            "value": 0.87,
            "ci_lower": 0.78,
            "ci_upper": 0.97,
            "outcome": "MACE (CV death, MI, stroke)",
            "source": "primary endpoint"
        }
    ]
}


def main():
    print("=" * 70)
    print("LEADER TRIAL PDF EXTRACTION VALIDATION")
    print("=" * 70)

    # Parse PDF
    print("\n1. Parsing PDF...")
    parser = PDFParser()
    content = parser.parse(str(LEADER_PDF))

    print(f"   Pages: {content.num_pages}")
    print(f"   Method: {content.extraction_method}")

    full_text = "\n".join(p.full_text for p in content.pages)
    print(f"   Total chars: {len(full_text):,}")

    # Show relevant context
    print("\n2. Searching for HR mentions...")
    import re
    hr_contexts = re.findall(r'.{50}hazard ratio.{100}', full_text, re.IGNORECASE)
    print(f"   Found {len(hr_contexts)} hazard ratio mentions")

    for i, ctx in enumerate(hr_contexts[:3], 1):
        print(f"\n   Context {i}:")
        # Clean up for display
        ctx_clean = ctx.replace('\n', ' ').strip()
        print(f"   {ctx_clean[:150]}...")

    # Extract effects
    print("\n3. Running extraction...")
    extractor = EnhancedExtractor()
    extractions = extractor.extract(full_text)

    print(f"   Total extractions: {len(extractions)}")

    # Filter HR extractions
    hr_extractions = [e for e in extractions if e.effect_type.value == "HR"]
    print(f"   HR extractions: {len(hr_extractions)}")

    # Show all HR extractions
    print("\n4. HR Extractions found:")
    for i, ext in enumerate(hr_extractions, 1):
        ci_str = f"({ext.ci.lower:.2f}-{ext.ci.upper:.2f})" if ext.ci and ext.ci.lower else "no CI"
        print(f"   {i}. HR {ext.point_estimate:.2f} {ci_str}")
        if ext.source_text:
            src = ext.source_text[:80].replace('\n', ' ')
            print(f"      Source: {src}...")

    # Compare to ground truth
    print("\n5. Comparison to Ground Truth:")
    gt = GROUND_TRUTH["effects"][0]
    print(f"   Expected: HR {gt['value']:.2f} ({gt['ci_lower']:.2f}-{gt['ci_upper']:.2f})")

    # Check if ground truth is found
    found_gt = False
    for ext in hr_extractions:
        if ext.ci and ext.ci.lower:
            value_match = abs(ext.point_estimate - gt['value']) < 0.02
            ci_lower_match = abs(ext.ci.lower - gt['ci_lower']) < 0.02
            ci_upper_match = abs(ext.ci.upper - gt['ci_upper']) < 0.02

            if value_match and ci_lower_match and ci_upper_match:
                found_gt = True
                print(f"   FOUND: HR {ext.point_estimate:.2f} ({ext.ci.lower:.2f}-{ext.ci.upper:.2f})")
                break

    if not found_gt:
        print("   NOT FOUND - checking close matches...")
        for ext in hr_extractions:
            if ext.ci and ext.ci.lower:
                value_diff = abs(ext.point_estimate - gt['value'])
                if value_diff < 0.1:
                    print(f"   Close: HR {ext.point_estimate:.2f} ({ext.ci.lower:.2f}-{ext.ci.upper:.2f})")

    # Calculate metrics
    print("\n6. Metrics:")

    # For single ground truth effect
    recall = 1.0 if found_gt else 0.0
    precision = 1.0 / len(hr_extractions) if hr_extractions and found_gt else 0.0
    ci_rate = sum(1 for e in hr_extractions if e.ci and e.ci.lower) / len(hr_extractions) if hr_extractions else 0.0

    print(f"   Recall (primary endpoint): {recall:.0%}")
    print(f"   Precision: {precision:.1%}")
    print(f"   CI completion: {ci_rate:.0%}")

    print("\n" + "=" * 70)
    if found_gt:
        print("RESULT: Primary endpoint HR successfully extracted with CI")
    else:
        print("RESULT: Primary endpoint HR NOT FOUND")
    print("=" * 70)


if __name__ == "__main__":
    main()
