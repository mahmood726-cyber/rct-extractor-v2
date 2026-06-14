"""
Arm-level / 2x2 extraction for vascular-surgery trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
vascular-surgery endpoints and procedure-class arm labels. All endpoints
(aneurysm / carotid / access / venous) are binary -> 2x2 events/N per arm.
"""
import re
from typing import Dict, List

from .vascular_surgery import get_vascular_surgery_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_VS_ENDPOINT_PATTERNS = []
for _sub in ("aneurysm", "carotid", "access", "venous"):
    _VS_ENDPOINT_PATTERNS.extend(get_vascular_surgery_endpoint_patterns(_sub))

# Vascular-surgery procedure arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE.
_VS_ARM_FULL = [
    # aneurysm
    (r"endovascular\s+(?:aneurysm\s+)?repair|endovascular\s+aneurysm", "evar"),
    (r"open\s+(?:aneurysm\s+|surgical\s+)?repair|open\s+surgery", "open-repair"),
    (r"fenestrated\s+(?:evar|endovascular)", "fevar"),
    # carotid
    (r"carotid\s+endarterectomy", "carotid-endarterectomy"),
    (r"carotid\s+(?:artery\s+)?stenting|carotid\s+stent", "carotid-stenting"),
    # access
    (r"arteriovenous\s+fistula|av\s+fistula", "av-fistula"),
    (r"arteriovenous\s+graft|av\s+graft", "av-graft"),
    # venous
    (r"endovenous\s+laser\s+ablation|endovenous\s+laser|\bevla\b|\bevlt\b", "endovenous-laser"),
    (r"radiofrequency\s+ablation|radiofrequency", "radiofrequency-ablation"),
    (r"(?:ultrasound[- ]guided\s+)?foam\s+sclerotherapy|foam", "foam-sclerotherapy"),
    (r"(?:surgical\s+)?stripping|high\s+ligation|conventional\s+surgery", "surgery"),
    (r"mechanochemical\s+ablation|\bmoca\b", "mechanochemical-ablation"),
    (r"cyanoacrylate(?:\s+(?:closure|glue))?", "cyanoacrylate"),
    # generic devices
    (r"balloon\s+angioplasty|angioplasty", "angioplasty"),
    (r"drug[- ](?:coated|eluting)\s+(?:balloon|stent)", "drug-coated-device"),
    (r"\bstent\b", "stent"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|best\s+medical\s+(?:therapy|treatment)", "standard-of-care"),
    (r"surveillance|conservative\s+management|watchful\s+waiting", "surveillance"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_VS_ARM_ABBREV = [
    (r"\bEVAR\b", "evar"),
    (r"\bCEA\b", "carotid-endarterectomy"),
    (r"\bCAS\b", "carotid-stenting"),
    (r"\bEVLA\b|\bEVLT\b", "endovenous-laser"),
    (r"\bRFA\b", "radiofrequency-ablation"),
    (r"\bUGFS\b", "foam-sclerotherapy"),
]
_VS_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _VS_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _VS_ARM_ABBREV])

# Vascular-surgery endpoints are all binary outcomes.
_VS_CONTINUOUS: set = set()
_VS_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_VS_ENDPOINT_PATTERNS,
                                arm_compiled=_VS_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_VS_ENDPOINT_PATTERNS,
                               arm_compiled=_VS_ARM_COMPILED,
                               continuous_endpoints=_VS_CONTINUOUS,
                               lognormal_endpoints=_VS_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_VS_ENDPOINT_PATTERNS,
                              arm_compiled=_VS_ARM_COMPILED,
                              continuous_endpoints=_VS_CONTINUOUS,
                              lognormal_endpoints=_VS_LOGNORMAL)
