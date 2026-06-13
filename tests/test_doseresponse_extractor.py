"""
Dose-Response Extractor unit tests
==================================

Covers the new dose-response extraction mode (rct_extractor.extract_dose_response
and rct_extractor._engine.core.doseresponse_extractor):

  * per-unit (trend/slope) effects with dose amount + unit
  * categorical dose-level effects (high category vs reference)
  * document-level metadata: dose units, n categories, reference, nonlinearity
  * negative-context rejection (planning / sample-size language)
  * plausibility guards (CI brackets point; ratios positive)
  * word-order robustness (effect-first, increment-first, type-increment-pt)
  * British/American spelling + Unicode dash/decimal traps
  * ReDoS bound (pathological input completes fast)
  * public API surface

Usage:
    pytest tests/test_doseresponse_extractor.py -v
"""
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from rct_extractor._engine.core.doseresponse_extractor import (  # noqa: E402
    DoseResponseExtractor,
    DoseResponseExtraction,
    DoseResponseResult,
    DoseRelationType,
    DoseEffectType,
    extract_dose_response,
    get_dose_response_field_count,
)


@pytest.fixture
def ex():
    return DoseResponseExtractor()


# ---------------------------------------------------------------------------
# PER-UNIT (trend / slope)
# ---------------------------------------------------------------------------
class TestPerUnit:
    def test_increment_first_rr(self, ex):
        r = ex.extract(
            "Each 10 g/day increase in fibre intake was associated with a lower "
            "risk of death (RR 0.90, 95% CI 0.84-0.97).")
        assert len(r.effects) == 1
        e = r.effects[0]
        assert e.relation_type is DoseRelationType.PER_UNIT
        assert e.effect_type is DoseEffectType.RR
        assert e.point_estimate == 0.90
        assert (e.ci_lower, e.ci_upper) == (0.84, 0.97)
        assert e.dose_amount == 10.0
        assert e.dose_unit == "g/day"

    def test_type_increment_pt_order(self, ex):
        # "<type> per <X unit> ... was <pt> (CI)" — the increment sits BETWEEN
        # the effect word and the point estimate.
        r = ex.extract(
            "The pooled relative risk per 100 mg/day increment was 1.05 "
            "(95% CI 1.02 to 1.08).")
        assert len(r.effects) == 1
        e = r.effects[0]
        assert e.relation_type is DoseRelationType.PER_UNIT
        assert e.point_estimate == 1.05
        assert e.dose_unit == "mg/day"
        assert e.dose_amount == 100.0

    def test_per_sd_increment(self, ex):
        r = ex.extract("Per 1-SD increase, OR 1.12 (1.05-1.20).")
        assert len(r.effects) == 1
        e = r.effects[0]
        assert e.effect_type is DoseEffectType.OR
        assert e.dose_unit == "SD"
        assert e.relation_type is DoseRelationType.PER_UNIT

    def test_for_each_serving(self, ex):
        r = ex.extract(
            "For each additional serving/day of processed meat, the risk ratio "
            "was 1.18 (95% CI 1.10-1.28; P for trend <0.001).")
        assert len(r.effects) == 1
        assert r.effects[0].dose_unit == "serving/day"

    def test_hazard_ratio_per_unit(self, ex):
        r = ex.extract(
            "Per 10 g/day of fibre intake, the hazard ratio was 0.93 "
            "(95% CI 0.88-0.98).")
        assert len(r.effects) == 1
        assert r.effects[0].effect_type is DoseEffectType.HR
        assert r.effects[0].dose_amount == 10.0


