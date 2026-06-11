"""
Arm-level / 2x2 + continuous extraction for fracture & orthopaedic-surgery trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
orthopaedic endpoints and surgical-technique arm labels:

  binary outcomes (reoperation / revision, nonunion, infection, complications,
    mortality, VTE, return to activity) -> 2x2 events/N per arm;
  continuous outcomes (functional score, time to union, pain, range of motion)
    -> per-arm mean+SD (Wan IQR->SD).

Comparisons are typically technique-vs-technique (nailing vs plating, operative
vs nonoperative, cemented vs uncemented, hemiarthroplasty vs fixation).
"""
import re
from typing import Dict, List

from .orthopaedic import get_orthopaedic_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_ORTHO_ENDPOINT_PATTERNS = []
for _sub in ("fracture_fixation", "arthroplasty", "healing", "functional"):
    _ORTHO_ENDPOINT_PATTERNS.extend(get_orthopaedic_endpoint_patterns(_sub))

_ORTHO_ARM_FULL = [
    (r"intramedullary\s+nail\w*|\bim\s+nail\w*", "intramedullary-nail"),
    (r"locking\s+plate|plate\s+fixation|plating", "plate-fixation"),
    (r"open\s+reduction(?:\s+(?:and\s+)?internal\s+fixation)?|\borif\b", "ORIF"),
    (r"external\s+fixation|external\s+fixator", "external-fixation"),
    (r"internal\s+fixation", "internal-fixation"),
    (r"non[- ]?operative(?:\s+(?:management|treatment))?|conservative\s+(?:management|treatment)|cast(?:ing)?",
     "nonoperative"),
    (r"(?<!non)(?<!non[- ])\boperative(?:\s+(?:management|treatment))?|surgical\s+(?:management|fixation)",
     "operative"),
    (r"hemiarthroplasty", "hemiarthroplasty"),
    (r"total\s+hip\s+(?:arthroplasty|replacement)", "total-hip-arthroplasty"),
    (r"total\s+knee\s+(?:arthroplasty|replacement)", "total-knee-arthroplasty"),
    (r"cemented", "cemented"),
    (r"uncemented|cementless", "uncemented"),
    (r"bone\s+morphogenetic\s+protein|\bbmp\b", "BMP"),
    (r"bone\s+graft|autograft", "bone-graft"),
    (r"teriparatide", "teriparatide"),
    (r"low[- ]intensity\s+(?:pulsed\s+)?ultrasound|\blipus\b", "LIPUS"),
    (r"physiotherapy|rehabilitation", "rehabilitation"),
    (r"acl\s+reconstruction|reconstruction", "reconstruction"),
    (r"\bplacebo\b", "placebo"),
    (r"sham\s+(?:surgery|procedure)?|sham", "sham"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care|standard\s+(?:treatment|fixation)", "standard-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_ORTHO_ARM_ABBREV = [   # case-sensitive
    (r"\bORIF\b", "ORIF"),
    (r"\bIMN\b", "intramedullary-nail"),
    (r"\bTHA\b|\bTHR\b", "total-hip-arthroplasty"),
    (r"\bTKA\b|\bTKR\b", "total-knee-arthroplasty"),
    (r"\bLIPUS\b", "LIPUS"),
    (r"\bACLR\b", "reconstruction"),
]
_ORTHO_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _ORTHO_ARM_FULL]
                       + [(re.compile(p), n) for p, n in _ORTHO_ARM_ABBREV])

# Continuous (mean+SD poolable) orthopaedic endpoints.
_ORTHO_CONTINUOUS = {
    "FUNCTIONAL_SCORE", "UNION_TIME", "PAIN_SCORE", "RANGE_OF_MOTION",
}
_ORTHO_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_ORTHO_ENDPOINT_PATTERNS,
                                arm_compiled=_ORTHO_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_ORTHO_ENDPOINT_PATTERNS,
                               arm_compiled=_ORTHO_ARM_COMPILED,
                               continuous_endpoints=_ORTHO_CONTINUOUS,
                               lognormal_endpoints=_ORTHO_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_ORTHO_ENDPOINT_PATTERNS,
                              arm_compiled=_ORTHO_ARM_COMPILED,
                              continuous_endpoints=_ORTHO_CONTINUOUS,
                              lognormal_endpoints=_ORTHO_LOGNORMAL)
