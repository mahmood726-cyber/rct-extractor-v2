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

_ALL_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "prevention", "severe", "transmission"):
    _ALL_ENDPOINT_PATTERNS.extend(get_malaria_endpoint_patterns(_sub))

# Trial-arm labels = antimalarial drug / intervention names.
_ARM_PATTERNS = [
    (r"artemether[- ]?lumefantrine|coartem|\bAL\b", "artemether-lumefantrine"),
    (r"dihydroartemisinin[- ]?piperaquine|DHA[- ]?PPQ|\bDP\b|\bDHA-?P\b", "dihydroartemisinin-piperaquine"),
    (r"artesunate[- ]?amodiaquine|\bASAQ\b|\bAS[- ]?AQ\b", "artesunate-amodiaquine"),
    (r"artesunate[- ]?mefloquine|\bASMQ\b", "artesunate-mefloquine"),
    (r"artesunate[- ]?pyronaridine|pyronaridine", "artesunate-pyronaridine"),
    (r"sulfadoxine[- ]?pyrimethamine|\bSP\b", "sulfadoxine-pyrimethamine"),
    (r"\bchloroquine\b|\bCQ\b", "chloroquine"),
    (r"\bamodiaquine\b|\bAQ\b", "amodiaquine"),
    (r"\bquinine\b", "quinine"),
    (r"\bartesunate\b", "artesunate"),
    (r"primaquine", "primaquine"),
    (r"\bplacebo\b", "placebo"),
    (r"RTS,?\s?S|AS01", "RTS,S"),
    (r"\bR21\b|Matrix[- ]?M", "R21"),
    (r"\bSMC\b|seasonal malaria chemoprevention", "SMC"),
    (r"control(?:\s+group|\s+arm)?", "control"),
]
_ARM_COMPILED = [(re.compile(p, re.I), name) for p, name in _ARM_PATTERNS]


def _tag(text, start, end, patterns, window):
    lo, hi = max(0, start - window), min(len(text), end + window)
    ctx = text[lo:hi].lower()
    for pat, label in patterns:
        if re.search(pat, ctx) if isinstance(pat, str) else pat.search(ctx):
            return label
    return None


def _tag_endpoint(text, start, end, window=120):
    lo, hi = max(0, start - window), min(len(text), end + window)
    ctx = text[lo:hi].lower()
    for pat, ep in _ALL_ENDPOINT_PATTERNS:
        if re.search(pat, ctx):
            return ep
    return None


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
                "source_text": re.sub(r"\s+", " ", text[max(0, s - 25):e + 5]).strip()[:120],
                "char_start": s, "char_end": e,
            })
            seen_spans.append((s, e))
    return out


def pair_2x2(proportions: List[Dict]) -> List[Dict]:
    """Pair same-endpoint proportions from two different arms into 2x2 tables."""
    by_ep = {}
    for p in proportions:
        by_ep.setdefault(p["endpoint"], []).append(p)
    tables = []
    for ep, props in by_ep.items():
        # distinct arms only; take the first two distinct-armed proportions
        armed = [p for p in props if p["arm"]]
        seen_arms = {}
        for p in armed:
            seen_arms.setdefault(p["arm"], p)
        arms = list(seen_arms.values())
        if len(arms) >= 2:
            a, b = arms[0], arms[1]
            tables.append({
                "endpoint": ep,
                "arm1": {"label": a["arm"], "events": a["events"], "total": a["total"]},
                "arm2": {"label": b["arm"], "events": b["events"], "total": b["total"]},
                "both_consistent": a["pct_consistent"] and b["pct_consistent"],
            })
    return tables


def extract_arm_level(text: str) -> Dict:
    """Convenience: proportions + paired 2x2 tables for a piece of text."""
    props = extract_proportions(text)
    return {"proportions": props, "tables_2x2": pair_2x2(props)}
