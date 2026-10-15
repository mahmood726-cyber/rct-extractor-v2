"""Regression guards for estimand and outcome integrity in the Meta-Starter-Kit bridge."""

import pytest

from rct_extractor._engine.bridges import meta_starter_kit as bridge


def _stub_extractors(monkeypatch, effects=(), table_endpoint="MORTALITY"):
    from rct_extractor._engine.specialties import registry

    monkeypatch.setattr(registry, "detect_specialty", lambda _: ("diabetes", None, 0.99))
    table = {
        "endpoint": table_endpoint,
        "arm1": {"events": 12, "total": 100},
        "arm2": {"events": 18, "total": 100},
    }
    monkeypatch.setattr(
        bridge, "_arm_extractor_for",
        lambda _: lambda text: {"poolable_2x2": [table]},
    )
    monkeypatch.setattr(bridge, "_effects_for", lambda spec, extractor, text: list(effects))


def _records():
    return [{"name": "Trial A", "text": "trial one"},
            {"name": "Trial B", "text": "trial two"}]


def test_hr_must_not_be_computed_from_event_counts():
    with pytest.raises(ValueError, match="HR cannot be derived from 2x2"):
        bridge.make_config(
            "Time to event", "HR",
            [bridge.binary_trial("A", 12, 100, 18, 100),
             bridge.binary_trial("B", 10, 90, 15, 90)],
        )


def test_hr_uses_reported_time_to_event_effect_even_when_counts_exist(monkeypatch):
    _stub_extractors(
        monkeypatch,
        effects=[{"type": "HR", "effect_size": 0.73, "ci_lower": 0.60,
                  "ci_upper": 0.89, "endpoint": "MORTALITY"}],
    )
    cfg = bridge.build_config_from_records(
        _records(), object(), title="Survival", effect_measure="HR", endpoint="MORTALITY"
    )
    assert len(cfg["trials"]) == 2
    assert all(t["effect"] == 0.73 and "tE" not in t for t in cfg["trials"])


def test_requested_endpoint_does_not_fall_back_to_unrelated_binary_endpoint(monkeypatch):
    _stub_extractors(
        monkeypatch,
        effects=[{"type": "RR", "effect_size": 0.66, "ci_lower": 0.50,
                  "ci_upper": 0.90, "endpoint": "STROKE"}],
    )
    cfg = bridge.build_config_from_records(
        _records(), object(), title="Stroke", effect_measure="RR", endpoint="STROKE"
    )
    assert all(t["effect"] == 0.66 and "tE" not in t for t in cfg["trials"])


def test_absent_requested_outcome_refuses_instead_of_pooling_mortality(monkeypatch):
    _stub_extractors(monkeypatch)
    with pytest.raises(ValueError, match="need >=2 valid trials"):
        bridge.build_config_from_records(
            _records(), object(), title="Stroke", effect_measure="RR", endpoint="STROKE"
        )


def test_endpoint_comparison_is_case_and_whitespace_insensitive(monkeypatch):
    _stub_extractors(monkeypatch, table_endpoint="  mOrTaLiTy ")
    cfg = bridge.build_config_from_records(
        _records(), object(), title="Mortality", effect_measure="RR", endpoint="mortality"
    )
    assert all(t["tE"] == 12 and "effect" not in t for t in cfg["trials"])


@pytest.mark.parametrize("counts", [
    (11, 10, 2, 10),  # more events than participants
    (1, 0, 2, 10),    # zero denominator
    (1.9, 10, 2, 10), # do not truncate fractional people
    (float("nan"), 10, 2, 10),
    (True, 10, 2, 10),
])
def test_binary_trial_rejects_impossible_counts(counts):
    with pytest.raises(ValueError, match="2x2|finite"):
        bridge.binary_trial("corrupt", *counts)


def test_make_config_validates_direct_2x2_rows_too():
    malformed = {"name": "bad", "tE": 12, "tN": 10, "cE": 1, "cN": 10}
    with pytest.raises(ValueError, match="impossible 2x2"):
        bridge.make_config(
            "Risk", "RR", [malformed, bridge.binary_trial("valid", 1, 10, 2, 10)]
        )


@pytest.mark.parametrize("effect,low,high", [
    (float("nan"), 0.5, 1.0),
    (0.8, 0.9, 1.1),
    (0.8, -0.1, 0.9),
])
def test_make_config_rejects_nonpoolable_effect_and_ci(effect, low, high):
    with pytest.raises(ValueError, match="finite|inside ordered|positive"):
        bridge.make_config(
            "Risk", "RR",
            [{"name": "bad", "effect": effect, "ci_low": low, "ci_high": high},
             bridge.effect_trial("valid", 0.75, 0.60, 0.90)],
        )


def test_mixed_hr_row_drops_incompatible_counts_not_reported_hr():
    mixed = {"name": "A", "tE": 10, "tN": 100, "cE": 12, "cN": 100,
             "effect": 0.75, "ci_low": 0.60, "ci_high": 0.90}
    cfg = bridge.make_config(
        "Survival", "HR", [mixed, bridge.effect_trial("B", 0.8, 0.7, 0.95)]
    )
    assert cfg["trials"][0]["effect"] == 0.75
    assert "tE" not in cfg["trials"][0]
