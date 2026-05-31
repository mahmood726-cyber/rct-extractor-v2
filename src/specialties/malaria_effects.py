"""
Malaria effect-estimate augmenter.

The deterministic core engine handles most effect formats, but malaria abstracts
(heavily Lancet / BMC / PLoS) use a few forms the core misses:

  1. Protective / vaccine efficacy as a PERCENTAGE with CI -- not a ratio, so the
     core (built around HR/OR/RR) has no concept of it. This is the single most
     common malaria-prevention/vaccine estimate (RTS,S, R21, SMC, IPT, bednets).
       "protective efficacy 42.7%, 95% CI 22.5-57.7"
       "vaccine efficacy (VE) was 56% (95% CI 51-60)"
  2. Bracketed / colon-punctuated ADJUSTED ratios the core drops:
       "adjusted odds ratio [aOR]: 0.50; 95%CI: 0.34-0.75"
       "adjusted risk ratio [aRR] = 0.78, 95% confidence interval [CI] 0.45-1.35"
       "adjusted incidence rate ratio (aIRR) = 1.23, 95% CI = 1.01, 1.50"

This module is ADDITIVE: it never modifies the core. The wrapper merges core +
augmenter results and de-duplicates so nothing is double counted.

Returned dicts mirror the core's to_dict() shape (type, effect_size, ci_lower,
ci_upper, source_text, char_start, char_end) plus origin="malaria_augment".
"""
import re
from typing import List, Dict, Optional

# Lancet middle-dot decimal; numbers may omit the leading zero (".58").
_NUM = r"[-+]?(?:\d+(?:[.·]\d+)?|[.·]\d+)"
_DASH = r"(?:–|—|−|-|to)"
# CI prefix: tolerate a short alphabetic label bracket "[CI]" (NOT a numeric
# bracket, which holds the limits), optional :/=/, and an optional opening
# bracket before the lower limit -- "(95% CI [0.57, 0.86])".
_CI = (r"95\s*%\s*(?:CI|confidence interval)s?\s*"
       r"(?:[\[(][A-Za-z][^\])]{0,8}[\])])?\s*[:=,]?\s*[\[(]?\s*")

# Map abbreviation/phrase -> core effect-type code. Case-insensitive so the
# spelled forms AND the abbreviations (aOR, aHR, IRR, MD ...) both resolve.
_RATIO_TYPE = [
    (re.compile(r"incidence rate ratio|\ba?IRR\b", re.I), "IRR"),
    (re.compile(r"\brate ratio\b", re.I), "IRR"),
    (re.compile(r"hazard ratio|\ba?HR\b", re.I), "HR"),
    (re.compile(r"odds ratio|\ba?OR\b", re.I), "OR"),
    (re.compile(r"risk ratio|relative risk|\ba?RR\b", re.I), "RR"),
    (re.compile(r"standardi[sz]ed mean difference|\bSMD\b", re.I), "SMD"),
    (re.compile(r"mean difference|\bMD\b", re.I), "MD"),
    (re.compile(r"risk difference|\ba?RD\b", re.I), "ARD"),
]


def _f(s: str) -> Optional[float]:
    try:
        return float(s.replace("·", "."))
    except (ValueError, AttributeError):
        return None


def _mk(etype, val, lo, hi, text, start, end):
    return {
        "type": etype, "effect_size": val,
        "ci_lower": lo, "ci_upper": hi,
        "p_value": None,
        "source_text": re.sub(r"\s+", " ", text[start:end]).strip()[:160],
        "char_start": start, "char_end": end,
        "origin": "malaria_augment",
    }


# 1. Efficacy percentage:  (protective|vaccine) efficacy [...] NN% [...] 95% CI lo-hi
_EFFICACY_RE = re.compile(
    r"(?P<kind>protective|vaccine)\s+efficacy"
    r"(?:\s*\((?:VE|PE)\))?"
    r"[^%\d]{0,18}?"
    r"(?P<val>" + _NUM + r")\s*%"
    r"[^\d]{0,30}?" + _CI +
    r"(?P<lo>" + _NUM + r")\s*" + _DASH + r"\s*(?P<hi>" + _NUM + r")",
    re.IGNORECASE,
)

