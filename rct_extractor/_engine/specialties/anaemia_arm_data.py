"""
Arm-level / 2x2 + continuous extraction for anaemia trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
anaemia endpoints and iron / ESA / transfusion arm labels:

  binary outcomes (Hb / anaemia target response, anaemia correction, transfusion
    requirement, iron-deficiency resolution) -> 2x2 events/N per arm;
  continuous outcomes (haemoglobin change, ferritin, transferrin saturation,
    reticulocyte, fatigue) -> per-arm mean+SD (Wan IQR->SD).

Comparisons are typically iron-route (IV vs oral iron), drug-vs-placebo (ESA,
HIF-PHI), supplement-vs-control, or transfusion-strategy (restrictive vs liberal).
"""
import re
from typing import Dict, List

from .anaemia import get_anaemia_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_AN_ENDPOINT_PATTERNS = []
for _sub in ("iron_therapy", "esa", "nutritional", "transfusion_anaemia"):
    _AN_ENDPOINT_PATTERNS.extend(get_anaemia_endpoint_patterns(_sub))

_AN_ARM_FULL = [
    (r"ferric\s+carboxymaltose", "ferric-carboxymaltose"),
    (r"iron\s+sucrose", "iron-sucrose"),
    (r"ferric\s+derisomaltose|iron\s+isomaltoside", "ferric-derisomaltose"),
    (r"ferric\s+gluconate", "ferric-gluconate"),
    (r"intravenous\s+iron|\biv\s+iron\b", "intravenous-iron"),
    (r"oral\s+iron|ferrous\s+(?:sulfate|sulphate|fumarate)", "oral-iron"),
    (r"ferric\s+maltol", "ferric-maltol"),
    (r"darbepoetin", "darbepoetin"),
    (r"epoetin", "epoetin"),
    (r"methoxy[- ]?polyethylene\s+glycol[- ]?epoetin", "MPG-epoetin"),
    (r"roxadustat", "roxadustat"),
    (r"daprodustat", "daprodustat"),
    (r"vadadustat", "vadadustat"),
    (r"iron\s+(?:and\s+)?folic\s+acid|iron[- ]folate", "iron-folic-acid"),
    (r"folic\s+acid", "folic-acid"),
    (r"vitamin\s+b12|cobalamin", "vitamin-B12"),
    (r"multiple\s+micronutrient|micronutrient", "micronutrient"),
    (r"restrictive\s+(?:transfusion\s+)?(?:strategy|threshold)", "restrictive-transfusion"),
    (r"liberal\s+(?:transfusion\s+)?(?:strategy|threshold)", "liberal-transfusion"),
    (r"\bplacebo\b", "placebo"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care|standard\s+(?:treatment|therapy)",
     "standard-of-care"),
    (r"no\s+(?:iron|treatment|supplement)|no[- ]treatment", "no-treatment"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_AN_ARM_ABBREV = [   # case-sensitive
    (r"\bFCM\b", "ferric-carboxymaltose"),
    (r"\bESA\b", "ESA"),
    (r"\bIFA\b", "iron-folic-acid"),
    (r"\bMMN\b", "micronutrient"),
    (r"\bHIF-PHI\b", "HIF-PHI"),
]
_AN_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _AN_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _AN_ARM_ABBREV])

# Continuous (mean+SD poolable) anaemia endpoints.
_AN_CONTINUOUS = {
    "HB_CHANGE", "FERRITIN", "TSAT", "RETICULOCYTE", "FATIGUE",
}
_AN_LOGNORMAL = {"FERRITIN"}  # ferritin is right-skewed; often log-normal


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_AN_ENDPOINT_PATTERNS,
                                arm_compiled=_AN_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_AN_ENDPOINT_PATTERNS,
                               arm_compiled=_AN_ARM_COMPILED,
                               continuous_endpoints=_AN_CONTINUOUS,
                               lognormal_endpoints=_AN_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_AN_ENDPOINT_PATTERNS,
                              arm_compiled=_AN_ARM_COMPILED,
                              continuous_endpoints=_AN_CONTINUOUS,
                              lognormal_endpoints=_AN_LOGNORMAL)
