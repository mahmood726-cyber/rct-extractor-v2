"""
Arm-level / 2x2 + continuous extraction for rehabilitation / physiotherapy trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
rehabilitation endpoints and rehabilitation-intervention arm labels:

  binary (cardiac mortality, hospital readmission, return to work) -> 2x2 events/N.
  continuous (motor function, FIM, gait, peak VO2, 6MWD, dyspnoea, QoL, pain,
    physical function) -> mean+SD / median+IQR, pooled as MD/SMD on the natural
    scale.
"""
import re
from typing import Dict, List

from .rehabilitation_physiotherapy import get_rehabilitation_physiotherapy_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_RP_ENDPOINT_PATTERNS = []
for _sub in ("neuro", "cardiac", "pulmonary", "musculoskeletal"):
    _RP_ENDPOINT_PATTERNS.extend(get_rehabilitation_physiotherapy_endpoint_patterns(_sub))

# Rehabilitation-intervention arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE.
_RP_ARM_FULL = [
    (r"cardiac\s+rehabilitation|exercise[- ]based\s+cardiac\s+rehabilitation", "cardiac-rehabilitation"),
    (r"pulmonary\s+rehabilitation", "pulmonary-rehabilitation"),
    (r"constraint[- ]induced\s+movement\s+therapy|constraint[- ]induced", "constraint-induced-therapy"),
    (r"robot[- ]assisted\s+(?:therapy|training|rehabilitation)?|robotic\s+(?:therapy|training)", "robot-assisted"),
    (r"virtual\s+reality", "virtual-reality"),
    (r"(?:functional\s+|neuromuscular\s+)?electrical\s+stimulation|\bfes\b", "electrical-stimulation"),
    (r"(?:supervised\s+|aerobic\s+|resistance\s+)?exercise(?:\s+(?:therapy|training|programme|program))?",
     "exercise-therapy"),
    (r"manual\s+therapy", "manual-therapy"),
    (r"occupational\s+therapy", "occupational-therapy"),
    (r"physiotherapy|physical\s+therapy", "physiotherapy"),
    (r"home[- ](?:based\s+)?(?:exercise|programme|program)|home[- ]based", "home-based"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"usual\s+care|standard\s+(?:of\s+)?care|conventional\s+(?:therapy|rehabilitation|care)",
     "usual-care"),
    (r"wait[- ]?list|waiting\s+list|no\s+(?:intervention|treatment)", "waitlist"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_RP_ARM_ABBREV = [
    (r"\bCIMT\b", "constraint-induced-therapy"),
    (r"\bFES\b|\bNMES\b", "electrical-stimulation"),
    (r"\bVR\b", "virtual-reality"),
]
_RP_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _RP_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _RP_ARM_ABBREV])

# Rehabilitation continuous outcomes (natural scale). Cardiac mortality /
# readmission and return-to-work are the binary ratio endpoints.
_RP_CONTINUOUS = {"MOTOR_FUNCTION", "FUNCTIONAL_INDEPENDENCE", "GAIT", "EXERCISE_CAPACITY",
                  "SIX_MWD", "DYSPNOEA", "RESPIRATORY_QOL", "PAIN", "PHYSICAL_FUNCTION"}
_RP_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_RP_ENDPOINT_PATTERNS,
                                arm_compiled=_RP_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_RP_ENDPOINT_PATTERNS,
                               arm_compiled=_RP_ARM_COMPILED,
                               continuous_endpoints=_RP_CONTINUOUS,
                               lognormal_endpoints=_RP_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_RP_ENDPOINT_PATTERNS,
                              arm_compiled=_RP_ARM_COMPILED,
                              continuous_endpoints=_RP_CONTINUOUS,
                              lognormal_endpoints=_RP_LOGNORMAL)
