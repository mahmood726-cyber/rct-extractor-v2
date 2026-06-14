"""Outcome-mixing guard + maximum methodologically-valid pooling.

Pooling effects that do not measure the SAME thing is one of the most damaging
errors in meta-analysis -- and unlike a transcription slip it is invisible to
numeric checks because every individual number is correct. The literature is
blunt about how common it is:

  * Different OUTCOMES pooled as one (all-cause vs cardiovascular mortality;
    a composite vs one of its components). A pooled estimate across heterogeneous
    constructs answers no clinical question.
  * Same outcome, different TIME POINTS (12-week vs 52-week response) pooled
    together -- a classic multiplicity / "vibration of effects" trap
    (Ioannidis; Tendal 2009 BMJ on outcome-reporting multiplicity).
  * Same construct, different INSTRUMENTS/SCALES (HAM-D vs MADRS; ACR20 vs
    ACR50) pooled on the raw scale instead of as an SMD.

This module derives a (canonical-outcome, time-point) signature for each effect
from the clause that introduces it, reusing the curated COMPONENT_STANDARDIZATION
ontology already maintained for composite endpoints (no parallel ontology), then:

  * check_pool_outcomes(effects)  -> flags a candidate pool that mixes outcomes
    or time points (the GUARD).
  * partition_valid_pools(items)  -> splits a set of effects into the MAXIMAL
    sub-pools that are methodologically valid to combine, so the caller pools as
    many trials as possible without crossing an outcome / time / measure boundary
    (the CONSTRUCTIVE counterpart -- "maximum valid pooling").

Design rule (keep the gold false-positive audit at 0): only ever flag mixing
between two CONFIDENTLY-identified, DIFFERENT known outcomes. An unrecognised
outcome phrase is never used to assert a mix.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from ..core.composite_endpoint import COMPONENT_STANDARDIZATION
except Exception:  # pragma: no cover - defensive: module path drift
    COMPONENT_STANDARDIZATION = {}

# Recognise BOTH the synonym keys ("mi", "death from any cause") AND the
# canonical values themselves ("myocardial infarction", "all-cause mortality"),
# so a spelled-out outcome in the source is matched as well as its abbreviation.
_OUTCOME_MAP = dict(COMPONENT_STANDARDIZATION)
for _v in set(COMPONENT_STANDARDIZATION.values()):
    _OUTCOME_MAP.setdefault(_v, _v)
# Longest-key-first so "non-fatal myocardial infarction" wins over "mi".
_SYNONYM_KEYS = sorted(_OUTCOME_MAP.keys(), key=len, reverse=True)

# Broad mortality/efficacy buckets used only to AVOID over-flagging trivially
# different wordings of the same construct is handled by COMPONENT_STANDARDIZATION;
# here we just normalise whitespace/case.
_TIME_RE = re.compile(
    r"\b(?:at|by|over|after|week|month|year|day)\W{0,3}"
    r"(\d{1,3}(?:\.\d+)?)\s*"
    r"(week|wk|month|mo|year|yr|day)s?\b",
    re.IGNORECASE,
)
_TIME_RE2 = re.compile(
    r"\b(\d{1,3}(?:\.\d+)?)[-\s]*"
    r"(week|wk|month|mo|year|yr|day)s?\b",
    re.IGNORECASE,
)
_UNIT_DAYS = {"day": 1, "wk": 7, "week": 7, "mo": 30, "month": 30,
              "yr": 365, "year": 365}


def _time_to_days(value: float, unit: str) -> float:
    return value * _UNIT_DAYS.get(unit.lower(), 0)


def parse_timepoint(text: str) -> Optional[Tuple[float, str]]:
    """Return (days, raw) for the first follow-up time in `text`, else None."""
    for rx in (_TIME_RE, _TIME_RE2):
        m = rx.search(text or "")
        if m:
            val = float(m.group(1))
            unit = m.group(2).lower()
            return _time_to_days(val, unit), m.group(0).strip()
    return None


def canonical_outcome(text: str) -> Optional[str]:
    """Map text to a canonical outcome name via the outcome ontology. Returns the
    most specific (longest) recognised outcome, or None (never guesses)."""
    if not text:
        return None
    low = text.lower()
    for key in _SYNONYM_KEYS:
        # word-boundary match so 'mi' doesn't fire inside 'mild'
        if re.search(r"(?<![a-z])" + re.escape(key) + r"(?![a-z])", low):
            return _OUTCOME_MAP[key]
    return None


def _nearest_outcome(clause: str) -> Optional[str]:
    """Outcome whose mention sits CLOSEST to the end of `clause` (i.e. nearest
    the effect that the clause introduces). On a positional tie, the more specific
    (longer) phrase wins. Returns None when nothing is recognised."""
    if not clause:
        return None
    low = clause.lower()
    best = None  # (start_pos, len, canonical)
    for key in _SYNONYM_KEYS:
        for m in re.finditer(r"(?<![a-z])" + re.escape(key) + r"(?![a-z])", low):
            cand = (m.start(), len(key), _OUTCOME_MAP[key])
            if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[1] > best[1]):
                best = cand
    return best[2] if best else None


def outcome_signature(text: str, char_start: Optional[int] = None,
                      window: int = 160) -> Dict[str, Any]:
    """Derive {outcome, timepoint_days, timepoint_raw} from the clause that
    introduces an effect (the `window` characters ending at char_start, falling
    back to the whole string)."""
    full = text or ""
    if char_start is not None and char_start > 0:
        # Outcome phrases INTRODUCE their effect -> look only BEHIND char_start so
        # the next sentence's outcome can't leak in. Time points may trail the
        # effect ("HR 0.70 at 52 weeks"), so allow a small forward window for time.
        outcome_clause = full[max(0, char_start - window):char_start]
        time_clause = full[max(0, char_start - window):char_start + 40]
    else:
        outcome_clause = time_clause = full
    tp = parse_timepoint(time_clause)
    return {
        "outcome": _nearest_outcome(outcome_clause),
        "timepoint_days": tp[0] if tp else None,
        "timepoint_raw": tp[1] if tp else None,
    }


def annotate_outcomes(effects: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
    """Attach an `outcome_signature` dict to each effect from its source context.
    Uses the effect's own char_start when present so multi-outcome abstracts bind
    each number to its nearest outcome phrase."""
    for e in effects:
        e["outcome_signature"] = outcome_signature(
            text, char_start=e.get("char_start"),
        )
    return effects


def _measure_family(t: str) -> str:
    t = re.sub(r"[^A-Z]", "", str(t).upper())
    cont = {"MD", "WMD", "SMD", "MEANDIFFERENCE", "STANDARDIZEDMEANDIFFERENCE"}
    if t in cont:
        return "continuous"
    if t in {"OR", "RR", "ODDSRATIO", "RISKRATIO"}:
        return "binary_ratio"
    if t in {"HR", "HAZARDRATIO"}:
        return "time_to_event"
    return t or "unknown"


def _timepoint_bucket(days: Optional[float]) -> Optional[str]:
    """Coarse follow-up buckets. Pooling across buckets is the time-mixing error;
    within a bucket minor differences (48 vs 52 wk) are acceptable."""
    if days is None:
        return None
    if days <= 31:
        return "<=1mo"
    if days <= 120:
        return "1-4mo"
    if days <= 270:
        return "4-9mo"
    if days <= 420:
        return "9-14mo"
    return ">14mo"


def check_pool_outcomes(effects: List[Dict[str, Any]]) -> List[str]:
    """Validate that a candidate POOL measures ONE outcome at ONE follow-up time.
    Each effect should carry `outcome_signature` (see annotate_outcomes). Flags:

      mixed_outcome    : >=2 effects map to DIFFERENT recognised canonical
                         outcomes (e.g. all-cause mortality pooled with CV death,
                         or a composite pooled with a component) -- the deadly,
                         construct-invalid pool. Soft/needs-review, never an
                         auto-drop (the pool owner decides), but high-priority.
      mixed_timepoint  : one outcome reported at >=2 distinct follow-up buckets.

    Only CONFIDENTLY recognised outcomes vote; unknown phrases are ignored, so a
    pool of correctly-matched-but-unrecognised outcomes is never false-flagged.
    """
    sigs = [e.get("outcome_signature") or {} for e in effects]
    outcomes = {s.get("outcome") for s in sigs if s.get("outcome")}
    buckets = {_timepoint_bucket(s.get("timepoint_days"))
               for s in sigs if s.get("timepoint_days") is not None}
    flags = []
    if len(outcomes) > 1:
        flags.append("mixed_outcome")
    if len(buckets) > 1:
        flags.append("mixed_timepoint")
    return flags


def partition_valid_pools(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Maximum methodologically-valid pooling: split `items` into the LARGEST
    sub-pools that may legitimately be combined. Two items pool together iff they
    share (canonical outcome, measure family, follow-up bucket). Items missing an
    outcome/timepoint are grouped by what IS known (so an unlabelled set still
    forms one pool rather than fragmenting).

    Each item: {label, est, se, type|measure, outcome?, timepoint_days?}.
    Returns: [{key:{outcome,measure,timepoint}, items:[...]}, ...] sorted largest
    first, so the caller pools the biggest valid group and reports the rest.
    """
    groups: Dict[Tuple, Dict[str, Any]] = {}
    for it in items:
        outcome = it.get("outcome")
        if outcome is None and it.get("outcome_signature"):
            outcome = it["outcome_signature"].get("outcome")
        measure = _measure_family(it.get("measure") or it.get("type") or "")
        days = it.get("timepoint_days")
        if days is None and it.get("outcome_signature"):
            days = it["outcome_signature"].get("timepoint_days")
        key = (outcome, measure, _timepoint_bucket(days))
        g = groups.setdefault(key, {"key": {
            "outcome": key[0], "measure": key[1], "timepoint": key[2]}, "items": []})
        g["items"].append(it)
    return sorted(groups.values(), key=lambda g: len(g["items"]), reverse=True)
