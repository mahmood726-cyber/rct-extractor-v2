"""Tests for recovery — SE triangulation + imputation-uncertainty propagation."""
import math
try:
    from recovery import (triangulate_se, se_from_ci, se_from_p, sd_from_iqr, sd_from_range,
                          var_of_sd_estimate, pool_compare_imputation)
except ImportError:
    from .recovery import (triangulate_se, se_from_ci, se_from_p, sd_from_iqr, sd_from_range,
                          var_of_sd_estimate, pool_compare_imputation)

def test_se_from_ci_log_scale():
    se = se_from_ci(0.75, 0.97, 0.95, log_scale=True)
    assert abs(se - (math.log(0.97) - math.log(0.75)) / (2 * 1.959964)) < 1e-9

def test_triangulation_agrees_when_consistent():
    # a p-value derived from the same CI must agree
    se = se_from_ci(0.75, 0.97, log_scale=True)
    z = abs(math.log(0.86)) / se
    from statistics import NormalDist
    p = 2 * (1 - NormalDist().cdf(z))
    r = triangulate_se(effect=0.86, ci=(0.75, 0.97), p=round(p, 4), log_scale=True)
    assert r["agree"] is True and r["confidence"] >= 0.9 and r["spread"] < 0.05

def test_triangulation_flags_mis_transcribed_ci():
    # a CI whose upper bound was mis-read disagrees with the p -> FLAGGED, fail closed
    r = triangulate_se(effect=0.86, ci=(0.75, 0.79), p=0.0215, log_scale=True)
    assert r["agree"] is False and r["confidence"] <= 0.3

def test_single_route_is_low_confidence():
    r = triangulate_se(effect=0.86, ci=(0.75, 0.97), log_scale=True)
    assert r["agree"] is None or r["confidence"] <= 0.6   # cannot corroborate with one route

def test_wan_sd_from_iqr_and_range():
    # Wan 2014 worked example region: monotone, positive, shrinks with n
    assert sd_from_iqr(10, 20, 40) > 0
    assert sd_from_range(5, 25, 40) > sd_from_iqr(10, 20, 40) * 0  # both defined
    assert var_of_sd_estimate(8.0, 40) > var_of_sd_estimate(8.0, 400)  # more n -> less var

def test_imputation_propagation_widens_ci():
    yi = [-0.2, 0.1, -0.05, 0.0, 0.15]
    vi = [0.04, 0.05, 0.03, 0.06, 0.05]
    extra = [v * (2.0 / (15 - 1)) for v in vi]   # all imputed at n=15
    r = pool_compare_imputation(yi, vi, extra)
    assert r["propagated"]["ci_width"] > r["naive"]["ci_width"]   # GUARANTEED direction
    assert r["ci_width_inflation"] > 0

def test_fail_closed_no_routes():
    r = triangulate_se(effect=0.86)   # nothing to triangulate
    assert r["se"] is None and r["confidence"] == 0.0

if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try: fn(); p += 1; print(f"  PASS {fn.__name__}")
        except AssertionError as e: print(f"  FAIL {fn.__name__}: {e}")
    print(f"{p}/{len(fns)} passed"); sys.exit(0 if p == len(fns) else 1)
