"""
Tests for GLP-1/GIP obesity arm-level continuous extraction
(src/specialties/obesity_arm_data.py). Snippets are grounded in the flagship
trials (STEP 1-4, SURMOUNT 1-2). Endpoint: % change in body weight (negative=loss).
"""
import math
import pytest
from src.specialties.obesity_arm_data import (
    extract_obesity_arms, to_engine_rows, extract_arm_level_obesity,
)


def _one(text, **kw):
    r = extract_obesity_arms(text, **kw)
    assert r, f"expected >=1 arm from: {text!r}"
    return r[0]


def test_basic_semaglutide_with_sd():
    a = _one("At week 68, the mean change in body weight was -14.9% (SD 6.2) "
             "with semaglutide 2.4 mg (n=488).", study_id="NCT03548935")
    assert a["agent"] == "semaglutide"
    assert a["dose_mg"] == 2.4
    assert a["response_pct"] == -14.9
    assert a["sd"] == 6.2
    assert a["n"] == 488
    assert a["timepoint_weeks"] == 68
    assert a["sd_source"] == "reported_sd"
    # responseVar = sd^2 / n
    assert abs(a["response_var"] - (6.2 ** 2 / 488)) < 1e-6
    assert not a["needs_review"]


def test_sign_is_loss_negative():
    a = _one("body-weight change of -20.9% with tirzepatide 15 mg (n=630)")
    assert a["agent"] == "tirzepatide" and a["dose_mg"] == 15.0
    assert a["response_pct"] == -20.9
    assert a["sign_convention"] == "negative_is_loss"


def test_placebo_dose_zero():
    a = _one("with placebo, the mean weight change was -2.4% (SD 6.0; n=181)")
    assert a["agent"] == "placebo"
    assert a["dose_mg"] == 0.0


def test_sd_recovered_from_se():
    a = _one("mean weight reduction was -12.4% (SE 0.5) with semaglutide 2.4 mg, n=200")
    assert a["sd_source"] == "from_se"
    assert abs(a["sd"] - 0.5 * math.sqrt(200)) < 1e-3


def test_sd_recovered_from_ci():
    a = _one("change in body weight -15.0% (95% CI -16.1 to -13.9) with "
             "tirzepatide 10 mg, n=300")
    assert a["sd_source"] == "from_ci"
    expected_sd = math.sqrt(300) * ((-13.9) - (-16.1)) / (2 * 1.959963984540054)
    assert abs(a["sd"] - expected_sd) < 1e-2


def test_variance_unrecoverable_flagged():
    # no SD/SE/CI and no n -> cannot recover variance -> flagged, engine drops it
    a = _one("weight change was -16.0% with retatrutide 12 mg")
    assert a["sd"] is None and a["response_var"] is None
    assert "variance_unrecoverable" in a["flags"] and a["needs_review"]
    assert to_engine_rows([a]) == []


def test_dose_negation_guard_week_not_dose():
    # "week 68" must NOT be parsed as a 68 mg dose
    a = _one("at week 68 the body weight change was -14.9% (SD 6.2) with "
             "semaglutide 2.4 mg (n=488)")
    assert a["dose_mg"] == 2.4


def test_ls_mean_detected():
    a = _one("least-squares mean change in body weight was -21.1% (SE 0.4) with "
             "tirzepatide 15 mg (n=630)")
    assert a["stat"] == "LS_MEAN"


def test_plain_mean_when_no_lsmean_cue():
    a = _one("mean body weight change -14.9% (SD 6.2), semaglutide 2.4 mg, n=488")
    assert a["stat"] == "MEAN"


def test_excluded_pre2010_agent_flagged():
    rows = extract_obesity_arms(
        "weight change was -8.0% (SD 5.0) with dulaglutide 4.5 mg, n=100")
    # dulaglutide is not a node -> not tagged as an agent, so no row OR flagged
    # if some other agent token is nearby. Here no post-2010 agent -> no rows.
    assert rows == []


def test_positive_change_for_active_arm_flagged():
    a = _one("body weight change of +1.2% (SD 4.0) with semaglutide 2.4 mg, n=50")
    assert "positive_change_for_active_arm" in a["flags"]


def test_requires_weight_cue():
    # a percentage with no weight cue is ignored (e.g. an adverse-event rate)
    assert extract_obesity_arms(
        "nausea occurred in 2.4% of the semaglutide 2.4 mg group") == []
    assert extract_obesity_arms(
        "44.2% of participants had nausea with semaglutide 2.4 mg") == []


def test_implausible_percent_rejected():
    assert extract_obesity_arms(
        "body weight change was -250% with tirzepatide 15 mg") == []


def test_engine_rows_schema_and_filtering():
    text = ("At week 72, least-squares mean change in body weight was -20.9% "
            "(SE 0.5) with tirzepatide 15 mg (n=630); with placebo it was "
            "-3.1% (SE 0.4; n=470).")
    res = extract_arm_level_obesity(text, study_id="NCT04184622")
    assert res["n_arms"] == 2
    rows = res["engine_rows"]
    assert len(rows) == 2
    for r in rows:
        assert set(r) >= {"study", "agent", "dose", "response", "n", "responseVar"}
        assert r["study"] == "NCT04184622"
    placebo = [r for r in rows if r["agent"] == "placebo"][0]
    assert placebo["dose"] == 0.0


def test_empty_and_none():
    assert extract_obesity_arms("") == []
    assert extract_obesity_arms(None) == []


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
