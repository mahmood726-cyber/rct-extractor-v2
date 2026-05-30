"""
Internal-consistency checks for extracted effect estimates.

An extracted (point estimate, confidence interval, p-value) triple is
over-determined: the three pieces must agree. A misread digit or a swapped CI
bound breaks that agreement, so consistency checking catches extraction errors
the regex layer cannot. Grounded in published methodology:

- Altman & Bland (BMJ 2011; 343:d2090) -- convert CI <-> p via the standard
  error; for ratios this is done on the LOG scale, then exponentiated.
    SE = (ln(upper) - ln(lower)) / (2 * 1.96)        # ratio, 95% CI
    z  = ln(PE) / SE                                  # test vs null=1
    P  = exp(-0.717*z - 0.416*z^2)                    # two-sided (Altman-Bland)
    inverse cross-check: z = -0.862 + sqrt(0.743 - 2.404*ln P)
- statcheck (Nuijten et al., 2016; Res Synth Methods 2020) -- recompute and flag
  "gross inconsistency" when the recomputed value flips the significance verdict.
- Geometric/arithmetic midpoint -- a ratio's point estimate is the geometric
  mean of its CI bounds (sqrt(lo*hi)); a difference's is the arithmetic mean
  ((lo+hi)/2). A large deviation indicates a misread digit.

This module is additive: it scores/flags/repairs but never mutates the core.
"""
import math
from typing import Dict, Optional

Z95 = 1.959964  # two-sided 95% normal quantile

RATIO_TYPES = {"HR", "OR", "RR", "IRR", "GMR", "RRR"}
DIFF_TYPES = {"MD", "SMD", "ARD", "RD", "WMD"}
PCT_TYPES = {"EFFICACY_PCT"}            # percentage scale, null = 0, linear CI

_EPS = 1e-9


def two_sided_p_from_z(z: float) -> float:
    """Altman-Bland two-sided P from a z-statistic."""
    z = abs(z)
    return math.exp(-0.717 * z - 0.416 * z * z)


def z_from_p(p: float) -> Optional[float]:
    """Altman-Bland inverse: z from a two-sided P (cross-check)."""
    if p is None or p <= 0 or p >= 1:
        return None
    inner = 0.743 - 2.404 * math.log(p)
    if inner < 0:
        return None
    return -0.862 + math.sqrt(inner)


def check_consistency(effect: Dict, mid_tol: float = 0.22,
                      gross_mid_tol: float = 0.6) -> Dict:
    """Score an extracted effect dict for internal consistency.

    Args:
        effect: {type, effect_size, ci_lower, ci_upper, p_value?}
        mid_tol: deviation of the point from the CI centre (|ln(PE)-log-midpoint|
                 for ratios; relative for differences) above which we flag a
                 soft 'point_off_ci_centre' (surfaced for review). Set above the
                 noise from rounded published CIs.
        gross_mid_tol: deviation above which the mismatch almost certainly means
                 a misread digit (e.g. CI upper '0.85' read as '85.0') ->
                 'point_grossly_off_centre'.

    Returns a dict with: checkable, consistent, score in [0,1], flags[],
    derived_p, ci_excludes_null, and an optional repaired CI.
    """
    etype = str(effect.get("type", "")).upper()
    pe = effect.get("effect_size")
    lo = effect.get("ci_lower")
    hi = effect.get("ci_upper")
    p = effect.get("p_value")

    res = {"checkable": False, "consistent": True, "score": 1.0,
           "flags": [], "derived_p": None, "ci_excludes_null": None,
           "repair": None}

    if pe is None or lo is None or hi is None:
        return res
    res["checkable"] = True

    # Repair 1: CI bounds reported in reverse order.
    if lo > hi:
        lo, hi = hi, lo
        res["repair"] = "swapped_ci_bounds"

    flags = []
    is_ratio = etype in RATIO_TYPES
    is_pct = etype in PCT_TYPES
    null = 1.0 if is_ratio else 0.0

    # Containment: point must lie within its CI.
    if not (lo - _EPS <= pe <= hi + _EPS):
        flags.append("point_outside_ci")

    z = None
    mid_err = None
    if is_ratio:
        if lo <= 0 or hi <= 0 or pe <= 0:
            flags.append("nonpositive_ratio")
        else:
            log_mid = (math.log(lo) + math.log(hi)) / 2.0
            mid_err = abs(math.log(pe) - log_mid)        # log scale
            se = (math.log(hi) - math.log(lo)) / (2.0 * Z95)
            if se > 0:
                z = math.log(pe) / se
    else:
        # difference / percentage: linear scale
        mid = (lo + hi) / 2.0
        denom = abs(mid) if abs(mid) > _EPS else 1.0
        mid_err = abs(pe - mid) / denom
        se = (hi - lo) / (2.0 * Z95)
        if se > 0:
            z = (pe - null) / se

    if mid_err is not None:
        if mid_err > gross_mid_tol:
            flags.append("point_grossly_off_centre")   # almost certainly a misread digit
        elif mid_err > mid_tol:
            flags.append("point_off_ci_centre")

    ci_excludes_null = (null < lo - _EPS) or (null > hi + _EPS)
    res["ci_excludes_null"] = ci_excludes_null

    derived_p = two_sided_p_from_z(z) if z is not None else None
    res["derived_p"] = derived_p

    # statcheck-style significance agreement with a reported p-value. We check
    # only the significance VERDICT (does the CI exclude the null vs is p<0.05),
    # not p magnitude -- abstracts report p as ceilings ("p<0.001"), so exact
    # magnitudes are unreliable and would false-flag good extractions.
    if p is not None and derived_p is not None:
        if (p < 0.05) != ci_excludes_null:
            flags.append("gross_sig_inconsistency")

    # Score: hard flags zero it out; soft flags reduce it. A gross midpoint
    # mismatch (misread digit) is near-hard but not auto-dropped, since a few
    # genuine wide/boundary CIs can trip it -- surfaced for review instead.
    hard = {"point_outside_ci", "nonpositive_ratio", "gross_sig_inconsistency"}
    penalty = {"point_grossly_off_centre": 0.7, "point_off_ci_centre": 0.4}
    score = 1.0
    if any(f in hard for f in flags):
        score = 0.0
    else:
        score -= sum(penalty.get(f, 0.0) for f in flags)
    score = max(0.0, score)

    res["flags"] = flags
    res["score"] = round(score, 3)
    res["consistent"] = (score >= 0.6)
    return res


def annotate(effects, drop_hard: bool = False, mid_tol: float = 0.12):
    """Attach a 'consistency' dict to each effect; optionally drop hard failures.

    Hard failures = point outside its CI, non-positive ratio bounds, or a
    significance flip vs a reported p. These are almost always extraction
    errors. Soft flags (point not at CI centre, p magnitude off) are kept but
    marked needs_review.
    """
    out = []
    for e in effects:
        c = check_consistency(e, mid_tol=mid_tol)
        e = dict(e)
        # Apply the safe repair (reversed CI bounds) to the emitted values.
        if c.get("repair") == "swapped_ci_bounds":
            e["ci_lower"], e["ci_upper"] = e["ci_upper"], e["ci_lower"]
        e["consistency"] = c
        # Surface ANY internal-consistency flag for human review; only hard
        # failures (score 0) are dropped.
        e["needs_review"] = bool(c["checkable"] and c["flags"])
        if drop_hard and c["checkable"] and c["score"] == 0.0:
            continue
        out.append(e)
    return out
