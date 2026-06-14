"""
Arm-level / 2x2 extraction for emergency-medicine / resuscitation trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
emergency/resuscitation endpoints and resuscitation-intervention arm labels. All
resuscitation/trauma/airway endpoints are binary -> 2x2 events/N per arm.
"""
import re
from typing import Dict, List

from .emergency_resuscitation import get_emergency_resuscitation_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_ER_ENDPOINT_PATTERNS = []
for _sub in ("cardiac_arrest", "trauma", "airway", "acute_care"):
    _ER_ENDPOINT_PATTERNS.extend(get_emergency_resuscitation_endpoint_patterns(_sub))

# Resuscitation-intervention arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE.
_ER_ARM_FULL = [
    # vasopressors / antiarrhythmics
    (r"adrenaline|epinephrine", "adrenaline"),
    (r"vasopressin", "vasopressin"),
    (r"amiodarone", "amiodarone"),
    (r"lidocaine|lignocaine", "lidocaine"),
    # trauma
    (r"tranexamic\s+acid", "tranexamic-acid"),
    # temperature / mechanical
    (r"targeted\s+temperature\s+management|therapeutic\s+hypothermia|(?:whole[- ]body\s+)?cooling",
     "targeted-temperature-management"),
    (r"normothermia", "normothermia"),
    (r"mechanical\s+(?:chest\s+compression|cpr)|lucas\b|autopulse", "mechanical-cpr"),
    (r"extracorporeal\s+(?:cpr|cardiopulmonary)|\becpr\b|\becmo\b", "ecpr"),
    # airway devices
    (r"supraglottic\s+airway|laryngeal\s+mask|i[- ]?gel", "supraglottic-airway"),
    (r"endotracheal\s+intubation|tracheal\s+intubation", "tracheal-intubation"),
    (r"bag[- ](?:valve[- ]mask|mask\s+ventilation)|\bbvm\b", "bag-valve-mask"),
    (r"video\s+laryngoscop\w*", "video-laryngoscopy"),
    (r"direct\s+laryngoscop\w*", "direct-laryngoscopy"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|standard\s+(?:advanced\s+life\s+support|treatment)",
     "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_ER_ARM_ABBREV = [
    (r"\bTXA\b", "tranexamic-acid"),
    (r"\bTTM\b", "targeted-temperature-management"),
    (r"\bECPR\b|\bECMO\b", "ecpr"),
    (r"\bSGA\b", "supraglottic-airway"),
    (r"\bETI\b", "tracheal-intubation"),
]
_ER_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _ER_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _ER_ARM_ABBREV])

# Emergency/resuscitation endpoints are all binary outcomes.
_ER_CONTINUOUS: set = set()
_ER_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_ER_ENDPOINT_PATTERNS,
                                arm_compiled=_ER_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_ER_ENDPOINT_PATTERNS,
                               arm_compiled=_ER_ARM_COMPILED,
                               continuous_endpoints=_ER_CONTINUOUS,
                               lognormal_endpoints=_ER_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_ER_ENDPOINT_PATTERNS,
                              arm_compiled=_ER_ARM_COMPILED,
                              continuous_endpoints=_ER_CONTINUOUS,
                              lognormal_endpoints=_ER_LOGNORMAL)