# 2. Labelled ratio with flexible bracket/colon/equals punctuation:
#    <phrase or abbrev> [ ... ] [:=,] value [ ... ] 95% CI lo (-|to) hi
_RATIO_RE = re.compile(
    r"(?P<label>(?:adjusted\s+)?(?:incidence\s+rate\s+ratio|rate\s+ratio|"
    r"hazard\s+ratio|odds\s+ratio|risk\s+ratio|relative\s+risk|risk\s+difference|"
    r"standardi[sz]ed\s+mean\s+difference|mean\s+difference)"
    r"|\b(?:aOR|aHR|aRR|aIRR|aRD|SMD|MD)\b)"
    r"\s*(?:\[[^\]]{1,12}\]|\([^)]{1,12}\))?\s*"   # optional [aOR] / (aIRR)
    r"(?:[:=,]|\bof\b|\bwas\b)?\s*"
    r"(?P<val>" + _NUM + r")"
    r"[^\d]{0,30}?" + _CI +
    r"(?P<lo>" + _NUM + r")\s*(?:" + _DASH + r"|,)\s*(?P<hi>" + _NUM + r")",
    re.IGNORECASE,
)


# Bare uppercase abbreviation followed by '=', ':' or ',' then the value and a
# 95% CI (e.g. "OR = 0.45, 95% CI: 0.36, 0.56" or the table form "RR, 0.34;
# 95% CI, 0.15 to 0.61"). CASE-SENSITIVE (no re.I) so the conjunction "or" can
# never match; the mandatory trailing "95% CI lo-hi" disambiguates from prose
# (e.g. "RR, 18 breaths"). Lets a second effect in a combined clause be caught.
_BARE_RATIO_RE = re.compile(
    r"\b(?P<label>aOR|aHR|aRR|aIRR|OR|HR|RR|IRR|RD)\s*[:=,]\s*"
    r"(?P<val>" + _NUM + r")"
    r"[^\d]{0,24}?" + _CI +
    r"(?P<lo>" + _NUM + r")\s*(?:" + _DASH + r"|,)\s*(?P<hi>" + _NUM + r")")


# RevMan / Cochrane forest-plot rows put "95% CI" inside the method annotation
# and the limits in brackets after the value:
#   "Mean Difference (IV, Random, 95% CI) -6.07 [-10.66, -1.48]"
#   "Risk Ratio (M-H, Fixed, 95% CI) 0.74 [0.61, 0.90]"
_REVMAN_RE = re.compile(
    r"(?P<label>mean difference|standardi[sz]ed mean difference|risk ratio|"
    r"relative risk|odds ratio|hazard ratio|risk difference|rate ratio|"
    r"incidence rate ratio)"
    r"[^\d\n]{0,40}?95\s*%\s*CI[)\s,:=]*"
    r"(?P<val>" + _NUM + r")\s*[\[(]\s*"
    r"(?P<lo>" + _NUM + r")\s*[,;]\s*(?P<hi>" + _NUM + r")\s*[\])]",
    re.IGNORECASE,
)

# PDF text frequently carries fi/fl ligatures ("conﬁdence interval") and odd
# spaces; normalising lets the same patterns fire on PDF and abstract text alike.
_LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi",
    "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st",
}


def normalize_text(text: str) -> str:
    if not text:
        return text
    for lig, repl in _LIGATURES.items():
        if lig in text:
            text = text.replace(lig, repl)
    return text


# Ratio effect-type codes (where a value must be ratio-shaped, and where bare
# RR/HR abbreviations risk colliding with vital signs).
_RATIO_CODES = {"HR", "OR", "RR", "IRR", "GMR"}
_VITAL_CONTEXT = re.compile(
    r"respiratory|heart\s*rate|pulse|breathing|\bbreaths?\b|\bbpm\b|"
    r"beats?\s*(?:/|per)\s*min|/\s*min\b|per\s+minute|mm\s*hg|systolic|diastolic",
    re.I)


def _ratio_type(label: str) -> Optional[str]:
    for rx, code in _RATIO_TYPE:
        if rx.search(label):
            return code
    return None


