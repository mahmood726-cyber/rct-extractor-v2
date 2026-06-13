"""
Arm-level / 2x2 + continuous extraction for plastic / reconstructive surgery trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
plastic-surgery endpoints and reconstructive-technique arm labels:

  binary (flap failure / necrosis, implant loss, capsular contracture, SSI,
    dehiscence, haematoma, seroma, reoperation, hypertrophic scar) -> 2x2 events/N.
  continuous (BREAST-Q, scar-scale, patient satisfaction) -> mean+SD / median+IQR,
    pooled as MD/SMD on the natural scale.
"""
import re
from typing import Dict, List

from .plastic_reconstructive_surgery import get_plastic_reconstructive_surgery_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_PR_ENDPOINT_PATTERNS = []
for _sub in ("flap", "breast", "complications", "scar"):
    _PR_ENDPOINT_PATTERNS.extend(get_plastic_reconstructive_surgery_endpoint_patterns(_sub))

# Reconstructive-technique arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE.
_PR_ARM_FULL = [
    (r"free\s+flap", "free-flap"),
    (r"pedicled\s+flap", "pedicled-flap"),
    (r"deep\s+inferior\s+epigastric\s+perforator(?:\s+flap)?|diep\s+flap", "diep-flap"),
    (r"transverse\s+rectus\s+abdominis(?:\s+myocutaneous)?(?:\s+flap)?", "tram-flap"),
    (r"latissimus\s+dorsi(?:\s+flap)?", "latissimus-dorsi-flap"),
    (r"implant[- ]based\s+reconstruction|implant[- ]based|prosthetic\s+reconstruction", "implant-based"),
    (r"autologous\s+reconstruction|autologous", "autologous"),
    (r"acellular\s+dermal\s+matrix|\badm\b", "acellular-dermal-matrix"),
    (r"negative[- ]pressure\s+wound\s+therapy|\bnpwt\b|vacuum[- ]assisted\s+closure", "npwt"),
    (r"silicone\s+(?:gel|sheet|dressing)|silicone", "silicone"),
    (r"pressure\s+garment", "pressure-garment"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|conventional\s+(?:dressing|treatment|technique)",
     "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_PR_ARM_ABBREV = [
    (r"\bDIEP\b", "diep-flap"),
    (r"\bTRAM\b", "tram-flap"),
    (r"\bADM\b", "acellular-dermal-matrix"),
    (r"\bNPWT\b", "npwt"),
]
_PR_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _PR_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _PR_ARM_ABBREV])

# Plastic-surgery continuous outcomes (natural scale).
_PR_CONTINUOUS = {"BREAST_Q", "SCAR_QUALITY", "PATIENT_SATISFACTION"}
_PR_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_PR_ENDPOINT_PATTERNS,
                                arm_compiled=_PR_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_PR_ENDPOINT_PATTERNS,
                               arm_compiled=_PR_ARM_COMPILED,
                               continuous_endpoints=_PR_CONTINUOUS,
                               lognormal_endpoints=_PR_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_PR_ENDPOINT_PATTERNS,
                              arm_compiled=_PR_ARM_COMPILED,
                              continuous_endpoints=_PR_CONTINUOUS,
                              lognormal_endpoints=_PR_LOGNORMAL)
