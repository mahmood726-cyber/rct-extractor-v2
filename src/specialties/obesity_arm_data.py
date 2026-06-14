"""
Arm-level continuous data extraction for GLP-1/GIP obesity dose-response NMA.

Endpoint: **% change in body weight** vs placebo, per arm, modelled as a
dose-response surface (allmeta MBNMA engine). Unlike the malaria module (binary
2x2 proportions), the obesity outcome is continuous, and the network node is the
(agent, dose) pair -- so this module must recover, per arm:

    { studyId, agent, dose_mg (numeric), n, response_pct (mean % weight change),
      sd, response_var (= sd^2 / n, the engine's responseVar), se, stat
      (LS_MEAN|MEAN), timepoint_weeks, sign_ok, flags, source_text }

Design notes (SPEC.md "Known hard parts"):
  - SIGN: negative = weight LOSS. Stored as reported; a positive value for an
    active arm is flagged (unexpected) rather than silently sign-flipped.
  - DOSE: numeric maintenance dose in mg; titration arms ("escalated to 15 mg")
    take the maintenance/target dose; a negation guard rejects "week 15", "n=15".
  - SD RECOVERY: prefer reported SD; else SD = SE*sqrt(n); else from 95% CI of a
    MEAN: SD = sqrt(n)*(hi-lo)/(2*1.96). If neither n nor a usable dispersion is
    present, response_var is NULLED and the arm is flagged (lessons.md: HR/CI
    same-source rule generalises -- never mix a point estimate with a fabricated
    variance).
  - LS-MEAN vs MEAN: prefer LEAST_SQUARES_MEAN/MMRM when named; record which.
  - This is the PUBLICATION-side extractor (paper/abstract text). AACT-posted
    results are read separately via aact-kit; the two are cross-checked downstream.

Node set is the curated post-2010 list (SPEC): semaglutide, tirzepatide,
retatrutide, orforglipron, survodutide, mazdutide, cagrilintide(/CagriSema),
placebo. Dulaglutide (~2008) is intentionally EXCLUDED and flagged if seen.
"""
import math
import re
from typing import List, Dict, Optional

try:
    from .malaria_effects import normalize_text
except Exception:  # pragma: no cover - allow standalone import in tests
    def normalize_text(t):
        return t

_Z = 1.959963984540054  # 95% normal quantile

# ---- agent (network node) labels -----------------------------------------
# Full names case-insensitive; curated post-2010 set only.
_AGENT_PATTERNS = [
    (r"cagrisema", "cagrisema"),                     # cagrilintide + semaglutide combo
    (r"\bsemaglutide\b|wegovy|ozempic", "semaglutide"),
    (r"\btirzepatide\b|zepbound|mounjaro", "tirzepatide"),
    (r"\bretatrutide\b|ly3437943", "retatrutide"),
    (r"\borforglipron\b|ly3502970", "orforglipron"),
    (r"\bsurvodutide\b|bi\s?456906", "survodutide"),
    (r"\bmazdutide\b|ly3305677|imdugleptin", "mazdutide"),
    (r"\bcagrilintide\b|amycretin", "cagrilintide"),
    (r"\bplacebo\b|matching\s+placebo", "placebo"),
]
_AGENT_COMPILED = [(re.compile(p, re.I), name) for p, name in _AGENT_PATTERNS]
# pre-2010 agents that must NOT enter the post-2010 network (flag if seen)
_EXCLUDED_AGENTS = re.compile(r"\bdulaglutide\b|trulicity|\bliraglutide\b|saxenda|"
                              r"\bexenatide\b|\blixisenatide\b", re.I)

# ---- weight-change endpoint cue -------------------------------------------
_WEIGHT_CUE = re.compile(
    r"(?:body[- ]?weight|weight\s+(?:change|loss|reduction)|change\s+in\s+"
    r"(?:body\s+)?weight|percent(?:age)?\s+weight|weight)\b", re.I)

# ---- dose ------------------------------------------------------------------
# numeric mg dose; allow QW/weekly/daily suffixes; "and"/"/" dose lists handled
# by capturing each. Negation guard rejects week/visit/n=/age contexts.
_DOSE = re.compile(r"(?<![\w.])(?P<dose>\d{1,4}(?:\.\d+)?)\s*(?:mg|milligram)s?\b", re.I)
_DOSE_NEG = re.compile(
    r"\b(?:week|weeks|wk|day|days|visit|dose\s+level|n|age|aged|year|years|"
    r"month|months|baseline\s+bmi|bmi)\s*[=:]?\s*$", re.I)

# ---- timepoint -------------------------------------------------------------
_WEEK = re.compile(r"\b(?:at\s+)?week\s+(?P<wk>\d{1,3})\b|\b(?P<wk2>\d{1,3})\s*weeks?\b", re.I)
_MONTH = re.compile(r"\b(?P<mo>\d{1,3})\s*months?\b", re.I)

