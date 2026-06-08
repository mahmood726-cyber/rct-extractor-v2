"""Tests for the system integrations (allmeta ma-studies-v1, Beast Trials)."""
import math

import pytest

from rct_extractor.integrations import allmeta, beast
from rct_extractor.integrations._common import (
    Z975,
    effect_to_est_se,
    pick_effect,
    twobytwo_to_est_se,
)

HR_ABSTRACT = "The primary endpoint had a hazard ratio of 0.62 (95% CI 0.45-0.85)."
TWO_BY_TWO = (
    "Cardiovascular death occurred in 30/200 (15.0%) in the empagliflozin group "
    "and 50/200 (25.0%) in the placebo group."
)


# ---- _common ----------------------------------------------------------------

def test_effect_to_est_se_ratio_is_log_scale():
    est, se = effect_to_est_se({"type": "HR", "effect_size": 0.62,
                                "ci_lower": 0.45, "ci_upper": 0.85})
    assert abs(est - math.log(0.62)) < 1e-9
    expected_se = (math.log(0.85) - math.log(0.45)) / (2 * Z975)
    assert abs(se - expected_se) < 1e-9


def test_effect_to_est_se_difference_is_natural_scale():
    est, se = effect_to_est_se({"type": "MD", "effect_size": -0.8,
                                "ci_lower": -1.2, "ci_upper": -0.4})
    assert abs(est - (-0.8)) < 1e-9
    assert abs(se - ((-0.4 - -1.2) / (2 * Z975))) < 1e-9


def test_effect_to_est_se_rejects_missing_ci():
    assert effect_to_est_se({"type": "HR", "effect_size": 0.62}) is None


def test_twobytwo_logor_no_zero_cell():
    table = {"arm1": {"events": 30, "total": 200}, "arm2": {"events": 50, "total": 200}}
    est, se = twobytwo_to_est_se(table, "OR")
    # OR = (30*150)/(170*50)
    expected = math.log((30 * 150) / (170 * 50))
    assert abs(est - expected) < 1e-9
    assert se > 0


def test_twobytwo_zero_cell_gets_correction():
    table = {"arm1": {"events": 0, "total": 100}, "arm2": {"events": 10, "total": 100}}
    res = twobytwo_to_est_se(table, "OR")
    assert res is not None and math.isfinite(res[0])  # 0.5 correction applied


def test_pick_effect_prefers_measure_and_endpoint():
    effects = [
        {"type": "RR", "endpoint": "MORTALITY", "ci_lower": 1, "ci_upper": 2, "effect_size": 1.5},
        {"type": "HR", "endpoint": "CV_DEATH", "ci_lower": 0.4, "ci_upper": 0.8, "effect_size": 0.6},
    ]
    e = pick_effect(effects, endpoint="CV_DEATH", measure="HR")
    assert e["type"] == "HR" and e["endpoint"] == "CV_DEATH"


# ---- allmeta (ma-studies-v1) ------------------------------------------------

def test_to_ma_studies_schema_and_shape():
    recs = [
        {"label": "FIDELIO", "text": HR_ABSTRACT, "year": 2020},
        {"label": "FIGARO", "text": "HR 0.87 (95% CI 0.76-0.98).", "year": 2021},
    ]
    payload = allmeta.to_ma_studies(recs, measure="HR", saved_at="2026-06-08T00:00:00Z")
    assert payload["_schema"] == "ma-studies-v1"
    assert payload["_savedAt"] == "2026-06-08T00:00:00Z"
    assert len(payload["studies"]) == 2
    s0 = payload["studies"][0]
    assert s0["label"] == "FIDELIO" and s0["year"] == 2020.0
    assert math.isfinite(s0["est"]) and s0["se"] > 0
    assert abs(s0["est"] - math.log(0.62)) < 1e-9  # log scale


def test_to_ma_studies_uses_2x2_for_or():
    recs = [{"label": "T1", "text": TWO_BY_TWO}, {"label": "T2", "text": TWO_BY_TWO}]
    payload = allmeta.to_ma_studies(recs, specialty="diabetes", measure="OR")
    assert len(payload["studies"]) == 2
    assert all(s["se"] > 0 for s in payload["studies"])


def test_to_ma_studies_validates_against_js_contract():
    # mirror the validation rules in shared/ma-studies-v1.js
    recs = [{"label": "T1", "text": HR_ABSTRACT}, {"label": "T2", "text": HR_ABSTRACT}]
    payload = allmeta.to_ma_studies(recs, measure="HR")
    assert payload["_schema"] == "ma-studies-v1"
    assert isinstance(payload["_savedAt"], str) and payload["_savedAt"]
    for s in payload["studies"]:
        assert isinstance(s["label"], str) and s["label"]
        assert isinstance(s["est"], float) and math.isfinite(s["est"])
        assert isinstance(s["se"], float) and s["se"] > 0


# ---- Beast ------------------------------------------------------------------

def test_to_beast_trials_2x2_path():
    recs = [{"study": "EMPA-REG", "text": TWO_BY_TWO, "year": 2015}]
    trials = beast.to_beast_trials(recs, specialty="diabetes")
    assert len(trials) == 1
    t = trials[0]
    assert t["study"] == "EMPA-REG" and t["year"] == 2015
    assert (t["e_events"], t["e_n"]) == (30, 200)
    assert (t["c_events"], t["c_n"]) == (50, 200)


def test_to_beast_trials_generic_path():
    recs = [{"study": "FIDELIO", "text": HR_ABSTRACT, "year": 2020}]
    trials = beast.to_beast_trials(recs, specialty="hypertension")
    assert len(trials) == 1
    t = trials[0]
    assert "yi" in t and "sei" in t
    assert abs(t["yi"] - math.log(0.62)) < 1e-9
    assert t["sei"] > 0 and t["year"] == 2020


def test_beast_source_template_is_valid_python():
    compile(beast.BEAST_SOURCE_TEMPLATE, "<beast_source_template>", "exec")


# ---- allmeta CLI ------------------------------------------------------------

def test_allmeta_cli_writes_payload(tmp_path):
    import json
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.txt").write_text(HR_ABSTRACT, encoding="utf-8")
    (corpus / "b.txt").write_text("HR 0.87 (95% CI 0.76-0.98).", encoding="utf-8")
    out = tmp_path / "studies.json"
    rc = allmeta.main([str(corpus), "-m", "HR", "-o", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["_schema"] == "ma-studies-v1"
    assert len(payload["studies"]) == 2
