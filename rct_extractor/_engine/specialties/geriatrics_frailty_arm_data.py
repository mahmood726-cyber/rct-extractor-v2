"""
Arm-level / 2x2 + continuous extraction for geriatrics / frailty trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
geriatrics/frailty endpoints and geriatric-intervention arm labels:

  binary/rate (falls, fallers, fall injury, delirium, frailty, mortality,
    hospitalisation, institutionalisation) -> 2x2 events/N per arm.
  continuous (cognitive function, physical performance, ADL) -> mean+SD /
    median+IQR, pooled as MD/SMD on the natural scale.
"""
import re
from typing import Dict, List

from .geriatrics_frailty import get_geriatrics_frailty_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_GF_ENDPOINT_PATTERNS = []
for _sub in ("falls", "cognition", "function", "outcomes"):
    _GF_ENDPOINT_PATTERNS.extend(get_geriatrics_frailty_endpoint_patterns(_sub))

# Geriatric-intervention arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE.
_GF_ARM_FULL = [
    (r"comprehensive\s+geriatric\s+assessment", "comprehensive-geriatric-assessment"),
    (r"(?:supervised\s+|progressive\s+|resistance\s+)?exercise(?:\s+(?:programme|program|training))?|"
     r"physical\s+activity", "exercise"),
    (r"multifactorial\s+intervention|multicomponent\s+intervention|multidomain\s+intervention",
     "multicomponent-intervention"),
    (r"vitamin\s+d(?:3)?|cholecalciferol", "vitamin-d"),
    (r"medication\s+review|deprescribing|pharmacist[- ]led\s+review", "medication-review"),
    (r"(?:oral\s+)?nutritional\s+supplement(?:ation)?|protein\s+supplement(?:ation)?", "nutritional-supplement"),
    (r"home[- ](?:based\s+)?(?:visit|assessment)|occupational\s+therapy", "home-intervention"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"usual\s+care|standard\s+(?:of\s+)?care|routine\s+care", "usual-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_GF_ARM_ABBREV = [
    (r"\bCGA\b", "comprehensive-geriatric-assessment"),
]
_GF_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _GF_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _GF_ARM_ABBREV])

# Geriatrics/frailty continuous outcomes (natural scale).
_GF_CONTINUOUS = {"COGNITIVE_FUNCTION", "PHYSICAL_FUNCTION", "ADL"}
_GF_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_GF_ENDPOINT_PATTERNS,
                                arm_compiled=_GF_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_GF_ENDPOINT_PATTERNS,
                               arm_compiled=_GF_ARM_COMPILED,
                               continuous_endpoints=_GF_CONTINUOUS,
                               lognormal_endpoints=_GF_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_GF_ENDPOINT_PATTERNS,
                              arm_compiled=_GF_ARM_COMPILED,
                              continuous_endpoints=_GF_CONTINUOUS,
                              lognormal_endpoints=_GF_LOGNORMAL)
