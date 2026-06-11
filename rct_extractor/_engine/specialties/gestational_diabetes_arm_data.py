"""
Arm-level / 2x2 + continuous extraction for gestational-diabetes (GDM) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with GDM endpoints
and glucose-lowering / lifestyle arm labels:

  binary outcomes (macrosomia, LGA, neonatal hypoglycaemia, pre-eclampsia,
    caesarean, insulin requirement, NICU, shoulder dystocia, GDM diagnosis) -> 2x2
    events/N per arm
  continuous (fasting/postprandial glucose, HbA1c, birth weight, gestational
    weight gain) -> mean/SD per arm, pooled on the natural scale (MD/SMD).
"""
import re
from typing import Dict, List

from .gestational_diabetes import get_gestational_diabetes_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# GDM endpoint patterns (string, endpoint) across all subspecialties.
_GDM_ENDPOINT_PATTERNS = []
for _sub in ("glycemic", "maternal", "neonatal", "screening"):
    _GDM_ENDPOINT_PATTERNS.extend(get_gestational_diabetes_endpoint_patterns(_sub))

# Glucose-lowering / lifestyle arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does not
# match).
_GDM_ARM_FULL = [
    (r"metformin", "metformin"),
    (r"glyburide|glibenclamide", "glyburide"),
    (r"\binsulin(?:\s+therapy)?\b", "insulin"),
    (r"medical\s+nutrition\s+therapy|dietary\s+(?:therapy|intervention|advice)|"
     r"diet(?:\s+alone|\s+therapy)?", "diet"),
    (r"lifestyle\s+(?:intervention|modification)|lifestyle", "lifestyle"),
    (r"myo[- ]?inositol|inositol", "inositol"),
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|routine\s+care", "standard-of-care"),
    (r"no\s+treatment|observation|expectant", "no-treatment"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_GDM_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bMNT\b", "diet"),
    (r"\bMET\b", "metformin"),
]
_GDM_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _GDM_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _GDM_ARM_ABBREV])

# GDM continuous outcomes (linear scales; none log-normal).
_GDM_CONTINUOUS = {"FASTING_GLUCOSE", "POSTPRANDIAL_GLUCOSE", "HBA1C", "BIRTH_WEIGHT",
                   "GESTATIONAL_WEIGHT_GAIN"}
_GDM_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_GDM_ENDPOINT_PATTERNS,
                                arm_compiled=_GDM_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_GDM_ENDPOINT_PATTERNS,
                               arm_compiled=_GDM_ARM_COMPILED,
                               continuous_endpoints=_GDM_CONTINUOUS,
                               lognormal_endpoints=_GDM_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_GDM_ENDPOINT_PATTERNS,
                              arm_compiled=_GDM_ARM_COMPILED,
                              continuous_endpoints=_GDM_CONTINUOUS,
                              lognormal_endpoints=_GDM_LOGNORMAL)
