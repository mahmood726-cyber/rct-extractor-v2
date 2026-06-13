"""
Arm-level / 2x2 + continuous extraction for bronchiectasis (non-CF) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
bronchiectasis endpoints and bronchiectasis-therapy drug-class arm labels:

  binary/rate (exacerbation, severe exacerbation, hospitalisation, Pseudomonas
    eradication) -> 2x2 events/N per arm.
  continuous (FEV1 / ppFEV1, QOL-B / SGRQ, bacterial load, sputum volume, cough)
    -> mean+SD / median+IQR, pooled as MD/SMD on the natural scale.
"""
import re
from typing import Dict, List

from .bronchiectasis import get_bronchiectasis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_BR_ENDPOINT_PATTERNS = []
for _sub in ("exacerbation", "microbiology", "function", "symptoms"):
    _BR_ENDPOINT_PATTERNS.extend(get_bronchiectasis_endpoint_patterns(_sub))

# Bronchiectasis-therapy arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE.
_BR_ARM_FULL = [
    # inhaled antibiotics
    (r"(?:inhaled\s+|nebulised\s+|nebulized\s+)?tobramycin", "tobramycin"),
    (r"(?:inhaled\s+|nebulised\s+|nebulized\s+)?colistimethate|colistin|colomycin", "colistin"),
    (r"aztreonam(?:\s+lysine)?", "aztreonam"),
    (r"(?:inhaled\s+|nebulised\s+|nebulized\s+)?gentamicin", "gentamicin"),
    (r"ciprofloxacin\s+(?:dry\s+powder|dpi)|inhaled\s+ciprofloxacin|ciprofloxacin", "ciprofloxacin"),
    # macrolides
    (r"azithromycin", "azithromycin"),
    (r"erythromycin", "erythromycin"),
    (r"clarithromycin|roxithromycin", "clarithromycin"),
    # DPP-1 inhibitor
    (r"brensocatib", "brensocatib"),
    # mucoactive / clearance
    (r"hypertonic\s+saline", "hypertonic-saline"),
    (r"(?:inhaled\s+)?mannitol|bronchitol", "mannitol"),
    (r"carbocisteine|carbocysteine", "carbocisteine"),
    (r"airway\s+clearance|chest\s+physiotherapy", "airway-clearance"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|best\s+supportive\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_BR_ARM_ABBREV = [
    (r"\bHTS\b", "hypertonic-saline"),
]
_BR_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _BR_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _BR_ARM_ABBREV])

# Bronchiectasis continuous outcomes (natural scale).
_BR_CONTINUOUS = {"BACTERIAL_LOAD", "FEV1", "QUALITY_OF_LIFE", "SPUTUM_VOLUME", "COUGH"}
_BR_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_BR_ENDPOINT_PATTERNS,
                                arm_compiled=_BR_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_BR_ENDPOINT_PATTERNS,
                               arm_compiled=_BR_ARM_COMPILED,
                               continuous_endpoints=_BR_CONTINUOUS,
                               lognormal_endpoints=_BR_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_BR_ENDPOINT_PATTERNS,
                              arm_compiled=_BR_ARM_COMPILED,
                              continuous_endpoints=_BR_CONTINUOUS,
                              lognormal_endpoints=_BR_LOGNORMAL)
