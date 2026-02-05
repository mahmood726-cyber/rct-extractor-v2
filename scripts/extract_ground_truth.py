#!/usr/bin/env python3
"""
Extract Ground Truth from external_validation_dataset.py
=========================================================

Parses all trials from CARDIOVASCULAR_VALIDATION, ONCOLOGY_VALIDATION,
and ADDITIONAL_TRIALS to create structured ground truth files.

Output: data/ground_truth/external_validation_ground_truth.jsonl

Usage:
    python scripts/extract_ground_truth.py
    python scripts/extract_ground_truth.py --format json
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.external_validation_dataset import (
    ALL_EXTERNAL_VALIDATION_TRIALS,
    CARDIOVASCULAR_VALIDATION,
    ONCOLOGY_VALIDATION,
    ADDITIONAL_TRIALS,
    ExternalValidationTrial,
    ExtractionDifficulty,
    ManualExtraction,
)

PROJECT_ROOT = Path(__file__).parent.parent
GROUND_TRUTH_DIR = PROJECT_ROOT / "data" / "ground_truth"


@dataclass
class GroundTruthEffect:
    """A single ground truth effect estimate"""
    effect_type: str
    value: float
    ci_lower: float
    ci_upper: float
    p_value: Optional[float]
    outcome: str
    timepoint: str
    comparison: str
    analysis_population: str
    source_type: str
    source_text: str
    extractor_id: str


@dataclass
class GroundTruthTrial:
    """Ground truth for a single trial"""
    trial_name: str
    nct_id: Optional[str]
    pmc_id: Optional[str]
    pmid: Optional[str]
    doi: Optional[str]
    therapeutic_area: str
    journal: str
    year: int
    difficulty: str
    source: str  # "external_validation"

    # Effects
    effects: List[Dict[str, Any]]

    # Dual extraction info
    extractor_a_count: int
    extractor_b_count: int
    agreement_rate: float

    # Full source text for testing
    source_text: str


def convert_extraction(ext: ManualExtraction) -> Dict[str, Any]:
    """Convert ManualExtraction to dict"""
    return {
        "effect_type": ext.effect_type,
        "value": ext.effect_size,
        "ci_lower": ext.ci_lower,
        "ci_upper": ext.ci_upper,
        "p_value": ext.p_value,
        "outcome": ext.outcome,
        "timepoint": ext.timepoint,
        "comparison": ext.comparison,
        "analysis_population": ext.analysis_population,
        "source_type": ext.source_type.value if hasattr(ext.source_type, 'value') else str(ext.source_type),
        "source_text": ext.source_text,
        "extractor_id": ext.extractor_id,
    }


def convert_trial(trial: ExternalValidationTrial) -> GroundTruthTrial:
    """Convert ExternalValidationTrial to GroundTruthTrial"""
    # Get consensus effects, or merge extractor_a effects
    effects = []

    if trial.consensus:
        for ext in trial.consensus:
            effects.append(convert_extraction(ext))
    else:
        # Use extractor_a as primary
        for ext in trial.extractor_a:
            effects.append(convert_extraction(ext))

    # Calculate agreement
    agreement = trial.agreement_rate() if trial.extractor_a and trial.extractor_b else 1.0

    return GroundTruthTrial(
        trial_name=trial.trial_name,
        nct_id=trial.nct_number,
        pmc_id=trial.pmc_id,
        pmid=trial.pmid,
        doi=trial.doi,
        therapeutic_area=trial.therapeutic_area,
        journal=trial.journal,
        year=trial.year,
        difficulty=trial.difficulty.value,
        source="external_validation",
        effects=effects,
        extractor_a_count=len(trial.extractor_a),
        extractor_b_count=len(trial.extractor_b),
        agreement_rate=agreement,
        source_text=trial.source_text,
    )


def extract_all_ground_truth() -> List[GroundTruthTrial]:
    """Extract ground truth from all trials"""
    ground_truth = []

    for trial in ALL_EXTERNAL_VALIDATION_TRIALS:
        gt = convert_trial(trial)
        ground_truth.append(gt)

    return ground_truth


def save_jsonl(ground_truth: List[GroundTruthTrial], output_path: Path):
    """Save ground truth as JSONL"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for gt in ground_truth:
            f.write(json.dumps(asdict(gt), ensure_ascii=False) + "\n")

    print(f"Saved {len(ground_truth)} trials to {output_path}")


