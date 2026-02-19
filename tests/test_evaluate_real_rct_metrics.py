from scripts.evaluate_real_rct_metrics import compute_metrics


def test_match_scoring_uses_gold_point_not_status_label() -> None:
    gold_records = [
        {
            "study_id": "S1",
            "cochrane_outcome_type": "binary",
            "cochrane_effect": 0.9466,
            "gold": {"effect_type": "RR", "point_estimate": 1.21, "ci_lower": 1.01, "ci_upper": 1.46},
        }
    ]
    result_records = [
        {
            "study_id": "S1",
            "status": "distant_match",
            "best_match": {
                "type": "RR",
                "effect_size": 1.21,
                "ci_lower": 1.01,
                "ci_upper": 1.46,
                "standard_error": 0.09,
                "source_text": "risk ratio: 1.21; 95% CI: 1.01, 1.46",
                "page_number": 1,
            },
        }
    ]

    metrics = compute_metrics(gold_records, result_records, selected_ids=None)

    assert metrics["rates"]["extraction_coverage"] == 1.0
    assert metrics["rates"]["strict_match_rate"] == 1.0
    assert metrics["rates"]["lenient_match_rate"] == 1.0


def test_match_scoring_falls_back_to_cochrane_when_gold_point_missing() -> None:
    gold_records = [
        {
            "study_id": "S2",
            "cochrane_outcome_type": "binary",
            "cochrane_effect": 2.0,
            "gold": {"effect_type": None, "point_estimate": None},
        }
    ]
    result_records = [
        {
            "study_id": "S2",
            "status": "no_match",
            "best_match": {
                "type": "RR",
                "effect_size": 1.92,
                "ci_lower": 1.2,
                "ci_upper": 3.0,
                "standard_error": 0.2,
                "source_text": "RR 1.92 (95% CI 1.2 to 3.0)",
                "page_number": 2,
            },
        }
    ]

    metrics = compute_metrics(gold_records, result_records, selected_ids=None)

    assert metrics["rates"]["strict_match_rate"] == 1.0
    assert metrics["rates"]["lenient_match_rate"] == 1.0


def test_coverage_uses_effect_presence_not_status() -> None:
    gold_records = [
        {
            "study_id": "S3",
            "cochrane_outcome_type": "continuous",
            "cochrane_effect": -1.0,
            "gold": {"effect_type": "MD", "point_estimate": -1.0},
        }
    ]
    result_records = [
        {
            "study_id": "S3",
            "status": "no_extractions",
            "best_match": {
                "type": "MD",
                "effect_size": -1.0,
                "ci_lower": -2.0,
                "ci_upper": 0.0,
                "standard_error": 0.5,
                "source_text": "mean difference -1.0",
                "page_number": 0,
            },
        }
    ]

    metrics = compute_metrics(gold_records, result_records, selected_ids=None)

    assert metrics["rates"]["extraction_coverage"] == 1.0
