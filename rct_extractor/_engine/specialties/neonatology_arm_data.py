"""
Arm-level / 2x2 extraction for neonatology (NICU) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
neonatology endpoints and NICU-intervention drug-class arm labels. All neonatal
morbidity/mortality endpoints are binary -> 2x2 events/N per arm.
"""
import re
from typing import Dict, List

from .neonatology import get_neonatology_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_NEO_ENDPOINT_PATTERNS = []
for _sub in ("respiratory", "gastrointestinal", "neurological", "complications"):
    _NEO_ENDPOINT_PATTERNS.extend(get_neonatology_endpoint_patterns(_sub))

# NICU-intervention arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE.
_NEO_ARM_FULL = [
    # surfactant
    (r"poractant(?:\s+alfa)?|curosurf", "poractant"),
    (r"beractant|survanta", "beractant"),
    (r"calfactant|infasurf", "calfactant"),
    (r"surfactant", "surfactant"),
    # respiratory support
    (r"(?:nasal\s+)?(?:n?cpap|continuous\s+positive\s+airway\s+pressure)", "cpap"),
    (r"inhaled\s+nitric\s+oxide", "inhaled-nitric-oxide"),
    (r"\bcaffeine\b|caffeine\s+citrate", "caffeine"),
    # PDA pharmacotherapy
    (r"indomethacin", "indomethacin"),
    (r"ibuprofen", "ibuprofen"),
    (r"paracetamol|acetaminophen", "paracetamol"),
    # other neonatal
    (r"probiotic\w*", "probiotics"),
    (r"erythropoietin|epoetin|darbepoetin", "erythropoietin"),
    (r"hydrocortisone", "hydrocortisone"),
    (r"dexamethasone", "dexamethasone"),
    (r"(?:therapeutic\s+)?hypothermia|(?:whole[- ]body\s+)?cooling", "hypothermia"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|conservative\s+management", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_NEO_ARM_ABBREV = [
    (r"\biNO\b", "inhaled-nitric-oxide"),
    (r"\bnCPAP\b|\bCPAP\b", "cpap"),
]
_NEO_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _NEO_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _NEO_ARM_ABBREV])

# Neonatology endpoints are all binary morbidity/mortality outcomes.
_NEO_CONTINUOUS: set = set()
_NEO_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_NEO_ENDPOINT_PATTERNS,
                                arm_compiled=_NEO_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_NEO_ENDPOINT_PATTERNS,
                               arm_compiled=_NEO_ARM_COMPILED,
                               continuous_endpoints=_NEO_CONTINUOUS,
                               lognormal_endpoints=_NEO_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_NEO_ENDPOINT_PATTERNS,
                              arm_compiled=_NEO_ARM_COMPILED,
                              continuous_endpoints=_NEO_CONTINUOUS,
                              lognormal_endpoints=_NEO_LOGNORMAL)
