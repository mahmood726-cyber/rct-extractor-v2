#!/usr/bin/env python3
"""
Gold Standard Annotation Validator
====================================

Validates gold standard annotation files against the ANNOTATION_SPEC.md schema.
Checks completeness, consistency, and plausibility of annotated effect estimates.

Usage:
    python scripts/validate_gold_annotations.py
    python scripts/validate_gold_annotations.py --annotations-dir test_pdfs/gold_standard/annotations
    python scripts/validate_gold_annotations.py --file test_pdfs/gold_standard/annotations/PMC12345.gold.jsonl
"""

import json
import sys
import os
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple


VALID_EFFECT_TYPES = {"HR", "OR", "RR", "RD", "ARD", "MD", "SMD", "IRR", "NNT", "NNH", "WMD", "ARR", "RRR"}
VALID_SOURCE_TYPES = {"text", "table", "figure", "abstract", "supplementary"}
VALID_CONFIDENCE_LEVELS = {"high", "medium", "low"}
VALID_ANALYSIS_POPULATIONS = {"ITT", "mITT", "per-protocol", "PP", "safety", ""}

# Ratio types must be positive
RATIO_TYPES = {"HR", "OR", "RR", "IRR"}


def validate_extraction(extraction: Dict[str, Any], idx: int, pdf_file: str) -> List[str]:
    """Validate a single extraction entry. Returns list of error messages."""
    errors = []
    prefix = f"  [{pdf_file}] extraction[{idx}]"

    # Required fields
    for field in ["effect_type", "point_estimate", "outcome", "source_type", "page_number", "confidence"]:
        if field not in extraction:
            errors.append(f"{prefix}: missing required field '{field}'")

    # Effect type
    effect_type = extraction.get("effect_type", "")
    if effect_type not in VALID_EFFECT_TYPES:
        errors.append(f"{prefix}: invalid effect_type '{effect_type}' (valid: {VALID_EFFECT_TYPES})")

    # Point estimate
    pe = extraction.get("point_estimate")
    if pe is not None:
        if not isinstance(pe, (int, float)):
            errors.append(f"{prefix}: point_estimate must be numeric, got {type(pe).__name__}")
        elif effect_type in RATIO_TYPES and pe <= 0:
            errors.append(f"{prefix}: {effect_type} point_estimate must be > 0, got {pe}")

    # CI bounds
    ci_lower = extraction.get("ci_lower")
    ci_upper = extraction.get("ci_upper")
    if ci_lower is not None and ci_upper is not None:
        if not isinstance(ci_lower, (int, float)) or not isinstance(ci_upper, (int, float)):
            errors.append(f"{prefix}: CI bounds must be numeric")
        elif ci_lower > ci_upper:
            errors.append(f"{prefix}: ci_lower ({ci_lower}) > ci_upper ({ci_upper})")
        elif pe is not None and isinstance(pe, (int, float)):
            if pe < ci_lower - 0.001 or pe > ci_upper + 0.001:
                errors.append(f"{prefix}: point_estimate {pe} outside CI [{ci_lower}, {ci_upper}]")

        # Ratio CI bounds must be positive
        if effect_type in RATIO_TYPES:
            if isinstance(ci_lower, (int, float)) and ci_lower <= 0:
                errors.append(f"{prefix}: {effect_type} ci_lower must be > 0, got {ci_lower}")
            if isinstance(ci_upper, (int, float)) and ci_upper <= 0:
                errors.append(f"{prefix}: {effect_type} ci_upper must be > 0, got {ci_upper}")

    # P-value
    p_value = extraction.get("p_value")
    if p_value is not None:
        if not isinstance(p_value, (int, float)):
            errors.append(f"{prefix}: p_value must be numeric")
        elif p_value < 0 or p_value > 1:
            errors.append(f"{prefix}: p_value must be in [0, 1], got {p_value}")

    # Source type
    source_type = extraction.get("source_type", "")
    if source_type not in VALID_SOURCE_TYPES:
        errors.append(f"{prefix}: invalid source_type '{source_type}' (valid: {VALID_SOURCE_TYPES})")

    # Page number
    page_num = extraction.get("page_number")
    if page_num is not None:
        if not isinstance(page_num, int) or page_num < 1:
            errors.append(f"{prefix}: page_number must be positive integer, got {page_num}")

    # Confidence
    confidence = extraction.get("confidence", "")
    if confidence not in VALID_CONFIDENCE_LEVELS:
        errors.append(f"{prefix}: invalid confidence '{confidence}' (valid: {VALID_CONFIDENCE_LEVELS})")

    # Text snippet
    text_snippet = extraction.get("text_snippet", "")
    if text_snippet and len(text_snippet) > 500:
        errors.append(f"{prefix}: text_snippet exceeds 500 chars ({len(text_snippet)})")

    # Outcome must be non-empty
    outcome = extraction.get("outcome", "")
    if not outcome or not outcome.strip():
        errors.append(f"{prefix}: outcome must be non-empty")

    return errors


