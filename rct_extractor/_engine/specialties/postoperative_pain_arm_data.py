"""
Arm-level / 2x2 + continuous extraction for postoperative (acute surgical) pain trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
postoperative-pain endpoints and analgesia / block arm labels:

  binary outcomes (rescue analgesia, PONV, moderate-to-severe pain, chronic
    post-surgical pain, block success) -> 2x2 events/N per arm;
  continuous outcomes (pain score, opioid/morphine consumption, time to first
    rescue analgesia, satisfaction) -> per-arm mean+SD (Wan IQR->SD).

Comparisons are typically block-vs-control (TAP block vs placebo), drug-vs-placebo
(dexamethasone, gabapentin, ketamine) or technique-vs-technique (epidural vs PCA).
"""
import re
from typing import Dict, List

from .postoperative_pain import get_postoperative_pain_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_POP_ENDPOINT_PATTERNS = []
for _sub in ("regional_analgesia", "multimodal", "opioid", "chronic_postsurgical"):
    _POP_ENDPOINT_PATTERNS.extend(get_postoperative_pain_endpoint_patterns(_sub))

_POP_ARM_FULL = [
    (r"transversus\s+abdominis\s+plane\s+block|\btap\s+block\b", "TAP-block"),
    (r"erector\s+spinae\s+(?:plane\s+)?block", "erector-spinae-block"),
    (r"interscalene\s+block", "interscalene-block"),
    (r"femoral\s+(?:nerve\s+)?block", "femoral-block"),
    (r"pectoral\s+(?:nerve\s+)?block|\bpecs\s+block\b", "pecs-block"),
    (r"epidural\s+analgesia|epidural", "epidural"),
    (r"wound\s+infiltration|local\s+infiltration", "wound-infiltration"),
    (r"intrathecal\s+morphine|spinal\s+morphine", "intrathecal-morphine"),
    (r"patient[- ]controlled\s+analgesia", "PCA"),
    (r"paracetamol|acetaminophen", "paracetamol"),
    (r"\bnsaid\b|ketorolac|ibuprofen|diclofenac|celecoxib|parecoxib", "NSAID"),
    (r"gabapentin", "gabapentin"),
    (r"pregabalin", "pregabalin"),
    (r"dexamethasone", "dexamethasone"),
    (r"dexmedetomidine", "dexmedetomidine"),
    (r"ketamine", "ketamine"),
    (r"magnesium", "magnesium"),
    (r"lidocaine|lignocaine", "lidocaine"),
    (r"ropivacaine", "ropivacaine"),
    (r"bupivacaine|levobupivacaine", "bupivacaine"),
    (r"morphine", "morphine"),
    (r"fentanyl", "fentanyl"),
    (r"\bplacebo\b", "placebo"),
    (r"sham\s+(?:block|procedure|injection)?|sham", "sham"),
    (r"saline|normal\s+saline", "saline"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care|standard\s+analgesia", "standard-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_POP_ARM_ABBREV = [   # case-sensitive
    (r"\bTAP\b", "TAP-block"),
    (r"\bPCA\b", "PCA"),
    (r"\bESP\b", "erector-spinae-block"),
    (r"\bPECS\b", "pecs-block"),
    (r"\bITM\b", "intrathecal-morphine"),
]
_POP_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _POP_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _POP_ARM_ABBREV])

# Continuous (mean+SD poolable) postoperative-pain endpoints.
_POP_CONTINUOUS = {
    "PAIN_SCORE", "OPIOID_CONSUMPTION", "TIME_TO_RESCUE", "SATISFACTION",
}
_POP_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_POP_ENDPOINT_PATTERNS,
                                arm_compiled=_POP_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_POP_ENDPOINT_PATTERNS,
                               arm_compiled=_POP_ARM_COMPILED,
                               continuous_endpoints=_POP_CONTINUOUS,
                               lognormal_endpoints=_POP_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_POP_ENDPOINT_PATTERNS,
                              arm_compiled=_POP_ARM_COMPILED,
                              continuous_endpoints=_POP_CONTINUOUS,
                              lognormal_endpoints=_POP_LOGNORMAL)
