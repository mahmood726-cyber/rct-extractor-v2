"""
Arm-level / 2x2 + continuous extraction for interstitial-lung-disease /
pulmonary-fibrosis trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
ILD endpoints and ILD-therapy drug-class arm labels:

  binary (disease progression, acute exacerbation, mortality, hospitalisation)
    -> 2x2 events/N per arm.
  continuous (FVC / ppFVC, DLCO) -> mean+SD / median+IQR, pooled as MD/SMD on the
    natural scale.
"""
import re
from typing import Dict, List

from .interstitial_lung_disease import get_interstitial_lung_disease_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_ILD_ENDPOINT_PATTERNS = []
for _sub in ("function", "progression", "mortality", "acute_events"):
    _ILD_ENDPOINT_PATTERNS.extend(get_interstitial_lung_disease_endpoint_patterns(_sub))

# ILD-therapy arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE.
_ILD_ARM_FULL = [
    # antifibrotics
    (r"nintedanib", "nintedanib"),
    (r"pirfenidone", "pirfenidone"),
    # immunosuppressants
    (r"mycophenolate\s+mofetil|mycophenolate|mycophenolic\s+acid", "mycophenolate"),
    (r"azathioprine", "azathioprine"),
    (r"cyclophosphamide|cyclophosphamide", "cyclophosphamide"),
    # biologics
    (r"rituximab", "rituximab"),
    (r"tocilizumab", "tocilizumab"),
    # other
    (r"n[- ]?acetylcysteine|\bnac\b", "n-acetylcysteine"),
    (r"corticosteroid|prednisone|prednisolone", "corticosteroid"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|best\s+supportive\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_ILD_ARM_ABBREV = [
    (r"\bMMF\b", "mycophenolate"),
    (r"\bNAC\b", "n-acetylcysteine"),
]
_ILD_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _ILD_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _ILD_ARM_ABBREV])

# ILD continuous outcomes (lung function; natural scale).
_ILD_CONTINUOUS = {"FVC", "PPFVC", "DLCO"}
_ILD_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_ILD_ENDPOINT_PATTERNS,
                                arm_compiled=_ILD_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_ILD_ENDPOINT_PATTERNS,
                               arm_compiled=_ILD_ARM_COMPILED,
                               continuous_endpoints=_ILD_CONTINUOUS,
                               lognormal_endpoints=_ILD_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_ILD_ENDPOINT_PATTERNS,
                              arm_compiled=_ILD_ARM_COMPILED,
                              continuous_endpoints=_ILD_CONTINUOUS,
                              lognormal_endpoints=_ILD_LOGNORMAL)
