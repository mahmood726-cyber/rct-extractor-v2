"""Source-grounding & multi-candidate disambiguation for extracted effects.

Internal-consistency checks (internal_consistency.py) verify that an extracted
(point, CI, p) triple agrees with *itself*. But the consistency audit showed the
remaining errors are extractions that are internally consistent yet WRONG:

  * wrong estimand  -- an HR returned for a mean-difference outcome (the HR value
    does not even appear in the source text);
  * wrong comparison -- the text reports OR 3.0 (vs placebo) AND OR 1.4 (vs an
    active comparator), and the extractor grabbed the wrong one.

Those need the SOURCE TEXT, not just the numbers. This module flags (never
auto-edits -- which value is the target is genuinely ambiguous):

  value_not_in_source : the extracted effect size does not appear in the text
                        (within rounding tolerance) -> likely a wrong/hallucinated
                        estimand. SOFT: a value computed from counts may not appear
                        verbatim, so it only marks needs_review.
  multiple_candidates : the text mentions >=2 distinct effect estimates of the
                        extracted type -> ambiguous which is the target outcome /
                        comparison; the extraction needs human disambiguation.

Both are soft (needs_review) flags -- they surface the extraction for a human,
they do not drop or rewrite it.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

_NUM = r"(\d+(?:\.\d+)?)"

# Spelled-out effect names (case-insensitive) per type family.
_PHRASE = {
    "HR": r"hazard\s+ratio",
    "OR": r"odds\s+ratio",
    "RR": r"(?:risk\s+ratio|relative\s+risk)",
    "IRR": r"(?:incidence\s+rate\s+ratio|rate\s+ratio)",
}
# Uppercase abbreviations (case-SENSITIVE so the English word "or" is not matched).
_ABBR = {"HR": "HR", "OR": "OR", "RR": "RR", "IRR": "IRR"}

_RATIO_FAMILIES = set(_PHRASE)


def _family(effect_type: str) -> Optional[str]:
    t = re.sub(r"[^A-Z]", "", str(effect_type or "").upper())
    if t in _RATIO_FAMILIES:
        return t
    if "HAZARD" in t:
        return "HR"
    if "ODDS" in t:
        return "OR"
    if t.endswith("RATIO") or "RELATIVERISK" in t or "RISKRATIO" in t:
        return "RR"
    return None


def _numbers_in_text(text: str) -> List[float]:
    return [float(m) for m in re.findall(r"\d+(?:\.\d+)?", text or "")]


def value_grounded(value: Optional[float], text: str,
                   rel_tol: float = 0.02, abs_tol: float = 0.01) -> bool:
    """True if `|value|` appears in the text as a number (within rounding tol).

    Sign-agnostic: the extractor may report a direction the text states the other
    way round (e.g. a difference written 'A vs B'), so compare magnitudes.
    """
    if value is None or not text:
        return True
    av = abs(value)
    for n in _numbers_in_text(text):
        if abs(abs(n) - av) <= max(abs_tol, rel_tol * av):
            return True
    return False


def count_type_mentions(text: str, effect_type: str) -> int:
    """Count DISTINCT effect-estimate values of this type stated in the text.

    Matches "<type-token> [= : (] <number>" where the type token is the spelled
    name (case-insensitive) or the uppercase abbreviation (case-sensitive, so
    'OR'/'RR' do not match the English words). De-duplicates by value so a value
    repeated in a sentence counts once.
    """
    fam = _family(effect_type)
    if not fam or not text:
        return 0
    sep = r"\s*[=:(]?\s*(?:of\s+)?"
    vals = set()
    for m in re.finditer(_PHRASE[fam] + sep + _NUM, text, re.I):
        vals.add(round(float(m.group(1)), 3))
    for m in re.finditer(r"\b" + _ABBR[fam] + r"\b" + sep + _NUM, text):
        vals.add(round(float(m.group(1)), 3))
    return len(vals)


def check_grounding(effect: Dict, text: str) -> List[str]:
    """Return grounding flags for one extracted effect against its source text."""
    flags = []
    es = effect.get("effect_size")
    etype = effect.get("type", "")
    # Value grounding ONLY for ratio effects: a ratio's point estimate is stated
    # verbatim, so a value absent from the text signals a wrong estimand (e.g. an
    # HR returned for a mean-difference outcome). Differences (MD/ARD/SMD) are
    # routinely derived/rounded and would false-flag, so they are not checked.
    if text and _family(etype) and es is not None and not value_grounded(es, text):
        flags.append("value_not_in_source")
    if text and count_type_mentions(text, etype) > 1:
        flags.append("multiple_candidates")
    return flags


def _first_index(value, text, rel_tol=0.02, abs_tol=0.01):
    """Earliest character index where |value| appears in the text, or -1."""
    if value is None or not text:
        return -1
    av = abs(value)
    for m in re.finditer(r"\d+(?:\.\d+)?", text):
        if abs(abs(float(m.group(0))) - av) <= max(abs_tol, rel_tol * av):
            return m.start()
    return -1


def order_effects(effects, text):
    """Order extracted effects so the PRIMARY-outcome effect comes first.

    The consistency audit found effects[0] was sometimes a SECONDARY outcome
    (INPULSIS returned a secondary HR before the primary mean difference), so a
    consumer taking the first effect got the wrong estimand. Text-grounded,
    stable heuristic — reorders only, never drops or edits:
      * earlier mention in the abstract ranks first (abstracts lead with the
        primary outcome);
      * an explicit "primary outcome/endpoint" just before the value promotes it;
        "secondary"/"exploratory"/"post hoc" just before it demotes it.
    """
    if not text or len(effects) < 2:
        return effects
    low = text.lower()

    def key(e):
        idx = _first_index(e.get("effect_size"), text)
        if idx < 0:
            return (10 ** 9, 0)            # un-locatable values sink to the end
        before = low[max(0, idx - 80):idx]
        boost = 0
        if re.search(r"primary\s+(?:outcome|end\s?point|efficacy)", before):
            boost -= 1_000_000             # explicit primary → first
        if re.search(r"\b(?:secondary|exploratory|post[\s-]?hoc)\b", low[max(0, idx - 50):idx]):
            boost += 500_000               # explicitly secondary → later
        return (idx + boost, idx)

    return sorted(effects, key=key)


def annotate_grounding(effects, text):
    """Attach grounding flags to each effect (under 'grounding') and merge them
    into the existing consistency flag list + needs_review. Never edits values.

    Result-level signal: when the extraction yields >=2 DISTINCT effect types
    (e.g. an HR for one outcome and an MD for another), which one is the target
    estimand is ambiguous -- the consumer must pick. Flag every effect
    'multiple_effect_types' for review (soft; nothing is dropped).
    """
    distinct_types = {str(e.get("type", "")).upper() for e in effects if e.get("type")}
    multi_type = len(distinct_types) > 1
    for e in effects:
        gf = check_grounding(e, text)
        if multi_type:
            gf = gf + ["multiple_effect_types"]
        e["grounding"] = {"flags": gf}
        if gf:
            e["needs_review"] = True
            c = e.get("consistency")
            if isinstance(c, dict):
                c["flags"] = list(c.get("flags") or []) + gf
    return effects
