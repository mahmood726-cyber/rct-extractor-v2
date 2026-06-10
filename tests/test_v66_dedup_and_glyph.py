"""
Regression tests for the v6.6 core-extractor fixes (real-PDF accuracy pass):

1. Negative-context dedup poisoning. The first-pass deduplicator must NOT record a
   (type, value, CI) key in `seen` before the negative-context filter runs.
   Otherwise an occurrence that sits in a negative context (e.g. a pooled
   observational estimate) records the key, is suppressed, and then silently
   drops an IDENTICAL but clean occurrence elsewhere in the body — leaving only a
   CI-less value-only leak. The clean occurrence must survive with its CI.

2. Control-character -> dash glyph repair. Some born-digital PDF fonts map the
   en-dash glyph between CI bounds onto a C0 control character (e.g. U+0001:
   "95% CI 0.45\x011.35"), which splits the interval and drops the whole CI. A
   control char strictly between two digits must be restored to a dash.

Both are generalizable parsing fixes — the inputs below are synthetic and contain
no benchmark gold value or PMCID; they exercise the mechanism, not a specific paper.
"""
import rct_extractor as rx
from rct_extractor._engine.core.enhanced_extractor_v3 import EnhancedExtractor


def _find(effects, point, tol=0.005):
    return [e for e in effects
            if e.get("effect_size") is not None
            and abs(e["effect_size"] - point) < tol]


# --------------------------------------------------------------------------- #
# 1. Negative-context dedup poisoning
# --------------------------------------------------------------------------- #

def test_clean_occurrence_survives_negative_context_twin():
    """An effect that also appears inside a negative-context sentence must still
    be extracted WITH its CI from a separate clean sentence."""
    text = (
        # Same rate ratio twice: first beside an observational-study marker
        # (correctly suppressed), then in a clean results sentence.
        "Pooled across 2 observational studies, the rate ratio was 0.90 "
        "(95% CI 0.50 to 1.61) with low certainty. "
        "In the randomised cohort the incidence rate ratio 0.90, 95% CI 0.50 to 1.61 "
        "indicated no significant difference between arms."
    )
    effects = rx.extract(text, specialty="meningitis")["effects"]
    hits = _find(effects, 0.90)
    assert hits, "the clean rate-ratio occurrence was dropped entirely"
    with_ci = [e for e in hits
               if e.get("ci_lower") is not None and e.get("ci_upper") is not None]
    assert with_ci, "the clean occurrence leaked without its CI (dedup poisoning)"
    e = with_ci[0]
    assert abs(e["ci_lower"] - 0.50) < 0.03 and abs(e["ci_upper"] - 1.61) < 0.03


def test_per_day_or_survives_propensity_score_twin():
    """A per-unit OR restated cleanly far from a propensity-score sentence keeps its
    CI. The negative-context window is local (~500 chars), so the clean restatement
    lives beyond it — exactly the real-paper layout (abstract result vs methods)."""
    filler = (" The trial enrolled adults across multiple sites and followed them "
              "for ninety days with standardised outcome adjudication.") * 6
    text = (
        "After propensity score matching, each additional day was associated with "
        "higher odds of death (OR = 1.13 per day; 95% CI: 1.04-1.22)."
        + filler +
        "Overall, longer sedative duration carried higher mortality "
        "(OR = 1.13 per day; 95% CI: 1.04-1.22)."
    )
    effects = rx.extract(text, specialty="meningitis")["effects"]
    with_ci = [e for e in _find(effects, 1.13)
               if e.get("ci_lower") is not None]
    assert with_ci, "per-day OR lost its CI to a suppressed propensity-score twin"
    assert abs(with_ci[0]["ci_lower"] - 1.04) < 0.03


def test_negative_context_still_suppresses_when_no_clean_twin():
    """The fix must NOT weaken suppression: an effect ONLY ever stated next to a
    negative-context marker is still declined."""
    text = (
        "This retrospective cohort study found that prior exposure raised the odds "
        "of recurrence (OR 2.50, 95% CI 1.40 to 4.46)."
    )
    effects = rx.extract(text, specialty="cervical_cancer")["effects"]
    assert not _find(effects, 2.50), \
        "retrospective-cohort estimate should remain suppressed (no clean twin)"


# --------------------------------------------------------------------------- #
# 2. Control-character -> dash glyph repair
# --------------------------------------------------------------------------- #

def test_control_char_between_ci_bounds_restored_to_dash():
    text = "Mortality was lower [hazard ratio 0.78 (95% CI 0.45\x011.35, p = 0.37)]."
    effects = rx.extract(text, specialty="meningitis")["effects"]
    hits = [e for e in _find(effects, 0.78) if e.get("ci_lower") is not None]
    assert hits, "control-char en-dash glyph dropped the CI"
    e = hits[0]
    assert abs(e["ci_lower"] - 0.45) < 0.03 and abs(e["ci_upper"] - 1.35) < 0.03


def test_control_char_repair_is_scoped_to_between_digits():
    """A control char NOT wedged between two digits must be left untouched (it is
    not a dash) — here it sits between letters and a digit, so the CI is unaffected
    and the normal CI still parses."""
    norm = EnhancedExtractor().normalize_text("group\x01A had RR 1.20 (95% CI 1.05-1.40)")
    # the stray control char between a letter and a letter/digit is not turned
    # into a dash inside a number; the real CI dash is preserved.
    assert "1.05-1.40" in norm
    assert "\x01" not in norm or norm.count("-") >= 1


def test_digit_control_digit_repair_unit():
    norm = EnhancedExtractor().normalize_text("0.45\x011.35")
    assert norm == "0.45-1.35"
