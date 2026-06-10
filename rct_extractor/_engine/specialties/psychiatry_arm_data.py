"""
Arm-level / 2x2 + continuous extraction for psychiatry trials (depression /
anxiety / bipolar / psychosis).

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with psychiatry
endpoints and antidepressant / antipsychotic / mood-stabiliser arm labels:

  binary outcomes (treatment response, remission, mania response, psychosis
    response, relapse) -> 2x2 events/N per arm
  continuous (MADRS, HAM-D, PHQ-9, HAM-A, GAD-7, YMRS, PANSS, CGI) -> mean+SD /
    median+IQR. All psychiatric rating scales are bounded interval scales --
    NOT log-normal, so the log-normal set is intentionally empty.
"""
import re
from typing import Dict, List

from .psychiatry import get_psychiatry_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Psychiatry endpoint patterns (string, endpoint) across all subspecialties.
_PSYCH_ENDPOINT_PATTERNS = []
for _sub in ("depression", "anxiety", "bipolar", "psychosis"):
    _PSYCH_ENDPOINT_PATTERNS.extend(get_psychiatry_endpoint_patterns(_sub))

# Antidepressant / antipsychotic / mood-stabiliser arm labels. All matched as
# full case-insensitive drug names with word boundaries. Bare effect
# abbreviations (HR/OR/RR) are NEVER arm labels (no abbreviation table here, so
# nothing uppercase-matches them). Note CGI is a rating SCALE, not an arm, so it
# is deliberately absent from the arm labels.
_PSYCH_ARM_FULL = [
    # SSRIs
    (r"\bsertraline\b|\bzoloft\b", "sertraline"),
    (r"\bfluoxetine\b|\bprozac\b", "fluoxetine"),
    (r"\bescitalopram\b|\blexapro\b", "escitalopram"),
    (r"\bcitalopram\b|\bcelexa\b", "citalopram"),
    (r"\bparoxetine\b|\bpaxil\b", "paroxetine"),
    # SNRIs
    (r"\bvenlafaxine\b|\beffexor\b", "venlafaxine"),
    (r"\bdesvenlafaxine\b|\bpristiq\b", "desvenlafaxine"),
    (r"\bduloxetine\b|\bcymbalta\b", "duloxetine"),
    # Other antidepressants
    (r"\bbupropion\b|\bwellbutrin\b", "bupropion"),
    (r"\bmirtazapine\b|\bremeron\b", "mirtazapine"),
    (r"\bvortioxetine\b|\btrintellix\b|\bbrintellix\b", "vortioxetine"),
    (r"\bagomelatine\b|\bvaldoxan\b", "agomelatine"),
    # Rapid-acting / neuroactive-steroid antidepressants
    (r"\besketamine\b|\bspravato\b", "esketamine"),
    (r"\bketamine\b", "ketamine"),
    (r"\bzuranolone\b|\bzurzuvae\b", "zuranolone"),
    (r"\bbrexanolone\b|\bzulresso\b", "brexanolone"),
    # Atypical antipsychotics
    (r"\brisperidone\b|\brisperdal\b", "risperidone"),
    (r"\bpaliperidone\b|\binvega\b", "paliperidone"),
    (r"\bolanzapine\b|\bzyprexa\b", "olanzapine"),
    (r"\bquetiapine\b|\bseroquel\b", "quetiapine"),
    (r"\baripiprazole\b|\babilify\b", "aripiprazole"),
    (r"\bbrexpiprazole\b|\brexulti\b", "brexpiprazole"),
    (r"\bcariprazine\b|\bvraylar\b", "cariprazine"),
    (r"\blurasidone\b|\blatuda\b", "lurasidone"),
    (r"\blumateperone\b|\bcaplyta\b", "lumateperone"),
    # Typical antipsychotic / clozapine
    (r"\bhaloperidol\b|\bhaldol\b", "haloperidol"),
    (r"\bclozapine\b|\bclozaril\b", "clozapine"),
    # Mood stabilisers
    (r"\blithium\b", "lithium"),
    (r"\bdivalproex\b|\bvalproate\b|\bvalproic\s+acid\b|\bdepakote\b", "valproate"),
    (r"\blamotrigine\b|\blamictal\b", "lamotrigine"),
    # Generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|treatment\s+as\s+usual", "standard-of-care"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_PSYCH_ARM_COMPILED = [(re.compile(p, re.I), n) for p, n in _PSYCH_ARM_FULL]

# Psychiatry continuous outcomes are all bounded ordinal/interval clinical rating
# scales (MADRS 0-60, HAM-D 0-52, PHQ-9 0-27, HAM-A 0-56, GAD-7 0-21, YMRS 0-60,
# PANSS 30-210, CGI 1-7) -- NOT log-normal, so no log-scale pooling. The
# log-normal set is intentionally empty.
_PSYCH_CONTINUOUS = {"MADRS_CHANGE", "HAMD_CHANGE", "PHQ9_CHANGE", "HAMA_CHANGE",
                     "GAD7_CHANGE", "YMRS_CHANGE", "PANSS_CHANGE", "CGI"}
_PSYCH_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_PSYCH_ENDPOINT_PATTERNS,
                                arm_compiled=_PSYCH_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_PSYCH_ENDPOINT_PATTERNS,
                               arm_compiled=_PSYCH_ARM_COMPILED,
                               continuous_endpoints=_PSYCH_CONTINUOUS,
                               lognormal_endpoints=_PSYCH_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_PSYCH_ENDPOINT_PATTERNS,
                              arm_compiled=_PSYCH_ARM_COMPILED,
                              continuous_endpoints=_PSYCH_CONTINUOUS,
                              lognormal_endpoints=_PSYCH_LOGNORMAL)
