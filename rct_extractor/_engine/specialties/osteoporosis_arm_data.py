"""
Arm-level / 2x2 + continuous extraction for osteoporosis trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
osteoporosis endpoints and bone-therapy drug-class arm labels:

  binary (vertebral / non-vertebral / hip / clinical / any fracture, ONJ, atypical
    femoral fracture, hypocalcaemia) -> 2x2 events/N per arm.
  continuous (lumbar-spine / total-hip / femoral-neck BMD percent change, CTX,
    P1NP) -> mean+SD / median+IQR, pooled as MD/SMD on the natural scale.
"""
import re
from typing import Dict, List

from .osteoporosis import get_osteoporosis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_OST_ENDPOINT_PATTERNS = []
for _sub in ("fracture", "bmd", "bone_turnover", "safety"):
    _OST_ENDPOINT_PATTERNS.extend(get_osteoporosis_endpoint_patterns(_sub))

# Bone-therapy drug-class arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE.
_OST_ARM_FULL = [
    # bisphosphonates
    (r"alendronate", "alendronate"),
    (r"risedronate", "risedronate"),
    (r"ibandronate", "ibandronate"),
    (r"zoledronic\s+acid|zoledronate", "zoledronic-acid"),
    (r"pamidronate", "pamidronate"),
    (r"bisphosphonate", "bisphosphonate"),
    # biologics / anabolics
    (r"denosumab", "denosumab"),
    (r"teriparatide", "teriparatide"),
    (r"abaloparatide", "abaloparatide"),
    (r"romosozumab", "romosozumab"),
    # SERMs / other
    (r"raloxifene", "raloxifene"),
    (r"bazedoxifene", "bazedoxifene"),
    (r"strontium\s+ranelate", "strontium-ranelate"),
    (r"calcitonin", "calcitonin"),
    (r"hormone\s+(?:replacement\s+)?therapy|estrogen|oestrogen", "hormone-therapy"),
    (r"calcium(?:\s+and\s+|\s*\+\s*|\s+plus\s+)?(?:and\s+)?vitamin\s+d|vitamin\s+d", "calcium-vitamin-d"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_OST_ARM_ABBREV = [
    (r"\bHRT\b", "hormone-therapy"),
    (r"\bZOL\b", "zoledronic-acid"),
]
_OST_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _OST_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _OST_ARM_ABBREV])

# Osteoporosis continuous outcomes (BMD percent change + bone-turnover markers).
_OST_CONTINUOUS = {"BMD_LUMBAR_SPINE", "BMD_TOTAL_HIP", "BMD_FEMORAL_NECK", "CTX", "P1NP"}
_OST_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_OST_ENDPOINT_PATTERNS,
                                arm_compiled=_OST_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_OST_ENDPOINT_PATTERNS,
                               arm_compiled=_OST_ARM_COMPILED,
                               continuous_endpoints=_OST_CONTINUOUS,
                               lognormal_endpoints=_OST_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_OST_ENDPOINT_PATTERNS,
                              arm_compiled=_OST_ARM_COMPILED,
                              continuous_endpoints=_OST_CONTINUOUS,
                              lognormal_endpoints=_OST_LOGNORMAL)
