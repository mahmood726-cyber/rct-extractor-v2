"""
select_primary_effect — general primary-outcome / population / scope ranker.

Fixes the mis-grabbed-HR bug class (CANVAS renal 0.60 vs MACE 0.86; SAVOR
on-treatment 1.03 vs ITT 1.00): the deterministic extractors did POSITIONAL
first-match selection (registry: primaries[0]/analyses[0]; abstract: first
regex hit) with NO ranking by outcome primacy, analysis population, or scope.

The number was parsed correctly; the wrong ROW was chosen. This module ranks
candidate effect rows so the pre-specified PRIMARY, ITT/full-analysis-set,
OVERALL (non-subgroup, non-single-dose) between-group effect wins, and emits an
`ambiguous` flag + runner-up when the margin is small so verification gets the
contested field instead of a silent pick.

Pure function; no I/O. A "candidate" is a dict with keys:
  outcome_type  : 'PRIMARY'|'SECONDARY'|'OTHER_PRE_SPECIFIED'|'POST_HOC' (any case)
  title         : outcome measure title
  population     : outcome.population text (analysis-set description) or ''
  param_type    : e.g. 'Hazard Ratio (HR)'
  param_value / ci_lower_limit / ci_upper_limit : floats or None
  groups_description / estimate_description : analysis prose or ''
"""
import re

# --- vocabularies (lowercased substring match) ---
_ITT = ("intent-to-treat", "intention-to-treat", "intent to treat", "intention to treat",
        " itt ", "(itt)", "full analysis set", "full-analysis", " fas ", "(fas)",
        "all randomi", "all-randomi", "analyzed as randomi", "analysed as randomi",
        "as randomized", "as randomised", "randomized set", "randomised set", "regardless of")
# Specific off-primary-population phrases ONLY. Bare "on treatment" is excluded because
# ITT descriptions say "...analyzed regardless of whether still on treatment"; mITT is
# EXCLUDED because it is frequently the pre-specified primary analysis set. An ITT marker
# in the text overrides these (see score_candidate).
_OFF_POP = ("per-protocol", "per protocol set", "per protocol population", "per protocol analysis",
            "on-treatment analysis", "on treatment analysis", "on-treatment set", "on-treatment population",
            "as-treated", "as treated analysis", "completers", "completer analysis",
            "evaluable population", "evaluable set", "evaluable participants", "evaluable patients",
            "safety analysis set", "safety set", "safety population",
            "sensitivity analysis", "post-hoc analysis", "post hoc analysis")
# Genuine subgroup markers ONLY. Deliberately EXCLUDES "stratified by"/"stratum"/"strata"
# (a primary analysis stratified by the randomization factor IS the overall ITT analysis,
# not a subgroup) and the over-generic "only"/"cohort " (matched legitimate prose).
_SUBGROUP = ("subgroup", "sub-group", "sub group", "subpopulation", "sub-population",
             "pd-l1", "biomarker-positive", "biomarker positive", "mutation-positive",
             "mutation positive", " brca", "by baseline", "in the subgroup",
             "restricted to patients", "restricted to the", "post-hoc subgroup")
_DOSE = ("dose", "mg ", " mg", "low-dose", "high-dose", "50 mg", "100 mg", "300 mg")
_OVERALL = ("combined", "pooled", "overall", "total", "both doses", "all doses",
            "integrated", "primary analysis")
_PROPER_EFFECT = ("hazard ratio", "odds ratio", "risk ratio", "relative risk",
                   "rate ratio", "mean difference", "hr", "or", "rr")


def _has(text, vocab):
    t = (text or "").lower()
    return any(v in t for v in vocab)


