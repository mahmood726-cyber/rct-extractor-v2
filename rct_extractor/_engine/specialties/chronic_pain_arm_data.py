"""
Arm-level / 2x2 + continuous extraction for chronic-pain trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
chronic-pain endpoints and analgesic / intervention arm labels:

  binary outcomes (>=30% / >=50% pain responder, pain relief, withdrawal due to
    adverse events, adverse events) -> 2x2 events/N per arm;
  continuous outcomes (pain intensity, physical function/disability, quality of
    life, sleep, opioid use) -> per-arm mean+SD (Wan IQR->SD).

Comparisons are typically drug-vs-placebo (pregabalin, duloxetine, opioids),
device/procedure-vs-sham (spinal cord stimulation, radiofrequency ablation), or
therapy-vs-usual-care (CBT, exercise).
"""
import re
from typing import Dict, List

from .chronic_pain import get_chronic_pain_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_CP_ENDPOINT_PATTERNS = []
for _sub in ("pharmacological", "interventional", "neuropathic", "behavioural"):
    _CP_ENDPOINT_PATTERNS.extend(get_chronic_pain_endpoint_patterns(_sub))

_CP_ARM_FULL = [
    (r"pregabalin", "pregabalin"),
    (r"gabapentin", "gabapentin"),
    (r"duloxetine", "duloxetine"),
    (r"milnacipran", "milnacipran"),
    (r"venlafaxine", "venlafaxine"),
    (r"amitriptyline", "amitriptyline"),
    (r"nortriptyline", "nortriptyline"),
    (r"oxycodone", "oxycodone"),
    (r"tapentadol", "tapentadol"),
    (r"tramadol", "tramadol"),
    (r"buprenorphine", "buprenorphine"),
    (r"morphine", "morphine"),
    (r"\bnsaid\b|naproxen|ibuprofen|celecoxib|diclofenac", "NSAID"),
    (r"capsaicin", "capsaicin"),
    (r"lidocaine|lignocaine", "lidocaine"),
    (r"nabiximols|cannabidiol|cannabi(?:noid|s)|nabilone", "cannabinoid"),
    (r"spinal\s+cord\s+stimulation", "spinal-cord-stimulation"),
    (r"radiofrequency\s+(?:ablation|denervation)", "radiofrequency-ablation"),
    (r"epidural\s+steroid", "epidural-steroid"),
    (r"nerve\s+block", "nerve-block"),
    (r"cognitive\s+behavio(?:u)?ral\s+therapy", "CBT"),
    (r"exercise\s+(?:therapy|program|intervention)|physiotherapy", "exercise"),
    (r"acupuncture", "acupuncture"),
    (r"mindfulness", "mindfulness"),
    (r"\bplacebo\b", "placebo"),
    (r"sham\s+(?:procedure|injection|stimulation|control)?|sham", "sham"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care|waitlist|wait[- ]list", "usual-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_CP_ARM_ABBREV = [   # case-sensitive
    (r"\bCBT\b", "CBT"),
    (r"\bSCS\b", "spinal-cord-stimulation"),
    (r"\bRFA\b", "radiofrequency-ablation"),
    (r"\bESI\b", "epidural-steroid"),
    (r"\bTENS\b", "TENS"),
]
_CP_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _CP_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _CP_ARM_ABBREV])

# Continuous (mean+SD poolable) chronic-pain endpoints.
_CP_CONTINUOUS = {
    "PAIN_INTENSITY", "FUNCTION", "QOL", "SLEEP", "OPIOID_USE",
}
_CP_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_CP_ENDPOINT_PATTERNS,
                                arm_compiled=_CP_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_CP_ENDPOINT_PATTERNS,
                               arm_compiled=_CP_ARM_COMPILED,
                               continuous_endpoints=_CP_CONTINUOUS,
                               lognormal_endpoints=_CP_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_CP_ENDPOINT_PATTERNS,
                              arm_compiled=_CP_ARM_COMPILED,
                              continuous_endpoints=_CP_CONTINUOUS,
                              lognormal_endpoints=_CP_LOGNORMAL)