# ---- analytic method (LS-mean / MMRM) -------------------------------------
_LSMEAN = re.compile(r"least[- ]squares?\s+mean|ls[- ]?means?\b|\blsm\b|mmrm|"
                     r"mixed[- ]?model|estimated\s+treatment\s+difference", re.I)

# ---- per-arm % weight change with dispersion ------------------------------
_NUM = r"[-+−–]?\d{1,3}(?:\.\d+)?"   # signed; en-dash/minus tolerated
# Dispersion terms WITHOUT their own opening paren -- a single optional "(" is
# allowed by the _PCT assembly so all three forms (±, (SD x), (SE x), (95% CI..))
# are handled uniformly.
_SD_TERM = (r"(?:±|\+/-|SD|s\.d\.|standard\s+deviation)\s*[:=]?\s*"
            r"(?P<sd>\d{1,3}(?:\.\d+)?)")
_SE_TERM = (r"(?:SE|s\.e\.|standard\s+error|SEM)\s*[:=]?\s*"
            r"(?P<se>\d{1,3}(?:\.\d+)?)")
_CI_TERM = (r"95\s*%\s*(?:CI|confidence\s+interval)\s*[:,]?\s*"
            r"(?P<lo>" + _NUM + r")\s*(?:to|,|–|—|-)\s*(?P<hi>" + _NUM + r")")

# A signed percentage near a weight cue, optionally followed by a dispersion term
# (which may be parenthesised: "(SD 6.2)", "± 6.2", "(95% CI -16.1 to -13.9)").
_PCT = re.compile(
    r"(?<![\d.])(?P<val>" + _NUM + r")\s*%"
    r"(?:\s*[\(,]?\s*(?:" + _SD_TERM + r"|" + _SE_TERM + r"|" + _CI_TERM + r")\s*\)?)?",
)
_N_NEAR = re.compile(r"\bn\s*[=:]\s*(?P<n>\d{1,6})", re.I)


