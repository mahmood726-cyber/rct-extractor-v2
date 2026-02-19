"""Regression tests for scientific-notation p-value parsing."""

import math

from src.core.enhanced_extractor_v3 import extract_p_value


def test_extract_p_value_e_notation():
    """P-values in e-notation should parse to the correct magnitude."""
    result = extract_p_value("P = 1.2e-5")
    assert result is not None
    assert math.isclose(result, 1.2e-5, rel_tol=0, abs_tol=1e-12)


def test_extract_p_value_coefficient_times_ten_notation():
    """P-values in coefficient x 10^-k notation should parse."""
    result = extract_p_value("P = 1 x 10^-4")
    assert result is not None
    assert math.isclose(result, 1e-4, rel_tol=0, abs_tol=1e-12)


def test_extract_p_value_ten_power_notation():
    """P-values in 10^-k notation without coefficient should parse."""
    result = extract_p_value("P < 10^-6")
    assert result is not None
    assert math.isclose(result, 1e-6, rel_tol=0, abs_tol=1e-12)


def test_extract_p_value_decimal_still_parses():
    """Standard decimal p-value parsing should remain intact."""
    result = extract_p_value("P = 0.002")
    assert result == 0.002
