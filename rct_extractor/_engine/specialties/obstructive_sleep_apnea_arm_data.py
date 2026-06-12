"""
Arm-level / 2x2 + continuous extraction for obstructive-sleep-apnoea (OSA) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
OSA endpoints and PAP / oral-appliance / surgical / pharmacological / comparator
arm labels:

  binary outcomes (treatment response / AHI normalisation, >=50% AHI reduction)
    -> 2x2 events/N per arm
  continuous (AHI, ODI, ESS, CPAP adherence, blood pressure, minimum SpO2, FOSQ)
    -> mean+SD / median+IQR. NONE is log-normal.

A bare effect abbreviation (HR/OR/RR) is NEVER an arm label.
"""
import re
from typing import Dict, List

from .obstructive_sleep_apnea import get_obstructive_sleep_apnea_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_OSA_ENDPOINT_PATTERNS = []
for _sub in ("cpap", "oral_appliance", "intervention"):
    _OSA_ENDPOINT_PATTERNS.extend(get_obstructive_sleep_apnea_endpoint_patterns(_sub))

# PAP / oral-appliance / surgical / pharmacological / comparator arm labels.
# Full names case-insensitive. Generic comparators included. NO bare effect
# abbreviation (HR/OR/RR) is a label.
_OSA_ARM_FULL = [
    # PAP therapy
    (r"continuous\s+positive\s+airway\s+pressure|\bcpap\b", "cpap"),
    (r"auto[- ]?(?:titrating|adjusting)\s+(?:pap|cpap)|\bapap\b", "apap"),
    (r"bi[- ]?level\s+(?:pap|positive)|\bbipap\b|\bbpap\b", "bipap"),
    # Oral appliance
    (r"mandibular\s+advancement\s+(?:device|splint)|\bmad\b|oral\s+appliance",
     "mandibular-advancement-device"),
    # Surgical / device
    (r"hypoglossal\s+nerve\s+stimulation|upper[- ]airway\s+stimulation",
     "hypoglossal-nerve-stimulation"),
    (r"uvulopalatopharyngoplasty|\buppp\b", "uppp"),
    (r"maxillomandibular\s+advancement", "maxillomandibular-advancement"),
    (r"positional\s+(?:therapy|device)", "positional-therapy"),
    # Pharmacological / lifestyle
    (r"tirzepatide", "tirzepatide"),
    (r"atomoxetine[- ]?(?:plus\s+)?oxybutynin|atomoxetine", "atomoxetine"),
    (r"weight\s+loss|lifestyle\s+intervention|dietary\s+intervention", "weight-loss"),
    # Generic comparators
    (r"sham\s+(?:cpap|device|stimulation)?|sub[- ]?therapeutic\s+cpap", "sham"),
    (r"\bplacebo\b", "placebo"),
    (r"conservative\s+(?:therapy|treatment)|sleep\s+hygiene", "conservative"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|no\s+treatment", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_OSA_ARM_COMPILED = [(re.compile(p, re.I), n) for p, n in _OSA_ARM_FULL]

# OSA continuous outcomes; none log-normal.
_OSA_CONTINUOUS = {"AHI", "ODI", "ESS", "CPAP_ADHERENCE", "BLOOD_PRESSURE",
                   "MINIMUM_SPO2", "FOSQ"}
_OSA_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_OSA_ENDPOINT_PATTERNS,
                                arm_compiled=_OSA_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_OSA_ENDPOINT_PATTERNS,
                               arm_compiled=_OSA_ARM_COMPILED,
                               continuous_endpoints=_OSA_CONTINUOUS,
                               lognormal_endpoints=_OSA_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_OSA_ENDPOINT_PATTERNS,
                              arm_compiled=_OSA_ARM_COMPILED,
                              continuous_endpoints=_OSA_CONTINUOUS,
                              lognormal_endpoints=_OSA_LOGNORMAL)
