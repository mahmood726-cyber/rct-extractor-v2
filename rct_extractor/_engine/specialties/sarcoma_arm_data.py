"""
Arm-level / 2x2 + continuous extraction for soft-tissue sarcoma trials.
Thin wrapper over the shared malaria_arm_data engine, configured with sarcoma
endpoints and cytotoxic / tyrosine-kinase-inhibitor arm labels (doxorubicin /
pazopanib / imatinib / regorafenib). Sarcoma endpoints are time-to-event or
binary (objective response); no continuous outcome configured.
"""
import re
from typing import Dict, List

from .sarcoma import get_sarcoma_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_SA_ENDPOINT_PATTERNS = []
for _sub in ("advanced", "gist", "localized", "mortality"):
    _SA_ENDPOINT_PATTERNS.extend(get_sarcoma_endpoint_patterns(_sub))

_SA_ARM_FULL = [
    (r"doxorubicin[, /-]+ifosfamide|ifosfamide[, /-]+doxorubicin", "doxorubicin-ifosfamide"),
    (r"doxorubicin|adriamycin", "doxorubicin"),
    (r"ifosfamide", "ifosfamide"),
    (r"pazopanib|votrient", "pazopanib"),
    (r"trabectedin|yondelis", "trabectedin"),
    (r"eribulin|halaven", "eribulin"),
    (r"olaratumab", "olaratumab"),
    (r"imatinib|gleevec|glivec", "imatinib"),
    (r"sunitinib|sutent", "sunitinib"),
    (r"regorafenib|stivarga", "regorafenib"),
    (r"ripretinib|qinlock", "ripretinib"),
    (r"avapritinib|ayvakit", "avapritinib"),
    (r"radiotherapy|radiation\s+therapy", "radiotherapy"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+(?:chemo)?therapy", "standard-of-care"),
    (r"best\s+supportive\s+care|\bbsc\b", "supportive-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_SA_ARM_ABBREV = [
    (r"\bGIST\b", "gist-cohort"),
    (r"\bBSC\b", "supportive-care"),
]
_SA_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _SA_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _SA_ARM_ABBREV])

_SA_CONTINUOUS = set()
_SA_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_SA_ENDPOINT_PATTERNS,
                                arm_compiled=_SA_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_SA_ENDPOINT_PATTERNS,
                               arm_compiled=_SA_ARM_COMPILED,
                               continuous_endpoints=_SA_CONTINUOUS,
                               lognormal_endpoints=_SA_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_SA_ENDPOINT_PATTERNS,
                              arm_compiled=_SA_ARM_COMPILED,
                              continuous_endpoints=_SA_CONTINUOUS,
                              lognormal_endpoints=_SA_LOGNORMAL)
