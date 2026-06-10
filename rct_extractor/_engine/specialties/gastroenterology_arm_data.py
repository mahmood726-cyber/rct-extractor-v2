"""
Arm-level / 2x2 + continuous extraction for gastroenterology trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with
gastroenterology endpoints and IBD / H. pylori / GERD-PPI / MASH arm labels:

  binary outcomes (clinical remission, clinical response, endoscopic remission /
    mucosal healing, steroid-free remission, H. pylori eradication, erosive-
    oesophagitis healing, heartburn-free, NASH/MASH resolution, fibrosis
    improvement) -> 2x2 events/N per arm
  continuous (CDAI change, Mayo score, MRI-PDFF liver fat) -> mean+SD /
    median+IQR. None of the gastroenterology continuous endpoints are log-normal
    (CDAI / Mayo are bounded clinical indices; MRI-PDFF liver fat is a percentage
    pooled on the raw scale), so the LOG-NORMAL set is intentionally EMPTY.
"""
import re
from typing import Dict, List

from .gastroenterology import get_gastroenterology_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Gastroenterology endpoint patterns (string, endpoint) across all subspecialties.
_GI_ENDPOINT_PATTERNS = []
for _sub in ("ibd", "hpylori", "gerd", "mash"):
    _GI_ENDPOINT_PATTERNS.extend(get_gastroenterology_endpoint_patterns(_sub))

# IBD biologics / small molecules, H. pylori antibiotics + PPIs, MASH agents, and
# generic comparators. Full names case-insensitive; a bare effect abbreviation
# (HR/OR/RR) is NEVER an arm label. Bismuth quadruple-therapy components are
# matched simply as their individual drug labels (no combo collapsing).
_GI_ARM_FULL = [
    # --- IBD: aminosalicylates / immunomodulators ---
    (r"mesalamine|mesalazine|5[- ]?asa|5[- ]aminosalicylic\s+acid", "mesalamine"),
    (r"sulfasalazine|sulphasalazine", "sulfasalazine"),
    (r"azathioprine", "azathioprine"),
    (r"methotrexate", "methotrexate"),
    # --- IBD: anti-TNF / anti-integrin / anti-IL / JAK / S1P ---
    (r"infliximab|\bremicade\b", "infliximab"),
    (r"adalimumab|\bhumira\b", "adalimumab"),
    (r"golimumab|\bsimponi\b", "golimumab"),
    (r"certolizumab(?:\s+pegol)?|\bcimzia\b", "certolizumab"),
    (r"vedolizumab|\bentyvio\b", "vedolizumab"),
    (r"ustekinumab|\bstelara\b", "ustekinumab"),
    (r"risankizumab|\bskyrizi\b", "risankizumab"),
    (r"mirikizumab|\bomvoh\b", "mirikizumab"),
    (r"tofacitinib|\bxeljanz\b", "tofacitinib"),
    (r"upadacitinib|\brinvoq\b", "upadacitinib"),
    (r"filgotinib|\bjyseleca\b", "filgotinib"),
    (r"ozanimod|\bzeposia\b", "ozanimod"),
    (r"etrasimod|\bvelsipity\b", "etrasimod"),
    # --- H. pylori antibiotics + bismuth ---
    (r"amoxicillin", "amoxicillin"),
    (r"clarithromycin", "clarithromycin"),
    (r"metronidazole", "metronidazole"),
    (r"tetracycline", "tetracycline"),
    (r"bismuth(?:\s+(?:subcitrate|subsalicylate))?", "bismuth"),
    # --- PPIs (H. pylori regimens + GERD) and PCAB ---
    (r"omeprazole", "omeprazole"),
    (r"esomeprazole|\bnexium\b", "esomeprazole"),
    (r"lansoprazole", "lansoprazole"),
    (r"pantoprazole", "pantoprazole"),
    (r"rabeprazole", "rabeprazole"),
    (r"vonoprazan|\bvoquezna\b", "vonoprazan"),
    # --- MASH ---
    (r"resmetirom|\brezdiffra\b", "resmetirom"),
    (r"semaglutide|\bwegovy\b|\bozempic\b", "semaglutide"),
    (r"obeticholic\s+acid|\bocaliva\b", "obeticholic-acid"),
    (r"pioglitazone", "pioglitazone"),
    # --- Generic comparators ---
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|standard\s+(?:medical\s+)?(?:care|therapy)|"
     r"best\s+supportive\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_GI_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\b5[- ]?ASA\b", "mesalamine"),
    (r"\bMTX\b", "methotrexate"),
    (r"\bAZA\b", "azathioprine"),
    (r"\bIFX\b", "infliximab"),
    (r"\bADA\b", "adalimumab"),
    (r"\bUST\b", "ustekinumab"),
    (r"\bVDZ\b", "vedolizumab"),
    (r"\bOCA\b", "obeticholic-acid"),
]
_GI_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _GI_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _GI_ARM_ABBREV])

# Gastroenterology continuous outcomes. CDAI and Mayo score are bounded clinical
# activity indices; MRI-PDFF liver fat is a percentage. None are right-skewed in a
# way that mandates log-scale pooling, so LOG-NORMAL is EMPTY (raw-scale MD).
_GI_CONTINUOUS = {"CDAI_CHANGE", "MAYO_SCORE", "LIVER_FAT", "HEARTBURN_FREE"}
_GI_LOGNORMAL = set()   # intentionally empty -- no log-normal GI continuous endpoint


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_GI_ENDPOINT_PATTERNS,
                                arm_compiled=_GI_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_GI_ENDPOINT_PATTERNS,
                               arm_compiled=_GI_ARM_COMPILED,
                               continuous_endpoints=_GI_CONTINUOUS,
                               lognormal_endpoints=_GI_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_GI_ENDPOINT_PATTERNS,
                              arm_compiled=_GI_ARM_COMPILED,
                              continuous_endpoints=_GI_CONTINUOUS,
                              lognormal_endpoints=_GI_LOGNORMAL)
