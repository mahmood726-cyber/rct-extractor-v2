"""
Arm-level / 2x2 + continuous extraction for oncology (breast / lung / GI) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with oncology
endpoints and chemo / targeted / immuno / endocrine arm labels.

Oncology efficacy is mostly time-to-event (OS / PFS / DFS reported as a hazard
ratio, NOT a 2x2) and RESPONSE proportions (objective response rate, complete /
partial response, disease control rate). The value this module adds is therefore
the RESPONSE 2x2s: per-arm events/N on ORR / CR / PR / DCR (and PSA_RESPONSE) that
a meta-analyst pools as risk/odds ratios.

  binary RESPONSE outcomes (ORR, CR, PR, DCR, PSA response) -> 2x2 events/N per arm
  continuous outcomes are rare in oncology abstracts; ONCOLOGY_ENDPOINTS exposes
    only QOL (quality of life, a mean difference) as genuinely continuous, so the
    continuous set is minimal and there are NO log-normal continuous endpoints.

The endpoint patterns reuse oncology.get_oncology_endpoint_patterns (which emits
canonical ORR/OS/PFS/DCR codes) plus a small rate-optional RESPONSE supplement so
"objective response in 150/300" (no literal "rate") is still tagged ORR.
"""
import re
from typing import Dict, List

from .oncology import get_oncology_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Oncology endpoint patterns (string, endpoint) across the three implemented
# subspecialties. These emit canonical codes (ORR, OS, PFS, DCR, DOR, TTP) plus a
# few subspecialty-specific ones (pCR, iDFS, CBR, DRFS, CNS_PFS, CNS_TTP) that the
# engine simply carries through as the tagged endpoint.
_ONC_ENDPOINT_PATTERNS = []
for _sub in ("breast", "lung", "gi"):
    _ONC_ENDPOINT_PATTERNS.extend(get_oncology_endpoint_patterns(_sub))

# Supplementary RESPONSE patterns: the oncology.py endpoint_patterns require the
# literal word "rate" ("objective response rate"), but abstracts frequently write
# the per-arm proportion as "an objective response occurred in 150/300", so add
# rate-optional forms mapping to the canonical ORR / DCR / CR / PR response codes
# in ONCOLOGY_ENDPOINTS. (literal-token alternations, no nested quantifiers.)
_ONC_RESPONSE_SUPPLEMENT = [
    (r"objective\s+response(?:\s+rate)?|overall\s+response(?:\s+rate)?|"
     r"tumou?r\s+response|\borr\b", "ORR"),
    (r"disease\s+control(?:\s+rate)?|clinical\s+benefit(?:\s+rate)?|\bdcr\b", "DCR"),
    (r"complete\s+response|complete\s+remission|\bcr\b", "CR"),
    (r"partial\s+response", "PR"),
    (r"psa\s+response|psa\s+decline|\bpsa50\b", "PSA_RESPONSE"),
    # The only genuinely continuous oncology endpoint (mean difference); needed so
    # extract_continuous can tag a QOL mean+SD.
    (r"quality\s+of\s+life|health[- ]related\s+quality\s+of\s+life|\bhrqol\b|\bqol\b",
     "QOL"),
]
_ONC_ENDPOINT_PATTERNS = _ONC_ENDPOINT_PATTERNS + _ONC_RESPONSE_SUPPLEMENT

_J = r"[/\-+ ]"   # combo joiner in text: slash, hyphen, plus, or space
# Trastuzumab fixed-conjugate partners. Bare "trastuzumab" is suppressed when it is
# the FIRST component of one of these combos (followed by joiner+partner), so the
# combo is labelled as a unit and not fragmented into a bare "trastuzumab" arm that
# then fails to pair. Plain "trastuzumab plus pertuzumab" still matches bare (the
# suppressor requires deruxtecan/emtansine specifically, not any partner).
_TRAST_CONJUGATE = r"deruxtecan|emtansine|DXd|DM1"