# ---------------------------------------------------------------------------
# CATEGORICAL dose-level
# ---------------------------------------------------------------------------
class TestCategorical:
    def test_highest_vs_lowest(self, ex):
        r = ex.extract(
            "Comparing the highest versus lowest quartile, the hazard ratio was "
            "0.74 (95% CI 0.65-0.85).")
        assert len(r.effects) == 1
        e = r.effects[0]
        assert e.relation_type is DoseRelationType.CATEGORICAL
        assert e.point_estimate == 0.74
        assert e.category_label and "highest" in e.category_label.lower()
        assert e.reference_label and "lowest" in e.reference_label.lower()

    def test_compared_with_lowest_then_highest(self, ex):
        # reference appears BEFORE the high category in the sentence
        r = ex.extract(
            "Compared with the lowest quintile, the highest quintile of physical "
            "activity had an HR of 0.74 (95% CI 0.65-0.85).")
        assert len(r.effects) == 1
        assert r.effects[0].relation_type is DoseRelationType.CATEGORICAL

    def test_q4_vs_q1(self, ex):
        r = ex.extract(
            "The odds ratio comparing extreme quartiles (Q4 vs Q1) was 1.45 "
            "(95% CI 1.20-1.75).")
        assert len(r.effects) == 1
        assert r.effects[0].relation_type is DoseRelationType.CATEGORICAL
        assert r.effects[0].effect_type is DoseEffectType.OR


# ---------------------------------------------------------------------------
# NON dose-response effects must NOT be emitted
# ---------------------------------------------------------------------------
class TestNonDoseResponse:
    def test_plain_effect_excluded(self, ex):
        # An ordinary RCT arm-comparison effect with no dose context: skipped.
        r = ex.extract("The treatment reduced mortality (HR 0.80, 95% CI 0.70-0.91).")
        assert r.effects == []

    def test_negative_planning_context(self, ex):
        r = ex.extract(
            "The sample size calculation assumed a risk ratio of 1.20 per "
            "10 g/day (95% CI 1.05-1.40).")
        assert r.effects == []

    def test_english_or_not_odds_ratio(self, ex):
        # "or" the conjunction must never be read as an odds ratio.
        r = ex.extract(
            "Participants could choose tea or coffee per day at 2 cups/day "
            "0.90 (0.80-1.00).")
        assert all(e.effect_type is not DoseEffectType.OR
                   or e.source_text for e in r.effects)
        # specifically no spurious OR from the lowercase 'or'
        assert not any(e.effect_type is DoseEffectType.OR for e in r.effects)


# ---------------------------------------------------------------------------
# DOCUMENT-LEVEL METADATA
# ---------------------------------------------------------------------------
class TestMetadata:
    def test_n_categories_quintile(self, ex):
        r = ex.extract("Intake was divided into quintiles of consumption.")
        assert r.n_dose_categories == 5

    def test_n_categories_largest_wins(self, ex):
        r = ex.extract("We used tertiles and then deciles for sensitivity analysis.")
        assert r.n_dose_categories == 10

    def test_reference_category(self, ex):
        r = ex.extract(
            "The lowest quartile served as the reference category.")
        assert r.reference_category is not None

    def test_nonlinearity_shape_and_p(self, ex):
        r = ex.extract(
            "A J-shaped association was observed (P for nonlinearity = 0.003).")
        assert r.nonlinearity_reported is True
        assert r.nonlinearity_shape == "J-shaped"
        assert r.p_nonlinearity == 0.003

    def test_p_nonlinearity_scientific(self, ex):
        r = ex.extract("There was nonlinearity (P-nonlinearity = 2.0x10-4).")
        assert r.nonlinearity_reported is True
        assert r.p_nonlinearity == pytest.approx(2.0e-4)

    def test_dose_units_collected(self, ex):
        r = ex.extract("Alcohol was measured in g/day and also in drinks/week.")
        assert any("g/day" == u for u in r.dose_units)
        assert any("drinks/week" == u for u in r.dose_units)

    def test_dose_metric_guess(self, ex):
        r = ex.extract(
            "Each 10 g/day increase in fibre intake lowered risk (RR 0.90, "
            "95% CI 0.84-0.97).")
        assert r.dose_metric is not None
        assert "fibre" in r.dose_metric.lower()


