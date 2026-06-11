"""
Arm-level / 2x2 + continuous extraction for burns & wound-healing trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
wound-healing endpoints and dressing / therapy arm labels:

  binary outcomes (complete healing / closure, amputation, infection, dehiscence,
    graft take, recurrence) -> 2x2 events/N per arm;
  continuous outcomes (time to healing, wound-area reduction, scar score, pain,
    length of stay) -> per-arm mean+SD (Wan IQR->SD).

Comparisons are typically dressing/therapy-vs-standard (NPWT vs standard care,
silver dressing vs control) or agent-vs-placebo (growth factor, HBOT).
"""
import re
from typing import Dict, List

from .wound_healing import get_wound_healing_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_WH_ENDPOINT_PATTERNS = []
for _sub in ("burns", "chronic_wounds", "surgical_wounds", "adjuncts"):
    _WH_ENDPOINT_PATTERNS.extend(get_wound_healing_endpoint_patterns(_sub))

_WH_ARM_FULL = [
    (r"negative[- ]pressure\s+wound\s+therapy|vacuum[- ]assisted\s+closure", "NPWT"),
    (r"hyperbaric\s+oxygen", "hyperbaric-oxygen"),
    (r"platelet[- ]derived\s+growth\s+factor|becaplermin", "PDGF"),
    (r"epidermal\s+growth\s+factor", "EGF"),
    (r"platelet[- ]rich\s+plasma", "PRP"),
    (r"silver\s+dressing|silver[- ]impregnated", "silver-dressing"),
    (r"honey\s+dressing|medical[- ]grade\s+honey", "honey-dressing"),
    (r"collagen\s+dressing", "collagen-dressing"),
    (r"hydrocolloid|hydrogel|foam\s+dressing", "advanced-dressing"),
    (r"skin\s+substitute|dermal\s+(?:template|substitute|matrix)|amniotic\s+membrane", "skin-substitute"),
    (r"split[- ]thickness\s+skin\s+graft|autograft", "skin-graft"),
    (r"enzymatic\s+debridement|bromelain|nexobrid", "enzymatic-debridement"),
    (r"compression\s+(?:therapy|bandaging|stocking)", "compression"),
    (r"early\s+excision", "early-excision"),
    (r"total\s+contact\s+cast", "total-contact-cast"),
    (r"\bplacebo\b", "placebo"),
    (r"sham\s+(?:therapy|procedure)?|sham", "sham"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care|standard\s+(?:wound\s+)?(?:care|dressing|treatment)|"
     r"conventional\s+(?:dressing|treatment)", "standard-care"),
    (r"saline\s+(?:gauze|dressing)|moist\s+gauze", "saline-gauze"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_WH_ARM_ABBREV = [   # case-sensitive
    (r"\bNPWT\b", "NPWT"),
    (r"\bVAC\b", "NPWT"),
    (r"\bHBOT\b", "hyperbaric-oxygen"),
    (r"\bPDGF\b", "PDGF"),
    (r"\bPRP\b", "PRP"),
    (r"\bTCC\b", "total-contact-cast"),
    (r"\bSTSG\b", "skin-graft"),
]
_WH_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _WH_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _WH_ARM_ABBREV])

# Continuous (mean+SD poolable) wound-healing endpoints.
_WH_CONTINUOUS = {
    "TIME_TO_HEALING", "WOUND_AREA_REDUCTION", "SCAR_SCORE", "PAIN_SCORE", "LENGTH_OF_STAY",
}
_WH_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_WH_ENDPOINT_PATTERNS,
                                arm_compiled=_WH_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_WH_ENDPOINT_PATTERNS,
                               arm_compiled=_WH_ARM_COMPILED,
                               continuous_endpoints=_WH_CONTINUOUS,
                               lognormal_endpoints=_WH_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_WH_ENDPOINT_PATTERNS,
                              arm_compiled=_WH_ARM_COMPILED,
                              continuous_endpoints=_WH_CONTINUOUS,
                              lognormal_endpoints=_WH_LOGNORMAL)
