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

import math
import re
from collections import Counter
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
        # Prefer the effect's OWN anchored position (char_start, emitted by the
        # extractor) over scanning for the first place its value MAGNITUDE happens
        # to appear. The magnitude scan collides with unrelated early numbers
        # (doses, years, baseline means, CI bounds) and returns -1 for computed /
        # rounded MD/SMD/ARD whose value is not verbatim in the text -- which then
        # sinks a genuine continuous PRIMARY below any verbatim ratio. Fall back to
        # the magnitude scan only when char_start is absent (e.g. synthetic effects).
        cs = e.get("char_start")
        if isinstance(cs, int) and not isinstance(cs, bool) and cs >= 0:
            idx = cs
        else:
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


def denominator_consistency(effects) -> List[str]:
    """Flag arm sample sizes that DISAGREE across outcomes of the same trial.

    In one RCT the randomised arm Ns are fixed, so every outcome that reports an
    arm N should reuse the same denominators (ITT) -- a different N on one
    outcome is usually a misread (e.g. an evaluable-subset N grabbed as the arm
    N, or a digit error). We treat the MODAL N per arm as truth and flag the
    minority values. Tolerance allows small mITT/per-protocol trims.

    Source idea: cross-outcome denominator-reuse gap noted in the repo survey
    (no existing implementation); generalises DossierGap's field-conflict ledger
    to within-trial arm Ns. Soft / advisory -- returns the list of flagged
    indices' codes via the effect dicts (mutation done by the caller).
    Returns the modal (n_tx, n_ctrl) for reference, or empty list if <2 effects
    carry arm Ns.
    """
    nt_vals = [e.get("n_tx") for e in effects if isinstance(e.get("n_tx"), (int, float)) and e.get("n_tx", 0) > 0]
    nc_vals = [e.get("n_ctrl") for e in effects if isinstance(e.get("n_ctrl"), (int, float)) and e.get("n_ctrl", 0) > 0]
    flagged = []
    for arm, vals in (("n_tx", nt_vals), ("n_ctrl", nc_vals)):
        if len(vals) < 2:
            continue
        modal = Counter(round(v) for v in vals).most_common(1)[0][0]
        if modal <= 0:
            continue
        for e in effects:
            v = e.get(arm)
            if isinstance(v, (int, float)) and v > 0:
                # >5% deviation from the trial's modal arm N -> denominator drift
                if abs(v - modal) > 0.05 * modal and abs(v - modal) > 1:
                    if "denominator_inconsistency" not in e.setdefault(
                            "_xtrial_flags", []):
                        e["_xtrial_flags"].append("denominator_inconsistency")
                    flagged.append("denominator_inconsistency")
    return flagged


def terminal_digit_uniform(values, min_n: int = 30, alpha: float = 0.001) -> Optional[bool]:
    """Chi-square uniformity test on the LAST digit of a set of integer counts.

    Genuine event/sample counts have ~uniform terminal digits; a strong
    non-uniformity (e.g. an excess of 0s and 5s) is a digit-preference /
    rounding / fabrication tell. ADVISORY ONLY -- a real signal needs many
    counts and is never grounds to drop an extraction.

    Source: Terminal Digit Analysis, ported (chi2, df=9) from asa.html tdaCheck
    and AlBurhan forensics. Returns True (uniform/ok), False (anomalous at a
    very strict alpha to avoid FPs), or None (too few values).
    """
    digits = [int(abs(round(v))) % 10 for v in values
              if isinstance(v, (int, float)) and v == v]
    n = len(digits)
    if n < min_n:
        return None
    counts = Counter(digits)
    expected = n / 10.0
    chi2 = sum((counts.get(d, 0) - expected) ** 2 / expected for d in range(10))
    # df=9 chi2 critical at alpha=0.001 is ~27.88; use a strict cutoff so the
    # advisory only fires on blatant non-uniformity (keeps FP rate near zero).
    crit = 27.877 if alpha <= 0.001 else 21.666   # 0.001 / 0.01 critical values
    return chi2 <= crit


