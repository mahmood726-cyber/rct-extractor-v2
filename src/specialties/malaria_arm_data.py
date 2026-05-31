"""
Arm-level / 2x2 data extraction for malaria binary outcomes.

~Half of malaria RCT papers report no pre-computed ratio+CI -- they report the
raw per-arm data ("ACPR was 121/125 (96.8%)") that meta-analysts pool into a
2x2 table themselves. This module extracts those proportions and pairs them into
2x2 tables, so the same corpus that yields effect estimates also yields poolable
raw data.

Supported per-arm forms (grounded in the malaria corpus):
    n/N (pct%)        "ACPR was 121/125 (96.8%; 95% CI 92.0-99.1)"
    pct% (n/N)        "cure rate was 100% (106/106)" / "93.0% (66/71)"
    n of N (pct%)     "12 of 12 (100%)" / "8 of 150"

Every proportion carries a built-in consistency check: the reported percentage
must match 100*events/total (catches OCR/transcription errors). Each proportion
is tagged with its malaria endpoint (ACPR, treatment failure, ...) and, when
identifiable, its trial arm (drug name). Same-endpoint proportions from two
different arms are paired into a 2x2.
"""
import re
from typing import List, Dict, Optional

from .malaria import get_malaria_endpoint_patterns
from .malaria_effects import normalize_text

# Per-arm proportion patterns. Each yields events (n), total (N), and optional pct.
_PROP_PATTERNS = [
    # n/N (pct%)
    re.compile(r"(?<![\d.])(?P<n>\d{1,6})\s*/\s*(?P<N>\d{1,6})\s*"
               r"\(\s*(?P<pct>\d{1,3}(?:\.\d+)?)\s*%"),
    # pct% (n/N)
    re.compile(r"(?P<pct>\d{1,3}(?:\.\d+)?)\s*%\s*"
               r"\(\s*(?P<n>\d{1,6})\s*/\s*(?P<N>\d{1,6})\s*\)"),
    # n of N (pct%)  -- pct optional
    re.compile(r"(?<![\d.])(?P<n>\d{1,6})\s+of\s+(?P<N>\d{1,6})\b"
               r"(?:\s*\(\s*(?P<pct>\d{1,3}(?:\.\d+)?)\s*%\)?)?"),
]

# PCR-correction status: corrected and uncorrected ACPR/failure have DIFFERENT
# numerators AND denominators (uncorrected counts all recurrences; corrected
# reclassifies reinfections) and must never be pooled together.
_PCR_CORRECTED = re.compile(r"pcr[- ]?(?:corrected|adjusted|confirmed)", re.I)
_PCR_UNCORRECTED = re.compile(r"pcr[- ]?uncorrected|uncorrected|crude", re.I)


