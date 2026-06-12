"""
Arm-level / 2x2 + continuous extraction for thyroid cancer trials.
Thin wrapper over the shared malaria_arm_data engine, configured with thyroid
cancer endpoints and kinase-inhibitor / radioiodine arm labels (lenvatinib /
sorafenib / cabozantinib / selpercatinib). Thyroid cancer endpoints are
time-to-event or binary (objective response); no continuous outcome configured.
"""
import re
from typing import Dict, List

from .thyroid_cancer import get_thyroid_cancer_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_TC_ENDPOINT_PATTERNS = []
for _sub in ("differentiated", "medullary", "anaplastic", "mortality"):
    _TC_ENDPOINT_PATTERNS.extend(get_thyroid_cancer_endpoint_patterns(_sub))

_TC_ARM_FULL = [
    (r"lenvatinib|lenvima", "lenvatinib"),
    (r"sorafenib|nexavar", "sorafenib"),
    (r"selpercatinib|retevmo", "selpercatinib"),
    (r"pralsetinib|gavreto", "pralsetinib"),
    (r"vandetanib|caprelsa", "vandetanib"),
    (r"cabozantinib|cabometyx", "cabozantinib"),
    (r"dabrafenib[, /-]+trametinib|dabrafenib", "dabrafenib"),
    (r"trametinib", "trametinib"),
    (r"radioactive\s+iodine|radioiodine|\bi[- ]?131\b|\brai\b", "radioiodine"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+therapy", "standard-of-care"),
    (r"best\s+supportive\s+care|\bbsc\b", "supportive-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_TC_ARM_ABBREV = [
    (r"\bRAI\b", "radioiodine"),
    (r"\bBSC\b", "supportive-care"),
]
_TC_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _TC_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _TC_ARM_ABBREV])

_TC_CONTINUOUS = set()
_TC_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_TC_ENDPOINT_PATTERNS,
                                arm_compiled=_TC_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_TC_ENDPOINT_PATTERNS,
                               arm_compiled=_TC_ARM_COMPILED,
                               continuous_endpoints=_TC_CONTINUOUS,
                               lognormal_endpoints=_TC_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_TC_ENDPOINT_PATTERNS,
                              arm_compiled=_TC_ARM_COMPILED,
                              continuous_endpoints=_TC_CONTINUOUS,
                              lognormal_endpoints=_TC_LOGNORMAL)
