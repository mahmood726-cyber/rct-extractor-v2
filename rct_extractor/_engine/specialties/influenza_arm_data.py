"""
Arm-level / 2x2 + continuous extraction for influenza trials.
Thin wrapper over the shared malaria_arm_data engine, configured with influenza
endpoints and antiviral / vaccine arm labels. Most influenza endpoints are binary
(laboratory-confirmed influenza, hospitalisation, complications); time to symptom
alleviation is configured as a continuous endpoint.
"""
import re
from typing import Dict, List

from .influenza import get_influenza_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_FLU_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "prevention", "complications", "mortality"):
    _FLU_ENDPOINT_PATTERNS.extend(get_influenza_endpoint_patterns(_sub))

_FLU_ARM_FULL = [
    (r"baloxavir(?:\s+marboxil)?|xofluza", "baloxavir"),
    (r"oseltamivir|tamiflu", "oseltamivir"),
    (r"zanamivir|relenza", "zanamivir"),
    (r"peramivir|rapivab", "peramivir"),
    (r"laninamivir", "laninamivir"),
    (r"(?:inactivated|quadrivalent|trivalent)\s+(?:influenza\s+)?vaccine|\biiv\b", "inactivated-vaccine"),
    (r"live[- ]attenuated\s+(?:influenza\s+)?vaccine|\blaiv\b", "live-vaccine"),
    (r"recombinant\s+(?:influenza\s+)?vaccine", "recombinant-vaccine"),
    (r"(?:influenza\s+)?vaccine", "vaccine"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+treatment|usual\s+care", "standard-of-care"),
    (r"no\s+(?:treatment|prophylaxis)|untreated", "no-treatment"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_FLU_ARM_ABBREV = [
    (r"\bLAIV\b", "live-vaccine"),
    (r"\bIIV\b", "inactivated-vaccine"),
]
_FLU_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _FLU_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _FLU_ARM_ABBREV])

# Time to symptom alleviation is a continuous (duration) endpoint.
_FLU_CONTINUOUS = {"TIME_TO_ALLEVIATION"}
_FLU_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_FLU_ENDPOINT_PATTERNS,
                                arm_compiled=_FLU_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_FLU_ENDPOINT_PATTERNS,
                               arm_compiled=_FLU_ARM_COMPILED,
                               continuous_endpoints=_FLU_CONTINUOUS,
                               lognormal_endpoints=_FLU_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_FLU_ENDPOINT_PATTERNS,
                              arm_compiled=_FLU_ARM_COMPILED,
                              continuous_endpoints=_FLU_CONTINUOUS,
                              lognormal_endpoints=_FLU_LOGNORMAL)
