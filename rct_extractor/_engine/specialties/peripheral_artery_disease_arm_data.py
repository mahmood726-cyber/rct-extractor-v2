"""
Arm-level / 2x2 + continuous extraction for peripheral artery disease (PAD) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
PAD endpoints and PAD drug / device / procedure arm labels:

  binary outcomes (MALE, amputation, amputation-free survival, acute limb
    ischaemia, limb salvage, primary patency, TLR/TVR, restenosis, MACE, MI,
    stroke, CV/all-cause death, major bleeding) -> 2x2 events/N per arm.
  continuous (maximal / pain-free walking distance, ankle-brachial index) ->
    mean+SD / median+IQR, pooled as MD/SMD on the natural scale.
"""
import re
from typing import Dict, List

from .peripheral_artery_disease import get_peripheral_artery_disease_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# PAD endpoint patterns (string, endpoint) across all subspecialties.
_PAD_ENDPOINT_PATTERNS = []
for _sub in ("limb_outcomes", "revascularisation", "medical_therapy", "functional"):
    _PAD_ENDPOINT_PATTERNS.extend(get_peripheral_artery_disease_endpoint_patterns(_sub))

# PAD drug / device / procedure arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE.
_PAD_ARM_FULL = [
    # antithrombotic / medical
    (r"cilostazol", "cilostazol"),
    (r"clopidogrel", "clopidogrel"),
    (r"ticagrelor", "ticagrelor"),
    (r"vorapaxar", "vorapaxar"),
    (r"rivaroxaban", "rivaroxaban"),
    (r"\baspirin\b|acetylsalicylic\s+acid", "aspirin"),
    (r"\bstatin\b|atorvastatin|rosuvastatin|simvastatin", "statin"),
    (r"pentoxifylline", "pentoxifylline"),
    (r"naftidrofuryl", "naftidrofuryl"),
    # devices / procedures
    (r"drug[- ]coated\s+balloon|paclitaxel[- ]coated\s+balloon", "drug-coated-balloon"),
    (r"drug[- ]eluting\s+stent", "drug-eluting-stent"),
    (r"bare[- ]metal\s+stent", "bare-metal-stent"),
    (r"plain\s+(?:old\s+)?balloon\s+angioplasty|percutaneous\s+transluminal\s+angioplasty|"
     r"balloon\s+angioplasty|\bangioplasty\b",
     "balloon-angioplasty"),
    (r"\bstent(?:ing)?\b", "stent"),
    (r"endovascular(?:\s+(?:therapy|treatment|revascular[is]ation))?", "endovascular"),
    (r"bypass\s+(?:surgery|graft|surg+ery)|surgical\s+revascular[is]ation|surgical\s+bypass",
     "bypass-surgery"),
    (r"supervised\s+exercise(?:\s+(?:therapy|training|program(?:me)?))?", "supervised-exercise"),
    (r"atherectomy", "atherectomy"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|optimal\s+medical\s+(?:therapy|treatment)",
     "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_PAD_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bDCB\b", "drug-coated-balloon"),
    (r"\bDES\b", "drug-eluting-stent"),
    (r"\bBMS\b", "bare-metal-stent"),
    (r"\bPTA\b", "balloon-angioplasty"),
    (r"\bOMT\b", "standard-of-care"),
]
_PAD_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _PAD_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _PAD_ARM_ABBREV])

# PAD continuous outcomes (functional, natural scale).
_PAD_CONTINUOUS = {"MAX_WALKING_DISTANCE", "PAIN_FREE_WALKING_DISTANCE", "ABI"}
_PAD_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_PAD_ENDPOINT_PATTERNS,
                                arm_compiled=_PAD_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_PAD_ENDPOINT_PATTERNS,
                               arm_compiled=_PAD_ARM_COMPILED,
                               continuous_endpoints=_PAD_CONTINUOUS,
                               lognormal_endpoints=_PAD_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_PAD_ENDPOINT_PATTERNS,
                              arm_compiled=_PAD_ARM_COMPILED,
                              continuous_endpoints=_PAD_CONTINUOUS,
                              lognormal_endpoints=_PAD_LOGNORMAL)
