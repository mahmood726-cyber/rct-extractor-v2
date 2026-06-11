"""
Arm-level / 2x2 + continuous extraction for allergic-rhinitis trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
allergic-rhinitis endpoints and pharmacotherapy / immunotherapy arm labels:

  binary outcomes (responder, rescue-medication use, asthma development, adverse
    events) -> 2x2 events/N per arm;
  continuous outcomes (TNSS, CSMS, TOSS, TSS, RQLQ, nasal congestion, rescue
    medication score) -> per-arm mean+SD (Wan IQR->SD).

Comparisons are typically drug-vs-placebo (intranasal steroid, antihistamine,
SLIT tablet) or active-vs-active (combination spray vs monotherapy).
"""
import re
from typing import Dict, List

from .allergic_rhinitis import get_allergic_rhinitis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_AR_ENDPOINT_PATTERNS = []
for _sub in ("pharmacotherapy", "immunotherapy", "biologics", "environmental"):
    _AR_ENDPOINT_PATTERNS.extend(get_allergic_rhinitis_endpoint_patterns(_sub))

_AR_ARM_FULL = [
    (r"fluticasone\s+furoate", "fluticasone-furoate"),
    (r"fluticasone", "fluticasone"),
    (r"mometasone", "mometasone"),
    (r"budesonide", "budesonide"),
    (r"triamcinolone", "triamcinolone"),
    (r"azelastine[- ]fluticasone|\bmp[- ]?azpd\b", "azelastine-fluticasone"),
    (r"azelastine", "azelastine"),
    (r"cetirizine|levocetirizine", "cetirizine"),
    (r"loratadine|desloratadine", "loratadine"),
    (r"fexofenadine", "fexofenadine"),
    (r"bilastine", "bilastine"),
    (r"montelukast", "montelukast"),
    (r"oxymetazoline", "oxymetazoline"),
    (r"sublingual\s+immunotherapy|slit\s+tablet|sublingual\s+tablet", "SLIT"),
    (r"subcutaneous\s+immunotherapy", "SCIT"),
    (r"grass\s+pollen\s+(?:tablet|extract)", "grass-pollen-tablet"),
    (r"house\s+dust\s+mite\s+(?:tablet|slit)", "HDM-tablet"),
    (r"omalizumab", "omalizumab"),
    (r"dupilumab", "dupilumab"),
    (r"nasal\s+saline|saline\s+irrigation", "nasal-saline"),
    (r"\bplacebo\b", "placebo"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care", "standard-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_AR_ARM_ABBREV = [   # case-sensitive
    (r"\bSLIT\b", "SLIT"),
    (r"\bSCIT\b", "SCIT"),
    (r"\bINS\b", "intranasal-steroid"),
    (r"\bAIT\b", "allergen-immunotherapy"),
]
_AR_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _AR_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _AR_ARM_ABBREV])

# Continuous (mean+SD poolable) allergic-rhinitis endpoints (symptom scores).
_AR_CONTINUOUS = {
    "TNSS", "CSMS", "TOSS", "TSS", "RQLQ", "NASAL_CONGESTION",
    "RESCUE_MEDICATION", "SYMPTOM_FREE_DAYS",
}
_AR_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_AR_ENDPOINT_PATTERNS,
                                arm_compiled=_AR_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_AR_ENDPOINT_PATTERNS,
                               arm_compiled=_AR_ARM_COMPILED,
                               continuous_endpoints=_AR_CONTINUOUS,
                               lognormal_endpoints=_AR_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_AR_ENDPOINT_PATTERNS,
                              arm_compiled=_AR_ARM_COMPILED,
                              continuous_endpoints=_AR_CONTINUOUS,
                              lognormal_endpoints=_AR_LOGNORMAL)