def _to_float(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    s = s.replace("−", "-").replace("–", "-").replace("—", "-")
    try:
        return float(s)
    except ValueError:
        return None


def _nearest(text, mid, compiled, window):
    """Nearest label (in either direction) to position `mid`."""
    lo, hi = max(0, mid - window), min(len(text), mid + window)
    region = text[lo:hi]
    rel = mid - lo
    best, best_d = None, 10 ** 9
    for pat, name in compiled:
        for m in pat.finditer(region):
            d = abs(((m.start() + m.end()) // 2) - rel)
            if d < best_d:
                best_d, best = d, name
    return best


def _nearest_dose(text, mid, window=80):
    """Nearest numeric mg dose to `mid`, with a negation guard. Returns float mg
    or None. Among equal-distance candidates the larger (maintenance) dose wins."""
    lo, hi = max(0, mid - window), min(len(text), mid + window)
    region = text[lo:hi]
    rel = mid - lo
    best, best_d = None, 10 ** 9
    for m in _DOSE.finditer(region):
        # reject "week 15", "n=15", "aged 15" etc. immediately before the number
        if _DOSE_NEG.search(region[max(0, m.start() - 14):m.start()]):
            continue
        d = abs(((m.start() + m.end()) // 2) - rel)
        dose = float(m.group("dose"))
        if d < best_d or (d == best_d and best is not None and dose > best):
            best_d, best = d, dose
    return best


def _nearest_timepoint_weeks(text, mid, window=120):
    lo, hi = max(0, mid - window), min(len(text), mid + window)
    region, rel = text[lo:hi], mid - lo
    best, best_d = None, 10 ** 9
    for m in _WEEK.finditer(region):
        wk = m.group("wk") or m.group("wk2")
        d = abs(((m.start() + m.end()) // 2) - rel)
        if wk and d < best_d:
            best_d, best = d, int(wk)
    if best is None:
        for m in _MONTH.finditer(region):
            d = abs(((m.start() + m.end()) // 2) - rel)
            if d < best_d:
                best_d, best = d, round(int(m.group("mo")) * 4.345, 1)  # months->weeks
    return best


def _recover_sd(n, sd, se, lo, hi):
    """Return (sd, response_var, source) recovering SD when only SE/CI present.
    response_var = sd^2 / n (variance of the mean = the engine's responseVar).
    Nulls out when ambiguous (lessons.md: never fabricate a variance)."""
    if sd is not None:
        src = "reported_sd"
    elif se is not None and n:
        sd = se * math.sqrt(n); src = "from_se"
    elif lo is not None and hi is not None and n:
        # CI of a MEAN -> SD = sqrt(n) * (hi-lo) / (2*z)
        sd = math.sqrt(n) * (hi - lo) / (2 * _Z); src = "from_ci"
    else:
        return None, None, "unrecoverable"
    if sd < 0:
        return None, None, "unrecoverable"
    rvar = (sd * sd / n) if n else None
    return round(sd, 4), (round(rvar, 6) if rvar is not None else None), src


def extract_obesity_arms(text: str, study_id: Optional[str] = None) -> List[Dict]:
    """Extract per-arm % weight-change rows for the obesity dose-response network.

    Each row follows the SPEC data contract and carries `flags` + `needs_review`
    so nothing fabricated reaches the engine. Reference (placebo) arms get dose 0.
    """
    if not text:
        return []
    text = normalize_text(text)
    rows: List[Dict] = []
    seen = []
    for m in _PCT.finditer(text):
        s, e = m.start(), m.end()
        if any(not (e <= ss or s >= ee) for ss, ee in seen):
            continue
        mid = (s + e) // 2
        # must sit near a weight-change cue (else it's some other percentage).
        # Window is asymmetric + wider on the left because a comparative sentence
        # states the cue once ("change in body weight was X% with A ... with
        # placebo it was Y%") and the second arm's % trails the cue.
        cue_lo, cue_hi = max(0, s - 160), min(len(text), e + 70)
        if not _WEIGHT_CUE.search(text[cue_lo:cue_hi]):
            continue
        val = _to_float(m.group("val"))
        if val is None or not (-100.0 <= val <= 60.0):   # implausible % change
            continue
        agent = _nearest(text, mid, _AGENT_COMPILED, window=90)
        if agent is None:
            continue                                       # untagged -> skip
        dose = 0.0 if agent == "placebo" else _nearest_dose(text, mid)
        # n often trails the arm: "... -14.9% (SD 6.2) with semaglutide 2.4 mg
        # (n=488)" -> search a wider right window. Prefer the nearest n= to the %.
        nmatch = _N_NEAR.search(text[max(0, s - 70):e + 95])
        n = int(nmatch.group("n")) if nmatch else None
        sd = _to_float(m.group("sd")) if m.groupdict().get("sd") else None
        se = _to_float(m.group("se")) if m.groupdict().get("se") else None
        lo = _to_float(m.group("lo")) if m.groupdict().get("lo") else None
        hi = _to_float(m.group("hi")) if m.groupdict().get("hi") else None
        sd_r, rvar, sd_src = _recover_sd(n, sd, se, lo, hi)
        stat = "LS_MEAN" if _LSMEAN.search(text[cue_lo:cue_hi]) else "MEAN"
        excluded = bool(_EXCLUDED_AGENTS.search(text[max(0, mid - 90):mid + 90]))
        flags = []
        if agent != "placebo" and dose is None:
            flags.append("dose_unresolved")
        if sd_src == "unrecoverable":
            flags.append("variance_unrecoverable")
        if agent != "placebo" and val > 0:
            flags.append("positive_change_for_active_arm")  # expected: loss (neg)
        if excluded:
            flags.append("pre2010_agent_in_context")
        tp = _nearest_timepoint_weeks(text, mid)
        rows.append({
            "study_id": study_id,
            "agent": agent,
            "dose_mg": dose,
            "n": n,
            "response_pct": val,            # negative = weight loss
            "sd": sd_r,
            "se": se,
            "response_var": rvar,           # sd^2 / n  (engine responseVar)
            "sd_source": sd_src,
            "stat": stat,
            "timepoint_weeks": tp,
            "sign_convention": "negative_is_loss",
            "flags": flags,
            "needs_review": bool(flags),
            "source_text": re.sub(r"\s+", " ", text[max(0, s - 40):e + 10]).strip()[:140],
            "char_start": s, "char_end": e,
        })
        seen.append((s, e))
    return rows


def to_engine_rows(arms: List[Dict], drop_review: bool = True) -> List[Dict]:
    """Project extracted arms onto the allmeta dose-response engine schema
    `{dose, response, n, responseVar}` grouped by (study, agent). By default
    drops rows flagged needs_review so nothing unverified reaches the engine."""
    out = []
    for a in arms:
        if drop_review and a["needs_review"]:
            continue
        if a["response_var"] is None or a["n"] is None:
            continue
        out.append({
            "study": a["study_id"], "agent": a["agent"],
            "dose": a["dose_mg"], "response": a["response_pct"],
            "n": a["n"], "responseVar": a["response_var"],
            "timepointWeeks": a["timepoint_weeks"],
        })
    return out


def extract_arm_level_obesity(text: str, study_id: Optional[str] = None) -> Dict:
    """Convenience: all arms + the engine-ready (verified) subset."""
    arms = extract_obesity_arms(text, study_id=study_id)
    return {"arms": arms, "engine_rows": to_engine_rows(arms),
            "n_arms": len(arms), "n_engine_ready": len(to_engine_rows(arms))}
