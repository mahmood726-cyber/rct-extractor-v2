"""
Arm-level / 2x2 + continuous extraction for melanoma trials.
Thin wrapper over the shared malaria_arm_data engine, configured with melanoma
endpoints and checkpoint-inhibitor / BRAF-MEK arm labels.
"""
import re
from typing import Dict, List

from .melanoma import get_melanoma_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_ME_ENDPOINT_PATTERNS = []
for _sub in ("systemic", "adjuvant", "neoadjuvant", "mortality"):
    _ME_ENDPOINT_PATTERNS.extend(get_melanoma_endpoint_patterns(_sub))

_ME_ARM_FULL = [
    (r"nivolumab(?:[- /]+(?:and\s+|plus\s+)?ipilimumab)?|opdivo", "nivolumab"),
    (r"ipilimumab|yervoy", "ipilimumab"),
    (r"pembrolizumab|keytruda", "pembrolizumab"),
    (r"relatlimab", "relatlimab"),
    (r"dabrafenib(?:[- /]+(?:and\s+|plus\s+)?trametinib)?|tafinlar", "dabrafenib-trametinib"),
    (r"encorafenib(?:[- /]+(?:and\s+|plus\s+)?binimetinib)?|braftovi", "encorafenib-binimetinib"),
    (r"vemurafenib(?:[- /]+(?:and\s+|plus\s+)?cobimetinib)?", "vemurafenib-cobimetinib"),
    (r"trametinib|mekinist", "trametinib"),
    (r"dacarbazine", "dacarbazine"),
    (r"interferon(?:[- ]alpha|[- ]alfa)?", "interferon"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"observation(?:\s+(?:group|arm|alone))?", "observation"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_ME_ARM_ABBREV = []
_ME_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _ME_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _ME_ARM_ABBREV])

_ME_CONTINUOUS = {"LDH_LEVEL", "QOL"}
_ME_LOGNORMAL = {"LDH_LEVEL"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_ME_ENDPOINT_PATTERNS,
                                arm_compiled=_ME_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_ME_ENDPOINT_PATTERNS,
                               arm_compiled=_ME_ARM_COMPILED,
                               continuous_endpoints=_ME_CONTINUOUS,
                               lognormal_endpoints=_ME_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_ME_ENDPOINT_PATTERNS,
                              arm_compiled=_ME_ARM_COMPILED,
                              continuous_endpoints=_ME_CONTINUOUS,
                              lognormal_endpoints=_ME_LOGNORMAL)
