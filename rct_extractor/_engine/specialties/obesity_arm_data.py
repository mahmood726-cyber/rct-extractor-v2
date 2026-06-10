"""
Arm-level / 2x2 + continuous extraction for obesity / weight-management trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
obesity endpoints and anti-obesity drug / intervention arm labels:

  continuous (percent / absolute body-weight change, BMI, waist circumference,
    fat mass, SBP, HbA1c) -> mean+SD / median+IQR, pooled as MD/SMD.
  binary (>=5%/>=10%/>=15% weight-loss responders, GI adverse events,
    gallbladder events, discontinuation) -> 2x2 events/N per arm.
"""
import re
from typing import Dict, List

from .obesity import get_obesity_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_OB_ENDPOINT_PATTERNS = []
for _sub in ("weight_loss", "body_composition", "cardiometabolic", "safety"):
    _OB_ENDPOINT_PATTERNS.extend(get_obesity_endpoint_patterns(_sub))

# Anti-obesity drug / intervention arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE.
_OB_ARM_FULL = [
    # incretin-based
    (r"semaglutide", "semaglutide"),
    (r"liraglutide", "liraglutide"),
    (r"dulaglutide", "dulaglutide"),
    (r"exenatide", "exenatide"),
    (r"tirzepatide", "tirzepatide"),
    (r"retatrutide", "retatrutide"),
    (r"cagrilintide", "cagrilintide"),
    (r"survodutide", "survodutide"),
    (r"orforglipron", "orforglipron"),
    (r"glp[- ]?1\s+receptor\s+agonist", "glp1-receptor-agonist"),
    # non-incretin pharmacotherapy
    (r"orlistat", "orlistat"),
    (r"phentermine[\/ -]?topiramate|phentermine", "phentermine-topiramate"),
    (r"naltrexone[\/ -]?bupropion", "naltrexone-bupropion"),
    (r"setmelanotide", "setmelanotide"),
    (r"lorcaserin", "lorcaserin"),
    # non-drug
    (r"bariatric\s+surgery|sleeve\s+gastrectomy|gastric\s+bypass|roux[- ]en[- ]y",
     "bariatric-surgery"),
    (r"lifestyle\s+(?:intervention|modification|program(?:me)?)|diet(?:ary)?\s+intervention|"
     r"caloric\s+restriction|behavio(?:u)?ral\s+(?:intervention|therapy)", "lifestyle"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_OB_ARM_ABBREV = [
    (r"\bGLP-?1\b", "glp1-receptor-agonist"),
]
_OB_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _OB_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _OB_ARM_ABBREV])

# Obesity continuous outcomes (natural scale).
_OB_CONTINUOUS = {"BODY_WEIGHT_PCT_CHANGE", "WEIGHT_CHANGE_KG", "BMI_CHANGE",
                  "WAIST_CIRCUMFERENCE", "FAT_MASS", "SBP_CHANGE", "HBA1C_CHANGE"}
_OB_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_OB_ENDPOINT_PATTERNS,
                                arm_compiled=_OB_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_OB_ENDPOINT_PATTERNS,
                               arm_compiled=_OB_ARM_COMPILED,
                               continuous_endpoints=_OB_CONTINUOUS,
                               lognormal_endpoints=_OB_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_OB_ENDPOINT_PATTERNS,
                              arm_compiled=_OB_ARM_COMPILED,
                              continuous_endpoints=_OB_CONTINUOUS,
                              lognormal_endpoints=_OB_LOGNORMAL)
