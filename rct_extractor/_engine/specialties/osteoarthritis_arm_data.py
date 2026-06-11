"""
Arm-level / 2x2 + continuous extraction for osteoarthritis trials.

Thin wrapper over the shared malaria_arm_data engine configured with OA endpoints
and OA arm labels:

  binary outcomes (OMERACT-OARSI responder, total joint replacement, adverse
    events) -> 2x2 events/N per arm.
  continuous outcomes (WOMAC pain/function/total, pain VAS, KOOS, joint space
    width) -> per-arm mean +/- SD, pooled as a mean difference.
"""
import re
from typing import Dict, List

from .osteoarthritis import get_osteoarthritis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_OA_ENDPOINT_PATTERNS = []
for _sub in ("pharmacologic", "intraarticular", "structural", "nonpharm"):
    _OA_ENDPOINT_PATTERNS.extend(get_osteoarthritis_endpoint_patterns(_sub))

_OA_ARM_FULL = [
    (r"naproxen", "naproxen"),
    (r"celecoxib", "celecoxib"),
    (r"diclofenac", "diclofenac"),
    (r"ibuprofen", "ibuprofen"),
    (r"etoricoxib", "etoricoxib"),
    (r"paracetamol|acetaminophen", "paracetamol"),
    (r"duloxetine", "duloxetine"),
    (r"tanezumab", "tanezumab"),
    (r"hyaluron(?:ic\s+acid|ate)|viscosupplement|hylan", "hyaluronic-acid"),
    (r"triamcinolone", "triamcinolone"),
    (r"methylprednisolone", "methylprednisolone"),
    (r"platelet[- ]rich\s+plasma|\bprp\b", "PRP"),
    (r"sprifermin", "sprifermin"),
    (r"lorecivivint", "lorecivivint"),
    (r"corticosteroid", "corticosteroid"),
    (r"exercise|physiotherapy|physical\s+therapy", "exercise"),
    (r"\bplacebo\b", "placebo"),
    (r"\bsaline\b", "saline"),
    (r"\bsham\b", "sham"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care", "standard-of-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"active\s+(?:treatment|comparator)", "active"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_OA_ARM_ABBREV = [
    (r"\bHA\b", "hyaluronic-acid"),
    (r"\bIACS\b", "corticosteroid"),
]
_OA_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _OA_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _OA_ARM_ABBREV])

_OA_CONTINUOUS = {"WOMAC_PAIN", "WOMAC_FUNCTION", "WOMAC_TOTAL", "PAIN_VAS",
                  "KOOS", "JOINT_SPACE_WIDTH"}
_OA_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_OA_ENDPOINT_PATTERNS,
                                arm_compiled=_OA_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_OA_ENDPOINT_PATTERNS,
                               arm_compiled=_OA_ARM_COMPILED,
                               continuous_endpoints=_OA_CONTINUOUS,
                               lognormal_endpoints=_OA_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_OA_ENDPOINT_PATTERNS,
                              arm_compiled=_OA_ARM_COMPILED,
                              continuous_endpoints=_OA_CONTINUOUS,
                              lognormal_endpoints=_OA_LOGNORMAL)
