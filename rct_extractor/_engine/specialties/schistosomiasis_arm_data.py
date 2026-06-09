"""
Arm-level / 2x2 + continuous extraction for schistosomiasis (bilharzia) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with schistosomiasis
endpoints and anthelmintic / vaccine arm labels:

  binary outcomes (parasitological cure, treatment failure, infection prevalence,
    reinfection, haematuria, periportal fibrosis) -> 2x2 events/N per arm
  continuous (egg reduction rate, haemoglobin -> mean+SD / median+IQR; egg counts
    and antibody titres are right-skewed -> log-normal, pool on the log scale).
"""
import re
from typing import Dict, List

from .schistosomiasis import get_schistosomiasis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Schistosomiasis endpoint patterns (string, endpoint) across all subspecialties.
_SCHISTO_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "prevention", "morbidity", "vaccine"):
    _SCHISTO_ENDPOINT_PATTERNS.extend(get_schistosomiasis_endpoint_patterns(_sub))

# Anthelmintic / vaccine arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_SCHISTO_ARM_FULL = [
    (r"praziquantel", "praziquantel"),
    (r"artesunate", "artesunate"),
    (r"artemether[- ]lumefantrine", "artemether-lumefantrine"),
    (r"artemether", "artemether"),
    (r"dihydroartemisinin", "dihydroartemisinin"),
    (r"artemisinin", "artemisinin"),
    (r"oxamniquine", "oxamniquine"),
    (r"mefloquine", "mefloquine"),
    (r"albendazole", "albendazole"),
    (r"mebendazole", "mebendazole"),
    # vaccines
    (r"sh28gst|bilhvax", "sh28gst"),
    (r"sm-?14", "sm14"),
    (r"sm-?tsp-?2", "sm-tsp-2"),
    (r"smp80", "smp80"),
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"untreated(?:\s+(?:group|arm|control))?", "untreated"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_SCHISTO_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bPZQ\b", "praziquantel"),
    (r"\bOXA\b", "oxamniquine"),
    (r"\bABZ\b", "albendazole"),
]
_SCHISTO_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _SCHISTO_ARM_FULL]
                         + [(re.compile(p), n) for p, n in _SCHISTO_ARM_ABBREV])

# Schistosomiasis continuous outcomes; egg counts and antibody titres are
# right-skewed and pooled on the log scale.
_SCHISTO_CONTINUOUS = {"EGG_REDUCTION_RATE", "EGG_COUNT", "ANAEMIA", "IMMUNOGENICITY"}
_SCHISTO_LOGNORMAL = {"EGG_COUNT", "IMMUNOGENICITY"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_SCHISTO_ENDPOINT_PATTERNS,
                                arm_compiled=_SCHISTO_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_SCHISTO_ENDPOINT_PATTERNS,
                               arm_compiled=_SCHISTO_ARM_COMPILED,
                               continuous_endpoints=_SCHISTO_CONTINUOUS,
                               lognormal_endpoints=_SCHISTO_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_SCHISTO_ENDPOINT_PATTERNS,
                              arm_compiled=_SCHISTO_ARM_COMPILED,
                              continuous_endpoints=_SCHISTO_CONTINUOUS,
                              lognormal_endpoints=_SCHISTO_LOGNORMAL)
