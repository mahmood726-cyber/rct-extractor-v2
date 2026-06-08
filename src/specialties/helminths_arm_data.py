"""
Arm-level / 2x2 + continuous extraction for soil-transmitted helminth (STH) /
deworming trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with STH /
deworming endpoints and anthelmintic arm labels:

  binary outcomes (cure rate, treatment failure, infection prevalence, heavy
    infection, reinfection, stunting, anaemia) -> 2x2 events/N per arm
  continuous (egg reduction rate, weight, height, haemoglobin, MUAC, cognition
    -> mean+SD / median+IQR; egg counts (EPG) are right-skewed -> log-normal,
    pool on the log scale).
"""
import re
from typing import Dict, List

from .helminths import get_helminths_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Helminths endpoint patterns (string, endpoint) across all subspecialties.
_HELM_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "mass_deworming", "nutrition", "reinfection"):
    _HELM_ENDPOINT_PATTERNS.extend(get_helminths_endpoint_patterns(_sub))

# Anthelmintic arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_HELM_ARM_FULL = [
    (r"albendazole", "albendazole"),
    (r"mebendazole", "mebendazole"),
    (r"pyrantel(?:\s+pamoate)?", "pyrantel"),
    (r"levamisole", "levamisole"),
    (r"ivermectin", "ivermectin"),
    (r"tribendimidine", "tribendimidine"),
    (r"oxantel(?:\s+pamoate)?", "oxantel"),
    (r"nitazoxanide", "nitazoxanide"),
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"untreated(?:\s+(?:group|arm|control))?", "untreated"),
    (r"no\s+treatment", "untreated"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"deworming\s+(?:group|arm)", "deworming"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_HELM_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bALB\b", "albendazole"),
    (r"\bABZ\b", "albendazole"),
    (r"\bMEB\b|\bMBZ\b", "mebendazole"),
    (r"\bIVM\b", "ivermectin"),
    (r"\bLEV\b", "levamisole"),
    (r"\bPYR\b", "pyrantel"),
]
_HELM_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _HELM_ARM_FULL]
                      + [(re.compile(p), n) for p, n in _HELM_ARM_ABBREV])

# Helminths continuous outcomes; egg counts (EPG) are right-skewed and pooled
# on the log scale.
_HELM_CONTINUOUS = {"EGG_REDUCTION_RATE", "EGG_COUNT", "WEIGHT", "HEIGHT",
                    "ANAEMIA", "MUAC", "COGNITION", "REINFECTION_INTENSITY"}
_HELM_LOGNORMAL = {"EGG_COUNT", "REINFECTION_INTENSITY"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_HELM_ENDPOINT_PATTERNS,
                                arm_compiled=_HELM_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_HELM_ENDPOINT_PATTERNS,
                               arm_compiled=_HELM_ARM_COMPILED,
                               continuous_endpoints=_HELM_CONTINUOUS,
                               lognormal_endpoints=_HELM_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_HELM_ENDPOINT_PATTERNS,
                              arm_compiled=_HELM_ARM_COMPILED,
                              continuous_endpoints=_HELM_CONTINUOUS,
                              lognormal_endpoints=_HELM_LOGNORMAL)
