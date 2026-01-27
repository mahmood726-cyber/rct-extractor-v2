"""
Tests for NumericParser - validates extraction patterns against real-world text
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.extractor import NumericParser


class TestHazardRatioParser:
    """Tests for HR pattern extraction"""

    def test_standard_hr_format(self):
        """Standard HR with parenthetical CI"""
        text = "The hazard ratio was 0.80 (95% CI, 0.67 to 0.95)"
        result = NumericParser.parse_hazard_ratio(text)
        assert result is not None
        assert result['hr'] == 0.80
        assert result['ci_low'] == 0.67
        assert result['ci_high'] == 0.95

    def test_hr_with_dash_ci(self):
        """HR with dash-separated CI"""
        text = "HR 0.74 (95% CI 0.65-0.85)"
        result = NumericParser.parse_hazard_ratio(text)
        assert result is not None
        assert result['hr'] == 0.74
        assert result['ci_low'] == 0.65
        assert result['ci_high'] == 0.85

    def test_hr_equals_format(self):
        """HR with equals sign"""
        text = "HR = 0.68; 95% CI, 0.57 to 0.82"
        result = NumericParser.parse_hazard_ratio(text)
        assert result is not None
        assert result['hr'] == 0.68

    def test_hr_bracket_format(self):
        """HR with square bracket CI"""
        text = "HR = 0.75 [95% CI: 0.62-0.90]"
        result = NumericParser.parse_hazard_ratio(text)
        assert result is not None
        assert result['hr'] == 0.75
        assert result['ci_low'] == 0.62
        assert result['ci_high'] == 0.90

    def test_unicode_minus(self):
        """Handle Unicode minus sign"""
        text = "HR 0.80 (95% CI, 0.67−0.95)"  # Unicode minus
        result = NumericParser.parse_hazard_ratio(text)
        assert result is not None
        assert result['hr'] == 0.80

    def test_nejm_format(self):
        """NEJM typical format"""
        text = "cardiovascular death (hazard ratio, 0.62; 95% CI, 0.49 to 0.77)"
        result = NumericParser.parse_hazard_ratio(text)
        assert result is not None
        assert result['hr'] == 0.62
        assert result['ci_low'] == 0.49
        assert result['ci_high'] == 0.77

    def test_lancet_format(self):
        """Lancet typical format"""
        text = "Hazard ratio 0·83 (95% CI 0·73–0·95)"  # Middle dot for decimal
        result = NumericParser.parse_hazard_ratio(text)
        assert result is not None
        assert result['hr'] == 0.83

    def test_no_hr_in_text(self):
        """Text without HR returns None"""
        text = "The mean age was 65 years."
        result = NumericParser.parse_hazard_ratio(text)
        assert result is None


class TestEventsParser:
    """Tests for events/n extraction"""

    def test_events_slash_format(self):
        """Standard events/n format"""
        text = "265/2500 (10.6%)"
        result = NumericParser.parse_events_n(text)
        assert result is not None
        assert result['events'] == 265
        assert result['n'] == 2500

    def test_events_parenthetical(self):
        """Events with parenthetical percentage"""
        text = "There were 187 deaths (7.5%)"
        result = NumericParser.parse_events_n(text)
        assert result is not None
        assert result['events'] == 187


class TestPValueParser:
    """Tests for p-value extraction"""

    def test_p_equals(self):
        """P = value format"""
        text = "p = 0.001"
        result = NumericParser.parse_p_value(text)
        assert result is not None
        assert result[0] == 0.001

    def test_p_less_than(self):
        """P < value format"""
        text = "P < 0.001"
        result = NumericParser.parse_p_value(text)
        assert result is not None
        assert result[0] == 0.001

    def test_p_value_word(self):
        """P-value = format"""
        text = "p-value = 0.012"
        result = NumericParser.parse_p_value(text)
        assert result is not None
        assert result[0] == 0.012


class TestRealWorldText:
    """Tests using actual text from major journals"""

    def test_paradigm_hf_primary(self):
        """PARADIGM-HF primary outcome"""
        text = "The hazard ratio was 0.80 (95% confidence interval [CI], 0.73 to 0.87; P<0.001)"
        hr = NumericParser.parse_hazard_ratio(text)
        pval = NumericParser.parse_p_value(text)

        assert hr is not None
        assert hr['hr'] == 0.80
        assert hr['ci_low'] == 0.73
        assert hr['ci_high'] == 0.87
        assert pval is not None
        assert pval[0] == 0.001

    def test_emperor_reduced_primary(self):
        """EMPEROR-Reduced primary outcome"""
        text = "hazard ratio, 0.75; 95% CI, 0.65 to 0.86; P<0.001"
        hr = NumericParser.parse_hazard_ratio(text)

        assert hr is not None
        assert hr['hr'] == 0.75
        assert hr['ci_low'] == 0.65
        assert hr['ci_high'] == 0.86

    def test_dapa_hf_primary(self):
        """DAPA-HF primary outcome"""
        text = "HR 0.74 (95% CI 0.65-0.85)"
        hr = NumericParser.parse_hazard_ratio(text)

        assert hr is not None
        assert hr['hr'] == 0.74
        assert hr['ci_low'] == 0.65
        assert hr['ci_high'] == 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
