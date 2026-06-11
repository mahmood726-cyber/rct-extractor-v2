"""
Arm-level / 2x2 + continuous extraction for perioperative & anaesthesia trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data configured with
perioperative endpoints and anaesthesia / surgery arm labels:

  binary outcomes (mortality, MACE, myocardial injury, PONV, delirium, AKI,
    surgical-site infection, complications) -> 2x2 events/N per arm;
  continuous outcomes (length of stay, time to recovery, pain score, opioid
    consumption) -> per-arm mean+SD (Wan IQR->SD when reported as median/IQR).

Comparisons are typically technique-vs-technique (regional vs general, TIVA vs
volatile, neuraxial vs GA) or drug-vs-placebo (antiemetics, beta-blockers,
dexmedetomidine, tranexamic acid).
"""
import re
from typing import Dict, List

from .perioperative import get_perioperative_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

_PERIOP_ENDPOINT_PATTERNS = []
for _sub in ("anaesthetic_technique", "ponv", "organ_protection", "recovery"):
    _PERIOP_ENDPOINT_PATTERNS.extend(get_perioperative_endpoint_patterns(_sub))

# Anaesthesia / surgery arm labels. Descriptive names case-insensitive; bare
# abbreviations (TIVA, GA, PNB, BIS) matched case-sensitively.
_PERIOP_ARM_FULL = [
    (r"regional\s+an(?:ae|e)sthesia|neuraxial\s+an(?:ae|e)sthesia", "regional-anaesthesia"),
    (r"spinal\s+an(?:ae|e)sthesia|\bspinal\b", "spinal"),
    (r"epidural\s+an(?:ae|e)sthesia|\bepidural\b", "epidural"),
    (r"peripheral\s+nerve\s+block|nerve\s+block|fascial\s+plane\s+block", "nerve-block"),
    (r"general\s+an(?:ae|e)sthesia", "general-anaesthesia"),
    (r"total\s+intravenous\s+an(?:ae|e)sthesia|propofol[- ]based", "TIVA"),
    (r"volatile\s+an(?:ae|e)sthe\w+|inhalational\s+an(?:ae|e)sthesia", "volatile-anaesthesia"),
    (r"sevoflurane", "sevoflurane"),
    (r"desflurane", "desflurane"),
    (r"propofol", "propofol"),
    (r"dexmedetomidine", "dexmedetomidine"),
    (r"ondansetron", "ondansetron"),
    (r"dexamethasone", "dexamethasone"),
    (r"droperidol", "droperidol"),
    (r"aprepitant", "aprepitant"),
    (r"palonosetron", "palonosetron"),
    (r"tranexamic\s+acid", "tranexamic-acid"),
    (r"beta[- ]?blocker|metoprolol|esmolol|bisoprolol", "beta-blocker"),
    (r"lidocaine|lignocaine", "lidocaine"),
    (r"ketamine", "ketamine"),
    (r"goal[- ]directed\s+(?:h(?:ae|e)modynamic\s+)?therapy", "goal-directed-therapy"),
    (r"enhanced\s+recovery\s+after\s+surgery", "ERAS"),
    (r"\bplacebo\b", "placebo"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care|standard\s+(?:treatment|management)",
     "standard-of-care"),
    (r"saline|normal\s+saline", "saline"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_PERIOP_ARM_ABBREV = [   # case-sensitive
    (r"\bERAS\b", "ERAS"),
    (r"\bTIVA\b", "TIVA"),
    (r"\bGA\b", "general-anaesthesia"),
    (r"\bRA\b", "regional-anaesthesia"),
    (r"\bPNB\b", "nerve-block"),
    (r"\bTXA\b", "tranexamic-acid"),
    (r"\bGDT\b", "goal-directed-therapy"),
    (r"\bBIS\b", "BIS-guided"),
]
_PERIOP_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _PERIOP_ARM_FULL]
                        + [(re.compile(p), n) for p, n in _PERIOP_ARM_ABBREV])

# Continuous (mean+SD poolable) perioperative endpoints. Length of stay, time to
# recovery, pain scores and opioid consumption are reported as means (or
# median/IQR -> Wan SD). None are log-normal here (opioid mg is treated linearly).
_PERIOP_CONTINUOUS = {
    "LENGTH_OF_STAY", "TIME_TO_RECOVERY", "PAIN_SCORE", "OPIOID_CONSUMPTION",
}
_PERIOP_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_PERIOP_ENDPOINT_PATTERNS,
                                arm_compiled=_PERIOP_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_PERIOP_ENDPOINT_PATTERNS,
                               arm_compiled=_PERIOP_ARM_COMPILED,
                               continuous_endpoints=_PERIOP_CONTINUOUS,
                               lognormal_endpoints=_PERIOP_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_PERIOP_ENDPOINT_PATTERNS,
                              arm_compiled=_PERIOP_ARM_COMPILED,
                              continuous_endpoints=_PERIOP_CONTINUOUS,
                              lognormal_endpoints=_PERIOP_LOGNORMAL)
