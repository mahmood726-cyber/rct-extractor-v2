"""
Arm-level / 2x2 + continuous extraction for menopause / HRT trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with menopause/HRT
endpoints and hormone-therapy / SERM / NK3-antagonist arm labels:

  binary / time-to-event outcomes (fracture, breast cancer, VTE, stroke, CHD,
    VMS responder, vulvovaginal atrophy, endometrial hyperplasia) -> 2x2
    events/N per arm
  continuous (VMS frequency/severity, BMD %, vaginal pH/maturation index, MENQOL
    quality of life) -> mean/SD per arm, pooled on the natural scale (MD/SMD).
"""
import re
from typing import Dict, List

from .menopause_hrt import get_menopause_hrt_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Menopause/HRT endpoint patterns (string, endpoint) across all subspecialties.
_MHT_ENDPOINT_PATTERNS = []
for _sub in ("vasomotor", "genitourinary", "bone", "safety"):
    _MHT_ENDPOINT_PATTERNS.extend(get_menopause_hrt_endpoint_patterns(_sub))

# Hormone-therapy / SERM / NK3 arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does not
# match).
_MHT_ARM_FULL = [
    # NK3 antagonists
    (r"fezolinetant", "fezolinetant"),
    (r"elinzanetant", "elinzanetant"),
    # systemic oestrogen / combinations
    (r"conjugated\s+equine\s+(?:o?estrogens?)|conjugated\s+o?estrogens?", "cee"),
    (r"o?estradiol(?:\s+valerate)?", "estradiol"),
    (r"o?estrogen(?:\s+plus\s+progest\w+)?|o?estrogen[- ]progest\w+", "estrogen"),
    (r"tibolone", "tibolone"),
    (r"medroxyprogesterone|\bmpa\b", "medroxyprogesterone"),
    # SERMs / GSM agents
    (r"raloxifene", "raloxifene"),
    (r"bazedoxifene", "bazedoxifene"),
    (r"ospemifene", "ospemifene"),
    (r"prasterone|intravaginal\s+dhea|vaginal\s+dhea", "prasterone"),
    # non-hormonal VMS
    (r"paroxetine", "paroxetine"),
    (r"venlafaxine|desvenlafaxine", "venlafaxine"),
    (r"gabapentin", "gabapentin"),
    (r"clonidine", "clonidine"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"no\s+treatment|observation", "no-treatment"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_MHT_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bCEE\b", "cee"),
    (r"\bHRT\b|\bHT\b|\bMHT\b", "hormone-therapy"),
    (r"\bMPA\b", "medroxyprogesterone"),
    (r"\bDHEA\b", "prasterone"),
]
_MHT_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _MHT_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _MHT_ARM_ABBREV])

# Menopause/HRT continuous outcomes (linear scales; none log-normal).
_MHT_CONTINUOUS = {"HOT_FLUSHES", "NIGHT_SWEATS", "VMS_SEVERITY", "SLEEP",
                   "VAGINAL_DRYNESS", "GSM_DYSPAREUNIA", "VAGINAL_PH", "BMD",
                   "QUALITY_OF_LIFE"}
_MHT_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_MHT_ENDPOINT_PATTERNS,
                                arm_compiled=_MHT_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_MHT_ENDPOINT_PATTERNS,
                               arm_compiled=_MHT_ARM_COMPILED,
                               continuous_endpoints=_MHT_CONTINUOUS,
                               lognormal_endpoints=_MHT_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_MHT_ENDPOINT_PATTERNS,
                              arm_compiled=_MHT_ARM_COMPILED,
                              continuous_endpoints=_MHT_CONTINUOUS,
                              lognormal_endpoints=_MHT_LOGNORMAL)
