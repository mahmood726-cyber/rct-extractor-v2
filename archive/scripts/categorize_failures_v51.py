#!/usr/bin/env python3
"""
Failure Categorization Script (v5.1)
======================================

Runs the extractor on development gold-standard PDFs and categorizes
each missed effect estimate by failure type.

Categories:
- pattern_gap: No regex pattern matches the text format
- table_only: Effect is only in a table, not inline text
- multi_column_interleave: Multi-column PDF layout corrupts text
- ocr_corruption: OCR errors prevent pattern matching
- negative_context_filter: Valid effect rejected by negative context
- ci_format_gap: Point estimate found but CI format not recognized
- other: Uncategorized

Usage:
    python scripts/categorize_failures_v51.py
    python scripts/categorize_failures_v51.py --output output/failure_categorization_v51.json
"""

import json
import sys
import os
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


FAILURE_CATEGORIES = [
    "pattern_gap",
    "table_only",
    "multi_column_interleave",
    "ocr_corruption",
    "negative_context_filter",
    "ci_format_gap",
    "other",
]


def values_match(expected: float, extracted: float, effect_type: str,
                tolerance: float = 0.05) -> bool:
    """Check if two values match within tolerance."""
    if expected == 0 and extracted == 0:
        return True
    if effect_type in ("HR", "OR", "RR", "IRR"):
        if expected == 0:
            return abs(extracted) < tolerance
        return abs(extracted - expected) / abs(expected) <= tolerance
    denom = max(abs(expected), abs(extracted), 1.0)
    return abs(extracted - expected) / denom <= tolerance


def effect_type_matches(expected_type: str, extracted_type: str) -> bool:
    """Check if effect types match."""
    aliases = {"RD": "ARD", "WMD": "MD", "ARR": "ARD"}
    et = aliases.get(expected_type, expected_type)
    xt = aliases.get(extracted_type, extracted_type)
    return et == xt


def categorize_failure(
    expected: Dict[str, Any],
    full_text: str,
    extracted_types_values: List[Tuple[str, float]],
) -> str:
    """
    Categorize why an expected effect was not extracted.

    Args:
        expected: Gold standard annotation dict
        full_text: Full text of the PDF
        extracted_types_values: List of (type, value) tuples from extraction

    Returns:
        Failure category string
    """
    effect_type = expected.get("effect_type", "")
    value = expected.get("point_estimate", 0.0)
    source_type = expected.get("source_type", "")
    text_snippet = expected.get("text_snippet", "")

    # 1. Table-only: annotated as coming from a table
    if source_type == "table":
        return "table_only"

    # 2. Check if the text snippet appears in the full text
    if text_snippet:
        snippet_clean = re.sub(r'\s+', ' ', text_snippet.strip())
        text_clean = re.sub(r'\s+', ' ', full_text)

        if snippet_clean not in text_clean:
            # Snippet not found — could be multi-column interleave or OCR
            # Check for OCR artifacts
            ocr_indicators = [
                'l' in str(value),  # l for 1
                'O' in str(value),  # O for 0
                any(c in text_snippet for c in ['\ufb01', '\ufb02']),  # Ligatures
            ]
            if any(ocr_indicators):
                return "ocr_corruption"
            return "multi_column_interleave"

    # 3. Check if the value appears in text at all
    value_str = str(value)
    if value_str not in full_text:
        # Value not even in text
        if source_type in ("figure", "supplementary"):
            return "other"
        return "multi_column_interleave"

    # 4. Value is in text — check if it was extracted with wrong type or no CI
    value_found_with_type = False
    for ext_type, ext_value in extracted_types_values:
        if values_match(value, ext_value, effect_type, 0.05):
            if effect_type_matches(effect_type, ext_type):
                # Extracted with matching type — must be CI format issue
                return "ci_format_gap"
            else:
                value_found_with_type = True

    if value_found_with_type:
        return "pattern_gap"  # Value found but wrong type

    # 5. Value in text but not extracted at all — pattern gap
    # Check if near negative context
    value_pos = full_text.find(value_str)
    if value_pos >= 0:
        context = full_text[max(0, value_pos - 200):value_pos + 200]
        neg_patterns = [
            r'protocol', r'sample size', r'planned', r'hypothesized',
            r'previous study', r'literature', r'reported by',
        ]
        for pat in neg_patterns:
            if re.search(pat, context, re.IGNORECASE):
                return "negative_context_filter"

    return "pattern_gap"


def load_gold_annotations(filepath: str) -> List[Dict[str, Any]]:
    """Load gold standard annotations."""
    extractions = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            extractions.extend(record.get("extractions", []))
    return extractions


