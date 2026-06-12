"""
Arm-level / 2x2 + continuous extraction for myelodysplastic syndrome (MDS) trials.
Thin wrapper over the shared malaria_arm_data engine, configured with MDS
endpoints and hypomethylating / erythroid-maturation / ESA arm labels. MDS
endpoints are binary (transfusion independence, haematologic improvement,
complete remission) or time-to-event; no continuous outcome configured.
"""
import re
from typing import Dict, List

from .myelodysplastic_syndrome import get_myelodysplastic_syndrome_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_MDS_ENDPOINT_PATTERNS = []
for _sub in ("lower_risk", "higher_risk", "response", "mortality"):
    _MDS_ENDPOINT_PATTERNS.extend(get_myelodysplastic_syndrome_endpoint_patterns(_sub))

_MDS_ARM_FULL = [
    (r"luspatercept|reblozyl", "luspatercept"),
    (r"azacitidine|vidaza", "azacitidine"),
    (r"decitabine|dacogen", "decitabine"),
    (r"venetoclax", "venetoclax"),
    (r"lenalidomide|revlimid", "lenalidomide"),
    (r"imetelstat|rytelo", "imetelstat"),
    (r"eltrombopag", "eltrombopag"),
    (r"epoetin|darbepoetin|erythropoiesis[- ]stimulating\s+agent|\besa\b", "esa"),
    (r"best\s+supportive\s+care|\bbsc\b", "supportive-care"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+therapy", "standard-of-care"),
    (r"observation", "observation"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_MDS_ARM_ABBREV = [
    (r"\bESA\b", "esa"),
    (r"\bBSC\b", "supportive-care"),
    (r"\bHMA\b", "hypomethylating"),
]
_MDS_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _MDS_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _MDS_ARM_ABBREV])

_MDS_CONTINUOUS = set()
_MDS_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_MDS_ENDPOINT_PATTERNS,
                                arm_compiled=_MDS_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_MDS_ENDPOINT_PATTERNS,
                               arm_compiled=_MDS_ARM_COMPILED,
                               continuous_endpoints=_MDS_CONTINUOUS,
                               lognormal_endpoints=_MDS_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_MDS_ENDPOINT_PATTERNS,
                              arm_compiled=_MDS_ARM_COMPILED,
                              continuous_endpoints=_MDS_CONTINUOUS,
                              lognormal_endpoints=_MDS_LOGNORMAL)
