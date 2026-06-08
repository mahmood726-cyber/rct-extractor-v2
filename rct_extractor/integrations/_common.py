"""Shared statistics helpers for converting extractor output to pooling inputs.

These turn an extracted effect (or a raw 2x2 table) into a point estimate and
standard error on the correct *analysis scale* -- log scale for ratio measures,
natural scale for differences. Both the allmeta (ma-studies-v1) and Beast
adapters use these so the two stay consistent.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

# Two-sided 95% normal quantile (matches allmeta's shared/ma-studies-v1.js).
Z975 = 1.959963984540054

RATIO_TYPES = {"OR", "RR", "HR", "IRR", "GMR", "RRR"}
DIFF_TYPES = {"MD", "SMD", "ARD", "RD", "WMD"}


def effect_to_est_se(effect: Dict) -> Optional[Tuple[float, float]]:
    """Convert an extractor effect dict to ``(est, se)`` on the analysis scale.

    Ratio measures (OR/RR/HR/...) return ``(log(point), se_of_log)``; difference
    measures return ``(point, se)``. Returns ``None`` if the effect lacks a
    usable point estimate + CI, or the values are out of range.
    """
    eff = effect.get("effect_size")
    lo = effect.get("ci_lower")
    hi = effect.get("ci_upper")
    if eff is None or lo is None or hi is None:
        return None
    etype = str(effect.get("type", "")).upper()
    try:
        if etype in RATIO_TYPES:
            if eff <= 0 or lo <= 0 or hi <= 0:
                return None
            est = math.log(float(eff))
            se = (math.log(float(hi)) - math.log(float(lo))) / (2 * Z975)
        else:
            est = float(eff)
            se = (float(hi) - float(lo)) / (2 * Z975)
    except (ValueError, ZeroDivisionError):
        return None
    if not (math.isfinite(est) and math.isfinite(se) and se > 0):
        return None
    return est, se


def twobytwo_to_est_se(table: Dict, measure: str = "OR") -> Optional[Tuple[float, float]]:
    """Convert a poolable 2x2 table (from extract_arm_level) to ``(log-est, se)``.

    A 0.5 continuity correction is applied *only* when at least one cell is zero
    (an unconditional correction biases the OR toward 1). Supports ``OR`` and
    ``RR`` (both on the log scale).
    """
    try:
        a = float(table["arm1"]["events"])
        n1 = float(table["arm1"]["total"])
        c = float(table["arm2"]["events"])
        n2 = float(table["arm2"]["total"])
    except (KeyError, TypeError, ValueError):
        return None
    b = n1 - a
    d = n2 - c
    if min(a, b, c, d) < 0 or n1 <= 0 or n2 <= 0:
        return None
    if 0 in (a, b, c, d):  # conditional 0.5 correction
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    m = measure.upper()
    try:
        if m == "RR":
            r1 = a / (a + b)
            r2 = c / (c + d)
            if r1 <= 0 or r2 <= 0:
                return None
            est = math.log(r1 / r2)
            se = math.sqrt(1 / a - 1 / (a + b) + 1 / c - 1 / (c + d))
        else:  # OR (default)
            est = math.log((a * d) / (b * c))
            se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    except (ValueError, ZeroDivisionError):
        return None
    if not (math.isfinite(est) and math.isfinite(se) and se > 0):
        return None
    return est, se


def pick_effect(effects, endpoint: Optional[str] = None, measure: Optional[str] = None):
    """Pick the most relevant effect with a usable CI from a list.

    Preference order: matches both endpoint and measure -> matches measure ->
    matches endpoint -> first effect with a CI.
    """
    usable = [e for e in effects if e.get("ci_lower") is not None and e.get("ci_upper") is not None]
    if not usable:
        return None
    m = measure.upper() if measure else None

    def _m(e):
        return m is None or str(e.get("type", "")).upper() == m

    def _e(e):
        return endpoint is None or e.get("endpoint") == endpoint

    for pred in (lambda e: _m(e) and _e(e), _m, _e, lambda e: True):
        for e in usable:
            if pred(e):
                return e
    return usable[0]
