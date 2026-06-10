"""
Arm-level / 2x2 extraction for venous thromboembolism (VTE) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, poolable gate) configured with VTE endpoints and
anticoagulant drug-class arm labels:

  binary outcomes (recurrent VTE/DVT/PE, incident VTE, DVT, PE, major bleeding,
    CRNM bleeding, intracranial / fatal bleeding, all-cause + PE-related death,
    post-thrombotic syndrome) -> 2x2 events/N per arm.

VTE trials report events, not continuous lab changes, so no continuous endpoints
are configured.
"""
import re
from typing import Dict, List

from .venous_thromboembolism import get_venous_thromboembolism_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# VTE endpoint patterns (string, endpoint) across all subspecialties.
_VTE_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "prevention", "bleeding", "mortality"):
    _VTE_ENDPOINT_PATTERNS.extend(get_venous_thromboembolism_endpoint_patterns(_sub))

# Anticoagulant drug-class arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE.
_VTE_ARM_FULL = [
    # DOACs
    (r"apixaban", "apixaban"),
    (r"rivaroxaban", "rivaroxaban"),
    (r"edoxaban", "edoxaban"),
    (r"dabigatran", "dabigatran"),
    (r"betrixaban", "betrixaban"),
    (r"direct\s+oral\s+anticoagulant", "doac"),
    # Vitamin-K antagonists
    (r"warfarin", "warfarin"),
    (r"acenocoumarol", "acenocoumarol"),
    (r"vitamin[- ]k\s+antagonist", "vitamin-k-antagonist"),
    # Heparins
    (r"enoxaparin", "enoxaparin"),
    (r"dalteparin", "dalteparin"),
    (r"tinzaparin", "tinzaparin"),
    (r"nadroparin", "nadroparin"),
    (r"low[- ]molecular[- ]weight\s+heparin", "lmwh"),
    (r"unfractionated\s+heparin", "unfractionated-heparin"),
    (r"fondaparinux", "fondaparinux"),
    # other comparators
    (r"\baspirin\b|acetylsalicylic\s+acid", "aspirin"),
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|conventional\s+(?:therapy|treatment)",
     "standard-of-care"),
    (r"no\s+(?:anticoagulation|prophylaxis|treatment)", "no-treatment"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_VTE_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bDOAC\b|\bNOAC\b", "doac"),
    (r"\bVKA\b", "vitamin-k-antagonist"),
    (r"\bLMWH\b", "lmwh"),
    (r"\bUFH\b", "unfractionated-heparin"),
]
_VTE_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _VTE_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _VTE_ARM_ABBREV])

# VTE outcomes are events; no continuous endpoints.
_VTE_CONTINUOUS: set = set()
_VTE_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_VTE_ENDPOINT_PATTERNS,
                                arm_compiled=_VTE_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_VTE_ENDPOINT_PATTERNS,
                               arm_compiled=_VTE_ARM_COMPILED,
                               continuous_endpoints=_VTE_CONTINUOUS,
                               lognormal_endpoints=_VTE_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_VTE_ENDPOINT_PATTERNS,
                              arm_compiled=_VTE_ARM_COMPILED,
                              continuous_endpoints=_VTE_CONTINUOUS,
                              lognormal_endpoints=_VTE_LOGNORMAL)
