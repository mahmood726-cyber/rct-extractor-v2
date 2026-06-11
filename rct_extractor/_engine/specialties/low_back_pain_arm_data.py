"""
Arm-level / 2x2 + continuous extraction for low-back-pain trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
low-back-pain endpoints and treatment arm labels:

  binary outcomes (responder, recovery, return to work, recurrence, reoperation,
    global improvement) -> 2x2 events/N per arm;
  continuous outcomes (pain intensity, disability [ODI/RMDQ], quality of life,
    opioid use) -> per-arm mean+SD (Wan IQR->SD).

Comparisons are typically intervention-vs-control (exercise vs usual care, CBT
vs usual care), drug-vs-placebo (NSAID, duloxetine) or surgery-vs-conservative.
"""
import re
from typing import Dict, List

from .low_back_pain import get_low_back_pain_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_LBP_ENDPOINT_PATTERNS = []
for _sub in ("pharmacological", "interventional", "physical", "psychological"):
    _LBP_ENDPOINT_PATTERNS.extend(get_low_back_pain_endpoint_patterns(_sub))

_LBP_ARM_FULL = [
    (r"\bnsaid\b|naproxen|ibuprofen|diclofenac|celecoxib", "NSAID"),
    (r"paracetamol|acetaminophen", "paracetamol"),
    (r"duloxetine", "duloxetine"),
    (r"amitriptyline", "amitriptyline"),
    (r"pregabalin", "pregabalin"),
    (r"gabapentin", "gabapentin"),
    (r"opioid|oxycodone|tramadol|tapentadol", "opioid"),
    (r"muscle\s+relaxant|cyclobenzaprine|tizanidine", "muscle-relaxant"),
    (r"epidural(?:\s+steroid)?(?:\s+injection)?", "epidural-steroid"),
    (r"radiofrequency\s+(?:ablation|denervation)", "radiofrequency"),
    (r"discectomy|microdiscectomy", "discectomy"),
    (r"spinal\s+fusion|lumbar\s+fusion", "fusion"),
    (r"exercise\s+(?:therapy|program)?|physiotherapy|physical\s+therapy", "exercise"),
    (r"spinal\s+manipulation|manual\s+therapy", "manual-therapy"),
    (r"mckenzie", "mckenzie"),
    (r"yoga", "yoga"),
    (r"cognitive\s+behavio(?:u)?ral\s+therapy|cognitive\s+functional\s+therapy", "CBT"),
    (r"mindfulness", "mindfulness"),
    (r"multidisciplinary|biopsychosocial", "multidisciplinary"),
    (r"\bplacebo\b", "placebo"),
    (r"sham\s+(?:injection|procedure|surgery)?|sham", "sham"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual[\s-]care|guideline[- ]based\s+care", "usual-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_LBP_ARM_ABBREV = [   # case-sensitive
    (r"\bCBT\b", "CBT"),
    (r"\bCFT\b", "cognitive-functional-therapy"),
    (r"\bESI\b", "epidural-steroid"),
    (r"\bRFA\b", "radiofrequency"),
]
_LBP_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _LBP_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _LBP_ARM_ABBREV])

# Continuous (mean+SD poolable) low-back-pain endpoints.
_LBP_CONTINUOUS = {
    "PAIN_INTENSITY", "DISABILITY", "QOL", "OPIOID_USE",
}
_LBP_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_LBP_ENDPOINT_PATTERNS,
                                arm_compiled=_LBP_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_LBP_ENDPOINT_PATTERNS,
                               arm_compiled=_LBP_ARM_COMPILED,
                               continuous_endpoints=_LBP_CONTINUOUS,
                               lognormal_endpoints=_LBP_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_LBP_ENDPOINT_PATTERNS,
                              arm_compiled=_LBP_ARM_COMPILED,
                              continuous_endpoints=_LBP_CONTINUOUS,
                              lognormal_endpoints=_LBP_LOGNORMAL)
