#!/usr/bin/env python3
"""
Consolidate Ground Truth from Multiple Sources
================================================

Merges ground truth from:
1. external_validation_dataset.py (39+ trials with dual manual extractions)
2. ClinicalTrials.gov API results (for NCT-linked PDFs)
3. Manual annotations in data/gold/

Output: data/ground_truth/consolidated.jsonl

Usage:
    python scripts/consolidate_ground_truth.py
    python scripts/consolidate_ground_truth.py --fetch-ctg
    python scripts/consolidate_ground_truth.py --dry-run
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from data.external_validation_dataset import (
    ALL_EXTERNAL_VALIDATION_TRIALS,
    ExternalValidationTrial,
    ExtractionDifficulty,
)

# Try to import CTG scraper
try:
    from scripts.ctg_scraper import CTGScraper, EffectEstimate
    HAS_CTG_SCRAPER = True
except ImportError:
    HAS_CTG_SCRAPER = False
    CTGScraper = None
    EffectEstimate = None

PROJECT_ROOT = Path(__file__).parent.parent
GROUND_TRUTH_DIR = PROJECT_ROOT / "data" / "ground_truth"
GOLD_DIR = PROJECT_ROOT / "data" / "gold"
OUTPUT_PATH = GROUND_TRUTH_DIR / "consolidated.jsonl"


@dataclass
class ConsolidatedGroundTruth:
    """Consolidated ground truth for a single PDF/trial"""
    pdf: str  # PDF filename or PMC ID
    trial: str  # Trial name
    nct_id: Optional[str]
    pmc_id: Optional[str]
    therapeutic_area: str
    difficulty: str

    # Ground truth effects from all sources
    ground_truth: List[Dict[str, Any]]

    # Source tracking
    sources: List[str]  # e.g., ["external_validation", "ctg", "manual"]

    # Full text for extraction testing
    source_text: str = ""

    # Metadata
    source_agreement: Optional[float] = None  # Agreement between sources
    verification_status: str = "unverified"  # "unverified", "verified", "conflict"
    notes: List[str] = field(default_factory=list)


def load_external_validation() -> Dict[str, List[Dict[str, Any]]]:
    """Load ground truth from external_validation_dataset.py"""
    print("Loading external validation dataset...")

    results = {}

    for trial in ALL_EXTERNAL_VALIDATION_TRIALS:
        key = trial.pmc_id if trial.pmc_id else trial.trial_name

        effects = []
        # Use consensus if available, else extractor_a
        extractions = trial.consensus if trial.consensus else trial.extractor_a

        for ext in extractions:
            effects.append({
                "type": ext.effect_type,
                "value": ext.effect_size,
                "ci_lower": ext.ci_lower,
                "ci_upper": ext.ci_upper,
                "p_value": ext.p_value,
                "outcome": ext.outcome,
                "source": "external_validation",
                "source_text": ext.source_text,
            })

        results[key] = {
            "trial": trial,
            "effects": effects,
            "source_text": trial.source_text,
        }

    print(f"  Loaded {len(results)} trials")
    return results


def load_gold_annotations() -> Dict[str, List[Dict[str, Any]]]:
    """Load ground truth from data/gold/ JSONL files"""
    print("Loading gold annotations...")

    results = {}

    if not GOLD_DIR.exists():
        print("  Gold directory not found, skipping")
        return results

    for jsonl_file in GOLD_DIR.glob("*.jsonl"):
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)

                    # Get key (PMC ID or trial name)
                    key = data.get("pmc_id") or data.get("trial_name", "")
                    if not key:
                        continue

                    expected = data.get("expected", {})
                    if not expected:
                        continue

                    # Convert to standard format
                    effect = {
                        "type": expected.get("measure_type", ""),
                        "value": expected.get("value"),
                        "ci_lower": expected.get("ci_lower"),
                        "ci_upper": expected.get("ci_upper"),
                        "source": "gold_annotation",
                        "source_file": jsonl_file.name,
                    }

                    if key not in results:
                        results[key] = []
                    results[key].append(effect)

        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Error reading {jsonl_file.name}: {e}")

    print(f"  Loaded annotations for {len(results)} PDFs/trials")
    return results


def fetch_ctg_ground_truth(nct_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch ground truth from ClinicalTrials.gov API"""
    if not HAS_CTG_SCRAPER or not HAS_REQUESTS:
        print("CTG scraper not available, skipping CTG fetch")
        return {}

    print(f"Fetching CTG results for {len(nct_ids)} NCT IDs...")

    results = {}
    scraper = CTGScraper(rate_limit=0.5)

    for i, nct_id in enumerate(nct_ids, 1):
        print(f"  [{i}/{len(nct_ids)}] {nct_id}...")

        try:
            study = scraper.fetch_study(nct_id)
            if study and study.effect_estimates:
                effects = []
                for est in study.effect_estimates:
                    effects.append({
                        "type": est.effect_type,
                        "value": est.value,
                        "ci_lower": est.ci_lower,
                        "ci_upper": est.ci_upper,
                        "p_value": est.p_value,
                        "outcome": est.outcome_title,
                        "source": "ctg",
                        "analysis_method": est.analysis_method,
                    })
                results[nct_id] = effects
                print(f"    Found {len(effects)} effects")
        except Exception as e:
            print(f"    Error: {e}")

    print(f"  Fetched results for {len(results)} studies")
    return results


