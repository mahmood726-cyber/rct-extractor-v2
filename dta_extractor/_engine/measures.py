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


def _value_first_pattern(label_regex: str) -> re.Pattern:
    """VALUE-before-LABEL phrasing: "95.2% sensitivity", "0.87 specificity".

    Common in field-evaluation abstracts. The value is ADJACENT to its own
    label (only whitespace between), so this is a high-confidence association;
    an optional CI may trail the label. group(1)=value, group(2)=%,
    group(3),(4)=CI. No unbounded quantifiers (no backtracking blowup).
    """
    return re.compile(
        r"(" + _NUM + r")\s*(%?)\s*(?:" + label_regex + r")" + _CI,
        re.IGNORECASE,
    )


_VALUE_FIRST = [(_value_first_pattern(lab), name) for lab, name in _LABELS]

# Paired "sensitivity and specificity ... were X% and Y% (respectively)".
# Overwhelmingly the most common paired construction in DTA abstracts and the
# one the LABEL->VALUE pattern silently drops. group(1)=sens value, (2)=spec.
_PAIR_SESP = re.compile(
    r"(?:sensitivit(?:y|ies)|\bSe\b|\bSn\b)\s+and\s+"
    r"(?:specificit(?:y|ies)|\bSp\b)\s*"
    r"(?:were|was|are|of|:|=|,)?\s*"
    r"(" + _NUM + r")\s*(%?)\s*and\s*(" + _NUM + r")\s*(%?)"
    r"(?:\s*,?\s*respectively)?",
    re.IGNORECASE,
)


def _gapped_pattern(label_regex: str) -> re.Pattern:
    """LABEL of/for <index-test phrase, <=40 non-terminal chars> was/= VALUE.

    Handles "sensitivity of tongue swab Xpert Ultra was 77.8%". The gap is
    bounded and forbids sentence terminators and '%' so it cannot leap across a
    clause boundary or a prior measure's value; an explicit copula/operator is
    required before the value to keep precision high.
    """
    return re.compile(
        r"(?:" + label_regex + r")\s+(?:of|for|by|using|with)\s+"
        r"[^.;:%]{1,40}?\s+(?:was|were|is|are|reached|=|:)\s*"
        r"(" + _NUM + r")\s*(%?)" + _CI,
        re.IGNORECASE,
    )


_GAPPED = [(_gapped_pattern(lab), name) for lab, name in _LABELS]

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


def _build_measure(name, value_tok, pct_tok, ci_lo_tok, ci_hi_tok,
                   whole, start, end) -> Optional[DTAMeasure]:
    """Normalise one raw match into a plausible DTAMeasure (or None)."""
    try:
        raw = _to_float(value_tok)
    except (TypeError, ValueError):
        return None
    is_pct = bool(pct_tok)
    value = _normalise(name, raw, is_pct)
    if not _plausible(name, value):
        return None
    ci_lo = ci_hi = None
    if ci_lo_tok is not None and ci_hi_tok is not None:
        try:
            lo = _to_float(ci_lo_tok)
            hi = _to_float(ci_hi_tok)
        except ValueError:
            lo = hi = None
        if lo is not None:
            ci_pct = is_pct or "%" in whole
            ci_lo = _normalise(name, lo, ci_pct)
            ci_hi = _normalise(name, hi, ci_pct)
            if not (ci_lo <= value <= ci_hi):  # CI must bracket the point
                ci_lo = ci_hi = None
    return DTAMeasure(measure=name, value=value, ci_lower=ci_lo, ci_upper=ci_hi,
                      source_text=whole.strip(), char_start=start, char_end=end)


def extract_measures(text: str) -> List[DTAMeasure]:
    """Return all accuracy measures found in `text`, normalised and de-duplicated.

    Three passes, most-specific first, so a value adjacent to its own label wins
    over a distant label reaching across a comma (the value-first swap bug):
      1. paired "sensitivity and specificity ... X% and Y%" (consumes both);
      2. value-first "X% sensitivity" (value adjacent to its label);
      3. label-first "sensitivity was X%" (original), SKIPPING any value token
         already claimed by pass 1/2 -- this is what kills the swap.
    """
    found: List[DTAMeasure] = []
    claimed: List[tuple] = []  # (start, end) of value tokens already assigned

    def overlaps(s: int, e: int) -> bool:
        return any(not (e <= cs or s >= ce) for cs, ce in claimed)

    # --- Pass 1: paired sensitivity+specificity ---------------------------
    for m in _PAIR_SESP.finditer(text):
        if _is_negative_context(text, m.start()):
            continue
        for name, vtok, ptok, vs, ve in (
            ("sensitivity", m.group(1), m.group(2), m.start(1), m.end(1)),
            ("specificity", m.group(3), m.group(4), m.start(3), m.end(3)),
        ):
            dm = _build_measure(name, vtok, ptok, None, None,
                                m.group(0), m.start(), m.end())
            if dm is not None:
                found.append(dm)
                claimed.append((vs, ve))

    # --- Pass 2: value-first (value adjacent to its own label) ------------
    for pattern, name in _VALUE_FIRST:
        for m in pattern.finditer(text):
            if _is_negative_context(text, m.start()) or overlaps(m.start(1), m.end(1)):
                continue
            dm = _build_measure(name, m.group(1), m.group(2), m.group(3), m.group(4),
                                m.group(0), m.start(), m.end())
            if dm is not None:
                found.append(dm)
                claimed.append((m.start(1), m.end(1)))

    # --- Pass 3: label-first (original), skipping already-claimed values ---
    for pattern, name in _COMPILED:
        for m in pattern.finditer(text):
            if _is_negative_context(text, m.start()) or overlaps(m.start(1), m.end(1)):
                continue
            dm = _build_measure(name, m.group(1), m.group(2), m.group(3), m.group(4),
                                m.group(0), m.start(), m.end())
            if dm is not None:
                found.append(dm)
                claimed.append((m.start(1), m.end(1)))

    # --- Pass 4: gapped label-of-testphrase-was-value (lowest priority) ---
    for pattern, name in _GAPPED:
        for m in pattern.finditer(text):
            if _is_negative_context(text, m.start()) or overlaps(m.start(1), m.end(1)):
                continue
            dm = _build_measure(name, m.group(1), m.group(2), m.group(3), m.group(4),
                                m.group(0), m.start(), m.end())
            if dm is not None:
                found.append(dm)
                claimed.append((m.start(1), m.end(1)))

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
