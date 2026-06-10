"""
Arm-level / 2x2 + continuous extraction for dyslipidaemia / lipid-lowering trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with dyslipidaemia
endpoints and lipid-lowering drug-class arm labels:

  binary outcomes (LDL-goal attainment, new-onset diabetes, myopathy, ALT
    elevation, discontinuation, MACE, MI, stroke, CV/all-cause death,
    revascularisation) -> 2x2 events/N per arm
  continuous (LDL/HDL/non-HDL/triglyceride/total-cholesterol/ApoB/Lp(a) change)
    -> mean+SD / median+IQR, pooled as MD/SMD on the natural scale.
"""
import re
from typing import Dict, List

from .dyslipidaemia import get_dyslipidaemia_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Dyslipidaemia endpoint patterns (string, endpoint) across all subspecialties.
_DLD_ENDPOINT_PATTERNS = []
for _sub in ("lipid_lowering", "ldl_target", "cv_events", "safety"):
    _DLD_ENDPOINT_PATTERNS.extend(get_dyslipidaemia_endpoint_patterns(_sub))

# Lipid-lowering drug-class arm labels. Full names case-insensitive; bare
# UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does not match).
_DLD_ARM_FULL = [
    # Statins
    (r"atorvastatin", "atorvastatin"),
    (r"rosuvastatin", "rosuvastatin"),
    (r"simvastatin", "simvastatin"),
    (r"pravastatin", "pravastatin"),
    (r"lovastatin", "lovastatin"),
    (r"pitavastatin", "pitavastatin"),
    (r"fluvastatin", "fluvastatin"),
    (r"high[- ]intensity\s+statin|moderate[- ]intensity\s+statin|\bstatin\b", "statin"),
    # Cholesterol-absorption inhibitor
    (r"ezetimibe", "ezetimibe"),
    # PCSK9 inhibitors / siRNA
    (r"evolocumab", "evolocumab"),
    (r"alirocumab", "alirocumab"),
    (r"inclisiran", "inclisiran"),
    (r"pcsk9\s+inhibitor", "pcsk9-inhibitor"),
    # Other lipid-lowering
    (r"bempedoic\s+acid", "bempedoic-acid"),
    (r"fenofibrate", "fenofibrate"),
    (r"gemfibrozil", "gemfibrozil"),
    (r"\bfibrate\b", "fibrate"),
    (r"colesevelam", "colesevelam"),
    (r"cholestyramine", "cholestyramine"),
    (r"icosapent\s+ethyl", "icosapent-ethyl"),
    (r"omega[- ]3(?:\s+fatty\s+acids?)?", "omega-3"),
    (r"niacin|nicotinic\s+acid", "niacin"),
    (r"anacetrapib", "anacetrapib"),
    (r"obicetrapib", "obicetrapib"),
    (r"evinacumab", "evinacumab"),
    # generic comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_DLD_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bPCSK9\b", "pcsk9-inhibitor"),
    (r"\bIPE\b", "icosapent-ethyl"),
]
_DLD_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _DLD_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _DLD_ARM_ABBREV])

# Dyslipidaemia continuous outcomes (lipid change, natural scale).
_DLD_CONTINUOUS = {"LDL_REDUCTION", "NON_HDL_REDUCTION", "HDL_CHANGE", "TG_REDUCTION",
                   "TOTAL_CHOL_REDUCTION", "APOB_REDUCTION", "LPA_REDUCTION"}
_DLD_LOGNORMAL: set = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_DLD_ENDPOINT_PATTERNS,
                                arm_compiled=_DLD_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_DLD_ENDPOINT_PATTERNS,
                               arm_compiled=_DLD_ARM_COMPILED,
                               continuous_endpoints=_DLD_CONTINUOUS,
                               lognormal_endpoints=_DLD_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_DLD_ENDPOINT_PATTERNS,
                              arm_compiled=_DLD_ARM_COMPILED,
                              continuous_endpoints=_DLD_CONTINUOUS,
                              lognormal_endpoints=_DLD_LOGNORMAL)
