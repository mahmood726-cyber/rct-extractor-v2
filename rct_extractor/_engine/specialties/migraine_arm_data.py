"""
Arm-level / 2x2 + continuous extraction for migraine trials.

Thin wrapper over the shared malaria_arm_data engine configured with migraine
endpoints and migraine arm labels:

  binary outcomes (2-h pain freedom / relief, MBS freedom, >=50% responder,
    rescue medication, adverse events) -> 2x2 events/N per arm.
  continuous outcomes (monthly migraine/headache days, acute medication days,
    MIDAS/HIT-6 disability) -> per-arm mean +/- SD, pooled as a mean difference.

Migraine interventions: triptans, gepants, lasmiditan (acute); anti-CGRP mAbs,
atogepant, topiramate, propranolol, onabotulinumtoxinA (preventive); placebo.
"""
import re
from typing import Dict, List

from .migraine import get_migraine_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_MIG_ENDPOINT_PATTERNS = []
for _sub in ("acute", "preventive", "chronic", "device_neuromod"):
    _MIG_ENDPOINT_PATTERNS.extend(get_migraine_endpoint_patterns(_sub))

_MIG_ARM_FULL = [
    (r"ubrogepant", "ubrogepant"),
    (r"rimegepant", "rimegepant"),
    (r"zavegepant", "zavegepant"),
    (r"atogepant", "atogepant"),
    (r"lasmiditan", "lasmiditan"),
    (r"sumatriptan", "sumatriptan"),
    (r"rizatriptan", "rizatriptan"),
    (r"eletriptan", "eletriptan"),
    (r"zolmitriptan", "zolmitriptan"),
    (r"naratriptan", "naratriptan"),
    (r"erenumab", "erenumab"),
    (r"fremanezumab", "fremanezumab"),
    (r"galcanezumab", "galcanezumab"),
    (r"eptinezumab", "eptinezumab"),
    (r"topiramate", "topiramate"),
    (r"propranolol", "propranolol"),
    (r"amitriptyline", "amitriptyline"),
    (r"onabotulinumtoxin\s?a|botulinum\s+toxin|botox", "onabotulinumtoxinA"),
    (r"\bplacebo\b", "placebo"),
    (r"\bsham\b", "sham"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care", "standard-of-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"active\s+(?:treatment|comparator)", "active"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_MIG_ARM_ABBREV = []
_MIG_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _MIG_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _MIG_ARM_ABBREV])

_MIG_CONTINUOUS = {"MMD", "MHD", "ACUTE_MED_DAYS", "DISABILITY"}
_MIG_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_MIG_ENDPOINT_PATTERNS,
                                arm_compiled=_MIG_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_MIG_ENDPOINT_PATTERNS,
                               arm_compiled=_MIG_ARM_COMPILED,
                               continuous_endpoints=_MIG_CONTINUOUS,
                               lognormal_endpoints=_MIG_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_MIG_ENDPOINT_PATTERNS,
                              arm_compiled=_MIG_ARM_COMPILED,
                              continuous_endpoints=_MIG_CONTINUOUS,
                              lognormal_endpoints=_MIG_LOGNORMAL)
