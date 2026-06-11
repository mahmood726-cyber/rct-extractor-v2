"""
Arm-level / 2x2 + continuous extraction for immune thrombocytopenia (ITP) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
ITP endpoints and immunotherapy / TPO-RA arm labels:

  binary outcomes (platelet response, complete / durable response, bleeding,
    rescue therapy, relapse, splenectomy avoidance) -> 2x2 events/N per arm;
  continuous outcomes (platelet count, time to response) -> per-arm mean+SD
    (Wan IQR->SD).

Comparisons are typically drug-vs-placebo (eltrombopag, romiplostim, rituximab,
fostamatinib) or regimen-vs-regimen (dexamethasone vs prednisone, IVIG vs steroids).
"""
import re
from typing import Dict, List

from .itp import get_itp_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_ITP_ENDPOINT_PATTERNS = []
for _sub in ("first_line", "tpo_ra", "second_line", "paediatric"):
    _ITP_ENDPOINT_PATTERNS.extend(get_itp_endpoint_patterns(_sub))

_ITP_ARM_FULL = [
    (r"eltrombopag", "eltrombopag"),
    (r"romiplostim", "romiplostim"),
    (r"avatrombopag", "avatrombopag"),
    (r"hetrombopag", "hetrombopag"),
    (r"lusutrombopag", "lusutrombopag"),
    (r"rituximab", "rituximab"),
    (r"fostamatinib", "fostamatinib"),
    (r"efgartigimod", "efgartigimod"),
    (r"rozanolixizumab", "rozanolixizumab"),
    (r"high[- ]dose\s+dexamethasone|dexamethasone", "dexamethasone"),
    (r"prednis(?:on|olon)e", "prednisone"),
    (r"intravenous\s+immunoglobulin|\bivig\b", "IVIG"),
    (r"anti[- ]d\s+immunoglobulin|anti[- ]d", "anti-D"),
    (r"mycophenolate", "mycophenolate"),
    (r"azathioprine", "azathioprine"),
    (r"splenectomy", "splenectomy"),
    (r"\bplacebo\b", "placebo"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care|standard\s+(?:treatment|therapy)",
     "standard-of-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_ITP_ARM_ABBREV = [   # case-sensitive
    (r"\bIVIG\b|\bIVIg\b", "IVIG"),
    (r"\bTPO-RA\b", "TPO-RA"),
    (r"\bHD-DXM\b|\bHDD\b", "dexamethasone"),
    (r"\bMMF\b", "mycophenolate"),
]
_ITP_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _ITP_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _ITP_ARM_ABBREV])

# Continuous (mean+SD poolable) ITP endpoints. Platelet count is right-skewed;
# treat as log-normal to flag for Wan/geometric handling.
_ITP_CONTINUOUS = {
    "PLATELET_COUNT", "TIME_TO_RESPONSE",
}
_ITP_LOGNORMAL = {"PLATELET_COUNT"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_ITP_ENDPOINT_PATTERNS,
                                arm_compiled=_ITP_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_ITP_ENDPOINT_PATTERNS,
                               arm_compiled=_ITP_ARM_COMPILED,
                               continuous_endpoints=_ITP_CONTINUOUS,
                               lognormal_endpoints=_ITP_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_ITP_ENDPOINT_PATTERNS,
                              arm_compiled=_ITP_ARM_COMPILED,
                              continuous_endpoints=_ITP_CONTINUOUS,
                              lognormal_endpoints=_ITP_LOGNORMAL)
