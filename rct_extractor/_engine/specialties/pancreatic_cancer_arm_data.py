"""
Arm-level / 2x2 + continuous extraction for pancreatic-cancer trials.

Thin wrapper over the shared malaria_arm_data engine, configured with
pancreatic-cancer endpoints and chemotherapy-regimen arm labels:

  binary (objective response, CA19-9 response, R0 resection, recurrence) -> 2x2
  continuous (serum CA19-9 -> log-normal; QoL -> MD).
"""
import re
from typing import Dict, List

from .pancreatic_cancer import get_pancreatic_cancer_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_PA_ENDPOINT_PATTERNS = []
for _sub in ("systemic", "adjuvant", "locally_advanced", "mortality"):
    _PA_ENDPOINT_PATTERNS.extend(get_pancreatic_cancer_endpoint_patterns(_sub))

_PA_ARM_FULL = [
    (r"(?:m)?folfirinox", "folfirinox"),
    (r"gemcitabine(?:[- ]+(?:and\s+)?nab[- ]?paclitaxel)?", "gemcitabine-nab-paclitaxel"),
    (r"nab[- ]?paclitaxel|abraxane", "nab-paclitaxel"),
    (r"gemcitabine[- ]capecitabine|gemcap", "gemcitabine-capecitabine"),
    (r"nalirifox", "nalirifox"),
    (r"liposomal\s+irinotecan|nal[- ]?iri|onivyde", "liposomal-irinotecan"),
    (r"gemcitabine", "gemcitabine"),
    (r"olaparib", "olaparib"),
    (r"erlotinib", "erlotinib"),
    (r"\bs-?1\b", "s-1"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"observation(?:\s+(?:group|arm|alone))?", "observation"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_PA_ARM_ABBREV = []
_PA_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _PA_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _PA_ARM_ABBREV])

_PA_CONTINUOUS = {"CA199_LEVEL", "QOL"}
_PA_LOGNORMAL = {"CA199_LEVEL"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_PA_ENDPOINT_PATTERNS,
                                arm_compiled=_PA_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_PA_ENDPOINT_PATTERNS,
                               arm_compiled=_PA_ARM_COMPILED,
                               continuous_endpoints=_PA_CONTINUOUS,
                               lognormal_endpoints=_PA_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_PA_ENDPOINT_PATTERNS,
                              arm_compiled=_PA_ARM_COMPILED,
                              continuous_endpoints=_PA_CONTINUOUS,
                              lognormal_endpoints=_PA_LOGNORMAL)
