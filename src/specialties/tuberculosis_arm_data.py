"""
Arm-level / 2x2 + continuous extraction for tuberculosis trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with TB endpoints
and anti-tuberculosis arm labels:

  binary outcomes (culture conversion, treatment success, unfavourable outcome,
    relapse, TPT completion, incident TB) -> 2x2 events/N per arm.

TB arm-level poolable data is overwhelmingly binary; time-to-culture-conversion
(the main continuous-looking outcome) is reported and pooled as a hazard ratio
via the core effect-size engine, not as a per-arm mean+SD, so the continuous set
is intentionally empty here.

TB regimens are frequently named by multi-drug abbreviations (HRZE, BPaL, BPaLM,
3HP, 1HP) as well as individual drugs; both forms are matched.
"""
import re
from typing import Dict, List

from .tuberculosis import get_tuberculosis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# TB endpoint patterns (string, endpoint) across all subspecialties.
_TB_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "drug_resistant", "prevention", "latent"):
    _TB_ENDPOINT_PATTERNS.extend(get_tuberculosis_endpoint_patterns(_sub))

# Anti-TB arm labels. Full names case-insensitive; bare regimen/drug
# abbreviations (HRZE, BPaL, INH, RIF, ...) matched case-sensitively so the
# common words don't collide.
_TB_ARM_FULL = [
    (r"isoniazid", "isoniazid"),
    (r"rifapentine", "rifapentine"),
    (r"rifampic?in", "rifampicin"),
    (r"rifabutin", "rifabutin"),
    (r"pyrazinamide", "pyrazinamide"),
    (r"ethambutol", "ethambutol"),
    (r"moxifloxacin", "moxifloxacin"),
    (r"levofloxacin", "levofloxacin"),
    (r"gatifloxacin", "gatifloxacin"),
    (r"bedaquiline", "bedaquiline"),
    (r"delamanid", "delamanid"),
    (r"pretomanid", "pretomanid"),
    (r"linezolid", "linezolid"),
    (r"clofazimine", "clofazimine"),
    (r"cycloserine", "cycloserine"),
    (r"amikacin", "amikacin"),
    (r"kanamycin", "kanamycin"),
    (r"capreomycin", "capreomycin"),
    (r"ethionamide", "ethionamide"),
    (r"streptomycin", "streptomycin"),
    (r"\bbcg\b|bacille\s+calmette[- ]gu[eé]rin", "BCG"),
    (r"\bm72\s*/?\s*as01e\b|\bm72\b", "M72/AS01E"),
    (r"isoniazid\s+preventive\s+therapy", "IPT"),
    (r"weekly\s+rifapentine(?:\s+(?:plus|and|\+)\s+isoniazid)?", "rifapentine-isoniazid"),
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|standard\s+(?:tb\s+)?(?:regimen|therapy|treatment)",
     "standard-of-care"),
    (r"control\s+(?:regimen|group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"short\w*\s+regimen|shorter\s+regimen", "short-regimen"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_TB_ARM_ABBREV = [   # case-sensitive
    (r"\bBPaLM\b", "BPaLM"),
    (r"\bBPaL\b", "BPaL"),
    (r"\b2?HRZE\b", "HRZE"),
    (r"\bHRZ\b", "HRZ"),
    (r"\b3HP\b", "3HP"),
    (r"\b1HP\b", "1HP"),
    (r"\b6H\b", "6H"),
    (r"\b9H\b", "9H"),
    (r"\b4R\b", "4R"),
    (r"\bINH\b", "isoniazid"),
    (r"\bRIF\b", "rifampicin"),
    (r"\bRPT\b", "rifapentine"),
    (r"\bPZA\b", "pyrazinamide"),
    (r"\bEMB\b", "ethambutol"),
    (r"\bMFX\b|\bMXF\b", "moxifloxacin"),
    (r"\bLFX\b|\bLVX\b", "levofloxacin"),
    (r"\bBDQ\b", "bedaquiline"),
    (r"\bDLM\b", "delamanid"),
    (r"\bLZD\b", "linezolid"),
    (r"\bCFZ\b", "clofazimine"),
]
_TB_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _TB_ARM_FULL]
                    + [(re.compile(p), n) for p, n in _TB_ARM_ABBREV])

# TB arm-level poolable outcomes are binary 2x2 (see module docstring); the
# continuous set is intentionally empty.
_TB_CONTINUOUS = set()
_TB_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_TB_ENDPOINT_PATTERNS,
                                arm_compiled=_TB_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_TB_ENDPOINT_PATTERNS,
                               arm_compiled=_TB_ARM_COMPILED,
                               continuous_endpoints=_TB_CONTINUOUS,
                               lognormal_endpoints=_TB_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_TB_ENDPOINT_PATTERNS,
                              arm_compiled=_TB_ARM_COMPILED,
                              continuous_endpoints=_TB_CONTINUOUS,
                              lognormal_endpoints=_TB_LOGNORMAL)
