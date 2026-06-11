"""
Arm-level / 2x2 + continuous extraction for gastric-cancer trials.
Thin wrapper over the shared malaria_arm_data engine, configured with
gastric-cancer endpoints and chemo / targeted / immunotherapy arm labels.
"""
import re
from typing import Dict, List

from .gastric_cancer import get_gastric_cancer_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_GC_ENDPOINT_PATTERNS = []
for _sub in ("systemic", "perioperative", "surgical", "mortality"):
    _GC_ENDPOINT_PATTERNS.extend(get_gastric_cancer_endpoint_patterns(_sub))

_GC_ARM_FULL = [
    (r"trastuzumab\s+deruxtecan|enhertu", "trastuzumab-deruxtecan"),
    (r"trastuzumab|herceptin", "trastuzumab"),
    (r"nivolumab|opdivo", "nivolumab"),
    (r"pembrolizumab|keytruda", "pembrolizumab"),
    (r"ramucirumab|cyramza", "ramucirumab"),
    (r"\bflot\b", "flot"),
    (r"folfox", "folfox"),
    (r"capox|xelox|capecitabine[- ]oxaliplatin", "capox"),
    (r"cisplatin(?:[- /]+(?:and\s+)?fluorouracil|[- /]+5[- ]?fu)?", "cisplatin-fluorouracil"),
    (r"\bs-?1\b", "s-1"),
    (r"capecitabine", "capecitabine"),
    (r"d2\s+(?:lymphadenectomy|dissection|gastrectomy)", "d2"),
    (r"d1\s+(?:lymphadenectomy|dissection|gastrectomy)", "d1"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"chemotherapy\s+alone", "chemotherapy-alone"),
    (r"surgery\s+alone", "surgery-alone"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_GC_ARM_ABBREV = [
    (r"\bFLOT\b", "flot"),
]
_GC_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _GC_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _GC_ARM_ABBREV])

_GC_CONTINUOUS = {"QOL"}
_GC_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_GC_ENDPOINT_PATTERNS,
                                arm_compiled=_GC_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_GC_ENDPOINT_PATTERNS,
                               arm_compiled=_GC_ARM_COMPILED,
                               continuous_endpoints=_GC_CONTINUOUS,
                               lognormal_endpoints=_GC_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_GC_ENDPOINT_PATTERNS,
                              arm_compiled=_GC_ARM_COMPILED,
                              continuous_endpoints=_GC_CONTINUOUS,
                              lognormal_endpoints=_GC_LOGNORMAL)
