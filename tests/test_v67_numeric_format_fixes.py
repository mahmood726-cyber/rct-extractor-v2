"""
Regression tests for the v6.7 core-extractor numeric-format fixes (real-PDF
accuracy pass; surfaced as non-disease-specific gaps during the glioma/MDS eval).

Three generalizable formats the generic CI-tail / type-glue previously missed:

1. LABEL INTERJECTION between an effect keyword and its value, where the label
   may itself contain a number: "HR for PFS 1.04", "RR for 90-day mortality was
   0.84". The pre-fix abbreviated glue (_ABGLUE) had no "for <label>" branch at
   all, and the spelled glue (_TWGLUE) excluded digits inside the label, so a
   numeric label ("90-day") truncated the match. Fixed with a clause-bounded,
   digit-permitting "for" branch in BOTH glues, kept precise by the mandatory
   95%-CI anchor (_CITAIL) that must follow the captured point estimate.

2. PARENTHETICAL-LABEL COLON between the keyword and value:
   "hazard ratio (CS HR): 1.75 (95% CI 1.20-2.55)", "aHR (adjusted): 0.62 ...".
   The parenthetical alias/label blocked the joiner. Fixed with an optional,
   bracket-balanced "(...)" segment ahead of the joiner in both glues.

3. EQUALS-SIGN as the SEPARATOR BETWEEN the two CI bounds:
   "95% CI 0.85 = 1.27" (an "=" where a dash/"to"/comma normally sits, a common
   PDF text-layer rendering of the en-dash). Fixed by adding "=" to the bound
   separator class in _BND. (Equals as the CI *introducer* — "95% CI = 0.85-1.27"
   — already worked via _CIPRE; covered here as a guard.)

All inputs are synthetic and contain NO benchmark gold value or PMCID; they
exercise the parsing mechanism, not a specific paper. The point/CI numbers are
arbitrary plausible values chosen only to drive the regex.
"""
import rct_extractor as rx
from rct_extractor._engine.core.enhanced_extractor_v3 import EnhancedExtractor


def _match(text, etype, point, lo, hi, tol=0.005):
    effects = rx.extract(text)["effects"]
    for e in effects:
        if (e.get("type") == etype
                and e.get("effect_size") is not None
                and abs(e["effect_size"] - point) < tol
                and e.get("ci_lower") is not None
                and abs(e["ci_lower"] - lo) < tol
                and e.get("ci_upper") is not None
                and abs(e["ci_upper"] - hi) < tol):
            return True
    return False


# --------------------------------------------------------------------------- #
# 1. Label interjection (keyword -> label[maybe with digits] -> value -> CI)
# --------------------------------------------------------------------------- #

def test_label_interjection_abbrev_hr_plain():
    assert _match("HR for PFS 1.04 (95% CI 0.85-1.27)", "HR", 1.04, 0.85, 1.27)


def test_label_interjection_abbrev_rr_numeric_label():
    # The label "90-day mortality" contains a number that must NOT be mistaken
    # for the point estimate; 0.84 (the value before the 95% CI) is correct.
    assert _match("RR for 90-day mortality was 0.84 (95% CI 0.72 to 0.98)",
                  "RR", 0.84, 0.72, 0.98)


def test_label_interjection_abbrev_or_numeric_label():
    assert _match("OR for 30-day readmission 0.55 (95% CI 0.40-0.75)",
                  "OR", 0.55, 0.40, 0.75)


def test_label_interjection_spelled_numeric_label():
    assert _match(
        "hazard ratio for 90-day mortality was 0.84 (95% CI 0.72 to 0.98)",
        "HR", 0.84, 0.72, 0.98)


def test_label_interjection_does_not_grab_label_number():
    # Guard: the numeric part of the label must never be returned as the effect.
    effects = rx.extract("RR for 90-day mortality was 0.84 (95% CI 0.72 to 0.98)")["effects"]
    assert not any(e.get("type") == "RR" and abs((e.get("effect_size") or 0) - 90) < 1
                   for e in effects)


# --------------------------------------------------------------------------- #
# 2. Parenthetical-label colon
# --------------------------------------------------------------------------- #

def test_parenthetical_label_colon_spelled():
    assert _match("hazard ratio (CS HR): 1.75 (95% CI 1.20-2.55)",
                  "HR", 1.75, 1.20, 2.55)


def test_parenthetical_label_colon_spaced():
    assert _match("hazard ratio ( CS HR ): 1.75 (95% CI 1.20-2.55)",
                  "HR", 1.75, 1.20, 2.55)


def test_parenthetical_label_colon_abbrev():
    assert _match("aHR (adjusted): 0.62 (95% CI 0.45-0.85)",
                  "HR", 0.62, 0.45, 0.85)


def test_parenthetical_label_colon_does_not_eat_ci_paren():
    # Guard: a normal "OR 0.67 (95% CI ...)" must still extract 0.67 with its CI
    # (the optional parenthetical must stay optional and not consume the CI paren).
    assert _match("OR 0.67 (95% CI 0.45-0.89)", "OR", 0.67, 0.45, 0.89)


# --------------------------------------------------------------------------- #
# 3. Equals-sign CI separators
# --------------------------------------------------------------------------- #

def test_equals_bound_separator():
    assert _match("HR 1.04 (95% CI 0.85 = 1.27)", "HR", 1.04, 0.85, 1.27)


def test_equals_bound_separator_no_paren():
    assert _match("aHR 0.84, 95% CI 0.72 = 0.98", "HR", 0.84, 0.72, 0.98)


def test_equals_introducer_still_works():
    # Guard for the already-working introducer-equals path.
    assert _match("HR 0.69 (95% CI = 0.52-0.90)", "HR", 0.69, 0.52, 0.90)
