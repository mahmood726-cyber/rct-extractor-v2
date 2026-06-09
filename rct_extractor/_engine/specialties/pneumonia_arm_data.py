"""
Arm-level / 2x2 + continuous extraction for childhood pneumonia / ARI trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with pneumonia
endpoints and antibiotic / pneumococcal-vaccine arm labels:

  binary outcomes (clinical cure, treatment failure, relapse, IPD, nasopharyngeal
    carriage, hospitalisation, ICU admission, mechanical ventilation, empyema,
    death) -> 2x2 events/N per arm
  continuous (time to symptom resolution, oxygen saturation, hospital stay ->
    mean+SD / median+IQR; anti-pneumococcal IgG GMC -> log-normal, pool on the
    log scale).
"""
import re
from typing import Dict, List

from .pneumonia import get_pneumonia_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Pneumonia endpoint patterns (string, endpoint) across all subspecialties.
_PNEUMONIA_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "vaccine", "mortality", "severe"):
    _PNEUMONIA_ENDPOINT_PATTERNS.extend(get_pneumonia_endpoint_patterns(_sub))

# Antibiotic / vaccine arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
# amoxicillin uses a negative lookahead so "amoxicillin-clavulanate" stays distinct.
_PNEUMONIA_ARM_FULL = [
    # antibiotics
    (r"amoxicillin[- ]clavulanate|co[- ]?amoxiclav", "amoxicillin-clavulanate"),
    (r"amoxicillin(?![- ]?clav)", "amoxicillin"),
    (r"co[- ]?trimoxazole|trimethoprim[- ]sulfamethoxazole", "co-trimoxazole"),
    (r"benzylpenicillin", "benzylpenicillin"),
    (r"penicillin", "penicillin"),
    (r"ampicillin", "ampicillin"),
    (r"ceftriaxone", "ceftriaxone"),
    (r"cefuroxime", "cefuroxime"),
    (r"cefotaxime", "cefotaxime"),
    (r"azithromycin", "azithromycin"),
    (r"chloramphenicol", "chloramphenicol"),
    (r"gentamicin", "gentamicin"),
    # vaccines
    (r"pneumococcal\s+conjugate\s+vaccine", "pneumococcal-conjugate-vaccine"),
    (r"\bppsv[- ]?23\b|23[- ]valent\s+polysaccharide", "ppsv23"),
    (r"haemophilus\s+influenzae\s+type\s+b\s+vaccine|hib\s+vaccine", "hib-vaccine"),
    # controls / generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_PNEUMONIA_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bPCV\s*\d{1,2}\b|\bPCV\b", "pneumococcal-conjugate-vaccine"),
    (r"\bPPSV\s*\d{0,2}\b", "ppsv23"),
    (r"\bHib\b", "hib-vaccine"),
    (r"\bAMX\b", "amoxicillin"),
    (r"\bSXT\b|\bTMP[- ]?SMX\b", "co-trimoxazole"),
    (r"\bCRO\b", "ceftriaxone"),
    (r"\bAZM\b|\bAZI\b", "azithromycin"),
]
_PNEUMONIA_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _PNEUMONIA_ARM_FULL]
                           + [(re.compile(p), n) for p, n in _PNEUMONIA_ARM_ABBREV])

# Pneumonia continuous outcomes; anti-pneumococcal IgG GMC (immunogenicity) is log-normal.
_PNEUMONIA_CONTINUOUS = {"TIME_TO_RESOLUTION", "OXYGEN_SATURATION", "HOSPITAL_STAY",
                         "IMMUNOGENICITY"}
_PNEUMONIA_LOGNORMAL = {"IMMUNOGENICITY"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_PNEUMONIA_ENDPOINT_PATTERNS,
                                arm_compiled=_PNEUMONIA_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_PNEUMONIA_ENDPOINT_PATTERNS,
                               arm_compiled=_PNEUMONIA_ARM_COMPILED,
                               continuous_endpoints=_PNEUMONIA_CONTINUOUS,
                               lognormal_endpoints=_PNEUMONIA_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_PNEUMONIA_ENDPOINT_PATTERNS,
                              arm_compiled=_PNEUMONIA_ARM_COMPILED,
                              continuous_endpoints=_PNEUMONIA_CONTINUOUS,
                              lognormal_endpoints=_PNEUMONIA_LOGNORMAL)
