"""
Data models for diagnostic test accuracy (DTA) extraction.

A DTA study reports how well an *index test* identifies a *target condition*
relative to a *reference standard*. The primary extractable data is the 2x2
contingency table (TP, FP, FN, TN) plus the derived accuracy measures
(sensitivity, specificity, PPV, NPV, likelihood ratios, diagnostic OR, AUC).

These models are deliberately plain dataclasses (no pydantic) to mirror the
RCT engine's `core/models.py` style and to stay dependency-light for installers.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class TwoByTwo:
    """A diagnostic 2x2 contingency table.

    Cells are counts of patients cross-classified by index-test result
    (positive/negative) and reference-standard truth (diseased/healthy):

                       diseased (D+)   healthy (D-)
        test +            TP              FP
        test -            FN              TN
    """

    tp: int
    fp: int
    fn: int
    tn: int

    # provenance
    source_text: str = ""
    char_start: int = 0
    char_end: int = 0
    # "stated" if all four cells appeared verbatim; "derived" if reconstructed
    # from sensitivity/specificity + group sizes.
    origin: str = "stated"

    # ---- group totals -------------------------------------------------
    @property
    def n_diseased(self) -> int:
        return self.tp + self.fn

    @property
    def n_healthy(self) -> int:
        return self.fp + self.tn

    @property
    def n_total(self) -> int:
        return self.tp + self.fp + self.fn + self.tn

    # ---- derived accuracy measures (0-1 scale) ------------------------
    @property
    def sensitivity(self) -> Optional[float]:
        d = self.n_diseased
        return self.tp / d if d > 0 else None

    @property
    def specificity(self) -> Optional[float]:
        d = self.n_healthy
        return self.tn / d if d > 0 else None

    @property
    def ppv(self) -> Optional[float]:
        d = self.tp + self.fp
        return self.tp / d if d > 0 else None

    @property
    def npv(self) -> Optional[float]:
        d = self.tn + self.fn
        return self.tn / d if d > 0 else None

    @property
    def dor(self) -> Optional[float]:
        """Diagnostic odds ratio = (TP*TN)/(FP*FN)."""
        denom = self.fp * self.fn
        if denom == 0:
            return None
        return (self.tp * self.tn) / denom

    def is_valid(self) -> bool:
        """All cells non-negative and at least one diseased and one healthy."""
        cells = (self.tp, self.fp, self.fn, self.tn)
        return (
            all(isinstance(c, int) and c >= 0 for c in cells)
            and self.n_diseased > 0
            and self.n_healthy > 0
        )

    def to_dict(self) -> dict:
        out = {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "tn": self.tn,
            "n_diseased": self.n_diseased,
            "n_healthy": self.n_healthy,
            "n_total": self.n_total,
            "origin": self.origin,
            "source_text": self.source_text,
            "char_start": self.char_start,
            "char_end": self.char_end,
        }
        for k in ("sensitivity", "specificity", "ppv", "npv", "dor"):
            v = getattr(self, k)
            out[k] = round(v, 6) if v is not None else None
        return out


@dataclass
class DTAMeasure:
    """A single reported accuracy measure, e.g. sensitivity = 0.92 (0.88-0.96).

    `value` and the CI bounds are stored on the canonical scale for the measure:
    proportions (sensitivity, specificity, ppv, npv, accuracy, auc) are 0-1;
    ratios (plr, nlr, dor) are kept on their natural >0 scale.
    """

    measure: str  # 'sensitivity' | 'specificity' | 'ppv' | 'npv' |
    #             'plr' | 'nlr' | 'dor' | 'auc' | 'accuracy'
    value: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    ci_level: float = 0.95

    # provenance
    source_text: str = ""
    char_start: int = 0
    char_end: int = 0
    origin: str = "stated"  # "stated" | "derived"

    def to_dict(self) -> dict:
        return {
            "measure": self.measure,
            "value": round(self.value, 6),
            "ci_lower": round(self.ci_lower, 6) if self.ci_lower is not None else None,
            "ci_upper": round(self.ci_upper, 6) if self.ci_upper is not None else None,
            "ci_level": self.ci_level,
            "origin": self.origin,
            "source_text": self.source_text,
            "char_start": self.char_start,
            "char_end": self.char_end,
        }


# Proportion-type measures live on 0-1; ratio-type measures on natural scale.
PROPORTION_MEASURES = frozenset(
    {"sensitivity", "specificity", "ppv", "npv", "accuracy", "auc"}
)
RATIO_MEASURES = frozenset({"plr", "nlr", "dor"})
ALL_MEASURES = PROPORTION_MEASURES | RATIO_MEASURES


@dataclass
class DTAStudyRecord:
    """The unit of DTA extraction: one index-test evaluation in one study."""

    index_test: Optional[str] = None
    reference_standard: Optional[str] = None
    target_condition: Optional[str] = None

    two_by_two: Optional[TwoByTwo] = None
    measures: Dict[str, DTAMeasure] = field(default_factory=dict)

    # internal-consistency report (filled by derive.check_consistency)
    consistency: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # whether this record carries enough to enter a bivariate / HSROC MA:
    # a valid 2x2, or sensitivity+specificity both present.
    poolable: bool = False

    def to_dict(self) -> dict:
        return {
            "index_test": self.index_test,
            "reference_standard": self.reference_standard,
            "target_condition": self.target_condition,
            "two_by_two": self.two_by_two.to_dict() if self.two_by_two else None,
            "measures": {k: v.to_dict() for k, v in self.measures.items()},
            "consistency": self.consistency,
            "warnings": self.warnings,
            "poolable": self.poolable,
        }
