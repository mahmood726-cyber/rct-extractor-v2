"""
Arm-level / 2x2 + continuous extraction for typhoid (enteric fever) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with typhoid
endpoints and antibiotic / vaccine arm labels:

  binary outcomes (clinical cure, microbiological cure, treatment failure,
    relapse, faecal carriage, perforation, MDR) -> 2x2 events/N per arm
  continuous (fever clearance time, hospital stay -> mean+SD / median+IQR;
    anti-Vi titre -> log-normal, pool on the log scale).
"""
import re
from typing import Dict, List

from .typhoid import get_typhoid_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Typhoid endpoint patterns (string, endpoint) across all subspecialties.
_TYPHOID_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "vaccine", "resistance", "complications"):
    _TYPHOID_ENDPOINT_PATTERNS.extend(get_typhoid_endpoint_patterns(_sub))

# Antibiotic / vaccine arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_TYPHOID_ARM_FULL = [
    (r"azithromycin", "azithromycin"),
    (r"ciprofloxacin", "ciprofloxacin"),
    (r"ofloxacin", "ofloxacin"),
    (r"gatifloxacin", "gatifloxacin"),
    (r"levofloxacin", "levofloxacin"),
    (r"norfloxacin", "norfloxacin"),
    (r"pefloxacin", "pefloxacin"),
    (r"ceftriaxone", "ceftriaxone"),
    (r"cefixime", "cefixime"),
    (r"cefotaxime", "cefotaxime"),
    (r"chloramphenicol", "chloramphenicol"),
    (r"amoxicillin", "amoxicillin"),
    (r"ampicillin", "ampicillin"),
    (r"co[- ]?trimoxazole|trimethoprim[- ]sulfamethoxazole", "co-trimoxazole"),
    # vaccines
    (r"typhoid\s+conjugate\s+vaccine|\bvi[- ]tt\b|\bvi[- ]dt\b", "typhoid-conjugate-vaccine"),
    (r"vi\s+polysaccharide|\bvi[- ]ps\b|\bvips\b", "vi-polysaccharide"),
    (r"ty21a", "ty21a"),
    (r"meningococcal\s+(?:conjugate\s+)?vaccine", "control-vaccine"),
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_TYPHOID_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bTCV\b", "typhoid-conjugate-vaccine"),
    (r"\bCIP\b", "ciprofloxacin"),
    (r"\bOFX\b", "ofloxacin"),
    (r"\bGAT\b", "gatifloxacin"),
    (r"\bCRO\b", "ceftriaxone"),
    (r"\bAZM\b|\bAZI\b", "azithromycin"),
]
_TYPHOID_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _TYPHOID_ARM_FULL]
                         + [(re.compile(p), n) for p, n in _TYPHOID_ARM_ABBREV])

# Typhoid continuous outcomes; anti-Vi titre (immunogenicity) is log-normal.
_TYPHOID_CONTINUOUS = {"FEVER_CLEARANCE_TIME", "HOSPITAL_STAY", "IMMUNOGENICITY"}
_TYPHOID_LOGNORMAL = {"IMMUNOGENICITY"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_TYPHOID_ENDPOINT_PATTERNS,
                                arm_compiled=_TYPHOID_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_TYPHOID_ENDPOINT_PATTERNS,
                               arm_compiled=_TYPHOID_ARM_COMPILED,
                               continuous_endpoints=_TYPHOID_CONTINUOUS,
                               lognormal_endpoints=_TYPHOID_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_TYPHOID_ENDPOINT_PATTERNS,
                              arm_compiled=_TYPHOID_ARM_COMPILED,
                              continuous_endpoints=_TYPHOID_CONTINUOUS,
                              lognormal_endpoints=_TYPHOID_LOGNORMAL)
