"""
Arm-level / 2x2 + continuous extraction for liver-transplant trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
liver-transplant endpoints and immunosuppression drug-class arm labels:

  binary (acute / antibody-mediated rejection, graft loss / retransplantation,
    hepatic artery thrombosis, biliary complication, primary non-function,
    patient survival, HCC recurrence, CMV infection, NODAT) -> 2x2 events/N per arm.
  continuous (eGFR / measured GFR, serum creatinine) -> mean+SD / median+IQR,
    pooled as MD/SMD on the natural scale.
"""
import re
from typing import Dict, List

from .liver_transplant import get_liver_transplant_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_LT_ENDPOINT_PATTERNS = []
for _sub in ("rejection", "graft", "function", "complications"):
    _LT_ENDPOINT_PATTERNS.extend(get_liver_transplant_endpoint_patterns(_sub))

# Immunosuppression drug-class arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE.
_LT_ARM_FULL = [
    # calcineurin inhibitors
    (r"extended[- ]release\s+tacrolimus|prolonged[- ]release\s+tacrolimus|tacrolimus", "tacrolimus"),
    (r"ciclosporin|cyclosporine|cyclosporin", "ciclosporin"),
    # antiproliferatives
    (r"mycophenolate\s+mofetil|mycophenolate|mycophenolic\s+acid", "mycophenolate"),
    (r"azathioprine", "azathioprine"),
    # mTOR inhibitors
    (r"everolimus", "everolimus"),
    (r"sirolimus|rapamycin", "sirolimus"),
    # induction
    (r"basiliximab", "basiliximab"),
    (r"anti[- ]thymocyte\s+globulin|antithymocyte\s+globulin|thymoglobulin", "atg"),
    # steroids / other
    (r"corticosteroid|prednisone|prednisolone|steroid", "corticosteroid"),
    (r"steroid[- ](?:free|avoidance|withdrawal)", "steroid-avoidance"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|standard\s+immunosuppression", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_LT_ARM_ABBREV = [
    (r"\bTAC\b|\bFK506\b", "tacrolimus"),
    (r"\bCsA\b", "ciclosporin"),
    (r"\bMMF\b|\bMPA\b", "mycophenolate"),
    (r"\bATG\b|\brATG\b", "atg"),
    (r"\bAZA\b", "azathioprine"),
    (r"\bEVR\b", "everolimus"),
]
_LT_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _LT_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _LT_ARM_ABBREV])

# Liver-transplant continuous outcomes (renal function; natural scale).
_LT_CONTINUOUS = {"EGFR", "SERUM_CREATININE"}
_LT_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_LT_ENDPOINT_PATTERNS,
                                arm_compiled=_LT_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_LT_ENDPOINT_PATTERNS,
                               arm_compiled=_LT_ARM_COMPILED,
                               continuous_endpoints=_LT_CONTINUOUS,
                               lognormal_endpoints=_LT_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_LT_ENDPOINT_PATTERNS,
                              arm_compiled=_LT_ARM_COMPILED,
                              continuous_endpoints=_LT_CONTINUOUS,
                              lognormal_endpoints=_LT_LOGNORMAL)
