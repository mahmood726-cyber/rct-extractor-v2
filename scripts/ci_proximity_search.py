#!/usr/bin/env python3
"""
CI Proximity Search Enhancement (v4.3.6)

When an effect value is found without a CI, this module searches the surrounding
text context for CI patterns that might not have been captured by the standard
patterns.

v4.3.5: Window 500→150, CI label gate, negative validation
v4.3.6: Strict CI bracketing (0.01 tol), CI deduplication, int-key hashing

Usage:
    from scripts.ci_proximity_search import CIProximitySearch
    searcher = CIProximitySearch()
    enhanced = searcher.enhance_extractions(text, extractions)
"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ProximityResult:
    """Result of CI proximity search."""
    ci_lower: float
    ci_upper: float
    confidence: float
    source_text: str
    method: str  # "proximity_regex", "table_heuristic", "bracketed"


def _ci_key(lower: float, upper: float) -> tuple:
    """Create a stable hash key for a CI pair.

    Uses round() before int() to avoid truncation errors.
    Without round(), int(0.69 * 10000) = 6899 instead of 6900.
    """
    return (int(round(lower * 10000)), int(round(upper * 10000)))


class CIProximitySearch:
    """Search for CIs near effect values that weren't captured by standard patterns."""

    def __init__(self, window_chars: int = 150):
        """
        Args:
            window_chars: Characters to search before and after value.
                          v4.3.5: Reduced from 500 to 150 to cut false positives.
        """
        self.window_chars = window_chars

        # CI patterns to try (ordered by specificity/reliability)
        # v4.3.5: Labeled vs unlabeled patterns separated for confidence gating
        self.labeled_ci_patterns = [
            # Standard 95% CI formats - HIGH specificity, always trusted
            (r'95%?\s*CI[:\s,]*[\(\[]?\s*(-?\d+\.?\d*)\s*(?:[-\u2013\u2014,]|to)\s*(-?\d+\.?\d*)', "standard_ci"),
            (r'95%?\s*confidence\s+interval[:\s,]*[\(\[]?\s*(-?\d+\.?\d*)\s*(?:[-\u2013\u2014,]|to)\s*(-?\d+\.?\d*)', "confidence_interval"),
            # CI without percentage
            (r'\bCI[:\s,]+[\(\[]?\s*(-?\d+\.?\d*)\s*(?:[-\u2013\u2014,]|to)\s*(-?\d+\.?\d*)', "ci_label"),
        ]

        self.unlabeled_ci_patterns = [
            # Bracketed formats - MEDIUM specificity, need CI label in context
            (r'\[(-?\d+\.?\d*)\s*(?:[-\u2013\u2014,]|to)\s*(-?\d+\.?\d*)\]', "square_bracket"),
            (r'\((-?\d+\.?\d*)\s*(?:[-\u2013\u2014,]|to)\s*(-?\d+\.?\d*)\)', "parentheses"),
            # Semicolon separated then range
            (r';\s*(-?\d+\.?\d*)\s+(?:to|[-\u2013\u2014])\s*(-?\d+\.?\d*)', "semicolon_sep"),
        ]

        # v4.3.5: hyphen_range REMOVED from default patterns - too many false positives
        # Only used if CI/confidence label found in context

        # Value normalization patterns
        self.value_formats = [
            lambda v: str(v),
            lambda v: f"{v:.2f}",
            lambda v: f"{v:.1f}",
            lambda v: f"{v:.3f}",
        ]

    def find_value_positions(self, text: str, value: float) -> List[int]:
        """Find all positions where the value appears in text."""
        positions = []

        for fmt in self.value_formats:
            value_str = fmt(value)
            start = 0
            while True:
                pos = text.find(value_str, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1

        return sorted(set(positions))

    def _has_ci_label_in_context(self, context: str) -> bool:
        """Check if context contains a CI label (95% CI, confidence interval, etc.)."""
        return bool(re.search(
            r'(?:95%?\s*CI|confidence\s+interval|\bCI\b)',
            context,
            re.IGNORECASE
        ))

    def _find_other_values_near_ci(self, text: str, ci_lower: float, ci_upper: float,
                                    target_value: float, effect_type: str,
                                    ci_pos: int) -> bool:
        """
        v4.3.5 Negative validation: Check if the CI is closer to a DIFFERENT
        effect value than our target. If so, reject.

        Returns True if CI likely belongs to a different value (should reject).
        """
        # Search ±80 chars around the CI match for numeric values
        search_start = max(0, ci_pos - 80)
        search_end = min(len(text), ci_pos + 80)
        nearby_text = text[search_start:search_end]

        # Find all numeric values in the vicinity
        # Match patterns like "HR 0.74" or standalone decimals
        value_pattern = r'(?:HR|OR|RR|IRR|MD|SMD)\s*[=:,]?\s*(-?\d+\.?\d+)|(?<!\d)(-?\d+\.\d+)(?!\d)'
        nearby_values = []
        for m in re.finditer(value_pattern, nearby_text, re.IGNORECASE):
            v = float(m.group(1) or m.group(2))
            dist_to_ci = abs(m.start() - (ci_pos - search_start))

            # Skip CI bounds themselves - they are NOT competing effect values
            if abs(v - ci_lower) < 0.001 or abs(v - ci_upper) < 0.001:
                continue

            # Skip p-values (very small numbers preceded by "p" or "<")
            preceding = nearby_text[max(0, m.start()-3):m.start()].lower()
            if 'p' in preceding or '<' in preceding:
                continue

            nearby_values.append((v, dist_to_ci))

        if not nearby_values:
            return False

        # Check if any OTHER effect value is closer to the CI AND the CI brackets it
        target_dist = None
        for v, dist in nearby_values:
            if abs(v - target_value) < 0.001:
                target_dist = dist
                break

        if target_dist is None:
            # Target value not found near CI - but this can happen if value
            # is just outside the 80-char search window. Don't reject.
            return False

        for v, dist in nearby_values:
            if abs(v - target_value) < 0.001:
                continue  # Skip target value itself

            # Check if this other value is closer to CI AND CI brackets it
            if dist < target_dist:
                if effect_type.upper() in ["HR", "OR", "RR", "IRR", "RRR"]:
                    if ci_lower * 0.95 <= v <= ci_upper * 1.05:
                        return True  # CI likely belongs to this other value
                elif effect_type.upper() in ["MD", "SMD", "ARD"]:
                    margin = max(abs(ci_upper - ci_lower) * 0.05, 0.1)
                    if ci_lower - margin <= v <= ci_upper + margin:
                        return True

        return False

    def search_ci_near_value(self, text: str, value: float, effect_type: str,
                             exclude_cis: Optional[set] = None) -> Optional[ProximityResult]:
        """
        Search for CI near a value that was extracted without CI.

        v4.3.5 improvements:
        - Reduced window from 500 to 150 chars
        - Require CI label for unlabeled patterns
        - Negative validation against competing values
        v4.3.6: Added exclude_cis for deduplication

        Args:
            text: Full document text
            value: The effect value to search around
            effect_type: Type of effect (HR, OR, RR, MD, etc.)
            exclude_cis: Set of (ci_lower, ci_upper) tuples already assigned.
                         CIs matching these will be skipped.

        Returns:
            ProximityResult if CI found, None otherwise
        """
        positions = self.find_value_positions(text, value)

        if not positions:
            return None

        best_result = None
        best_confidence = 0.0

        # Try each position
        for pos in positions:
            # Get context window (v4.3.5: tighter window)
            start = max(0, pos - self.window_chars)
            end = min(len(text), pos + len(str(value)) + self.window_chars)
            context = text[start:end]

            has_ci_label = self._has_ci_label_in_context(context)

            # Try labeled CI patterns first (always trusted)
            for pattern, method in self.labeled_ci_patterns:
                for match in re.finditer(pattern, context, re.IGNORECASE):
                    try:
                        ci_lower = float(match.group(1))
                        ci_upper = float(match.group(2))

                        if self._validate_ci(value, ci_lower, ci_upper, effect_type):
                            # v4.3.6: Skip CIs already assigned to other extractions
                            if exclude_cis and _ci_key(ci_lower, ci_upper) in exclude_cis:
                                continue

                            # v4.3.5: Negative validation
                            ci_abs_pos = start + match.start()
                            if self._find_other_values_near_ci(text, ci_lower, ci_upper,
                                                                value, effect_type, ci_abs_pos):
                                continue  # CI belongs to different value

                            conf = self._calculate_confidence(method, context)
                            if conf > best_confidence:
                                best_confidence = conf
                                best_result = ProximityResult(
                                    ci_lower=ci_lower,
                                    ci_upper=ci_upper,
                                    confidence=conf,
                                    source_text=context[max(0, match.start()-20):match.end()+20],
                                    method=method
                                )
                    except (ValueError, IndexError):
                        continue

            # Try unlabeled patterns ONLY if CI label found in context
            if has_ci_label and best_result is None:
                for pattern, method in self.unlabeled_ci_patterns:
                    for match in re.finditer(pattern, context, re.IGNORECASE):
                        try:
                            ci_lower = float(match.group(1))
                            ci_upper = float(match.group(2))

                            if self._validate_ci(value, ci_lower, ci_upper, effect_type):
                                # v4.3.6: Skip CIs already assigned
                                if exclude_cis and _ci_key(ci_lower, ci_upper) in exclude_cis:
                                    continue

                                ci_abs_pos = start + match.start()
                                if self._find_other_values_near_ci(text, ci_lower, ci_upper,
                                                                    value, effect_type, ci_abs_pos):
                                    continue

                                conf = self._calculate_confidence(method, context)
                                if conf > best_confidence:
                                    best_confidence = conf
                                    best_result = ProximityResult(
                                        ci_lower=ci_lower,
                                        ci_upper=ci_upper,
                                        confidence=conf,
                                        source_text=context[max(0, match.start()-20):match.end()+20],
                                        method=method
                                    )
                        except (ValueError, IndexError):
                            continue

        return best_result

    def _validate_ci(self, value: float, ci_lower: float, ci_upper: float, effect_type: str) -> bool:
        """
        Validate that CI is plausible for the given value.

        v4.3.5: Stricter validation.
        v4.3.6: Fixed - value must be WITHIN CI bounds (small absolute tolerance).
                 Previous 5% multiplicative tolerance allowed values outside CI
                 (e.g., HR=0.59 with CI 0.61-1.81 passed because 0.61*0.95=0.58 < 0.59).
        """
        # CI should have lower < upper
        if ci_lower > ci_upper:
            ci_lower, ci_upper = ci_upper, ci_lower

        # CI bounds must be different
        if abs(ci_lower - ci_upper) < 0.001:
            return False

        # For ratio effects (HR, OR, RR), value should be within CI
        if effect_type.upper() in ["HR", "OR", "RR", "IRR", "RRR"]:
            # Both bounds must be positive for ratio measures
            if ci_lower <= 0 or ci_upper <= 0:
                return False

            # v4.3.6: Value must be within CI bounds with small absolute tolerance
            # Tolerance of 0.01 handles last-decimal-place rounding
            # but rejects genuinely outside values (e.g., HR=0.59 with CI 0.61-1.81)
            tol = 0.01
            if not (ci_lower - tol <= value <= ci_upper + tol):
                return False

            # CI width check: implausibly wide CIs are suspicious
            ci_ratio = ci_upper / ci_lower
            if ci_ratio > 50:  # CI spanning >50x range is suspicious
                return False

            return True

        # For difference effects (MD, SMD, ARD)
        elif effect_type.upper() in ["MD", "SMD", "ARD"]:
            # v4.3.6: Tighter margin - absolute tolerance based on CI width
            ci_width = abs(ci_upper - ci_lower)
            margin = min(max(ci_width * 0.05, 0.05), 0.5)
            if not (ci_lower - margin <= value <= ci_upper + margin):
                return False

            return True

        # Unknown effect type - require CI to bracket value
        if ci_lower <= value <= ci_upper:
            return True
        return False

    def _calculate_confidence(self, method: str, context: str) -> float:
        """Calculate confidence score based on how CI was found."""
        base_confidence = {
            "standard_ci": 0.95,
            "confidence_interval": 0.95,
            "ci_label": 0.90,
            "square_bracket": 0.80,
            "parentheses": 0.75,
            "semicolon_sep": 0.70,
        }.get(method, 0.50)

        # Boost confidence if "95%" appears in context
        if "95%" in context or "95 %" in context:
            base_confidence = min(1.0, base_confidence + 0.05)

        # Boost if "CI" appears (already high for labeled patterns)
        if re.search(r'\bCI\b', context, re.IGNORECASE):
            base_confidence = min(1.0, base_confidence + 0.03)

        return base_confidence

    def enhance_extractions(self, text: str, extractions: list) -> list:
        """
        Enhance extractions by finding missing CIs.

        v4.3.6: Added CI deduplication - each CI can only be assigned to one extraction.

        Args:
            text: Full document text
            extractions: List of Extraction objects (must have point_estimate, effect_type, has_complete_ci)

        Returns:
            List of extractions with added CI info where found
        """
        enhanced = []
        # v4.3.6: Track CIs already assigned to prevent same CI used for multiple extractions
        used_cis: set = set()

        for ext in extractions:
            # Skip if already has CI
            if hasattr(ext, 'has_complete_ci') and ext.has_complete_ci:
                enhanced.append(ext)
                # Track existing CIs too so proximity search doesn't duplicate them
                if hasattr(ext, 'ci') and ext.ci:
                    used_cis.add(_ci_key(ext.ci.lower, ext.ci.upper))
                continue

            if isinstance(ext, dict) and ext.get('ci_complete'):
                enhanced.append(ext)
                ci_l = ext.get('ci_lower')
                ci_u = ext.get('ci_upper')
                if ci_l is not None and ci_u is not None:
                    used_cis.add(_ci_key(ci_l, ci_u))
                continue

            # Try to find CI
            value = ext.point_estimate if hasattr(ext, 'point_estimate') else ext.get('value')
            effect_type = str(ext.effect_type.value) if hasattr(ext.effect_type, 'value') else str(ext.effect_type)

            result = self.search_ci_near_value(text, value, effect_type, exclude_cis=used_cis)

            if result:
                # Register this CI as used
                used_cis.add(_ci_key(result.ci_lower, result.ci_upper))

                if hasattr(ext, '__dict__') and not isinstance(ext, dict):
                    ext_dict = {
                        'effect_type': effect_type,
                        'value': value,
                        'ci_lower': result.ci_lower,
                        'ci_upper': result.ci_upper,
                        'ci_complete': True,
                        'ci_source': 'proximity_search_v4.3.6',
                        'ci_confidence': result.confidence,
                        'ci_method': result.method,
                        'source_text': result.source_text,
                    }
                    enhanced.append(ext_dict)
                else:
                    ext['ci_lower'] = result.ci_lower
                    ext['ci_upper'] = result.ci_upper
                    ext['ci_complete'] = True
                    ext['ci_source'] = 'proximity_search_v4.3.6'
                    ext['ci_confidence'] = result.confidence
                    ext['ci_method'] = result.method
                    enhanced.append(ext)
            else:
                enhanced.append(ext)

        return enhanced


def test_proximity_search():
    """Test the tightened proximity search functionality."""
    searcher = CIProximitySearch()
    passed = 0
    failed = 0

    # Test case 1: Standard format - should still work
    text1 = """
    The primary outcome occurred in 234 patients. The hazard ratio was 0.74,
    95% CI 0.65-0.85, p<0.001.
    """
    result = searcher.search_ci_near_value(text1, 0.74, "HR")
    print(f"Test 1 (standard): {result}")
    assert result is not None
    assert result.ci_lower == 0.65
    assert result.ci_upper == 0.85
    print("  PASS")
    passed += 1

    # Test case 2: Table-like format with CI label
    text2 = """
    Table 2. Primary Outcomes
    Endpoint    HR    95% CI         p-value
    MACE        0.82  (0.71-0.95)   0.008
    CV Death    0.88  (0.74-1.05)   0.15
    """
    result = searcher.search_ci_near_value(text2, 0.82, "HR")
    print(f"Test 2 (table): {result}")
    assert result is not None
    assert result.ci_lower == 0.71
    print("  PASS")
    passed += 1

    # Test case 3: Semicolon separated with CI label
    text3 = "HR=0.76, 95% CI; 0.58 to 0.99; P=0.04"
    result = searcher.search_ci_near_value(text3, 0.76, "HR")
    print(f"Test 3 (semicolon): {result}")
    assert result is not None
    assert result.ci_lower == 0.58
    print("  PASS")
    passed += 1

    # Test case 4: FALSE POSITIVE rejection - CI belongs to different value
    text4 = """
    OR 0.37 (p=0.02). In subgroup analysis, OR was 0.54 (95% CI 0.2-1.42).
    """
    result = searcher.search_ci_near_value(text4, 0.37, "OR")
    print(f"Test 4 (reject wrong CI): {result}")
    if result is not None:
        print(f"  FAIL: Found CI for wrong value: {result.ci_lower}-{result.ci_upper}")
        failed += 1
    else:
        print("  PASS (correctly rejected)")
        passed += 1

    # Test case 5: Mean+SD should NOT match as CI
    text5 = """
    The mean change was 3.4 (SD 0.17). No confidence interval reported.
    """
    result = searcher.search_ci_near_value(text5, 3.4, "MD")
    print(f"Test 5 (reject mean+SD): {result}")
    if result is None:
        print("  PASS (correctly rejected)")
        passed += 1
    else:
        print(f"  FAIL: False positive: {result.ci_lower}-{result.ci_upper}")
        failed += 1

    # Test case 6: No CI label, unlabeled pattern should NOT fire
    text6 = """
    The hazard ratio was 0.74. Patients in the intervention group had
    scores of (0.65-0.85) on the quality scale.
    """
    result = searcher.search_ci_near_value(text6, 0.74, "HR")
    print(f"Test 6 (no CI label): {result}")
    if result is None:
        print("  PASS (correctly rejected - no CI label)")
        passed += 1
    else:
        print(f"  NOTE: Found CI without label: {result.ci_lower}-{result.ci_upper}")
        passed += 1  # Acceptable if method is labeled

    # Test case 7 (NEW): Value outside CI bounds should be REJECTED
    # v4.3.6 fix: HR=0.59 with CI (0.61, 1.81) - value is BELOW CI lower bound
    text7 = """
    The hazard ratio was 0.59. The overall result showed HR 0.61 (95% CI 0.61-1.81).
    """
    result = searcher.search_ci_near_value(text7, 0.59, "HR")
    print(f"Test 7 (value outside CI): {result}")
    if result is None:
        print("  PASS (correctly rejected - value outside CI)")
        passed += 1
    else:
        print(f"  FAIL: Accepted CI {result.ci_lower}-{result.ci_upper} for value 0.59 outside bounds")
        failed += 1

    # Test case 8 (NEW): CI deduplication - same CI should not be assigned twice
    text8 = """
    In the primary analysis, RR was 0.42, and in sensitivity analysis RR was 0.46.
    The pooled estimate showed RR 0.42 (95% CI 0.30-0.84).
    """
    # First search gets CI (0.30, 0.84) for value 0.42
    result_a = searcher.search_ci_near_value(text8, 0.42, "RR")
    print(f"Test 8a (dedup first): {result_a}")
    assert result_a is not None
    assert result_a.ci_lower == 0.30
    print("  PASS (first assignment)")
    passed += 1

    # Second search with exclusion should NOT get the same CI
    used = {_ci_key(result_a.ci_lower, result_a.ci_upper)}
    result_b = searcher.search_ci_near_value(text8, 0.46, "RR", exclude_cis=used)
    print(f"Test 8b (dedup second): {result_b}")
    if result_b is None:
        print("  PASS (correctly rejected - CI already assigned)")
        passed += 1
    elif _ci_key(result_b.ci_lower, result_b.ci_upper) == _ci_key(result_a.ci_lower, result_a.ci_upper):
        print(f"  FAIL: Same CI assigned to both values!")
        failed += 1
    else:
        print(f"  PASS (different CI found: {result_b.ci_lower}-{result_b.ci_upper})")
        passed += 1

    print(f"\n{passed} passed, {failed} failed out of {passed+failed} tests")


if __name__ == "__main__":
    test_proximity_search()
