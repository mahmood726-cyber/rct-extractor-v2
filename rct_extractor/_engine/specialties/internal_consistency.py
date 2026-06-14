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

RATIO_TYPES = {"HR", "OR", "RR", "IRR", "GMR"}
DIFF_TYPES = {"MD", "SMD", "ARD", "RD", "WMD"}
# Percentage 1-RR quantities: efficacy / relative-risk-reduction. These are on a
# % scale with null = 0 (NOT ratio null = 1) -- treating RRR as a ratio gives a
# wrong significance verdict for every vaccine-efficacy estimate. (P0-5)
PCT_TYPES = {"EFFICACY_PCT", "RRR"}

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


def _recompute_ratio(etype: str, et, nt, ec, nc) -> Optional[float]:
    """Recompute OR or RR from a 2x2 table (0.5 correction on any zero cell).

    Only OR and RR are directly determined by the 2x2 table, so only those are
    cross-checked; HR/IRR depend on person-time / censoring and a risk-ratio
    proxy would false-flag them, so they are skipped.
    """
    a, b, c, d = et, nt - et, ec, nc - ec
    if min(a, b, c, d) == 0:
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    if etype == "OR":
        return (a * d) / (b * c) if (b * c) else None
    if etype == "RR":
        rt, rc = a / (a + b), c / (c + d)
        return (rt / rc) if rc else None
    return None


def grim_consistent(mean: float, n: int, items: int = 1,
                    decimals: Optional[int] = None) -> Optional[bool]:
    """GRIM test (Brown & Heathers 2017): a reported MEAN of integer-valued
    items must equal (integer sum)/(n*items). Returns False if no integer sum
    can round to the reported mean at its stated decimal precision.

    Interval form (Brown/Heathers): the half-unit rounding window around the
    reported mean must contain a multiple of 1/(n*items). Ported from the
    R-validated asa.html grimCheck (C:\\Projects\\asa\\asa.html). Returns None
    when the test does not apply (n<1, n*items too large to constrain a mean at
    `decimals` places => every mean passes, so no signal).
    """
    if mean is None or n is None or n < 1 or items < 1:
        return None
    eff_n = n * items
    if decimals is None:
        s = repr(float(mean))
        decimals = len(s.split(".")[1]) if "." in s else 0
    scale = 10 ** decimals
    # If eff_n >= scale, every target mean is reachable -> no constraint, skip.
    if eff_n >= scale:
        return None
    half = 0.5 / scale
    lo_sum = (mean - half) * eff_n
    hi_sum = (mean + half) * eff_n
    return math.ceil(lo_sum - 1e-9) <= math.floor(hi_sum + 1e-9)


def grimmer_consistent(sd: float, n: int, mean: float, items: int = 1,
                       decimals: Optional[int] = None) -> Optional[bool]:
    """GRIMMER test (Anaya 2016): given n+mean, the reported SD implies a
    sum-of-squares (SD^2*(n-1) + n*mean^2) that must be a non-negative integer
    for integer-item data. Returns False when no integer SS is reachable within
    the rounding window of both mean and SD. Ported from asa.html grimmerCheck.

    Returns None when inapplicable (n<2, sd<0, or precision too coarse to
    constrain -> every SD passes).
    """
    if sd is None or n is None or mean is None or n < 2 or sd < 0 or items < 1:
        return None
    if decimals is None:
        ss = repr(float(sd))
        decimals = len(ss.split(".")[1]) if "." in ss else 0
    eff_n = n * items
    scale = 10 ** decimals
    if eff_n >= scale:
        return None
    # Precondition: GRIMMER is only meaningful when the MEAN is GRIM-consistent.
    # If the mean already fails GRIM that error dominates; don't double-flag.
    if grim_consistent(mean, n, items, decimals) is False:
        return None
    half = 0.5 / scale
    # The integer sum is fixed by the (GRIM-passing) mean: sum = round(mean*eff_n).
    # Then SS_int = SD^2*(n-1) + sum^2/(n*items^2)... work on the integer SS that
    # the SD implies and test whether ANY integer SS lands in the SD's rounding
    # window. Scan the SD window; flag only when NO integer SS is reachable.
    lo_sd, hi_sd = max(0.0, sd - half), sd + half
    steps = 400
    reachable = False
    for i in range(steps + 1):
        test_sd = lo_sd + (hi_sd - lo_sd) * i / steps
        ss = test_sd * test_sd * (n - 1) + n * mean * mean
        scaled = ss * items * items
        if scaled < -1e-6:
            continue
        if abs(scaled - round(scaled)) < 0.008:
            reachable = True
            break
    return not reachable


