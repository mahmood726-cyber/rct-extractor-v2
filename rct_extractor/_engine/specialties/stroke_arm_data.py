"""
Arm-level / 2x2 + continuous extraction for stroke (cerebrovascular) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with stroke
endpoints and thrombolytic / thrombectomy / antiplatelet / anticoagulant arm
labels:

  binary outcomes (functional independence [mRS 0-2], recanalisation, sICH,
    mortality, recurrent stroke, major bleeding, haematoma expansion, poor
    outcome, MACE) -> 2x2 events/N per arm
  continuous (NIHSS, Fugl-Meyer motor function, Barthel Index) -> mean+SD /
    median+IQR. None of the stroke scales are log-normal (bounded ordinal /
    interval scores), so the log-normal set is empty.
"""
import re
from typing import Dict, List

from .stroke import get_stroke_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Stroke endpoint patterns (string, endpoint) across all subspecialties.
_STROKE_ENDPOINT_PATTERNS = []
for _sub in ("acute_ischemic", "hemorrhagic", "secondary_prevention", "recovery"):
    _STROKE_ENDPOINT_PATTERNS.extend(get_stroke_endpoint_patterns(_sub))

_J = r"[/\-+ ]"   # combo joiner in text: slash, hyphen, plus, or space

# Thrombolytic / thrombectomy / antiplatelet / anticoagulant arm labels. Full
# names case-insensitive; bare UPPERCASE abbreviations case-sensitive so that a
# bare effect abbreviation (HR/OR/RR) is NEVER an arm label and "tNK" only matches
# the uppercase token. Combination antiplatelet (DAPT) is matched as a unit FIRST
# so a 2x2 arm is not fragmented into aspirin + clopidogrel.
_STROKE_ARM_FULL = [
    # Dual antiplatelet combinations (match as a unit before the singletons)
    (rf"aspirin{_J}clopidogrel|clopidogrel{_J}aspirin|"
     r"dual\s+antiplatelet(?:\s+therapy)?", "dual-antiplatelet"),
    (rf"aspirin{_J}ticagrelor|ticagrelor{_J}aspirin", "aspirin-ticagrelor"),
    # Thrombolytics
    (r"tenecteplase|\btnk[- ]?tpa\b", "tenecteplase"),
    (r"alteplase|recombinant\s+tissue\s+plasminogen\s+activator|\brt[- ]?pa\b", "alteplase"),
    # Thrombectomy / endovascular
    (r"mechanical\s+thrombectomy|endovascular\s+(?:therapy|treatment|thrombectomy)|"
     r"thrombectomy", "thrombectomy"),
    # Antiplatelets (singletons)
    (r"\baspirin\b|acetylsalicylic\s+acid", "aspirin"),
    (r"clopidogrel|\bplavix\b", "clopidogrel"),
    (r"ticagrelor|\bbrilinta\b", "ticagrelor"),
    # Anticoagulants
    (r"warfarin|\bcoumadin\b", "warfarin"),
    (r"apixaban|\beliquis\b", "apixaban"),
    (r"rivaroxaban|\bxarelto\b", "rivaroxaban"),
    (r"dabigatran|\bpradaxa\b", "dabigatran"),
    (r"edoxaban|\blixiana\b|\bsavaysa\b", "edoxaban"),
    (r"andexanet(?:\s+alfa)?", "andexanet"),
    (r"anticoagulation|anticoagulant\s+(?:therapy|treatment)", "anticoagulation"),
    # Haemorrhagic-stroke agents
    (r"tranexamic\s+acid|\btxa\b", "tranexamic-acid"),
    (r"nimodipine", "nimodipine"),
    # Generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|standard\s+medical\s+(?:care|therapy)|"
     r"medical\s+management|best\s+medical\s+therapy", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_STROKE_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bTNK\b", "tenecteplase"),
    (r"\bTPA\b|\brtPA\b|\brt-PA\b", "alteplase"),
    (r"\bEVT\b", "thrombectomy"),
    (r"\bMT\b", "thrombectomy"),
    (r"\bDAPT\b", "dual-antiplatelet"),
    (r"\bASA\b", "aspirin"),
    (r"\bTXA\b", "tranexamic-acid"),
]
_STROKE_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _STROKE_ARM_FULL]
                        + [(re.compile(p), n) for p, n in _STROKE_ARM_ABBREV])

# Stroke continuous outcomes are bounded ordinal/interval clinical scales
# (NIHSS 0-42, Fugl-Meyer 0-66/0-226, Barthel 0-100) -- NOT log-normal, so no
# log-scale pooling. lognormal set intentionally empty.
_STROKE_CONTINUOUS = {"NIHSS", "MOTOR_FUNCTION", "BARTHEL_INDEX", "EARLY_NEURO_IMPROVEMENT"}
_STROKE_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_STROKE_ENDPOINT_PATTERNS,
                                arm_compiled=_STROKE_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_STROKE_ENDPOINT_PATTERNS,
                               arm_compiled=_STROKE_ARM_COMPILED,
                               continuous_endpoints=_STROKE_CONTINUOUS,
                               lognormal_endpoints=_STROKE_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_STROKE_ENDPOINT_PATTERNS,
                              arm_compiled=_STROKE_ARM_COMPILED,
                              continuous_endpoints=_STROKE_CONTINUOUS,
                              lognormal_endpoints=_STROKE_LOGNORMAL)
