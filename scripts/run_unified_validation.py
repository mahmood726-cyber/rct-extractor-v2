#!/usr/bin/env python3
"""
Unified Validation Pipeline for RCT Extractor v4.3
====================================================

Single command to validate extraction against ground truth corpus.

Features:
- Extracts effects from PDFs or source text
- Compares against consolidated ground truth
- Calculates precision, recall, CI completion by effect type
- Generates detailed report

Usage:
    python scripts/run_unified_validation.py
    python scripts/run_unified_validation.py --pdfs test_pdfs/validated_rcts/
    python scripts/run_unified_validation.py --ground-truth data/ground_truth/consolidated.jsonl
    python scripts/run_unified_validation.py --output output/validation_v4.3.json
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.external_validation_dataset import (
    ALL_EXTERNAL_VALIDATION_TRIALS,
    ExtractionDifficulty,
)

# Try to import extractor
try:
    from src.core.enhanced_extractor_v3 import EnhancedExtractor, EffectType, Extraction
    HAS_EXTRACTOR = True
except ImportError:
    HAS_EXTRACTOR = False
    EnhancedExtractor = None

# Try to import PDF parser
try:
    from src.pdf.pdf_parser import extract_text_from_pdf
    HAS_PDF_PARSER = True
except ImportError:
    HAS_PDF_PARSER = False
    extract_text_from_pdf = None


PROJECT_ROOT = Path(__file__).parent.parent
GROUND_TRUTH_DIR = PROJECT_ROOT / "data" / "ground_truth"
OUTPUT_DIR = PROJECT_ROOT / "output"
BASELINES_DIR = PROJECT_ROOT / "data" / "baselines"


@dataclass
class EffectMatch:
    """Match result between expected and extracted effect"""
    expected_type: str
    expected_value: float
    expected_ci_lower: Optional[float]
    expected_ci_upper: Optional[float]
    extracted_type: Optional[str]
    extracted_value: Optional[float]
    extracted_ci_lower: Optional[float]
    extracted_ci_upper: Optional[float]
    match_status: str  # "exact", "value_only", "type_only", "missed"
    has_complete_ci: bool
    value_error: Optional[float]
    ci_lower_error: Optional[float]
    ci_upper_error: Optional[float]


@dataclass
class TrialValidation:
    """Validation results for a single trial"""
    trial_name: str
    pmc_id: Optional[str]
    nct_id: Optional[str]
    therapeutic_area: str
    difficulty: str

    # Counts
    expected_effects: int
    extracted_effects: int
    matched_effects: int
    missed_effects: int
    with_complete_ci: int
    extra_effects: int

    # Matches
    matches: List[EffectMatch]

    # By effect type
    by_type: Dict[str, Dict[str, int]]


@dataclass
class ValidationSummary:
    """Overall validation summary"""
    version: str
    timestamp: str
    corpus_size: int
    pdfs_processed: int
    pdfs_with_extractions: int

    # Overall metrics
    total_expected: int
    total_extracted: int
    total_matched: int
    total_missed: int
    total_with_ci: int

    # Rates
    extraction_rate: float  # PDFs with extractions / total PDFs
    recall: float  # matched / expected
    precision: float  # matched / extracted
    ci_completion: float  # with_ci / matched

    # By effect type
    by_effect_type: Dict[str, Dict[str, float]]

    # By difficulty
    by_difficulty: Dict[str, Dict[str, float]]

    # By therapeutic area
    by_therapeutic_area: Dict[str, Dict[str, float]]

    # Comparison to baseline
    baseline_comparison: Optional[Dict[str, float]]


def load_ground_truth(gt_path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Load ground truth from file or external_validation_dataset"""
    # Try consolidated JSONL first
    if gt_path and gt_path.exists():
        results = {}
        with open(gt_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    key = data.get("pmc_id") or data.get("trial")
                    results[key] = data
        return results

    # Try default path
    default_path = GROUND_TRUTH_DIR / "consolidated.jsonl"
    if default_path.exists():
        return load_ground_truth(default_path)

    # Fall back to external_validation_dataset
    results = {}
    for trial in ALL_EXTERNAL_VALIDATION_TRIALS:
        key = trial.pmc_id if trial.pmc_id else trial.trial_name

        effects = []
        extractions = trial.consensus if trial.consensus else trial.extractor_a
        for ext in extractions:
            effects.append({
                "type": ext.effect_type,
                "value": ext.effect_size,
                "ci_lower": ext.ci_lower,
                "ci_upper": ext.ci_upper,
            })

        results[key] = {
            "trial": trial.trial_name,
            "pmc_id": trial.pmc_id,
            "nct_id": trial.nct_number,
            "therapeutic_area": trial.therapeutic_area,
            "difficulty": trial.difficulty.value,
            "ground_truth": effects,
            "source_text": trial.source_text,
        }

    return results


def load_baseline(version: str = "latest") -> Optional[Dict[str, float]]:
    """Load baseline metrics for comparison"""
    if version == "latest":
        # Find most recent baseline
        baselines = list(BASELINES_DIR.glob("v*.json"))
        if not baselines:
            return None
        latest = sorted(baselines)[-1]
    else:
        latest = BASELINES_DIR / f"v{version}_baseline.json"

    if not latest.exists():
        return None

    with open(latest, "r") as f:
        data = json.load(f)
        return data.get("metrics", {})


def extract_from_text(text: str) -> List[Extraction]:
    """Run extraction on text"""
    if not HAS_EXTRACTOR or not text:
        return []

    extractor = EnhancedExtractor()
    return extractor.extract(text)


def extract_from_pdf(pdf_path: Path) -> List[Extraction]:
    """Extract effects from PDF"""
    if not HAS_PDF_PARSER or not pdf_path.exists():
        return []

    try:
        text = extract_text_from_pdf(str(pdf_path))
        if text:
            return extract_from_text(text)
    except Exception:
        pass

    return []


def match_effects(
    expected: List[Dict[str, Any]],
    extracted: List[Extraction],
    tolerance: float = 0.05
) -> Tuple[List[EffectMatch], List[Extraction]]:
    """
    Match expected effects to extractions.

    Returns:
        - List of match results
        - List of unmatched (extra) extractions
    """
    matches = []
    matched_extractions = set()

    for exp in expected:
        exp_type = exp.get("type", "")
        exp_val = exp.get("value")
        exp_ci_lower = exp.get("ci_lower")
        exp_ci_upper = exp.get("ci_upper")

        if exp_val is None:
            continue

        best_match = None
        best_status = "missed"
        best_ext = None

        for ext in extracted:
            if id(ext) in matched_extractions:
                continue

            # Get extraction values
            ext_type = ext.effect_type.value if hasattr(ext.effect_type, "value") else str(ext.effect_type)
            ext_val = ext.point_estimate

            # Type check
            if ext_type.upper() != exp_type.upper():
                continue

            # Value check
            if ext_val is None:
                continue

            try:
                val_error = abs(ext_val - exp_val) / max(abs(exp_val), 0.001)
                if val_error > tolerance:
                    continue

                # CI check
                has_ci = ext.ci is not None and ext.ci.lower is not None and ext.ci.upper is not None
                ext_ci_lower = ext.ci.lower if ext.ci else None
                ext_ci_upper = ext.ci.upper if ext.ci else None

                ci_match = False
                if has_ci and exp_ci_lower and exp_ci_upper:
                    ci_lower_err = abs(ext_ci_lower - exp_ci_lower) / max(abs(exp_ci_lower), 0.001)
                    ci_upper_err = abs(ext_ci_upper - exp_ci_upper) / max(abs(exp_ci_upper), 0.001)
                    ci_match = ci_lower_err <= tolerance and ci_upper_err <= tolerance

                if ci_match:
                    status = "exact"
                elif has_ci:
                    status = "value_only"  # Value matches but CI differs
                else:
                    status = "value_only"  # No CI extracted

                # Update best match
                if best_status == "missed" or (status == "exact" and best_status != "exact"):
                    best_match = ext
                    best_status = status
                    best_ext = ext

            except (TypeError, ZeroDivisionError):
                continue

        # Create match record
        if best_ext:
            matched_extractions.add(id(best_ext))
            ext_ci_lower = best_ext.ci.lower if best_ext.ci else None
            ext_ci_upper = best_ext.ci.upper if best_ext.ci else None
            has_complete_ci = ext_ci_lower is not None and ext_ci_upper is not None

            matches.append(EffectMatch(
                expected_type=exp_type,
                expected_value=exp_val,
                expected_ci_lower=exp_ci_lower,
                expected_ci_upper=exp_ci_upper,
                extracted_type=best_ext.effect_type.value,
                extracted_value=best_ext.point_estimate,
                extracted_ci_lower=ext_ci_lower,
                extracted_ci_upper=ext_ci_upper,
                match_status=best_status,
                has_complete_ci=has_complete_ci,
                value_error=abs(best_ext.point_estimate - exp_val) / max(abs(exp_val), 0.001) if exp_val else None,
                ci_lower_error=abs(ext_ci_lower - exp_ci_lower) / max(abs(exp_ci_lower), 0.001) if ext_ci_lower and exp_ci_lower else None,
                ci_upper_error=abs(ext_ci_upper - exp_ci_upper) / max(abs(exp_ci_upper), 0.001) if ext_ci_upper and exp_ci_upper else None,
            ))
        else:
            matches.append(EffectMatch(
                expected_type=exp_type,
                expected_value=exp_val,
                expected_ci_lower=exp_ci_lower,
                expected_ci_upper=exp_ci_upper,
                extracted_type=None,
                extracted_value=None,
                extracted_ci_lower=None,
                extracted_ci_upper=None,
                match_status="missed",
                has_complete_ci=False,
                value_error=None,
                ci_lower_error=None,
                ci_upper_error=None,
            ))

    # Find extra extractions
    extra = [ext for ext in extracted if id(ext) not in matched_extractions]

    return matches, extra


def validate_trial(
    trial_data: Dict[str, Any],
    pdf_dir: Optional[Path] = None
) -> TrialValidation:
    """Validate extraction for a single trial"""
    trial_name = trial_data.get("trial", "")
    pmc_id = trial_data.get("pmc_id")
    ground_truth = trial_data.get("ground_truth", [])

    # Get text to extract from
    text = trial_data.get("source_text", "")

    # Try PDF if available
    if pdf_dir and pmc_id:
        pdf_path = pdf_dir / f"{pmc_id}.pdf"
        if pdf_path.exists():
            extractions = extract_from_pdf(pdf_path)
        else:
            extractions = extract_from_text(text)
    else:
        extractions = extract_from_text(text)

    # Match effects
    matches, extra = match_effects(ground_truth, extractions)

    # Count by type
    by_type = {}
    for m in matches:
        et = m.expected_type
        if et not in by_type:
            by_type[et] = {"expected": 0, "matched": 0, "with_ci": 0}
        by_type[et]["expected"] += 1
        if m.match_status != "missed":
            by_type[et]["matched"] += 1
        if m.has_complete_ci:
            by_type[et]["with_ci"] += 1

    matched_count = len([m for m in matches if m.match_status != "missed"])
    with_ci_count = len([m for m in matches if m.has_complete_ci])

    return TrialValidation(
        trial_name=trial_name,
        pmc_id=pmc_id,
        nct_id=trial_data.get("nct_id"),
        therapeutic_area=trial_data.get("therapeutic_area", ""),
        difficulty=trial_data.get("difficulty", ""),
        expected_effects=len(ground_truth),
        extracted_effects=len(extractions),
        matched_effects=matched_count,
        missed_effects=len(matches) - matched_count,
        with_complete_ci=with_ci_count,
        extra_effects=len(extra),
        matches=[asdict(m) for m in matches],
        by_type=by_type,
    )


def run_validation(
    ground_truth: Dict[str, Dict[str, Any]],
    pdf_dir: Optional[Path] = None,
    verbose: bool = False
) -> Tuple[List[TrialValidation], ValidationSummary]:
    """Run validation on all trials"""
    validations = []

    for key, trial_data in ground_truth.items():
        if verbose:
            print(f"Validating: {trial_data.get('trial', key)}...")

        validation = validate_trial(trial_data, pdf_dir)
        validations.append(validation)

        if verbose:
            print(f"  Expected: {validation.expected_effects}, "
                  f"Matched: {validation.matched_effects}, "
                  f"CI: {validation.with_complete_ci}")

    # Calculate summary
    total_expected = sum(v.expected_effects for v in validations)
    total_extracted = sum(v.extracted_effects for v in validations)
    total_matched = sum(v.matched_effects for v in validations)
    total_missed = sum(v.missed_effects for v in validations)
    total_with_ci = sum(v.with_complete_ci for v in validations)
    pdfs_with_extractions = len([v for v in validations if v.extracted_effects > 0])

    # By effect type
    by_effect_type = {}
    for v in validations:
        for et, counts in v.by_type.items():
            if et not in by_effect_type:
                by_effect_type[et] = {"expected": 0, "matched": 0, "with_ci": 0}
            by_effect_type[et]["expected"] += counts["expected"]
            by_effect_type[et]["matched"] += counts["matched"]
            by_effect_type[et]["with_ci"] += counts["with_ci"]

    # Calculate rates per type
    for et, counts in by_effect_type.items():
        counts["recall"] = counts["matched"] / counts["expected"] if counts["expected"] > 0 else 0
        counts["ci_rate"] = counts["with_ci"] / counts["matched"] if counts["matched"] > 0 else 0

    # By difficulty
    by_difficulty = {}
    for diff in ["easy", "moderate", "hard", "very_hard"]:
        trials = [v for v in validations if v.difficulty == diff]
        if trials:
            exp = sum(v.expected_effects for v in trials)
            matched = sum(v.matched_effects for v in trials)
            ci = sum(v.with_complete_ci for v in trials)
            by_difficulty[diff] = {
                "trials": len(trials),
                "expected": exp,
                "matched": matched,
                "with_ci": ci,
                "recall": matched / exp if exp > 0 else 0,
                "ci_rate": ci / matched if matched > 0 else 0,
            }

    # By therapeutic area
    by_area = {}
    for v in validations:
        area = v.therapeutic_area.split(" - ")[0] if v.therapeutic_area else "Unknown"
        if area not in by_area:
            by_area[area] = {"trials": 0, "expected": 0, "matched": 0, "with_ci": 0}
        by_area[area]["trials"] += 1
        by_area[area]["expected"] += v.expected_effects
        by_area[area]["matched"] += v.matched_effects
        by_area[area]["with_ci"] += v.with_complete_ci

    for area, counts in by_area.items():
        counts["recall"] = counts["matched"] / counts["expected"] if counts["expected"] > 0 else 0
        counts["ci_rate"] = counts["with_ci"] / counts["matched"] if counts["matched"] > 0 else 0

    # Load baseline for comparison
    baseline = load_baseline()
    baseline_comparison = None
    if baseline:
        current_ci_completion = total_with_ci / total_matched if total_matched > 0 else 0
        baseline_comparison = {
            "ci_completion_delta": current_ci_completion - baseline.get("ci_completion", 0),
            "extraction_rate_delta": (pdfs_with_extractions / len(validations) if validations else 0) - baseline.get("extraction_rate", 0),
        }

    summary = ValidationSummary(
        version="4.3.0",
        timestamp=datetime.now().isoformat(),
        corpus_size=len(ground_truth),
        pdfs_processed=len(validations),
        pdfs_with_extractions=pdfs_with_extractions,
        total_expected=total_expected,
        total_extracted=total_extracted,
        total_matched=total_matched,
        total_missed=total_missed,
        total_with_ci=total_with_ci,
        extraction_rate=pdfs_with_extractions / len(validations) if validations else 0,
        recall=total_matched / total_expected if total_expected > 0 else 0,
        precision=total_matched / total_extracted if total_extracted > 0 else 0,
        ci_completion=total_with_ci / total_matched if total_matched > 0 else 0,
        by_effect_type=by_effect_type,
        by_difficulty=by_difficulty,
        by_therapeutic_area=by_area,
        baseline_comparison=baseline_comparison,
    )

    return validations, summary


def save_results(
    validations: List[TrialValidation],
    summary: ValidationSummary,
    output_path: Path
):
    """Save validation results"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "summary": asdict(summary),
        "trials": [asdict(v) for v in validations],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved results to: {output_path}")


def print_summary(summary: ValidationSummary):
    """Print validation summary"""
    print("\n" + "=" * 70)
    print("UNIFIED VALIDATION RESULTS - RCT Extractor v4.3")
    print("=" * 70)

    print(f"\nCorpus: {summary.corpus_size} trials")
    print(f"Processed: {summary.pdfs_processed}")
    print(f"With extractions: {summary.pdfs_with_extractions} ({summary.extraction_rate:.1%})")

    print(f"\n--- Effect Metrics ---")
    print(f"Expected: {summary.total_expected}")
    print(f"Extracted: {summary.total_extracted}")
    print(f"Matched: {summary.total_matched}")
    print(f"With CI: {summary.total_with_ci}")

    print(f"\n--- Key Rates ---")
    print(f"Recall: {summary.recall:.1%}")
    print(f"Precision: {summary.precision:.1%}")
    print(f"CI Completion: {summary.ci_completion:.1%}")

    # Target comparison
    print(f"\n--- Target Comparison ---")
    print(f"CI Completion: {summary.ci_completion:.1%} (target: >80%)")
    print(f"Extraction Rate: {summary.extraction_rate:.1%} (target: >70%)")

    # By effect type
    print(f"\n--- By Effect Type ---")
    for et, rates in sorted(summary.by_effect_type.items(), key=lambda x: -x[1].get("expected", 0)):
        print(f"  {et}: recall={rates.get('recall', 0):.1%}, CI={rates.get('ci_rate', 0):.1%} "
              f"(n={rates.get('expected', 0)})")

    # Baseline comparison
    if summary.baseline_comparison:
        print(f"\n--- vs Baseline ---")
        delta_ci = summary.baseline_comparison.get("ci_completion_delta", 0)
        delta_rate = summary.baseline_comparison.get("extraction_rate_delta", 0)
        print(f"CI Completion: {'+' if delta_ci >= 0 else ''}{delta_ci:.1%}")
        print(f"Extraction Rate: {'+' if delta_rate >= 0 else ''}{delta_rate:.1%}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Run unified validation pipeline for RCT Extractor"
    )
    parser.add_argument(
        "--pdfs", type=Path,
        help="Directory containing PDFs to validate"
    )
    parser.add_argument(
        "--ground-truth", type=Path,
        help="Ground truth JSONL file"
    )
    parser.add_argument(
        "--output", type=Path,
        default=OUTPUT_DIR / "validation_v4.3.json",
        help="Output file path"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if not HAS_EXTRACTOR:
        print("Error: Enhanced extractor not available")
        sys.exit(1)

    # Load ground truth
    print("Loading ground truth...")
    ground_truth = load_ground_truth(args.ground_truth)
    print(f"Loaded {len(ground_truth)} trials")

    # Run validation
    print("\nRunning validation...")
    validations, summary = run_validation(ground_truth, args.pdfs, args.verbose)

    # Print summary
    print_summary(summary)

    # Save results
    save_results(validations, summary, args.output)

    # Return exit code based on targets
    if summary.ci_completion >= 0.80 and summary.extraction_rate >= 0.70:
        print("\n[PASS] All targets met!")
        sys.exit(0)
    else:
        print("\n[FAIL] Targets not met")
        sys.exit(1)


if __name__ == "__main__":
    main()
