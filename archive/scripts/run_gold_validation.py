#!/usr/bin/env python3
"""
Gold Standard Validation Runner
=================================

Runs the RCT extractor against gold standard annotated PDFs and computes
sensitivity, precision, F1, and CI completion metrics.

Usage:
    python scripts/run_gold_validation.py
    python scripts/run_gold_validation.py --split development
    python scripts/run_gold_validation.py --split held_out
    python scripts/run_gold_validation.py --output output/validation_results.json
"""

import json
import sys
import os
import hashlib
import time
import argparse
import math
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class MatchResult:
    """Result of matching an expected effect to extractions."""
    expected_type: str
    expected_value: float
    expected_ci_lower: Optional[float]
    expected_ci_upper: Optional[float]
    expected_source: str
    matched: bool
    matched_value: Optional[float] = None
    matched_has_ci: bool = False
    matched_ci_lower: Optional[float] = None
    matched_ci_upper: Optional[float] = None
    value_error: Optional[float] = None
    ci_correct: bool = False


@dataclass
class PDFValidationResult:
    """Validation result for a single PDF."""
    pdf_file: str
    num_expected: int
    num_extracted: int
    num_matched: int
    num_with_ci_expected: int
    num_with_ci_matched: int
    sensitivity: float
    precision: float
    f1: float
    ci_completion: float
    false_positives: int
    match_details: List[Dict[str, Any]] = field(default_factory=list)
    extraction_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)


@dataclass
class ValidationSummary:
    """Summary across all PDFs."""
    split: str
    num_pdfs: int
    total_expected: int
    total_extracted: int
    total_matched: int
    total_ci_expected: int
    total_ci_matched: int
    sensitivity: float
    precision: float
    f1: float
    ci_completion: float
    sensitivity_ci: Tuple[float, float] = (0.0, 0.0)
    precision_ci: Tuple[float, float] = (0.0, 0.0)
    ci_completion_ci: Tuple[float, float] = (0.0, 0.0)
    per_type_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    per_pdf_results: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = ""
    extractor_version: str = "5.1.0"


def wilson_ci(successes: int, trials: int, alpha: float = 0.05) -> Tuple[float, float]:
    """Wilson score confidence interval for a proportion."""
    if trials == 0:
        return (0.0, 0.0)
    z = 1.96  # 95% CI
    p_hat = successes / trials
    denom = 1 + z**2 / trials
    center = (p_hat + z**2 / (2 * trials)) / denom
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * trials)) / trials) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def effect_type_matches(expected_type: str, extracted_type: str) -> bool:
    """Check if effect types match (with aliases)."""
    aliases = {
        "RD": "ARD",
        "WMD": "MD",
        "ARR": "ARD",
    }
    et = aliases.get(expected_type, expected_type)
    xt = aliases.get(extracted_type, extracted_type)
    return et == xt


def values_match(expected: float, extracted: float, effect_type: str, tolerance: float = 0.05) -> bool:
    """Check if two values match within tolerance."""
    if expected == 0 and extracted == 0:
        return True
    # For ratios, use relative tolerance
    if effect_type in ("HR", "OR", "RR", "IRR"):
        if expected == 0:
            return abs(extracted) < tolerance
        return abs(extracted - expected) / abs(expected) <= tolerance
    # For differences, use absolute tolerance scaled by magnitude
    denom = max(abs(expected), abs(extracted), 1.0)
    return abs(extracted - expected) / denom <= tolerance


