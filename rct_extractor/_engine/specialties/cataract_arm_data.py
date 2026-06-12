"""
Arm-level / 2x2 + continuous extraction for cataract / lens-surgery trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with cataract
endpoints and IOL-type / surgical-technique / peri-operative-drug arm labels:

  binary outcomes (spectacle independence, posterior-capsule opacification,
    Nd:YAG capsulotomy, cystoid macular o?edema, endophthalmitis, dysphotopsia)
    -> 2x2 events/N per arm
  continuous (CDVA/UDVA in logMAR or letters, surgically induced astigmatism in
    dioptres, endothelial cell loss in cells/mm^2, corneal/macular thickness in
    microns) -> mean+SD / median+IQR. NONE of the cataract continuous measures
    is log-normal -- all pooled on the raw scale.

A bare effect abbreviation (HR/OR/RR) is NEVER an arm label.
"""
import re
from typing import Dict, List

from .cataract import get_cataract_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Cataract endpoint patterns (string, endpoint) across all subspecialties.
_CAT_ENDPOINT_PATTERNS = []
for _sub in ("surgery", "iol", "pco", "complications"):
    _CAT_ENDPOINT_PATTERNS.extend(get_cataract_endpoint_patterns(_sub))

# Surgical-technique / IOL-type / peri-operative-drug arm labels. Full names
# case-insensitive. Generic comparators included so a technique-vs-technique or
# lens-vs-lens 2x2 pairs. NO bare effect abbreviation (HR/OR/RR) is a label.
_CAT_ARM_FULL = [
    # Surgical technique
    (r"femtosecond\s+laser[- ]assisted\s+cataract\s+surgery|femtosecond\s+laser|\bflacs\b",
     "flacs"),
    (r"phacoemulsification|\bphaco\b", "phacoemulsification"),
    (r"manual\s+small[- ]incision\s+cataract\s+surgery|\bmsics\b|\bsics\b",
     "manual-sics"),
    # IOL types
    (r"monofocal(?:\s+iol)?", "monofocal-iol"),
    (r"trifocal(?:\s+iol)?", "trifocal-iol"),
    (r"multifocal(?:\s+iol)?", "multifocal-iol"),
    (r"extended\s+depth\s+of\s+focus(?:\s+iol)?|\bedof\b|\bedf\b", "edof-iol"),
    (r"toric(?:\s+iol)?", "toric-iol"),
    (r"accommodating\s+(?:iol|lens)", "accommodating-iol"),
    # IOL material (canonical PCO comparison)
    (r"hydrophobic(?:\s+acrylic)?(?:\s+iol)?", "hydrophobic-iol"),
    (r"hydrophilic(?:\s+acrylic)?(?:\s+iol)?", "hydrophilic-iol"),
    # Peri-operative drugs
    (r"intracameral\s+cefuroxime|cefuroxime", "cefuroxime"),
    (r"intracameral\s+moxifloxacin|moxifloxacin", "moxifloxacin"),
    (r"nepafenac", "nepafenac"),
    (r"ketorolac", "ketorolac"),
    (r"bromfenac", "bromfenac"),
    (r"prednisolone(?:\s+acetate)?", "prednisolone"),
    (r"dexamethasone", "dexamethasone"),
    # Generic comparators
    (r"\bplacebo\b", "placebo"),
    (r"\bsham(?:\s+(?:injection|procedure|treatment))?\b", "sham"),
    (r"\bvehicle\b", "vehicle"),
    (r"conventional(?:\s+(?:surgery|phacoemulsification))?", "conventional"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|standard\s+(?:medical\s+)?(?:care|therapy)",
     "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
# Case-SENSITIVE uppercase abbreviations. Deliberately exclude any token that
# collides with a bare effect abbreviation (HR/OR/RR) or a measure.
_CAT_ARM_ABBREV = [
    (r"\bFLACS\b", "flacs"),
    (r"\bMSICS\b", "manual-sics"),
    (r"\bEDOF\b", "edof-iol"),
]
_CAT_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _CAT_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _CAT_ARM_ABBREV])

# Cataract continuous outcomes. NONE are log-normal: CDVA/UDVA (logMAR/letters),
# SIA (dioptres), endothelial cell loss (cells/mm^2) and corneal/macular
# thickness (microns) are pooled on the raw scale.
_CAT_CONTINUOUS = {"CDVA_CHANGE", "SIA", "ENDOTHELIAL_CELL_LOSS", "CCT_CHANGE",
                   "UDVA_CHANGE", "CMT_CHANGE"}
_CAT_LOGNORMAL = set()   # empty: no log-normal cataract endpoints


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_CAT_ENDPOINT_PATTERNS,
                                arm_compiled=_CAT_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_CAT_ENDPOINT_PATTERNS,
                               arm_compiled=_CAT_ARM_COMPILED,
                               continuous_endpoints=_CAT_CONTINUOUS,
                               lognormal_endpoints=_CAT_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_CAT_ENDPOINT_PATTERNS,
                              arm_compiled=_CAT_ARM_COMPILED,
                              continuous_endpoints=_CAT_CONTINUOUS,
                              lognormal_endpoints=_CAT_LOGNORMAL)
