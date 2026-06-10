"""
Arm-level / 2x2 + continuous extraction for rheumatology (inflammatory arthritis
/ connective-tissue disease) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with rheumatology
endpoints and csDMARD / TNFi / JAKi / IL-17 / IL-23 / IL-6 / costimulation /
B-cell / urate-lowering / lupus-biologic arm labels:

  binary composite responses (ACR20/50/70, DAS28 remission, MDA, PASI response,
    ASAS20/40, gout flare, urate target, SRI-4, BICLA, SLE flare) -> 2x2
    events/N per arm
  continuous indices (DAS28 change, HAQ-DI, modified total Sharp score, BASDAI
    change, ASDAS change, SLEDAI change, serum urate) -> mean+SD / median+IQR.
    None of these scales are log-normal (bounded clinical indices / mg-dL urate),
    so the log-normal set is EMPTY. (CRP would be log-normal but is not an
    endpoint here.)
"""
import re
from typing import Dict, List

from .rheumatology import get_rheumatology_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Rheumatology endpoint patterns (string, endpoint) across all subspecialties.
_RHEUM_ENDPOINT_PATTERNS = []
for _sub in ("ra", "psa", "axspa", "gout", "sle"):
    _RHEUM_ENDPOINT_PATTERNS.extend(get_rheumatology_endpoint_patterns(_sub))

_J = r"[/\-+ ]"   # combo joiner in text: slash, hyphen, plus, or space

# Drug / arm labels. Full names case-insensitive; bare UPPERCASE abbreviations
# CASE-SENSITIVE so a bare effect abbreviation (HR/OR/RR) is NEVER an arm label
# and tokens like "MTX" only match the uppercase form. Combination csDMARD
# regimens are not matched as a unit (each component is its own arm label).
_RHEUM_ARM_FULL = [
    # csDMARDs
    (r"methotrexate", "methotrexate"),
    (r"sulfasalazine", "sulfasalazine"),
    (r"leflunomide", "leflunomide"),
    (r"hydroxychloroquine", "hydroxychloroquine"),
    # TNF inhibitors
    (r"adalimumab|\bhumira\b", "adalimumab"),
    (r"etanercept|\benbrel\b", "etanercept"),
    (r"infliximab|\bremicade\b", "infliximab"),
    (r"golimumab|\bsimponi\b", "golimumab"),
    (r"certolizumab(?:\s+pegol)?|\bcimzia\b", "certolizumab"),
    # JAK inhibitors
    (r"tofacitinib|\bxeljanz\b", "tofacitinib"),
    (r"baricitinib|\bolumiant\b", "baricitinib"),
    (r"upadacitinib|\brinvoq\b", "upadacitinib"),
    (r"filgotinib|\bjyseleca\b", "filgotinib"),
    # IL-6 receptor / costimulation / B-cell
    (r"tocilizumab|\bactemra\b|\broactemra\b", "tocilizumab"),
    (r"sarilumab|\bkevzara\b", "sarilumab"),
    (r"abatacept|\borencia\b", "abatacept"),
    (r"rituximab|\bmabthera\b|\brituxan\b", "rituximab"),
    # IL-17 inhibitors
    (r"secukinumab|\bcosentyx\b", "secukinumab"),
    (r"ixekizumab|\btaltz\b", "ixekizumab"),
    (r"bimekizumab|\bbimzelx\b", "bimekizumab"),
    # IL-23 / IL-12-23 inhibitors
    (r"ustekinumab|\bstelara\b", "ustekinumab"),
    (r"guselkumab|\btremfya\b", "guselkumab"),
    (r"risankizumab|\bskyrizi\b", "risankizumab"),
    # Lupus biologics
    (r"belimumab|\bbenlysta\b", "belimumab"),
    (r"anifrolumab|\bsaphnelo\b", "anifrolumab"),
    # Urate-lowering / gout agents
    (r"allopurinol", "allopurinol"),
    (r"febuxostat|\buloric\b|\badenuric\b", "febuxostat"),
    (r"colchicine", "colchicine"),
    (r"pegloticase|\bkrystexxa\b", "pegloticase"),
    # Glucocorticoid
    (r"prednisone|prednisolone|glucocorticoid|cortico?steroid", "glucocorticoid"),
    # Generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|background\s+(?:therapy|dmard)", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_RHEUM_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bMTX\b", "methotrexate"),
    (r"\bSSZ\b", "sulfasalazine"),
    (r"\bLEF\b", "leflunomide"),
    (r"\bHCQ\b", "hydroxychloroquine"),
    (r"\bADA\b", "adalimumab"),
    (r"\bETN\b", "etanercept"),
    (r"\bIFX\b", "infliximab"),
    (r"\bGOL\b", "golimumab"),
    (r"\bCZP\b", "certolizumab"),
    (r"\bTOFA\b", "tofacitinib"),
    (r"\bBARI\b", "baricitinib"),
    (r"\bUPA\b", "upadacitinib"),
    (r"\bTCZ\b", "tocilizumab"),
    (r"\bRTX\b", "rituximab"),
]
_RHEUM_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _RHEUM_ARM_FULL]
                       + [(re.compile(p), n) for p, n in _RHEUM_ARM_ABBREV])

# Rheumatology continuous outcomes are bounded clinical disease-activity /
# function / structural indices (DAS28 0-9.4, HAQ-DI 0-3, mTSS, BASDAI 0-10,
# ASDAS, SLEDAI 0-105) plus serum urate (mg/dL) -- NONE are log-normal, so no
# log-scale pooling. lognormal set intentionally empty. (CRP would be log-normal
# but is not an endpoint in this profile.)
_RHEUM_CONTINUOUS = {"DAS28_CHANGE", "HAQ_DI", "RADIOGRAPHIC_PROGRESSION",
                     "BASDAI_CHANGE", "ASDAS_CHANGE", "SLEDAI_CHANGE", "SERUM_URATE"}
_RHEUM_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_RHEUM_ENDPOINT_PATTERNS,
                                arm_compiled=_RHEUM_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_RHEUM_ENDPOINT_PATTERNS,
                               arm_compiled=_RHEUM_ARM_COMPILED,
                               continuous_endpoints=_RHEUM_CONTINUOUS,
                               lognormal_endpoints=_RHEUM_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_RHEUM_ENDPOINT_PATTERNS,
                              arm_compiled=_RHEUM_ARM_COMPILED,
                              continuous_endpoints=_RHEUM_CONTINUOUS,
                              lognormal_endpoints=_RHEUM_LOGNORMAL)
