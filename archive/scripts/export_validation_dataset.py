#!/usr/bin/env python3
"""
Export Validation Dataset to JSONL Format
==========================================

Exports the stratified validation dataset to JSONL format for reproducibility
and external validation.

Usage:
    python scripts/export_validation_dataset.py
    python scripts/export_validation_dataset.py --output data/validation_export.jsonl
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.stratified_validation_dataset import (
    STRATIFIED_VALIDATION_TRIALS,
    get_validation_summary,
)


def export_to_jsonl(output_path: Path):
    """Export validation dataset to JSONL format"""

    records = []

    for i, trial in enumerate(STRATIFIED_VALIDATION_TRIALS, 1):
        record = {
            "id": i,
            "trial_name": trial.trial_name,
            "year": trial.year,
            "year_block": trial.year_block.value,
            "journal": trial.journal.value,
            "therapeutic_area": trial.therapeutic_area.value,
            "effect_type": trial.effect_type.value,
            "gold_standard": {
                "point_estimate": trial.expected_value,
                "ci_lower": trial.expected_ci_lower,
                "ci_upper": trial.expected_ci_upper,
            },
            "source_text": trial.source_text.strip(),
            "pmid": trial.pmid if trial.pmid else None,
            "notes": trial.notes if trial.notes else None,
        }
        records.append(record)

    # Write JSONL
    with open(output_path, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    print(f"Exported {len(records)} trials to {output_path}")
    return records


def export_summary(output_path: Path):
    """Export dataset summary as JSON"""
    summary = get_validation_summary()

    metadata = {
        "export_date": datetime.now().isoformat(),
        "version": "4.0.6",
        "total_trials": summary["total_trials"],
        "by_year_block": dict(summary["by_year_block"]),
        "by_journal": dict(summary["by_journal"]),
        "by_therapeutic_area": dict(summary["by_therapeutic_area"]),
        "by_effect_type": dict(summary["by_effect_type"]),
        "schema": {
            "id": "Sequential trial ID",
            "trial_name": "Short trial name/acronym",
            "year": "Publication year",
            "year_block": "5-year block (e.g., 2015-2019)",
            "journal": "Source journal",
            "therapeutic_area": "Medical specialty",
            "effect_type": "Type of effect measure",
            "gold_standard": {
                "point_estimate": "Effect estimate value",
                "ci_lower": "Lower bound of 95% CI",
                "ci_upper": "Upper bound of 95% CI",
            },
            "source_text": "Text containing the effect estimate",
            "pmid": "PubMed ID (if available)",
            "notes": "Additional notes",
        }
    }

    summary_path = output_path.parent / "validation_metadata.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"Exported metadata to {summary_path}")
    return metadata


def main():
    parser = argparse.ArgumentParser(
        description="Export validation dataset to JSONL format"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("data/validation_dataset.jsonl"),
        help="Output path for JSONL file"
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip metadata summary export"
    )

    args = parser.parse_args()

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Export dataset
    records = export_to_jsonl(args.output)

    # Export summary
    if not args.no_summary:
        export_summary(args.output)

    # Print summary
    print("\n" + "=" * 60)
    print("EXPORT SUMMARY")
    print("=" * 60)
    print(f"Total trials: {len(records)}")
    print(f"Output file: {args.output}")
    print(f"Format: JSON Lines (one record per line)")
    print("\nUse this dataset for:")
    print("  - Independent validation")
    print("  - Reproducibility checks")
    print("  - External benchmarking")


if __name__ == "__main__":
    main()
