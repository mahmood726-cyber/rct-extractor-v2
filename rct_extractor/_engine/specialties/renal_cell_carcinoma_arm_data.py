"""
Arm-level / 2x2 + continuous extraction for renal-cell-carcinoma trials.
Thin wrapper over the shared malaria_arm_data engine, configured with RCC
endpoints and VEGF-TKI / checkpoint-combination arm labels.
"""
import re
from typing import Dict, List

from .renal_cell_carcinoma import get_renal_cell_carcinoma_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_RC_ENDPOINT_PATTERNS = []
for _sub in ("advanced", "adjuvant", "subsequent_line", "mortality"):
    _RC_ENDPOINT_PATTERNS.extend(get_renal_cell_carcinoma_endpoint_patterns(_sub))

_RC_ARM_FULL = [
    (r"ipilimumab(?:[- /]+(?:and\s+|plus\s+)?nivolumab)?|nivo[- ]?ipi", "ipilimumab-nivolumab"),
    (r"pembrolizumab(?:[- /]+(?:and\s+|plus\s+)?axitinib)?|keytruda", "pembrolizumab-axitinib"),
    (r"lenvatinib(?:[- /]+(?:and\s+|plus\s+)?pembrolizumab)?|lenvima", "lenvatinib-pembrolizumab"),
    (r"cabozantinib(?:[- /]+(?:and\s+|plus\s+)?nivolumab)?|cabometyx", "cabozantinib-nivolumab"),
    (r"nivolumab|opdivo", "nivolumab"),
    (r"sunitinib|sutent", "sunitinib"),
    (r"pazopanib|votrient", "pazopanib"),
    (r"axitinib|inlyta", "axitinib"),
    (r"everolimus|afinitor", "everolimus"),
    (r"tivozanib|fotivda", "tivozanib"),
    (r"belzutifan|welireg", "belzutifan"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+(?:chemo)?therapy", "standard-of-care"),
    (r"observation(?:\s+(?:group|arm|alone))?", "observation"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_RC_ARM_ABBREV = []
_RC_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _RC_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _RC_ARM_ABBREV])

_RC_CONTINUOUS = set()
_RC_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_RC_ENDPOINT_PATTERNS,
                                arm_compiled=_RC_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_RC_ENDPOINT_PATTERNS,
                               arm_compiled=_RC_ARM_COMPILED,
                               continuous_endpoints=_RC_CONTINUOUS,
                               lognormal_endpoints=_RC_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_RC_ENDPOINT_PATTERNS,
                              arm_compiled=_RC_ARM_COMPILED,
                              continuous_endpoints=_RC_CONTINUOUS,
                              lognormal_endpoints=_RC_LOGNORMAL)