def match_extractions(
    expected: List[Dict[str, Any]],
    extracted: List[Any],
    tolerance: float = 0.05
) -> Tuple[List[MatchResult], int]:
    """
    Match expected effects to extracted effects.

    Returns:
        Tuple of (match_results, false_positive_count)
    """
    results = []
    used_extracted = set()

    for exp in expected:
        exp_type = exp.get("effect_type", "")
        exp_value = exp.get("point_estimate", 0.0)
        exp_ci_lower = exp.get("ci_lower")
        exp_ci_upper = exp.get("ci_upper")
        exp_source = exp.get("source_type", "unknown")

        best_match = None
        best_error = float('inf')

        for idx, ext in enumerate(extracted):
            if idx in used_extracted:
                continue

            # Get extracted type
            ext_type = ext.effect_type.value if hasattr(ext.effect_type, 'value') else str(ext.effect_type)

            if not effect_type_matches(exp_type, ext_type):
                continue

            ext_value = ext.point_estimate
            if values_match(exp_value, ext_value, exp_type, tolerance):
                error = abs(ext_value - exp_value)
                if error < best_error:
                    best_error = error
                    best_match = (idx, ext)

        if best_match is not None:
            idx, ext = best_match
            used_extracted.add(idx)

            # Check CI
            ext_has_ci = ext.ci is not None and ext.has_complete_ci
            ci_correct = False
            ext_ci_lower = None
            ext_ci_upper = None

            if ext_has_ci and exp_ci_lower is not None and exp_ci_upper is not None:
                ext_ci_lower = ext.ci.lower
                ext_ci_upper = ext.ci.upper
                ci_correct = (
                    values_match(exp_ci_lower, ext_ci_lower, exp_type, tolerance) and
                    values_match(exp_ci_upper, ext_ci_upper, exp_type, tolerance)
                )

            results.append(MatchResult(
                expected_type=exp_type,
                expected_value=exp_value,
                expected_ci_lower=exp_ci_lower,
                expected_ci_upper=exp_ci_upper,
                expected_source=exp_source,
                matched=True,
                matched_value=ext.point_estimate,
                matched_has_ci=ext_has_ci,
                matched_ci_lower=ext_ci_lower,
                matched_ci_upper=ext_ci_upper,
                value_error=best_error,
                ci_correct=ci_correct,
            ))
        else:
            results.append(MatchResult(
                expected_type=exp_type,
                expected_value=exp_value,
                expected_ci_lower=exp_ci_lower,
                expected_ci_upper=exp_ci_upper,
                expected_source=exp_source,
                matched=False,
            ))

    false_positives = len(extracted) - len(used_extracted)
    return results, false_positives


def load_gold_annotations(filepath: str) -> List[Dict[str, Any]]:
    """Load gold standard annotations from JSONL file."""
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
    """Resolve a PDF filename to its full path."""
    candidates = [
        project_root / "test_pdfs" / source / pdf_file,
        project_root / "test_pdfs" / "open_access_rcts" / pdf_file,
        project_root / "test_pdfs" / "oa_rct_corpus_v2" / pdf_file,
        project_root / "test_pdfs" / "oa_rct_corpus" / pdf_file,
    ]
    # Also check real_pdfs subdirectories
    for subdir in ["cardiology", "respiratory", "diabetes", "oncology", "infectious",
                   "neurology", "rheumatology"]:
        candidates.append(project_root / "test_pdfs" / "real_pdfs" / subdir / pdf_file)

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def validate_pdf(
    pdf_path: str,
    gold_annotations: List[Dict[str, Any]],
    pipeline,
    tolerance: float = 0.05
) -> PDFValidationResult:
    """Run extraction on a PDF and compare to gold standard."""
    pdf_file = os.path.basename(pdf_path)
    errors = []

    # Run extraction
    start_time = time.time()
    try:
        result = pipeline.extract_from_pdf(pdf_path)
        extracted = result.effect_estimates
    except Exception as e:
        errors.append(f"Extraction failed: {e}")
        extracted = []
    extraction_time = time.time() - start_time

    # Match against gold standard
    match_results, false_positives = match_extractions(
        gold_annotations, extracted, tolerance
    )

    # Compute metrics
    num_expected = len(gold_annotations)
    num_extracted = len(extracted)
    num_matched = sum(1 for r in match_results if r.matched)

    # CI metrics: only count expected effects that have CI annotated
    num_with_ci_expected = sum(
        1 for r in match_results
        if r.expected_ci_lower is not None and r.expected_ci_upper is not None
    )
    num_with_ci_matched = sum(
        1 for r in match_results
        if r.matched and r.matched_has_ci
        and r.expected_ci_lower is not None and r.expected_ci_upper is not None
    )

    sensitivity = num_matched / num_expected if num_expected > 0 else 0.0
    precision = num_matched / num_extracted if num_extracted > 0 else 0.0
    f1 = (2 * sensitivity * precision / (sensitivity + precision)
          if (sensitivity + precision) > 0 else 0.0)
    ci_completion = (num_with_ci_matched / num_with_ci_expected
                    if num_with_ci_expected > 0 else 0.0)

    return PDFValidationResult(
        pdf_file=pdf_file,
        num_expected=num_expected,
        num_extracted=num_extracted,
        num_matched=num_matched,
        num_with_ci_expected=num_with_ci_expected,
        num_with_ci_matched=num_with_ci_matched,
        sensitivity=sensitivity,
        precision=precision,
        f1=f1,
        ci_completion=ci_completion,
        false_positives=false_positives,
        match_details=[{
            "type": r.expected_type,
            "expected_value": r.expected_value,
            "matched": r.matched,
            "matched_value": r.matched_value,
            "matched_has_ci": r.matched_has_ci,
            "source": r.expected_source,
        } for r in match_results],
        extraction_time_seconds=extraction_time,
        errors=errors,
    )


