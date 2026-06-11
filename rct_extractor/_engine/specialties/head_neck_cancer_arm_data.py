"""
Arm-level / 2x2 + continuous extraction for head-and-neck-cancer trials.
Thin wrapper over the shared malaria_arm_data engine, configured with HNSCC/NPC
endpoints and chemoradiation / immunotherapy / targeted arm labels.
"""
import re
from typing import Dict, List

from .head_neck_cancer import get_head_neck_cancer_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_HN_ENDPOINT_PATTERNS = []
for _sub in ("definitive", "recurrent_metastatic", "nasopharyngeal", "mortality"):
    _HN_ENDPOINT_PATTERNS.extend(get_head_neck_cancer_endpoint_patterns(_sub))

_HN_ARM_FULL = [
    (r"pembrolizumab|keytruda", "pembrolizumab"),
    (r"nivolumab|opdivo", "nivolumab"),
    (r"cetuximab(?:[- /]+radi\w*)?|erbitux", "cetuximab"),
    (r"cisplatin(?:[- /]+radi\w*)?", "cisplatin"),
    (r"carboplatin", "carboplatin"),
    (r"gemcitabine(?:[- /]+(?:and\s+)?cisplatin)?", "gemcitabine-cisplatin"),
    (r"docetaxel[- ,/]+cisplatin[- ,/]+(?:5[- ]?fu|fluorouracil)|\btpf\b", "tpf"),
    (r"fluorouracil|5[- ]?fu", "fluorouracil"),
    (r"radi(?:o)?therapy\s+alone|radiation\s+alone", "radiotherapy-alone"),
    (r"external[- ]beam\s+radi\w*|intensity[- ]modulated\s+radi\w*|radiotherapy", "radiotherapy"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+(?:chemo)?therapy", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_HN_ARM_ABBREV = [
    (r"\bTPF\b", "tpf"),
    (r"\bIMRT\b|\bEBRT\b", "radiotherapy"),
]
_HN_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _HN_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _HN_ARM_ABBREV])

_HN_CONTINUOUS = set()
_HN_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_HN_ENDPOINT_PATTERNS,
                                arm_compiled=_HN_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_HN_ENDPOINT_PATTERNS,
                               arm_compiled=_HN_ARM_COMPILED,
                               continuous_endpoints=_HN_CONTINUOUS,
                               lognormal_endpoints=_HN_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_HN_ENDPOINT_PATTERNS,
                              arm_compiled=_HN_ARM_COMPILED,
                              continuous_endpoints=_HN_CONTINUOUS,
                              lognormal_endpoints=_HN_LOGNORMAL)
