"""
provenance — the source-stratum tag + the abstract-discipline wall.

Every extracted value carries a provenance class so its trust level is visible and so
abstract-sourced numbers can be measured against registry/full-text for the same trial.
Four strata, by descending structure:
    registry  — CT.gov results 2x2/analysis (structured field-read; no spin)
    jats_xml  — Europe PMC OA table cells (structured markup)
    abstract  — free for EVERY paper, 100% coverage, but the MOST spin-prone layer
    pdf       — layout thrown away; the hard case

THE ABSTRACT DISCIPLINE (Boutron: 38-58% of abstracts contain spin): spin lives in the
INTERPRETATION, not the INTEGERS. "n/N virally suppressed" is a count; "well tolerated and
highly effective" is spin. So from an abstract we accept COUNTS and effect estimates that
carry their own CI (verifiable numbers), and we REFUSE a bare directional/interpretive claim
(no number, or a prose effect direction with no CI). Fail closed: unverifiable -> flagged,
never guessed. Registry/JATS/PDF-table numbers are structural and not spin-gated the same way.
"""
import re

STRATA = ("registry", "jats_xml", "abstract", "pdf")
_SPIN_TERMS = ("well tolerated", "highly effective", "safe and effective", "promising",
               "favourable", "favorable", "excellent", "marked improvement", "substantial benefit",
               "clinically meaningful", "encouraging", "superior efficacy", "remarkable")
_STRUCT_CONF = {"registry": 0.99, "jats_xml": 0.9, "abstract": 0.75, "pdf": 0.6}


def is_count(value):
    """A verifiable count = integer events within an integer total (a 2x2 cell)."""
    e, n = value.get("events"), value.get("total")
    return (isinstance(e, int) and isinstance(n, int) and 0 <= e <= n and n > 0)

def is_effect_with_ci(value):
    v = value.get("param_value", value.get("value"))
    lo, hi = value.get("ci_lower_limit", value.get("ci_lower")), value.get("ci_upper_limit", value.get("ci_upper"))
    return (v is not None and lo is not None and hi is not None)


def tag(value, stratum, source_text=""):
    """Attach a provenance block; fail closed on unverifiable abstract-sourced values.

    Returns the value dict with `provenance` = {stratum, verifiable, spin_risk, confidence,
    reason, flagged}. For an abstract, a value is accepted only if it is a COUNT or an
    effect-with-CI (an integer, not an interpretation); otherwise flagged=True.
    """
    if stratum not in STRATA:
        raise ValueError(f"unknown stratum {stratum!r}")
    verifiable = is_count(value) or is_effect_with_ci(value)
    spin = bool(source_text) and any(t in source_text.lower() for t in _SPIN_TERMS)
    flagged = False
    reason = "ok"
    if stratum == "abstract":
        # counts-only discipline: refuse a bare directional/interpretive claim
        if not verifiable:
            flagged = True; reason = "abstract-unverifiable (no count / no CI) -> FLAG, not guessed"
        elif spin:
            # a number sitting next to spin language: keep the number, flag the context
            reason = "abstract-count beside spin language (kept number, flagged context)"
    conf = _STRUCT_CONF[stratum]
    if flagged:
        conf = 0.0
    value = dict(value)
    value["provenance"] = {"stratum": stratum, "verifiable": verifiable, "spin_risk": spin,
                           "confidence": conf, "reason": reason, "flagged": flagged}
    return value


def disagreement(value_a, value_b, rel_tol=0.10):
    """Cross-source check for the SAME trial+outcome (e.g. abstract vs registry 2x2).
    Returns (agree, rel_diff). Disagreement is the registered-vs-published question in
    miniature — a finding, not noise."""
    a = value_a.get("param_value", value_a.get("value"))
    b = value_b.get("param_value", value_b.get("value"))
    if a is None or b is None or b == 0:
        # try counts
        if is_count(value_a) and is_count(value_b):
            a = value_a["events"] / value_a["total"]; b = value_b["events"] / value_b["total"]
        else:
            return None, None
    rd = abs(a - b) / abs(b) if b else None
    return (rd is not None and rd <= rel_tol), rd