def save_json(ground_truth: List[GroundTruthTrial], output_path: Path):
    """Save ground truth as single JSON file"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Count effects
    total_effects = sum(len(gt.effects) for gt in ground_truth)
    by_type = {}
    for gt in ground_truth:
        for eff in gt.effects:
            et = eff["effect_type"]
            by_type[et] = by_type.get(et, 0) + 1

    data = {
        "version": "4.3.0",
        "generated": datetime.now().isoformat(),
        "source": "external_validation_dataset.py",
        "summary": {
            "total_trials": len(ground_truth),
            "total_effects": total_effects,
            "with_pmc_id": len([gt for gt in ground_truth if gt.pmc_id]),
            "with_nct_id": len([gt for gt in ground_truth if gt.nct_id]),
            "by_effect_type": by_type,
            "by_difficulty": {
                diff.value: len([gt for gt in ground_truth if gt.difficulty == diff.value])
                for diff in ExtractionDifficulty
            },
            "avg_agreement_rate": sum(gt.agreement_rate for gt in ground_truth) / len(ground_truth) if ground_truth else 0,
        },
        "trials": [asdict(gt) for gt in ground_truth],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(ground_truth)} trials to {output_path}")


def print_summary(ground_truth: List[GroundTruthTrial]):
    """Print summary statistics"""
    print("\n" + "=" * 70)
    print("GROUND TRUTH EXTRACTION SUMMARY")
    print("=" * 70)

    print(f"\nTotal trials: {len(ground_truth)}")
    print(f"With PMC ID: {len([gt for gt in ground_truth if gt.pmc_id])}")
    print(f"With NCT ID: {len([gt for gt in ground_truth if gt.nct_id])}")

    # Effect counts
    total_effects = sum(len(gt.effects) for gt in ground_truth)
    print(f"\nTotal effects: {total_effects}")

    # By type
    by_type = {}
    for gt in ground_truth:
        for eff in gt.effects:
            et = eff["effect_type"]
            by_type[et] = by_type.get(et, 0) + 1

    print("\nBy effect type:")
    for et, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {et}: {count}")

    # By therapeutic area
    by_area = {}
    for gt in ground_truth:
        area = gt.therapeutic_area.split(" - ")[0]
        by_area[area] = by_area.get(area, 0) + 1

    print("\nBy therapeutic area:")
    for area, count in sorted(by_area.items(), key=lambda x: -x[1]):
        print(f"  {area}: {count}")

    # By difficulty
    print("\nBy difficulty:")
    for diff in ExtractionDifficulty:
        count = len([gt for gt in ground_truth if gt.difficulty == diff.value])
        print(f"  {diff.value}: {count}")

    # Agreement statistics
    agreements = [gt.agreement_rate for gt in ground_truth if gt.extractor_a_count > 0 and gt.extractor_b_count > 0]
    if agreements:
        avg_agreement = sum(agreements) / len(agreements)
        print(f"\nAverage inter-rater agreement: {avg_agreement:.1%}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Extract ground truth from external_validation_dataset.py"
    )
    parser.add_argument(
        "--format", choices=["jsonl", "json", "both"], default="both",
        help="Output format (default: both)"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=GROUND_TRUTH_DIR,
        help="Output directory"
    )

    args = parser.parse_args()

    # Extract ground truth
    print("Extracting ground truth from external_validation_dataset.py...")
    ground_truth = extract_all_ground_truth()

    # Save outputs
    if args.format in ("jsonl", "both"):
        jsonl_path = args.output_dir / "external_validation_ground_truth.jsonl"
        save_jsonl(ground_truth, jsonl_path)

    if args.format in ("json", "both"):
        json_path = args.output_dir / "external_validation_ground_truth.json"
        save_json(ground_truth, json_path)

    # Print summary
    print_summary(ground_truth)


if __name__ == "__main__":
    main()
