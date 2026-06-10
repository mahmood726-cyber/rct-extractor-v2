"""
Arm-level / 2x2 + continuous extraction for ophthalmology (eye) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with ophthalmology
endpoints and anti-VEGF / complement / steroid / glaucoma-drop / dry-eye arm
labels:

  binary outcomes (>=15-letter vision gain, avoidance of <15-letter loss, target
    IOP, >=2-step diabetic-retinopathy improvement, visual-field progression)
    -> 2x2 events/N per arm
  continuous (BCVA change in ETDRS letters, central retinal/subfield thickness,
    IOP change in mmHg, OSDI, corneal staining, Schirmer) -> mean+SD / median+IQR.
    NONE of the ophthalmology continuous measures are log-normal -- letters,
    microns, mmHg and the bounded dry-eye scores are pooled on the raw scale.

A bare effect abbreviation (HR/OR/RR) is NEVER an arm label.
"""
import re
from typing import Dict, List

from .ophthalmology import get_ophthalmology_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Ophthalmology endpoint patterns (string, endpoint) across all subspecialties.
_OPHTH_ENDPOINT_PATTERNS = []
for _sub in ("amd", "dme", "glaucoma", "dry_eye"):
    _OPHTH_ENDPOINT_PATTERNS.extend(get_ophthalmology_endpoint_patterns(_sub))

# Anti-VEGF / complement / steroid / glaucoma-drop / dry-eye arm labels. Full
# names case-insensitive. Generic comparators (placebo / sham / vehicle /
# standard-of-care / control) included so a drug-vs-comparator 2x2 pairs. NO bare
# effect abbreviation (HR/OR/RR) is used as a label.
_OPHTH_ARM_FULL = [
    # Anti-VEGF
    (r"ranibizumab|\blucentis\b", "ranibizumab"),
    (r"aflibercept|\beylea\b", "aflibercept"),
    (r"bevacizumab|\bavastin\b", "bevacizumab"),
    (r"brolucizumab|\bbeovu\b", "brolucizumab"),
    (r"faricimab|\bvabysmo\b", "faricimab"),
    # Complement inhibitors (geographic atrophy)
    (r"pegcetacoplan|\bsyfovre\b", "pegcetacoplan"),
    (r"avacincaptad(?:\s+pegol)?|\bizervay\b", "avacincaptad"),
    # Steroids (intravitreal)
    (r"dexamethasone(?:\s+(?:intravitreal\s+)?implant)?|\bozurdex\b", "dexamethasone-implant"),
    (r"triamcinolone(?:\s+acetonide)?", "triamcinolone"),
    # Glaucoma drops
    (r"latanoprost|\bxalatan\b", "latanoprost"),
    (r"bimatoprost|\blumigan\b", "bimatoprost"),
    (r"travoprost|\btravatan\b", "travoprost"),
    (r"timolol", "timolol"),
    (r"brinzolamide|\bazopt\b", "brinzolamide"),
    (r"dorzolamide|\btrusopt\b", "dorzolamide"),
    (r"brimonidine|\balphagan\b", "brimonidine"),
    (r"netarsudil|\brhopressa\b", "netarsudil"),
    # Dry eye
    (r"cyclosporine|cyclosporin|cic?losporin\w*|\brestasis\b|\bcequa\b|\bikervis\b", "cyclosporine"),
    (r"lifitegrast|\bxiidra\b", "lifitegrast"),
    (r"varenicline\s+nasal(?:\s+spray)?|\btyrvaya\b", "varenicline-nasal"),
    # Generic comparators
    (r"\bplacebo\b", "placebo"),
    (r"\bsham(?:\s+(?:injection|procedure|treatment))?\b", "sham"),
    (r"\bvehicle\b", "vehicle"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|standard\s+(?:medical\s+)?(?:care|therapy)",
     "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
# Case-SENSITIVE uppercase abbreviations. Deliberately exclude any token that
# collides with a bare effect abbreviation (HR/OR/RR) or a measure.
_OPHTH_ARM_ABBREV = [
    (r"\bIVT[- ]?TA\b", "triamcinolone"),
    (r"\bDEX\b", "dexamethasone-implant"),
]
_OPHTH_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _OPHTH_ARM_FULL]
                       + [(re.compile(p), n) for p, n in _OPHTH_ARM_ABBREV])

# Ophthalmology continuous outcomes. NONE are log-normal: BCVA (ETDRS letters),
# CRT/CST (microns), IOP (mmHg) and the bounded dry-eye scales (OSDI, corneal
# staining, Schirmer) are pooled on the raw scale.
_OPHTH_CONTINUOUS = {"BCVA_CHANGE", "CRT_CHANGE", "IOP_CHANGE",
                     "OSDI_CHANGE", "CORNEAL_STAINING", "SCHIRMER"}
_OPHTH_LOGNORMAL = set()   # empty: no log-normal ophthalmology endpoints


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_OPHTH_ENDPOINT_PATTERNS,
                                arm_compiled=_OPHTH_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_OPHTH_ENDPOINT_PATTERNS,
                               arm_compiled=_OPHTH_ARM_COMPILED,
                               continuous_endpoints=_OPHTH_CONTINUOUS,
                               lognormal_endpoints=_OPHTH_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_OPHTH_ENDPOINT_PATTERNS,
                              arm_compiled=_OPHTH_ARM_COMPILED,
                              continuous_endpoints=_OPHTH_CONTINUOUS,
                              lognormal_endpoints=_OPHTH_LOGNORMAL)
