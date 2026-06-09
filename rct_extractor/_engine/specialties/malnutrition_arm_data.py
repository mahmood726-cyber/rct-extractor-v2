"""
Arm-level / 2x2 + continuous extraction for malnutrition (SAM / undernutrition)
trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with malnutrition
endpoints and therapeutic-feeding / micronutrient arm labels:

  binary outcomes (nutritional recovery, default, relapse, stunting, wasting,
    anaemia, oedema resolution, mortality) -> 2x2 events/N per arm
  continuous (weight-gain rate, MUAC change, weight gain, height gain,
    weight-for-height z-score, length of stay, time to recovery -> mean+SD /
    median+IQR; serum micronutrient titres -> log-normal, pool on the log scale).
"""
import re
from typing import Dict, List

from .malnutrition import get_malnutrition_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Malnutrition endpoint patterns (string, endpoint) across all subspecialties.
_MALN_ENDPOINT_PATTERNS = []
for _sub in ("therapeutic_feeding", "micronutrient", "mortality", "recovery_growth"):
    _MALN_ENDPOINT_PATTERNS.extend(get_malnutrition_endpoint_patterns(_sub))

# Therapeutic-feeding / micronutrient arm labels. Full names case-insensitive;
# bare UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does
# not match).
_MALN_ARM_FULL = [
    (r"ready[- ]to[- ]use\s+therapeutic\s+food", "rutf"),
    (r"ready[- ]to[- ]use\s+supplementary\s+food", "rusf"),
    (r"locally[- ]produced\s+rutf|local\s+rutf", "local-rutf"),
    (r"milk[- ]based\s+(?:rutf|formula)", "milk-rutf"),
    (r"soy[- ]based\s+(?:rutf|formula)", "soy-rutf"),
    (r"corn[- ]soy\s+blend", "corn-soy-blend"),
    (r"therapeutic\s+milk|\bf-?75\b|\bf-?100\b", "therapeutic-milk"),
    (r"multiple\s+micronutrient\s+powder|micronutrient\s+powder", "micronutrient-powder"),
    (r"lipid[- ]based\s+nutrient\s+supplement|sq[- ]lns", "lns"),
    (r"\bzinc\b", "zinc"),
    (r"vitamin\s+a", "vitamin-a"),
    (r"\biron\b", "iron"),
    (r"amoxicillin", "amoxicillin"),
    (r"cefdinir", "cefdinir"),
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|routine\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_MALN_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bRUTF\b", "rutf"),
    (r"\bRUSF\b", "rusf"),
    (r"\bMNP\b", "micronutrient-powder"),
    (r"\bLNS\b", "lns"),
    (r"\bSQ-LNS\b", "lns"),
    (r"\bCSB\b", "corn-soy-blend"),
]
_MALN_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _MALN_ARM_FULL]
                      + [(re.compile(p), n) for p, n in _MALN_ARM_ABBREV])

# Malnutrition continuous outcomes; serum micronutrient titre is log-normal.
_MALN_CONTINUOUS = {"WEIGHT_GAIN_RATE", "LENGTH_OF_STAY", "MICRONUTRIENT_STATUS",
                    "MUAC_CHANGE", "WEIGHT_GAIN", "HEIGHT_GAIN",
                    "WEIGHT_FOR_HEIGHT", "TIME_TO_RECOVERY"}
_MALN_LOGNORMAL = {"MICRONUTRIENT_STATUS"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_MALN_ENDPOINT_PATTERNS,
                                arm_compiled=_MALN_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_MALN_ENDPOINT_PATTERNS,
                               arm_compiled=_MALN_ARM_COMPILED,
                               continuous_endpoints=_MALN_CONTINUOUS,
                               lognormal_endpoints=_MALN_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_MALN_ENDPOINT_PATTERNS,
                              arm_compiled=_MALN_ARM_COMPILED,
                              continuous_endpoints=_MALN_CONTINUOUS,
                              lognormal_endpoints=_MALN_LOGNORMAL)
