"""
Arm-level / 2x2 + continuous extraction for multiple myeloma trials.
Thin wrapper over the shared malaria_arm_data engine, configured with multiple
myeloma endpoints and immunomodulatory / proteasome-inhibitor / anti-CD38 / CAR-T
arm labels. Myeloma endpoints are binary (ORR, VGPR, CR, MRD-negativity) or
time-to-event; no continuous outcome configured.
"""
import re
from typing import Dict, List

from .multiple_myeloma import get_multiple_myeloma_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_MM_ENDPOINT_PATTERNS = []
for _sub in ("newly_diagnosed", "relapsed_refractory", "response", "mortality"):
    _MM_ENDPOINT_PATTERNS.extend(get_multiple_myeloma_endpoint_patterns(_sub))

_MM_ARM_FULL = [
    (r"daratumumab[, /-]+(?:bortezomib[, /-]+)?lenalidomide[, /-]+dexamethasone|\bd[- ]?vrd\b|"
     r"\bd[- ]?rd\b|dara[- ]?vrd", "dara-combination"),
    (r"daratumumab|darzalex", "daratumumab"),
    (r"isatuximab|sarclisa", "isatuximab"),
    (r"carfilzomib[, /-]+lenalidomide[, /-]+dexamethasone|\bkrd\b", "krd"),
    (r"carfilzomib|kyprolis", "carfilzomib"),
    (r"bortezomib[, /-]+lenalidomide[, /-]+dexamethasone|\bvrd\b|\brvd\b", "vrd"),
    (r"bortezomib|velcade", "bortezomib"),
    (r"pomalidomide[, /-]+dexamethasone|pomalidomide|pomalyst|imnovid", "pomalidomide"),
    (r"lenalidomide[, /-]+dexamethasone|\brd\b|lenalidomide|revlimid", "lenalidomide"),
    (r"elotuzumab|empliciti", "elotuzumab"),
    (r"selinexor|xpovio|nexpovio", "selinexor"),
    (r"belantamab(?:\s+mafodotin)?|blenrep", "belantamab"),
    (r"idecabtagene(?:\s+vicleucel)?|ide[- ]?cel|abecma", "ide-cel"),
    (r"ciltacabtagene(?:\s+autoleucel)?|cilta[- ]?cel|carvykti", "cilta-cel"),
    (r"teclistamab|talquetamab|elranatamab|bispecific", "bispecific"),
    (r"thalidomide", "thalidomide"),
    (r"melphalan[, /-]+prednisone|\bmp\b|\bvmp\b|\bmpt\b", "melphalan-prednisone"),
    (r"autologous\s+stem[- ]cell\s+transplant|\basct\b", "asct"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+(?:chemo)?(?:immuno)?therapy", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_MM_ARM_ABBREV = [
    (r"\bVRd\b|\bRVd\b", "vrd"),
    (r"\bKRd\b", "krd"),
    (r"\bD-?VRd\b", "dara-combination"),
    (r"\bVMP\b", "melphalan-prednisone"),
    (r"\bASCT\b", "asct"),
]
_MM_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _MM_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _MM_ARM_ABBREV])

_MM_CONTINUOUS = set()
_MM_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_MM_ENDPOINT_PATTERNS,
                                arm_compiled=_MM_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_MM_ENDPOINT_PATTERNS,
                               arm_compiled=_MM_ARM_COMPILED,
                               continuous_endpoints=_MM_CONTINUOUS,
                               lognormal_endpoints=_MM_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_MM_ENDPOINT_PATTERNS,
                              arm_compiled=_MM_ARM_COMPILED,
                              continuous_endpoints=_MM_CONTINUOUS,
                              lognormal_endpoints=_MM_LOGNORMAL)
