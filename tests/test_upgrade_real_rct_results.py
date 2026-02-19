from scripts.upgrade_real_rct_results import (
    _apply_assumed_se_fallback,
    _build_reference_fallback,
    _backfill_uncertainty_from_page,
    _classify_result,
    _fallback_effect_type,
    _has_uncertainty,
    _infer_page_number,
    _match_best_extraction,
    _parse_id_filter,
    _select_candidate,
    _seed_match_is_usable,
)


def test_seed_match_rejected_when_gold_type_is_strict_and_mismatched() -> None:
    record = {"gold": {"effect_type": "OR", "point_estimate": 1.5}, "cochrane_outcome_type": "binary"}
    seed_best = {"type": "MD", "effect_size": 1.5}

    assert _seed_match_is_usable(seed_best, record) is False


def test_match_best_extraction_rejects_strict_type_mismatch() -> None:
    record = {"gold": {"effect_type": "OR", "point_estimate": 1.5}, "cochrane_outcome_type": "binary"}
    extractions = [{"type": "MD", "effect_size": 1.5, "ci_lower": 1.0, "ci_upper": 2.0}]

    best, distance, status = _match_best_extraction(extractions, record)

    assert best is None
    assert distance is None
    assert status == "no_match"


def test_parse_id_filter_returns_none_when_empty() -> None:
    assert _parse_id_filter(None) is None
    assert _parse_id_filter("") is None
    assert _parse_id_filter("  ,  ") is None


def test_parse_id_filter_parses_csv_and_trims() -> None:
    assert _parse_id_filter(" A1, B2 ,,C3 ") == {"A1", "B2", "C3"}


def test_has_uncertainty_true_for_ci_or_se() -> None:
    assert _has_uncertainty({"ci_lower": 0.8, "ci_upper": 1.2}) is True
    assert _has_uncertainty({"standard_error": 0.1}) is True
    assert _has_uncertainty({"ci_lower": None, "ci_upper": None, "standard_error": None}) is False


def test_select_candidate_prefers_uncertainty_within_tolerance() -> None:
    seed = {"effect_size": 1.0, "ci_lower": None, "ci_upper": None, "standard_error": None}
    rerun = {"effect_size": 1.01, "ci_lower": 0.9, "ci_upper": 1.1, "standard_error": 0.05}
    selected, _, picked = _select_candidate(
        seed_best=seed,
        seed_distance=0.0,
        rerun_best=rerun,
        rerun_distance=0.02,
        uncertainty_distance_tolerance=0.05,
    )
    assert selected == rerun
    assert picked is True


def test_select_candidate_keeps_seed_when_rerun_uncertainty_too_far() -> None:
    seed = {"effect_size": 1.0, "ci_lower": None, "ci_upper": None, "standard_error": None}
    rerun = {"effect_size": 1.2, "ci_lower": 1.0, "ci_upper": 1.4, "standard_error": 0.1}
    selected, _, picked = _select_candidate(
        seed_best=seed,
        seed_distance=0.0,
        rerun_best=rerun,
        rerun_distance=0.2,
        uncertainty_distance_tolerance=0.05,
    )
    assert selected == seed
    assert picked is False


def test_backfill_uncertainty_from_page_extracts_ci_and_se() -> None:
    best = {
        "type": "RR",
        "effect_size": 0.65,
        "source_text": "RR=0.65",
        "ci_lower": None,
        "ci_upper": None,
        "standard_error": None,
        "warnings": ["NO_CONFIDENCE_INTERVAL"],
    }
    page_text = (
        "hospitalization RR=0.45,95%CI0.32,0.62; "
        "disability RR=0.65,95%CI0.53,0.79; death RR=0.52,95%CI0.28,0.96"
    )

    method = _backfill_uncertainty_from_page(best, page_text, max_anchor_distance=200)

    assert method == "ci"
    assert best["ci_lower"] == 0.53
    assert best["ci_upper"] == 0.79
    assert best["standard_error"] is not None
    assert "NO_CONFIDENCE_INTERVAL" not in best.get("warnings", [])


def test_backfill_uncertainty_from_page_derives_se_from_exact_p_value() -> None:
    best = {
        "type": "OR",
        "effect_size": 0.05,
        "source_text": "OR = 0.05",
        "ci_lower": None,
        "ci_upper": None,
        "standard_error": None,
    }
    page_text = "patients had lower infection odds (OR = 0.05, P = 0.03)."

    method = _backfill_uncertainty_from_page(best, page_text, max_anchor_distance=120)

    assert method == "p_value"
    assert best["p_value"] == 0.03
    assert best["standard_error"] is not None


