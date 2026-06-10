"""
Arm-level / 2x2 + continuous extraction for ovarian-cancer trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data, configured with
ovarian-cancer endpoints and chemotherapy / anti-angiogenic / PARP-inhibitor /
surgical arm labels:

  binary outcomes (objective response, CA-125 response, complete cytoreduction,
    recurrence) -> 2x2 events/N per arm
  continuous (serum CA-125 -> log-normal, pool on the log scale; QoL -> MD).
"""
import re
from typing import Dict, List

from .ovarian_cancer import get_ovarian_cancer_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_OC_ENDPOINT_PATTERNS = []
for _sub in ("systemic", "maintenance", "surgical", "mortality"):
    _OC_ENDPOINT_PATTERNS.extend(get_ovarian_cancer_endpoint_patterns(_sub))

# Ovarian-cancer arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE.
_OC_ARM_FULL = [
    (r"olaparib|lynparza", "olaparib"),
    (r"niraparib|zejula", "niraparib"),
    (r"rucaparib|rubraca", "rucaparib"),
    (r"bevacizumab|avastin", "bevacizumab"),
    (r"carboplatin(?:[- /]+paclitaxel)?", "carboplatin-paclitaxel"),
    (r"cisplatin", "cisplatin"),
    (r"(?:pegylated\s+)?liposomal\s+doxorubicin|caelyx|doxil", "liposomal-doxorubicin"),
    (r"gemcitabine", "gemcitabine"),
    (r"topotecan", "topotecan"),
    (r"paclitaxel", "paclitaxel"),
    (r"primary\s+debulking\s+surgery", "primary-debulking"),
    (r"interval\s+debulking\s+surgery|neoadjuvant\s+chemotherapy", "neoadjuvant-interval-debulking"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_OC_ARM_ABBREV = [
    (r"\bPDS\b", "primary-debulking"),
    (r"\bIDS\b|\bNACT\b", "neoadjuvant-interval-debulking"),
]
_OC_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _OC_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _OC_ARM_ABBREV])

# Serum CA-125 is a tumour marker conventionally analysed on the log scale.
_OC_CONTINUOUS = {"CA125_LEVEL", "QOL"}
_OC_LOGNORMAL = {"CA125_LEVEL"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_OC_ENDPOINT_PATTERNS,
                                arm_compiled=_OC_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_OC_ENDPOINT_PATTERNS,
                               arm_compiled=_OC_ARM_COMPILED,
                               continuous_endpoints=_OC_CONTINUOUS,
                               lognormal_endpoints=_OC_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_OC_ENDPOINT_PATTERNS,
                              arm_compiled=_OC_ARM_COMPILED,
                              continuous_endpoints=_OC_CONTINUOUS,
                              lognormal_endpoints=_OC_LOGNORMAL)
