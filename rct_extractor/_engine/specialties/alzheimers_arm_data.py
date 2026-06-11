"""
Arm-level / 2x2 + continuous extraction for Alzheimer's disease / dementia trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
AD endpoints and AD arm labels:

  binary outcomes (responder, ARIA, progression-to-dementia, psychosis, adverse
    events) -> 2x2 events/N per arm.
  continuous outcomes (ADAS-Cog, CDR-SB, MMSE, ADCS-ADL, iADRS, NPI, CMAI,
    amyloid PET centiloids) -> per-arm mean +/- SD, pooled as a mean difference.

AD interventions: cholinesterase inhibitors / memantine, anti-amyloid mAbs
(lecanemab, aducanumab, donanemab, ...), BPSD agents (brexpiprazole), placebo.
"""
import re
from typing import Dict, List

from .alzheimers import get_alzheimers_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_AD_ENDPOINT_PATTERNS = []
for _sub in ("symptomatic", "disease_modifying", "neuropsychiatric", "prevention_mci"):
    _AD_ENDPOINT_PATTERNS.extend(get_alzheimers_endpoint_patterns(_sub))

_AD_ARM_FULL = [
    (r"donepezil", "donepezil"),
    (r"rivastigmine", "rivastigmine"),
    (r"galantamine", "galantamine"),
    (r"memantine", "memantine"),
    (r"lecanemab", "lecanemab"),
    (r"aducanumab", "aducanumab"),
    (r"donanemab", "donanemab"),
    (r"gantenerumab", "gantenerumab"),
    (r"solanezumab", "solanezumab"),
    (r"crenezumab", "crenezumab"),
    (r"bapineuzumab", "bapineuzumab"),
    (r"brexpiprazole", "brexpiprazole"),
    (r"pimavanserin", "pimavanserin"),
    (r"citalopram", "citalopram"),
    (r"risperidone", "risperidone"),
    (r"\bplacebo\b", "placebo"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care", "standard-of-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"active\s+(?:treatment|comparator)", "active"),
    (r"high[- ]dose", "high-dose"),
    (r"low[- ]dose", "low-dose"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_AD_ARM_ABBREV = []  # AD trials rarely use bare drug abbreviations
_AD_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _AD_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _AD_ARM_ABBREV])

_AD_CONTINUOUS = {"ADAS_COG", "CDR_SB", "MMSE", "ADCS_ADL", "IADRS", "NPI",
                  "AGITATION", "AMYLOID_PET"}
_AD_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_AD_ENDPOINT_PATTERNS,
                                arm_compiled=_AD_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_AD_ENDPOINT_PATTERNS,
                               arm_compiled=_AD_ARM_COMPILED,
                               continuous_endpoints=_AD_CONTINUOUS,
                               lognormal_endpoints=_AD_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_AD_ENDPOINT_PATTERNS,
                              arm_compiled=_AD_ARM_COMPILED,
                              continuous_endpoints=_AD_CONTINUOUS,
                              lognormal_endpoints=_AD_LOGNORMAL)