def augment_malaria_effects(text: str, existing: Optional[List[Dict]] = None) -> List[Dict]:
    """Return malaria-specific effect dicts the core engine missed.

    `existing` are core extractions (dicts with char_start/char_end); any
    augmenter hit overlapping an existing extraction span is dropped (dedup).
    """
    if not text:
        return []
    text = normalize_text(text)
    existing = existing or []
    spans = [(e.get("char_start", -1), e.get("char_end", -1)) for e in existing]

    def overlaps(s, e):
        return any(not (e <= xs or s >= xe) for xs, xe in spans if xs >= 0)

    out = []
    seen = []

    for m in _EFFICACY_RE.finditer(text):
        val, lo, hi = _f(m["val"]), _f(m["lo"]), _f(m["hi"])
        if val is None or lo is None or hi is None:
            continue
        s, e = m.start(), m.end()
        if overlaps(s, e):
            continue
        out.append(_mk("EFFICACY_PCT", val, lo, hi, text, s, e))
        seen.append((s, e))

    for rx in (_RATIO_RE, _BARE_RATIO_RE, _REVMAN_RE):
        for m in rx.finditer(text):
            etype = _ratio_type(m["label"])
            if not etype:
                continue
            val, lo, hi = _f(m["val"]), _f(m["lo"]), _f(m["hi"])
            if val is None or lo is None or hi is None:
                continue
            # Plausibility: point estimate should sit within (or near) its CI.
            if not (min(lo, hi) - 0.05 <= val <= max(lo, hi) + 0.05):
                continue
            s, e = m.start(), m.end()
            # Bare RR/HR/OR also abbreviate respiratory/heart rate, odds vs a
            # boolean -- reject when the context is a vital sign or the value is
            # outside any plausible ratio range. (P0-2)
            if rx is _BARE_RATIO_RE and etype in _RATIO_CODES:
                ctx = text[max(0, s - 26):min(len(text), e + 16)].lower()
                if _VITAL_CONTEXT.search(ctx) or not (0.01 <= abs(val) <= 50):
                    continue
            if overlaps(s, e) or any(not (e <= ss or s >= ee) for ss, ee in seen):
                continue
            out.append(_mk(etype, val, lo, hi, text, s, e))
            seen.append((s, e))

    return out


def extract_malaria_effects(extractor, text, consistency=True, drop_inconsistent=True):
    """One-call malaria extraction: core engine + malaria augmenter, deduped,
    then screened for internal consistency.

    `extractor` is an EnhancedExtractor instance. Returns a list of effect dicts
    (core + augmenter) in to_dict() shape. This is what student-facing tooling
    should call so malaria-specific formats (efficacy %, bracketed adjusted
    ratios) are captured without touching the core engine.

    When consistency=True, each effect gets a 'consistency' score + 'needs_review'
    flag (Altman-Bland / statcheck / CI-midpoint checks) and reversed CI bounds
    are repaired. drop_inconsistent removes hard failures (point outside its CI,
    non-positive ratio bounds, significance flip vs a reported p) -- almost
    always extraction errors.
    """
    from src.core.enhanced_extractor_v3 import to_dict
    from src.specialties.internal_consistency import annotate
    text = normalize_text(text) if text else text   # fi/fl ligatures -> ascii
    core = [to_dict(x) for x in extractor.extract(text)] if text else []
    merged = core + augment_malaria_effects(text, core)
    merged = [e for e in merged if not _is_vital_sign(e, text)]   # P0-2 (core too)
    if consistency:
        merged = annotate(merged, drop_hard=drop_inconsistent)
    return merged


def _is_vital_sign(effect, text):
    """Drop a ratio-typed extraction that is really a vital sign (respiratory
    rate RR, heart rate HR) -- bare RR/HR collide with effect-measure codes."""
    if effect.get("type") not in _RATIO_CODES:
        return False
    s = effect.get("char_start")
    e = effect.get("char_end")
    if s is None or e is None:
        ctx = effect.get("source_text", "")
    else:
        ctx = text[max(0, s - 26):min(len(text), e + 18)]
    return bool(_VITAL_CONTEXT.search(ctx))
