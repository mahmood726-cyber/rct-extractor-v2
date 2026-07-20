"""
Arm-level / 2x2 + continuous extraction for substance-use-disorder (SUD) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
SUD endpoints and MOUD / behavioural / comparator arm labels:

  binary outcomes (retention, negative UDS, abstinence, overdose, relapse) -> 2x2
    events/N per arm
  continuous (craving, opioid-withdrawal severity) -> mean+SD / median+IQR.
    NONE is log-normal.

A bare effect abbreviation (HR/OR/RR) is NEVER an arm label.
"""
import re
from typing import Dict, List

from .substance_use_disorder import get_substance_use_disorder_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_SUD_ENDPOINT_PATTERNS = []
for _sub in ("opioid", "stimulant", "general"):
    _SUD_ENDPOINT_PATTERNS.extend(get_substance_use_disorder_endpoint_patterns(_sub))

# MOUD / behavioural / comparator arm labels. Full names case-insensitive.
# Generic comparators included. NO bare effect abbreviation (HR/OR/RR) is a label.
_SUD_ARM_FULL = [
    # Medications for opioid use disorder
    (r"buprenorphine[- ]naloxone|\bsuboxone\b|\bzubsolv\b", "buprenorphine-naloxone"),
    (r"(?:extended[- ]release\s+|depot\s+|injectable\s+|sublingual\s+)?buprenorphine|\bsublocade\b",
     "buprenorphine"),
    (r"methadone", "methadone"),
    (r"(?:extended[- ]release\s+|xr[- ]|injectable\s+)?naltrexone|\bvivitrol\b", "naltrexone"),
    (r"lofexidine|\blucemyra\b", "lofexidine"),
    (r"clonidine", "clonidine"),
    # Stimulant-disorder agents
    (r"bupropion", "bupropion"),
    (r"modafinil", "modafinil"),
    (r"topiramate", "topiramate"),
    # Behavioural
    (r"contingency\s+management", "contingency-management"),
    (r"cognitive\s+behaviou?ral\s+therapy|\bcbt\b", "cbt"),
    # Generic comparators
    (r"\bplacebo\b", "placebo"),
    (r"\bdetoxification\b|\bdetox\b|medically\s+managed\s+withdrawal", "detoxification"),
    (r"treatment\s+as\s+usual|\btau\b|usual\s+care", "treatment-as-usual"),
    (r"standard\s+(?:of\s+)?care", "standard-of-care"),
    (r"wait[- ]?list(?:\s+control)?", "waitlist"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_SUD_ARM_COMPILED = [(re.compile(p, re.I), n) for p, n in _SUD_ARM_FULL]

# SUD continuous outcomes; none log-normal.
_SUD_CONTINUOUS = {"CRAVING", "WITHDRAWAL_SEVERITY"}
_SUD_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_SUD_ENDPOINT_PATTERNS,
                                arm_compiled=_SUD_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_SUD_ENDPOINT_PATTERNS,
                               arm_compiled=_SUD_ARM_COMPILED,
                               continuous_endpoints=_SUD_CONTINUOUS,
                               lognormal_endpoints=_SUD_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_SUD_ENDPOINT_PATTERNS,
                              arm_compiled=_SUD_ARM_COMPILED,
                              continuous_endpoints=_SUD_CONTINUOUS,
                              lognormal_endpoints=_SUD_LOGNORMAL)
