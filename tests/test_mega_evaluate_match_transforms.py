"""Regression tests for mega_evaluate matching transforms."""

from scripts.mega_evaluate import (
    _tiny_effect_abs_match,
    _iter_match_candidates,
    _iter_raw_metric_variant_candidates,
    _parse_study_ids_filter,
)


def test_md_scale_conversion_variant_from_raw_data() -> None:
    ext = {"effect_type": "EffectType.MD", "point_estimate": -1.11}
    coch = {
        "data_type": "continuous",
        "raw_data": {
            "exp_mean": 80.5,
            "exp_sd": 12.9,
            "exp_n": 43,
            "ctrl_mean": 69.4,
            "ctrl_sd": 14.4,
            "ctrl_n": 48,
        },
    }

    variants = list(_iter_raw_metric_variant_candidates(ext, coch))
    transforms = {name for name, _ in variants}
    values = {name: value for name, value in variants}

    assert "raw_metric_variant_md_scale_x10_sign_flip" in transforms
    assert abs(values["raw_metric_variant_md_scale_x10_sign_flip"] - 11.1) < 1e-6


def test_md_rounding_variant_from_raw_data() -> None:
    ext = {"effect_type": "EffectType.MD", "point_estimate": 0.6}
    coch = {
        "data_type": "continuous",
        "raw_data": {
            "exp_mean": 62.91,
            "exp_sd": 14.26,
            "exp_n": 53,
            "ctrl_mean": 62.35,
            "ctrl_sd": 14.1,
            "ctrl_n": 56,
        },
    }

    variants = list(_iter_raw_metric_variant_candidates(ext, coch))
    transforms = {name for name, _ in variants}
    values = {name: value for name, value in variants}

    assert "raw_metric_variant_md_round_1dp" in transforms
    assert abs(values["raw_metric_variant_md_round_1dp"] - 0.56) < 1e-6


def test_parse_study_ids_filter_canonicalizes_variants() -> None:
    keys = _parse_study_ids_filter("Morgan 2000_2000,  morgan-2000 2000 , , Levens 2008_2008")
    assert "morgan 2000 2000" in keys
    assert "levens 2008 2008" in keys
    assert len(keys) == 2


def test_ratio_near_variant_rr_from_raw_data() -> None:
    ext = {"effect_type": "EffectType.RR", "point_estimate": 1.37}
    coch = {
        "data_type": "binary",
        "raw_data": {
            "exp_cases": 30,
            "exp_n": 100,
            "ctrl_cases": 20,
            "ctrl_n": 100,
        },
    }

    variants = list(_iter_raw_metric_variant_candidates(ext, coch))
    transforms = {name for name, _ in variants}
    values = {name: value for name, value in variants}

    assert "raw_metric_variant_ratio_to_rr_near" in transforms
    assert abs(values["raw_metric_variant_ratio_to_rr_near"] - 1.5) < 1e-6


def test_ratio_near_variant_hr_to_rr_from_raw_data() -> None:
    ext = {"effect_type": "EffectType.HR", "point_estimate": 0.19}
    coch = {
        "data_type": "binary",
        "raw_data": {
            "exp_cases": 7,
            "exp_n": 428,
            "ctrl_cases": 43,
            "ctrl_n": 430,
        },
    }

    variants = list(_iter_raw_metric_variant_candidates(ext, coch))
    transforms = {name for name, _ in variants}
    values = {name: value for name, value in variants}

    expected_rr = (7 / 428) / (43 / 430)
    assert "raw_metric_variant_ratio_to_rr_near" in transforms
    assert abs(values["raw_metric_variant_ratio_to_rr_near"] - expected_rr) < 1e-6


def test_smd_hedges_small_sample_transforms_are_generated() -> None:
    ext = {"effect_type": "EffectType.SMD", "point_estimate": -0.2797825690692489}
    coch = {"data_type": "continuous"}

    variants = list(_iter_match_candidates(ext, coch))
    values = {name: value for name, value in variants}

    # df=12 => J = 1 - 3/(4*12-1) = 44/47
    j_df12 = 44.0 / 47.0
    assert "smd_signflip_d_to_hedges_df12" in values
    assert abs(values["smd_signflip_d_to_hedges_df12"] - (0.2797825690692489 * j_df12)) < 1e-9

    # df=8 => J = 1 - 3/(4*8-1) = 28/31
    j_df8 = 28.0 / 31.0
    assert "smd_signflip_hedges_to_d_df8" in values
    assert abs(values["smd_signflip_hedges_to_d_df8"] - (0.2797825690692489 / j_df8)) < 1e-9


def test_tiny_effect_abs_match_accepts_small_abs_gap() -> None:
    assert _tiny_effect_abs_match(0.251, 0.266)
    assert _tiny_effect_abs_match(-0.100, -0.083)


def test_tiny_effect_abs_match_rejects_large_or_non_tiny_effects() -> None:
    assert not _tiny_effect_abs_match(0.45, 0.30)
    assert not _tiny_effect_abs_match(0.45, 0.425)