def score_candidate(c, protocol_primary_titles=None):
    """Higher = more likely the correct primary-ITT-overall effect. Returns (score, reasons)."""
    s = 0.0
    reasons = []
    otype = (c.get("outcome_type") or "").upper()
    title = c.get("title") or ""
    pop = " ".join([str(c.get("population") or ""), str(c.get("groups_description") or ""),
                    str(c.get("estimate_description") or "")])

    # 1) Outcome primacy (dominant signal)
    if otype == "PRIMARY":
        s += 100; reasons.append("primary")
    elif otype == "OTHER_PRE_SPECIFIED":
        s += 20; reasons.append("other-prespecified")
    elif otype == "SECONDARY":
        s += 0; reasons.append("secondary")
    elif otype == "POST_HOC":
        s -= 60; reasons.append("post-hoc(-)")

    # 1b) Protocol-declared primary endpoint match (independent confirmation of primacy)
    if protocol_primary_titles:
        if _title_matches_any(title, protocol_primary_titles):
            s += 40; reasons.append("protocol-primary-match")
        else:
            s -= 10; reasons.append("no-protocol-match(-)")

    # 2) Analysis population: ITT/FAS up, off-ITT down. A strong ITT marker OVERRIDES the
    # off-ITT penalty ("analyzed as randomized regardless of whether still on treatment" is ITT).
    itt = _has(pop, _ITT)
    if itt:
        s += 30; reasons.append("ITT")
    if (_has(pop, _OFF_POP) or _has(title, _OFF_POP)) and not itt:
        s -= 45; reasons.append("off-ITT(-)")

    # 3) Scope: overall up, subgroup / single-dose down
    if _has(title, _SUBGROUP) or _has(pop, _SUBGROUP):
        s -= 50; reasons.append("subgroup(-)")
    # "overall/combined/pooled" is a POPULATION-scope signal — read it only from the
    # analysis-population text, NEVER the outcome title ("Overall Survival" is an outcome
    # NAME, not an overall-population flag; matching it there mis-ranks OS above the true
    # primary among co-primaries).
    if _has(pop, _OVERALL):
        s += 15; reasons.append("overall")
    # single-dose sub-analysis (e.g. CANVAS 0.93 dose-1) unless explicitly combined/overall
    if _has(pop, _DOSE) and not _has(pop, _OVERALL) and not _has(title, _OVERALL):
        s -= 12; reasons.append("dose-arm(-)")

    # 4) Completeness of the effect (proper between-group ratio with a CI)
    pt = (c.get("param_type") or "").lower()
    if any(e in pt for e in _PROPER_EFFECT):
        s += 8; reasons.append("effect-type")
    if c.get("ci_lower_limit") is not None and c.get("ci_upper_limit") is not None \
            and c.get("param_value") is not None:
        s += 8; reasons.append("has-CI")
    else:
        s -= 20; reasons.append("no-CI(-)")

    return s, reasons


def _norm(t):
    return re.sub(r"[^a-z0-9 ]", " ", (t or "").lower())


def _title_matches_any(title, protos):
    tn = set(_norm(title).split())
    for p in protos:
        pn = set(_norm(p).split()) - {"the", "of", "in", "to", "a", "and", "or", "with",
                                       "from", "at", "for", "change", "time", "rate",
                                       "number", "percentage", "participants", "patients"}
        if pn and len(tn & pn) / max(1, len(pn)) >= 0.5:
            return True
    return False


def select_primary_effect(candidates, protocol_primary_titles=None, margin=25.0):
    """Rank candidates; return the top pick with an ambiguity flag.

    Returns dict: {pick, score, reasons, ambiguous, runner_up, n_candidates}.
    `pick` is None if candidates is empty. `ambiguous` is True when the top two
    scores are within `margin` (verification should adjudicate the contested field).
    """
    if not candidates:
        return {"pick": None, "score": None, "reasons": [], "ambiguous": False,
                "runner_up": None, "n_candidates": 0}
    # Score, keeping ORIGINAL index. Sort by score desc, then original index asc so that
    # among structurally-equal rows (legitimate co-primaries / equal-rank dose arms) the
    # SOURCE ORDER wins — on primary-first registry data that returns the principal row,
    # and it never re-orders two equally-valid co-primaries. The finer bonuses only break
    # ties INSIDE the same tier; a within-`margin` gap is reported as ambiguous, not silently
    # resolved, so verification adjudicates the contested field.
    scored = sorted(
        ([score_candidate(c, protocol_primary_titles), i, c]
         for i, c in enumerate(candidates)),
        key=lambda x: (-x[0][0], x[1]))
    (top_score, top_reasons), _, top = scored[0]
    runner = scored[1] if len(scored) > 1 else None
    ambiguous = bool(runner and (top_score - runner[0][0]) < margin)
    return {
        "pick": top, "score": top_score, "reasons": top_reasons,
        "ambiguous": ambiguous,
        "runner_up": (runner[1] if runner else None),
        "runner_up_score": (runner[0][0] if runner else None),
        "n_candidates": len(candidates),
    }


def first_row(candidates):
    """Rung-0 baseline: positional first match (reproduces analyses[0]/first-regex)."""
    return candidates[0] if candidates else None
