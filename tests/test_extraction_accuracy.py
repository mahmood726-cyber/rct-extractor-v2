"""
Extraction Accuracy Regression Tests
=====================================

Tests that extraction accuracy meets baseline thresholds.
Run these tests to ensure pattern changes don't degrade performance.

Usage:
    pytest tests/test_extraction_accuracy.py -v
    pytest tests/test_extraction_accuracy.py::test_ci_completion_meets_target -v
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.external_validation_dataset import (
    ALL_EXTERNAL_VALIDATION_TRIALS,
    ExtractionDifficulty,
)

try:
    from src.core.enhanced_extractor_v3 import EnhancedExtractor, EffectType
    HAS_EXTRACTOR = True
except ImportError:
    HAS_EXTRACTOR = False
    EnhancedExtractor = None


# Target thresholds for v4.3
TARGETS = {
    "ci_completion": 0.80,
    "extraction_rate": 0.70,
    "md_ci_rate": 0.70,
    "rr_ci_rate": 0.80,
    "hr_ci_rate": 0.90,
    "or_ci_rate": 0.85,
}

# Minimum acceptable (for regression prevention)
MINIMUMS = {
    "ci_completion": 0.65,
    "extraction_rate": 0.50,
    "md_ci_rate": 0.25,
    "hr_ci_rate": 0.80,
}


def get_ground_truth() -> List[Dict[str, Any]]:
    """Get ground truth from external_validation_dataset"""
    results = []

    for trial in ALL_EXTERNAL_VALIDATION_TRIALS:
        extractions = trial.consensus if trial.consensus else trial.extractor_a

        effects = []
        for ext in extractions:
            effects.append({
                "type": ext.effect_type,
                "value": ext.effect_size,
                "ci_lower": ext.ci_lower,
                "ci_upper": ext.ci_upper,
            })

        results.append({
            "trial": trial.trial_name,
            "source_text": trial.source_text,
            "effects": effects,
            "difficulty": trial.difficulty.value,
        })

    return results


def run_extraction(text: str) -> List[Any]:
    """Run extraction on text"""
    if not HAS_EXTRACTOR:
        return []

    extractor = EnhancedExtractor()
    return extractor.extract(text)


def match_effect(expected: Dict, extractions: List, tolerance: float = 0.05) -> tuple:
    """Match expected effect to extraction, return (matched, has_ci)"""
    exp_type = expected.get("type", "")
    exp_val = expected.get("value")

    if exp_val is None:
        return False, False

    for ext in extractions:
        ext_type = ext.effect_type.value if hasattr(ext.effect_type, "value") else str(ext.effect_type)
        ext_val = ext.point_estimate

        if ext_type.upper() != exp_type.upper():
            continue

        if ext_val is None:
            continue

        try:
            if abs(ext_val - exp_val) / max(abs(exp_val), 0.001) <= tolerance:
                has_ci = ext.ci is not None and ext.ci.lower is not None and ext.ci.upper is not None
                return True, has_ci
        except (TypeError, ZeroDivisionError):
            continue

    return False, False


def calculate_metrics(ground_truth: List[Dict]) -> Dict[str, float]:
    """Calculate extraction metrics against ground truth"""
    total_expected = 0
    total_matched = 0
    total_with_ci = 0
    trials_with_extractions = 0

    by_type = {}

    for trial in ground_truth:
        text = trial.get("source_text", "")
        expected = trial.get("effects", [])

        if not text or not expected:
            continue

        extractions = run_extraction(text)

        if extractions:
            trials_with_extractions += 1

        for exp in expected:
            exp_type = exp.get("type", "")
            total_expected += 1

            if exp_type not in by_type:
                by_type[exp_type] = {"expected": 0, "matched": 0, "with_ci": 0}
            by_type[exp_type]["expected"] += 1

            matched, has_ci = match_effect(exp, extractions)

            if matched:
                total_matched += 1
                by_type[exp_type]["matched"] += 1
                if has_ci:
                    total_with_ci += 1
                    by_type[exp_type]["with_ci"] += 1

    # Calculate rates
    metrics = {
        "total_trials": len(ground_truth),
        "trials_with_text": len([t for t in ground_truth if t.get("source_text")]),
        "trials_with_extractions": trials_with_extractions,
        "total_expected": total_expected,
        "total_matched": total_matched,
        "total_with_ci": total_with_ci,
        "extraction_rate": trials_with_extractions / len(ground_truth) if ground_truth else 0,
        "recall": total_matched / total_expected if total_expected > 0 else 0,
        "ci_completion": total_with_ci / total_matched if total_matched > 0 else 0,
    }

    # Per-type CI rates
    for etype, counts in by_type.items():
        key = f"{etype.lower()}_ci_rate"
        if counts["matched"] > 0:
            metrics[key] = counts["with_ci"] / counts["matched"]
        else:
            metrics[key] = 0.0

    return metrics


@pytest.fixture(scope="module")
def validation_metrics():
    """Calculate metrics once for all tests"""
    if not HAS_EXTRACTOR:
        pytest.skip("Enhanced extractor not available")

    ground_truth = get_ground_truth()
    return calculate_metrics(ground_truth)


class TestExtractionAccuracy:
    """Test extraction accuracy against baselines"""

    def test_extractor_available(self):
        """Test that extractor module is available"""
        assert HAS_EXTRACTOR, "Enhanced extractor must be available"

    def test_ground_truth_available(self):
        """Test that ground truth is available"""
        gt = get_ground_truth()
        assert len(gt) >= 30, f"Expected at least 30 trials, got {len(gt)}"

    def test_ci_completion_meets_minimum(self, validation_metrics):
        """Test that CI completion meets minimum threshold"""
        ci_completion = validation_metrics.get("ci_completion", 0)
        minimum = MINIMUMS["ci_completion"]

        assert ci_completion >= minimum, (
            f"CI completion {ci_completion:.1%} below minimum {minimum:.1%}"
        )

    def test_ci_completion_meets_target(self, validation_metrics):
        """Test that CI completion meets target threshold"""
        ci_completion = validation_metrics.get("ci_completion", 0)
        target = TARGETS["ci_completion"]

        # Use xfail if below target but above minimum
        if ci_completion < target:
            pytest.xfail(
                f"CI completion {ci_completion:.1%} below target {target:.1%} "
                "(improvement needed)"
            )

    def test_extraction_rate_meets_minimum(self, validation_metrics):
        """Test that extraction rate meets minimum threshold"""
        extraction_rate = validation_metrics.get("extraction_rate", 0)
        minimum = MINIMUMS["extraction_rate"]

        assert extraction_rate >= minimum, (
            f"Extraction rate {extraction_rate:.1%} below minimum {minimum:.1%}"
        )

    def test_extraction_rate_meets_target(self, validation_metrics):
        """Test that extraction rate meets target threshold"""
        extraction_rate = validation_metrics.get("extraction_rate", 0)
        target = TARGETS["extraction_rate"]

        if extraction_rate < target:
            pytest.xfail(
                f"Extraction rate {extraction_rate:.1%} below target {target:.1%}"
            )

    def test_hr_ci_rate_meets_minimum(self, validation_metrics):
        """Test that HR CI rate meets minimum threshold"""
        hr_ci_rate = validation_metrics.get("hr_ci_rate", 0)
        minimum = MINIMUMS["hr_ci_rate"]

        assert hr_ci_rate >= minimum, (
            f"HR CI rate {hr_ci_rate:.1%} below minimum {minimum:.1%}"
        )

    def test_md_ci_rate_meets_minimum(self, validation_metrics):
        """Test that MD CI rate meets minimum threshold"""
        md_ci_rate = validation_metrics.get("md_ci_rate", 0)
        minimum = MINIMUMS["md_ci_rate"]

        assert md_ci_rate >= minimum, (
            f"MD CI rate {md_ci_rate:.1%} below minimum {minimum:.1%}"
        )

    def test_md_ci_rate_meets_target(self, validation_metrics):
        """Test that MD CI rate meets target threshold"""
        md_ci_rate = validation_metrics.get("md_ci_rate", 0)
        target = TARGETS["md_ci_rate"]

        if md_ci_rate < target:
            pytest.xfail(
                f"MD CI rate {md_ci_rate:.1%} below target {target:.1%}"
            )


class TestSpecificTrials:
    """Test extraction on specific important trials"""

    @pytest.mark.parametrize("trial_name,expected_hr", [
        ("DAPA-HF", 0.74),
        ("EMPEROR-Reduced", 0.75),
        ("PARADIGM-HF", 0.80),
    ])
    def test_landmark_cardiovascular_trials(self, trial_name, expected_hr):
        """Test extraction of landmark CV trial results"""
        if not HAS_EXTRACTOR:
            pytest.skip("Extractor not available")

        # Find trial
        trial = next(
            (t for t in ALL_EXTERNAL_VALIDATION_TRIALS if t.trial_name == trial_name),
            None
        )
        assert trial is not None, f"Trial {trial_name} not found"

        # Extract
        extractions = run_extraction(trial.source_text)
        assert len(extractions) > 0, f"No extractions from {trial_name}"

        # Find HR match
        hr_found = False
        for ext in extractions:
            if ext.effect_type == EffectType.HR:
                if abs(ext.point_estimate - expected_hr) < 0.02:
                    hr_found = True
                    # Check CI
                    assert ext.ci is not None, f"{trial_name}: HR found but no CI"
                    break

        assert hr_found, f"{trial_name}: HR {expected_hr} not found"

    @pytest.mark.parametrize("trial_name,expected_type,expected_value", [
        ("KEYNOTE-024", "HR", 0.50),
        ("KEYNOTE-189", "HR", 0.49),
        ("CLEOPATRA", "HR", 0.62),
    ])
    def test_oncology_trials(self, trial_name, expected_type, expected_value):
        """Test extraction of oncology trial results"""
        if not HAS_EXTRACTOR:
            pytest.skip("Extractor not available")

        trial = next(
            (t for t in ALL_EXTERNAL_VALIDATION_TRIALS if t.trial_name == trial_name),
            None
        )
        assert trial is not None, f"Trial {trial_name} not found"

        extractions = run_extraction(trial.source_text)
        assert len(extractions) > 0, f"No extractions from {trial_name}"

        # Find match
        found = False
        for ext in extractions:
            ext_type = ext.effect_type.value
            if ext_type == expected_type:
                if abs(ext.point_estimate - expected_value) < 0.02:
                    found = True
                    break

        assert found, f"{trial_name}: {expected_type} {expected_value} not found"


class TestPatternCoverage:
    """Test that key patterns are working"""

    @pytest.mark.parametrize("text,expected_type,expected_value", [
        # Standard HR
        ("hazard ratio, 0.74; 95% CI, 0.65 to 0.85", "HR", 0.74),
        ("HR 0.75 (0.65-0.86)", "HR", 0.75),
        ("HR for death, 0.49; 95% CI, 0.38 to 0.64", "HR", 0.49),

        # Standard OR
        ("odds ratio 0.72 (0.55-0.94)", "OR", 0.72),
        ("OR = 0.26, 95% CI: 0.11-0.60", "OR", 0.26),

        # Standard RR
        ("relative risk, 0.66; 95% CI, 0.53 to 0.82", "RR", 0.66),
        ("RR 1.32 (1.12-1.55)", "RR", 1.32),

        # Standard MD
        ("mean difference -4.0; 95% CI, -7.31 to -0.64", "MD", -4.0),
        ("MD -0.5 (-1.0 to 0.0)", "MD", -0.5),
    ])
    def test_standard_patterns(self, text, expected_type, expected_value):
        """Test standard effect patterns"""
        if not HAS_EXTRACTOR:
            pytest.skip("Extractor not available")

        extractions = run_extraction(text)
        assert len(extractions) >= 1, f"No extraction from: {text}"

        # Find match
        found = False
        for ext in extractions:
            ext_type = ext.effect_type.value
            if ext_type == expected_type:
                if abs(ext.point_estimate - expected_value) < 0.02:
                    found = True
                    # Verify CI was extracted
                    assert ext.ci is not None, f"CI not extracted from: {text}"
                    break

        assert found, f"{expected_type} {expected_value} not found in: {text}"


class TestNegativeControls:
    """Test that negative controls produce minimal false positives"""

    @pytest.fixture(scope="class")
    def negative_control_results(self):
        """Run extraction on all negative controls"""
        if not HAS_EXTRACTOR:
            pytest.skip("Extractor not available")

        from data.negative_controls import NEGATIVE_CONTROLS
        extractor = EnhancedExtractor()

        results = []
        for nc in NEGATIVE_CONTROLS:
            extractions = extractor.extract(nc.source_text)
            results.append({
                "id": nc.id,
                "type": nc.control_type.value,
                "extractions": len(extractions),
                "expected": nc.expected_extractions,
            })
        return results

    def test_protocol_papers_minimal_extractions(self, negative_control_results):
        """Protocol papers should produce minimal extractions"""
        protocol_results = [r for r in negative_control_results if r["type"] == "protocol"]
        fp_count = sum(1 for r in protocol_results if r["extractions"] > r["expected"])

        # Allow at most 1 protocol to have false positives
        assert fp_count <= 1, f"{fp_count} protocol papers have false positives"

    def test_methods_examples_minimal_extractions(self, negative_control_results):
        """Methods/example text should produce minimal extractions"""
        methods_results = [r for r in negative_control_results if r["type"] == "methods_example"]
        fp_count = sum(1 for r in methods_results if r["extractions"] > r["expected"])

        # Allow at most 1 methods example to have false positives
        assert fp_count <= 1, f"{fp_count} methods examples have false positives"

    def test_observational_studies_minimal_extractions(self, negative_control_results):
        """Observational studies should produce minimal extractions"""
        obs_results = [r for r in negative_control_results if r["type"] == "observational"]
        fp_count = sum(1 for r in obs_results if r["extractions"] > r["expected"])

        # Allow at most 2 observational studies to have false positives
        assert fp_count <= 2, f"{fp_count} observational studies have false positives"

    def test_overall_fp_rate_below_threshold(self, negative_control_results):
        """Overall false positive rate should be below 30%"""
        fp_count = sum(1 for r in negative_control_results if r["extractions"] > r["expected"])
        fp_rate = fp_count / len(negative_control_results) if negative_control_results else 0

        assert fp_rate <= 0.30, f"False positive rate {fp_rate:.1%} exceeds 30% threshold"


class TestHardDifficultyTrials:
    """Test extraction on hard difficulty trials"""

    @pytest.mark.parametrize("trial_name,expected_type,expected_value", [
        ("ASCOT-LLA", "HR", 0.64),
        ("DREAM", "HR", 0.40),
        ("RALES", "RR", 0.70),
        ("DECLARE-TIMI 58", "HR", 0.93),
    ])
    def test_hard_trials(self, trial_name, expected_type, expected_value):
        """Test extraction on hard difficulty trials"""
        if not HAS_EXTRACTOR:
            pytest.skip("Extractor not available")

        trial = next(
            (t for t in ALL_EXTERNAL_VALIDATION_TRIALS if t.trial_name == trial_name),
            None
        )
        if trial is None:
            pytest.skip(f"Trial {trial_name} not found")

        extractions = run_extraction(trial.source_text)

        found = False
        for ext in extractions:
            ext_type = ext.effect_type.value
            if ext_type == expected_type and abs(ext.point_estimate - expected_value) < 0.02:
                found = True
                break

        assert found, f"{trial_name}: {expected_type} {expected_value} not found"


def test_print_metrics():
    """Print current metrics for manual inspection"""
    if not HAS_EXTRACTOR:
        pytest.skip("Extractor not available")

    ground_truth = get_ground_truth()
    metrics = calculate_metrics(ground_truth)

    print("\n" + "=" * 50)
    print("CURRENT EXTRACTION METRICS")
    print("=" * 50)
    print(f"Trials: {metrics['total_trials']}")
    print(f"With text: {metrics['trials_with_text']}")
    print(f"With extractions: {metrics['trials_with_extractions']}")
    print(f"Extraction rate: {metrics['extraction_rate']:.1%}")
    print(f"Total expected: {metrics['total_expected']}")
    print(f"Total matched: {metrics['total_matched']}")
    print(f"Recall: {metrics['recall']:.1%}")
    print(f"CI completion: {metrics['ci_completion']:.1%}")

    print("\nPer-type CI rates:")
    for key, val in sorted(metrics.items()):
        if key.endswith("_ci_rate"):
            etype = key.replace("_ci_rate", "").upper()
            print(f"  {etype}: {val:.1%}")

    print("=" * 50)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
