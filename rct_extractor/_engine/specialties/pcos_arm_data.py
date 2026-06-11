"""
Arm-level / 2x2 + continuous extraction for polycystic-ovary-syndrome (PCOS) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
PCOS endpoints and PCOS drug / intervention arm labels:

  binary (ovulation, clinical pregnancy, live birth, miscarriage, multiple
    pregnancy, menstrual regularity, OHSS, GI adverse events) -> 2x2 events/N.
  continuous (BMI / body weight, HOMA-IR, HbA1c, testosterone, SHBG,
    Ferriman-Gallwey hirsutism score) -> mean+SD / median+IQR, pooled as MD/SMD.
"""
import re
from typing import Dict, List

from .pcos import get_pcos_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_PCOS_ENDPOINT_PATTERNS = []
for _sub in ("reproductive", "metabolic", "androgen", "safety"):
    _PCOS_ENDPOINT_PATTERNS.extend(get_pcos_endpoint_patterns(_sub))

# PCOS drug / intervention arm labels. Full names case-insensitive.
_PCOS_ARM_FULL = [
    (r"letrozole", "letrozole"),
    (r"clomi(?:phene|fene)(?:\s+citrate)?", "clomifene"),
    (r"metformin", "metformin"),
    (r"myo[- ]?inositol|inositol", "inositol"),
    (r"spironolactone", "spironolactone"),
    (r"gonadotrop(?:h)?in|\bfsh\b|follicle[- ]stimulating", "gonadotropin"),
    (r"oral\s+contraceptive|combined\s+oral\s+contraceptive|ethinyl\s+(?:estradiol|oestradiol)",
     "oral-contraceptive"),
    (r"laparoscopic\s+ovarian\s+(?:drilling|diathermy)", "ovarian-drilling"),
    (r"pioglitazone|rosiglitazone|thiazolidinedione", "thiazolidinedione"),
    (r"orlistat", "orlistat"),
    (r"liraglutide|semaglutide|exenatide", "glp1-agonist"),
    (r"lifestyle\s+(?:intervention|modification)|diet(?:ary)?\s+intervention", "lifestyle"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_PCOS_ARM_ABBREV = [
    (r"\bOCP\b", "oral-contraceptive"),
    (r"\bLOD\b", "ovarian-drilling"),
]
_PCOS_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _PCOS_ARM_FULL]
                      + [(re.compile(p), n) for p, n in _PCOS_ARM_ABBREV])

# PCOS continuous outcomes (metabolic + androgen; natural scale).
_PCOS_CONTINUOUS = {"BMI_WEIGHT", "HOMA_IR", "HBA1C", "TESTOSTERONE", "SHBG", "HIRSUTISM"}
_PCOS_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_PCOS_ENDPOINT_PATTERNS,
                                arm_compiled=_PCOS_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_PCOS_ENDPOINT_PATTERNS,
                               arm_compiled=_PCOS_ARM_COMPILED,
                               continuous_endpoints=_PCOS_CONTINUOUS,
                               lognormal_endpoints=_PCOS_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_PCOS_ENDPOINT_PATTERNS,
                              arm_compiled=_PCOS_ARM_COMPILED,
                              continuous_endpoints=_PCOS_CONTINUOUS,
                              lognormal_endpoints=_PCOS_LOGNORMAL)
