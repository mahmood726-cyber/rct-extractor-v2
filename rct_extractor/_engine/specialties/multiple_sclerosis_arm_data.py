"""
Arm-level / 2x2 + continuous extraction for multiple sclerosis trials.

Thin wrapper over the shared malaria_arm_data engine configured with MS endpoints
and MS arm labels:

  binary outcomes (relapse-free, NEDA, CDP, relapse recovery, adverse events)
    -> 2x2 events/N per arm.
  continuous outcomes (EDSS change, SDMT, T25FW, fatigue, spasticity, brain
    atrophy, lesion counts) -> per-arm mean +/- SD, pooled as a mean difference.

MS interventions: interferon beta / glatiramer / S1P modulators / fumarates /
teriflunomide / natalizumab / anti-CD20 mAbs / cladribine / alemtuzumab; symptom
agents (fampridine, nabiximols); placebo.
"""
import re
from typing import Dict, List

from .multiple_sclerosis import get_multiple_sclerosis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_MS_ENDPOINT_PATTERNS = []
for _sub in ("relapsing", "progressive", "symptomatic", "acute_relapse"):
    _MS_ENDPOINT_PATTERNS.extend(get_multiple_sclerosis_endpoint_patterns(_sub))

_MS_ARM_FULL = [
    (r"interferon\s+beta(?:[- ]1[ab])?|ifn[- ]?beta", "interferon-beta"),
    (r"glatiramer(?:\s+acetate)?", "glatiramer"),
    (r"natalizumab", "natalizumab"),
    (r"fingolimod", "fingolimod"),
    (r"ozanimod", "ozanimod"),
    (r"ponesimod", "ponesimod"),
    (r"siponimod", "siponimod"),
    (r"dimethyl\s+fumarate|diroximel\s+fumarate", "dimethyl-fumarate"),
    (r"teriflunomide", "teriflunomide"),
    (r"cladribine", "cladribine"),
    (r"ocrelizumab", "ocrelizumab"),
    (r"ofatumumab", "ofatumumab"),
    (r"ublituximab", "ublituximab"),
    (r"rituximab", "rituximab"),
    (r"alemtuzumab", "alemtuzumab"),
    (r"tolebrutinib", "tolebrutinib"),
    (r"fampridine|dalfampridine", "fampridine"),
    (r"nabiximols", "nabiximols"),
    (r"methylprednisolone", "methylprednisolone"),
    (r"plasma\s+exchange|plasmapheresis", "plasma-exchange"),
    (r"\bplacebo\b", "placebo"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care", "standard-of-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"active\s+(?:treatment|comparator)", "active"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_MS_ARM_ABBREV = [
    (r"\bIFN\b", "interferon-beta"),
    (r"\bGA\b", "glatiramer"),
    (r"\bDMF\b", "dimethyl-fumarate"),
    (r"\bIVMP\b", "methylprednisolone"),
]
_MS_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _MS_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _MS_ARM_ABBREV])

_MS_CONTINUOUS = {"EDSS_CHANGE", "SDMT", "T25FW", "FATIGUE", "SPASTICITY",
                  "BRAIN_ATROPHY", "GAD_LESIONS", "T2_LESIONS"}
_MS_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_MS_ENDPOINT_PATTERNS,
                                arm_compiled=_MS_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_MS_ENDPOINT_PATTERNS,
                               arm_compiled=_MS_ARM_COMPILED,
                               continuous_endpoints=_MS_CONTINUOUS,
                               lognormal_endpoints=_MS_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_MS_ENDPOINT_PATTERNS,
                              arm_compiled=_MS_ARM_COMPILED,
                              continuous_endpoints=_MS_CONTINUOUS,
                              lognormal_endpoints=_MS_LOGNORMAL)
