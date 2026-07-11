#!/usr/bin/env python3
"""Value-only mean-difference patterns must not capture the CONFIDENCE LEVEL as the
value. A table header like "Mean difference (95% CIs)" was yielding a spurious
MD 95 (a garbage effect that pollutes a meta-analysis and can register as a
direction sign-flip). Found via the real efetch-based selection eval (Keene_2022).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from rct_extractor._engine.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict


@pytest.fixture(scope="module")
def ex():
    return EnhancedExtractor()


def _mds(ex, text):
    return [to_dict(x)["effect_size"] for x in ex.extract(text) if to_dict(x)["type"] == "MD"]


class TestMdCiLevelGuard:
    @pytest.mark.parametrize("text", [
        "the mean difference 95% CIs OMAS",
        "Mean difference (95% CIs)",
        "weighted mean difference 95% CI",
        "between-group difference 95% confidence interval",
    ])
    def test_ci_level_not_captured_as_md(self, ex, text):
        # no bare CI-level should surface as an MD value
        assert 95.0 not in _mds(ex, text) and 9.0 not in _mds(ex, text)

    @pytest.mark.parametrize("text,val", [
        ("mean difference 3.2 (95% CI 1.1 to 5.3)", 3.2),
        ("The mean difference was 4.5 (95% CI 1.2 to 7.8)", 4.5),
        ("Calculated MD: -58.000", -58.0),
    ])
    def test_legit_md_still_extracted(self, ex, text, val):
        assert any(abs(v - val) < 1e-6 for v in _mds(ex, text))


class TestBareRegressionCoefNotMd:
    """A bare regression coefficient (beta/B = X) with NO CI is not a poolable mean
    difference. Extracting it as a value-only MD made it win effects[0] over the real
    primary and register as a sign-flip on the real eval (raised direction accuracy
    31.2% -> 41.7% when removed). Coefficients reported WITH a CI still extract."""

    @pytest.mark.parametrize("text", [
        "The coefficient b = 0.29 for the model.",
        "beta = 6 in the adjusted regression",
        "beta=0.20 (standardized)",
        "B = -3.61 in the model",
    ])
    def test_bare_coef_not_extracted_as_md(self, ex, text):
        assert _mds(ex, text) == []

    @pytest.mark.parametrize("text,val", [
        ("beta = 0.5 (95% CI 0.2 to 0.8)", 0.5),
        ("beta = 1.2, 95% CI 0.4 to 2.0", 1.2),
    ])
    def test_coef_with_ci_still_extracted(self, ex, text, val):
        assert any(abs(v - val) < 1e-6 for v in _mds(ex, text))
