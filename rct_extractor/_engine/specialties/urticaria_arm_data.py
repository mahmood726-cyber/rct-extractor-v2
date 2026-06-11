"""
Arm-level / 2x2 + continuous extraction for chronic-urticaria / anaphylaxis trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
urticaria endpoints and antihistamine / biologic arm labels:

  binary outcomes (complete response / UAS7=0, well-controlled, angioedema,
    anaphylaxis recurrence, responder) -> 2x2 events/N per arm;
  continuous outcomes (UAS7, ISS7, HSS7, UCT, DLQI) -> per-arm mean+SD
    (Wan IQR->SD).

Comparisons are typically drug-vs-placebo (omalizumab, remibrutinib, updosed
antihistamine) or active-vs-active (updosed vs standard antihistamine).
"""
import re
from typing import Dict, List

from .urticaria import get_urticaria_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_URT_ENDPOINT_PATTERNS = []
for _sub in ("antihistamine", "biologic", "anaphylaxis", "other"):
    _URT_ENDPOINT_PATTERNS.extend(get_urticaria_endpoint_patterns(_sub))

_URT_ARM_FULL = [
    (r"omalizumab", "omalizumab"),
    (r"ligelizumab", "ligelizumab"),
    (r"dupilumab", "dupilumab"),
    (r"remibrutinib", "remibrutinib"),
    (r"fenebrutinib", "fenebrutinib"),
    (r"rilzabrutinib", "rilzabrutinib"),
    (r"barzolvolimab", "barzolvolimab"),
    (r"updos\w+\s+(?:antihistamine|cetirizine|bilastine)|updosed", "updosed-antihistamine"),
    (r"cetirizine|levocetirizine", "cetirizine"),
    (r"bilastine", "bilastine"),
    (r"fexofenadine", "fexofenadine"),
    (r"rupatadine", "rupatadine"),
    (r"desloratadine|loratadine", "desloratadine"),
    (r"ebastine", "ebastine"),
    (r"ciclosporin|cyclosporine", "ciclosporin"),
    (r"(?:adrenaline|epinephrine)\s+(?:auto[- ]?injector|autoinjector)|intranasal\s+(?:adrenaline|epinephrine)",
     "epinephrine"),
    (r"\bplacebo\b", "placebo"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care|standard\s+(?:dose\s+)?antihistamine",
     "standard-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_URT_ARM_ABBREV = [   # case-sensitive
    (r"\bXOLAIR\b", "omalizumab"),
    (r"\bBTKi\b", "BTK-inhibitor"),
]
_URT_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _URT_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _URT_ARM_ABBREV])

# Continuous (mean+SD poolable) urticaria endpoints (symptom scores / QoL).
_URT_CONTINUOUS = {
    "UAS7", "ISS7", "HSS7", "UCT", "DLQI",
}
_URT_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_URT_ENDPOINT_PATTERNS,
                                arm_compiled=_URT_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_URT_ENDPOINT_PATTERNS,
                               arm_compiled=_URT_ARM_COMPILED,
                               continuous_endpoints=_URT_CONTINUOUS,
                               lognormal_endpoints=_URT_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_URT_ENDPOINT_PATTERNS,
                              arm_compiled=_URT_ARM_COMPILED,
                              continuous_endpoints=_URT_CONTINUOUS,
                              lognormal_endpoints=_URT_LOGNORMAL)
