"""
Arm-level / 2x2 + continuous extraction for type-2 diabetes trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with diabetes
endpoints and glucose-lowering drug-class arm labels:

  binary outcomes (HbA1c-target attainment, MACE, HF hospitalisation, ESKD,
    severe/documented hypoglycaemia, retinopathy, amputation, DKA) -> 2x2 events/N
  continuous (HbA1c change, fasting plasma glucose, body weight, eGFR slope,
    time-in-range) -> mean+SD / median+IQR; UACR -> log-normal, pool on the log
    scale (use GMR, not raw MD).
"""
import re
from typing import Dict, List

from .diabetes import get_diabetes_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Diabetes endpoint patterns (string, endpoint) across all subspecialties.
_DIABETES_ENDPOINT_PATTERNS = []
for _sub in ("glycemic", "cardiorenal", "hypoglycemia", "complications"):
    _DIABETES_ENDPOINT_PATTERNS.extend(get_diabetes_endpoint_patterns(_sub))

# Glucose-lowering / comparator arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token never matches).
_DIABETES_ARM_FULL = [
    (r"metformin", "metformin"),
    # SGLT2 inhibitors
    (r"empagliflozin", "empagliflozin"),
    (r"dapagliflozin", "dapagliflozin"),
    (r"canagliflozin", "canagliflozin"),
    (r"ertugliflozin", "ertugliflozin"),
    (r"sotagliflozin", "sotagliflozin"),
    (r"sglt[- ]?2\s+inhibitor", "sglt2-inhibitor"),
    # GLP-1 receptor agonists + dual agonist
    (r"liraglutide", "liraglutide"),
    (r"semaglutide", "semaglutide"),
    (r"dulaglutide", "dulaglutide"),
    (r"exenatide", "exenatide"),
    (r"lixisenatide", "lixisenatide"),
    (r"albiglutide", "albiglutide"),
    (r"tirzepatide", "tirzepatide"),
    (r"glp[- ]?1\s+receptor\s+agonist", "glp1-ra"),
    # DPP-4 inhibitors
    (r"sitagliptin", "sitagliptin"),
    (r"saxagliptin", "saxagliptin"),
    (r"linagliptin", "linagliptin"),
    (r"alogliptin", "alogliptin"),
    (r"vildagliptin", "vildagliptin"),
    # sulfonylureas / TZD
    (r"glimepiride", "glimepiride"),
    (r"gliclazide", "gliclazide"),
    (r"glibenclamide|glyburide", "glibenclamide"),
    (r"glipizide", "glipizide"),
    (r"sulfonylurea|sulphonylurea", "sulfonylurea"),
    (r"pioglitazone", "pioglitazone"),
    (r"rosiglitazone", "rosiglitazone"),
    # insulin
    (r"insulin\s+glargine", "insulin-glargine"),
    (r"insulin\s+degludec", "insulin-degludec"),
    (r"insulin\s+detemir", "insulin-detemir"),
    (r"basal\s+insulin", "basal-insulin"),
    (r"\binsulin\b", "insulin"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"lifestyle\s+(?:intervention|modification)|diet\s+and\s+exercise", "lifestyle"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_DIABETES_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bEMPA\b", "empagliflozin"),
    (r"\bDAPA\b", "dapagliflozin"),
    (r"\bCANA\b", "canagliflozin"),
    (r"\bSEMA\b", "semaglutide"),
    (r"\bMET\b", "metformin"),
    (r"\bSU\b", "sulfonylurea"),
    (r"\bGLAR\b", "insulin-glargine"),
]
_DIABETES_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _DIABETES_ARM_FULL]
                          + [(re.compile(p), n) for p, n in _DIABETES_ARM_ABBREV])

# Diabetes continuous outcomes; UACR is log-normal (pool on log scale / use GMR).
_DIABETES_CONTINUOUS = {"HBA1C_REDUCTION", "FASTING_PLASMA_GLUCOSE", "BODY_WEIGHT",
                        "TIME_IN_RANGE", "EGFR_SLOPE", "UACR"}
_DIABETES_LOGNORMAL = {"UACR"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_DIABETES_ENDPOINT_PATTERNS,
                                arm_compiled=_DIABETES_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_DIABETES_ENDPOINT_PATTERNS,
                               arm_compiled=_DIABETES_ARM_COMPILED,
                               continuous_endpoints=_DIABETES_CONTINUOUS,
                               lognormal_endpoints=_DIABETES_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_DIABETES_ENDPOINT_PATTERNS,
                              arm_compiled=_DIABETES_ARM_COMPILED,
                              continuous_endpoints=_DIABETES_CONTINUOUS,
                              lognormal_endpoints=_DIABETES_LOGNORMAL)