def annotate_trial_level(effects):
    """Attach cross-outcome (trial-level) data-quality flags to each effect.

    Runs:
      * denominator_consistency -- arm Ns must match across outcomes (soft);
      * terminal_digit_uniform  -- advisory anomaly over all extracted counts.

    Both are soft/advisory and merged into needs_review + the consistency flag
    list, mirroring annotate_grounding. Never drops or edits values.
    """
    denominator_consistency(effects)
    # Pool every integer count for the terminal-digit advisory.
    pooled = []
    for e in effects:
        for k in ("events_tx", "events_ctrl", "n_tx", "n_ctrl", "n_total"):
            v = e.get(k)
            if isinstance(v, (int, float)) and v == v and v >= 0:
                pooled.append(v)
    td = terminal_digit_uniform(pooled)
    for e in effects:
        xf = e.pop("_xtrial_flags", [])
        if td is False:
            xf = xf + ["terminal_digit_anomaly"]
        if xf:
            e["needs_review"] = True
            c = e.get("consistency")
            if isinstance(c, dict):
                c["flags"] = list(c.get("flags") or []) + xf
            g = e.setdefault("grounding", {"flags": []})
            g["flags"] = list(g.get("flags") or []) + xf
    return effects


# Summary-measure families. A meta-analysis must pool ONE summary measure
# (Cochrane Handbook §10.4); mixing them is invalid. The cardinal error is
# pooling a CONTINUOUS measure (mean difference) with any binary/ratio effect.
_MEASURE_FAMILY = {
    "OR": "binary_ratio", "RR": "binary_ratio", "RISKRATIO": "binary_ratio",
    "ODDSRATIO": "binary_ratio",
    "HR": "time_to_event", "HAZARDRATIO": "time_to_event",
    "IRR": "rate_ratio", "RATERATIO": "rate_ratio",
    "MD": "continuous", "WMD": "continuous", "SMD": "continuous",
    "MEANDIFFERENCE": "continuous", "STANDARDIZEDMEANDIFFERENCE": "continuous",
    "RD": "risk_difference", "ARD": "risk_difference", "RISKDIFFERENCE": "risk_difference",
    "RRR": "percentage", "EFFICACYPCT": "percentage",
    "GMR": "ratio_other",
}


def check_pool_measures(effects) -> List[str]:
    """Validate that a candidate POOL (effects from DIFFERENT studies for the
    SAME outcome) uses ONE summary measure. Returns flags:

      mixed_continuous_and_binary : a continuous measure (MD/SMD) pooled with any
                                    other family -> ALWAYS invalid (Cochrane
                                    §10.4); a mean difference cannot be combined
                                    with an odds/risk/hazard ratio.
      mixed_summary_measure       : >=2 distinct effect families pooled (e.g. HR
                                    with OR) -> different scales, needs review.
      mixed_effect_subtype        : different types within one family (e.g. OR
                                    with RR, or MD with SMD) -> different scales.

    This checks effects intended to be POOLED TOGETHER. A single trial that
    reports MD for one outcome and OR for another is NOT this error (see
    multiple_effect_types in check_grounding) -- those are different outcomes,
    not one pool.
    """
    by_family: Dict[str, set] = {}
    for e in effects:
        t = re.sub(r"[^A-Z]", "", str(e.get("type", "")).upper())
        fam = _MEASURE_FAMILY.get(t)
        if fam:
            by_family.setdefault(fam, set()).add(t)
    families = set(by_family)
    if "continuous" in families and len(families) > 1:
        return ["mixed_continuous_and_binary"]
    if len(families) > 1:
        return ["mixed_summary_measure"]
    if len(families) == 1:
        only = next(iter(families))
        if len(by_family[only]) > 1:
            return ["mixed_effect_subtype"]
    return []


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
