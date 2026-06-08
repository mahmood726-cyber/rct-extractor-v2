"""
Arm-level / 2x2 + continuous extraction for maternal & neonatal health trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with maternal /
neonatal endpoints and obstetric / neonatal intervention arm labels:

  binary outcomes (postpartum haemorrhage, maternal/neonatal/perinatal mortality,
    stillbirth, pre-eclampsia, eclampsia, neonatal sepsis, caesarean, preterm
    birth, low birth weight, RDS) -> 2x2 events/N per arm
  continuous (blood loss -> mL; birth weight -> g; gestational age -> weeks;
    Apgar score; duration of labour) -> mean+SD / median+IQR -> MD/SMD.
"""
import re
from typing import Dict, List

from .maternal_neonatal import get_maternal_neonatal_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Maternal/neonatal endpoint patterns (string, endpoint) across all subspecialties.
_MNH_ENDPOINT_PATTERNS = []
for _sub in ("maternal", "hypertensive", "neonatal", "preterm"):
    _MNH_ENDPOINT_PATTERNS.extend(get_maternal_neonatal_endpoint_patterns(_sub))

# Obstetric / neonatal intervention arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_MNH_ARM_FULL = [
    # uterotonics / PPH
    (r"oxytocin", "oxytocin"),
    (r"carbetocin", "carbetocin"),
    (r"misoprostol", "misoprostol"),
    (r"syntometrine", "syntometrine"),
    (r"methylergometrine|methylergonovine", "methylergometrine"),
    (r"ergometrine|ergonovine", "ergometrine"),
    (r"carboprost", "carboprost"),
    (r"tranexamic\s+acid", "tranexamic-acid"),
    # hypertensive
    (r"magnesium\s+sul(?:f|ph)ate", "magnesium-sulphate"),
    (r"labetalol", "labetalol"),
    (r"hydralazine", "hydralazine"),
    (r"methyldopa", "methyldopa"),
    (r"nifedipine", "nifedipine"),
    (r"low[- ]dose\s+aspirin|aspirin", "aspirin"),
    (r"calcium(?:\s+supplementation)?", "calcium"),
    # preterm / neonatal
    (r"dexamethasone", "dexamethasone"),
    (r"betamethasone", "betamethasone"),
    (r"antenatal\s+cortico?steroids?", "antenatal-corticosteroids"),
    (r"atosiban", "atosiban"),
    (r"progesterone", "progesterone"),
    (r"chlorhexidine", "chlorhexidine"),
    (r"kangaroo\s+mother\s+care", "kangaroo-mother-care"),
    # management / generic
    (r"active\s+management", "active-management"),
    (r"expectant\s+management", "expectant-management"),
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|routine\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_MNH_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bTXA\b", "tranexamic-acid"),
    (r"\bMgSO4\b", "magnesium-sulphate"),
    (r"\bACS\b", "antenatal-corticosteroids"),
    (r"\bKMC\b", "kangaroo-mother-care"),
    (r"\bAMTSL\b", "active-management"),
]
_MNH_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _MNH_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _MNH_ARM_ABBREV])

# Continuous maternal/neonatal outcomes; none are routinely pooled on the log scale.
_MNH_CONTINUOUS = {"BLOOD_LOSS", "BIRTH_WEIGHT", "GESTATIONAL_AGE",
                   "APGAR_SCORE", "LABOUR_DURATION"}
_MNH_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_MNH_ENDPOINT_PATTERNS,
                                arm_compiled=_MNH_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_MNH_ENDPOINT_PATTERNS,
                               arm_compiled=_MNH_ARM_COMPILED,
                               continuous_endpoints=_MNH_CONTINUOUS,
                               lognormal_endpoints=_MNH_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_MNH_ENDPOINT_PATTERNS,
                              arm_compiled=_MNH_ARM_COMPILED,
                              continuous_endpoints=_MNH_CONTINUOUS,
                              lognormal_endpoints=_MNH_LOGNORMAL)
