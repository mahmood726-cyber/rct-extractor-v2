"""
Arm-level / 2x2 + continuous extraction for HIV trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with HIV endpoints
and antiretroviral arm labels:

  binary outcomes (viral suppression, virologic failure, HIV acquisition, MTCT,
    discontinuation) -> 2x2 events/N per arm
  continuous (CD4 change, HIV-RNA, weight) -> mean+SD / median+IQR; HIV-RNA is
    log-normal (pool on the log scale).
"""
import re
from typing import Dict, List

from .hiv import get_hiv_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# HIV endpoint patterns (string, endpoint) across all subspecialties.
_HIV_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "prevention", "pmtct", "coinfection"):
    _HIV_ENDPOINT_PATTERNS.extend(get_hiv_endpoint_patterns(_sub))

# Antiretroviral arm labels. Full names case-insensitive; bare UPPERCASE drug
# abbreviations CASE-SENSITIVE (so "art" the word != ART regimen tokens, and
# 3TC/AZT etc. only match uppercase).
_HIV_ARM_FULL = [
    (r"dolutegravir", "dolutegravir"),
    (r"bictegravir", "bictegravir"),
    (r"raltegravir", "raltegravir"),
    (r"elvitegravir", "elvitegravir"),
    (r"cabotegravir", "cabotegravir"),
    (r"efavirenz", "efavirenz"),
    (r"nevirapine", "nevirapine"),
    (r"rilpivirine", "rilpivirine"),
    (r"doravirine", "doravirine"),
    (r"tenofovir\s+alafenamide", "tenofovir-alafenamide"),
    (r"tenofovir(?:\s+disoproxil)?", "tenofovir"),
    (r"emtricitabine", "emtricitabine"),
    (r"lamivudine", "lamivudine"),
    (r"abacavir", "abacavir"),
    (r"zidovudine", "zidovudine"),
    (r"lopinavir(?:[/-]ritonavir)?", "lopinavir-ritonavir"),
    (r"darunavir", "darunavir"),
    (r"atazanavir", "atazanavir"),
    (r"lenacapavir", "lenacapavir"),
    (r"dapivirine\s+ring|vaginal\s+ring", "dapivirine-ring"),
    (r"\bplacebo\b", "placebo"),
    (r"maternal\s+(?:antiretroviral|art)|antiretroviral\s+(?:therapy\s+)?(?:group|arm)|"
     r"art\s+(?:group|arm)", "ART"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_HIV_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bDTG\b", "dolutegravir"),
    (r"\bBIC\b", "bictegravir"),
    (r"\bRAL\b", "raltegravir"),
    (r"\bEVG\b", "elvitegravir"),
    (r"\bCAB(?:[- ]?LA)?\b", "cabotegravir"),
    (r"\bEFV\b", "efavirenz"),
    (r"\bNVP\b", "nevirapine"),
    (r"\bRPV\b", "rilpivirine"),
    (r"\bDOR\b", "doravirine"),
    (r"\bTAF\b", "tenofovir-alafenamide"),
    (r"\bTDF\b", "tenofovir"),
    (r"\bFTC\b", "emtricitabine"),
    (r"\b3TC\b", "lamivudine"),
    (r"\bABC\b", "abacavir"),
    (r"\b(?:AZT|ZDV)\b", "zidovudine"),
    (r"\bDRV\b", "darunavir"),
    (r"\bATV\b", "atazanavir"),
    (r"\bLPV(?:/r)?\b", "lopinavir-ritonavir"),
]
_HIV_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _HIV_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _HIV_ARM_ABBREV])

# HIV continuous outcomes; HIV-RNA (viral load) is log-normal.
_HIV_CONTINUOUS = {"CD4_COUNT", "HIV_RNA", "WEIGHT_GAIN"}
_HIV_LOGNORMAL = {"HIV_RNA"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_HIV_ENDPOINT_PATTERNS,
                                arm_compiled=_HIV_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_HIV_ENDPOINT_PATTERNS,
                               arm_compiled=_HIV_ARM_COMPILED,
                               continuous_endpoints=_HIV_CONTINUOUS,
                               lognormal_endpoints=_HIV_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_HIV_ENDPOINT_PATTERNS,
                              arm_compiled=_HIV_ARM_COMPILED,
                              continuous_endpoints=_HIV_CONTINUOUS,
                              lognormal_endpoints=_HIV_LOGNORMAL)
