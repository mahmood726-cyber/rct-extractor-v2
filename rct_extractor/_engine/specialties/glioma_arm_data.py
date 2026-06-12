"""
Arm-level / 2x2 + continuous extraction for glioma / glioblastoma trials.
Thin wrapper over the shared malaria_arm_data engine, configured with glioma
endpoints and neuro-oncology arm labels (temozolomide / TTFields / bevacizumab /
vorasidenib). Glioma endpoints are time-to-event or binary (objective response,
6-month PFS); no continuous outcome configured.
"""
import re
from typing import Dict, List

from .glioma import get_glioma_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_GL_ENDPOINT_PATTERNS = []
for _sub in ("glioblastoma", "recurrent", "low_grade", "mortality"):
    _GL_ENDPOINT_PATTERNS.extend(get_glioma_endpoint_patterns(_sub))

_GL_ARM_FULL = [
    (r"temozolomide[, /-]+radiotherapy|chemoradiotherapy|stupp", "temozolomide-rt"),
    (r"tumou?r[- ]treating\s+fields|ttfields|optune", "ttfields"),
    (r"temozolomide|temodar", "temozolomide"),
    (r"bevacizumab|avastin", "bevacizumab"),
    (r"\blomustine\b|\bccnu\b", "lomustine"),
    (r"carmustine\s+wafer|gliadel|\bbcnu\b", "carmustine"),
    (r"regorafenib", "regorafenib"),
    (r"vorasidenib|ivosidenib", "ivosidenib-class"),
    (r"procarbazine[, /-]+lomustine[, /-]+vincristine|\bpcv\b", "pcv"),
    (r"radiotherapy|radiation\s+therapy", "radiotherapy"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+(?:chemo)?(?:radio)?therapy", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_GL_ARM_ABBREV = [
    (r"\bTTFields\b", "ttfields"),
    (r"\bPCV\b", "pcv"),
    (r"\bTMZ\b", "temozolomide"),
]
_GL_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _GL_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _GL_ARM_ABBREV])

_GL_CONTINUOUS = set()
_GL_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_GL_ENDPOINT_PATTERNS,
                                arm_compiled=_GL_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_GL_ENDPOINT_PATTERNS,
                               arm_compiled=_GL_ARM_COMPILED,
                               continuous_endpoints=_GL_CONTINUOUS,
                               lognormal_endpoints=_GL_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_GL_ENDPOINT_PATTERNS,
                              arm_compiled=_GL_ARM_COMPILED,
                              continuous_endpoints=_GL_CONTINUOUS,
                              lognormal_endpoints=_GL_LOGNORMAL)