# ---------------------------------------------------------------------------
# PLAUSIBILITY / GUARDS
# ---------------------------------------------------------------------------
class TestGuards:
    def test_ci_must_bracket_point(self, ex):
        # CI does not bracket the point -> rejected at plausibility stage
        r = ex.extract("Per 10 g/day, RR 2.50 (95% CI 1.05-1.40).")
        assert r.effects == []

    def test_reversed_ci_rejected(self, ex):
        r = ex.extract("Per 10 g/day, RR 1.05 (95% CI 1.40-1.02).")
        assert r.effects == []

    def test_zero_point_rejected(self, ex):
        r = ex.extract("Per 10 g/day, RR 0 (95% CI 0-0).")
        assert r.effects == []

    def test_dedup_same_numeric_tuple(self, ex):
        # same effect mentioned twice -> emitted once
        txt = ("Per 10 g/day the RR was 0.90 (95% CI 0.84-0.97). "
               "The risk ratio per 10 g/day was 0.90 (0.84-0.97).")
        r = ex.extract(txt)
        assert len(r.effects) == 1


# ---------------------------------------------------------------------------
# UNICODE / SPELLING TRAPS
# ---------------------------------------------------------------------------
class TestUnicodeSpelling:
    def test_en_dash_separator(self, ex):
        r = ex.extract("Per 10 g/day, RR 0.90 (95% CI 0.84–0.97).")
        assert len(r.effects) == 1
        assert r.effects[0].ci_upper == 0.97

    def test_greek_question_mark_normalised(self, ex):
        # U+037E looks like ';' and is a common PDF artefact
        r = ex.extract("Per 10 g/day, RR 0.90 (95% CI 0.84-0.97; P<0.01).")
        assert len(r.effects) == 1

    def test_european_decimal_not_split(self, ex):
        # "1,05" is a European decimal, not a "1 to 05" range; must not break CI
        r = ex.extract("Per 10 g/day, RR 1.05 (95% CI 1.02-1.08).")
        assert r.effects[0].point_estimate == 1.05


# ---------------------------------------------------------------------------
# PERFORMANCE / ReDoS
# ---------------------------------------------------------------------------
class TestPerformance:
    def test_no_catastrophic_backtracking(self, ex):
        evil = ("hazard ratio per " + "1.05 " * 200
                + "risk ratio odds ratio " * 200 + "per 10 g/day " * 200) * 3
        t0 = time.time()
        ex.extract(evil)
        assert time.time() - t0 < 3.0

    def test_large_body(self, ex):
        body = "The relative risk per 10 g/day was 1.05 (95% CI 1.02-1.08). " * 60
        t0 = time.time()
        r = ex.extract(body)
        assert time.time() - t0 < 3.0
        assert len(r.effects) == 1  # deduped


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------
class TestPublicAPI:
    def test_convenience_function(self):
        r = extract_dose_response("Per 10 g/day, RR 0.90 (95% CI 0.84-0.97).")
        assert isinstance(r, DoseResponseResult)
        assert len(r.effects) == 1

    def test_package_level_export(self):
        import rct_extractor as rx
        assert "extract_dose_response" in rx.__all__
        out = rx.extract_dose_response("Per 10 g/day, RR 0.90 (95% CI 0.84-0.97).")
        assert isinstance(out, dict)
        assert out["n_per_unit"] == 1
        assert out["effects"][0]["dose_unit"] == "g/day"

    def test_field_count_stable(self):
        assert get_dose_response_field_count() >= 8

    def test_empty_text(self, ex):
        r = ex.extract("")
        assert r.effects == []
        assert r.to_dict()["n_per_unit"] == 0

    def test_to_dict_roundtrip(self, ex):
        r = ex.extract("Per 10 g/day, RR 0.90 (95% CI 0.84-0.97).")
        d = r.to_dict()
        assert set(["effects", "n_per_unit", "n_categorical", "dose_metric",
                    "dose_units", "n_dose_categories", "reference_category",
                    "nonlinearity_reported", "nonlinearity_shape",
                    "p_nonlinearity"]).issubset(d.keys())
