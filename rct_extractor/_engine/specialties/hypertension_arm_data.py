"""
Arm-level / 2x2 + continuous extraction for hypertension / cardiovascular trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with hypertension
endpoints and antihypertensive drug-class arm labels:

  binary outcomes (BP control, response, stroke, MI, CV death, all-cause
    mortality, adherence, persistence) -> 2x2 events/N per arm
  continuous (systolic / diastolic / mean-arterial / ambulatory blood-pressure
    reduction) -> mean+SD / median+IQR, pooled as MD/SMD on the natural scale.
"""
import re
from typing import Dict, List

from .hypertension import get_hypertension_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Hypertension endpoint patterns (string, endpoint) across all subspecialties.
_HTN_ENDPOINT_PATTERNS = []
for _sub in ("bp_lowering", "cv_events", "bp_reduction", "adherence"):
    _HTN_ENDPOINT_PATTERNS.extend(get_hypertension_endpoint_patterns(_sub))

# Antihypertensive drug-class arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_HTN_ARM_FULL = [
    # ACE inhibitors
    (r"lisinopril", "lisinopril"),
    (r"enalapril", "enalapril"),
    (r"ramipril", "ramipril"),
    (r"perindopril", "perindopril"),
    (r"captopril", "captopril"),
    (r"angiotensin[- ]converting[- ]enzyme\s+inhibitor|ace\s+inhibitor", "ace-inhibitor"),
    # ARBs
    (r"losartan", "losartan"),
    (r"valsartan", "valsartan"),
    (r"candesartan", "candesartan"),
    (r"telmisartan", "telmisartan"),
    (r"olmesartan", "olmesartan"),
    (r"irbesartan", "irbesartan"),
    (r"angiotensin[- ]receptor\s+blocker", "angiotensin-receptor-blocker"),
    # Calcium-channel blockers
    (r"amlodipine", "amlodipine"),
    (r"nifedipine", "nifedipine"),
    (r"felodipine", "felodipine"),
    (r"lercanidipine", "lercanidipine"),
    (r"calcium[- ]channel\s+blocker", "calcium-channel-blocker"),
    # Thiazide / thiazide-like diuretics
    (r"hydrochlorothiazide", "hydrochlorothiazide"),
    (r"chlort(?:h)?alidone", "chlorthalidone"),
    (r"indapamide", "indapamide"),
    (r"bendroflumethiazide", "bendroflumethiazide"),
    (r"thiazide(?:[- ]like)?\s+diuretic|thiazide", "thiazide-diuretic"),
    # Beta-blockers
    (r"atenolol", "atenolol"),
    (r"metoprolol", "metoprolol"),
    (r"bisoprolol", "bisoprolol"),
    (r"carvedilol", "carvedilol"),
    (r"nebivolol", "nebivolol"),
    (r"beta[- ]blocker", "beta-blocker"),
    # MRA / ARNI / other
    (r"spironolactone", "spironolactone"),
    (r"eplerenone", "eplerenone"),
    (r"sacubitril[\/ -]?valsartan|sacubitril", "sacubitril-valsartan"),
    (r"hydralazine", "hydralazine"),
    (r"methyldopa", "methyldopa"),
    (r"doxazosin", "doxazosin"),
    (r"aliskiren", "aliskiren"),
    # generic comparators
    (r"single[- ]pill\s+combination|fixed[- ]dose\s+combination", "single-pill-combination"),
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    # "control" as an arm, but NOT the "blood[- ]pressure control" endpoint phrase
    (r"(?<!pressure[- ])control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_HTN_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bHCTZ\b", "hydrochlorothiazide"),
    (r"\bACEi?\b", "ace-inhibitor"),
    (r"\bARB\b", "angiotensin-receptor-blocker"),
    (r"\bCCB\b", "calcium-channel-blocker"),
    (r"\bSPC\b", "single-pill-combination"),
]
_HTN_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _HTN_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _HTN_ARM_ABBREV])

# Hypertension continuous outcomes (blood-pressure change, natural scale; no
# log-normal endpoints).
_HTN_CONTINUOUS = {"SBP_REDUCTION", "DBP_REDUCTION", "MAP_REDUCTION", "AMBULATORY_SBP"}
_HTN_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_HTN_ENDPOINT_PATTERNS,
                                arm_compiled=_HTN_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_HTN_ENDPOINT_PATTERNS,
                               arm_compiled=_HTN_ARM_COMPILED,
                               continuous_endpoints=_HTN_CONTINUOUS,
                               lognormal_endpoints=_HTN_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_HTN_ENDPOINT_PATTERNS,
                              arm_compiled=_HTN_ARM_COMPILED,
                              continuous_endpoints=_HTN_CONTINUOUS,
                              lognormal_endpoints=_HTN_LOGNORMAL)
