"""
Arm-level / 2x2 + continuous extraction for cardiology (heart failure / ACS /
atrial fibrillation / valve) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with cardiology
endpoints and cardiology arm labels:

  binary outcomes (CV death or HF hospitalisation, MACE, MI, stroke, major
    bleeding, ...) -> 2x2 events/N per arm
  continuous (LVEF, KCCQ score, NT-proBNP) -> mean+SD / median+IQR; NT-proBNP /
    BNP (natriuretic peptides) are log-normal (pool on the log scale).
"""
import re
from typing import Dict, List

from .cardiology import get_cardiology_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Cardiology endpoint patterns (string, endpoint) across all subspecialties.
_CARD_ENDPOINT_PATTERNS = []
for _sub in ("heart_failure", "acs", "af", "valve"):
    _CARD_ENDPOINT_PATTERNS.extend(get_cardiology_endpoint_patterns(_sub))

_J = r"[/\-+ ]"   # combo joiner in text: slash, hyphen, plus, or space

# Cardiology arm labels. Full names case-insensitive; bare UPPERCASE
# abbreviations case-sensitive. The sacubitril-valsartan fixed-dose combination
# (Entresto / ARNI) is matched as a unit FIRST so a 2x2 arm is not fragmented
# into its valsartan / sacubitril components (which would then fail to pair).
# Bare effect abbreviations (HR/RR/OR) are NEVER used as arm labels -- they
# collide with hazard ratio / heart rate / odds ratio.
_CARD_ARM_FULL = [
    # ARNI fixed-dose combination (combo FIRST; brand + generic forms)
    (rf"sacubitril{_J}valsartan|valsartan{_J}sacubitril|\bentresto\b|\barni\b",
     "sacubitril-valsartan"),
    # ARNI components (combo-suppressed: only match when NOT part of the combo).
    # The lookahead/lookbehind exclude an adjacent joiner+partner so the combo
    # above wins; plain "valsartan monotherapy" still matches.
    (rf"(?<!sacubitril{_J})valsartan(?!{_J}sacubitril)", "valsartan"),
    (rf"sacubitril(?!{_J}valsartan)", "sacubitril"),
    # SGLT2 inhibitors
    (r"empagliflozin|\bjardiance\b", "empagliflozin"),
    (r"dapagliflozin|\bfarxiga\b|\bforxiga\b", "dapagliflozin"),
    (r"canagliflozin|\binvokana\b", "canagliflozin"),
    # MRAs
    (r"spironolactone", "spironolactone"),
    (r"eplerenone", "eplerenone"),
    (r"finerenone|\bkerendia\b", "finerenone"),
    # Beta-blockers
    (r"carvedilol", "carvedilol"),
    (r"metoprolol", "metoprolol"),
    (r"bisoprolol", "bisoprolol"),
    # ACE inhibitors
    (r"enalapril", "enalapril"),
    (r"ramipril", "ramipril"),
    (r"lisinopril", "lisinopril"),
    # ARBs
    (r"candesartan", "candesartan"),
    (r"losartan", "losartan"),
    # HF rate control / other
    (r"ivabradine", "ivabradine"),
    (r"digoxin", "digoxin"),
    # Antiplatelets
    (r"ticagrelor|\bbrilinta\b", "ticagrelor"),
    (r"prasugrel|\beffient\b", "prasugrel"),
    (r"clopidogrel|\bplavix\b", "clopidogrel"),
    (r"\baspirin\b|acetylsalicylic\s+acid", "aspirin"),
    # Anticoagulants
    (r"apixaban|\beliquis\b", "apixaban"),
    (r"rivaroxaban|\bxarelto\b", "rivaroxaban"),
    (r"dabigatran|\bpradaxa\b", "dabigatran"),
    (r"edoxaban|\blixiana\b|\bsavaysa\b", "edoxaban"),
    (r"warfarin", "warfarin"),
    # Statins / PCSK9
    (r"atorvastatin|\blipitor\b", "atorvastatin"),
    (r"rosuvastatin|\bcrestor\b", "rosuvastatin"),
    (r"evolocumab|\brepatha\b", "evolocumab"),
    (r"alirocumab|\bpraluent\b", "alirocumab"),
    # Antiarrhythmics
    (r"amiodarone", "amiodarone"),
    (r"dronedarone|\bmultaq\b", "dronedarone"),
    # Procedures / devices
    (r"percutaneous\s+coronary\s+intervention", "PCI"),
    (r"coronary\s+artery\s+bypass(?:\s+graft(?:ing)?)?", "CABG"),
    (r"transcatheter\s+aortic\s+valve\s+(?:replacement|implantation)", "TAVR"),
    (r"surgical\s+aortic\s+valve\s+replacement", "SAVR"),
    # Generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|standard\s+therapy", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_CARD_ARM_ABBREV = [   # case-sensitive uppercase abbreviations
    (r"\bPCI\b", "PCI"),
    (r"\bCABG\b", "CABG"),
    (r"\bTAVR\b|\bTAVI\b", "TAVR"),
    (r"\bSAVR\b", "SAVR"),
    (r"\bASA\b", "aspirin"),
    (r"\bDAPT\b", "dual-antiplatelet"),
]
_CARD_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _CARD_ARM_FULL]
                      + [(re.compile(p), n) for p, n in _CARD_ARM_ABBREV])

# Cardiology continuous outcomes; NT-proBNP / BNP (natriuretic peptides) are
# log-normal -- pool on the log scale / use a geometric mean ratio, not a raw MD.
_CARD_CONTINUOUS = {"LVEF", "KCCQ_CSS", "NT_PROBNP"}
_CARD_LOGNORMAL = {"NT_PROBNP"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_CARD_ENDPOINT_PATTERNS,
                                arm_compiled=_CARD_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_CARD_ENDPOINT_PATTERNS,
                               arm_compiled=_CARD_ARM_COMPILED,
                               continuous_endpoints=_CARD_CONTINUOUS,
                               lognormal_endpoints=_CARD_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_CARD_ENDPOINT_PATTERNS,
                              arm_compiled=_CARD_ARM_COMPILED,
                              continuous_endpoints=_CARD_CONTINUOUS,
                              lognormal_endpoints=_CARD_LOGNORMAL)
