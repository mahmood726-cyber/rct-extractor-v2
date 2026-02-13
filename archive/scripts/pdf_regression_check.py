#!/usr/bin/env python3
"""
PDF Validation Regression Checker
=================================

Compares current validation results against baseline to detect regressions.

Usage:
    python scripts/pdf_regression_check.py  # Compare against baseline
    python scripts/pdf_regression_check.py --update  # Update baseline
    python scripts/pdf_regression_check.py --ci-mode  # Exit with code on regression

Exit Codes:
    0 - No regression detected
    1 - Regression detected (accuracy dropped)
    2 - Error running validation
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
BASELINE_PATH = PROJECT_ROOT / "data" / "baselines" / "pdf_validation_baseline.json"
OUTPUT_DIR = PROJECT_ROOT / "output"
CURRENT_RESULTS_PATH = OUTPUT_DIR / "pdf_validation_report.json"


@dataclass
class RegressionResult:
    """Result of regression check"""
    has_regression: bool
    baseline_f1: float
    current_f1: float
    f1_change: float
    baseline_precision: float
    current_precision: float
    precision_change: float
    baseline_recall: float
    current_recall: float
    recall_change: float
    regressions_by_area: Dict[str, Dict[str, float]]
    new_failures: List[str]
    fixed_failures: List[str]
    message: str


def load_baseline() -> Optional[Dict[str, Any]]:
    """Load baseline metrics"""
    if not BASELINE_PATH.exists():
        logger.warning(f"No baseline found at {BASELINE_PATH}")
        return None

    with open(BASELINE_PATH, "r") as f:
        return json.load(f)


def load_current_results() -> Optional[Dict[str, Any]]:
    """Load current validation results"""
    if not CURRENT_RESULTS_PATH.exists():
        logger.error(f"No current results at {CURRENT_RESULTS_PATH}")
        logger.info("Run 'python scripts/run_real_pdf_validation.py --all' first")
        return None

    with open(CURRENT_RESULTS_PATH, "r") as f:
        return json.load(f)


def compare_metrics(
    baseline: Dict[str, Any],
    current: Dict[str, Any],
    tolerance: float = 0.02
) -> RegressionResult:
    """Compare baseline and current metrics for regressions"""

    # Overall metrics
    baseline_f1 = baseline.get("overall_f1", 0.0)
    current_f1 = current.get("overall_f1", 0.0)
    f1_change = current_f1 - baseline_f1

    baseline_precision = baseline.get("overall_precision", 0.0)
    current_precision = current.get("overall_precision", 0.0)
    precision_change = current_precision - baseline_precision

    baseline_recall = baseline.get("overall_recall", 0.0)
    current_recall = current.get("overall_recall", 0.0)
    recall_change = current_recall - baseline_recall

    # Check for regression (drop more than tolerance)
    has_regression = (
        f1_change < -tolerance or
        precision_change < -tolerance or
        recall_change < -tolerance
    )

    # Check by therapeutic area
    regressions_by_area = {}
    baseline_areas = baseline.get("by_therapeutic_area", {})
    current_areas = current.get("by_therapeutic_area", {})

    for area in set(baseline_areas.keys()) | set(current_areas.keys()):
        b_metrics = baseline_areas.get(area, {})
        c_metrics = current_areas.get(area, {})

        area_f1_change = c_metrics.get("f1", 0) - b_metrics.get("f1", 0)
        if area_f1_change < -tolerance:
            regressions_by_area[area] = {
                "baseline_f1": b_metrics.get("f1", 0),
                "current_f1": c_metrics.get("f1", 0),
                "change": area_f1_change
            }
            has_regression = True

    # Check for new failures
    baseline_results = {r.get("trial_name"): r for r in baseline.get("results", [])}
    current_results = {r.get("trial_name"): r for r in current.get("results", [])}

    new_failures = []
    fixed_failures = []

    for trial, c_result in current_results.items():
        b_result = baseline_results.get(trial)
        if b_result:
            b_f1 = b_result.get("f1_score", 0)
            c_f1 = c_result.get("f1_score", 0)

            # New failure: was passing (>=0.9), now failing (<0.9)
            if b_f1 >= 0.9 and c_f1 < 0.9:
                new_failures.append(trial)
                has_regression = True

            # Fixed: was failing, now passing
            if b_f1 < 0.9 and c_f1 >= 0.9:
                fixed_failures.append(trial)

    # Generate message
    if has_regression:
        msg_parts = []
        if f1_change < -tolerance:
            msg_parts.append(f"F1 dropped by {abs(f1_change):.1%}")
        if precision_change < -tolerance:
            msg_parts.append(f"Precision dropped by {abs(precision_change):.1%}")
        if recall_change < -tolerance:
            msg_parts.append(f"Recall dropped by {abs(recall_change):.1%}")
        if regressions_by_area:
            msg_parts.append(f"Regressions in {len(regressions_by_area)} areas")
        if new_failures:
            msg_parts.append(f"{len(new_failures)} new failures")
        message = "REGRESSION DETECTED: " + "; ".join(msg_parts)
    else:
        improvements = []
        if f1_change > tolerance:
            improvements.append(f"F1 improved by {f1_change:.1%}")
        if fixed_failures:
            improvements.append(f"{len(fixed_failures)} fixed")
        if improvements:
            message = "IMPROVEMENT: " + "; ".join(improvements)
        else:
            message = "NO REGRESSION: metrics stable"

    return RegressionResult(
        has_regression=has_regression,
        baseline_f1=baseline_f1,
        current_f1=current_f1,
        f1_change=f1_change,
        baseline_precision=baseline_precision,
        current_precision=current_precision,
        precision_change=precision_change,
        baseline_recall=baseline_recall,
        current_recall=current_recall,
        recall_change=recall_change,
        regressions_by_area=regressions_by_area,
        new_failures=new_failures,
        fixed_failures=fixed_failures,
        message=message
    )


def update_baseline(current: Dict[str, Any]) -> Path:
    """Update baseline with current results"""
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)

    baseline = {
        "version": "1.0.0",
        "created": datetime.now().isoformat(),
        "source": str(CURRENT_RESULTS_PATH),
        "overall_f1": current.get("overall_f1", 0.0),
        "overall_precision": current.get("overall_precision", 0.0),
        "overall_recall": current.get("overall_recall", 0.0),
        "total_pdfs": current.get("total_pdfs", 0),
        "pdfs_processed": current.get("pdfs_processed", 0),
        "by_therapeutic_area": current.get("by_therapeutic_area", {}),
        "by_effect_type": current.get("by_effect_type", {}),
        "results": current.get("results", []),
    }

    with open(BASELINE_PATH, "w") as f:
        json.dump(baseline, f, indent=2)

    logger.info(f"Baseline updated: {BASELINE_PATH}")
    return BASELINE_PATH


def print_report(result: RegressionResult):
    """Print regression check report"""
    print("\n" + "=" * 70)
    print("PDF VALIDATION REGRESSION CHECK")
    print("=" * 70)

    print(f"\n{result.message}")

    print("\nMetric Comparison:")
    print(f"  {'Metric':<15} {'Baseline':>12} {'Current':>12} {'Change':>12}")
    print("-" * 55)
    print(f"  {'F1 Score':<15} {result.baseline_f1:>11.1%} {result.current_f1:>11.1%} "
          f"{'+' if result.f1_change >= 0 else ''}{result.f1_change:>10.1%}")
    print(f"  {'Precision':<15} {result.baseline_precision:>11.1%} {result.current_precision:>11.1%} "
          f"{'+' if result.precision_change >= 0 else ''}{result.precision_change:>10.1%}")
    print(f"  {'Recall':<15} {result.baseline_recall:>11.1%} {result.current_recall:>11.1%} "
          f"{'+' if result.recall_change >= 0 else ''}{result.recall_change:>10.1%}")

    if result.regressions_by_area:
        print("\nRegressions by Therapeutic Area:")
        for area, metrics in result.regressions_by_area.items():
            print(f"  {area}: {metrics['baseline_f1']:.1%} -> {metrics['current_f1']:.1%} "
                  f"(change: {metrics['change']:.1%})")

    if result.new_failures:
        print(f"\nNew Failures ({len(result.new_failures)}):")
        for trial in result.new_failures:
            print(f"  - {trial}")

    if result.fixed_failures:
        print(f"\nFixed ({len(result.fixed_failures)}):")
        for trial in result.fixed_failures:
            print(f"  + {trial}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Check for PDF validation regressions against baseline"
    )
    parser.add_argument(
        "--update", action="store_true",
        help="Update baseline with current results"
    )
    parser.add_argument(
        "--ci-mode", action="store_true",
        help="CI mode: exit with code 1 on regression"
    )
    parser.add_argument(
        "--tolerance", type=float, default=0.02,
        help="Tolerance for regression detection (default: 0.02 = 2%)"
    )
    parser.add_argument(
        "--baseline", type=Path, default=BASELINE_PATH,
        help="Path to baseline file"
    )
    parser.add_argument(
        "--current", type=Path, default=CURRENT_RESULTS_PATH,
        help="Path to current results file"
    )

    args = parser.parse_args()

    # Load current results
    current = load_current_results()
    if current is None:
        logger.error("Cannot proceed without current results")
        sys.exit(2)

    # Update mode
    if args.update:
        update_baseline(current)
        print(f"Baseline updated with F1={current.get('overall_f1', 0):.1%}")
        sys.exit(0)

    # Load baseline
    baseline = load_baseline()
    if baseline is None:
        logger.warning("No baseline exists. Creating initial baseline.")
        update_baseline(current)
        print("Initial baseline created. Run again after making changes to check for regressions.")
        sys.exit(0)

    # Compare
    result = compare_metrics(baseline, current, tolerance=args.tolerance)

    # Print report
    print_report(result)

    # Save comparison result
    comparison_path = OUTPUT_DIR / "regression_check_result.json"
    with open(comparison_path, "w") as f:
        json.dump(asdict(result), f, indent=2)
    logger.info(f"Comparison saved: {comparison_path}")

    # CI mode exit
    if args.ci_mode:
        if result.has_regression:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()
