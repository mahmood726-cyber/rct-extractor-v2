"""
Arm-level / 2x2 + continuous extraction for meningitis trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with meningitis
endpoints and antibiotic / adjunctive / vaccine arm labels:

  binary outcomes (clinical cure, treatment failure, CSF sterilisation, death,
    hearing loss, neurological sequelae, seizures, carriage) -> 2x2 events/N per arm
  continuous (time to recovery / fever clearance -> mean+SD / median+IQR;
    SBA titre -> log-normal, pool on the log scale).
"""
import re
from typing import Dict, List

from .meningitis import get_meningitis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Meningitis endpoint patterns (string, endpoint) across all subspecialties.
_MENINGITIS_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "vaccine", "mortality", "sequelae"):
    _MENINGITIS_ENDPOINT_PATTERNS.extend(get_meningitis_endpoint_patterns(_sub))

# Antibiotic / adjunctive / vaccine arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_MENINGITIS_ARM_FULL = [
    # antibiotics
    (r"ceftriaxone", "ceftriaxone"),
    (r"cefotaxime", "cefotaxime"),
    (r"oily\s+chloramphenicol", "oily-chloramphenicol"),
    (r"chloramphenicol", "chloramphenicol"),
    (r"benzylpenicillin", "benzylpenicillin"),
    (r"\bpenicillin\b", "penicillin"),
    (r"ampicillin", "ampicillin"),
    (r"meropenem", "meropenem"),
    (r"vancomycin", "vancomycin"),
    (r"ceftazidime", "ceftazidime"),
    # adjunctive
    (r"dexamethasone", "dexamethasone"),
    (r"glycerol", "glycerol"),
    # vaccines
    (r"meningococcal\s+(?:a\s+)?conjugate\s+vaccine|menafrivac|\bmena[- ]?tt\b",
     "meningococcal-conjugate-vaccine"),
    (r"pneumococcal\s+conjugate\s+vaccine|prevnar|synflorix", "pneumococcal-conjugate-vaccine"),
    (r"haemophilus\s+influenzae\s+type\s+b\s+(?:conjugate\s+)?vaccine", "hib-vaccine"),
    (r"polysaccharide\s+vaccine", "polysaccharide-vaccine"),
    (r"bexsero|4cmenb", "4cmenb"),
    # generic comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_MENINGITIS_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bCRO\b", "ceftriaxone"),
    (r"\bCTX\b", "cefotaxime"),
    (r"\bDEX\b", "dexamethasone"),
    (r"\bPCV\b|\bPCV1[03]\b", "pneumococcal-conjugate-vaccine"),
    (r"\bHib\b", "hib-vaccine"),
    (r"\bMenA\b|\bMenAfriVac\b", "meningococcal-conjugate-vaccine"),
    (r"\bMenACWY\b|\bMenC\b|\bMenB\b", "meningococcal-conjugate-vaccine"),
]
_MENINGITIS_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _MENINGITIS_ARM_FULL]
                            + [(re.compile(p), n) for p, n in _MENINGITIS_ARM_ABBREV])

# Meningitis continuous outcomes; SBA titre (immunogenicity) is log-normal.
_MENINGITIS_CONTINUOUS = {"TIME_TO_RECOVERY", "IMMUNOGENICITY"}
_MENINGITIS_LOGNORMAL = {"IMMUNOGENICITY"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_MENINGITIS_ENDPOINT_PATTERNS,
                                arm_compiled=_MENINGITIS_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_MENINGITIS_ENDPOINT_PATTERNS,
                               arm_compiled=_MENINGITIS_ARM_COMPILED,
                               continuous_endpoints=_MENINGITIS_CONTINUOUS,
                               lognormal_endpoints=_MENINGITIS_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_MENINGITIS_ENDPOINT_PATTERNS,
                              arm_compiled=_MENINGITIS_ARM_COMPILED,
                              continuous_endpoints=_MENINGITIS_CONTINUOUS,
                              lognormal_endpoints=_MENINGITIS_LOGNORMAL)