def consolidate_effects(
    sources: Dict[str, List[Dict[str, Any]]],
    primary_key: str
) -> tuple[List[Dict[str, Any]], List[str], Optional[float]]:
    """
    Consolidate effects from multiple sources.

    Returns:
        - Merged effects list
        - List of source names
        - Agreement rate (if multiple sources)
    """
    all_effects = []
    source_names = set()

    for source_name, effects in sources.items():
        source_names.add(source_name)
        for eff in effects:
            # Add source tracking
            eff_copy = dict(eff)
            eff_copy["_source"] = source_name
            all_effects.append(eff_copy)

    # Calculate agreement if multiple sources
    agreement = None
    if len(source_names) > 1:
        # Simple agreement: do values match within tolerance?
        matches = 0
        comparisons = 0

        # Group by effect type
        by_type = {}
        for eff in all_effects:
            et = eff.get("type", "")
            if et not in by_type:
                by_type[et] = []
            by_type[et].append(eff)

        for et, effs in by_type.items():
            if len(effs) < 2:
                continue

            # Compare values
            values = [e.get("value") for e in effs if e.get("value") is not None]
            if len(values) >= 2:
                comparisons += 1
                # Check if values are within 5% of each other
                max_val = max(abs(v) for v in values if v != 0) if any(v != 0 for v in values) else 1
                if all(abs(v - values[0]) / max_val < 0.05 for v in values):
                    matches += 1

        if comparisons > 0:
            agreement = matches / comparisons

    # Deduplicate effects (prefer external_validation > ctg > gold)
    priority = {"external_validation": 0, "ctg": 1, "gold_annotation": 2}

    deduped = {}
    for eff in sorted(all_effects, key=lambda e: priority.get(e.get("_source", ""), 99)):
        # Key by type + value (rounded)
        val = eff.get("value")
        key = f"{eff.get('type')}_{round(val, 3) if val else 'none'}"

        if key not in deduped:
            deduped[key] = eff

    return list(deduped.values()), list(source_names), agreement


