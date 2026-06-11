"""
Arm-level / 2x2 + continuous extraction for lymphoma trials.
Thin wrapper over the shared malaria_arm_data engine, configured with lymphoma
endpoints and immunochemotherapy / CAR-T arm labels. Lymphoma endpoints are
binary (CR, ORR, relapse) or time-to-event; no continuous outcome configured.
"""
import re
from typing import Dict, List

from .lymphoma import get_lymphoma_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_LY_ENDPOINT_PATTERNS = []
for _sub in ("hodgkin", "aggressive", "indolent", "mortality"):
    _LY_ENDPOINT_PATTERNS.extend(get_lymphoma_endpoint_patterns(_sub))

_LY_ARM_FULL = [
    (r"brentuximab(?:\s+vedotin)?(?:[- /]+avd)?|bv[- ]?avd|adcetris", "brentuximab-avd"),
    (r"\babvd\b", "abvd"),
    (r"escalated\s+beacopp|\bbeacopp\b", "beacopp"),
    (r"polatuzumab(?:\s+vedotin)?|pola[- ]?r[- ]?chp", "pola-r-chp"),
    (r"\br[- ]?chop\b|rituximab[- ,/]+cyclophosphamide", "r-chop"),
    (r"axicabtagene(?:\s+ciloleucel)?|axi[- ]?cel", "axi-cel"),
    (r"tisagenlecleucel|tisa[- ]?cel", "tisa-cel"),
    (r"lisocabtagene(?:\s+maraleucel)?|liso[- ]?cel", "liso-cel"),
    (r"tafasitamab", "tafasitamab"),
    (r"obinutuzumab", "obinutuzumab"),
    (r"bendamustine", "bendamustine"),
    (r"lenalidomide", "lenalidomide"),
    (r"nivolumab|pembrolizumab", "checkpoint-inhibitor"),
    (r"rituximab", "rituximab"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+(?:chemo)?(?:immuno)?therapy", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_LY_ARM_ABBREV = [
    (r"\bABVD\b", "abvd"),
    (r"\bR-?CHOP\b", "r-chop"),
    (r"\bBEACOPP\b", "beacopp"),
]
_LY_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _LY_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _LY_ARM_ABBREV])

_LY_CONTINUOUS = set()
_LY_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_LY_ENDPOINT_PATTERNS,
                                arm_compiled=_LY_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_LY_ENDPOINT_PATTERNS,
                               arm_compiled=_LY_ARM_COMPILED,
                               continuous_endpoints=_LY_CONTINUOUS,
                               lognormal_endpoints=_LY_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_LY_ENDPOINT_PATTERNS,
                              arm_compiled=_LY_ARM_COMPILED,
                              continuous_endpoints=_LY_CONTINUOUS,
                              lognormal_endpoints=_LY_LOGNORMAL)
