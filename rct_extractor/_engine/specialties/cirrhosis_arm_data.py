"""
Arm-level / 2x2 + continuous extraction for cirrhosis / decompensated liver
disease trials.

Thin wrapper over the shared malaria_arm_data engine configured with cirrhosis
endpoints and arm labels:

  binary outcomes (variceal bleeding / rebleeding, HRS reversal, SBP, HE
    recurrence/reversal, ACLF, mortality, readmission) -> 2x2 events/N per arm.
  continuous outcomes (HVPG, MELD) -> per-arm mean +/- SD, pooled as a mean
    difference.
"""
import re
from typing import Dict, List

from .cirrhosis import get_cirrhosis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_CIRR_ENDPOINT_PATTERNS = []
for _sub in ("portal_hypertension", "decompensation", "encephalopathy", "progression"):
    _CIRR_ENDPOINT_PATTERNS.extend(get_cirrhosis_endpoint_patterns(_sub))

_CIRR_ARM_FULL = [
    (r"carvedilol", "carvedilol"),
    (r"propranolol", "propranolol"),
    (r"nadolol", "nadolol"),
    (r"terlipressin", "terlipressin"),
    (r"midodrine", "midodrine"),
    (r"octreotide", "octreotide"),
    (r"norfloxacin", "norfloxacin"),
    (r"rifaximin", "rifaximin"),
    (r"lactulose", "lactulose"),
    (r"l[- ]ornithine\s+l[- ]aspartate|\blola\b", "LOLA"),
    (r"albumin", "albumin"),
    (r"simvastatin|statin", "statin"),
    (r"tolvaptan", "tolvaptan"),
    (r"band[\s-]+ligation|endoscopic\s+(?:variceal\s+)?ligation|\bevl\b", "band-ligation"),
    (r"transjugular\s+intrahepatic|\btips\b", "TIPS"),
    (r"\bplacebo\b", "placebo"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care|standard\s+(?:medical\s+)?(?:therapy|treatment)",
     "standard-of-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"active\s+(?:treatment|comparator)", "active"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_CIRR_ARM_ABBREV = [
    (r"\bNSBB\b", "beta-blocker"),
    (r"\bTIPS\b", "TIPS"),
    (r"\bEVL\b", "band-ligation"),
]
_CIRR_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _CIRR_ARM_FULL]
                      + [(re.compile(p), n) for p, n in _CIRR_ARM_ABBREV])

_CIRR_CONTINUOUS = {"HVPG", "MELD"}
_CIRR_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_CIRR_ENDPOINT_PATTERNS,
                                arm_compiled=_CIRR_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_CIRR_ENDPOINT_PATTERNS,
                               arm_compiled=_CIRR_ARM_COMPILED,
                               continuous_endpoints=_CIRR_CONTINUOUS,
                               lognormal_endpoints=_CIRR_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_CIRR_ENDPOINT_PATTERNS,
                              arm_compiled=_CIRR_ARM_COMPILED,
                              continuous_endpoints=_CIRR_CONTINUOUS,
                              lognormal_endpoints=_CIRR_LOGNORMAL)
