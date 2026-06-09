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

from .malaria import get_malaria_endpoint_patterns

# Malaria endpoint patterns, used to tag each effect's endpoint so dedup keys on
# endpoint (not just shape) and doesn't merge distinct same-valued estimates.
_ALL_EP = []
for _s in ("treatment", "prevention", "severe", "transmission"):
    _ALL_EP.extend((re.compile(p, re.I), ep) for p, ep in get_malaria_endpoint_patterns(_s))


def _tag_effect_endpoint(text, start, end, window=120):
    lo, hi = max(0, start - window), min(len(text), end + window)
    ctx = text[lo:hi]
    mid = (start + end) // 2 - lo
    best, best_d = None, 10 ** 9
    for rx, ep in _ALL_EP:
        for m in rx.finditer(ctx):
            d = abs(((m.start() + m.end()) // 2) - mid)
            if d < best_d:
                best_d, best = d, ep
    return best


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
    r"\s*(?:\[[^\]]{1,12}\]|\([^)]{1,12}\))?"      # optional [aOR] / (aIRR)
    # stray close-bracket when the LABEL itself was opened in a bracket the core
    # didn't see -- "(weighted mean difference) was 0.74", "(SMD) = 1.4". Optional,
    # so every previously-matched estimate still matches (strict superset).
    r"(?:\s*[\])])?"
    r"(?:s|es)?"                                    # plural: 'relative risks', 'odds ratios'
    # linking phrase the core misses: "<measure> for <subgroup> was/were <val>",
    # bounded and digit/clause-free so it can't reach across to a distant number.
    r"(?:\s*[^\d;:=()\[\]]{0,30}?\b(?:was|were|of)\b)?"
    r"\s*[:=,]?\s*"
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
# The separator also accepts a lower-case spelled-out linking phrase between the
# abbreviation and its value -- "was" / "of" / "for <subgroup> of" ("the OR was
# 3.35 (95% CI 2.23-5.03)", "pooled OR of 1.015 (95% CI ...)", "HR for OS of 1.04
# (95% CI ...)"). This is the UNION of the tuberculosis (was/of) and hepatitis
# (for <subgroup> of) linker extensions: a STRICT SUPERSET of the original
# [\s:=,]+ alternative, kept first so every previously-matched estimate still
# matches. Linkers stay lower-case so "OR" the word / "For" at a sentence start
# can't supply one. (Same linking-phrase class as the typhoid was/were/of fix in
# _RATIO_RE; surfaced mining published TB + hepatitis MAs.)
_BARE_RATIO_RE = re.compile(
    # optional opening + closing bracket AROUND the abbreviation, so the form
    # where the abbreviation is parenthesised and its spelled name sits far away
    # (or is absent) still matches -- "risk (RR) 1.94 (95% CI 1.52 to 2.48)",
    # "[aOR] 0.50; 95% CI 0.34-0.75". Both groups are optional, so the original
    # bare "RR, 0.34 ..." still matches exactly (strict superset).
    r"[\[(]?\s*"
    r"\b(?P<label>aOR|aHR|aRR|aIRR|OR|HR|RR|IRR|RD)"
    r"(?:\s*[\])])?"
    r"(?:[\s:=,]+|\s+was\s+|\s+(?:for\s+[A-Za-z][\w ]{0,18}?\s+)?of\s+)"
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
    # track whether each existing (core) extraction already has a CI; only
    # suppress an augmenter hit that overlaps a CI-BEARING core extraction, so a
    # CI-bearing augmenter match still emits when core got the value but no CI.
    spans = [(e.get("char_start", -1), e.get("char_end", -1),
              e.get("ci_lower") is not None and e.get("ci_upper") is not None)
             for e in existing]

    def overlaps(s, e):
        return any((not (e <= xs or s >= xe)) and has_ci
                   for xs, xe, has_ci in spans if xs >= 0)

    out = []
    seen = []

    for m in _EFFICACY_RE.finditer(text):
        val, lo, hi = _f(m["val"]), _f(m["lo"]), _f(m["hi"])
        if val is None or lo is None or hi is None:
            continue
        # Efficacy is a percentage in [-100, 100] and the point sits in its CI;
        # guard the standalone augmenter path too. (P1)
        if not (-100 <= val <= 100) or not (min(lo, hi) - 0.5 <= val <= max(lo, hi) + 0.5):
            continue
        s, e = m.start(), m.end()
        # Efficacy phrasing "(protective|vaccine) efficacy ... NN% ... 95% CI" is
        # highly specific; emit even when the core mis-typed the same span (it
        # often reads "efficacy of NN% (95% CI ...)" as a mean difference).
        # extract_malaria_effects drops the overlapping core copy so the
        # authoritative EFFICACY_PCT (with its log(1-VE) pooling field) wins.
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


def extract_malaria_effects(extractor, text, consistency=True, drop_inconsistent=True,
                            dedup=True):
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
    norm, omap = _normalize_with_offsets(text) if text else (text, None)
    core = [to_dict(x) for x in extractor.extract(norm)] if norm else []
    merged = core + augment_malaria_effects(norm, core)
    merged = [e for e in merged if not _is_vital_sign(e, norm)]   # P0-2 (core too)
    # EFFICACY_PCT precedence: a (protective|vaccine) efficacy % is authoritative,
    # so drop any non-efficacy core copy covering the same span (the core often
    # mis-types "efficacy of NN% (95% CI ...)" as MD -> wrong pooling scale).
    _eff_spans = [(e.get("char_start", -1), e.get("char_end", -1))
                  for e in merged if e.get("type") == "EFFICACY_PCT"]
    if _eff_spans:
        merged = [e for e in merged if e.get("type") == "EFFICACY_PCT"
                  or not any(not (e.get("char_end", -2) <= s or e.get("char_start", -2) >= en)
                             for s, en in _eff_spans)]
    for e in merged:                                              # tag endpoint
        e["endpoint"] = _tag_effect_endpoint(norm, e.get("char_start", 0), e.get("char_end", 0))
    if dedup:
        merged = _dedup_effects(merged)                           # P1: cross-mention
    _add_log_rr(merged)                                           # log-scale pooling field
    if consistency:
        merged = annotate(merged, drop_hard=drop_inconsistent)
    # translate char offsets from the normalized frame back to the ORIGINAL text
    if omap is not None:
        for e in merged:
            for k in ("char_start", "char_end"):
                p = e.get(k)
                if isinstance(p, int) and 0 <= p < len(omap):
                    e[k] = omap[p]
    return merged


_LIG_LENS = {lig: len(rep) for lig, rep in _LIGATURES.items()}


def _normalize_with_offsets(text):
    """normalize_text() but also return omap: omap[i] = index in the ORIGINAL
    text of normalized-char i (so returned char_start/char_end can be mapped
    back to the input even though ligature expansion changes length)."""
    if not any(lig in text for lig in _LIGATURES):
        return text, list(range(len(text) + 1))
    out, omap = [], []
    for i, ch in enumerate(text):
        rep = _LIGATURES.get(ch)
        if rep:
            for c in rep:
                out.append(c); omap.append(i)
        else:
            out.append(ch); omap.append(i)
    omap.append(len(text))
    return "".join(out), omap


def _add_log_rr(effects):
    """For EFFICACY_PCT / RRR, attach the log-RR field they must be POOLED on:
    log_rr = ln(1 - VE/100). Pooling these on the raw % scale is wrong. (stats review)"""
    import math

    def lr(x):
        if x is None or x >= 100:
            return None
        v = 1.0 - x / 100.0
        return round(math.log(v), 6) if v > 0 else None

    for e in effects:
        if e.get("type") in ("EFFICACY_PCT", "RRR"):
            e["log_rr"] = lr(e.get("effect_size"))
            e["log_rr_lower"] = lr(e.get("ci_upper"))   # CI flips on 1-VE
            e["log_rr_upper"] = lr(e.get("ci_lower"))
            e["pooling_note"] = "pool on log(1-VE/100) scale, not raw %"
    return effects


def _round(x):
    return round(x, 3) if isinstance(x, (int, float)) else None


def _dedup_effects(effects):
    """Collapse the same effect reported more than once in one document (abstract
    + results + forest-plot row) -- otherwise one trial enters a pool 2-3x,
    inflating its weight. Keys on ENDPOINT too (so an identical ratio for two
    different outcomes is NOT merged) -- the review's false-merge concern. (P1)"""
    # key on (type, endpoint, value) WITHOUT the CI, and prefer the CI-bearing
    # copy -- so core's value-only extraction is replaced by the augmenter's
    # value+CI one for the same effect (instead of keeping both / the CI-less one).
    by_key = {}
    order = []
    for e in effects:
        key = (e.get("type"), e.get("endpoint"), _round(e.get("effect_size")))
        has_ci = e.get("ci_lower") is not None and e.get("ci_upper") is not None
        if key not in by_key:
            by_key[key] = e
            order.append(key)
        else:
            kept = by_key[key]
            kept_ci = kept.get("ci_lower") is not None and kept.get("ci_upper") is not None
            if has_ci and not kept_ci:
                by_key[key] = e   # upgrade to the CI-bearing copy
    return [by_key[k] for k in order]


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
