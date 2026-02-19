from scripts.build_ma_records_from_results import _iter_ma_candidates


def test_iter_ma_candidates_skips_missing_page_or_source() -> None:
    gold = [{"study_id": "S1", "cochrane_outcome": "Outcome 1", "gold": {"is_primary": True}}]
    results = [
        {
            "study_id": "S1",
            "best_match": {
                "type": "RR",
                "effect_size": 1.2,
                "ci_lower": 1.0,
                "ci_upper": 1.4,
                "standard_error": 0.1,
                "source_text": "",
                "page_number": 1,
            },
        }
    ]
    rows = list(_iter_ma_candidates(gold, results))
    assert rows == []


def test_iter_ma_candidates_emits_contract_ready_payload() -> None:
    gold = [
        {
            "study_id": "S2",
            "cochrane_outcome": "Outcome 2",
            "gold": {"is_primary": True, "outcome_name": "Primary Outcome"},
        }
    ]
    results = [
        {
            "study_id": "S2",
            "best_match": {
                "type": "RR",
                "effect_size": 1.2,
                "ci_lower": 1.0,
                "ci_upper": 1.4,
                "standard_error": 0.1,
                "p_value": 0.02,
                "source_text": "RR 1.2 (95% CI 1.0 to 1.4)",
                "page_number": 3,
                "char_start": 10,
                "char_end": 40,
            },
        }
    ]

    rows = list(_iter_ma_candidates(gold, results))
    assert len(rows) == 1
    row = rows[0]
    assert row["study_id"] == "S2"
    assert row["outcome_name"] == "Primary Outcome"
    assert row["effect_type"] == "RR"
    assert row["provenance"]["page_number"] == 3
