"""
Arm-level / 2x2 + continuous extraction for sepsis / septic shock trials.

Thin wrapper over the shared malaria_arm_data engine configured with sepsis
endpoints and arm labels:

  binary outcomes (28-/90-day mortality, shock reversal, new RRT/AKI, adverse
    events) -> 2x2 events/N per arm.
  continuous outcomes (vasopressor-/ventilator-/organ-support-free days, SOFA,
    length of stay) -> per-arm mean +/- SD, pooled as a mean difference.
"""
import re
from typing import Dict, List

from .sepsis import get_sepsis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_SEP_ENDPOINT_PATTERNS = []
for _sub in ("hemodynamic", "adjunctive", "antimicrobial_source", "organ_support"):
    _SEP_ENDPOINT_PATTERNS.extend(get_sepsis_endpoint_patterns(_sub))

_SEP_ARM_FULL = [
    (r"noradrenaline|norepinephrine", "norepinephrine"),
    (r"vasopressin", "vasopressin"),
    (r"angiotensin\s+ii", "angiotensin-II"),
    (r"terlipressin", "terlipressin"),
    (r"dopamine", "dopamine"),
    (r"dobutamine", "dobutamine"),
    (r"hydrocortisone(?:\s*(?:plus|and|\+)\s*fludrocortisone)?", "hydrocortisone"),
    (r"fludrocortisone", "fludrocortisone"),
    (r"vitamin\s+c|ascorbic\s+acid", "vitamin-C"),
    (r"thiamine", "thiamine"),
    (r"balanced\s+crystalloid|lactated\s+ringer|plasma[- ]?lyte", "balanced-crystalloid"),
    (r"normal\s+saline|0\.9\s*%\s+saline|\bsaline\b", "saline"),
    (r"albumin", "albumin"),
    (r"meropenem|piperacillin(?:[- /]tazobactam)?", "broad-spectrum-antibiotic"),
    (r"\bplacebo\b", "placebo"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care", "standard-of-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"active\s+(?:treatment|comparator)", "active"),
    (r"early\s+(?:group|strategy)", "early"),
    (r"(?:delayed|standard)\s+(?:group|strategy)", "delayed"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_SEP_ARM_ABBREV = [
    (r"\bNE\b", "norepinephrine"),
    (r"\bAVP\b", "vasopressin"),
    (r"\bNS\b", "saline"),
]
_SEP_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _SEP_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _SEP_ARM_ABBREV])

_SEP_CONTINUOUS = {"VASOPRESSOR_FREE_DAYS", "VENTILATOR_FREE_DAYS",
                   "ORGAN_SUPPORT_FREE_DAYS", "SOFA", "LENGTH_OF_STAY",
                   "ANTIBIOTIC_DURATION"}
_SEP_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_SEP_ENDPOINT_PATTERNS,
                                arm_compiled=_SEP_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_SEP_ENDPOINT_PATTERNS,
                               arm_compiled=_SEP_ARM_COMPILED,
                               continuous_endpoints=_SEP_CONTINUOUS,
                               lognormal_endpoints=_SEP_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_SEP_ENDPOINT_PATTERNS,
                              arm_compiled=_SEP_ARM_COMPILED,
                              continuous_endpoints=_SEP_CONTINUOUS,
                              lognormal_endpoints=_SEP_LOGNORMAL)
