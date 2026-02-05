"""
CI Proximity Search Regression Tests (v4.3.6)
==============================================

Tests CI proximity search correctness including:
- Standard CI recovery
- False positive rejection
- CI validation bracketing
- CI deduplication
- Snippet validation baseline

Usage:
    pytest tests/test_ci_proximity.py -v
"""

import json
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.ci_proximity_search import CIProximitySearch, _ci_key

try:
    from src.core.enhanced_extractor_v3 import EnhancedExtractor
    HAS_EXTRACTOR = True
except ImportError:
    HAS_EXTRACTOR = False

PROJECT_ROOT = Path(__file__).parent.parent
GT_PATH = PROJECT_ROOT / "data" / "ground_truth" / "external_validation_ground_truth.json"


class TestCIKeyFunction:
    """Test the _ci_key helper for stable hashing."""

    def test_basic_key(self):
        assert _ci_key(0.65, 0.85) == (6500, 8500)

    def test_float_rounding_stability(self):
        # These should produce the same key despite float imprecision
        a = _ci_key(0.1 + 0.2, 0.85)
        b = _ci_key(0.3, 0.85)
        assert a == b

    def test_negative_values(self):
        key = _ci_key(-1.5, 0.5)
        assert key == (-15000, 5000)

    def test_truncation_bug_0_69(self):
        """int(0.69 * 10000) = 6899 without round(). Must give 6900."""
        key = _ci_key(0.46, 0.69)
        assert key == (4600, 6900), f"Got {key}, expected (4600, 6900)"

    def test_truncation_bug_various(self):
        """Values known to fail with int() truncation."""
        assert _ci_key(4.81, 5.0) == (48100, 50000)
        assert _ci_key(0.0, 2.51) == (0, 25100)
        assert _ci_key(2.78, 3.01) == (27800, 30100)


class TestCIValidation:
    """Test CI validation rejects impossible cases."""

    @pytest.fixture
    def searcher(self):
        return CIProximitySearch()

    def test_value_inside_ci_passes(self, searcher):
        assert searcher._validate_ci(0.74, 0.65, 0.85, "HR") is True

    def test_value_at_ci_lower_bound_passes(self, searcher):
        assert searcher._validate_ci(0.65, 0.65, 0.85, "HR") is True

    def test_value_outside_ci_lower_rejected(self, searcher):
        """v4.3.6 fix: HR=0.59 with CI 0.61-1.81 must be rejected."""
        assert searcher._validate_ci(0.59, 0.61, 1.81, "HR") is False

    def test_value_far_outside_ci_rejected(self, searcher):
        assert searcher._validate_ci(0.30, 0.65, 0.85, "HR") is False

    def test_value_slightly_below_with_tolerance(self, searcher):
        # 0.64 is within 0.01 tolerance of ci_lower=0.65
        assert searcher._validate_ci(0.64, 0.65, 0.85, "HR") is True

    def test_negative_ci_ratio_rejected(self, searcher):
        assert searcher._validate_ci(0.74, -0.5, 0.85, "HR") is False

    def test_implausibly_wide_ci_rejected(self, searcher):
        assert searcher._validate_ci(1.0, 0.01, 100.0, "HR") is False

    def test_md_value_inside_ci(self, searcher):
        assert searcher._validate_ci(-2.5, -5.0, 0.0, "MD") is True

    def test_md_value_outside_ci(self, searcher):
        assert searcher._validate_ci(-10.0, -5.0, 0.0, "MD") is False


class TestCIRecovery:
    """Test CI is correctly recovered from text."""

    @pytest.fixture
    def searcher(self):
        return CIProximitySearch()

    def test_standard_ci_format(self, searcher):
        text = "The hazard ratio was 0.74, 95% CI 0.65-0.85, p<0.001."
        result = searcher.search_ci_near_value(text, 0.74, "HR")
        assert result is not None
        assert result.ci_lower == 0.65
        assert result.ci_upper == 0.85

    def test_table_format_with_ci_label(self, searcher):
        text = """Table 2. Primary Outcomes
        Endpoint    HR    95% CI         p-value
        MACE        0.82  (0.71-0.95)   0.008"""
        result = searcher.search_ci_near_value(text, 0.82, "HR")
        assert result is not None
        assert result.ci_lower == 0.71
        assert result.ci_upper == 0.95

    def test_semicolon_format(self, searcher):
        text = "HR=0.76, 95% CI; 0.58 to 0.99; P=0.04"
        result = searcher.search_ci_near_value(text, 0.76, "HR")
        assert result is not None
        assert result.ci_lower == 0.58


class TestFalsePositiveRejection:
    """Test that false positives are correctly rejected."""

    @pytest.fixture
    def searcher(self):
        return CIProximitySearch()

    def test_reject_ci_belonging_to_different_value(self, searcher):
        text = "OR 0.37 (p=0.02). In subgroup analysis, OR was 0.54 (95% CI 0.2-1.42)."
        result = searcher.search_ci_near_value(text, 0.37, "OR")
        assert result is None

    def test_reject_mean_sd_as_ci(self, searcher):
        text = "The mean change was 3.4 (SD 0.17). No confidence interval reported."
        result = searcher.search_ci_near_value(text, 3.4, "MD")
        assert result is None

    def test_reject_unlabeled_pattern_without_ci_label(self, searcher):
        text = "The hazard ratio was 0.74. Patients had scores of (0.65-0.85) on the scale."
        result = searcher.search_ci_near_value(text, 0.74, "HR")
        assert result is None

    def test_reject_value_outside_ci_bounds(self, searcher):
        text = "The hazard ratio was 0.59. The overall result showed HR 0.61 (95% CI 0.61-1.81)."
        result = searcher.search_ci_near_value(text, 0.59, "HR")
        assert result is None