def consolidate_all(fetch_ctg: bool = False, dry_run: bool = False) -> List[ConsolidatedGroundTruth]:
    """Consolidate ground truth from all sources"""

    # Load external validation
    ext_val = load_external_validation()

    # Load gold annotations
    gold = load_gold_annotations()

    # Optionally fetch CTG results
    ctg = {}
    if fetch_ctg and HAS_CTG_SCRAPER:
        nct_ids = [
            trial.nct_number
            for trial in ALL_EXTERNAL_VALIDATION_TRIALS
            if trial.nct_number
        ]
        ctg = fetch_ctg_ground_truth(nct_ids)

    # Consolidate for each trial
    consolidated = []

    for trial in ALL_EXTERNAL_VALIDATION_TRIALS:
        # Gather effects from all sources
        sources = {}

        # External validation
        key = trial.pmc_id if trial.pmc_id else trial.trial_name
        if key in ext_val:
            sources["external_validation"] = ext_val[key]["effects"]

        # Gold annotations (by PMC ID or trial name)
        if trial.pmc_id and trial.pmc_id in gold:
            sources["gold_annotation"] = gold[trial.pmc_id]
        elif trial.trial_name in gold:
            sources["gold_annotation"] = gold[trial.trial_name]

        # CTG results
        if trial.nct_number and trial.nct_number in ctg:
            sources["ctg"] = ctg[trial.nct_number]

        # Consolidate
        effects, source_names, agreement = consolidate_effects(sources, key)

        # Determine verification status
        if len(source_names) >= 2:
            if agreement is not None and agreement >= 0.8:
                status = "verified"
            elif agreement is not None and agreement < 0.5:
                status = "conflict"
            else:
                status = "partial"
        else:
            status = "single_source"

        # Create consolidated record
        pdf_name = f"{trial.pmc_id}.pdf" if trial.pmc_id else f"{trial.trial_name}.pdf"

        record = ConsolidatedGroundTruth(
            pdf=pdf_name,
            trial=trial.trial_name,
            nct_id=trial.nct_number,
            pmc_id=trial.pmc_id,
            therapeutic_area=trial.therapeutic_area,
            difficulty=trial.difficulty.value,
            ground_truth=effects,
            sources=source_names,
            source_text=trial.source_text,
            source_agreement=agreement,
            verification_status=status,
        )

        consolidated.append(record)

    return consolidated


def save_consolidated(consolidated: List[ConsolidatedGroundTruth], output_path: Path):
    """Save consolidated ground truth as JSONL"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for record in consolidated:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    print(f"\nSaved {len(consolidated)} records to {output_path}")


def print_summary(consolidated: List[ConsolidatedGroundTruth]):
    """Print consolidation summary"""
    print("\n" + "=" * 70)
    print("GROUND TRUTH CONSOLIDATION SUMMARY")
    print("=" * 70)

    print(f"\nTotal trials: {len(consolidated)}")
    print(f"With PMC ID: {len([c for c in consolidated if c.pmc_id])}")
    print(f"With NCT ID: {len([c for c in consolidated if c.nct_id])}")

    # Count effects
    total_effects = sum(len(c.ground_truth) for c in consolidated)
    print(f"\nTotal ground truth effects: {total_effects}")

    # By source count
    source_counts = {}
    for c in consolidated:
        n = len(c.sources)
        source_counts[n] = source_counts.get(n, 0) + 1

    print("\nTrials by number of sources:")
    for n, count in sorted(source_counts.items()):
        print(f"  {n} source(s): {count}")

    # By verification status
    print("\nBy verification status:")
    status_counts = {}
    for c in consolidated:
        status_counts[c.verification_status] = status_counts.get(c.verification_status, 0) + 1
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    # By effect type
    by_type = {}
    for c in consolidated:
        for eff in c.ground_truth:
            et = eff.get("type", "unknown")
            by_type[et] = by_type.get(et, 0) + 1

    print("\nBy effect type:")
    for et, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {et}: {count}")

    # Multi-source agreement
    multi_source = [c for c in consolidated if c.source_agreement is not None]
    if multi_source:
        avg_agreement = sum(c.source_agreement for c in multi_source) / len(multi_source)
        print(f"\nMulti-source trials: {len(multi_source)}")
        print(f"Average agreement: {avg_agreement:.1%}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Consolidate ground truth from multiple sources"
    )
    parser.add_argument(
        "--fetch-ctg", action="store_true",
        help="Fetch results from ClinicalTrials.gov API"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be done without writing files"
    )
    parser.add_argument(
        "--output", type=Path, default=OUTPUT_PATH,
        help="Output file path"
    )

    args = parser.parse_args()

    # Consolidate
    consolidated = consolidate_all(
        fetch_ctg=args.fetch_ctg,
        dry_run=args.dry_run,
    )

    # Print summary
    print_summary(consolidated)

    # Save
    if not args.dry_run:
        save_consolidated(consolidated, args.output)
    else:
        print("\n[DRY RUN] Would save to:", args.output)


if __name__ == "__main__":
    main()
