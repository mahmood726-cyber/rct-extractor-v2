"""
Arm-level / 2x2 + continuous extraction for bladder-cancer trials.
Thin wrapper over the shared malaria_arm_data engine, configured with bladder
endpoints and intravesical / chemo / immunotherapy arm labels.
"""
import re
from typing import Dict, List

from .bladder_cancer import get_bladder_cancer_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_BL_ENDPOINT_PATTERNS = []
for _sub in ("nmibc", "mibc", "advanced", "mortality"):
    _BL_ENDPOINT_PATTERNS.extend(get_bladder_cancer_endpoint_patterns(_sub))

_BL_ARM_FULL = [
    (r"bacillus\s+calmette[- ]gu[ée]rin|\bbcg\b", "bcg"),
    (r"mitomycin\s*c?", "mitomycin"),
    (r"pembrolizumab|keytruda", "pembrolizumab"),
    (r"atezolizumab|tecentriq", "atezolizumab"),
    (r"avelumab|bavencio", "avelumab"),
    (r"nivolumab|opdivo", "nivolumab"),
    (r"enfortumab(?:\s+vedotin)?|padcev", "enfortumab-vedotin"),
    (r"sacituzumab(?:\s+govitecan)?", "sacituzumab"),
    (r"gemcitabine(?:[- /]+(?:and\s+)?cisplatin)?", "gemcitabine-cisplatin"),
    (r"\bddmvac\b|\bmvac\b", "mvac"),
    (r"cisplatin", "cisplatin"),
    (r"radical\s+cystectomy", "cystectomy"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+(?:chemo)?therapy", "standard-of-care"),
    (r"observation(?:\s+(?:group|arm|alone))?", "observation"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_BL_ARM_ABBREV = [
    (r"\bBCG\b", "bcg"),
    (r"\bMVAC\b|\bddMVAC\b", "mvac"),
]
_BL_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _BL_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _BL_ARM_ABBREV])

_BL_CONTINUOUS = set()
_BL_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_BL_ENDPOINT_PATTERNS,
                                arm_compiled=_BL_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_BL_ENDPOINT_PATTERNS,
                               arm_compiled=_BL_ARM_COMPILED,
                               continuous_endpoints=_BL_CONTINUOUS,
                               lognormal_endpoints=_BL_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_BL_ENDPOINT_PATTERNS,
                              arm_compiled=_BL_ARM_COMPILED,
                              continuous_endpoints=_BL_CONTINUOUS,
                              lognormal_endpoints=_BL_LOGNORMAL)