class TestCIDeduplication:
    """Test that the same CI is not assigned to multiple extractions."""

    @pytest.fixture
    def searcher(self):
        return CIProximitySearch()

    def test_same_ci_not_assigned_twice(self, searcher):
        text = """In the primary analysis, RR was 0.42, and in sensitivity analysis RR was 0.46.
        The pooled estimate showed RR 0.42 (95% CI 0.30-0.84)."""

        result_a = searcher.search_ci_near_value(text, 0.42, "RR")
        assert result_a is not None
        assert result_a.ci_lower == 0.30

        used = {_ci_key(result_a.ci_lower, result_a.ci_upper)}
        result_b = searcher.search_ci_near_value(text, 0.46, "RR", exclude_cis=used)
        assert result_b is None  # CI already taken

    def test_different_cis_can_be_assigned(self, searcher):
        text = """HR 0.74 (95% CI 0.65-0.85). Secondary: HR 0.80 (95% CI 0.70-0.92)."""

        result_a = searcher.search_ci_near_value(text, 0.74, "HR")
        assert result_a is not None

        used = {_ci_key(result_a.ci_lower, result_a.ci_upper)}
        result_b = searcher.search_ci_near_value(text, 0.80, "HR", exclude_cis=used)
        assert result_b is not None
        assert result_b.ci_lower == 0.70


class TestSnippetValidationBaseline:
    """Regression test: snippet validation must meet baseline thresholds."""

    @pytest.fixture(scope="class")
    def snippet_results(self):
        if not HAS_EXTRACTOR:
            pytest.skip("Extractor not available")
        if not GT_PATH.exists():
            pytest.skip("Ground truth not found")

        with open(GT_PATH) as f:
            gt_data = json.load(f)

        extractor = EnhancedExtractor()
        proximity = CIProximitySearch()

        total_gt = 0
        total_matched = 0
        total_ci = 0

        for trial in gt_data.get("trials", []):
            source_text = trial.get("source_text", "")
            gt_effects = trial.get("effects", [])
            if not source_text or not gt_effects:
                continue

            extractions = extractor.extract(source_text)
            ext_dicts = []
            for e in extractions:
                d = {
                    "effect_type": str(e.effect_type.value) if hasattr(e.effect_type, 'value') else str(e.effect_type),
                    "value": e.point_estimate,
                    "ci_lower": e.ci.lower if e.ci else None,
                    "ci_upper": e.ci.upper if e.ci else None,
                    "ci_complete": e.has_complete_ci,
                }
                ext_dicts.append(d)

            # Proximity search with dedup
            used_cis = set()
            for d in ext_dicts:
                if d["ci_complete"] and d["ci_lower"] is not None:
                    used_cis.add(_ci_key(d["ci_lower"], d["ci_upper"]))
            for d in ext_dicts:
                if d["ci_complete"]:
                    continue
                r = proximity.search_ci_near_value(
                    source_text, d["value"], d["effect_type"], exclude_cis=used_cis
                )
                if r:
                    d["ci_lower"] = r.ci_lower
                    d["ci_upper"] = r.ci_upper
                    d["ci_complete"] = True
                    used_cis.add(_ci_key(r.ci_lower, r.ci_upper))

            for gt in gt_effects:
                total_gt += 1
                gt_value = gt.get("value")
                gt_type = gt.get("effect_type", "").upper()

                # Find best match (smallest value diff) - not just first match
                best_match = None
                best_diff = float('inf')
                for ext in ext_dicts:
                    ext_type = ext.get("effect_type", "").upper()
                    type_ok = ext_type == gt_type or (
                        ext_type in ("HR", "OR", "RR", "IRR") and
                        gt_type in ("HR", "OR", "RR", "IRR"))
                    if type_ok:
                        diff = abs(ext["value"] - gt_value)
                        if diff < best_diff:
                            best_diff = diff
                            best_match = ext

                if best_match and best_diff < 0.05:
                    total_matched += 1
                    if best_match.get("ci_complete") and gt.get("ci_lower") is not None:
                        cl = abs((best_match.get("ci_lower") or 0) - gt["ci_lower"])
                        cu = abs((best_match.get("ci_upper") or 0) - gt["ci_upper"])
                        if cl < 0.05 and cu < 0.05:
                            total_ci += 1

        return {
            "total_gt": total_gt,
            "matched": total_matched,
            "ci_correct": total_ci,
            "recall": total_matched / total_gt if total_gt else 0,
            "ci_accuracy": total_ci / total_gt if total_gt else 0,
        }

    def test_snippet_recall_above_95(self, snippet_results):
        """Snippet recall must stay above 95%."""
        assert snippet_results["recall"] >= 0.95, (
            f"Snippet recall {snippet_results['recall']:.1%} below 95% baseline"
        )

    def test_snippet_ci_accuracy_above_85(self, snippet_results):
        """Snippet CI accuracy must stay above 85%."""
        assert snippet_results["ci_accuracy"] >= 0.85, (
            f"Snippet CI accuracy {snippet_results['ci_accuracy']:.1%} below 85% baseline"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
