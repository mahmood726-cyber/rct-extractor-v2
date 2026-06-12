"""
Arm-level / 2x2 + continuous extraction for testicular cancer (germ cell) trials.
Thin wrapper over the shared malaria_arm_data engine, configured with testicular
cancer endpoints and platinum-chemotherapy / surveillance / radiotherapy arm
labels. Endpoints are time-to-event or binary (relapse, favourable response);
no continuous outcome configured.
"""
import re
from typing import Dict, List

from .testicular_cancer import get_testicular_cancer_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_TG_ENDPOINT_PATTERNS = []
for _sub in ("seminoma", "nonseminoma", "advanced", "mortality"):
    _TG_ENDPOINT_PATTERNS.extend(get_testicular_cancer_endpoint_patterns(_sub))

_TG_ARM_FULL = [
    (r"bleomycin[, /-]+etoposide[, /-]+cisplatin|\bbep\b", "bep"),
    (r"etoposide[, /-]+ifosfamide[, /-]+cisplatin|\bvip\b", "vip"),
    (r"paclitaxel[, /-]+ifosfamide[, /-]+cisplatin|\btip\b", "tip"),
    (r"etoposide[, /-]+cisplatin|\bep\b(?![a-z])", "ep"),
    (r"single[- ]agent\s+carboplatin|adjuvant\s+carboplatin|carboplatin", "carboplatin"),
    (r"high[- ]dose\s+chemotherapy|hdct", "high-dose-chemo"),
    (r"para[- ]aortic\s+(?:radiotherapy|irradiation)|radiotherapy|radiation\s+therapy",
     "radiotherapy"),
    (r"retroperitoneal\s+lymph[- ]node\s+dissection|\brplnd\b", "rplnd"),
    (r"surveillance|active\s+monitoring", "surveillance"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|standard\s+(?:chemo)?therapy", "standard-of-care"),
    (r"observation", "observation"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_TG_ARM_ABBREV = [
    (r"\bBEP\b", "bep"),
    (r"\bVIP\b", "vip"),
    (r"\bTIP\b", "tip"),
    (r"\bRPLND\b", "rplnd"),
]
_TG_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _TG_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _TG_ARM_ABBREV])

_TG_CONTINUOUS = set()
_TG_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_TG_ENDPOINT_PATTERNS,
                                arm_compiled=_TG_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_TG_ENDPOINT_PATTERNS,
                               arm_compiled=_TG_ARM_COMPILED,
                               continuous_endpoints=_TG_CONTINUOUS,
                               lognormal_endpoints=_TG_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_TG_ENDPOINT_PATTERNS,
                              arm_compiled=_TG_ARM_COMPILED,
                              continuous_endpoints=_TG_CONTINUOUS,
                              lognormal_endpoints=_TG_LOGNORMAL)
