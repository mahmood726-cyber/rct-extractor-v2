"""
Arm-level / 2x2 + continuous extraction for lymphatic filariasis (LF /
elephantiasis) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with LF endpoints
and antifilarial / MDA arm labels:

  binary outcomes (microfilaria clearance, antigen clearance, mf / antigen
    prevalence, lymphoedema, hydrocele, adverse events) -> 2x2 events/N per arm
  continuous (limb volume -> mean+SD / median+IQR; microfilaria density is
    strongly right-skewed -> log-normal, pool on the log scale as a GMR).

LF MDA regimens are combinations, so the arm labels include the standard
two-drug DA (DEC+albendazole) and IA (ivermectin+albendazole) and the WHO
triple-drug IDA (ivermectin+DEC+albendazole), as well as the single agents,
DEC-medicated salt and the anti-Wolbachia macrofilaricide doxycycline.
"""
import re
from typing import Dict, List

from .lymphatic_filariasis import get_lymphatic_filariasis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# LF endpoint patterns (string, endpoint) across all subspecialties.
_LF_ENDPOINT_PATTERNS = []
for _sub in ("mda", "transmission", "morbidity", "safety"):
    _LF_ENDPOINT_PATTERNS.extend(get_lymphatic_filariasis_endpoint_patterns(_sub))

# Antifilarial / MDA arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
# Combination regimens are listed BEFORE single agents so the longest / most
# specific arm label wins.
_LF_ARM_FULL = [
    # triple-drug regimen (IDA)
    (r"ivermectin[- +,]+(?:plus\s+)?dec[- +,]+(?:plus\s+)?albendazole|"
     r"ivermectin[- +,]+(?:plus\s+)?diethylcarbamazine[- +,]+(?:plus\s+)?albendazole|"
     r"triple[- ]drug(?:\s+therapy)?|triple\s+therapy", "IDA"),
    # two-drug regimens
    (r"diethylcarbamazine[- +,]+(?:plus\s+)?albendazole|dec[- +,]+(?:plus\s+)?albendazole",
     "DA"),
    (r"ivermectin[- +,]+(?:plus\s+)?albendazole", "IA"),
    # DEC-medicated salt
    (r"dec[- ]medicated\s+salt|diethylcarbamazine[- ]medicated\s+salt|"
     r"medicated\s+salt", "dec-medicated-salt"),
    # single agents
    (r"diethylcarbamazine", "diethylcarbamazine"),
    (r"albendazole", "albendazole"),
    (r"ivermectin", "ivermectin"),
    (r"doxycycline", "doxycycline"),
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"untreated(?:\s+(?:group|arm|control))?", "untreated"),
    (r"no\s+treatment", "untreated"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_LF_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bIDA\b", "IDA"),
    (r"\bDEC\b", "diethylcarbamazine"),
    (r"\bALB\b|\bABZ\b", "albendazole"),
    (r"\bIVM\b", "ivermectin"),
    (r"\bDA\b", "DA"),
    (r"\bIA\b", "IA"),
]
_LF_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _LF_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _LF_ARM_ABBREV])

# LF continuous outcomes; microfilaria density is strongly right-skewed and
# pooled on the log scale (geometric mean ratio).
_LF_CONTINUOUS = {"MF_DENSITY", "LIMB_VOLUME"}
_LF_LOGNORMAL = {"MF_DENSITY"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_LF_ENDPOINT_PATTERNS,
                                arm_compiled=_LF_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_LF_ENDPOINT_PATTERNS,
                               arm_compiled=_LF_ARM_COMPILED,
                               continuous_endpoints=_LF_CONTINUOUS,
                               lognormal_endpoints=_LF_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_LF_ENDPOINT_PATTERNS,
                              arm_compiled=_LF_ARM_COMPILED,
                              continuous_endpoints=_LF_CONTINUOUS,
                              lognormal_endpoints=_LF_LOGNORMAL)
