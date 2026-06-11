"""
Arm-level / 2x2 + continuous extraction for urinary-incontinence / OAB trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with UI/OAB endpoints
and medical / device / surgical arm labels:

  binary outcomes (continence / dry rate, objective cure, treatment response,
    urinary retention, UTI, dry mouth, constipation) -> 2x2 events/N per arm
  continuous (UUI / incontinence episodes, micturition frequency, urgency
    episodes, nocturia, pad weight, ICIQ / OAB-q / KHQ scores) -> mean/SD per arm,
    pooled on the natural scale (MD/SMD).
"""
import re
from typing import Dict, List

from .urinary_incontinence import get_urinary_incontinence_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# UI/OAB endpoint patterns (string, endpoint) across all subspecialties.
_UI_ENDPOINT_PATTERNS = []
for _sub in ("oab", "sui", "procedural", "qol"):
    _UI_ENDPOINT_PATTERNS.extend(get_urinary_incontinence_endpoint_patterns(_sub))

# Medical / device / surgical arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_UI_ARM_FULL = [
    # beta-3 agonists
    (r"mirabegron", "mirabegron"),
    (r"vibegron", "vibegron"),
    # antimuscarinics
    (r"solifenacin", "solifenacin"),
    (r"tolterodine(?:\s+extended[- ]release)?", "tolterodine"),
    (r"fesoterodine", "fesoterodine"),
    (r"oxybutynin", "oxybutynin"),
    (r"darifenacin", "darifenacin"),
    (r"trospium", "trospium"),
    # SUI medical / training
    (r"duloxetine", "duloxetine"),
    (r"pelvic[- ]floor\s+muscle\s+training|pelvic[- ]floor\s+(?:exercise|rehabilitation)",
     "pfmt"),
    # procedural / device
    (r"onabotulinumtoxin\s?a?|botulinum\s+toxin|intradetrusor\s+botulinum", "botulinum-toxin"),
    (r"sacral\s+neuromodulation", "sacral-neuromodulation"),
    (r"percutaneous\s+tibial\s+nerve\s+stimulation|tibial\s+nerve\s+stimulation", "ptns"),
    # surgical SUI
    (r"midurethral\s+sling|tension[- ]free\s+vaginal\s+tape", "midurethral-sling"),
    (r"transobturator(?:\s+tape)?", "transobturator-tape"),
    (r"burch\s+colposuspension|colposuspension", "colposuspension"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"sham\s+(?:procedure|stimulation)", "sham"),
    (r"behaviou?ral\s+therapy|bladder\s+training", "behavioural-therapy"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_UI_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bPFMT\b", "pfmt"),
    (r"\bPTNS\b", "ptns"),
    (r"\bSNM\b", "sacral-neuromodulation"),
    (r"\bTVT\b", "midurethral-sling"),
    (r"\bTOT\b", "transobturator-tape"),
    (r"\bBoNT\b|\bBTX\b", "botulinum-toxin"),
]
_UI_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _UI_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _UI_ARM_ABBREV])

# UI/OAB continuous outcomes (linear scales; none log-normal).
_UI_CONTINUOUS = {"UUI_EPISODES", "MICTURITION_FREQUENCY", "URGENCY_EPISODES",
                  "NOCTURIA", "INCONTINENCE_EPISODES", "PAD_TEST", "ICIQ",
                  "OAB_Q", "KHQ"}
_UI_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_UI_ENDPOINT_PATTERNS,
                                arm_compiled=_UI_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_UI_ENDPOINT_PATTERNS,
                               arm_compiled=_UI_ARM_COMPILED,
                               continuous_endpoints=_UI_CONTINUOUS,
                               lognormal_endpoints=_UI_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_UI_ENDPOINT_PATTERNS,
                              arm_compiled=_UI_ARM_COMPILED,
                              continuous_endpoints=_UI_CONTINUOUS,
                              lognormal_endpoints=_UI_LOGNORMAL)