def _nearest_status(text, start, end, options, window=90, default="unspecified"):
    """Return the status whose keyword is nearest the proportion (windows may
    contain more than one)."""
    lo, hi = max(0, start - window), min(len(text), end + window)
    region = text[lo:hi]
    mid = (start + end) // 2 - lo
    best, best_d = default, 10 ** 9
    for rx, status in options:
        for m in rx.finditer(region):
            d = abs(((m.start() + m.end()) // 2) - mid)
            if d < best_d:
                best_d, best = d, status
    return best


def _pcr_status(text, start, end):
    return _nearest_status(text, start, end,
                           ((_PCR_CORRECTED, "corrected"), (_PCR_UNCORRECTED, "uncorrected")))


# ITT vs per-protocol: different denominator conventions for the same arm.
_ITT = re.compile(r"\bm?itt\b|intention[- ]to[- ]treat|intent[- ]to[- ]treat", re.I)
_PP = re.compile(r"per[- ]protocol|\bpp\b|evaluable|per\s+protocol", re.I)


def _analysis_population(text, start, end):
    return _nearest_status(text, start, end, ((_ITT, "itt"), (_PP, "pp")))


# Non-event contexts that precede a "<n> of <N>" that is NOT a clinical count.
_NEGATED_CONTEXT = re.compile(
    r"\b(?:page|pages|figure|fig|table|ref|reference|chapter|section|"
    r"appendix|version|step|item|panel|day|days|week|weeks|month|months|"
    r"year|years|age|aged|visit|dose|doses|round|phase|part)\.?\s*$",
    re.I)

_ALL_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "prevention", "severe", "transmission"):
    _ALL_ENDPOINT_PATTERNS.extend(get_malaria_endpoint_patterns(_sub))

# Trial-arm labels. FULL names are matched case-insensitively; bare UPPERCASE
# drug abbreviations are matched CASE-SENSITIVELY (P0-3) so "et al." != AL,
# "the dp" != DP, etc.
_ARM_PATTERNS = [
    (r"artemether[- ]?lumefantrine|coartem", "artemether-lumefantrine"),
    (r"dihydroartemisinin[- ]?piperaquine", "dihydroartemisinin-piperaquine"),
    (r"artesunate[- ]?amodiaquine", "artesunate-amodiaquine"),
    (r"artesunate[- ]?mefloquine", "artesunate-mefloquine"),
    (r"artesunate[- ]?pyronaridine|pyronaridine[- ]?piperaquine|pyronaridine", "artesunate-pyronaridine"),
    (r"sulfadoxine[- ]?pyrimethamine", "sulfadoxine-pyrimethamine"),
    (r"\bchloroquine\b", "chloroquine"),
    (r"\bamodiaquine\b", "amodiaquine"),
    (r"\bquinine\b", "quinine"),
    (r"\btafenoquine\b|krintafel", "tafenoquine"),
    (r"atovaquone[- ]?proguanil|malarone", "atovaquone-proguanil"),
    (r"\bmefloquine\b", "mefloquine"),
    (r"arterolane[- ]?piperaquine|synriam", "arterolane-piperaquine"),
    (r"\bartesunate\b", "artesunate"),
    (r"rectal\s+artesunate|artesunate\s+suppositor", "rectal-artesunate"),
    (r"primaquine", "primaquine"),
    (r"\bplacebo\b", "placebo"),
    (r"seasonal malaria chemoprevention", "SMC"),
    (r"matrix[- ]?m", "R21"),
    # Generic arm labels (lower priority; nearest-distance still wins). Many
    # trials name arms by role, not drug ("intervention group" vs "control").
    (r"intervention\s+(?:group|arm)|interventions?\b", "intervention"),
    (r"treatment\s+(?:group|arm)|treated\s+group", "treatment"),
    (r"experimental\s+(?:group|arm)", "experimental"),
    (r"active\s+(?:treatment|group|arm)", "active"),
    (r"vaccine\s+(?:group|arm|recipients?)", "vaccine"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
    (r"control(?:\s+group|\s+arm)?|usual\s+care|standard\s+care", "control"),
]
# Case-SENSITIVE uppercase abbreviations (no re.I).
_ARM_ABBREV = [
    (r"\bAL\b", "artemether-lumefantrine"),
    (r"\bDHA[- ]?PPQ\b|\bDP\b|\bDHA-?P\b", "dihydroartemisinin-piperaquine"),
    (r"\bASAQ\b|\bAS[- ]?AQ\b", "artesunate-amodiaquine"),
    (r"\bASMQ\b", "artesunate-mefloquine"),
    (r"\bSPAQ\b|\bSP\s*\+?\s*AQ\b", "SP-AQ"),
    (r"\bSP\b", "sulfadoxine-pyrimethamine"),
    (r"\bCQ\b", "chloroquine"),
    (r"\bAQ\b", "amodiaquine"),
    (r"\bMQ\b", "mefloquine"),
    (r"\bTQ\b", "tafenoquine"),
    (r"RTS,?\s?S|AS01", "RTS,S"),
    (r"\bR21\b", "R21"),
    (r"\bSMC\b", "SMC"),
    (r"\bRAS\b", "rectal-artesunate"),
]
_ARM_COMPILED = ([(re.compile(p, re.I), name) for p, name in _ARM_PATTERNS]
                 + [(re.compile(p), name) for p, name in _ARM_ABBREV])


def _tag(text, start, end, patterns, window):
    lo, hi = max(0, start - window), min(len(text), end + window)
    ctx = text[lo:hi].lower()
    for pat, label in patterns:
        if re.search(pat, ctx) if isinstance(pat, str) else pat.search(ctx):
            return label
    return None


def _tag_endpoint(text, start, end, window=120):
    # NEAREST endpoint to the proportion, not first-in-list (P0-1): otherwise
    # "ACPR aside, anaemia in 8 of 150" mislabels the anaemia count as ACPR.
    lo, hi = max(0, start - window), min(len(text), end + window)
    ctx = text[lo:hi].lower()
    prop_mid = (start + end) // 2 - lo
    best, best_dist = None, 10 ** 9
    for pat, ep in _ALL_ENDPOINT_PATTERNS:
        for m in re.finditer(pat, ctx):
            d = abs(((m.start() + m.end()) // 2) - prop_mid)
            if d < best_dist:
                best_dist, best = d, ep
    return best


def _tag_arm(text, start, end, window=70):
    # nearest arm label in EITHER direction (drug names may precede or follow the
    # proportion: "AL group 121/125" vs "8 of 150 chloroquine recipients").
    lo, hi = max(0, start - window), min(len(text), end + window)
    region = text[lo:hi]
    prop_mid = (start + end) // 2 - lo
    best, best_dist = None, 10 ** 9
    for pat, name in _ARM_COMPILED:
        for m in pat.finditer(region):
            d = abs(((m.start() + m.end()) // 2) - prop_mid)
            if d < best_dist:
                best_dist, best = d, name
    return best


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    """Extract per-arm binary proportions with a built-in consistency check.

    pct_tol: max absolute difference (percentage points) between the reported
    percentage and 100*events/total before the proportion is flagged inconsistent.
    """
    if not text:
        return []
    text = normalize_text(text)
    out = []
    seen_spans = []
    for rx in _PROP_PATTERNS:
        for m in rx.finditer(text):
            n = int(m.group("n"))
            N = int(m.group("N"))
            if N <= 1 or n > N:           # implausible proportion
                continue
            s, e = m.start(), m.end()
            # Reject "page 8 of 150", "figure 2 of 5", "day 8 of 14" etc. (P0-4):
            # a count-of-total preceded by a non-event context word is not a
            # clinical proportion. (lessons.md negated-counts rule.)
            if _NEGATED_CONTEXT.search(text[max(0, s - 22):s]):
                continue
            if any(not (e <= ss or s >= ee) for ss, ee in seen_spans):
                continue
            computed = 100.0 * n / N
            pct = float(m.group("pct")) if m.groupdict().get("pct") else round(computed, 1)
            consistent = abs(pct - computed) <= pct_tol
            ep = _tag_endpoint(text, s, e)
            if ep is None:               # only keep proportions tied to a malaria endpoint
                continue
            out.append({
                "events": n, "total": N, "pct": pct,
                "computed_pct": round(computed, 2),
                "pct_consistent": consistent,
                "endpoint": ep,
                "arm": _tag_arm(text, s, e),
                "pcr_status": _pcr_status(text, s, e),
                "analysis_population": _analysis_population(text, s, e),
                "source_text": re.sub(r"\s+", " ", text[max(0, s - 25):e + 5]).strip()[:120],
                "char_start": s, "char_end": e,
            })
            seen_spans.append((s, e))
    return out


def pair_2x2(proportions: List[Dict], max_gap: int = 260) -> List[Dict]:
    """Pair same-endpoint proportions into 2x2 tables -- but only when the two
    proportions sit in the SAME comparative statement (within max_gap chars).

    Pairing across the whole document grabs unrelated table cells; requiring
    proximity targets real "X (n1/N1) vs Y (n2/N2)" comparisons. A 2x2 is flagged
    needs_review when an arm label is missing/generic or the % is inconsistent.
    """
    _GENERIC = {"intervention", "treatment", "control", "active", "experimental",
                "vaccine", "group_1", "group_2", None}
    by_ep = {}
    for p in proportions:
        by_ep.setdefault(p["endpoint"], []).append(p)

    tables = []
    for ep, props in by_ep.items():
        # drop identical (events,total) duplicates
        deduped, seen_counts = [], set()
        for p in sorted(props, key=lambda x: x.get("char_start", 0)):
            key = (p["events"], p["total"])
            if key not in seen_counts:
                seen_counts.add(key)
                deduped.append(p)
        # ≥3 distinct arms for this endpoint -> multi-arm trial; naive pairwise
        # pooling double-counts a shared control, so flag every pair. (P1)
        distinct_arms = {p["arm"] for p in deduped if p["arm"]}
        multi_arm = len(distinct_arms) >= 3
        used = set()
        for i in range(len(deduped)):
            if i in used:
                continue
            a = deduped[i]
            for j in range(i + 1, len(deduped)):
                if j in used:
                    continue
                b = deduped[j]
                gap = abs(b.get("char_start", 0) - a.get("char_start", 0))
                if gap > max_gap:
                    break  # sorted -> no closer candidate further on
                if a["total"] == b["total"] and a["events"] == b["events"]:
                    continue
                if a["arm"] and b["arm"] and a["arm"] == b["arm"]:
                    continue  # same named arm -> not a between-arm pair
                # NEVER pair PCR-corrected with PCR-uncorrected (P0-7): different
                # numerator AND denominator conventions -> meaningless ratio.
                sa, sb = a.get("pcr_status", "unspecified"), b.get("pcr_status", "unspecified")
                if {sa, sb} == {"corrected", "uncorrected"}:
                    continue
                pop_mismatch = (a.get("analysis_population", "unspecified") != "unspecified"
                                and b.get("analysis_population", "unspecified") != "unspecified"
                                and a["analysis_population"] != b["analysis_population"])
                review = (a["arm"] in _GENERIC or b["arm"] in _GENERIC
                          or not a["pct_consistent"] or not b["pct_consistent"]
                          or multi_arm or pop_mismatch)
                tables.append({
                    "endpoint": ep,
                    "pcr_status": sa if sa == sb else (sa if sb == "unspecified" else sb),
                    "analysis_population": a.get("analysis_population", "unspecified"),
                    "arm1": {"label": a["arm"] or "arm_1", "events": a["events"], "total": a["total"]},
                    "arm2": {"label": b["arm"] or "arm_2", "events": b["events"], "total": b["total"]},
                    "both_consistent": a["pct_consistent"] and b["pct_consistent"],
                    "needs_review": review,
                    "multi_arm": multi_arm,
                    "population_mismatch": pop_mismatch,
                    "char_gap": gap,
                })
                used.add(i)
                used.add(j)
                break
    return tables


# ---- Continuous per-arm data (mean+SD / median+IQR) ----
_NUM_C = r"[-+]?\d+(?:[.·]\d+)?"
# Continuous malaria outcomes (the rest are binary proportions).
_CONTINUOUS_ENDPOINTS = {
    "PARASITE_CLEARANCE_TIME", "FEVER_CLEARANCE_TIME", "HAEMOGLOBIN",
    "PARASITAEMIA", "PARASITE_REDUCTION_RATIO",
}
_MEAN_SD = re.compile(
    r"(?:mean\s+(?:of\s+)?)?(?P<mean>" + _NUM_C + r")\s*"
    r"(?:±|\+/-|\(\s*(?:SD|s\.d\.|standard\s+deviation)\s*[:=]?\s*)\s*"
    r"(?P<sd>" + _NUM_C + r")\)?", re.I)
_MEDIAN_IQR = re.compile(
    r"median\b[^\d\n]{0,45}?(?P<median>" + _NUM_C + r")\s*[^\d\n]{0,8}?"
    r"\(\s*(?:IQR|interquartile\s+range|range)\s*[:=]?\s*"
    r"(?P<lo>" + _NUM_C + r")\s*(?:–|—|-|to|,)\s*(?P<hi>" + _NUM_C + r")\s*\)", re.I)
_N_NEAR = re.compile(r"\bn\s*[=:]\s*(\d{1,6})", re.I)


def _fc(s):
    try:
        return float(s.replace("·", "."))
    except (ValueError, AttributeError):
        return None


def extract_continuous(text: str) -> List[Dict]:
    """Per-arm continuous data (mean+SD poolable; median+IQR flagged as needing
    transformation) for continuous malaria outcomes. Tagged with endpoint + arm."""
    if not text:
        return []
    text = normalize_text(text)
    out, spans = [], []

    def _emit(ep, arm, s, e, **kw):
        spans.append((s, e))
        nm = _N_NEAR.search(text[max(0, s - 40):e + 25])
        out.append({"endpoint": ep, "arm": arm, "n": int(nm.group(1)) if nm else None,
                    "char_start": s, "char_end": e,
                    "source_text": re.sub(r"\s+", " ", text[max(0, s - 20):e + 5]).strip()[:120],
                    **kw})

    for m in _MEDIAN_IQR.finditer(text):
        s, e = m.start(), m.end()
        ep = _tag_endpoint(text, s, e)
        if ep not in _CONTINUOUS_ENDPOINTS:
            continue
        out_med, lo, hi = _fc(m["median"]), _fc(m["lo"]), _fc(m["hi"])
        if None in (out_med, lo, hi):
            continue
        _emit(ep, _tag_arm(text, s, e), s, e, stat="median_iqr",
              median=out_med, iqr_lower=lo, iqr_upper=hi, poolable=False)

    for m in _MEAN_SD.finditer(text):
        s, e = m.start(), m.end()
        if any(not (e <= ss or s >= ee) for ss, ee in spans):
            continue
        ep = _tag_endpoint(text, s, e)
        if ep not in _CONTINUOUS_ENDPOINTS:
            continue
        mean, sd = _fc(m["mean"]), _fc(m["sd"])
        if mean is None or sd is None or sd < 0:
            continue
        _emit(ep, _tag_arm(text, s, e), s, e, stat="mean_sd",
              mean=mean, sd=sd, poolable=True)
    return out


def poolable_ready(tables):
    """Return only 2x2 tables safe to pool WITHOUT human verification: both arms
    drug-named (not generic), consistent percentages, and not flagged for review
    (so multi-arm / population-mismatch / PCR issues are excluded). (P2)"""
    return [t for t in tables if not t.get("needs_review")
            and t.get("both_consistent")]


def extract_arm_level(text: str) -> Dict:
    """Convenience: proportions + paired 2x2 tables for a piece of text.

    `tables_2x2` is ALL paired tables (verify arm labels before pooling);
    `poolable_2x2` is the high-confidence subset safe to pool as-is.
    """
    props = extract_proportions(text)
    tables = pair_2x2(props)
    return {"proportions": props, "tables_2x2": tables,
            "poolable_2x2": poolable_ready(tables),
            "continuous": extract_continuous(text)}