def validate_annotation_file(filepath: str) -> Tuple[List[str], Dict[str, Any]]:
    """
    Validate a single annotation file.

    Returns:
        Tuple of (errors, stats)
    """
    errors = []
    stats = {
        "file": filepath,
        "num_extractions": 0,
        "effect_types": {},
        "source_types": {},
        "has_ci": 0,
        "missing_ci": 0,
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except Exception as e:
        return [f"Cannot read file {filepath}: {e}"], stats

    if not content:
        return [f"File is empty: {filepath}"], stats

    # Parse JSONL (each line is a JSON object)
    lines = content.split('\n')
    records = []
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
            records.append(record)
        except json.JSONDecodeError as e:
            errors.append(f"Line {line_num}: invalid JSON: {e}")

    if not records:
        errors.append(f"No valid JSON records in {filepath}")
        return errors, stats

    # Validate each record
    for record in records:
        # Top-level required fields
        pdf_file = record.get("pdf_file", os.path.basename(filepath))

        for field in ["pdf_file", "trial_name", "annotator", "annotation_date", "extractions"]:
            if field not in record:
                errors.append(f"[{pdf_file}] missing top-level field '{field}'")

        # Annotator
        annotator = record.get("annotator", "")
        if annotator not in ("annotator_a", "annotator_b", "consensus", "auto", ""):
            errors.append(f"[{pdf_file}] invalid annotator '{annotator}'")

        # Validate extractions
        extractions = record.get("extractions", [])
        if not isinstance(extractions, list):
            errors.append(f"[{pdf_file}] 'extractions' must be a list")
            continue

        stats["num_extractions"] += len(extractions)

        for idx, extraction in enumerate(extractions):
            ext_errors = validate_extraction(extraction, idx, pdf_file)
            errors.extend(ext_errors)

            # Collect stats
            etype = extraction.get("effect_type", "UNKNOWN")
            stats["effect_types"][etype] = stats["effect_types"].get(etype, 0) + 1

            stype = extraction.get("source_type", "unknown")
            stats["source_types"][stype] = stats["source_types"].get(stype, 0) + 1

            if extraction.get("ci_lower") is not None and extraction.get("ci_upper") is not None:
                stats["has_ci"] += 1
            else:
                stats["missing_ci"] += 1

    return errors, stats


def main():
    parser = argparse.ArgumentParser(description="Validate gold standard annotations")
    parser.add_argument("--annotations-dir", default=None,
                       help="Directory containing .gold.jsonl files")
    parser.add_argument("--file", default=None,
                       help="Validate a single file")
    args = parser.parse_args()

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    if args.file:
        files = [args.file]
    elif args.annotations_dir:
        ann_dir = Path(args.annotations_dir)
        files = sorted(str(f) for f in ann_dir.glob("*.gold.jsonl"))
    else:
        ann_dir = project_root / "test_pdfs" / "gold_standard" / "annotations"
        files = sorted(str(f) for f in ann_dir.glob("*.gold.jsonl"))

    if not files:
        print("No annotation files found.")
        sys.exit(1)

    total_errors = 0
    total_extractions = 0
    total_with_ci = 0
    all_effect_types = {}
    all_source_types = {}

    print(f"Validating {len(files)} annotation file(s)...\n")

    for filepath in files:
        errors, stats = validate_annotation_file(filepath)
        total_errors += len(errors)
        total_extractions += stats["num_extractions"]
        total_with_ci += stats["has_ci"]

        for k, v in stats["effect_types"].items():
            all_effect_types[k] = all_effect_types.get(k, 0) + v
        for k, v in stats["source_types"].items():
            all_source_types[k] = all_source_types.get(k, 0) + v

        status = "PASS" if not errors else f"FAIL ({len(errors)} errors)"
        print(f"  {os.path.basename(filepath)}: {status} ({stats['num_extractions']} extractions)")

        if errors:
            for err in errors:
                print(f"    ERROR: {err}")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Files validated: {len(files)}")
    print(f"  Total extractions: {total_extractions}")
    print(f"  With CI: {total_with_ci} ({100*total_with_ci/max(total_extractions,1):.1f}%)")
    print(f"  Effect types: {dict(sorted(all_effect_types.items()))}")
    print(f"  Source types: {dict(sorted(all_source_types.items()))}")
    print(f"  Total errors: {total_errors}")
    print(f"  Result: {'PASS' if total_errors == 0 else 'FAIL'}")

    sys.exit(0 if total_errors == 0 else 1)


if __name__ == "__main__":
    main()
