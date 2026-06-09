"""
Arm-level / 2x2 + continuous extraction for cholera (Vibrio cholerae) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with cholera
endpoints and antibiotic / vaccine / ORS arm labels:

  binary outcomes (clinical cure, bacteriological clearance, treatment failure,
    seroconversion, severe dehydration, hypovolaemic shock, AKI, death,
    unscheduled IV, vomiting) -> 2x2 events/N per arm
  continuous (duration of diarrhoea, total stool output, ORS / fluid intake,
    hospital stay -> mean+SD / median+IQR; vibriocidal titre -> log-normal, pool
    on the log scale).
"""
import re
from typing import Dict, List

from .cholera import get_cholera_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Cholera endpoint patterns (string, endpoint) across all subspecialties.
_CHOLERA_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "rehydration", "vaccine", "severe"):
    _CHOLERA_ENDPOINT_PATTERNS.extend(get_cholera_endpoint_patterns(_sub))

# Antibiotic / vaccine / ORS arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token won't match).
_CHOLERA_ARM_FULL = [
    # antibiotics
    (r"doxycycline", "doxycycline"),
    (r"azithromycin", "azithromycin"),
    (r"ciprofloxacin", "ciprofloxacin"),
    (r"erythromycin", "erythromycin"),
    (r"tetracycline", "tetracycline"),
    (r"norfloxacin", "norfloxacin"),
    (r"furazolidone", "furazolidone"),
    (r"ampicillin", "ampicillin"),
    (r"chloramphenicol", "chloramphenicol"),
    (r"co[- ]?trimoxazole|trimethoprim[- ]sulfamethoxazole", "co-trimoxazole"),
    # vaccines
    (r"oral\s+cholera\s+vaccine", "oral-cholera-vaccine"),
    (r"dukoral|wc[- ]?rbs", "dukoral"),
    (r"shanchol", "shanchol"),
    (r"euvichol(?:[- ]plus)?", "euvichol"),
    (r"hillchol|\bbivwc\b", "hillchol"),
    (r"killed\s+whole[- ]cell(?:\s+vaccine)?", "killed-whole-cell"),
    (r"cvd\s*103[- ]?hgr|vaxchora", "cvd103-hgr"),
    # rehydration arms
    (r"rice[- ]based\s+(?:ors|oral\s+rehydration|solution)?", "rice-based-ors"),
    (r"reduced[- ]osmolarity\s+(?:ors|oral\s+rehydration|solution)?|"
     r"hypo[- ]?osmolar\s+(?:ors|solution)?|low[- ]osmolarity\s+(?:ors|solution)?",
     "reduced-osmolarity-ors"),
    (r"glucose[- ]based\s+(?:ors|solution)|glucose\s+ors|standard\s+ors|"
     r"standard\s+oral\s+rehydration", "standard-ors"),
    (r"ringer'?s?\s+lactate|lactated\s+ringer", "ringers-lactate"),
    # controls / generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_CHOLERA_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bOCV\b", "oral-cholera-vaccine"),
    (r"\bDOX\b", "doxycycline"),
    (r"\bAZM\b|\bAZI\b", "azithromycin"),
    (r"\bCIP\b", "ciprofloxacin"),
]
_CHOLERA_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _CHOLERA_ARM_FULL]
                         + [(re.compile(p), n) for p, n in _CHOLERA_ARM_ABBREV])

# Cholera continuous outcomes; vibriocidal titre (immunogenicity) is log-normal.
_CHOLERA_CONTINUOUS = {"DIARRHEA_DURATION", "STOOL_OUTPUT", "ORS_INTAKE",
                       "HOSPITAL_STAY", "IMMUNOGENICITY"}
_CHOLERA_LOGNORMAL = {"IMMUNOGENICITY"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_CHOLERA_ENDPOINT_PATTERNS,
                                arm_compiled=_CHOLERA_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_CHOLERA_ENDPOINT_PATTERNS,
                               arm_compiled=_CHOLERA_ARM_COMPILED,
                               continuous_endpoints=_CHOLERA_CONTINUOUS,
                               lognormal_endpoints=_CHOLERA_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_CHOLERA_ENDPOINT_PATTERNS,
                              arm_compiled=_CHOLERA_ARM_COMPILED,
                              continuous_endpoints=_CHOLERA_CONTINUOUS,
                              lognormal_endpoints=_CHOLERA_LOGNORMAL)
