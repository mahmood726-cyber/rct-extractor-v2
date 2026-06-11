"""
Arm-level / 2x2 + continuous extraction for schizophrenia trials.

Thin wrapper over the shared malaria_arm_data engine configured with schizophrenia
endpoints and antipsychotic arm labels:

  binary outcomes (PANSS responder, relapse, rehospitalization, all-cause
    discontinuation, EPS/akathisia, clinically-significant weight gain, adverse
    events) -> 2x2 events/N per arm.
  continuous outcomes (PANSS total/positive/negative, CGI, cognition, weight)
    -> per-arm mean +/- SD, pooled as a mean difference.
"""
import re
from typing import Dict, List

from .schizophrenia import get_schizophrenia_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_SCZ_ENDPOINT_PATTERNS = []
for _sub in ("acute", "maintenance", "negative_cognitive", "safety"):
    _SCZ_ENDPOINT_PATTERNS.extend(get_schizophrenia_endpoint_patterns(_sub))

_SCZ_ARM_FULL = [
    (r"risperidone", "risperidone"),
    (r"paliperidone(?:\s+palmitate)?", "paliperidone"),
    (r"olanzapine", "olanzapine"),
    (r"quetiapine", "quetiapine"),
    (r"aripiprazole", "aripiprazole"),
    (r"brexpiprazole", "brexpiprazole"),
    (r"cariprazine", "cariprazine"),
    (r"lurasidone", "lurasidone"),
    (r"ziprasidone", "ziprasidone"),
    (r"asenapine", "asenapine"),
    (r"amisulpride", "amisulpride"),
    (r"clozapine", "clozapine"),
    (r"haloperidol", "haloperidol"),
    (r"xanomeline(?:[- /]trospium)?|karxt", "xanomeline-trospium"),
    (r"\bplacebo\b", "placebo"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care|treatment\s+as\s+usual", "standard-of-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"active\s+(?:treatment|comparator)", "active"),
    (r"long[- ]acting\s+injectable|\blai\b|depot", "LAI"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_SCZ_ARM_ABBREV = []
_SCZ_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _SCZ_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _SCZ_ARM_ABBREV])

_SCZ_CONTINUOUS = {"PANSS_TOTAL", "PANSS_POSITIVE", "PANSS_NEGATIVE", "CGI",
                   "COGNITION", "FUNCTIONING", "WEIGHT_GAIN"}
_SCZ_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_SCZ_ENDPOINT_PATTERNS,
                                arm_compiled=_SCZ_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_SCZ_ENDPOINT_PATTERNS,
                               arm_compiled=_SCZ_ARM_COMPILED,
                               continuous_endpoints=_SCZ_CONTINUOUS,
                               lognormal_endpoints=_SCZ_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_SCZ_ENDPOINT_PATTERNS,
                              arm_compiled=_SCZ_ARM_COMPILED,
                              continuous_endpoints=_SCZ_CONTINUOUS,
                              lognormal_endpoints=_SCZ_LOGNORMAL)