# Chemo / targeted / immuno / endocrine arm labels. Full names case-insensitive;
# bare UPPERCASE abbreviations case-sensitive. Fixed antibody-drug-conjugate combos
# (trastuzumab-emtansine, trastuzumab-deruxtecan) are matched as a UNIT FIRST so a
# 2x2 arm is not fragmented into "trastuzumab" + a dangling component.
_ONC_ARM_FULL = [
    # Antibody-drug conjugates and fixed combos (match as a unit FIRST)
    (rf"trastuzumab{_J}deruxtecan|\benhertu\b", "trastuzumab-deruxtecan"),
    (rf"trastuzumab{_J}emtansine|\bkadcyla\b", "trastuzumab-emtansine"),
    # HER2 monoclonals (bare trastuzumab suppressed as the 1st combo component)
    (rf"trastuzumab(?!{_J}(?:{_TRAST_CONJUGATE}))|\bherceptin\b", "trastuzumab"),
    (r"pertuzumab|\bperjeta\b", "pertuzumab"),
    # Immune checkpoint inhibitors
    (r"pembrolizumab|\bkeytruda\b", "pembrolizumab"),
    (r"nivolumab|\bopdivo\b", "nivolumab"),
    (r"atezolizumab|\btecentriq\b", "atezolizumab"),
    (r"durvalumab|\bimfinzi\b", "durvalumab"),
    # Other targeted antibodies / TKIs
    (r"bevacizumab|\bavastin\b", "bevacizumab"),
    (r"cetuximab|\berbitux\b", "cetuximab"),
    (r"panitumumab|\bvectibix\b", "panitumumab"),
    (r"osimertinib|\btagrisso\b", "osimertinib"),
    (r"erlotinib|\btarceva\b", "erlotinib"),
    (r"gefitinib|\biressa\b", "gefitinib"),
    (r"alectinib|\balecensa\b", "alectinib"),
    (r"crizotinib|\bxalkori\b", "crizotinib"),
    (r"palbociclib|\bibrance\b", "palbociclib"),
    (r"ribociclib|\bkisqali\b", "ribociclib"),
    (r"abemaciclib|\bverzenio\b", "abemaciclib"),
    (r"olaparib|\blynparza\b", "olaparib"),
    (r"sotorasib|\blumakras\b", "sotorasib"),
    # Cytotoxic chemotherapy backbones
    (r"paclitaxel", "paclitaxel"),
    (r"docetaxel", "docetaxel"),
    (r"carboplatin", "carboplatin"),
    (r"cisplatin", "cisplatin"),
    (r"oxaliplatin", "oxaliplatin"),
    (r"capecitabine", "capecitabine"),
    (r"fluorouracil|\b5[- ]?fu\b", "fluorouracil"),
    (r"gemcitabine", "gemcitabine"),
    (r"pemetrexed", "pemetrexed"),
    (r"doxorubicin", "doxorubicin"),
    (r"cyclophosphamide", "cyclophosphamide"),
    # Endocrine therapy
    (r"letrozole", "letrozole"),
    (r"anastrozole", "anastrozole"),
    (r"tamoxifen", "tamoxifen"),
    (r"fulvestrant", "fulvestrant"),
    # Generic / control arms
    (r"\bplacebo\b", "placebo"),
    (r"best\s+supportive\s+care", "best-supportive-care"),
    (r"standard[- ]of[- ]care|standard\s+(?:of\s+)?care|standard\s+chemotherapy|"
     r"\bchemotherapy\b|usual\s+care", "standard-of-care"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_ONC_ARM_ABBREV = [   # case-sensitive uppercase combo/agent abbreviations
    (rf"\bT{_J}DXd\b", "trastuzumab-deruxtecan"),
    (rf"\bT{_J}DM1\b", "trastuzumab-emtansine"),
    (r"\bBSC\b", "best-supportive-care"),
    (r"\bSOC\b", "standard-of-care"),
]
_ONC_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _ONC_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _ONC_ARM_ABBREV])

# Continuous outcomes. Oncology efficacy is overwhelmingly time-to-event (HR) or
# response (proportions); ONCOLOGY_ENDPOINTS exposes only QOL (quality of life) as
# a genuinely continuous mean-difference endpoint, so the continuous set is minimal
# and there are NO log-normal continuous endpoints.
_ONC_CONTINUOUS = {"QOL"}
_ONC_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_ONC_ENDPOINT_PATTERNS,
                                arm_compiled=_ONC_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_ONC_ENDPOINT_PATTERNS,
                               arm_compiled=_ONC_ARM_COMPILED,
                               continuous_endpoints=_ONC_CONTINUOUS,
                               lognormal_endpoints=_ONC_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_ONC_ENDPOINT_PATTERNS,
                              arm_compiled=_ONC_ARM_COMPILED,
                              continuous_endpoints=_ONC_CONTINUOUS,
                              lognormal_endpoints=_ONC_LOGNORMAL)