def run_validation(
    split: str = "development",
    output_path: Optional[str] = None,
    tolerance: float = 0.05,
) -> ValidationSummary:
    """
    Run full validation on a split.

    Args:
        split: "development" or "held_out"
        output_path: Path to write JSON results
        tolerance: Matching tolerance for effect values
    """
    from src.core.pdf_extraction_pipeline import PDFExtractionPipeline

    proj_root = Path(__file__).parent.parent

    # Load split definition
    split_path = proj_root / "data" / "gold_standard_split.json"
    with open(split_path, 'r') as f:
        split_data = json.load(f)

    if split not in split_data:
        print(f"Invalid split: {split}. Available: {list(split_data.keys())}")
        sys.exit(1)

    pdfs = split_data[split]["pdfs"]
    print(f"Running validation on '{split}' split ({len(pdfs)} PDFs)...\n")

    # Initialize pipeline
    pipeline = PDFExtractionPipeline(extract_diagnostics=False)

    # Process each PDF
    per_pdf_results = []
    total_expected = 0
    total_extracted = 0
    total_matched = 0
    total_ci_expected = 0
    total_ci_matched = 0
    per_type = {}

    for pdf_info in pdfs:
        pdf_file = pdf_info["file"]
        source = pdf_info["source"]

        # Find PDF
        pdf_path = resolve_pdf_path(pdf_file, source, proj_root)
        if not pdf_path:
            print(f"  SKIP {pdf_file}: PDF not found")
            continue

        # Find gold annotation
        ann_path = proj_root / "test_pdfs" / "gold_standard" / "annotations" / pdf_file.replace(".pdf", ".gold.jsonl")
        if not ann_path.exists():
            print(f"  SKIP {pdf_file}: no gold annotation")
            continue

        # Load gold annotations
        gold = load_gold_annotations(str(ann_path))
        if not gold:
            print(f"  SKIP {pdf_file}: empty gold annotation")
            continue

        # Run validation
        result = validate_pdf(pdf_path, gold, pipeline, tolerance)
        per_pdf_results.append(result)

        total_expected += result.num_expected
        total_extracted += result.num_extracted
        total_matched += result.num_matched
        total_ci_expected += result.num_with_ci_expected
        total_ci_matched += result.num_with_ci_matched

        # Per-type tracking
        for detail in result.match_details:
            etype = detail["type"]
            if etype not in per_type:
                per_type[etype] = {"expected": 0, "matched": 0, "ci_expected": 0, "ci_matched": 0}
            per_type[etype]["expected"] += 1
            if detail["matched"]:
                per_type[etype]["matched"] += 1

        status = "OK" if result.sensitivity >= 0.7 else "LOW"
        print(f"  {pdf_file}: sens={result.sensitivity:.0%} prec={result.precision:.0%} "
              f"CI={result.ci_completion:.0%} ({result.num_matched}/{result.num_expected}) "
              f"[{status}] {result.extraction_time_seconds:.1f}s")

    # Compute summary
    sensitivity = total_matched / total_expected if total_expected > 0 else 0.0
    precision = total_matched / total_extracted if total_extracted > 0 else 0.0
    f1 = 2 * sensitivity * precision / (sensitivity + precision) if (sensitivity + precision) > 0 else 0.0
    ci_completion = total_ci_matched / total_ci_expected if total_ci_expected > 0 else 0.0

    # Wilson CIs
    sens_ci = wilson_ci(total_matched, total_expected)
    prec_ci = wilson_ci(total_matched, total_extracted)
    ci_comp_ci = wilson_ci(total_ci_matched, total_ci_expected)

    # Per-type metrics
    per_type_metrics = {}
    for etype, counts in per_type.items():
        if counts["expected"] > 0:
            per_type_metrics[etype] = {
                "expected": counts["expected"],
                "matched": counts["matched"],
                "sensitivity": counts["matched"] / counts["expected"],
            }

    summary = ValidationSummary(
        split=split,
        num_pdfs=len(per_pdf_results),
        total_expected=total_expected,
        total_extracted=total_extracted,
        total_matched=total_matched,
        total_ci_expected=total_ci_expected,
        total_ci_matched=total_ci_matched,
        sensitivity=sensitivity,
        precision=precision,
        f1=f1,
        ci_completion=ci_completion,
        sensitivity_ci=sens_ci,
        precision_ci=prec_ci,
        ci_completion_ci=ci_comp_ci,
        per_type_metrics=per_type_metrics,
        per_pdf_results=[asdict(r) for r in per_pdf_results],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Print summary
    print(f"\n{'='*60}")
    print(f"Validation Summary ({split})")
    print(f"{'='*60}")
    print(f"  PDFs validated: {summary.num_pdfs}")
    print(f"  Total expected: {summary.total_expected}")
    print(f"  Total extracted: {summary.total_extracted}")
    print(f"  Total matched: {summary.total_matched}")
    print(f"  Sensitivity: {summary.sensitivity:.1%} (95% CI: {sens_ci[0]:.1%}-{sens_ci[1]:.1%})")
    print(f"  Precision: {summary.precision:.1%} (95% CI: {prec_ci[0]:.1%}-{prec_ci[1]:.1%})")
    print(f"  F1: {summary.f1:.1%}")
    print(f"  CI completion: {summary.ci_completion:.1%} (95% CI: {ci_comp_ci[0]:.1%}-{ci_comp_ci[1]:.1%})")
    print(f"\n  Per-type sensitivity:")
    for etype, metrics in sorted(per_type_metrics.items()):
        print(f"    {etype}: {metrics['sensitivity']:.0%} ({metrics['matched']}/{metrics['expected']})")

    # Save output
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(asdict(summary), f, indent=2, default=str)
        print(f"\n  Results saved to: {output_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run gold standard validation")
    parser.add_argument("--split", default="development",
                       choices=["development", "held_out"],
                       help="Which split to validate")
    parser.add_argument("--output", default=None,
                       help="Output JSON path")
    parser.add_argument("--tolerance", type=float, default=0.05,
                       help="Matching tolerance for effect values")
    args = parser.parse_args()

    if args.output is None:
        args.output = f"output/{args.split}_validation_v51.json"

    run_validation(
        split=args.split,
        output_path=args.output,
        tolerance=args.tolerance,
    )


if __name__ == "__main__":
    main()
