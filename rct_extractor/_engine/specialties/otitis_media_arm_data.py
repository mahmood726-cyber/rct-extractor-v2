"""
Arm-level / 2x2 + continuous extraction for otitis-media (middle-ear) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
otitis-media endpoints and antibiotic / vaccine / surgical / comparator arm
labels:

  binary outcomes (treatment failure, clinical cure, recurrence, effusion
    resolution, otorrho?ea/perforation, tympanostomy-tube insertion) -> 2x2
    events/N per arm
  continuous (hearing level in dB, ear-pain score) -> mean+SD / median+IQR.
    NONE is log-normal.

A bare effect abbreviation (HR/OR/RR) is NEVER an arm label.
"""
import re
from typing import Dict, List

from .otitis_media import get_otitis_media_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_OM_ENDPOINT_PATTERNS = []
for _sub in ("aom", "ome", "prevention"):
    _OM_ENDPOINT_PATTERNS.extend(get_otitis_media_endpoint_patterns(_sub))

# Antibiotic / vaccine / surgical / management arm labels. Full names
# case-insensitive. Generic comparators included. NO bare effect abbreviation
# (HR/OR/RR) is a label.
_OM_ARM_FULL = [
    # Antibiotics
    (r"amoxicillin[- ]clavulanate|amoxicillin/clavulanate|co[- ]amoxiclav|augmentin",
     "amoxicillin-clavulanate"),
    (r"amoxicillin", "amoxicillin"),
    (r"azithromycin", "azithromycin"),
    (r"cefdinir", "cefdinir"),
    (r"cefuroxime", "cefuroxime"),
    (r"ceftriaxone", "ceftriaxone"),
    (r"penicillin", "penicillin"),
    (r"trimethoprim[- ]sulfamethoxazole|co[- ]trimoxazole", "cotrimoxazole"),
    # Management strategies
    (r"watchful\s+waiting|wait[- ]and[- ]see|observation(?:\s+(?:group|arm))?|delayed\s+(?:antibiotic|prescri)",
     "watchful-waiting"),
    (r"immediate\s+(?:antibiotic|treatment)", "immediate-antibiotic"),
    # Surgical / device
    (r"tympanostomy\s+tubes?|ventilation\s+tubes?|grommets?", "tympanostomy-tubes"),
    (r"myringotomy", "myringotomy"),
    (r"adenoidectomy", "adenoidectomy"),
    # Vaccines / prophylaxis
    (r"pneumococcal\s+conjugate\s+vaccine|\bpcv(?:7|10|13|15|20)?\b", "pcv"),
    (r"xylitol", "xylitol"),
    # Generic comparators
    (r"\bplacebo\b", "placebo"),
    (r"\bvehicle\b", "vehicle"),
    (r"no\s+treatment|no\s+antibiotic", "no-treatment"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_OM_ARM_COMPILED = [(re.compile(p, re.I), n) for p, n in _OM_ARM_FULL]

# Otitis-media continuous outcomes; none log-normal.
_OM_CONTINUOUS = {"HEARING_LEVEL", "EAR_PAIN"}
_OM_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_OM_ENDPOINT_PATTERNS,
                                arm_compiled=_OM_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_OM_ENDPOINT_PATTERNS,
                               arm_compiled=_OM_ARM_COMPILED,
                               continuous_endpoints=_OM_CONTINUOUS,
                               lognormal_endpoints=_OM_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_OM_ENDPOINT_PATTERNS,
                              arm_compiled=_OM_ARM_COMPILED,
                              continuous_endpoints=_OM_CONTINUOUS,
                              lognormal_endpoints=_OM_LOGNORMAL)
