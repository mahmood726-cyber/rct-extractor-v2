"""
2x2 contingency-table (TP / FP / FN / TN) extraction for DTA text.

Two routes:
  1. EXPLICIT counts -- the text names all four cells, in any order, e.g.
       "TP = 35, FP = 2, FN = 8, TN = 95"
       "true positives 35, false positives 2, false negatives 8, true negatives 95"
       "35 true-positive, 8 false-negative, 2 false-positive and 95 true-negative"
  2. DERIVED counts -- the text gives sensitivity & specificity plus the number
     of diseased and non-diseased subjects, from which TP/FN/TN/FP follow.

All quantifiers are bounded; the four-cell collector reads labelled numbers
within a bounded window rather than via a single nested regex, so there is no
catastrophic-backtracking surface.
"""
from __future__ import annotations

import re
from typing import List, Optional

from .models import TwoByTwo

# One labelled cell: a cell name (full phrase OR abbreviation) followed by a
# small connector and an integer. Counts are bounded to 6 digits.
_CELL_LABELS = {
    "tp": r"true[\s-]*positives?|\bTP\b",
    "fp": r"false[\s-]*positives?|\bFP\b",
    "fn": r"false[\s-]*negatives?|\bFN\b",
    "tn": r"true[\s-]*negatives?|\bTN\b",
}
_CONNECT = r"\s*(?:were|was|of|:|=|,|n\s*=|\()?\s*"
_INT = r"(\d{1,6})"

# Two orientations: "label <connector> number"  and  "number <connector> label".
_CELL_LABEL_FIRST = {
    cell: re.compile(lab + _CONNECT + _INT, re.IGNORECASE)
    for cell, lab in _CELL_LABELS.items()
}
_CELL_NUMBER_FIRST = {
    cell: re.compile(_INT + r"\s*(?:were|was)?\s*(?:" + lab + r")", re.IGNORECASE)
    for cell, lab in _CELL_LABELS.items()
}


def _collect_cells(window: str) -> Optional[dict]:
    """Find the FIRST occurrence of each of the four cells inside `window`."""
    cells = {}
    spans = {}
    for cell in ("tp", "fp", "fn", "tn"):
        best = None
        for compiled in (_CELL_LABEL_FIRST[cell], _CELL_NUMBER_FIRST[cell]):
            m = compiled.search(window)
            if m and (best is None or m.start() < best.start()):
                best = m
        if best is None:
            return None
        # the integer is whichever group captured digits
        val = next((g for g in best.groups() if g and g.isdigit()), None)
        if val is None:
            return None
        cells[cell] = int(val)
        spans[cell] = best.start()
    return cells


# Trigger: any place where all four abbreviations or phrases plausibly co-occur.
_TRIGGER = re.compile(
    r"true[\s-]*positives?|false[\s-]*positives?|\bTP\b|\bFP\b|\bFN\b|\bTN\b",
    re.IGNORECASE,
)


def extract_two_by_two(text: str, window: int = 220) -> List[TwoByTwo]:
    """Extract explicit 2x2 tables. Scans windows seeded at the first cell label."""
    results: List[TwoByTwo] = []
    used_spans: List[tuple] = []
    for trig in _TRIGGER.finditer(text):
        # Begin a little before the trigger so a leading count ("35 true
        # positives") is inside the window, not cut off at the label.
        start = max(0, trig.start() - 15)
        # skip if this trigger is inside a window we already consumed
        if any(a <= start <= b for a, b in used_spans):
            continue
        win = text[start:start + window]
        cells = _collect_cells(win)
        if cells is None:
            continue
        t2 = TwoByTwo(
            tp=cells["tp"],
            fp=cells["fp"],
            fn=cells["fn"],
            tn=cells["tn"],
            source_text=win.strip()[:200],
            char_start=start,
            char_end=start + window,
            origin="stated",
        )
        if t2.is_valid():
            results.append(t2)
            used_spans.append((start, start + window))
    return results


# ---- Derivation route ------------------------------------------------------
_DISEASED = re.compile(
    r"(\d{1,6})\s+(?:patients?|participants?|subjects?|cases?|samples?)?\s*"
    r"(?:with|who\s+had|had|were)?\s*(?:the\s+)?"
    r"(?:disease|condition|target\s+condition|positive(?:\s+by)?\s+(?:the\s+)?reference)",
    re.IGNORECASE,
)


def derive_two_by_two(
    sensitivity: float,
    specificity: float,
    n_diseased: Optional[int],
    n_healthy: Optional[int],
) -> Optional[TwoByTwo]:
    """Reconstruct a 2x2 from Se, Sp and the two group sizes (rounded to ints)."""
    if n_diseased is None or n_healthy is None:
        return None
    if not (0 <= sensitivity <= 1 and 0 <= specificity <= 1):
        return None
    if n_diseased <= 0 or n_healthy <= 0:
        return None
    tp = round(sensitivity * n_diseased)
    fn = n_diseased - tp
    tn = round(specificity * n_healthy)
    fp = n_healthy - tn
    return TwoByTwo(tp=tp, fp=fp, fn=fn, tn=tn, origin="derived")
