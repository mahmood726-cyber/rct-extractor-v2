"""
Arm-level / 2x2 + continuous extraction for pulmonary-hypertension (PAH) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
PH endpoints and PAH drug-class arm labels:

  continuous (6-minute walk distance, PVR, mPAP, cardiac index, Borg dyspnoea,
    NT-proBNP) -> mean+SD / median+IQR, pooled as MD/SMD on the natural scale.
  binary (WHO functional-class improvement, clinical worsening, PH
    hospitalisation, all-cause mortality) -> 2x2 events/N per arm.
"""
import re
from typing import Dict, List

from .pulmonary_hypertension import get_pulmonary_hypertension_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_PH_ENDPOINT_PATTERNS = []
for _sub in ("functional", "hemodynamics", "clinical_worsening", "biomarker"):
    _PH_ENDPOINT_PATTERNS.extend(get_pulmonary_hypertension_endpoint_patterns(_sub))

# PAH drug-class arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE.
_PH_ARM_FULL = [
    # PDE5 inhibitors
    (r"sildenafil", "sildenafil"),
    (r"tadalafil", "tadalafil"),
    (r"vardenafil", "vardenafil"),
    # endothelin receptor antagonists
    (r"bosentan", "bosentan"),
    (r"ambrisentan", "ambrisentan"),
    (r"macitentan", "macitentan"),
    # prostacyclin pathway
    (r"epoprostenol", "epoprostenol"),
    (r"treprostinil", "treprostinil"),
    (r"iloprost", "iloprost"),
    (r"selexipag", "selexipag"),
    (r"beraprost", "beraprost"),
    # sGC stimulator / activin
    (r"riociguat", "riociguat"),
    (r"sotatercept", "sotatercept"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|background\s+therapy", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_PH_ARM_ABBREV = [
    (r"\bERA\b", "endothelin-receptor-antagonist"),
    (r"\bPDE5i?\b", "pde5-inhibitor"),
]
_PH_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _PH_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _PH_ARM_ABBREV])

# PH continuous outcomes (functional + haemodynamic + biomarker; natural scale).
_PH_CONTINUOUS = {"SIX_MWD", "PVR", "MPAP", "CARDIAC_INDEX", "BORG_DYSPNEA", "NT_PROBNP"}
_PH_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_PH_ENDPOINT_PATTERNS,
                                arm_compiled=_PH_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_PH_ENDPOINT_PATTERNS,
                               arm_compiled=_PH_ARM_COMPILED,
                               continuous_endpoints=_PH_CONTINUOUS,
                               lognormal_endpoints=_PH_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_PH_ENDPOINT_PATTERNS,
                              arm_compiled=_PH_ARM_COMPILED,
                              continuous_endpoints=_PH_CONTINUOUS,
                              lognormal_endpoints=_PH_LOGNORMAL)
