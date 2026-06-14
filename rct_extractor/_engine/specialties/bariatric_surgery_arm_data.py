"""
Arm-level / 2x2 + continuous extraction for bariatric / metabolic surgery trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
bariatric-surgery endpoints and bariatric-procedure arm labels:

  binary (diabetes / hypertension / dyslipidaemia remission, postoperative
    complication, anastomotic leak, reoperation, mortality, nutritional
    deficiency, anaemia) -> 2x2 events/N per arm.
  continuous (%TWL, %EWL, BMI, HbA1c) -> mean+SD / median+IQR, pooled as MD/SMD
    on the natural scale.
"""
import re
from typing import Dict, List

from .bariatric_surgery import get_bariatric_surgery_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_BS_ENDPOINT_PATTERNS = []
for _sub in ("weight", "metabolic", "complications", "nutritional"):
    _BS_ENDPOINT_PATTERNS.extend(get_bariatric_surgery_endpoint_patterns(_sub))

# Bariatric-procedure arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE.
_BS_ARM_FULL = [
    (r"roux[- ]en[- ]y\s+gastric\s+bypass|roux[- ]en[- ]y|gastric\s+bypass", "gastric-bypass"),
    (r"(?:laparoscopic\s+)?sleeve\s+gastrectomy|vertical\s+sleeve\s+gastrectomy", "sleeve-gastrectomy"),
    (r"one[- ]anastomosis\s+gastric\s+bypass|mini[- ]gastric\s+bypass", "oagb"),
    (r"(?:laparoscopic\s+)?adjustable\s+gastric\s+band(?:ing)?|gastric\s+band(?:ing)?", "gastric-banding"),
    (r"biliopancreatic\s+diversion(?:\s+with\s+duodenal\s+switch)?|duodenal\s+switch", "bpd-ds"),
    (r"intragastric\s+balloon|gastric\s+balloon", "intragastric-balloon"),
    (r"medical\s+(?:therapy|treatment|management)|intensive\s+medical\s+therapy|lifestyle\s+(?:intervention|modification)",
     "medical-therapy"),
    # comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|conventional\s+(?:therapy|treatment)", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_BS_ARM_ABBREV = [
    (r"\bRYGB\b", "gastric-bypass"),
    (r"\bLSG\b|\bSG\b|\bVSG\b", "sleeve-gastrectomy"),
    (r"\bOAGB\b|\bMGB\b", "oagb"),
    (r"\bLAGB\b|\bAGB\b", "gastric-banding"),
    (r"\bBPD\b|\bBPD/DS\b", "bpd-ds"),
]
_BS_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _BS_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _BS_ARM_ABBREV])

# Bariatric-surgery continuous outcomes (natural scale).
_BS_CONTINUOUS = {"TOTAL_WEIGHT_LOSS", "EXCESS_WEIGHT_LOSS", "BMI_CHANGE", "HBA1C"}
_BS_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_BS_ENDPOINT_PATTERNS,
                                arm_compiled=_BS_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_BS_ENDPOINT_PATTERNS,
                               arm_compiled=_BS_ARM_COMPILED,
                               continuous_endpoints=_BS_CONTINUOUS,
                               lognormal_endpoints=_BS_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_BS_ENDPOINT_PATTERNS,
                              arm_compiled=_BS_ARM_COMPILED,
                              continuous_endpoints=_BS_CONTINUOUS,
                              lognormal_endpoints=_BS_LOGNORMAL)
