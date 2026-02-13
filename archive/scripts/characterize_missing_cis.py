#!/usr/bin/env python3
"""
Characterize the 22 Missing CIs
================================

For each extraction missing a CI, determine why:
- CI is in a table (not extractable from text)
- CI is in a figure
- CI is genuinely absent from the paper
- CI exists but pattern doesn't match

Usage:
    python scripts/characterize_missing_cis.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.enhanced_extractor_v3 import EnhancedExtractor
from src.core.text_preprocessor import TextPreprocessor, TextLine
from src.pdf.pdf_parser import PDFParser
from scripts.ci_proximity_search import CIProximitySearch, _ci_key

PROJECT_ROOT = Path(__file__).parent.parent


def characterize_missing(pdf_path: Path, extractor: EnhancedExtractor,
                         preprocessor: TextPreprocessor,
                         proximity: CIProximitySearch) -> list:
    """Find extractions missing CIs and characterize why."""
    parser = PDFParser()
    pdf_content = parser.parse(str(pdf_path))
    raw_text = "\n".join(page.full_text for page in pdf_content.pages)

    # Preprocess
    raw_lines = raw_text.split('\n')
    text_lines = [TextLine(text=line, page_num=0, line_num=i)
                  for i, line in enumerate(raw_lines)]
    if text_lines:
        doc = preprocessor.process(text_lines)
        processed = doc.reading_order_text
    else:
        processed = raw_text

    # Extract
    extractions = extractor.extract(processed)

    # Convert and run proximity
    results = []
    used_cis = set()

    for e in extractions:
        d = {
            "effect_type": str(e.effect_type.value) if hasattr(e.effect_type, 'value') else str(e.effect_type),
            "value": e.point_estimate,
            "ci_lower": e.ci.lower if e.ci else None,
            "ci_upper": e.ci.upper if e.ci else None,
            "ci_complete": e.has_complete_ci,
            "source_text": e.source_text[:200] if e.source_text else "",
        }
        if d["ci_complete"] and d["ci_lower"] is not None:
            used_cis.add(_ci_key(d["ci_lower"], d["ci_upper"]))

        if not d["ci_complete"]:
            r = proximity.search_ci_near_value(
                processed, d["value"], d["effect_type"], exclude_cis=used_cis
            )
            if r:
                d["ci_lower"] = r.ci_lower
                d["ci_upper"] = r.ci_upper
                d["ci_complete"] = True
                d["ci_source"] = "proximity"
                used_cis.add(_ci_key(r.ci_lower, r.ci_upper))

        results.append(d)

    # Characterize missing CIs
    missing = []
    for d in results:
        if d["ci_complete"]:
            continue

        value = d["value"]
        effect_type = d["effect_type"]
        source = d.get("source_text", "")

        # Search raw text for CI near this value
        category = "UNKNOWN"
        evidence = ""

        # Check if value appears in table context
        value_str = f"{value:.2f}" if isinstance(value, float) else str(value)
        for i, line in enumerate(raw_lines):
            if value_str in line:
                # Check if nearby lines look like a table
                context_lines = raw_lines[max(0, i-3):min(len(raw_lines), i+4)]
                context = "\n".join(context_lines)

                # Table indicators: lots of numbers, tabs, alignment
                num_count = len(re.findall(r'\d+\.?\d*', context))
                has_tab = '\t' in context
                short_lines = sum(1 for l in context_lines if len(l.strip()) < 40)

                if num_count > 8 or has_tab or short_lines >= 4:
                    category = "IN_TABLE"
                    evidence = context[:200]
                    break

                # Check if CI exists in nearby text but wasn't matched
                ci_nearby = re.search(
                    r'(?:95%?\s*CI|CI)[:\s,]*[\(\[]?\s*(-?\d+\.?\d*)\s*'
                    r'(?:[-\u2013\u2014,]|to)\s*(-?\d+\.?\d*)',
                    context, re.IGNORECASE
                )
                if ci_nearby:
                    category = "CI_EXISTS_NOT_MATCHED"
                    evidence = f"CI found: {ci_nearby.group(0)} in context: {context[:150]}"
                    break

        if category == "UNKNOWN":
            # Check if effect type + value appear only in abstract
            abstract_end = processed.find("Introduction") or processed.find("METHODS") or processed.find("Background")
            if abstract_end and abstract_end > 0:
                in_abstract = value_str in processed[:abstract_end]
                in_body = value_str in processed[abstract_end:]
                if in_abstract and not in_body:
                    category = "ABSTRACT_ONLY"
                    evidence = "Value only in abstract, not in body text"

        if category == "UNKNOWN":
            # Check if value appears at all
            if value_str not in processed:
                category = "VALUE_NOT_IN_TEXT"
                evidence = f"Value {value_str} not found in processed text"
            else:
                category = "CI_ABSENT"
                evidence = f"Value found but no CI pattern nearby"

        missing.append({
            "pmc_id": pdf_path.stem,
            "effect_type": effect_type,
            "value": value,
            "source_text": source[:150],
            "category": category,
            "evidence": evidence[:200],
        })

    return missing


def main():
    print("Characterizing 22 missing CIs...\n")

    extractor = EnhancedExtractor()
    preprocessor = TextPreprocessor()
    proximity = CIProximitySearch()

    # Get all curated PDFs
    manifest_path = PROJECT_ROOT / "data" / "curated_rct_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        excluded = set(manifest.get("excluded_pdfs", []))
    else:
        excluded = set()

    pdf_dir = PROJECT_ROOT / "test_pdfs" / "open_access_rcts"
    pdf_files = sorted(pdf_dir.glob("PMC*.pdf"))
    pdf_files = [f for f in pdf_files if f.name not in excluded]

    all_missing = []
    total_extractions = 0
    total_ci = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        try:
            missing = characterize_missing(pdf_path, extractor, preprocessor, proximity)
            total_extractions += len(missing)  # approximate

            if missing:
                for m in missing:
                    print(f"  [{m['category']:25s}] {m['pmc_id']} {m['effect_type']}={m['value']}")
                all_missing.extend(missing)
        except Exception as e:
            print(f"  ERROR processing {pdf_path.name}: {str(e)[:80]}")

    # Summary
    print("\n" + "=" * 70)
    print(f"MISSING CI CHARACTERIZATION ({len(all_missing)} total)")
    print("=" * 70)

    by_category = {}
    for m in all_missing:
        cat = m["category"]
        by_category[cat] = by_category.get(cat, 0) + 1

    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"  {cat:25s}: {count}")

    # Save
    output_path = PROJECT_ROOT / "output" / "missing_ci_characterization.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "total_missing": len(all_missing),
            "by_category": by_category,
            "details": all_missing,
        }, f, indent=2)
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
