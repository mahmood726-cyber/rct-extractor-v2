"""
Arm-level / 2x2 + continuous extraction for diarrhoeal-disease trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with diarrhoeal
endpoints and ORS / zinc / rotavirus-vaccine / antibiotic arm labels:

  binary outcomes (rehydration/treatment failure, clinical cure, bacteriological
    cure, vomiting, dehydration, persistent diarrhoea, mortality,
    rotavirus gastroenteritis) -> 2x2 events/N per arm
  continuous (duration of diarrhoea, stool output, stool frequency, ORS intake,
    time to resolution -> mean+SD / median+IQR; anti-rotavirus IgA titre ->
    log-normal, pool on the log scale).
"""
import re
from typing import Dict, List

from .diarrhoeal import get_diarrhoeal_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Diarrhoeal endpoint patterns (string, endpoint) across all subspecialties.
_DIARRHOEAL_ENDPOINT_PATTERNS = []
for _sub in ("rehydration", "rotavirus", "treatment", "mortality_duration"):
    _DIARRHOEAL_ENDPOINT_PATTERNS.extend(get_diarrhoeal_endpoint_patterns(_sub))

# ORS / zinc / antibiotic / rotavirus-vaccine arm labels. Full names
# case-insensitive; bare UPPERCASE abbreviations CASE-SENSITIVE (so a stray
# lowercase token does not match).
_DIARRHOEAL_ARM_FULL = [
    # rehydration / supportive
    (r"reduced[- ]osmolarity\s+(?:ors|oral\s+rehydration)", "reduced-osmolarity-ors"),
    (r"hypo[- ]?osmolar\s+(?:ors|oral\s+rehydration)", "hypo-osmolar-ors"),
    (r"rice[- ]based\s+(?:ors|oral\s+rehydration)", "rice-based-ors"),
    (r"standard\s+(?:who\s+)?(?:ors|oral\s+rehydration)", "standard-ors"),
    (r"oral\s+rehydration\s+(?:solution|salts?)", "ors"),
    (r"zinc\s+(?:sulphate|sulfate|acetate|gluconate)|zinc\s+supplement(?:ation)?|\bzinc\b", "zinc"),
    (r"racecadotril", "racecadotril"),
    (r"saccharomyces\s+boulardii", "saccharomyces-boulardii"),
    (r"lactobacillus(?:\s+\w+)?|probiotics?", "probiotic"),
    (r"smectite|diosmectite", "smectite"),
    (r"loperamide", "loperamide"),
    # antibiotics
    (r"azithromycin", "azithromycin"),
    (r"ciprofloxacin", "ciprofloxacin"),
    (r"ofloxacin", "ofloxacin"),
    (r"ceftriaxone", "ceftriaxone"),
    (r"cefixime", "cefixime"),
    (r"nalidixic\s+acid", "nalidixic-acid"),
    (r"co[- ]?trimoxazole|trimethoprim[- ]sulfamethoxazole", "co-trimoxazole"),
    (r"metronidazole", "metronidazole"),
    (r"erythromycin", "erythromycin"),
    # rotavirus vaccines
    (r"rotarix", "rotarix"),
    (r"rotateq", "rotateq"),
    (r"rotavac", "rotavac"),
    (r"rotasiil", "rotasiil"),
    (r"rotavirus\s+vaccine", "rotavirus-vaccine"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"no\s+(?:zinc|supplement|treatment)", "no-treatment"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_DIARRHOEAL_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bORS\b", "ors"),
    (r"\bRV1\b", "rotarix"),
    (r"\bRV5\b", "rotateq"),
    (r"\bAZM\b|\bAZI\b", "azithromycin"),
    (r"\bCIP\b", "ciprofloxacin"),
    (r"\bCRO\b", "ceftriaxone"),
]
_DIARRHOEAL_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _DIARRHOEAL_ARM_FULL]
                            + [(re.compile(p), n) for p, n in _DIARRHOEAL_ARM_ABBREV])

# Diarrhoeal continuous outcomes; anti-rotavirus IgA titre (immunogenicity) is
# log-normal and must be pooled on the log scale.
_DIARRHOEAL_CONTINUOUS = {"DIARRHOEA_DURATION", "STOOL_OUTPUT", "STOOL_FREQUENCY",
                          "ORS_INTAKE", "TIME_TO_RESOLUTION", "RV_IMMUNOGENICITY"}
_DIARRHOEAL_LOGNORMAL = {"RV_IMMUNOGENICITY"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_DIARRHOEAL_ENDPOINT_PATTERNS,
                                arm_compiled=_DIARRHOEAL_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_DIARRHOEAL_ENDPOINT_PATTERNS,
                               arm_compiled=_DIARRHOEAL_ARM_COMPILED,
                               continuous_endpoints=_DIARRHOEAL_CONTINUOUS,
                               lognormal_endpoints=_DIARRHOEAL_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_DIARRHOEAL_ENDPOINT_PATTERNS,
                              arm_compiled=_DIARRHOEAL_ARM_COMPILED,
                              continuous_endpoints=_DIARRHOEAL_CONTINUOUS,
                              lognormal_endpoints=_DIARRHOEAL_LOGNORMAL)
