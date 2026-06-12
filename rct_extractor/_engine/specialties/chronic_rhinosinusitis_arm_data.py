"""
Arm-level / 2x2 + continuous extraction for chronic-rhinosinusitis (CRS) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
CRS endpoints and biologic / intranasal-steroid / saline / surgery arm labels:

  binary outcomes (rescue surgery / systemic steroids, revision surgery) -> 2x2
    events/N per arm
  continuous (SNOT-22, nasal polyp score, nasal congestion, smell, Lund-Mackay,
    Lund-Kennedy) -> mean+SD / median+IQR. NONE is log-normal -- all bounded
    clinical scores pooled on the raw scale.

A bare effect abbreviation (HR/OR/RR) is NEVER an arm label.
"""
import re
from typing import Dict, List

from .chronic_rhinosinusitis import get_chronic_rhinosinusitis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_CRS_ENDPOINT_PATTERNS = []
for _sub in ("crswnp", "crssnp", "surgery"):
    _CRS_ENDPOINT_PATTERNS.extend(get_chronic_rhinosinusitis_endpoint_patterns(_sub))

# Biologic / intranasal-steroid / irrigation / antibiotic / surgery arm labels.
# Full names case-insensitive. Generic comparators included. NO bare effect
# abbreviation (HR/OR/RR) is a label.
_CRS_ARM_FULL = [
    # Biologics
    (r"dupilumab|\bdupixent\b", "dupilumab"),
    (r"omalizumab|\bxolair\b", "omalizumab"),
    (r"mepolizumab|\bnucala\b", "mepolizumab"),
    (r"benralizumab|\bfasenra\b", "benralizumab"),
    (r"tezepelumab", "tezepelumab"),
    # Intranasal / systemic steroids
    (r"mometasone(?:\s+furoate)?", "mometasone"),
    (r"fluticasone(?:\s+(?:propionate|furoate))?", "fluticasone"),
    (r"budesonide", "budesonide"),
    (r"beclomethasone|beclometasone", "beclomethasone"),
    (r"prednis(?:ol)?one", "prednisone"),
    # Medical therapy
    (r"saline\s+irrigation|nasal\s+(?:saline\s+)?irrigation|nasal\s+lavage", "saline-irrigation"),
    (r"doxycycline", "doxycycline"),
    (r"(?:long[- ]term\s+)?macrolide|clarithromycin|azithromycin", "macrolide"),
    # Surgery
    (r"functional\s+endoscopic\s+sinus\s+surgery|\bfess\b|endoscopic\s+sinus\s+surgery|sinus\s+surgery",
     "sinus-surgery"),
    # Generic comparators
    (r"\bplacebo\b", "placebo"),
    (r"\bvehicle\b", "vehicle"),
    (r"medical\s+(?:therapy|treatment|management)", "medical-therapy"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_CRS_ARM_ABBREV = [
    (r"\bFESS\b", "sinus-surgery"),
]
_CRS_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _CRS_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _CRS_ARM_ABBREV])

# All CRS continuous outcomes; none log-normal.
_CRS_CONTINUOUS = {"SNOT22", "NPS", "NASAL_CONGESTION", "SMELL",
                   "LUND_MACKAY", "LUND_KENNEDY"}
_CRS_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_CRS_ENDPOINT_PATTERNS,
                                arm_compiled=_CRS_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_CRS_ENDPOINT_PATTERNS,
                               arm_compiled=_CRS_ARM_COMPILED,
                               continuous_endpoints=_CRS_CONTINUOUS,
                               lognormal_endpoints=_CRS_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_CRS_ENDPOINT_PATTERNS,
                              arm_compiled=_CRS_ARM_COMPILED,
                              continuous_endpoints=_CRS_CONTINUOUS,
                              lognormal_endpoints=_CRS_LOGNORMAL)
