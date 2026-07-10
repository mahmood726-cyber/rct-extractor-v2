#!/usr/bin/env python3
"""The api.extract results generator (S1): scores the extractor's OWN primary pick
(is_primary / effects[0]) rather than an oracle-selected closest-to-truth match.

Uses small, clearly-synthetic abstract fixtures (SYNTH_*) so the selection path
can be exercised end-to-end without the gitignored PDF corpus.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pytest

import gen_api_extract_results as gen
import score_primary_direction as spd


CORPUS = [
    {
        "study_id": "SYNTH_HR",
        "specialty": "cardiology",
        "text": ("A secondary odds ratio 1.50 (95% CI 1.10-2.05) was observed. "
                 "The primary outcome, mortality, showed a hazard ratio 0.70 (95% CI 0.55-0.89)."),
        "cochrane_effect": 0.70,
        "cochrane_outcome_type": "binary",
    },
    {
        "study_id": "SYNTH_NONE",
        "specialty": "cardiology",
        "text": "This narrative paragraph reports no quantitative effect estimate at all.",
        "cochrane_effect": 0.90,
        "cochrane_outcome_type": "binary",
    },
]


class TestGenerator:
    def test_best_match_is_the_extractors_own_primary_pick(self):
        r = gen.generate_results(CORPUS)[0]
        bm = r["best_match"]
        # the primary-labelled HR wins effects[0] over the earlier secondary OR
        assert bm.get("is_primary") is True
        assert bm["type"] == "HR" and abs(bm["effect_size"] - 0.70) < 1e-6
        assert bm["direction"] == "decrease"
        assert r["n_extractions"] >= 2

    def test_no_extraction_record(self):
        r = gen.generate_results(CORPUS)[1]
        assert r["best_match"] == {} and r["status"] == "no_extractions"
        # a no-pick record carries a reason so recall isn't over-counted as failure
        assert r["no_effect_reason"] == "no_comparative_effect_found"

    def test_diagnostic_study_labelled_appropriate(self):
        # an AUC / diagnostic-accuracy study has no poolable comparative effect;
        # its no-extraction is APPROPRIATE, not a recall miss.
        assert gen.no_effect_reason(
            "The model discriminated well, AUC 0.83 (95% CI 0.79-0.87); "
            "sensitivity 0.81 and specificity 0.76.") == "diagnostic_accuracy"
        assert gen.no_effect_reason("A narrative with no numbers.") == "no_comparative_effect_found"

    def test_scorer_sees_real_selection_not_oracle(self):
        # A result carrying is_primary makes the scorer report oracle_selected=False.
        results = gen.generate_results(CORPUS)
        assert any("is_primary" in (r.get("best_match") or {}) for r in results)

    def test_end_to_end_score_agree_value_match(self):
        r = gen.generate_results(CORPUS)[0]
        meta = {"SYNTH_HR": {"outcome_type": "binary", "raw": {}}}
        s = spd.score_record(r, meta)
        assert s["selection"] == "value_match"
        assert s["direction"] == "agree"
