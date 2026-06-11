"""
Arm-level / 2x2 + continuous extraction for blood-transfusion-strategy trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
transfusion endpoints and strategy / product arm labels:

  binary outcomes (mortality, transfusion exposure, ischaemic events, MACE,
    infection, rebleeding, transfusion reaction) -> 2x2 events/N per arm;
  continuous outcomes (units transfused, haemoglobin, length of stay) -> per-arm
    mean+SD (Wan IQR->SD).

Comparisons are typically strategy-vs-strategy (restrictive vs liberal, 1:1:1 vs
standard ratio, fresh vs standard-age blood) or prophylactic-vs-therapeutic.
"""
import re
from typing import Dict, List

from .transfusion import get_transfusion_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_TX_ENDPOINT_PATTERNS = []
for _sub in ("threshold", "platelet_plasma", "massive", "processing"):
    _TX_ENDPOINT_PATTERNS.extend(get_transfusion_endpoint_patterns(_sub))

_TX_ARM_FULL = [
    (r"restrictive\s+(?:transfusion\s+)?(?:strategy|threshold|group)|restrictive", "restrictive"),
    (r"liberal\s+(?:transfusion\s+)?(?:strategy|threshold|group)|liberal", "liberal"),
    (r"prophylactic\s+(?:platelet\s+)?transfusion|prophylactic", "prophylactic"),
    (r"therapeutic\s+(?:platelet\s+)?transfusion|therapeutic", "therapeutic"),
    (r"fresh(?:er)?\s+(?:blood|red\s+cells)|fresh", "fresh-blood"),
    (r"standard[- ]age\s+blood|older\s+(?:blood|red\s+cells)|standard[- ]issue", "standard-age-blood"),
    (r"fresh\s+frozen\s+plasma|\bffp\b", "fresh-frozen-plasma"),
    (r"fibrinogen\s+concentrate", "fibrinogen-concentrate"),
    (r"cryoprecipitate", "cryoprecipitate"),
    (r"tranexamic\s+acid", "tranexamic-acid"),
    (r"whole\s+blood", "whole-blood"),
    (r"1\s*:\s*1\s*:\s*1|fixed[- ]ratio|higher[- ]ratio", "1:1:1-ratio"),
    (r"leukoreduc\w+|leucoreduc\w+", "leukoreduced"),
    (r"washed\s+red\s+cells", "washed-red-cells"),
    (r"pathogen[- ](?:reduced|inactivat\w+)", "pathogen-reduced"),
    (r"\bplacebo\b", "placebo"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care|standard\s+(?:transfusion\s+)?(?:practice|care)",
     "standard-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_TX_ARM_ABBREV = [   # case-sensitive
    (r"\bFFP\b", "fresh-frozen-plasma"),
    (r"\bTXA\b", "tranexamic-acid"),
    (r"\bMTP\b", "massive-transfusion-protocol"),
]
_TX_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _TX_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _TX_ARM_ABBREV])

# Continuous (mean+SD poolable) transfusion endpoints.
_TX_CONTINUOUS = {
    "UNITS_TRANSFUSED", "HB_LEVEL", "LENGTH_OF_STAY",
}
_TX_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_TX_ENDPOINT_PATTERNS,
                                arm_compiled=_TX_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_TX_ENDPOINT_PATTERNS,
                               arm_compiled=_TX_ARM_COMPILED,
                               continuous_endpoints=_TX_CONTINUOUS,
                               lognormal_endpoints=_TX_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_TX_ENDPOINT_PATTERNS,
                              arm_compiled=_TX_ARM_COMPILED,
                              continuous_endpoints=_TX_CONTINUOUS,
                              lognormal_endpoints=_TX_LOGNORMAL)
