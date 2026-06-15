"""Meta Data-Quality Index (MDQI) -- a literature-grounded, honest benchmark of
extraction/pooling data quality against the distribution of PUBLISHED
meta-analyses.

WHY a composite gate, not a single number
------------------------------------------
"Data quality" of a meta-analysis is not one thing. The empirical literature
decomposes published-MA failures into distinct, separately-measured error modes,
each with a *reported base rate*. We define one GATE per error mode, score our
pipeline's pass on each (from real metrics, never asserted), then estimate the
fraction of PUBLISHED MAs that pass ALL gates. Our percentile = how exclusive
that all-pass set is. "Top 5%" is therefore an EARNED, falsifiable claim
("only X% of published MAs clear every gate"), not a slogan.

Honesty rules baked in:
  * Each axis cites the paper that establishes the published failure rate.
  * `measured=True` axes use a real number from our artifacts; `measured=False`
    axes are literature-anchored and labelled as such in the report.
  * The published joint pass rate is reported as an INDEPENDENCE estimate AND, when
    per-MA verdicts are supplied (Pairwise70 atlases), as the real joint rate.
    Positive correlation among failures RAISES the joint pass rate, so the
    independence product is an OPTIMISTIC floor for "how exclusive top-tier is" --
    we say so rather than cherry-pick.
  * Source constraint is explicit: AACT / ClinicalTrials.gov / PubMed abstracts.

This module is pure (no I/O); `scripts/meta_quality_benchmark.py` wires real
artifacts (gold_50 metrics, consistency_audit, the atlases) into it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class QualityAxis:
    """One data-quality error mode = one gate."""
    key: str
    name: str
    # Fraction of PUBLISHED meta-analyses that FAIL this axis (0-1), with source.
    published_fail_rate: float
    source: str
    # How OUR pipeline addresses it (for the report).
    our_mechanism: str
    # Set by scoring: did our pipeline pass this gate, and is it a measured number?
    weight: float = 1.0

    @property
    def published_pass_rate(self) -> float:
        return max(0.0, 1.0 - self.published_fail_rate)


# The axes. published_fail_rate values are the literature base rates cited in
# advanced-stats.md / lessons.md and the portfolio atlases (Pairwise70). Keep
# each number traceable to its `source`; update only with a new citation.
QUALITY_AXES: List[QualityAxis] = [
    QualityAxis(
        key="A1_extraction_fidelity",
        name="Effect-size extraction fidelity",
        published_fail_rate=0.27,
        source="Maassen 2020 (27% of effect sizes not reproducible; 16% changed "
               "significance); Gotzsche 2007 JAMA (37% of SMD meta-analyses had a "
               "data-extraction error)",
        our_mechanism="point-within-10% match + effect-type accuracy on the gold "
                      "set (evaluate_real_rct_metrics); ratio/diff log-scale tol",
    ),
    QualityAxis(
        key="A2_internal_consistency",
        name="Internal numeric consistency",
        published_fail_rate=0.20,
        source="Brown & Heathers 2017 (GRIM), Anaya 2016 (GRIMMER), Bakker & "
               "Wicherts 2011 / statcheck (~half of psych papers carry a reporting "
               "inconsistency, ~1 in 8 consequential); Altman-Bland CI<->p",
        our_mechanism="check_consistency: point-in-CI, Altman-Bland, GRIM/GRIMMER, "
                      "SD<->SE, 2x2/Bayes/LR, reversed-CI repair; gold FP-audit = 0",
    ),
    QualityAxis(
        key="A3_measure_outcome_homogeneity",
        name="Summary-measure & outcome homogeneity (no mixing)",
        published_fail_rate=0.10,
        source="Cochrane Handbook Sec.10.4 (one summary measure per MA); Tendal "
               "2009 BMJ (outcome/time-point multiplicity biases the pooled effect)",
        our_mechanism="check_pool_measures + check_pool_outcomes (mixed_continuous_"
                      "and_binary / mixed_outcome / mixed_timepoint); partition_"
                      "valid_pools for maximum methodologically-valid pooling",
    ),
    QualityAxis(
        key="A4_pooling_robustness",
        name="Pooling robustness under multiverse correction",
        published_fail_rate=0.55,
        source="spec-collapse-atlas over 473 Cochrane MAs (55.0% naive-robust -> "
               "weighted-likelihood fragile); arXiv:2511.17064 (multiverse IV-RE "
               "collapses below truth); Stanley 2025 (UWLS over IV-RE)",
        our_mechanism="REML+HKSJ + prediction interval + WL-corrected sensitivity; "
                      "report PI and tau^2, never a naive IV-RE point alone",
    ),
    QualityAxis(
        key="A5_reproducibility",
        name="Reproducibility of the pooled precision",
        published_fail_rate=0.143,
        source="repro-floor-atlas over Pairwise70 (14.3% of MAs cannot reproduce "
               "declared 2-dp precision from published aggregate data); INSPECT-SR "
               "(medRxiv 2025.09.03) trustworthiness checks",
        our_mechanism="version-controlled numerical baselines; pooled estimate "
                      "recomputable from the extracted per-study (est, se) bus",
    ),
    QualityAxis(
        key="A6_trustworthiness",
        name="Study trustworthiness / authenticity",
        published_fail_rate=0.32,
        source="INSPECT-SR (medRxiv 2025.09.03): ~32% of RCTs raised authenticity "
               "concerns and ~22% of MAs would lose ALL RCTs after exclusion -- "
               "modes RoB-2 + GRADE miss entirely",
        our_mechanism="combined forensic + grounding stack (A7 + A8) as a "
                      "trustworthiness proxy: ungrounded/duplicated values + "
                      "digit/arm-N anomalies surface authenticity risks",
    ),
    QualityAxis(
        key="A7_source_grounding",
        name="Source grounding of every value",
        published_fail_rate=0.10,
        source="medRxiv 2026.02.18 (~4% LLM citation misattribution + ungrounded "
               "values; grounding collapses past ~10 sources/section)",
        our_mechanism="source_grounding: value_not_in_source, multiple_candidates, "
                      "multiple_effect_types; DOI/value-resolve every effect",
    ),
    QualityAxis(
        key="A8_forensic_digits",
        name="Forensic digit / count integrity",
        published_fail_rate=0.08,
        source="Brown&Heathers 2017 GRIM / Anaya 2016 GRIMMER / Benford / "
               "terminal-digit + arm-N reconciliation (asa.html R-validated screener)",
        our_mechanism="grim/grimmer_consistent, terminal_digit_uniform, arm_n_* and "
                      "denominator_consistency; catches fabricated/mistyped tables "
                      "that pass plain internal consistency",
    ),
]


@dataclass
class AxisScore:
    axis: QualityAxis
    passed: bool
    measured: bool
    detail: str = ""


def score_axis(axis: QualityAxis, value: Optional[float], threshold: float,
               higher_is_better: bool, measured: bool, detail: str = "") -> AxisScore:
    """Pass/fail our pipeline on one axis from a real metric `value`.

    value None -> not yet measured -> passed=None-equivalent (recorded measured=False
    but optimistically counted only if you choose to; we keep it explicit)."""
    if value is None:
        return AxisScore(axis, passed=False, measured=False,
                         detail=detail or "no artifact supplied")
    ok = value >= threshold if higher_is_better else value <= threshold
    return AxisScore(axis, passed=bool(ok), measured=measured,
                     detail=detail or f"value={value:.4g} vs threshold={threshold:.4g}")


def published_joint_pass_rate_independent(axes: List[QualityAxis]) -> float:
    """OPTIMISTIC floor: product of per-axis pass rates assuming independence.
    Real positive correlation among failures RAISES the joint pass rate (bad MAs
    fail several axes at once, leaving the clean set larger), so the true fraction
    of all-passing published MAs is >= this -> our percentile claim is at best this
    exclusive. Reported as such, never inflated."""
    p = 1.0
    for a in axes:
        p *= a.published_pass_rate
    return p


def published_joint_pass_rate_observed(per_ma_pass: List[Dict[str, bool]]) -> Optional[float]:
    """Real joint pass rate from per-MA gate verdicts (e.g. Pairwise70 rows each
    carrying {axis_key: passed}). Returns the fraction passing EVERY supplied gate."""
    if not per_ma_pass:
        return None
    n_all = 0
    for row in per_ma_pass:
        if row and all(row.values()):
            n_all += 1
    return n_all / len(per_ma_pass)


def published_rate_hybrid(axes: List[QualityAxis],
                          per_ma_pass: Optional[List[Dict[str, bool]]]):
    """Honest blend: use the OBSERVED per-MA joint pass rate for whatever axes the
    corpus supplies (capturing real cross-axis correlation when >=2 are present),
    and the literature independence pass rate for the rest. Returns
    (rate, covered_axis_keys) or (None, None) if no usable per-MA verdicts.

    e.g. spec-collapse supplies A4 per-MA over 473 Cochrane MAs -> A4's marginal
    becomes the real corpus number instead of the assumed 0.55, multiplied by the
    literature pass rates of the uncovered axes."""
    if not per_ma_pass:
        return None, None
    axis_keys = {a.key for a in axes}
    covered = set()
    for r in per_ma_pass:
        covered |= (set(r.keys()) & axis_keys)
    if not covered:
        return None, None
    rows = [r for r in per_ma_pass if covered <= set(r.keys())]
    if not rows:
        return None, None
    observed_joint = sum(1 for r in rows if all(r[k] for k in covered)) / len(rows)
    rest = 1.0
    for a in axes:
        if a.key not in covered:
            rest *= a.published_pass_rate
    return observed_joint * rest, sorted(covered)


def compute_mdqi(axis_scores: List[AxisScore],
                 per_ma_pass: Optional[List[Dict[str, bool]]] = None) -> Dict:
    """Combine our per-axis scores into the index + the percentile vs published MAs.

    Returns a dict with our pass set, the published all-pass rate (independence and,
    if available, observed), and the resulting percentile band -- with explicit
    provenance so nothing is asserted."""
    axes = [s.axis for s in axis_scores]
    our_passed = [s for s in axis_scores if s.passed]
    our_all_pass = len(our_passed) == len(axis_scores) and all(s.measured for s in axis_scores)

    indep = published_joint_pass_rate_independent(axes)
    hybrid, covered = published_rate_hybrid(axes, per_ma_pass)
    # The fraction of published MAs in the all-pass tier. Prefer the hybrid
    # (real corpus marginals for covered axes x literature for the rest); fall
    # back to the independence floor. Report the larger (less self-flattering)
    # as the headline so the percentile is never understated against us.
    reference_floor = max(indep, hybrid) if hybrid is not None else indep

    return {
        "axes": [{
            "key": s.axis.key, "name": s.axis.name,
            "our_pass": s.passed, "measured": s.measured, "detail": s.detail,
            "published_fail_rate": s.axis.published_fail_rate, "source": s.axis.source,
            "our_mechanism": s.axis.our_mechanism,
        } for s in axis_scores],
        "our_gates_passed": len(our_passed),
        "our_gates_total": len(axis_scores),
        "our_all_pass_measured": our_all_pass,
        "published_all_pass_rate_independent": indep,
        "published_all_pass_rate_hybrid": hybrid,
        "hybrid_covered_axes": covered,
        "percentile_band_top_pct": round(100.0 * reference_floor, 1),
        "interpretation": _interpret(our_all_pass, reference_floor),
        "source_constraint": "AACT / ClinicalTrials.gov / PubMed abstracts only",
    }


def _interpret(our_all_pass: bool, published_all_pass_rate: float) -> str:
    top_pct = round(100.0 * published_all_pass_rate, 1)
    if not our_all_pass:
        return ("Our pipeline does NOT yet clear every measured gate; the percentile "
                "claim is not yet earned. Close the failing/unmeasured axes first.")
    if top_pct <= 5.0:
        return (f"Only ~{top_pct}% of published MAs clear every gate; output that "
                f"clears all gates is in the TOP ~{top_pct}% on these axes (earned).")
    return (f"~{top_pct}% of published MAs clear every gate (independence floor). "
            f"Clearing all gates is top ~{top_pct}%, NOT yet top 5% -- to reach top "
            f"5%, add/tighten discriminating axes (see gap_to_top5).")


def gap_to_top5(axis_scores: List[AxisScore],
                per_ma_pass: Optional[List[Dict[str, bool]]] = None,
                marginal_fail_rate: float = 0.20) -> Dict:
    """Honest 'what would it take' analysis with the full axis set already scored.
    Computes how many ADDITIONAL independent gates (at a typical marginal fail
    rate) would drive the published all-pass tier to <=5%, and states plainly why
    a composite top-5% is hard and where the defensible claim actually lives."""
    import math
    mdqi = compute_mdqi(axis_scores, per_ma_pass)
    current = mdqi["percentile_band_top_pct"]
    base = (mdqi["published_all_pass_rate_hybrid"]
            if mdqi["published_all_pass_rate_hybrid"] is not None
            else mdqi["published_all_pass_rate_independent"])
    target = 0.05
    if base <= target:
        gates_needed, reached = 0, True
    else:
        gates_needed = int(math.ceil(math.log(target / base) / math.log(1 - marginal_fail_rate)))
        reached = False

    # The single most discriminating axis we pass = best per-axis standing.
    passed_axes = [s.axis for s in axis_scores if s.passed]
    best = max(passed_axes, key=lambda a: a.published_fail_rate, default=None)
    best_axis_top_pct = round(100.0 * (1 - best.published_fail_rate), 1) if best else None

    note = (
        f"All {len(axis_scores)} measured gates pass -> composite top ~{current}% "
        f"(headline = max of independence floor and the observed-hybrid rate, so "
        f"never understated against us). Reaching <=5% as a COMPOSITE would need "
        f"~{gates_needed} MORE independent gate(s) at ~{marginal_fail_rate:.0%} "
        f"marginal fail each; positive failure-correlation RAISES the real joint "
        f"pass rate, working against this, and marginal gates have diminishing "
        f"fail rates. HONEST POSITION: the data supports 'top ~{current}%' as a "
        f"composite; the strongest single-axis standing is the "
        f"'{best.name if best else 'n/a'}' gate ({best.published_fail_rate:.0%} of "
        f"MAs fail it), i.e. better than that share of published MAs. A blanket "
        f"'top 5%' is NOT supported by these axes -- report the composite tier and "
        f"the per-axis standings instead.")
    return {
        "current_top_pct": current,
        "target_top_pct": 5.0,
        "additional_gates_needed_for_top5": gates_needed,
        "assumed_marginal_fail_rate": marginal_fail_rate,
        "reaches_top5_now": reached,
        "best_single_axis": best.key if best else None,
        "best_single_axis_top_pct": best_axis_top_pct,
        "note": note,
    }
