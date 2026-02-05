#!/usr/bin/env python3
"""
Analyze Extraction Failures Against Ground Truth
==================================================

For each PDF with ground truth:
1. Run extraction
2. Compare to ground truth
3. Log: missed effects, wrong values, missing CIs
4. Extract the source text context around missed effects

Output: output/extraction_failures.json

Usage:
    python scripts/analyze_extraction_failures.py
    python scripts/analyze_extraction_failures.py --pdf-dir test_pdfs/validated_rcts
    python scripts/analyze_extraction_failures.py --verbose
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
    ExternalValidationTrial,
)

# Try to import extractor
try:
    from src.core.enhanced_extractor_v3 import EnhancedExtractor, EffectType
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


@dataclass
class ExtractionFailure:
    """A single extraction failure"""
    trial_name: str
    pdf: str
    failure_type: str  # "missed", "wrong_value", "missing_ci", "extra"
    expected_type: str
    expected_value: float
    expected_ci_lower: Optional[float]
    expected_ci_upper: Optional[float]
    extracted_value: Optional[float]
    extracted_ci_lower: Optional[float]
    extracted_ci_upper: Optional[float]
    source_text_context: str  # 200 chars around expected location
    pattern_matched: str = ""
    notes: str = ""


@dataclass
class TrialAnalysis:
    """Analysis results for a single trial"""
    trial_name: str
    pdf: str
    pmc_id: Optional[str]
    nct_id: Optional[str]
    therapeutic_area: str
    difficulty: str

    # Counts
    expected_count: int
    extracted_count: int
    matched_count: int
    missed_count: int
    wrong_value_count: int
    missing_ci_count: int
    extra_count: int

    # Details
    failures: List[ExtractionFailure]

    # Metrics
    recall: float
    precision: float
    ci_completion: float


def load_ground_truth() -> Dict[str, Dict[str, Any]]:
    """Load consolidated ground truth"""
    gt_path = GROUND_TRUTH_DIR / "consolidated.jsonl"

    if gt_path.exists():
        results = {}
        with open(gt_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    key = data.get("pmc_id") or data.get("trial")
                    results[key] = data
        return results

    # Fall back to external validation directly
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
                "source_text": ext.source_text,
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


def match_effect(
    expected: Dict[str, Any],
    extractions: List[Any],
    tolerance: float = 0.05
) -> Tuple[Optional[Any], str]:
    """
    Match expected effect to an extraction.

    Returns:
        - Matched extraction (or None)
        - Match status: "exact", "value_only", "type_match", "none"
    """
    exp_type = expected.get("type", "")
    exp_val = expected.get("value")
    exp_ci_lower = expected.get("ci_lower")
    exp_ci_upper = expected.get("ci_upper")

    if exp_val is None:
        return None, "none"

    for ext in extractions:
        # Get extraction type
        if hasattr(ext, "effect_type"):
            ext_type = ext.effect_type.value if hasattr(ext.effect_type, "value") else str(ext.effect_type)
        else:
            ext_type = str(ext.get("effect_type", ""))

        # Get extraction value
        if hasattr(ext, "point_estimate"):
            ext_val = ext.point_estimate
        else:
            ext_val = ext.get("value")

        # Type match
        if ext_type.upper() != exp_type.upper():
            continue

        # Value match (within tolerance)
        if ext_val is None:
            continue

        try:
            if abs(ext_val - exp_val) / max(abs(exp_val), 0.001) <= tolerance:
                # Check CI
                if hasattr(ext, "ci") and ext.ci:
                    ext_ci_lower = ext.ci.lower
                    ext_ci_upper = ext.ci.upper
                else:
                    ext_ci_lower = ext.get("ci_lower")
                    ext_ci_upper = ext.get("ci_upper")

                if exp_ci_lower and exp_ci_upper:
                    if ext_ci_lower and ext_ci_upper:
                        ci_match = (
                            abs(ext_ci_lower - exp_ci_lower) / max(abs(exp_ci_lower), 0.001) <= tolerance and
                            abs(ext_ci_upper - exp_ci_upper) / max(abs(exp_ci_upper), 0.001) <= tolerance
                        )
                        if ci_match:
                            return ext, "exact"
                        else:
                            return ext, "value_only"
                    else:
                        return ext, "value_only"
                else:
                    return ext, "exact"
        except (TypeError, ZeroDivisionError):
            continue

    return None, "none"


def analyze_trial(
    trial_data: Dict[str, Any],
    extractions: List[Any],
    verbose: bool = False
) -> TrialAnalysis:
    """Analyze extractions for a single trial"""
    trial_name = trial_data.get("trial", "")
    ground_truth = trial_data.get("ground_truth", [])
    source_text = trial_data.get("source_text", "")

    failures = []
    matched = []
    missing_ci = []

    # Match each expected effect
    for expected in ground_truth:
        ext, status = match_effect(expected, extractions)

        if status == "none":
            # Missed
            failures.append(ExtractionFailure(
                trial_name=trial_name,
                pdf=trial_data.get("pmc_id", trial_name),
                failure_type="missed",
                expected_type=expected.get("type", ""),
                expected_value=expected.get("value"),
                expected_ci_lower=expected.get("ci_lower"),
                expected_ci_upper=expected.get("ci_upper"),
                extracted_value=None,
                extracted_ci_lower=None,
                extracted_ci_upper=None,
                source_text_context=expected.get("source_text", "")[:200],
            ))
        elif status == "value_only":
            # CI missing
            missing_ci.append(expected)
            matched.append(ext)

            # Get extracted CI values
            if hasattr(ext, "ci") and ext.ci:
                ext_ci_lower = ext.ci.lower
                ext_ci_upper = ext.ci.upper
            else:
                ext_ci_lower = getattr(ext, "ci_lower", None)
                ext_ci_upper = getattr(ext, "ci_upper", None)

            failures.append(ExtractionFailure(
                trial_name=trial_name,
                pdf=trial_data.get("pmc_id", trial_name),
                failure_type="missing_ci",
                expected_type=expected.get("type", ""),
                expected_value=expected.get("value"),
                expected_ci_lower=expected.get("ci_lower"),
                expected_ci_upper=expected.get("ci_upper"),
                extracted_value=getattr(ext, "point_estimate", None) or ext.get("value"),
                extracted_ci_lower=ext_ci_lower,
                extracted_ci_upper=ext_ci_upper,
                source_text_context=expected.get("source_text", "")[:200],
            ))
        else:
            # Exact match
            matched.append(ext)

    # Check for extra extractions
    matched_set = set(id(e) for e in matched)
    extra = [e for e in extractions if id(e) not in matched_set]

    # Calculate metrics
    expected_count = len(ground_truth)
    extracted_count = len(extractions)
    matched_count = len([f for f in failures if f.failure_type != "missed"]) + len(matched) - len(missing_ci)
    missed_count = len([f for f in failures if f.failure_type == "missed"])
    ci_missing_count = len([f for f in failures if f.failure_type == "missing_ci"])

    recall = matched_count / expected_count if expected_count > 0 else 0
    precision = matched_count / extracted_count if extracted_count > 0 else 0

    # CI completion: of matched effects, how many have complete CI?
    effects_with_ci = matched_count - ci_missing_count
    ci_completion = effects_with_ci / expected_count if expected_count > 0 else 0

    return TrialAnalysis(
        trial_name=trial_name,
        pdf=trial_data.get("pmc_id", trial_name),
        pmc_id=trial_data.get("pmc_id"),
        nct_id=trial_data.get("nct_id"),
        therapeutic_area=trial_data.get("therapeutic_area", ""),
        difficulty=trial_data.get("difficulty", ""),
        expected_count=expected_count,
        extracted_count=extracted_count,
        matched_count=matched_count,
        missed_count=missed_count,
        wrong_value_count=0,  # TODO: implement value mismatch detection
        missing_ci_count=ci_missing_count,
        extra_count=len(extra),
        failures=failures,
        recall=recall,
        precision=precision,
        ci_completion=ci_completion,
    )


def run_text_extraction(text: str) -> List[Any]:
    """Run extraction on text"""
    if not HAS_EXTRACTOR:
        return []

    extractor = EnhancedExtractor()
    return extractor.extract(text)


def analyze_all(
    ground_truth: Dict[str, Dict[str, Any]],
    pdf_dir: Optional[Path] = None,
    verbose: bool = False
) -> List[TrialAnalysis]:
    """Analyze all trials"""
    results = []

    for key, trial_data in ground_truth.items():
        if verbose:
            print(f"Analyzing: {trial_data.get('trial', key)}...")

        # Get text to extract from
        text = trial_data.get("source_text", "")

        # If PDF dir provided and we have a PMC ID, try to load PDF
        if pdf_dir and trial_data.get("pmc_id"):
            pdf_path = pdf_dir / f"{trial_data['pmc_id']}.pdf"
            if pdf_path.exists() and HAS_PDF_PARSER:
                try:
                    pdf_text = extract_text_from_pdf(str(pdf_path))
                    if pdf_text:
                        text = pdf_text
                except Exception as e:
                    if verbose:
                        print(f"  Warning: Could not read PDF: {e}")

        if not text:
            if verbose:
                print(f"  Skipping: no text available")
            continue

        # Run extraction
        extractions = run_text_extraction(text)

        # Analyze
        analysis = analyze_trial(trial_data, extractions, verbose)
        results.append(analysis)

        if verbose:
            print(f"  Expected: {analysis.expected_count}, "
                  f"Extracted: {analysis.extracted_count}, "
                  f"Missed: {analysis.missed_count}, "
                  f"CI Missing: {analysis.missing_ci_count}")

    return results


def save_results(results: List[TrialAnalysis], output_path: Path):
    """Save analysis results"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Calculate aggregate metrics
    total_expected = sum(r.expected_count for r in results)
    total_extracted = sum(r.extracted_count for r in results)
    total_matched = sum(r.matched_count for r in results)
    total_missed = sum(r.missed_count for r in results)
    total_missing_ci = sum(r.missing_ci_count for r in results)

    all_failures = []
    for r in results:
        for f in r.failures:
            all_failures.append(asdict(f))

    # Group failures by type
    failures_by_type = {}
    for f in all_failures:
        ft = f["failure_type"]
        if ft not in failures_by_type:
            failures_by_type[ft] = []
        failures_by_type[ft].append(f)

    # Group failures by effect type
    failures_by_effect = {}
    for f in all_failures:
        et = f["expected_type"]
        if et not in failures_by_effect:
            failures_by_effect[et] = {"missed": 0, "missing_ci": 0}
        failures_by_effect[et][f["failure_type"]] = failures_by_effect[et].get(f["failure_type"], 0) + 1

    data = {
        "version": "4.3.0",
        "generated": datetime.now().isoformat(),
        "summary": {
            "trials_analyzed": len(results),
            "total_expected": total_expected,
            "total_extracted": total_extracted,
            "total_matched": total_matched,
            "total_missed": total_missed,
            "total_missing_ci": total_missing_ci,
            "overall_recall": total_matched / total_expected if total_expected > 0 else 0,
            "overall_precision": total_matched / total_extracted if total_extracted > 0 else 0,
            "ci_completion": (total_matched - total_missing_ci) / total_expected if total_expected > 0 else 0,
        },
        "failures_by_type": {ft: len(failures) for ft, failures in failures_by_type.items()},
        "failures_by_effect_type": failures_by_effect,
        "trials": [asdict(r) for r in results],
        "all_failures": all_failures,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved results to: {output_path}")


def print_summary(results: List[TrialAnalysis]):
    """Print analysis summary"""
    print("\n" + "=" * 70)
    print("EXTRACTION FAILURE ANALYSIS")
    print("=" * 70)

    total_expected = sum(r.expected_count for r in results)
    total_matched = sum(r.matched_count for r in results)
    total_missed = sum(r.missed_count for r in results)
    total_missing_ci = sum(r.missing_ci_count for r in results)

    print(f"\nTrials analyzed: {len(results)}")
    print(f"Expected effects: {total_expected}")
    print(f"Matched effects: {total_matched}")
    print(f"Missed effects: {total_missed}")
    print(f"Missing CI: {total_missing_ci}")

    recall = total_matched / total_expected if total_expected > 0 else 0
    ci_completion = (total_matched - total_missing_ci) / total_expected if total_expected > 0 else 0

    print(f"\nOverall recall: {recall:.1%}")
    print(f"CI completion: {ci_completion:.1%}")

    # By effect type
    print("\nBy effect type:")
    by_type = {}
    for r in results:
        for f in r.failures:
            et = f.expected_type
            if et not in by_type:
                by_type[et] = {"missed": 0, "missing_ci": 0, "total": 0}
            by_type[et][f.failure_type] = by_type[et].get(f.failure_type, 0) + 1

    # Add totals from ground truth
    for r in results:
        # This is approximate - would need GT grouped by type
        pass

    for et, counts in sorted(by_type.items()):
        print(f"  {et}: missed={counts.get('missed', 0)}, missing_ci={counts.get('missing_ci', 0)}")

    # Top failure patterns
    print("\nTop missed effects (sample):")
    missed = [f for r in results for f in r.failures if f.failure_type == "missed"]
    for f in missed[:10]:
        print(f"  {f.trial_name}: {f.expected_type} {f.expected_value}")
        if f.source_text_context:
            print(f"    Text: '{f.source_text_context[:80]}...'")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze extraction failures against ground truth"
    )
    parser.add_argument(
        "--pdf-dir", type=Path,
        help="Directory containing PDFs to extract from"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--output", type=Path,
        default=OUTPUT_DIR / "extraction_failures.json",
        help="Output file path"
    )

    args = parser.parse_args()

    if not HAS_EXTRACTOR:
        print("Error: Enhanced extractor not available")
        print("Make sure src/core/enhanced_extractor_v3.py exists")
        sys.exit(1)

    # Load ground truth
    print("Loading ground truth...")
    ground_truth = load_ground_truth()
    print(f"Loaded {len(ground_truth)} trials")

    # Run analysis
    print("\nAnalyzing extractions...")
    results = analyze_all(ground_truth, args.pdf_dir, args.verbose)

    # Print summary
    print_summary(results)

    # Save results
    save_results(results, args.output)


if __name__ == "__main__":
    main()