def resolve_pdf_path(pdf_file: str, source: str, project_root: Path) -> Optional[str]:
    """Resolve PDF path."""
    candidates = [
        project_root / "test_pdfs" / source / pdf_file,
        project_root / "test_pdfs" / "open_access_rcts" / pdf_file,
        project_root / "test_pdfs" / "oa_rct_corpus_v2" / pdf_file,
        project_root / "test_pdfs" / "oa_rct_corpus" / pdf_file,
    ]
    for subdir in ["cardiology", "respiratory", "diabetes", "oncology",
                   "infectious", "neurology", "rheumatology"]:
        candidates.append(project_root / "test_pdfs" / "real_pdfs" / subdir / pdf_file)

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def main():
    parser = argparse.ArgumentParser(description="Categorize extraction failures")
    parser.add_argument("--output", default="output/failure_categorization_v51.json")
    args = parser.parse_args()

    proj_root = Path(__file__).parent.parent

    # Load split
    split_path = proj_root / "data" / "gold_standard_split.json"
    with open(split_path, 'r') as f:
        split_data = json.load(f)

    dev_pdfs = split_data["development"]["pdfs"]

    # Import pipeline
    from src.core.pdf_extraction_pipeline import PDFExtractionPipeline
    pipeline = PDFExtractionPipeline(extract_diagnostics=False)

    # Results
    all_failures = []
    category_counts = {cat: 0 for cat in FAILURE_CATEGORIES}
    per_type_counts = {}
    pdfs_processed = 0
    total_expected = 0
    total_matched = 0

    print(f"Categorizing failures on {len(dev_pdfs)} development PDFs...\n")

    for pdf_info in dev_pdfs:
        pdf_file = pdf_info["file"]
        source = pdf_info["source"]

        # Find PDF
        pdf_path = resolve_pdf_path(pdf_file, source, proj_root)
        if not pdf_path:
            print(f"  SKIP {pdf_file}: PDF not found")
            continue

        # Find annotation
        ann_path = proj_root / "test_pdfs" / "gold_standard" / "annotations" / pdf_file.replace(".pdf", ".gold.jsonl")
        if not ann_path.exists():
            print(f"  SKIP {pdf_file}: no gold annotation")
            continue

        gold = load_gold_annotations(str(ann_path))
        if not gold:
            print(f"  SKIP {pdf_file}: empty annotation")
            continue

        # Run extraction
        try:
            result = pipeline.extract_from_pdf(pdf_path)
        except Exception as e:
            print(f"  ERROR {pdf_file}: {e}")
            continue

        pdfs_processed += 1
        total_expected += len(gold)

        # Build extracted list
        extracted_list = [
            (e.effect_type.value, e.point_estimate)
            for e in result.effect_estimates
        ]

        # Match each expected effect
        used_extracted = set()
        pdf_failures = []

        for exp in gold:
            exp_type = exp.get("effect_type", "")
            exp_value = exp.get("point_estimate", 0.0)

            # Try to find match
            matched = False
            for idx, (ext_type, ext_value) in enumerate(extracted_list):
                if idx in used_extracted:
                    continue
                if effect_type_matches(exp_type, ext_type) and values_match(exp_value, ext_value, exp_type, 0.05):
                    matched = True
                    used_extracted.add(idx)
                    total_matched += 1
                    break

            if not matched:
                category = categorize_failure(exp, result.full_text, extracted_list)
                category_counts[category] += 1

                if exp_type not in per_type_counts:
                    per_type_counts[exp_type] = {cat: 0 for cat in FAILURE_CATEGORIES}
                per_type_counts[exp_type][category] += 1

                pdf_failures.append({
                    "effect_type": exp_type,
                    "point_estimate": exp_value,
                    "outcome": exp.get("outcome", ""),
                    "source_type": exp.get("source_type", ""),
                    "category": category,
                    "text_snippet": exp.get("text_snippet", "")[:200],
                })

        if pdf_failures:
            all_failures.append({
                "pdf_file": pdf_file,
                "failures": pdf_failures,
            })
            print(f"  {pdf_file}: {len(pdf_failures)} failures "
                  f"({len(gold) - len(pdf_failures)}/{len(gold)} matched)")
        else:
            print(f"  {pdf_file}: PERFECT ({len(gold)}/{len(gold)} matched)")

    # Summary
    total_failures = sum(category_counts.values())
    print(f"\n{'='*60}")
    print(f"Failure Categorization Summary")
    print(f"{'='*60}")
    print(f"  PDFs processed: {pdfs_processed}")
    print(f"  Total expected: {total_expected}")
    print(f"  Total matched: {total_matched}")
    print(f"  Total failures: {total_failures}")
    if total_expected > 0:
        print(f"  Sensitivity: {total_matched/total_expected:.1%}")
    print(f"\n  Failure categories:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        if count > 0:
            pct = 100 * count / max(total_failures, 1)
            print(f"    {cat}: {count} ({pct:.1f}%)")

    print(f"\n  Per-type breakdown:")
    for etype, cats in sorted(per_type_counts.items()):
        type_total = sum(cats.values())
        if type_total > 0:
            top_cat = max(cats, key=cats.get)
            print(f"    {etype}: {type_total} failures (most common: {top_cat})")

    # Save output
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pdfs_processed": pdfs_processed,
        "total_expected": total_expected,
        "total_matched": total_matched,
        "total_failures": total_failures,
        "sensitivity": total_matched / max(total_expected, 1),
        "category_counts": category_counts,
        "per_type_counts": per_type_counts,
        "failures": all_failures,
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to: {args.output}")


if __name__ == "__main__":
    main()
