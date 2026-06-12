"""
Arm-level / 2x2 + continuous extraction for insomnia trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
insomnia endpoints and hypnotic / behavioural-therapy / comparator arm labels:

  binary outcomes (treatment response, remission) -> 2x2 events/N per arm
  continuous (ISI, SOL, WASO, TST, sleep efficiency, PSQI, LPS) -> mean+SD /
    median+IQR. NONE is log-normal.

A bare effect abbreviation (HR/OR/RR) is NEVER an arm label.
"""
import re
from typing import Dict, List

from .insomnia import get_insomnia_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_INS_ENDPOINT_PATTERNS = []
for _sub in ("pharmacotherapy", "cbt_i", "objective"):
    _INS_ENDPOINT_PATTERNS.extend(get_insomnia_endpoint_patterns(_sub))

# Hypnotic / behavioural-therapy / comparator arm labels. Full names
# case-insensitive. Generic comparators included. NO bare effect abbreviation
# (HR/OR/RR) is a label.
_INS_ARM_FULL = [
    # Dual orexin-receptor antagonists
    (r"suvorexant|\bbelsomra\b", "suvorexant"),
    (r"lemborexant|\bdayvigo\b", "lemborexant"),
    (r"daridorexant|\bquviviq\b", "daridorexant"),
    # Z-drugs
    (r"eszopiclone|\blunesta\b", "eszopiclone"),
    (r"zolpidem|\bambien\b|\bstilnox\b", "zolpidem"),
    (r"zopiclone", "zopiclone"),
    (r"zaleplon|\bsonata\b", "zaleplon"),
    # Melatonin agonists / other
    (r"ramelteon|\brozerem\b", "ramelteon"),
    (r"(?:prolonged[- ]release\s+)?melatonin|\bcircadin\b", "melatonin"),
    (r"low[- ]dose\s+doxepin|doxepin|\bsilenor\b", "doxepin"),
    (r"trazodone", "trazodone"),
    # Benzodiazepines
    (r"temazepam", "temazepam"),
    (r"triazolam", "triazolam"),
    # Behavioural therapy
    (r"cognitive\s+behaviou?ral\s+therapy(?:\s+for\s+insomnia)?|\bcbt[- ]?i\b|digital\s+cbt",
     "cbt-i"),
    (r"sleep\s+hygiene(?:\s+education)?", "sleep-hygiene"),
    # Generic comparators
    (r"\bplacebo\b", "placebo"),
    (r"\bvehicle\b", "vehicle"),
    (r"wait[- ]?list(?:\s+control)?|waiting\s+list", "waitlist"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|treatment\s+as\s+usual", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_INS_ARM_COMPILED = [(re.compile(p, re.I), n) for p, n in _INS_ARM_FULL]

# Insomnia continuous outcomes; none log-normal.
_INS_CONTINUOUS = {"ISI", "SOL", "WASO", "TST", "SLEEP_EFFICIENCY", "PSQI", "LPS"}
_INS_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_INS_ENDPOINT_PATTERNS,
                                arm_compiled=_INS_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_INS_ENDPOINT_PATTERNS,
                               arm_compiled=_INS_ARM_COMPILED,
                               continuous_endpoints=_INS_CONTINUOUS,
                               lognormal_endpoints=_INS_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_INS_ENDPOINT_PATTERNS,
                              arm_compiled=_INS_ARM_COMPILED,
                              continuous_endpoints=_INS_CONTINUOUS,
                              lognormal_endpoints=_INS_LOGNORMAL)
