"""
Arm-level / 2x2 + continuous extraction for COVID-19 trials.

Thin wrapper over the shared malaria_arm_data engine configured with COVID-19
endpoints and arm labels:

  binary outcomes (hospitalization or death, mortality, progression to mechanical
    ventilation, symptomatic infection, adverse events) -> 2x2 events/N per arm.
  continuous outcomes (viral load change) -> per-arm mean +/- SD; recovery is a
    time-to-event pooled as a hazard ratio by the core engine.
"""
import re
from typing import Dict, List

from .covid19 import get_covid19_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_COV_ENDPOINT_PATTERNS = []
for _sub in ("antiviral", "immunomodulator", "prophylaxis_vaccine", "severe_supportive"):
    _COV_ENDPOINT_PATTERNS.extend(get_covid19_endpoint_patterns(_sub))

_COV_ARM_FULL = [
    (r"nirmatrelvir(?:[- /]ritonavir)?|paxlovid", "nirmatrelvir-ritonavir"),
    (r"molnupiravir", "molnupiravir"),
    (r"remdesivir", "remdesivir"),
    (r"ensitrelvir", "ensitrelvir"),
    (r"fluvoxamine", "fluvoxamine"),
    (r"dexamethasone", "dexamethasone"),
    (r"hydrocortisone", "hydrocortisone"),
    (r"methylprednisolone", "methylprednisolone"),
    (r"tocilizumab", "tocilizumab"),
    (r"sarilumab", "sarilumab"),
    (r"baricitinib", "baricitinib"),
    (r"anakinra", "anakinra"),
    (r"casirivimab(?:[- /]imdevimab)?", "casirivimab-imdevimab"),
    (r"sotrovimab", "sotrovimab"),
    (r"tixagevimab(?:[- /]cilgavimab)?|evusheld", "tixagevimab-cilgavimab"),
    (r"convalescent\s+plasma", "convalescent-plasma"),
    (r"heparin|enoxaparin", "heparin"),
    (r"\bplacebo\b", "placebo"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care|standard\s+care", "standard-of-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"active\s+(?:treatment|comparator)", "active"),
    (r"\bvaccine\b|vaccinated", "vaccine"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_COV_ARM_ABBREV = [
    (r"\bSOC\b", "standard-of-care"),
]
_COV_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _COV_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _COV_ARM_ABBREV])

_COV_CONTINUOUS = {"VIRAL_CLEARANCE"}
_COV_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_COV_ENDPOINT_PATTERNS,
                                arm_compiled=_COV_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_COV_ENDPOINT_PATTERNS,
                               arm_compiled=_COV_ARM_COMPILED,
                               continuous_endpoints=_COV_CONTINUOUS,
                               lognormal_endpoints=_COV_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_COV_ENDPOINT_PATTERNS,
                              arm_compiled=_COV_ARM_COMPILED,
                              continuous_endpoints=_COV_CONTINUOUS,
                              lognormal_endpoints=_COV_LOGNORMAL)
