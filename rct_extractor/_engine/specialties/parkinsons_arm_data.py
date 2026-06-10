"""
Arm-level / 2x2 + continuous extraction for Parkinson's disease trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with PD endpoints
and PD arm labels:

  binary outcomes (motor responder, dyskinesia, falls, psychosis response,
    adverse events) -> 2x2 events/N per arm.
  continuous outcomes (MDS-UPDRS Part III / total, ON/OFF time, PDQ-39 QoL,
    LEDD, cognition scales) -> per-arm mean +/- SD, pooled as a mean difference
    by the core effect-size engine.

PD interventions are named by drug (levodopa, pramipexole, rasagiline, ...),
by device (DBS, LCIG, apomorphine infusion), or by control/placebo arms.
"""
import re
from typing import Dict, List

from .parkinsons import get_parkinsons_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# PD endpoint patterns (string, endpoint) across all subspecialties.
_PD_ENDPOINT_PATTERNS = []
for _sub in ("motor", "device_advanced", "nonmotor", "neuroprotection"):
    _PD_ENDPOINT_PATTERNS.extend(get_parkinsons_endpoint_patterns(_sub))

# PD arm labels. Full drug/device names case-insensitive; bare abbreviations
# (DBS, LCIG, STN) matched case-sensitively so the common words don't collide.
_PD_ARM_FULL = [
    (r"levodopa[- ]carbidopa\s+intestinal\s+gel", "LCIG"),
    (r"levodopa(?:[- /]carbidopa)?|l[- ]?dopa", "levodopa"),
    (r"pramipexole", "pramipexole"),
    (r"ropinirole", "ropinirole"),
    (r"rotigotine", "rotigotine"),
    (r"apomorphine", "apomorphine"),
    (r"rasagiline", "rasagiline"),
    (r"selegiline", "selegiline"),
    (r"safinamide", "safinamide"),
    (r"entacapone", "entacapone"),
    (r"opicapone", "opicapone"),
    (r"tolcapone", "tolcapone"),
    (r"amantadine", "amantadine"),
    (r"istradefylline", "istradefylline"),
    (r"pimavanserin", "pimavanserin"),
    (r"rivastigmine", "rivastigmine"),
    (r"droxidopa", "droxidopa"),
    (r"isradipine", "isradipine"),
    (r"exenatide", "exenatide"),
    (r"foslevodopa(?:[- /]foscarbidopa)?", "foslevodopa"),
    (r"deep\s+brain\s+stimulation", "DBS"),
    (r"focused\s+ultrasound|mr[- ]?guided\s+focused\s+ultrasound", "focused-ultrasound"),
    (r"best\s+medical\s+(?:therapy|treatment)|medical\s+therapy", "medical-therapy"),
    (r"\bplacebo\b", "placebo"),
    (r"\bsham\b", "sham"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care", "standard-of-care"),
    (r"control\s+(?:regimen|group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"active\s+(?:treatment|comparator)", "active"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_PD_ARM_ABBREV = [   # case-sensitive
    (r"\bLCIG\b", "LCIG"),
    (r"\bDBS\b", "DBS"),
    (r"\bSTN\b", "STN-DBS"),
    (r"\bGPi\b", "GPi-DBS"),
    (r"\bMRgFUS\b", "focused-ultrasound"),
    (r"\bLED\b|\bLEDD\b", "levodopa"),
]
_PD_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _PD_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _PD_ARM_ABBREV])

# PD continuous (mean+/-SD) poolable outcomes; none are routinely log-normal.
_PD_CONTINUOUS = {"UPDRS_III", "UPDRS_TOTAL", "ON_TIME", "OFF_TIME", "LEDD",
                  "QUALITY_OF_LIFE", "COGNITION"}
_PD_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_PD_ENDPOINT_PATTERNS,
                                arm_compiled=_PD_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_PD_ENDPOINT_PATTERNS,
                               arm_compiled=_PD_ARM_COMPILED,
                               continuous_endpoints=_PD_CONTINUOUS,
                               lognormal_endpoints=_PD_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_PD_ENDPOINT_PATTERNS,
                              arm_compiled=_PD_ARM_COMPILED,
                              continuous_endpoints=_PD_CONTINUOUS,
                              lognormal_endpoints=_PD_LOGNORMAL)
