"""
Arm-level / 2x2 + continuous extraction for uterine-fibroids (leiomyoma) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with uterine-fibroids
endpoints and medical / procedural arm labels:

  binary outcomes (bleeding-control responder, amenorrhoea, anaemia,
    re-intervention, hysterectomy, complications) -> 2x2 events/N per arm
  continuous (menstrual blood loss, haemoglobin, fibroid/uterine volume, UFS-QoL
    symptom-severity and QoL scores, hospital stay) -> mean/SD per arm, pooled on
    the natural scale (MD/SMD).
"""
import re
from typing import Dict, List

from .uterine_fibroids import get_uterine_fibroids_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Uterine-fibroids endpoint patterns (string, endpoint) across all subspecialties.
_UF_ENDPOINT_PATTERNS = []
for _sub in ("bleeding", "volume", "procedural", "qol"):
    _UF_ENDPOINT_PATTERNS.extend(get_uterine_fibroids_endpoint_patterns(_sub))

# Medical / procedural arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_UF_ARM_FULL = [
    # GnRH antagonists (+/- add-back)
    (r"relugolix(?:\s+combination)?", "relugolix"),
    (r"elagolix", "elagolix"),
    (r"linzagolix", "linzagolix"),
    (r"(?:gn?rh\s+agonist|leuprol(?:ide|in)|goserelin|triptorelin)", "gnrh-agonist"),
    # SPRM / antifibrinolytic / hormonal
    (r"ulipristal(?:\s+acetate)?", "ulipristal"),
    (r"tranexamic(?:\s+acid)?", "tranexamic-acid"),
    (r"levonorgestrel(?:[- ]releasing)?(?:\s+intrauterine)?|lng[- ]ius", "lng-ius"),
    (r"add[- ]back(?:\s+therapy)?", "add-back"),
    # procedural
    (r"uterine\s+artery\s+emboli[sz]ation", "uae"),
    (r"myomectomy", "myomectomy"),
    (r"hysterectomy", "hysterectomy"),
    (r"(?:mr[- ]?guided\s+)?focused\s+ultrasound|mrgfus", "focused-ultrasound"),
    (r"radiofrequency\s+ablation", "rf-ablation"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"sham\s+(?:procedure|surgery)", "sham"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_UF_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bUAE\b", "uae"),
    (r"\bMRgFUS\b|\bHIFU\b", "focused-ultrasound"),
    (r"\bRFA\b", "rf-ablation"),
    (r"\bUPA\b", "ulipristal"),
    (r"\bLNG[- ]IUS\b", "lng-ius"),
    (r"\bTXA\b", "tranexamic-acid"),
]
_UF_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _UF_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _UF_ARM_ABBREV])

# Uterine-fibroids continuous outcomes (linear scales; none log-normal).
_UF_CONTINUOUS = {"MENSTRUAL_BLOOD_LOSS", "HAEMOGLOBIN", "FIBROID_VOLUME",
                  "UTERINE_VOLUME", "SYMPTOM_SEVERITY", "HOSPITAL_STAY",
                  "QUALITY_OF_LIFE", "PELVIC_PAIN"}
_UF_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_UF_ENDPOINT_PATTERNS,
                                arm_compiled=_UF_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_UF_ENDPOINT_PATTERNS,
                               arm_compiled=_UF_ARM_COMPILED,
                               continuous_endpoints=_UF_CONTINUOUS,
                               lognormal_endpoints=_UF_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_UF_ENDPOINT_PATTERNS,
                              arm_compiled=_UF_ARM_COMPILED,
                              continuous_endpoints=_UF_CONTINUOUS,
                              lognormal_endpoints=_UF_LOGNORMAL)
