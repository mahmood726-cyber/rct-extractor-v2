"""
Arm-level / 2x2 + continuous extraction for dermatology (inflammatory skin
disease) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with dermatology
endpoints and conventional-systemic / biologic / oral-JAKi / topical arm labels:

  binary outcomes (PASI75/90/100, IGA response, EASI75/90, vIGA-AD, pruritus-NRS
    responder, acne IGA success, HiSCR) -> 2x2 events/N per arm
  continuous (PASI change, EASI change, SCORAD, lesion count) -> mean+SD /
    median+IQR. These are bounded clinical severity indices / counts, NOT
    log-normal -- the LOG-NORMAL set is empty, so nothing here is pooled on the
    log scale.

A bare effect abbreviation (HR/OR/RR) is NEVER an arm label. Generic comparators
(placebo / vehicle / standard-of-care / control / group_1/2) are included so a
drug-vs-placebo (or drug-vs-vehicle, for a topical) 2x2 pairs.
"""
import re
from typing import Dict, List

from .dermatology import get_dermatology_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Dermatology endpoint patterns (string, endpoint) across all subspecialties.
_DERM_ENDPOINT_PATTERNS = []
for _sub in ("psoriasis", "atopic_dermatitis", "acne", "hidradenitis"):
    _DERM_ENDPOINT_PATTERNS.extend(get_dermatology_endpoint_patterns(_sub))

# Conventional systemics / biologics / oral small molecules / topicals. Full names
# case-insensitive. A bare effect abbreviation (HR/OR/RR) is NEVER an arm label.
_DERM_ARM_FULL = [
    # --- Psoriasis conventional systemics + oral small molecules ---
    (r"methotrexate|\bmtx\b", "methotrexate"),
    (r"cyclosporine|cyclosporin|cic?losporin\w*|\bneoral\b|\bsandimmune\b", "cyclosporine"),
    (r"acitretin", "acitretin"),
    (r"apremilast|\botezla\b", "apremilast"),
    (r"deucravacitinib|\bsotyktu\b", "deucravacitinib"),
    # --- Psoriasis biologics (TNF, IL-12/23, IL-17, IL-23) ---
    (r"etanercept|\benbrel\b", "etanercept"),
    (r"adalimumab|\bhumira\b", "adalimumab"),
    (r"infliximab|\bremicade\b", "infliximab"),
    (r"certolizumab(?:\s+pegol)?|\bcimzia\b", "certolizumab"),
    (r"ustekinumab|\bstelara\b", "ustekinumab"),
    (r"secukinumab|\bcosentyx\b", "secukinumab"),
    (r"ixekizumab|\btaltz\b", "ixekizumab"),
    (r"brodalumab|\bsiliq\b|\blumicef\b", "brodalumab"),
    (r"bimekizumab|\bbimzelx\b", "bimekizumab"),
    (r"guselkumab|\btremfya\b", "guselkumab"),
    (r"risankizumab|\bskyrizi\b", "risankizumab"),
    (r"tildrakizumab|\bilumya\b|\bilumetri\b", "tildrakizumab"),
    # --- Atopic dermatitis biologics + oral JAK inhibitors + topical ---
    (r"dupilumab|\bdupixent\b", "dupilumab"),
    (r"tralokinumab|\badtralza\b|\badbry\b", "tralokinumab"),
    (r"lebrikizumab|\bebglyss\b", "lebrikizumab"),
    (r"upadacitinib|\brinvoq\b", "upadacitinib"),
    (r"abrocitinib|\bcibinqo\b", "abrocitinib"),
    (r"baricitinib|\bolumiant\b", "baricitinib"),
    (r"crisaborole|\beucrisa\b", "crisaborole"),
    # --- Acne systemics + topicals ---
    (r"isotretinoin|\baccutane\b|\bclaravis\b", "isotretinoin"),
    (r"doxycycline", "doxycycline"),
    (r"minocycline", "minocycline"),
    (r"adapalene", "adapalene"),
    (r"benzoyl\s+peroxide|\bbpo\b", "benzoyl-peroxide"),
    (r"clindamycin", "clindamycin"),
    (r"spironolactone|\baldactone\b", "spironolactone"),
    (r"clascoterone|\bwinlevi\b", "clascoterone"),
    # --- Generic comparators ---
    (r"\bplacebo\b", "placebo"),
    (r"\bvehicle\b", "vehicle"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|standard\s+(?:medical\s+)?(?:care|therapy)",
     "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
# No dermatology-specific uppercase-only abbreviations beyond the generic ones
# already covered case-insensitively above (MTX/BPO matched within full names).
_DERM_ARM_ABBREV = []
_DERM_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _DERM_ARM_FULL]
                      + [(re.compile(p), n) for p, n in _DERM_ARM_ABBREV])

# Dermatology continuous outcomes. PASI change, EASI change, SCORAD and lesion
# counts are bounded clinical severity indices / counts -- NOT right-skewed
# log-normal biomarkers -- so they pool as a raw-scale MD. The LOG-NORMAL set is
# deliberately EMPTY.
_DERM_CONTINUOUS = {"PASI_CHANGE", "EASI_CHANGE", "SCORAD", "LESION_COUNT"}
_DERM_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_DERM_ENDPOINT_PATTERNS,
                                arm_compiled=_DERM_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_DERM_ENDPOINT_PATTERNS,
                               arm_compiled=_DERM_ARM_COMPILED,
                               continuous_endpoints=_DERM_CONTINUOUS,
                               lognormal_endpoints=_DERM_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_DERM_ENDPOINT_PATTERNS,
                              arm_compiled=_DERM_ARM_COMPILED,
                              continuous_endpoints=_DERM_CONTINUOUS,
                              lognormal_endpoints=_DERM_LOGNORMAL)
