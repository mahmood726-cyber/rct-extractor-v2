"""
Cross-derivation and internal-consistency checks for DTA records.

Two jobs:
  * derive_measures_from_2x2 -- compute every accuracy measure exactly from a
    2x2 table (the deterministic, R-checkable maths).
  * check_consistency -- when both a 2x2 AND text-stated measures are present,
    confirm they agree within tolerance; record any disagreement.

The maths is the textbook DTA set (cf. rules/advanced-stats.md DTA section and
lessons.md "DOR = exp(mu1+mu2)" -- here on the natural scale DOR = TP*TN/FP*FN).
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .models import DTAMeasure, TwoByTwo


def derive_measures_from_2x2(t2: TwoByTwo) -> Dict[str, DTAMeasure]:
    """Exact accuracy measures from a 2x2 table (all 'derived' origin)."""
    out: Dict[str, DTAMeasure] = {}

    def add(name: str, value: Optional[float]):
        if value is not None:
            out[name] = DTAMeasure(measure=name, value=value, origin="derived")

    se = t2.sensitivity
    sp = t2.specificity
    add("sensitivity", se)
    add("specificity", sp)
    add("ppv", t2.ppv)
    add("npv", t2.npv)
    add("dor", t2.dor)

    # accuracy = (TP+TN)/N
    if t2.n_total > 0:
        add("accuracy", (t2.tp + t2.tn) / t2.n_total)

    # likelihood ratios (need se, sp in open interval to be finite)
    if se is not None and sp is not None:
        if sp < 1.0:
            add("plr", se / (1.0 - sp))
        if sp > 0.0:
            add("nlr", (1.0 - se) / sp)
    return out


def check_consistency(
    t2: Optional[TwoByTwo],
    stated: Dict[str, DTAMeasure],
    tol: float = 0.02,
) -> List[str]:
    """Compare text-stated measures against 2x2-derived ones.

    Returns a list of human-readable consistency notes (empty == all consistent
    or nothing to compare). Proportions compared on absolute tolerance `tol`;
    ratios on a 10% relative tolerance.
    """
    notes: List[str] = []
    if t2 is None or not t2.is_valid():
        return notes

    derived = derive_measures_from_2x2(t2)
    for name, sm in stated.items():
        dm = derived.get(name)
        if dm is None:
            continue
        if name in ("sensitivity", "specificity", "ppv", "npv", "accuracy"):
            if abs(sm.value - dm.value) > tol:
                notes.append(
                    f"{name}: stated {sm.value:.3f} vs 2x2-derived {dm.value:.3f} "
                    f"(|d|={abs(sm.value - dm.value):.3f} > {tol})"
                )
        else:  # ratios
            denom = dm.value if dm.value else 1.0
            if abs(sm.value - dm.value) / denom > 0.10:
                notes.append(
                    f"{name}: stated {sm.value:.3f} vs 2x2-derived {dm.value:.3f} "
                    f"(rel diff > 10%)"
                )
    return notes


def merge_measures(
    stated: Dict[str, DTAMeasure],
    derived: Dict[str, DTAMeasure],
) -> Dict[str, DTAMeasure]:
    """Prefer stated measures; fill gaps with derived ones."""
    merged = dict(derived)
    merged.update(stated)  # stated wins on key collision
    return merged