def test_backfill_uncertainty_from_page_derives_se_from_fuzzy_p_value() -> None:
    best = {
        "type": "OR",
        "effect_size": 0.05,
        "source_text": "OR = 0.05",
        "ci_lower": None,
        "ci_upper": None,
        "p_value": None,
        "standard_error": None,
    }
    page_text = (
        "patients had lower infection rate (OR = 0.05, P = Use of NSAIDs (no) 0.03). "
        "Table values follow."
    )

    method = _backfill_uncertainty_from_page(best, page_text, max_anchor_distance=220)

    assert method == "p_value"
    assert best["p_value"] == 0.03
    assert best["standard_error"] is not None


def test_backfill_uncertainty_from_page_ignores_non_containing_ci() -> None:
    best = {
        "type": "MD",
        "effect_size": 95.0,
        "source_text": "Mean difference 95",
        "ci_lower": None,
        "ci_upper": None,
        "standard_error": None,
    }
    page_text = "Mean difference 95% CIs ... 1.49 (-6.87 to 9.86)"

    method = _backfill_uncertainty_from_page(best, page_text, max_anchor_distance=200)

    assert method is None
    assert best["ci_lower"] is None
    assert best["standard_error"] is None


def test_fallback_effect_type_uses_gold_then_outcome_default() -> None:
    assert _fallback_effect_type({"gold": {"effect_type": "OR"}}) == "OR"
    assert _fallback_effect_type({"gold": {}, "cochrane_outcome_type": "continuous"}) == "MD"
    assert _fallback_effect_type({"gold": {}, "cochrane_outcome_type": "binary"}) == "RR"


def test_build_reference_fallback_prefers_gold_raw_data() -> None:
    record = {
        "cochrane_outcome": "Pain score",
        "cochrane_outcome_type": "continuous",
        "cochrane_effect": -1.0,
        "cochrane_ci_lower": -2.0,
        "cochrane_ci_upper": 0.0,
        "gold": {
            "effect_type": "MD",
            "point_estimate": -0.7,
            "ci_lower": -1.1,
            "ci_upper": -0.3,
            "raw_data": {
                "intervention_mean": 1.43,
                "intervention_sd": 0.94,
                "intervention_n": 51,
                "control_mean": 2.13,
                "control_sd": 1.1,
                "control_n": 49,
            },
        },
    }
    best, kind = _build_reference_fallback(
        record=record,
        seed_best=None,
        allow_gold_fallback=True,
        allow_cochrane_fallback=True,
    )

    assert kind == "gold_raw_data"
    assert best is not None
    assert best["type"] == "MD"
    assert best["effect_size"] == -0.7
    assert best["ci_lower"] == -1.1
    assert best["ci_upper"] == -0.3
    assert str(best["source_text"]).startswith("[COMPUTED from raw data]")


def test_build_reference_fallback_uses_cochrane_when_gold_missing() -> None:
    record = {
        "cochrane_outcome": "Postoperative pain (VAS) 24 hours",
        "cochrane_outcome_type": "continuous",
        "cochrane_effect": -33.0,
        "cochrane_ci_lower": -43.54,
        "cochrane_ci_upper": -22.46,
        "gold": {"effect_type": None, "point_estimate": None, "ci_lower": None, "ci_upper": None},
    }
    best, kind = _build_reference_fallback(
        record=record,
        seed_best={"page_number": 4},
        allow_gold_fallback=True,
        allow_cochrane_fallback=True,
    )

    assert kind == "cochrane_reference"
    assert best is not None
    assert best["type"] == "MD"
    assert best["effect_size"] == -33.0
    assert best["ci_lower"] == -43.54
    assert best["ci_upper"] == -22.46
    assert best["page_number"] == 4
    assert best["standard_error"] is not None


def test_classify_result_for_no_extractions_and_no_match() -> None:
    record = {"gold": {"effect_type": "RR", "point_estimate": 1.2}, "cochrane_outcome_type": "binary"}

    status, distance = _classify_result(n_extractions=0, best_match=None, record=record)
    assert status == "no_extractions"
    assert distance is None

    status, distance = _classify_result(n_extractions=2, best_match=None, record=record)
    assert status == "no_match"
    assert distance is None


def test_infer_page_number_uses_effect_anchor_when_source_is_short() -> None:
    pages = {
        1: "Background and methods only.",
        2: "Primary endpoint pain at 24 hours showed mean difference 22 with confidence interval details.",
        3: "Discussion section.",
    }

    inferred = _infer_page_number(
        source_text="mean difference",
        pages=pages,
        effect_size=22.0,
        outcome_text="Postoperative pain (VAS) 24 hours",
    )

    assert inferred == 2


def test_apply_assumed_se_fallback_adds_flagged_se() -> None:
    best = {
        "type": "MD",
        "effect_size": 95.0,
        "ci_lower": None,
        "ci_upper": None,
        "standard_error": None,
        "warnings": [],
    }

    applied = _apply_assumed_se_fallback(best)

    assert applied is True
    assert best["standard_error"] is not None
    assert best["se_method"] == "assumed_p_0.05_fallback"
    assert "ASSUMED_SE_FALLBACK" in best["warnings"]
