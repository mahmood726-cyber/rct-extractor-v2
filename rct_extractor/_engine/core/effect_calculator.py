"""
Effect Size Calculator — Compute effects from raw study data.

Computes the same effects that Cochrane/RevMan would compute from:
- 2×2 tables (binary outcomes) → OR, RR, RD
- Two-group means/SDs/n (continuous outcomes) → MD, SMD (Hedges' g)

This enables "reverse engineering" Cochrane effects from papers that only
report raw data (counts, means, SDs) without pre-computed effect estimates.

All formulas use standard meta-analysis methods:
- OR: Woolf's method (log-OR with normal approximation)
- RR: Log-RR with normal approximation
- RD: Newcombe's method (normal approximation)
- MD: Direct difference with pooled variance
- SMD: Hedges' g with small-sample correction
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple


# Z-value for 95% CI (default)
Z_95 = 1.959964


@dataclass
class ComputedEffect:
    """Result of an effect size computation."""
    effect_type: str          # OR, RR, RD, MD, SMD
    point_estimate: float
    ci_lower: float
    ci_upper: float
    se: float                 # Standard error (on natural scale for MD/RD, log scale for OR/RR)
    method: str               # e.g., "woolf_log_or", "hedges_g"
    source: str = "computed"  # Always "computed" (not "extracted")
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "effect_type": self.effect_type,
            "point_estimate": round(self.point_estimate, 4),
            "ci_lower": round(self.ci_lower, 4),
            "ci_upper": round(self.ci_upper, 4),
            "se": round(self.se, 4),
            "method": self.method,
            "source": self.source,
            "notes": self.notes,
        }


# ============================================================
# BINARY OUTCOMES — 2×2 table computations
# ============================================================

def _apply_continuity_correction(a: int, b: int, c: int, d: int,
                                  cc: float = 0.5) -> Tuple[float, float, float, float]:
    """Apply continuity correction when any cell is zero."""
    if a == 0 or b == 0 or c == 0 or d == 0:
        return (a + cc, b + cc, c + cc, d + cc)
    return (float(a), float(b), float(c), float(d))


def compute_or(events_t: int, n_t: int, events_c: int, n_c: int,
               conf_level: float = 0.95) -> Optional[ComputedEffect]:
    """
    Compute odds ratio from 2×2 table using Woolf's method.

    2×2 table:
                    Event   No-event
    Treatment:       a        b       (n_t = a + b)
    Control:         c        d       (n_c = c + d)

    OR = (a*d) / (b*c)
    SE(ln OR) = sqrt(1/a + 1/b + 1/c + 1/d)
    95% CI: exp(ln(OR) ± Z * SE)
    """
    a = events_t
    b = n_t - events_t
    c = events_c
    d = n_c - events_c

    if b < 0 or d < 0:
        return None

    # Apply continuity correction if needed
    af, bf, cf, df = _apply_continuity_correction(a, b, c, d)

    if bf * cf == 0:
        return None

    or_val = (af * df) / (bf * cf)
    if or_val <= 0:
        return None

    ln_or = math.log(or_val)
    se_ln_or = math.sqrt(1/af + 1/bf + 1/cf + 1/df)

    z = _z_for_level(conf_level)
    ci_lower = math.exp(ln_or - z * se_ln_or)
    ci_upper = math.exp(ln_or + z * se_ln_or)

    notes = None
    if a == 0 or b == 0 or c == 0 or d == 0:
        notes = "continuity correction applied (0.5 added to all cells)"

    return ComputedEffect(
        effect_type="OR",
        point_estimate=or_val,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        se=se_ln_or,
        method="woolf_log_or",
        notes=notes,
    )


def compute_rr(events_t: int, n_t: int, events_c: int, n_c: int,
               conf_level: float = 0.95) -> Optional[ComputedEffect]:
    """
    Compute risk ratio from 2×2 table.

    RR = (a/n_t) / (c/n_c)
    SE(ln RR) = sqrt(1/a - 1/n_t + 1/c - 1/n_c)
    95% CI: exp(ln(RR) ± Z * SE)
    """
    a = events_t
    c = events_c

    if n_t <= 0 or n_c <= 0:
        return None

    # Need non-zero events for log-RR
    af, cf = float(a), float(c)
    notes = None
    if a == 0 or c == 0:
        af = a + 0.5
        cf = c + 0.5
        n_t_f = n_t + 1.0
        n_c_f = n_c + 1.0
        notes = "continuity correction applied"
    else:
        n_t_f = float(n_t)
        n_c_f = float(n_c)

    p_t = af / n_t_f
    p_c = cf / n_c_f

    if p_c == 0:
        return None

    rr = p_t / p_c
    if rr <= 0:
        return None

    ln_rr = math.log(rr)
    se_ln_rr = math.sqrt(1/af - 1/n_t_f + 1/cf - 1/n_c_f)

    z = _z_for_level(conf_level)
    ci_lower = math.exp(ln_rr - z * se_ln_rr)
    ci_upper = math.exp(ln_rr + z * se_ln_rr)

    return ComputedEffect(
        effect_type="RR",
        point_estimate=rr,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        se=se_ln_rr,
        method="log_rr",
        notes=notes,
    )


def compute_rd(events_t: int, n_t: int, events_c: int, n_c: int,
               conf_level: float = 0.95) -> Optional[ComputedEffect]:
    """
    Compute risk difference from 2×2 table.

    RD = p_t - p_c
    SE(RD) = sqrt(p_t*(1-p_t)/n_t + p_c*(1-p_c)/n_c)
    """
    if n_t <= 0 or n_c <= 0:
        return None

    p_t = events_t / n_t
    p_c = events_c / n_c
    rd = p_t - p_c

    # SE using Wald method
    var_rd = p_t * (1 - p_t) / n_t + p_c * (1 - p_c) / n_c
    if var_rd < 0:
        return None
    se_rd = math.sqrt(var_rd) if var_rd > 0 else 0.0001  # floor for zero variance

    z = _z_for_level(conf_level)
    ci_lower = rd - z * se_rd
    ci_upper = rd + z * se_rd

    return ComputedEffect(
        effect_type="RD",
        point_estimate=rd,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        se=se_rd,
        method="wald_rd",
    )


# ============================================================
# CONTINUOUS OUTCOMES — Two-group computations
# ============================================================

def compute_md(mean_t: float, sd_t: float, n_t: int,
               mean_c: float, sd_c: float, n_c: int,
               conf_level: float = 0.95) -> Optional[ComputedEffect]:
    """
    Compute mean difference from two-group summary statistics.

    MD = mean_t - mean_c
    SE(MD) = sqrt(sd_t²/n_t + sd_c²/n_c)
    """
    if n_t <= 0 or n_c <= 0 or sd_t < 0 or sd_c < 0:
        return None

    md = mean_t - mean_c
    var_md = (sd_t ** 2) / n_t + (sd_c ** 2) / n_c
    se_md = math.sqrt(var_md) if var_md > 0 else 0.0001

    z = _z_for_level(conf_level)
    ci_lower = md - z * se_md
    ci_upper = md + z * se_md

    return ComputedEffect(
        effect_type="MD",
        point_estimate=md,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        se=se_md,
        method="independent_groups_md",
    )


def compute_smd(mean_t: float, sd_t: float, n_t: int,
                mean_c: float, sd_c: float, n_c: int,
                conf_level: float = 0.95) -> Optional[ComputedEffect]:
    """
    Compute standardized mean difference (Hedges' g) from two-group data.

    Sp = sqrt(((n_t-1)*sd_t² + (n_c-1)*sd_c²) / (n_t + n_c - 2))  # pooled SD
    d = (mean_t - mean_c) / Sp                                       # Cohen's d
    J = 1 - 3 / (4*(n_t + n_c - 2) - 1)                            # Hedges correction
    g = d * J                                                         # Hedges' g
    V(g) = (n_t + n_c) / (n_t * n_c) + g² / (2*(n_t + n_c - 2))   # variance
    """
    if n_t <= 1 or n_c <= 1 or sd_t < 0 or sd_c < 0:
        return None

    df = n_t + n_c - 2
    if df <= 0:
        return None

    # Pooled standard deviation
    pooled_var = ((n_t - 1) * sd_t ** 2 + (n_c - 1) * sd_c ** 2) / df
    if pooled_var <= 0:
        return None
    sp = math.sqrt(pooled_var)

    if sp == 0:
        return None

    # Cohen's d
    d = (mean_t - mean_c) / sp

    # Hedges' correction factor J (small-sample bias correction)
    j = 1 - 3 / (4 * df - 1)

    # Hedges' g
    g = d * j

    # Variance of g
    v_g = (n_t + n_c) / (n_t * n_c) + (g ** 2) / (2 * df)
    se_g = math.sqrt(v_g)

    z = _z_for_level(conf_level)
    ci_lower = g - z * se_g
    ci_upper = g + z * se_g

    return ComputedEffect(
        effect_type="SMD",
        point_estimate=g,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        se=se_g,
        method="hedges_g",
    )


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def sem_to_sd(sem: float, n: int) -> Optional[float]:
    """Convert standard error of mean to standard deviation: SD = SEM * sqrt(n)."""
    if n <= 0 or sem < 0:
        return None
    return sem * math.sqrt(n)


def pct_to_events(pct: float, n: int) -> int:
    """Convert percentage to event count: events = round(pct/100 * n)."""
    return round(pct / 100.0 * n)


def _normalize_raw_data_aliases(raw_data: dict) -> dict:
    """
    Normalize common raw_data key aliases to intervention/control naming.

    Cochrane-derived rows frequently use exp_*/ctrl_* keys while the extractor
    stack emits intervention_*/control_* keys.
    """
    if not isinstance(raw_data, dict):
        return {}

    normalized = dict(raw_data)
    alias_pairs = (
        ("intervention_events", "exp_cases"),
        ("intervention_n", "exp_n"),
        ("control_events", "ctrl_cases"),
        ("control_n", "ctrl_n"),
        ("intervention_pct", "exp_pct"),
        ("control_pct", "ctrl_pct"),
        ("intervention_mean", "exp_mean"),
        ("intervention_sd", "exp_sd"),
        ("control_mean", "ctrl_mean"),
        ("control_sd", "ctrl_sd"),
        ("intervention_se", "exp_se"),
        ("control_se", "ctrl_se"),
        ("intervention_change", "exp_change"),
        ("control_change", "ctrl_change"),
        ("intervention_sem", "exp_sem"),
        ("control_sem", "ctrl_sem"),
    )
    for canonical_key, alias_key in alias_pairs:
        if normalized.get(canonical_key) is None and raw_data.get(alias_key) is not None:
            normalized[canonical_key] = raw_data[alias_key]
    return normalized


def compute_effect_from_raw_data(raw_data: dict, cochrane_type: str,
                                  cochrane_effect_type: str = None) -> Optional[ComputedEffect]:
    """
    Compute effect from raw_data dict (as stored in gold_50.jsonl).

    Dispatches to the appropriate computation based on available fields:
    - intervention_events/n + control_events/n → OR, RR, RD
    - intervention_mean/sd/n + control_mean/sd/n → MD, SMD
    - intervention_pct/n + control_pct/n → OR, RR (after converting pct→events)
    - intervention_change/sem/n + control_change/sem/n → MD (after SEM→SD)

    Args:
        raw_data: Dict with per-arm statistics
        cochrane_type: "binary" or "continuous"
        cochrane_effect_type: Optional hint ("OR", "RR", "MD", "SMD") for which
            effect to compute. If None, inferred from cochrane_type.
    """
    family = compute_effect_family_from_raw_data(raw_data, cochrane_type)
    if not family:
        return None

    if cochrane_effect_type:
        requested = str(cochrane_effect_type).upper()
        # Pipeline uses ARD enum for risk difference.
        if requested == "ARD":
            requested = "RD"
        for effect in family:
            if effect.effect_type == requested:
                return effect

    preferred = "OR" if str(cochrane_type).lower() == "binary" else "MD"
    for effect in family:
        if effect.effect_type == preferred:
            return effect
    return family[0]


def compute_effect_family_from_raw_data(raw_data: dict, cochrane_type: str) -> List[ComputedEffect]:
    """
    Compute all effect types available from one raw_data record.

    Binary:
        OR, RR, RD
    Continuous:
        MD, SMD
    """
    raw_data = _normalize_raw_data_aliases(raw_data)
    if not raw_data:
        return []

    computed: List[ComputedEffect] = []

    # Binary: events/N
    if "intervention_events" in raw_data and "control_events" in raw_data:
        a = raw_data["intervention_events"]
        n1 = raw_data["intervention_n"]
        c = raw_data["control_events"]
        n2 = raw_data["control_n"]
        for fn in (compute_or, compute_rr, compute_rd):
            result = fn(a, n1, c, n2)
            if result is not None:
                computed.append(result)

    # Binary: percentages
    elif "intervention_pct" in raw_data and "control_pct" in raw_data:
        n1 = raw_data["intervention_n"]
        n2 = raw_data["control_n"]
        a = pct_to_events(raw_data["intervention_pct"], n1)
        c = pct_to_events(raw_data["control_pct"], n2)
        for fn in (compute_or, compute_rr, compute_rd):
            result = fn(a, n1, c, n2)
            if result is not None:
                computed.append(result)

    # Continuous: means/SDs
    elif "intervention_mean" in raw_data and "control_mean" in raw_data:
        m1 = raw_data["intervention_mean"]
        sd1 = raw_data.get("intervention_sd")
        n1 = raw_data["intervention_n"]
        m2 = raw_data["control_mean"]
        sd2 = raw_data.get("control_sd")
        n2 = raw_data["control_n"]

        if sd1 is None and "intervention_se" in raw_data:
            sd1 = sem_to_sd(raw_data["intervention_se"], n1)
        if sd2 is None and "control_se" in raw_data:
            sd2 = sem_to_sd(raw_data["control_se"], n2)

        if sd1 is not None and sd2 is not None:
            md = compute_md(m1, sd1, n1, m2, sd2, n2)
            smd = compute_smd(m1, sd1, n1, m2, sd2, n2)
            if md is not None:
                computed.append(md)
            if smd is not None:
                computed.append(smd)

    # Continuous: change scores with SEM
    elif "intervention_change" in raw_data and "control_change" in raw_data:
        m1 = raw_data["intervention_change"]
        m2 = raw_data["control_change"]
        n1 = raw_data["intervention_n"]
        n2 = raw_data["control_n"]

        sd1 = raw_data.get("intervention_sd")
        sd2 = raw_data.get("control_sd")
        if sd1 is None and "intervention_sem" in raw_data:
            sd1 = sem_to_sd(raw_data["intervention_sem"], n1)
        if sd2 is None and "control_sem" in raw_data:
            sd2 = sem_to_sd(raw_data["control_sem"], n2)

        if sd1 is not None and sd2 is not None:
            md = compute_md(m1, sd1, n1, m2, sd2, n2)
            smd = compute_smd(m1, sd1, n1, m2, sd2, n2)
            if md is not None:
                computed.append(md)
            if smd is not None:
                computed.append(smd)

    deduped: List[ComputedEffect] = []
    seen = set()
    for effect in computed:
        key = effect.effect_type
        if key in seen:
            continue
        seen.add(key)
        deduped.append(effect)
    return deduped


def _z_for_level(conf_level: float) -> float:
    """Get Z-value for a given confidence level."""
    z_map = {
        0.90: 1.6449,
        0.95: 1.9600,
        0.975: 2.2414,
        0.99: 2.5758,
        0.999: 3.2905,
    }
    return z_map.get(conf_level, Z_95)
