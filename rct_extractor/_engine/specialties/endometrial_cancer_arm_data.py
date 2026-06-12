"""
Arm-level / 2x2 + continuous extraction for endometrial cancer trials.
Thin wrapper over the shared malaria_arm_data engine, configured with endometrial
cancer endpoints and chemotherapy / checkpoint-inhibitor / hormonal arm labels.
Endometrial cancer endpoints are time-to-event or binary (objective response);
no continuous outcome configured.
"""
import re
from typing import Dict, List

from .endometrial_cancer import get_endometrial_cancer_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_EC_ENDPOINT_PATTERNS = []
for _sub in ("advanced", "adjuvant", "immunotherapy", "mortality"):
    _EC_ENDPOINT_PATTERNS.extend(get_endometrial_cancer_endpoint_patterns(_sub))

_EC_ARM_FULL = [
    (r"pembrolizumab[, /-]+lenvatinib|lenvatinib[, /-]+pembrolizumab", "pembro-lenvatinib"),
    (r"carboplatin[, /-]+paclitaxel|paclitaxel[, /-]+carboplatin", "carboplatin-paclitaxel"),
    (r"dostarlimab|jemperli", "dostarlimab"),
    (r"pembrolizumab|keytruda", "pembrolizumab"),
    (r"durvalumab|imfinzi", "durvalumab"),
    (r"lenvatinib|lenvima", "lenvatinib"),
    (r"megestrol|medroxyprogesterone|progestin|hormonal\s+therapy", "hormonal"),
    (r"chemoradi(?:o|ation)?therapy|chemoradiation", "chemoradiotherapy"),
    (r"vaginal\s+brachytherapy", "brachytherapy"),
    (r"(?:pelvic\s+)?(?:external\s+beam\s+)?radiotherapy|radiation\s+therapy", "radiotherapy"),
    (r"carboplatin", "carboplatin"),
    (r"paclitaxel", "paclitaxel"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+(?:chemo)?therapy", "standard-of-care"),
    (r"observation", "observation"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_EC_ARM_ABBREV = [
    (r"\bEBRT\b", "radiotherapy"),
    (r"\bVBT\b", "brachytherapy"),
]
_EC_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _EC_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _EC_ARM_ABBREV])

_EC_CONTINUOUS = set()
_EC_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_EC_ENDPOINT_PATTERNS,
                                arm_compiled=_EC_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_EC_ENDPOINT_PATTERNS,
                               arm_compiled=_EC_ARM_COMPILED,
                               continuous_endpoints=_EC_CONTINUOUS,
                               lognormal_endpoints=_EC_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_EC_ENDPOINT_PATTERNS,
                              arm_compiled=_EC_ARM_COMPILED,
                              continuous_endpoints=_EC_CONTINUOUS,
                              lognormal_endpoints=_EC_LOGNORMAL)
