"""
Arm-level / 2x2 + continuous extraction for trachoma trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with trachoma
endpoints and antibiotic / surgery / F&E arm labels:

  binary outcomes (active trachoma / TF, intense trachoma / TI, ocular-chlamydia
    infection, trichiasis / TT, trichiasis recurrence, corneal opacity, clean
    face, reinfection, mortality, adverse events, macrolide resistance)
    -> 2x2 events/N per arm
  continuous (visual acuity / logMAR -> mean+SD / median+IQR; chlamydial load and
    fly counts are right-skewed -> log-normal, pool on the log scale / GMR).
"""
import re
from typing import Dict, List

from .trachoma import get_trachoma_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Trachoma endpoint patterns (string, endpoint) across all subspecialties.
_TRACHOMA_ENDPOINT_PATTERNS = []
for _sub in ("mda", "surgery", "transmission", "mortality_safety"):
    _TRACHOMA_ENDPOINT_PATTERNS.extend(get_trachoma_endpoint_patterns(_sub))

# Antibiotic / surgery / F&E arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does not
# match).
_TRACHOMA_ARM_FULL = [
    # antibiotics
    (r"azithromycin", "azithromycin"),
    (r"tetracycline(?:\s+(?:1%\s+)?eye)?(?:\s+ointment)?", "tetracycline"),
    (r"doxycycline", "doxycycline"),
    (r"erythromycin", "erythromycin"),
    # MDA frequency arms
    (r"biannual|bi-annual|twice[- ]yearly\s+(?:azithromycin|treatment|mda)",
     "biannual-azithromycin"),
    (r"annual\s+(?:azithromycin|treatment|mda)", "annual-azithromycin"),
    # surgery
    (r"bilamellar\s+tarsal\s+rotation", "bilamellar-tarsal-rotation"),
    (r"posterior\s+lamellar\s+tarsal\s+rotation", "posterior-lamellar-tarsal-rotation"),
    (r"epilation", "epilation"),
    (r"trichiasis\s+surgery|eyelid\s+surgery|lid\s+surgery", "surgery"),
    # F&E / transmission
    (r"face[- ]washing|facial\s+cleanliness", "face-washing"),
    (r"fly\s+control|insecticide", "fly-control"),
    (r"environmental\s+improvement|latrine", "environmental"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"untreated(?:\s+(?:group|arm|control))?", "untreated"),
    (r"no\s+(?:surgery|treatment|intervention)", "no-treatment"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_TRACHOMA_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bBLTR\b", "bilamellar-tarsal-rotation"),
    (r"\bPLTR\b", "posterior-lamellar-tarsal-rotation"),
    (r"\bTEO\b", "tetracycline"),
]
_TRACHOMA_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _TRACHOMA_ARM_FULL]
                          + [(re.compile(p), n) for p, n in _TRACHOMA_ARM_ABBREV])

# Trachoma continuous outcomes; chlamydial load and fly counts are right-skewed
# and pooled on the log scale (GMR), visual acuity (logMAR) pools as a raw MD.
_TRACHOMA_CONTINUOUS = {"VISUAL_ACUITY", "INFECTION_LOAD", "FLY_DENSITY"}
_TRACHOMA_LOGNORMAL = {"INFECTION_LOAD", "FLY_DENSITY"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_TRACHOMA_ENDPOINT_PATTERNS,
                                arm_compiled=_TRACHOMA_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_TRACHOMA_ENDPOINT_PATTERNS,
                               arm_compiled=_TRACHOMA_ARM_COMPILED,
                               continuous_endpoints=_TRACHOMA_CONTINUOUS,
                               lognormal_endpoints=_TRACHOMA_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_TRACHOMA_ENDPOINT_PATTERNS,
                              arm_compiled=_TRACHOMA_ARM_COMPILED,
                              continuous_endpoints=_TRACHOMA_CONTINUOUS,
                              lognormal_endpoints=_TRACHOMA_LOGNORMAL)
