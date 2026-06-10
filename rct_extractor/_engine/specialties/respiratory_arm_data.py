"""
Arm-level / 2x2 + continuous extraction for respiratory (COPD / asthma / ILD)
trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with respiratory
endpoints and inhaler / biologic / antifibrotic arm labels:

  binary outcomes (exacerbation occurrence, hospitalisation, OCS reduction
    achieved, ILD progression, mortality, SAE) -> 2x2 events/N per arm
  continuous (FEV1, FVC, SGRQ, ACQ, ACT, AQLQ, PEF, 6MWD, DLCO) -> mean+SD /
    median+IQR; FeNO and blood eosinophils are log-normal (pool on the log scale).
"""
import re
from typing import Dict, List

from .respiratory import get_respiratory_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Respiratory endpoint patterns (string, endpoint) across all subspecialties.
_RESP_ENDPOINT_PATTERNS = []
for _sub in ("copd", "asthma", "ild", "general_respiratory"):
    _RESP_ENDPOINT_PATTERNS.extend(get_respiratory_endpoint_patterns(_sub))

_J = r"[/\-+ ]"   # combo joiner in text: slash, hyphen, plus, or space

# Inhaler / biologic / antifibrotic arm labels. Full names case-insensitive;
# bare UPPERCASE abbreviations case-sensitive. Fixed-dose combination inhalers are
# matched as a unit FIRST so a 2x2 arm is not fragmented into its components.
_RESP_ARM_FULL = [
    # ICS/LABA and triple combination inhalers (brand + generic forms)
    (rf"fluticasone(?:\s+furoate)?{_J}(?:umeclidinium{_J})?vilanterol|\btrelegy\b|\bbreo\b|\brelvar\b",
     "fluticasone-vilanterol"),
    (rf"budesonide{_J}(?:glycopyrr?onium{_J})?formoterol|\bsymbicort\b|\bbreztri\b|\btrixeo\b",
     "budesonide-formoterol"),
    (rf"fluticasone{_J}salmeterol|salmeterol{_J}fluticasone|\badvair\b|\bseretide\b",
     "fluticasone-salmeterol"),
    (rf"umeclidinium{_J}vilanterol|\banoro\b", "umeclidinium-vilanterol"),
    (rf"glycopyrr?onium{_J}(?:indacaterol|formoterol)|\bultibro\b|\bbevespi\b",
     "glycopyrronium-laba"),
    (rf"indacaterol{_J}glycopyrr?onium", "glycopyrronium-laba"),
    # COPD bronchodilators (LAMA / LABA monocomponents)
    (r"tiotropium|\bspiriva\b", "tiotropium"),
    (r"umeclidinium", "umeclidinium"),
    (r"glycopyrr?onium|glycopyrr?olate", "glycopyrronium"),
    (r"aclidinium", "aclidinium"),
    (r"salmeterol", "salmeterol"),
    (r"formoterol", "formoterol"),
    (r"vilanterol", "vilanterol"),
    (r"indacaterol", "indacaterol"),
    (r"olodaterol", "olodaterol"),
    # ICS monocomponents
    (r"fluticasone(?:\s+(?:furoate|propionate))?", "fluticasone"),
    (r"budesonide", "budesonide"),
    (r"beclomethasone|beclometasone", "beclomethasone"),
    (r"mometasone", "mometasone"),
    (r"ciclesonide", "ciclesonide"),
    (r"roflumilast", "roflumilast"),
    (r"triple\s+therapy", "triple-therapy"),
    # Asthma biologics
    (r"mepolizumab|\bnucala\b", "mepolizumab"),
    (r"benralizumab|\bfasenra\b", "benralizumab"),
    (r"reslizumab|\bcinqair\b", "reslizumab"),
    (r"dupilumab|\bdupixent\b", "dupilumab"),
    (r"omalizumab|\bxolair\b", "omalizumab"),
    (r"tezepelumab|\btezspire\b", "tezepelumab"),
    # ILD antifibrotics
    (r"nintedanib|\bofev\b", "nintedanib"),
    (r"pirfenidone|\besbriet\b", "pirfenidone"),
    # Generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_RESP_ARM_ABBREV = [   # case-sensitive uppercase device/combo abbreviations
    (rf"\bFF{_J}UMEC{_J}VI\b", "fluticasone-umeclidinium-vilanterol"),
    (rf"\bFF{_J}VI\b", "fluticasone-vilanterol"),
    (rf"\bUMEC{_J}VI\b", "umeclidinium-vilanterol"),
    (rf"\bBUD{_J}FORM\b", "budesonide-formoterol"),
    (r"\bUMEC\b", "umeclidinium"),
    (r"\bTIO\b", "tiotropium"),
]
_RESP_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _RESP_ARM_FULL]
                      + [(re.compile(p), n) for p, n in _RESP_ARM_ABBREV])

# Continuous outcomes; FeNO and blood eosinophils are log-normal -- pool on the
# log scale.
_RESP_CONTINUOUS = {
    "TROUGH_FEV1", "FEV1_DECLINE", "SGRQ", "CAT_SCORE", "DYSPNEA_TDI",
    "RESCUE_MEDICATION", "ACQ", "ACT", "AQLQ", "PEF", "FENO", "BLOOD_EOSINOPHILS",
    "FVC", "FVC_DECLINE", "DLCO", "SIX_MIN_WALK",
}
_RESP_LOGNORMAL = {"FENO", "BLOOD_EOSINOPHILS"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_RESP_ENDPOINT_PATTERNS,
                                arm_compiled=_RESP_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_RESP_ENDPOINT_PATTERNS,
                               arm_compiled=_RESP_ARM_COMPILED,
                               continuous_endpoints=_RESP_CONTINUOUS,
                               lognormal_endpoints=_RESP_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_RESP_ENDPOINT_PATTERNS,
                              arm_compiled=_RESP_ARM_COMPILED,
                              continuous_endpoints=_RESP_CONTINUOUS,
                              lognormal_endpoints=_RESP_LOGNORMAL)
