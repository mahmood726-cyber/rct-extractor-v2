"""
Arm-level / 2x2 + continuous extraction for oesophageal-cancer trials.
Thin wrapper over the shared malaria_arm_data engine, configured with oesophageal
endpoints and chemoradiation / immunotherapy / surgical arm labels.
"""
import re
from typing import Dict, List

from .oesophageal_cancer import get_oesophageal_cancer_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_OE_ENDPOINT_PATTERNS = []
for _sub in ("definitive", "adjuvant", "advanced", "mortality"):
    _OE_ENDPOINT_PATTERNS.extend(get_oesophageal_cancer_endpoint_patterns(_sub))

_OE_ARM_FULL = [
    (r"carboplatin[- ,/]+paclitaxel(?:[- ,/]+radi\w*)?", "carboplatin-paclitaxel"),
    (r"cisplatin[- ,/]+(?:5[- ]?fu|fluorouracil)", "cisplatin-fluorouracil"),
    (r"pembrolizumab|keytruda", "pembrolizumab"),
    (r"nivolumab|opdivo", "nivolumab"),
    (r"tislelizumab", "tislelizumab"),
    (r"\bflot\b", "flot"),
    (r"neoadjuvant\s+chemoradi\w*|chemoradi(?:o|ation)therapy", "chemoradiotherapy"),
    (r"(?:o?esophagectomy|esophagectomy)|surgery[\s-]+alone", "surgery"),
    (r"\bcross\s+regimen\b", "cross"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+(?:chemo)?therapy", "standard-of-care"),
    (r"surgery[\s-]+alone", "surgery-alone"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_OE_ARM_ABBREV = [
    (r"\bFLOT\b", "flot"),
    (r"\bCROSS\b", "cross"),
]
_OE_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _OE_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _OE_ARM_ABBREV])

_OE_CONTINUOUS = set()
_OE_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_OE_ENDPOINT_PATTERNS,
                                arm_compiled=_OE_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_OE_ENDPOINT_PATTERNS,
                               arm_compiled=_OE_ARM_COMPILED,
                               continuous_endpoints=_OE_CONTINUOUS,
                               lognormal_endpoints=_OE_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_OE_ENDPOINT_PATTERNS,
                              arm_compiled=_OE_ARM_COMPILED,
                              continuous_endpoints=_OE_CONTINUOUS,
                              lognormal_endpoints=_OE_LOGNORMAL)
