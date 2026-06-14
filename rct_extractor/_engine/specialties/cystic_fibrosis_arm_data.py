"""
Arm-level / 2x2 + continuous extraction for cystic-fibrosis trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
cystic-fibrosis endpoints and CFTR-modulator / CF-therapy drug-class arm labels:

  binary (pulmonary exacerbation, Pseudomonas eradication, respiratory
    hospitalisation) -> 2x2 events/N per arm.
  continuous (ppFEV1 / FEV1, lung clearance index, sweat chloride, BMI, weight,
    sputum density, CFQ-R) -> mean+SD / median+IQR, pooled as MD/SMD on the
    natural scale.
"""
import re
from typing import Dict, List

from .cystic_fibrosis import get_cystic_fibrosis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_CF_ENDPOINT_PATTERNS = []
for _sub in ("pulmonary", "nutrition", "microbiology", "systemic"):
    _CF_ENDPOINT_PATTERNS.extend(get_cystic_fibrosis_endpoint_patterns(_sub))

# CFTR-modulator and CF-therapy arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE.
_CF_ARM_FULL = [
    # CFTR modulators
    (r"elexacaftor[-/ ]tezacaftor[-/ ]ivacaftor|elexacaftor/tezacaftor/ivacaftor|"
     r"trikafta|kaftrio", "eti"),
    (r"tezacaftor[-/ ]ivacaftor|symdeko|symkevi", "tezacaftor-ivacaftor"),
    (r"lumacaftor[-/ ]ivacaftor|orkambi", "lumacaftor-ivacaftor"),
    # ivacaftor is the only single-component CFTR modulator used as monotherapy;
    # elexacaftor / tezacaftor / lumacaftor only ever appear inside the combined
    # regimens above, so no standalone labels for them (they would otherwise win
    # the nearest-distance arm match over the combined ETI / LUM-IVA / TEZ-IVA
    # label as a left-anchored substring).
    (r"ivacaftor|kalydeco", "ivacaftor"),
    # mucoactive
    (r"dornase\s+alfa|rhdnase|pulmozyme", "dornase-alfa"),
    (r"hypertonic\s+saline", "hypertonic-saline"),
    (r"inhaled\s+mannitol|mannitol|bronchitol", "mannitol"),
    # inhaled antibiotics
    (r"(?:inhaled\s+|nebulised\s+|nebulized\s+)?tobramycin|tobi", "tobramycin"),
    (r"aztreonam(?:\s+lysine)?|cayston", "aztreonam"),
    (r"colistimethate|colistin|colomycin", "colistin"),
    # read-through
    (r"ataluren|ptc124", "ataluren"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|best\s+supportive\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_CF_ARM_ABBREV = [
    (r"\bETI\b|\bELX/TEZ/IVA\b", "eti"),
    (r"\bLUM/IVA\b", "lumacaftor-ivacaftor"),
    (r"\bTEZ/IVA\b", "tezacaftor-ivacaftor"),
]
_CF_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _CF_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _CF_ARM_ABBREV])

# Cystic-fibrosis continuous outcomes (natural scale).
_CF_CONTINUOUS = {"PPFEV1", "FEV1", "LCI", "SWEAT_CHLORIDE", "BMI", "WEIGHT",
                  "SPUTUM_DENSITY", "CFQ_R"}
_CF_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_CF_ENDPOINT_PATTERNS,
                                arm_compiled=_CF_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_CF_ENDPOINT_PATTERNS,
                               arm_compiled=_CF_ARM_COMPILED,
                               continuous_endpoints=_CF_CONTINUOUS,
                               lognormal_endpoints=_CF_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_CF_ENDPOINT_PATTERNS,
                              arm_compiled=_CF_ARM_COMPILED,
                              continuous_endpoints=_CF_CONTINUOUS,
                              lognormal_endpoints=_CF_LOGNORMAL)
