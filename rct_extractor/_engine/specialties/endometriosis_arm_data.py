"""
Arm-level / 2x2 + continuous extraction for endometriosis trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with endometriosis
endpoints and hormonal / surgical arm labels:

  binary outcomes (recurrence, responder, amenorrhoea, hot flushes, clinical
    pregnancy, live birth, miscarriage, reoperation) -> 2x2 events/N per arm
  continuous (pain VAS/NRS, dysmenorrhoea, dyspareunia, BMD, EHP-30 quality of
    life, lesion size) -> mean/SD per arm, pooled on the natural scale (MD/SMD).
"""
import re
from typing import Dict, List

from .endometriosis import get_endometriosis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Endometriosis endpoint patterns (string, endpoint) across all subspecialties.
_ENDO_ENDPOINT_PATTERNS = []
for _sub in ("pain", "medical", "surgical", "fertility"):
    _ENDO_ENDPOINT_PATTERNS.extend(get_endometriosis_endpoint_patterns(_sub))

# Hormonal / surgical arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_ENDO_ARM_FULL = [
    # GnRH antagonists
    (r"elagolix", "elagolix"),
    (r"relugolix(?:\s+combination)?", "relugolix"),
    (r"linzagolix", "linzagolix"),
    # GnRH agonists
    (r"leuprol(?:ide|in)|leuprorelin", "leuprolide"),
    (r"goserelin", "goserelin"),
    (r"triptorelin", "triptorelin"),
    (r"nafarelin", "nafarelin"),
    # progestins / other hormonal
    (r"dienogest", "dienogest"),
    (r"medroxyprogesterone|\bdmpa\b|depot[- ]medroxyprogesterone", "medroxyprogesterone"),
    (r"norethindrone|norethisterone", "norethindrone"),
    (r"combined\s+oral\s+contraceptive|oral\s+contraceptive", "oral-contraceptive"),
    (r"danazol", "danazol"),
    (r"letrozole", "letrozole"),
    (r"anastrozole", "anastrozole"),
    (r"add[- ]back(?:\s+therapy)?", "add-back"),
    # surgical arms
    (r"laparoscopic\s+excision|excisional\s+surgery|excision", "excision"),
    (r"ablation|coagulation|fulguration", "ablation"),
    (r"cystectomy", "cystectomy"),
    (r"drainage(?:\s+and\s+(?:coagulation|ablation))?", "drainage"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"sham\s+(?:surgery|procedure)", "sham"),
    (r"expectant\s+management|no\s+treatment|observation", "expectant"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_ENDO_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bGnRH\b", "gnrh-analog"),
    (r"\bCOC\b", "oral-contraceptive"),
    (r"\bDMPA\b", "medroxyprogesterone"),
]
_ENDO_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _ENDO_ARM_FULL]
                      + [(re.compile(p), n) for p, n in _ENDO_ARM_ABBREV])

# Endometriosis continuous outcomes (linear scales; none log-normal).
_ENDO_CONTINUOUS = {"PELVIC_PAIN", "DYSMENORRHOEA", "DYSPAREUNIA", "DYSCHEZIA",
                    "BMD_LOSS", "LESION_REDUCTION", "QUALITY_OF_LIFE"}
_ENDO_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_ENDO_ENDPOINT_PATTERNS,
                                arm_compiled=_ENDO_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_ENDO_ENDPOINT_PATTERNS,
                               arm_compiled=_ENDO_ARM_COMPILED,
                               continuous_endpoints=_ENDO_CONTINUOUS,
                               lognormal_endpoints=_ENDO_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_ENDO_ENDPOINT_PATTERNS,
                              arm_compiled=_ENDO_ARM_COMPILED,
                              continuous_endpoints=_ENDO_CONTINUOUS,
                              lognormal_endpoints=_ENDO_LOGNORMAL)
