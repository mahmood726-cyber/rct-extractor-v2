"""
Arm-level / 2x2 + continuous extraction for thyroid-disorder trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
thyroid endpoints and thyroid drug / intervention arm labels:

  continuous (TSH, free T4/T3, total T4, TPO antibody, thyroid QoL) -> mean+SD /
    median+IQR, pooled as MD/SMD.
  binary (TSH normalisation, euthyroidism, remission, relapse, orbitopathy
    response, pregnancy loss, preterm birth, adverse events) -> 2x2 events/N.
"""
import re
from typing import Dict, List

from .thyroid import get_thyroid_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_THY_ENDPOINT_PATTERNS = []
for _sub in ("hypothyroidism", "hyperthyroidism", "thyroid_function", "outcomes"):
    _THY_ENDPOINT_PATTERNS.extend(get_thyroid_endpoint_patterns(_sub))

# Thyroid drug / intervention arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE.
_THY_ARM_FULL = [
    # hypothyroidism
    (r"levothyroxine|l[- ]?thyroxine", "levothyroxine"),
    (r"liothyronine", "liothyronine"),
    (r"combination\s+(?:therapy|lt4[\/+ -]*lt3|levothyroxine[\/+ -]*liothyronine)",
     "combination-lt4-lt3"),
    (r"desiccated\s+thyroid|natural\s+thyroid|armour\s+thyroid", "desiccated-thyroid"),
    # hyperthyroidism
    (r"methimazole|thiamazole", "methimazole"),
    (r"carbimazole", "carbimazole"),
    (r"propylthiouracil", "propylthiouracil"),
    (r"radioactive\s+iodine|radioiodine|iodine[- ]?131", "radioactive-iodine"),
    (r"thyroidectomy", "thyroidectomy"),
    (r"block[- ]and[- ]replace", "block-and-replace"),
    # adjuncts
    (r"selenium", "selenium"),
    (r"\bbeta[- ]blocker\b|propranolol", "beta-blocker"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"no\s+treatment|observation|watchful\s+waiting", "no-treatment"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_THY_ARM_ABBREV = [
    (r"\bLT4\b", "levothyroxine"),
    (r"\bLT3\b", "liothyronine"),
    (r"\bPTU\b", "propylthiouracil"),
    (r"\bMMI\b", "methimazole"),
    (r"\bRAI\b", "radioactive-iodine"),
    (r"\bATD\b", "antithyroid-drug"),
]
_THY_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _THY_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _THY_ARM_ABBREV])

# Thyroid continuous outcomes (lab levels + QoL; natural scale).
_THY_CONTINUOUS = {"TSH_LEVEL", "FT4_LEVEL", "FT3_LEVEL", "T4_LEVEL", "TPO_ANTIBODY",
                   "THYROID_QOL"}
_THY_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_THY_ENDPOINT_PATTERNS,
                                arm_compiled=_THY_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_THY_ENDPOINT_PATTERNS,
                               arm_compiled=_THY_ARM_COMPILED,
                               continuous_endpoints=_THY_CONTINUOUS,
                               lognormal_endpoints=_THY_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_THY_ENDPOINT_PATTERNS,
                              arm_compiled=_THY_ARM_COMPILED,
                              continuous_endpoints=_THY_CONTINUOUS,
                              lognormal_endpoints=_THY_LOGNORMAL)
