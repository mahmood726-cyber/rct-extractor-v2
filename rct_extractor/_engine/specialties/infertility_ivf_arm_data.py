"""
Arm-level / 2x2 + continuous extraction for infertility / IVF / ART trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with infertility/IVF
endpoints and stimulation-protocol / transfer-strategy arm labels:

  binary outcomes (clinical pregnancy, live birth, ongoing pregnancy, miscarriage,
    OHSS, multiple pregnancy, ovulation, cycle cancellation) -> 2x2 events/N per arm
  continuous (oocytes retrieved, mature MII oocytes, peak oestradiol, total
    gonadotrophin dose, endometrial thickness) -> mean/SD per arm, pooled on the
    natural scale (MD/SMD).
"""
import re
from typing import Dict, List

from .infertility_ivf import get_infertility_ivf_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Infertility/IVF endpoint patterns (string, endpoint) across all subspecialties.
_IVF_ENDPOINT_PATTERNS = []
for _sub in ("stimulation", "lab", "transfer", "ovulation"):
    _IVF_ENDPOINT_PATTERNS.extend(get_infertility_ivf_endpoint_patterns(_sub))

# Stimulation-protocol / transfer-strategy arm labels. Full names case-insensitive;
# bare UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token does not
# match).
_IVF_ARM_FULL = [
    # stimulation protocols
    (r"gn?rh\s+antagonist(?:\s+protocol)?", "gnrh-antagonist"),
    (r"(?:long\s+)?gn?rh\s+agonist(?:\s+protocol)?|long\s+protocol", "gnrh-agonist"),
    (r"progestin[- ]primed(?:\s+ovarian\s+stimulation)?|\bppos\b", "ppos"),
    (r"recombinant\s+fsh|follitropin(?:\s+(?:alfa|beta|delta))?|rec[- ]?fsh", "rfsh"),
    (r"highly[- ]purified\s+(?:hmg|menotrophin)|hp[- ]?hmg|human\s+menopausal\s+gonadotro?ph?in|menotro?ph?in",
     "hmg"),
    (r"corifollitropin", "corifollitropin"),
    (r"clomi(?:phene|fene)(?:\s+citrate)?", "clomiphene"),
    (r"letrozole", "letrozole"),
    # trigger
    (r"hcg\s+trigger|human\s+chorionic\s+gonadotro?ph?in\s+trigger", "hcg-trigger"),
    (r"gn?rh[- ]agonist\s+trigger|agonist\s+trigger", "agonist-trigger"),
    # transfer strategy
    (r"frozen[- ](?:thawed\s+)?(?:embryo\s+)?(?:transfer)?|frozen\s+embryo|\bfet\b",
     "frozen-transfer"),
    (r"fresh\s+(?:embryo\s+)?transfer|fresh\s+cycle", "fresh-transfer"),
    (r"(?:elective\s+)?single\s+embryo\s+transfer|single[- ]embryo", "single-embryo-transfer"),
    (r"double\s+embryo\s+transfer|two\s+embryos?", "double-embryo-transfer"),
    (r"blastocyst[- ](?:stage\s+)?(?:transfer)?", "blastocyst-transfer"),
    (r"cleavage[- ](?:stage\s+)?(?:transfer)?", "cleavage-transfer"),
    # lab method
    (r"intracytoplasmic\s+sperm\s+injection", "icsi"),
    (r"conventional\s+ivf|standard\s+ivf", "conventional-ivf"),
    # generic
    (r"\bplacebo\b", "placebo"),
    (r"intrauterine\s+insemination", "iui"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_IVF_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bFET\b", "frozen-transfer"),
    (r"\bICSI\b", "icsi"),
    (r"\bIVF\b", "conventional-ivf"),
    (r"\bIUI\b", "iui"),
    (r"\bGnRH\b(?=\s*antagonist)", "gnrh-antagonist"),
    (r"\brFSH\b|\bhMG\b", "rfsh"),
    (r"\bPPOS\b", "ppos"),
    (r"\beSET\b|\bSET\b", "single-embryo-transfer"),
]
_IVF_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _IVF_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _IVF_ARM_ABBREV])

# Infertility/IVF continuous outcomes (linear scales; none log-normal).
_IVF_CONTINUOUS = {"OOCYTES_RETRIEVED", "MATURE_OOCYTES", "ESTRADIOL_TRIGGER",
                   "GONADOTROPHIN_DOSE", "ENDOMETRIAL_THICKNESS"}
_IVF_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_IVF_ENDPOINT_PATTERNS,
                                arm_compiled=_IVF_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_IVF_ENDPOINT_PATTERNS,
                               arm_compiled=_IVF_ARM_COMPILED,
                               continuous_endpoints=_IVF_CONTINUOUS,
                               lognormal_endpoints=_IVF_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_IVF_ENDPOINT_PATTERNS,
                              arm_compiled=_IVF_ARM_COMPILED,
                              continuous_endpoints=_IVF_CONTINUOUS,
                              lognormal_endpoints=_IVF_LOGNORMAL)
