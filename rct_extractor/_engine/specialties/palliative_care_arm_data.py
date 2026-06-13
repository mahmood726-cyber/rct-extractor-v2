"""
Arm-level / 2x2 + continuous extraction for palliative / end-of-life care trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
palliative-care endpoints and palliative-intervention arm labels:

  binary (home death, hospital admission / ED visit, aggressive EOL care,
    advance-care-planning completion, survival/mortality) -> 2x2 events/N.
  continuous (pain, dyspnoea, symptom burden, quality of life, mood,
    survival time) -> mean+SD / median+IQR, pooled as MD/SMD on the natural scale.
"""
import re
from typing import Dict, List

from .palliative_care import get_palliative_care_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_PC_ENDPOINT_PATTERNS = []
for _sub in ("symptoms", "quality_of_life", "care_utilisation", "survival"):
    _PC_ENDPOINT_PATTERNS.extend(get_palliative_care_endpoint_patterns(_sub))

# Palliative-intervention arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE.
_PC_ARM_FULL = [
    (r"early\s+(?:specialist\s+|integrated\s+)?palliative\s+care", "early-palliative-care"),
    (r"specialist\s+palliative\s+care|(?:specialist\s+)?palliative\s+care\s+(?:team|consultation)",
     "specialist-palliative-care"),
    (r"palliative\s+care\s+(?:intervention|programme|program)?|palliative\s+care", "palliative-care"),
    (r"advance\s+care\s+planning", "advance-care-planning"),
    (r"hospice(?:\s+care)?", "hospice"),
    (r"morphine|opioid", "opioid"),
    (r"methylnaltrexone", "methylnaltrexone"),
    (r"(?:supplemental\s+)?oxygen", "oxygen"),
    (r"fan\s+therapy|handheld\s+fan", "fan-therapy"),
    (r"corticosteroid|dexamethasone", "corticosteroid"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"usual\s+(?:oncology\s+)?care|standard\s+(?:oncology\s+)?care|standard\s+care", "usual-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_PC_ARM_ABBREV = [
    (r"\bACP\b", "advance-care-planning"),
    (r"\bEPC\b", "early-palliative-care"),
]
_PC_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _PC_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _PC_ARM_ABBREV])

# Palliative-care continuous outcomes (natural scale). Care-utilisation and
# survival/mortality are the binary ratio endpoints.
_PC_CONTINUOUS = {"PAIN", "DYSPNOEA", "SYMPTOM_BURDEN", "QUALITY_OF_LIFE", "MOOD", "SURVIVAL_TIME"}
_PC_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_PC_ENDPOINT_PATTERNS,
                                arm_compiled=_PC_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_PC_ENDPOINT_PATTERNS,
                               arm_compiled=_PC_ARM_COMPILED,
                               continuous_endpoints=_PC_CONTINUOUS,
                               lognormal_endpoints=_PC_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_PC_ENDPOINT_PATTERNS,
                              arm_compiled=_PC_ARM_COMPILED,
                              continuous_endpoints=_PC_CONTINUOUS,
                              lognormal_endpoints=_PC_LOGNORMAL)
