"""
Arm-level / 2x2 + continuous extraction for sickle cell disease (SCD) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with SCD endpoints
and disease-modifying / chelator arm labels:

  binary / recurrent-event outcomes (vaso-occlusive crisis, acute chest syndrome,
    hospitalisation, transfusion, dactylitis, stroke, silent infarct, infection,
    alloimmunisation, readmission) -> 2x2 events/N per arm
  continuous (total- and fetal-haemoglobin change, crisis duration, length of
    stay, opioid use, pain score, TCD velocity, ferritin, liver iron) -> mean+SD /
    median+IQR -> MD.
"""
import re
from typing import Dict, List

from .sickle_cell import get_sickle_cell_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# SCD endpoint patterns (string, endpoint) across all subspecialties.
_SICKLE_CELL_ENDPOINT_PATTERNS = []
for _sub in ("disease_modifying", "acute_pain", "prevention", "transfusion"):
    _SICKLE_CELL_ENDPOINT_PATTERNS.extend(get_sickle_cell_endpoint_patterns(_sub))

# Disease-modifying / chelator / comparator arm labels. Full names case-insensitive;
# bare UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_SICKLE_CELL_ARM_FULL = [
    (r"hydroxyurea|hydroxycarbamide", "hydroxyurea"),
    (r"voxelotor", "voxelotor"),
    (r"crizanlizumab", "crizanlizumab"),
    (r"l[- ]?glutamine|\bglutamine\b", "l-glutamine"),
    (r"deferasirox", "deferasirox"),
    (r"deferiprone", "deferiprone"),
    (r"deferoxamine|desferrioxamine", "deferoxamine"),
    (r"penicillin", "penicillin"),
    (r"ticagrelor", "ticagrelor"),
    (r"prasugrel", "prasugrel"),
    (r"rivipansel", "rivipansel"),
    (r"sevuparin", "sevuparin"),
    (r"chronic\s+(?:blood\s+)?transfusion|regular\s+(?:blood\s+)?transfusion", "chronic-transfusion"),
    (r"(?:ha?ematopoietic\s+)?stem[- ]cell\s+transplant", "stem-cell-transplant"),
    (r"gene\s+therapy", "gene-therapy"),
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|supportive\s+care", "standard-of-care"),
    (r"observation(?:\s+arm)?", "observation"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_SICKLE_CELL_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bHU\b", "hydroxyurea"),
    (r"\bHC\b", "hydroxyurea"),
    (r"\bSCT\b", "stem-cell-transplant"),
]
_SICKLE_CELL_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _SICKLE_CELL_ARM_FULL]
                             + [(re.compile(p), n) for p, n in _SICKLE_CELL_ARM_ABBREV])

# SCD continuous outcomes. Haemoglobin/HbF change, durations, scores, velocities
# and iron measures are reported as mean+SD (or median+IQR) on the natural scale.
_SICKLE_CELL_CONTINUOUS = {
    "TOTAL_HEMOGLOBIN", "FETAL_HEMOGLOBIN", "CRISIS_DURATION", "LENGTH_OF_STAY",
    "OPIOID_USE", "PAIN_INTENSITY", "TCD_VELOCITY", "SERUM_FERRITIN", "LIVER_IRON",
}
_SICKLE_CELL_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_SICKLE_CELL_ENDPOINT_PATTERNS,
                                arm_compiled=_SICKLE_CELL_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_SICKLE_CELL_ENDPOINT_PATTERNS,
                               arm_compiled=_SICKLE_CELL_ARM_COMPILED,
                               continuous_endpoints=_SICKLE_CELL_CONTINUOUS,
                               lognormal_endpoints=_SICKLE_CELL_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_SICKLE_CELL_ENDPOINT_PATTERNS,
                              arm_compiled=_SICKLE_CELL_ARM_COMPILED,
                              continuous_endpoints=_SICKLE_CELL_CONTINUOUS,
                              lognormal_endpoints=_SICKLE_CELL_LOGNORMAL)
