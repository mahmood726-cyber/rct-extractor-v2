"""
Arm-level / 2x2 + continuous extraction for leukaemia trials.
Thin wrapper over the shared malaria_arm_data engine, configured with leukaemia
endpoints and AML / ALL / CLL / CML drug arm labels. Leukaemia endpoints are
predominantly binary (CR, MRD negativity, molecular/cytogenetic response, relapse)
or time-to-event; no disease-specific continuous outcome is configured.
"""
import re
from typing import Dict, List

from .leukaemia import get_leukaemia_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_LK_ENDPOINT_PATTERNS = []
for _sub in ("aml", "all", "cll", "cml"):
    _LK_ENDPOINT_PATTERNS.extend(get_leukaemia_endpoint_patterns(_sub))

_LK_ARM_FULL = [
    (r"venetoclax(?:[- /]+(?:and\s+|plus\s+)?azacitidine)?", "venetoclax"),
    (r"azacitidine|decitabine", "azacitidine"),
    (r"ibrutinib", "ibrutinib"),
    (r"acalabrutinib", "acalabrutinib"),
    (r"zanubrutinib", "zanubrutinib"),
    (r"obinutuzumab", "obinutuzumab"),
    (r"rituximab", "rituximab"),
    (r"blinatumomab", "blinatumomab"),
    (r"inotuzumab(?:\s+ozogamicin)?", "inotuzumab"),
    (r"tisagenlecleucel|car[- ]?t(?:\s+cell)?(?:\s+therapy)?", "car-t"),
    (r"midostaurin|gilteritinib|quizartinib", "flt3-inhibitor"),
    (r"gemtuzumab(?:\s+ozogamicin)?", "gemtuzumab"),
    (r"cpx[- ]?351|vyxeos", "cpx-351"),
    (r"imatinib|gleevec|glivec", "imatinib"),
    (r"dasatinib", "dasatinib"),
    (r"nilotinib", "nilotinib"),
    (r"bosutinib", "bosutinib"),
    (r"ponatinib", "ponatinib"),
    (r"asciminib", "asciminib"),
    (r"chlorambucil", "chlorambucil"),
    (r"cytarabine(?:[- /]+(?:and\s+)?daunorubicin)?|\b7\s*\+\s*3\b", "7+3"),
    (r"\bfcr\b|fludarabine[- ,/]+cyclophosphamide[- ,/]+rituximab", "fcr"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+(?:chemo)?therapy", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_LK_ARM_ABBREV = [
    (r"\bFCR\b", "fcr"),
    (r"\bCAR[- ]?T\b", "car-t"),
]
_LK_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _LK_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _LK_ARM_ABBREV])

_LK_CONTINUOUS = set()
_LK_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_LK_ENDPOINT_PATTERNS,
                                arm_compiled=_LK_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_LK_ENDPOINT_PATTERNS,
                               arm_compiled=_LK_ARM_COMPILED,
                               continuous_endpoints=_LK_CONTINUOUS,
                               lognormal_endpoints=_LK_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_LK_ENDPOINT_PATTERNS,
                              arm_compiled=_LK_ARM_COMPILED,
                              continuous_endpoints=_LK_CONTINUOUS,
                              lognormal_endpoints=_LK_LOGNORMAL)
