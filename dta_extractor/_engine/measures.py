"""
Accuracy-measure extraction for DTA text.

Extracts sensitivity / specificity / PPV / NPV / LR+ / LR- / DOR / AUC /
accuracy as point estimates with an OPTIONAL 95% CI. This complements the
RCT engine's `core.diagnostic_accuracy_extractor.DiagnosticAccuracyExtractor`,
which only matches measures that ARE accompanied by a CI -- whereas a large
fraction of DTA abstracts report bare point estimates ("sensitivity 92% and
specificity 88%").

Design rules carried over from the RCT engine:
  * No catastrophic-backtracking constructs. Every quantifier is bounded or
    anchored to a literal; there is no nested unbounded `(\\w\\s)+?`.
  * Values are normalised to a canonical scale: proportions -> 0-1, ratios kept
    natural.
  * A negative-context guard drops hypothetical / sample-size / threshold
    statements ("assuming a sensitivity of 90%", "to achieve specificity >= 0.8").
"""
from __future__ import annotations

import re
from typing import List, Optional

from .models import DTAMeasure, PROPORTION_MEASURES

# A bare number, optionally a percentage. Bounded digits => no backtracking blowup.
_NUM = r"\d{1,3}(?:[.,]\d{1,3})?"

# Optional 95% CI in any of the common bracketings. The whole group is optional
# so a bare point estimate still matches. Bounded, single alternation.
_CI = (
    r"(?:\s*[\(\[]\s*(?:95\s*%?\s*(?:CI|confidence\s+interval)[:\s]*)?"
    r"(" + _NUM + r")\s*%?\s*(?:[-‐-―−]|to)\s*(" + _NUM + r")\s*%?\s*[\)\]])?"
)

# value group + optional CI group. Connector covers "was/of/:/=" and bare space.
_CONNECT = r"\s*(?:was|of|of\s+about|:|=|,)?\s*"


def _measure_pattern(label_regex: str) -> re.Pattern:
    # Wrap the label in a non-capturing group so its internal `|` alternation
    # does NOT span the whole pattern (which would make the value group optional
    # and capture nothing -- a precedence trap).
    return re.compile(
        r"(?:" + label_regex + r")" + _CONNECT + r"(" + _NUM + r")\s*(%?)" + _CI,
        re.IGNORECASE,
    )


# label -> (canonical measure name). Spelled-out labels are case-insensitive;
# bare abbreviations use word boundaries so prose words can't masquerade as them.
_LABELS = [
    (r"sensitivit(?:y|ies)|\bSe\b|\bSn\b", "sensitivity"),
    (r"specificit(?:y|ies)|\bSp\b", "specificity"),
    (r"positive\s+predictive\s+value|\bPPV\b", "ppv"),
    (r"negative\s+predictive\s+value|\bNPV\b", "npv"),
    (r"positive\s+likelihood\s+ratio|\bLR\s*\+|\bPLR\b|\bLR\s*\(\s*\+\s*\)", "plr"),
    (r"negative\s+likelihood\s+ratio|\bLR\s*[-−]|\bNLR\b|\bLR\s*\(\s*[-−]\s*\)", "nlr"),
    (r"diagnostic\s+odds\s+ratio|\bDOR\b", "dor"),
    (
        r"area\s+under\s+the\s+(?:ROC\s+|receiver[\s-]operating[\s-]characteristic\s+)?curve"
        r"|\bAUROC\b|\bAUC\b|\bc[-\s]?statistic\b|\bc[-\s]?index\b",
        "auc",
    ),
    (r"overall\s+accuracy|diagnostic\s+accuracy|\baccuracy\b", "accuracy"),
]

_COMPILED = [(_measure_pattern(lab), name) for lab, name in _LABELS]

# Hypothetical / planning / threshold contexts: NOT observed results.
_NEGATIVE_CONTEXT = re.compile(
    r"(?:assum\w+|hypothetic\w+|expect\w+|requir\w+|target\w*|anticipat\w+|"
    r"to\s+achieve|to\s+detect|to\s+ensure|minimum|at\s+least|threshold|"
    r"power(?:ed)?|sample[-\s]size)",
    re.IGNORECASE,
)


def _is_negative_context(text: str, start: int, window: int = 60) -> bool:
    ctx = text[max(0, start - window):start]
    return bool(_NEGATIVE_CONTEXT.search(ctx))


def _to_float(tok: str) -> float:
    return float(tok.replace(",", "."))


def _normalise(name: str, value: float, is_pct: bool) -> float:
    """Proportions -> 0-1. Ratios kept natural."""
    if name in PROPORTION_MEASURES:
        if is_pct or value > 1.0:
            return value / 100.0
    return value


def _plausible(name: str, v: float) -> bool:
    if name in PROPORTION_MEASURES:
        return 0.0 <= v <= 1.0
    # ratios must be positive and finite
    return 0.0 < v < 1e6


def extract_measures(text: str) -> List[DTAMeasure]:
    """Return all accuracy measures found in `text`, normalised and de-duplicated."""
    found: List[DTAMeasure] = []
    for pattern, name in _COMPILED:
        for m in pattern.finditer(text):
            if _is_negative_context(text, m.start()):
                continue
            try:
                raw = _to_float(m.group(1))
            except (TypeError, ValueError):
                continue
            is_pct = bool(m.group(2)) or raw > 1.0 if name in PROPORTION_MEASURES else False
            value = _normalise(name, raw, bool(m.group(2)))
            if not _plausible(name, value):
                continue

            ci_lo = ci_hi = None
            if m.group(3) is not None and m.group(4) is not None:
                try:
                    lo = _to_float(m.group(3))
                    hi = _to_float(m.group(4))
                except ValueError:
                    lo = hi = None
                if lo is not None:
                    ci_pct = bool(m.group(2)) or "%" in m.group(0)
                    ci_lo = _normalise(name, lo, ci_pct)
                    ci_hi = _normalise(name, hi, ci_pct)
                    # CI must bracket the point estimate (else it's a mis-parse).
                    if not (ci_lo <= value <= ci_hi):
                        ci_lo = ci_hi = None

            found.append(
                DTAMeasure(
                    measure=name,
                    value=value,
                    ci_lower=ci_lo,
                    ci_upper=ci_hi,
                    source_text=m.group(0).strip(),
                    char_start=m.start(),
                    char_end=m.end(),
                )
            )

    # De-duplicate: same measure at near-identical span. Keep the one WITH a CI.
    found.sort(key=lambda x: (x.char_start, x.ci_lower is None))
    deduped: List[DTAMeasure] = []
    seen = []  # (measure, start)
    for mz in found:
        if any(
            mz.measure == pm and abs(mz.char_start - ps) <= 3 for pm, ps in seen
        ):
            continue
        seen.append((mz.measure, mz.char_start))
        deduped.append(mz)
    return deduped