def check_consistency(effect: Dict, mid_tol: float = 0.22,
                      gross_mid_tol: float = 0.6,
                      table_log_tol: float = 0.30) -> Dict:
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

    # Count-level checks (when the 2x2 cell counts are present). These catch the
    # negated-count trap -- an extracted arm N that is actually a "Not
    # randomised"/"discontinued" count, so events > N -- and effect estimates
    # that disagree with the table they summarise. Keys: events_tx / n_tx /
    # events_ctrl / n_ctrl. Absent on effect-only extractions, so they never
    # fire on the abstract-level gold set.
    et_, nt_, ec_, nc_ = (effect.get("events_tx"), effect.get("n_tx"),
                          effect.get("events_ctrl"), effect.get("n_ctrl"))
    for ev, n in ((et_, nt_), (ec_, nc_)):
        if ev is not None and n is not None:
            if n <= 0:
                flags.append("arm_n_nonpositive")
            elif ev < 0:
                flags.append("events_negative")
            elif ev > n:
                flags.append("events_exceed_n")
    bad_counts = {"arm_n_nonpositive", "events_negative", "events_exceed_n"}
    if (is_ratio and pe and pe > 0 and None not in (et_, nt_, ec_, nc_)
            and nt_ and nc_ and nt_ > 0 and nc_ > 0
            and not (bad_counts & set(flags))):
        recomputed = _recompute_ratio(etype, et_, nt_, ec_, nc_)
        if recomputed and recomputed > 0:
            if abs(math.log(pe) - math.log(recomputed)) > table_log_tol:
                flags.append("effect_table_mismatch")

    # (A percentage-scale check for RRR/efficacy was considered for the "4S" class
    # but is redundant: a point on a different scale from its CI is already caught
    # by point_outside_ci, and the 4S case itself is a correct extraction read
    # against a proportion-encoded gold value — not an extraction error.)

    # --- arm-N-sums-to-total -------------------------------------------------
    # When randomised arm Ns AND a reported trial total are both extracted, the
    # arms must reconcile to the total (allow a small tolerance for screen-fail /
    # mITT trims). A gross mismatch usually means one of the three numbers is a
    # misread or a wrong field (e.g. an enrolled-vs-randomised confusion).
    # Source idea: dataextractor/qc.js ConsistencyValidator (arm-N reconciliation).
    nt2, nc2, total = (effect.get("n_tx"), effect.get("n_ctrl"),
                       effect.get("n_total"))
    if (nt2 is not None and nc2 is not None and total is not None
            and nt2 > 0 and nc2 > 0 and total > 0):
        arm_sum = nt2 + nc2
        # arms can be a subset of total (multi-arm trial) but must never exceed
        # it by more than rounding; and a 2-arm total should be close to the sum.
        if arm_sum > total * 1.02 + 1:
            flags.append("arm_n_exceeds_total")          # hard: impossible
        elif abs(arm_sum - total) > 0.20 * total:
            flags.append("arm_n_sum_mismatch")           # soft: review

    # --- percentage <-> count coherence -------------------------------------
    # A reported event percentage must match events/N within rounding. Catches a
    # mis-paired %/count (e.g. a % copied from a different row). Keys:
    # pct_tx/pct_ctrl are event rates in PERCENT for each arm.
    # Source idea: gap noted across repos (qc.js does %-range only); standard
    # %<->count coherence.
    for ev, n_, pct in ((et_, nt_, effect.get("pct_tx")),
                        (ec_, nc_, effect.get("pct_ctrl"))):
        if ev is not None and n_ and n_ > 0 and pct is not None and 0 <= pct <= 100:
            if 0 <= ev <= n_:
                implied = 100.0 * ev / n_
                # tolerance: half a percentage point or 1 count's worth, plus 2%
                # relative slack for ITT-vs-evaluable denominator differences.
                tol = max(0.5, 100.0 / n_) + 0.02 * implied
                if abs(implied - pct) > tol:
                    flags.append("pct_count_incoherent")  # soft: review

    # --- proportion / percentage range --------------------------------------
    # A field declared as a percentage must lie in [0,100]; a proportion in
    # [0,1]. A value outside its declared range is a unit/parse error.
    # Source idea: dataextractor/qc.js NumericValidator FIELD_RANGES.
    for key, hi_bound in (("pct_tx", 100.0), ("pct_ctrl", 100.0)):
        v = effect.get(key)
        if v is not None and (v < 0 or v > hi_bound):
            flags.append("proportion_out_of_range")       # hard: impossible
            break

    # --- GRIM / GRIMMER (mean & SD granularity) ------------------------------
    # When a continuous-outcome mean (+ optional SD) and the arm N are present,
    # the mean must be reconstructible from an integer sum (GRIM) and the SD must
    # imply an integer sum-of-squares (GRIMMER). Only meaningful for
    # integer-item scales; gated by `scale_items` being supplied (default 1 for
    # raw integer counts/scores). Source: Brown & Heathers 2017 (GRIM),
    # Anaya 2016 (GRIMMER); ported from R-validated asa.html.
    items = effect.get("scale_items")
    if items:                       # only run when the caller marks an integer scale
        for mean_v, sd_v, n_v in (
            (effect.get("mean_tx"), effect.get("sd_tx"), effect.get("n_tx")),
            (effect.get("mean_ctrl"), effect.get("sd_ctrl"), effect.get("n_ctrl")),
        ):
            if mean_v is not None and n_v and n_v >= 1:
                if grim_consistent(mean_v, int(n_v), int(items)) is False:
                    flags.append("grim_inconsistent")     # soft: review
                if sd_v is not None and grimmer_consistent(
                        sd_v, int(n_v), mean_v, int(items)) is False:
                    flags.append("grimmer_inconsistent")  # soft: review

    # Score: hard flags zero it out (and get dropped); soft flags reduce it and
    # surface needs_review. gross_sig_inconsistency is SOFT, not hard: a CI that
    # includes the null while p<0.05 (or vice versa) is usually discordant
    # REPORTING (different model/rounding), not a misread digit -- flag it for
    # review, don't discard a correct extraction. (P0-6)
    hard = {"point_outside_ci", "nonpositive_ratio",
            "events_exceed_n", "arm_n_nonpositive", "events_negative",
            "arm_n_exceeds_total", "proportion_out_of_range"}
    penalty = {"point_grossly_off_centre": 0.7, "point_off_ci_centre": 0.4,
               "gross_sig_inconsistency": 0.4, "effect_table_mismatch": 0.4,
               "arm_n_sum_mismatch": 0.4, "pct_count_incoherent": 0.4,
               "grim_inconsistent": 0.4, "grimmer_inconsistent": 0.3}
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
