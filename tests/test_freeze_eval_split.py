from scripts.freeze_eval_split import _has_reference_effect


def test_has_reference_effect_accepts_cochrane_effect() -> None:
    assert _has_reference_effect({"cochrane_effect": 1.23, "gold": {}}) is True


def test_has_reference_effect_accepts_gold_point_without_cochrane() -> None:
    assert _has_reference_effect({"cochrane_effect": None, "gold": {"point_estimate": 0.91}}) is True


def test_has_reference_effect_rejects_when_both_missing() -> None:
    assert _has_reference_effect({"cochrane_effect": None, "gold": {"point_estimate": None}}) is False
