"""
Arm-level / 2x2 + continuous extraction for erectile-dysfunction (ED) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with ED endpoints
and pharmacologic / device / shockwave arm labels:

  binary outcomes (SEP2, SEP3, GAQ responder, successful intercourse, class
    adverse events) -> 2x2 events/N per arm
  continuous (IIEF-EF domain, EHS, EDITS treatment satisfaction) -> mean/SD per
    arm, pooled on the natural scale (MD/SMD).
"""
import re
from typing import Dict, List

from .erectile_dysfunction import get_erectile_dysfunction_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# ED endpoint patterns (string, endpoint) across all subspecialties.
_ED_ENDPOINT_PATTERNS = []
for _sub in ("pharmacologic", "shockwave", "device", "safety"):
    _ED_ENDPOINT_PATTERNS.extend(get_erectile_dysfunction_endpoint_patterns(_sub))

# Pharmacologic / device / shockwave arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_ED_ARM_FULL = [
    # PDE5 inhibitors
    (r"sildenafil", "sildenafil"),
    (r"tadalafil", "tadalafil"),
    (r"vardenafil", "vardenafil"),
    (r"avanafil", "avanafil"),
    (r"udenafil", "udenafil"),
    (r"mirodenafil", "mirodenafil"),
    # other pharmacologic
    (r"alprostadil|intracavernosal|intraurethral|\bmuse\b", "alprostadil"),
    (r"testosterone", "testosterone"),
    # shockwave / regenerative
    (r"low[- ]intensity\s+(?:extracorporeal\s+)?shock\s*wave|li[- ]?eswt|shock\s*wave",
     "shockwave"),
    (r"platelet[- ]rich\s+plasma", "prp"),
    (r"stem[- ]cell", "stem-cell"),
    # device
    (r"vacuum\s+erection\s+device|vacuum\s+constriction", "vacuum-device"),
    (r"penile\s+(?:prosthesis|implant)|inflatable\s+penile", "penile-prosthesis"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"sham\s+(?:procedure|shock|therapy)", "sham"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_ED_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bLi[- ]?ESWT\b|\bESWT\b", "shockwave"),
    (r"\bPRP\b", "prp"),
    (r"\bVED\b", "vacuum-device"),
    (r"\bICI\b", "alprostadil"),
]
_ED_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _ED_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _ED_ARM_ABBREV])

# ED continuous outcomes (linear scales; none log-normal).
_ED_CONTINUOUS = {"IIEF_EF", "EHS", "TREATMENT_SATISFACTION"}
_ED_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_ED_ENDPOINT_PATTERNS,
                                arm_compiled=_ED_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_ED_ENDPOINT_PATTERNS,
                               arm_compiled=_ED_ARM_COMPILED,
                               continuous_endpoints=_ED_CONTINUOUS,
                               lognormal_endpoints=_ED_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_ED_ENDPOINT_PATTERNS,
                              arm_compiled=_ED_ARM_COMPILED,
                              continuous_endpoints=_ED_CONTINUOUS,
                              lognormal_endpoints=_ED_LOGNORMAL)
