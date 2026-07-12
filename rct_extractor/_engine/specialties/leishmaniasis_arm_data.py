"""
Arm-level / 2x2 + continuous extraction for leishmaniasis (visceral + cutaneous) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with leishmaniasis
endpoints and antileishmanial arm labels:

  binary outcomes (definitive / initial cure, relapse, parasite clearance, PKDL,
    cutaneous complete cure, mortality, adverse events, drug toxicities)
    -> 2x2 events/N per arm
  continuous (lesion size / induration, treatment duration, hospital stay)
    -> mean+SD / median+IQR (Wan).
"""
import re
from typing import Dict, List

from .leishmaniasis import get_leishmaniasis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Leishmaniasis endpoint patterns (string, endpoint) across all subspecialties.
_LEISH_ENDPOINT_PATTERNS = []
for _sub in ("visceral", "cutaneous", "combination", "safety"):
    _LEISH_ENDPOINT_PATTERNS.extend(get_leishmaniasis_endpoint_patterns(_sub))

# Antileishmanial arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
# Combination arms first so "SSG + paromomycin" is not split into a single drug.
_LEISH_ARM_FULL = [
    (r"(?:sodium\s+)?stibogluconate\s*(?:\+|/|and|plus)\s*paromomycin|"
     r"paromomycin\s*(?:\+|/|and|plus)\s*(?:sodium\s+)?stibogluconate", "ssg-paromomycin"),
    (r"liposomal\s+amphotericin\s*b|ambisome|l[- ]?amb(?:isome)?", "liposomal-amphotericin-b"),
    (r"amphotericin\s*b\s+deoxycholate|conventional\s+amphotericin", "amphotericin-b-deoxycholate"),
    (r"amphotericin\s*b", "amphotericin-b"),
    (r"miltefosine", "miltefosine"),
    (r"paromomycin|aminosidine", "paromomycin"),
    (r"meglumine\s+antimoniate|glucantime", "meglumine-antimoniate"),
    (r"sodium\s+stibogluconate|pentostam", "sodium-stibogluconate"),
    (r"pentavalent\s+antimon\w*|antimonial\w*", "antimonials"),
    (r"pentamidine", "pentamidine"),
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"untreated(?:\s+(?:group|arm|control))?", "untreated"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_LEISH_ARM_ABBREV = [   # case-sensitive uppercase (only unambiguous antileishmanial abbrevs;
                        # MA / PM dropped -- too collision-prone with US state codes / initials)
    (r"\bSSG\b", "sodium-stibogluconate"),
    (r"\bL-?AmB\b", "liposomal-amphotericin-b"),
    (r"\bAmB\b", "amphotericin-b"),
]
_LEISH_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _LEISH_ARM_FULL]
                       + [(re.compile(p), n) for p, n in _LEISH_ARM_ABBREV])

# Leishmaniasis continuous outcomes (mean+SD / median+IQR; all pool as raw MD).
_LEISH_CONTINUOUS = {"LESION_SIZE", "TREATMENT_DURATION", "HOSPITAL_STAY"}
_LEISH_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_LEISH_ENDPOINT_PATTERNS,
                                arm_compiled=_LEISH_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_LEISH_ENDPOINT_PATTERNS,
                               arm_compiled=_LEISH_ARM_COMPILED,
                               continuous_endpoints=_LEISH_CONTINUOUS,
                               lognormal_endpoints=_LEISH_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_LEISH_ENDPOINT_PATTERNS,
                              arm_compiled=_LEISH_ARM_COMPILED,
                              continuous_endpoints=_LEISH_CONTINUOUS,
                              lognormal_endpoints=_LEISH_LOGNORMAL)
