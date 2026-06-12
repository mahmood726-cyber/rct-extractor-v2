"""
Arm-level / 2x2 + continuous extraction for allergic-conjunctivitis trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
ocular-allergy endpoints and ocular-antihistamine / mast-cell-stabilizer /
steroid / immunomodulator arm labels:

  binary outcomes (composite symptom responder, corneal involvement) -> 2x2
    events/N per arm
  continuous (ocular itching, conjunctival hypera?emia, tearing, chemosis,
    eyelid swelling, total ocular symptom score) -> mean+SD / median+IQR.
    NONE is log-normal -- all bounded ocular symptom scales pooled on raw scale.

A bare effect abbreviation (HR/OR/RR) is NEVER an arm label.
"""
import re
from typing import Dict, List

from .allergic_conjunctivitis import get_allergic_conjunctivitis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_AC_ENDPOINT_PATTERNS = []
for _sub in ("seasonal_perennial", "vernal_atopic", "challenge_model"):
    _AC_ENDPOINT_PATTERNS.extend(get_allergic_conjunctivitis_endpoint_patterns(_sub))

# Ocular-antihistamine / mast-cell-stabilizer / steroid / immunomodulator arm
# labels. Full names case-insensitive. Generic comparators included so a
# drug-vs-comparator 2x2 pairs. NO bare effect abbreviation (HR/OR/RR) is a label.
_AC_ARM_FULL = [
    # Ocular antihistamines / dual-action
    (r"olopatadine|\bpatanol\b|\bpataday\b|\bpazeo\b", "olopatadine"),
    (r"ketotifen|\bzaditor\b|\bzaditen\b", "ketotifen"),
    (r"bepotastine|\bbepreve\b", "bepotastine"),
    (r"alcaftadine|\blastacaft\b", "alcaftadine"),
    (r"epinastine|\belestat\b", "epinastine"),
    (r"emedastine|\bemadine\b", "emedastine"),
    (r"levocabastine|\blivostin\b", "levocabastine"),
    (r"azelastine\s+(?:ophthalmic|eye)|azelastine", "azelastine"),
    (r"cetirizine\s+(?:ophthalmic|eye)|cetirizine", "cetirizine"),
    # Mast-cell stabilizers
    (r"sodium\s+cromoglicate|cromoglicate|cromolyn(?:\s+sodium)?|cromoglycate", "cromolyn"),
    (r"nedocromil", "nedocromil"),
    (r"lodoxamide|\balomide\b", "lodoxamide"),
    (r"pemirolast", "pemirolast"),
    # Steroids
    (r"loteprednol(?:\s+etabonate)?|\blotemax\b|\balrex\b", "loteprednol"),
    (r"fluorometholone|\bfml\b", "fluorometholone"),
    # Immunomodulators (VKC/AKC)
    (r"cic?losporine?|ciclosporin|\bverkazia\b|\bikervis\b", "cyclosporine"),
    (r"tacrolimus", "tacrolimus"),
    # Generic comparators
    (r"\bplacebo\b", "placebo"),
    (r"\bvehicle\b", "vehicle"),
    (r"artificial\s+tears?|saline(?:\s+drops?)?|lubricant\s+drops?", "artificial-tears"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_AC_ARM_COMPILED = [(re.compile(p, re.I), n) for p, n in _AC_ARM_FULL]

# All ocular-allergy continuous outcomes; none log-normal.
_AC_CONTINUOUS = {"OCULAR_ITCHING", "CONJUNCTIVAL_HYPERAEMIA", "TEARING",
                  "CHEMOSIS", "EYELID_SWELLING", "TOSS"}
_AC_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_AC_ENDPOINT_PATTERNS,
                                arm_compiled=_AC_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_AC_ENDPOINT_PATTERNS,
                               arm_compiled=_AC_ARM_COMPILED,
                               continuous_endpoints=_AC_CONTINUOUS,
                               lognormal_endpoints=_AC_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_AC_ENDPOINT_PATTERNS,
                              arm_compiled=_AC_ARM_COMPILED,
                              continuous_endpoints=_AC_CONTINUOUS,
                              lognormal_endpoints=_AC_LOGNORMAL)
