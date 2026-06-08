"""
Arm-level / 2x2 + continuous extraction for cervical-cancer / HPV trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with cervical-cancer
endpoints and HPV-vaccine / screening-method / precancer-treatment arm labels:

  binary outcomes (persistent infection, CIN2+, genital warts, screen-positive,
    lesion clearance, treatment failure, recurrence, cancer incidence) -> 2x2
    events/N per arm
  continuous (anti-HPV titre -> log-normal, pool on the log scale).
"""
import re
from typing import Dict, List

from .cervical_cancer import get_cervical_cancer_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Cervical-cancer endpoint patterns (string, endpoint) across all subspecialties.
_CC_ENDPOINT_PATTERNS = []
for _sub in ("vaccine", "screening", "treatment", "mortality"):
    _CC_ENDPOINT_PATTERNS.extend(get_cervical_cancer_endpoint_patterns(_sub))

# HPV-vaccine / screening / treatment arm labels. Full names case-insensitive;
# bare UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does not
# match).
_CC_ARM_FULL = [
    # HPV vaccines
    (r"nonavalent|9[- ]valent\s+(?:hpv\s+)?vaccine|nine[- ]valent", "nonavalent-hpv-vaccine"),
    (r"gardasil\s*9", "nonavalent-hpv-vaccine"),
    (r"quadrivalent\s+(?:hpv\s+)?vaccine|gardasil(?!\s*9)", "quadrivalent-hpv-vaccine"),
    (r"bivalent\s+(?:hpv\s+)?vaccine|cervarix", "bivalent-hpv-vaccine"),
    (r"cecolin", "cecolin"),
    (r"walrinvax", "walrinvax"),
    (r"hepatitis\s+[ab]\s+vaccine|meningococcal\s+(?:conjugate\s+)?vaccine", "control-vaccine"),
    # screening methods
    (r"visual\s+inspection\s+with\s+acetic\s+acid", "via"),
    (r"hpv\s+(?:dna\s+)?test(?:ing)?|care\s?hpv", "hpv-testing"),
    (r"liquid[- ]based\s+cytology|conventional\s+cytology|pap\s+smear|cytology", "cytology"),
    (r"self[- ](?:sampling|collection|collected)", "self-sampling"),
    # precancer treatments
    (r"cryotherapy|cryosurgery", "cryotherapy"),
    (r"thermal\s+ablation|thermocoagulation|cold\s+coagulation", "thermal-ablation"),
    (r"loop\s+electrosurgical\s+excision|loop\s+excision", "leep"),
    (r"cold[- ]knife\s+coni[sz]ation|coni[sz]ation", "conization"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_CC_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bVIA\b", "via"),
    (r"\bVILI\b", "vili"),
    (r"\bHPV\b(?=\s*(?:test|dna))", "hpv-testing"),
    (r"\bLEEP\b|\bLLETZ\b", "leep"),
    (r"\b4vHPV\b|\bqHPV\b", "quadrivalent-hpv-vaccine"),
    (r"\b2vHPV\b|\bbHPV\b", "bivalent-hpv-vaccine"),
    (r"\b9vHPV\b", "nonavalent-hpv-vaccine"),
]
_CC_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _CC_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _CC_ARM_ABBREV])

# Cervical-cancer continuous outcomes; anti-HPV titre (immunogenicity) is log-normal.
_CC_CONTINUOUS = {"HPV_IMMUNOGENICITY"}
_CC_LOGNORMAL = {"HPV_IMMUNOGENICITY"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_CC_ENDPOINT_PATTERNS,
                                arm_compiled=_CC_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_CC_ENDPOINT_PATTERNS,
                               arm_compiled=_CC_ARM_COMPILED,
                               continuous_endpoints=_CC_CONTINUOUS,
                               lognormal_endpoints=_CC_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_CC_ENDPOINT_PATTERNS,
                              arm_compiled=_CC_ARM_COMPILED,
                              continuous_endpoints=_CC_CONTINUOUS,
                              lognormal_endpoints=_CC_LOGNORMAL)
