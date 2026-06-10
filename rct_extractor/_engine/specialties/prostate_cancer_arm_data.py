"""
Arm-level / 2x2 + continuous extraction for prostate-cancer trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with prostate-cancer
endpoints and AR-targeted / chemotherapy / ADT / radiotherapy arm labels:

  binary outcomes (PSA response, biochemical recurrence, skeletal-related event,
    metastasis, objective response) -> 2x2 events/N per arm
  continuous (PSA level -> log-normal, pool on the log scale; QoL FACT-P -> MD).
"""
import re
from typing import Dict, List

from .prostate_cancer import get_prostate_cancer_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Prostate-cancer endpoint patterns (string, endpoint) across all subspecialties.
_PC_ENDPOINT_PATTERNS = []
for _sub in ("systemic", "localized", "hormonal", "mortality"):
    _PC_ENDPOINT_PATTERNS.extend(get_prostate_cancer_endpoint_patterns(_sub))

# Prostate-cancer arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_PC_ARM_FULL = [
    # AR-pathway inhibitors / systemic agents
    (r"abiraterone(?:\s+acetate)?|zytiga", "abiraterone"),
    (r"enzalutamide|xtandi", "enzalutamide"),
    (r"apalutamide|erleada", "apalutamide"),
    (r"darolutamide|nubeqa", "darolutamide"),
    (r"cabazitaxel|jevtana", "cabazitaxel"),
    (r"docetaxel", "docetaxel"),
    (r"olaparib", "olaparib"),
    (r"\[?177lu\]?[- ]?(?:lu[- ]?)?psma[- ]?617|lutetium[- ]?177|pluvicto", "lu177-psma"),
    (r"sipuleucel[- ]?t|provenge", "sipuleucel-t"),
    (r"radium[- ]?223|xofigo", "radium-223"),
    # ADT agents
    (r"leuprolide|leuprorelin", "leuprolide"),
    (r"goserelin|zoladex", "goserelin"),
    (r"triptorelin", "triptorelin"),
    (r"degarelix|firmagon", "degarelix"),
    (r"relugolix|orgovyx", "relugolix"),
    (r"bicalutamide", "bicalutamide"),
    (r"androgen[- ]deprivation\s+therapy(?:\s+alone)?", "adt"),
    # local modalities
    (r"radical\s+prostatectomy", "prostatectomy"),
    (r"external[- ]beam\s+radi\w*|intensity[- ]modulated\s+radi\w*|"
     r"radiotherapy|radiation\s+therapy|stereotactic\s+body\s+radi\w*", "radiotherapy"),
    (r"brachytherapy", "brachytherapy"),
    (r"active\s+surveillance", "active-surveillance"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_PC_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bADT\b", "adt"),
    (r"\bEBRT\b|\bIMRT\b|\bSBRT\b", "radiotherapy"),
    (r"\bAS\b(?=\s+(?:arm|group))", "active-surveillance"),
]
_PC_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _PC_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _PC_ARM_ABBREV])

# Prostate-cancer continuous outcomes; serum PSA is conventionally log-normal.
# (Testosterone suppression is reported as a proportion reaching castrate level,
# so it stays a binary 2x2 endpoint, not continuous.)
_PC_CONTINUOUS = {"PSA_LEVEL", "QOL"}
_PC_LOGNORMAL = {"PSA_LEVEL"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_PC_ENDPOINT_PATTERNS,
                                arm_compiled=_PC_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_PC_ENDPOINT_PATTERNS,
                               arm_compiled=_PC_ARM_COMPILED,
                               continuous_endpoints=_PC_CONTINUOUS,
                               lognormal_endpoints=_PC_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_PC_ENDPOINT_PATTERNS,
                              arm_compiled=_PC_ARM_COMPILED,
                              continuous_endpoints=_PC_CONTINUOUS,
                              lognormal_endpoints=_PC_LOGNORMAL)
