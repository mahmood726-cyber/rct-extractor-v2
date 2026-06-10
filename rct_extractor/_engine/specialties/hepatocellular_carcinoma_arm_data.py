"""
Arm-level / 2x2 + continuous extraction for hepatocellular-carcinoma trials.
Thin wrapper over the shared malaria_arm_data engine, configured with HCC
endpoints and systemic / locoregional / curative arm labels.
"""
import re
from typing import Dict, List

from .hepatocellular_carcinoma import get_hepatocellular_carcinoma_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_HCC_ENDPOINT_PATTERNS = []
for _sub in ("systemic", "locoregional", "curative", "mortality"):
    _HCC_ENDPOINT_PATTERNS.extend(get_hepatocellular_carcinoma_endpoint_patterns(_sub))

_HCC_ARM_FULL = [
    (r"atezolizumab(?:[- /]+(?:and\s+|plus\s+)?bevacizumab)?", "atezolizumab-bevacizumab"),
    (r"durvalumab(?:[- /]+(?:and\s+|plus\s+)?tremelimumab)?", "durvalumab-tremelimumab"),
    (r"sorafenib|nexavar", "sorafenib"),
    (r"lenvatinib|lenvima", "lenvatinib"),
    (r"regorafenib|stivarga", "regorafenib"),
    (r"cabozantinib|cabometyx", "cabozantinib"),
    (r"ramucirumab|cyramza", "ramucirumab"),
    (r"bevacizumab|avastin", "bevacizumab"),
    (r"transarterial\s+chemoembolization|\btace\b", "tace"),
    (r"transarterial\s+radioembolization|\btare\b|yttrium[- ]?90|\by90\b", "tare-y90"),
    (r"radiofrequency\s+ablation|\brfa\b", "rfa"),
    (r"microwave\s+ablation|\bmwa\b", "mwa"),
    (r"hepatic\s+resection|liver\s+resection|hepatectomy|\bresection\b", "resection"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|best\s+supportive\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_HCC_ARM_ABBREV = [
    (r"\bTACE\b", "tace"),
    (r"\bRFA\b", "rfa"),
    (r"\bMWA\b", "mwa"),
    (r"\bTARE\b|\bSIRT\b", "tare-y90"),
]
_HCC_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _HCC_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _HCC_ARM_ABBREV])

_HCC_CONTINUOUS = {"AFP_LEVEL", "QOL"}
_HCC_LOGNORMAL = {"AFP_LEVEL"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_HCC_ENDPOINT_PATTERNS,
                                arm_compiled=_HCC_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_HCC_ENDPOINT_PATTERNS,
                               arm_compiled=_HCC_ARM_COMPILED,
                               continuous_endpoints=_HCC_CONTINUOUS,
                               lognormal_endpoints=_HCC_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_HCC_ENDPOINT_PATTERNS,
                              arm_compiled=_HCC_ARM_COMPILED,
                              continuous_endpoints=_HCC_CONTINUOUS,
                              lognormal_endpoints=_HCC_LOGNORMAL)
