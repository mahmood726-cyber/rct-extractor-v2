"""
Arm-level / 2x2 + continuous extraction for alcohol-use-disorder (AUD) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
AUD endpoints and pharmacotherapy / behavioural / comparator arm labels:

  binary outcomes (abstinence, relapse, retention, seizures) -> 2x2 events/N per arm
  continuous (heavy-drinking days, percent days abstinent, drinks per day,
    craving, CIWA-Ar) -> mean+SD / median+IQR. NONE is log-normal.

A bare effect abbreviation (HR/OR/RR) is NEVER an arm label.
"""
import re
from typing import Dict, List

from .alcohol_use_disorder import get_alcohol_use_disorder_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_AUD_ENDPOINT_PATTERNS = []
for _sub in ("pharmacotherapy", "psychosocial", "withdrawal"):
    _AUD_ENDPOINT_PATTERNS.extend(get_alcohol_use_disorder_endpoint_patterns(_sub))

# Pharmacotherapy / behavioural / comparator arm labels. Full names
# case-insensitive. Generic comparators included. NO bare effect abbreviation
# (HR/OR/RR) is a label.
_AUD_ARM_FULL = [
    # Anti-craving / aversive pharmacotherapy
    (r"(?:extended[- ]release\s+|xr[- ]|injectable\s+)?naltrexone|\bvivitrol\b", "naltrexone"),
    (r"acamprosate|\bcampral\b", "acamprosate"),
    (r"nalmefene|\bselincro\b", "nalmefene"),
    (r"disulfiram|\bantabuse\b", "disulfiram"),
    (r"baclofen", "baclofen"),
    (r"topiramate", "topiramate"),
    (r"gabapentin", "gabapentin"),
    (r"varenicline", "varenicline"),
    (r"ondansetron", "ondansetron"),
    # Behavioural
    (r"cognitive\s+behaviou?ral\s+therapy|\bcbt\b", "cbt"),
    (r"motivational\s+(?:enhancement\s+therapy|interviewing)|\bmet\b|\bmi\b", "motivational"),
    (r"brief\s+intervention", "brief-intervention"),
    (r"contingency\s+management", "contingency-management"),
    # Withdrawal management
    (r"chlordiazepoxide", "chlordiazepoxide"),
    (r"diazepam", "diazepam"),
    (r"lorazepam", "lorazepam"),
    # Generic comparators
    (r"\bplacebo\b", "placebo"),
    (r"treatment\s+as\s+usual|\btau\b|usual\s+care", "treatment-as-usual"),
    (r"standard\s+(?:of\s+)?care", "standard-of-care"),
    (r"wait[- ]?list(?:\s+control)?", "waitlist"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_AUD_ARM_COMPILED = [(re.compile(p, re.I), n) for p, n in _AUD_ARM_FULL]

# AUD continuous outcomes; none log-normal.
_AUD_CONTINUOUS = {"HEAVY_DRINKING_DAYS", "PCT_DAYS_ABSTINENT", "DRINKS_PER_DAY",
                   "CRAVING", "WITHDRAWAL_SEVERITY"}
_AUD_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_AUD_ENDPOINT_PATTERNS,
                                arm_compiled=_AUD_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_AUD_ENDPOINT_PATTERNS,
                               arm_compiled=_AUD_ARM_COMPILED,
                               continuous_endpoints=_AUD_CONTINUOUS,
                               lognormal_endpoints=_AUD_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_AUD_ENDPOINT_PATTERNS,
                              arm_compiled=_AUD_ARM_COMPILED,
                              continuous_endpoints=_AUD_CONTINUOUS,
                              lognormal_endpoints=_AUD_LOGNORMAL)
