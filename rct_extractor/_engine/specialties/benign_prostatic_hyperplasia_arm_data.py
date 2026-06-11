"""
Arm-level / 2x2 + continuous extraction for benign-prostatic-hyperplasia (BPH /
LUTS) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with BPH endpoints
and medical / surgical arm labels:

  binary / time-to-event outcomes (acute urinary retention, BPH surgery, clinical
    progression, symptom responder, ejaculatory dysfunction) -> 2x2 events/N per arm
  continuous (IPSS total / storage / voiding, IPSS QoL, Qmax, post-void residual,
    prostate volume) -> mean/SD per arm, pooled on the natural scale (MD/SMD).
"""
import re
from typing import Dict, List

from .benign_prostatic_hyperplasia import get_benign_prostatic_hyperplasia_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# BPH endpoint patterns (string, endpoint) across all subspecialties.
_BPH_ENDPOINT_PATTERNS = []
for _sub in ("symptoms", "flow", "progression", "sexual"):
    _BPH_ENDPOINT_PATTERNS.extend(get_benign_prostatic_hyperplasia_endpoint_patterns(_sub))

# Medical / surgical arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_BPH_ARM_FULL = [
    # alpha-blockers
    (r"tamsulosin", "tamsulosin"),
    (r"alfuzosin", "alfuzosin"),
    (r"silodosin", "silodosin"),
    (r"doxazosin", "doxazosin"),
    (r"terazosin", "terazosin"),
    # 5-ARI
    (r"finasteride", "finasteride"),
    (r"dutasteride", "dutasteride"),
    # PDE5 / combination
    (r"tadalafil", "tadalafil"),
    (r"combination\s+(?:therapy|treatment)", "combination"),
    # procedures
    (r"transurethral\s+resection(?:\s+of\s+the\s+prostate)?", "turp"),
    (r"holmium\s+laser\s+enucleation|holep", "holep"),
    (r"photoselective\s+vapori[sz]ation|greenlight|pvp", "greenlight"),
    (r"prostatic\s+urethral\s+lift|urolift", "urolift"),
    (r"water\s+vapou?r\s+thermal\s+therapy|rezum", "rezum"),
    (r"prostatic\s+artery\s+emboli[sz]ation", "pae"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"sham\s+(?:procedure|surgery)", "sham"),
    (r"watchful\s+waiting|active\s+surveillance", "watchful-waiting"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_BPH_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bTURP\b", "turp"),
    (r"\bHoLEP\b", "holep"),
    (r"\bPVP\b", "greenlight"),
    (r"\bPUL\b", "urolift"),
    (r"\bPAE\b", "pae"),
]
_BPH_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _BPH_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _BPH_ARM_ABBREV])

# BPH continuous outcomes (linear scales; none log-normal).
_BPH_CONTINUOUS = {"IPSS_TOTAL", "IPSS_STORAGE", "IPSS_VOIDING", "IPSS_QOL",
                   "QMAX", "POST_VOID_RESIDUAL", "PROSTATE_VOLUME"}
_BPH_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_BPH_ENDPOINT_PATTERNS,
                                arm_compiled=_BPH_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_BPH_ENDPOINT_PATTERNS,
                               arm_compiled=_BPH_ARM_COMPILED,
                               continuous_endpoints=_BPH_CONTINUOUS,
                               lognormal_endpoints=_BPH_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_BPH_ENDPOINT_PATTERNS,
                              arm_compiled=_BPH_ARM_COMPILED,
                              continuous_endpoints=_BPH_CONTINUOUS,
                              lognormal_endpoints=_BPH_LOGNORMAL)
