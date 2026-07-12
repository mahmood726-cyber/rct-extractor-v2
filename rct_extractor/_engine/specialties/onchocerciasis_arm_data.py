"""
Arm-level / 2x2 + continuous extraction for onchocerciasis (river blindness) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with onchocerciasis
endpoints and microfilaricidal / macrofilaricidal arm labels:

  binary outcomes (microfilarial clearance, microfilarial / nodule prevalence,
    visual impairment / blindness, onchocercal skin disease, adverse events,
    Mazzotti reaction) -> 2x2 events/N per arm
  continuous (skin microfilarial density / community microfilarial load,
    microfilarial-density reduction, transmission potential, ocular microfilariae)
    -> mean+SD / median+IQR; skin microfilarial densities, loads and transmission
    potentials are right-skewed -> log-normal, pool on the log scale / use GMR.
"""
import re
from typing import Dict, List

from .onchocerciasis import get_onchocerciasis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Onchocerciasis endpoint patterns (string, endpoint) across all subspecialties.
_ONCHO_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "mda", "morbidity", "safety"):
    _ONCHO_ENDPOINT_PATTERNS.extend(get_onchocerciasis_endpoint_patterns(_sub))

# Microfilaricidal / macrofilaricidal arm labels. Full names case-insensitive;
# bare UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does not
# match). Combination arms listed before their components so the combo wins.
_ONCHO_ARM_FULL = [
    (r"ivermectin\s*(?:\+|plus|and|/|-)\s*albendazole", "ivermectin-albendazole"),
    (r"ivermectin\s*(?:\+|plus|and|/|-)\s*doxycycline", "ivermectin-doxycycline"),
    (r"ivermectin", "ivermectin"),
    (r"moxidectin", "moxidectin"),
    (r"doxycycline", "doxycycline"),
    (r"diethylcarbamazine", "diethylcarbamazine"),
    (r"suramin", "suramin"),
    (r"albendazole", "albendazole"),
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"untreated(?:\s+(?:group|arm|control))?", "untreated"),
    (r"no\s+treatment", "untreated"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_ONCHO_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bIVM\b", "ivermectin"),
    (r"\bMOX\b", "moxidectin"),
    (r"\bDEC\b", "diethylcarbamazine"),
    (r"\bDOX\b", "doxycycline"),
    (r"\bABZ\b", "albendazole"),
]
_ONCHO_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _ONCHO_ARM_FULL]
                       + [(re.compile(p), n) for p, n in _ONCHO_ARM_ABBREV])

# Onchocerciasis continuous outcomes; skin microfilarial densities / loads and
# transmission potentials are right-skewed and pooled on the log scale (GMR).
_ONCHO_CONTINUOUS = {"SKIN_MF_DENSITY", "MICROFILARIAL_REDUCTION", "TRANSMISSION",
                     "OCULAR_MICROFILARIAE"}
_ONCHO_LOGNORMAL = {"SKIN_MF_DENSITY", "TRANSMISSION", "OCULAR_MICROFILARIAE"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_ONCHO_ENDPOINT_PATTERNS,
                                arm_compiled=_ONCHO_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_ONCHO_ENDPOINT_PATTERNS,
                               arm_compiled=_ONCHO_ARM_COMPILED,
                               continuous_endpoints=_ONCHO_CONTINUOUS,
                               lognormal_endpoints=_ONCHO_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_ONCHO_ENDPOINT_PATTERNS,
                              arm_compiled=_ONCHO_ARM_COMPILED,
                              continuous_endpoints=_ONCHO_CONTINUOUS,
                              lognormal_endpoints=_ONCHO_LOGNORMAL)
