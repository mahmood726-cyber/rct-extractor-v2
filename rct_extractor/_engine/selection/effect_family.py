"""
effect_family — canonical effect-measure family, the fix for the ratio/difference confusion.

Two bugs, one root cause (effect-family misclassification), fixed here:
  1. AACT param_type is fragmented into 6,417 distinct strings (LS Mean Difference alone
     has ~15 spellings). A ratio-only pooler silently mis-ingests the 27k+ PRIMARY
     DIFFERENCE-scale analyses. -> normalize_param_type().
  2. Prose extraction mislabels effect TYPE: "aRR, 0.99" read as ARD (a difference),
     "61% (95% CI 52-70)" read as MD. Both caught in the malaria adjudication set. Pooling
     a ratio on the difference scale is the TB rate-difference catastrophe. -> classify_from_text().

Families: 'ratio' (pool on log scale), 'difference' (natural scale), 'standardized' (SMD),
'slope' (regression coefficient), 'proportion' (single-arm %/rate), 'unknown'.
A pool must NEVER mix families; a ratio and a difference are not interconvertible without
the baseline risk.
"""
import re

# order matters: 'difference' wins over 'ratio'/'proportion' when both words present
# ("Difference in response rates" is a difference; "Rate Ratio" is a ratio).
def normalize_param_type(s):
    t = (s or "").lower().strip()
    if not t:
        return "unknown"
    # standardized mean difference first (contains "difference" but is its own family)
    if ("standardized mean" in t or "standardised mean" in t or "effect size" in t
            or "cohen" in t or re.search(r"\bsmd\b", t) or "pooled sd" in t):
        return "standardized"
    # difference family (any explicit difference wording)
    if ("difference" in t or re.search(r"\brd\b", t) or "differ" in t):
        return "difference"
    # ratio family (incl. vaccine efficacy = 1-RR, and geometric-mean fold rise/change)
    if ("ratio" in t or "hazard" in t or "odds" in t or "relative risk" in t
            or "cox proportional hazard" in t or "vaccine efficacy" in t or re.search(r"\bve\b", t)
            or "fold rise" in t or "fold increase" in t or "fold change" in t
            or re.search(r"\b(hr|or|rr|gmr|irr)\b", t)):
        return "ratio"
    # slope / regression coefficient
    if ("slope" in t or "coefficient" in t or re.search(r"\bbeta\b", t)):
        return "slope"
    # single-arm proportion / rate (no ratio, no difference)
    if ("percentage" in t or "proportion" in t or t == "rate" or "percent" in t
            or "incidence rate" in t):
        return "proportion"
    # single-arm location estimate (LS mean / least-squares mean / bare mean): NOT a
    # between-group effect — must never be pooled as a treatment effect. Flag distinctly.
    if (re.search(r"\b(ls ?means?|lsmeans?|least[- ]squares?\s*\(?ls?\)?\s*means?|"
                  r"least[- ]squares? means?|geometric means?|means?)\b", t)):
        return "single_arm"
    return "unknown"


# prose effect quote -> family. Reads the measure KEYWORD, not just the number.
_RATIO_TOK = re.compile(r"\b(a?hr|a?or|a?rr|hazard ratio|odds ratio|risk ratio|"
                        r"relative risk|rate ratio|incidence rate ratio|irr|"
                        r"geometric mean ratio|gmr|ratio)\b", re.I)
_DIFF_TOK = re.compile(r"(risk difference|mean difference|rate difference|absolute "
                       r"(?:risk )?difference|\bard\b|\brd\b|difference of|percentage[- ]point)", re.I)
_SMD_TOK = re.compile(r"(standardi[sz]ed mean difference|\bsmd\b|cohen'?s? d|hedges)", re.I)
_PCT_ONLY = re.compile(r"\d+(?:\.\d+)?\s*%")

def classify_from_text(source_text, declared_type=None):
    """Return (family, confidence, note). Overrides a declared type when the text keyword
    disagrees — the malaria failure mode. 'aRR' beats a declared 'ARD'."""
    s = source_text or ""
    if _SMD_TOK.search(s):
        return "standardized", 0.9, "smd-token"
    # an explicit ratio token (aRR/aHR/OR/…) is decisive even if a difference word is near
    mr = _RATIO_TOK.search(s)
    md = _DIFF_TOK.search(s)
    if mr and not (md and md.start() < mr.start()):
        return "ratio", 0.85, f"ratio-token:{mr.group(0)}"
    if md:
        return "difference", 0.85, f"diff-token:{md.group(0)}"
    # bare percentage with a CI but no ratio/difference word -> a proportion, NOT a mean diff
    if _PCT_ONLY.search(s):
        return "proportion", 0.6, "percent-only"
    if declared_type:
        return normalize_param_type(declared_type), 0.4, "fallback-declared"
    return "unknown", 0.0, "no-token"
