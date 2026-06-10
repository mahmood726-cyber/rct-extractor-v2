"""
Arm-level / 2x2 + continuous extraction for nephrology (kidney) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with nephrology
endpoints and SGLT2 / RAAS / endothelin / immunosuppressant / anaemia-agent arm
labels:

  binary outcomes (kidney failure [ESKD], composite kidney outcome, AKI, need
    for RRT, kidney recovery, complete remission, relapse, mortality,
    hospitalisation, vascular-access failure) -> 2x2 events/N per arm
  continuous (eGFR slope, Kt/V dialysis adequacy, albuminuria/UACR,
    proteinuria/UPCR) -> mean+SD / median+IQR. Urinary albumin/protein (UACR,
    UPCR, 24h protein) are LOG-NORMAL -- pool on the log scale (GMR), not a raw
    MD. eGFR slope and Kt/V are NOT log-normal.
"""
import re
from typing import Dict, List

from .nephrology import get_nephrology_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Nephrology endpoint patterns (string, endpoint) across all subspecialties.
_NEPHRO_ENDPOINT_PATTERNS = []
for _sub in ("ckd", "dialysis", "aki", "glomerular"):
    _NEPHRO_ENDPOINT_PATTERNS.extend(get_nephrology_endpoint_patterns(_sub))

# SGLT2 inhibitor / RAAS / endothelin-antagonist / immunosuppressant / anaemia-
# agent arm labels. Full names case-insensitive; a bare effect abbreviation
# (HR/OR/RR) is NEVER an arm label. mycophenolate mofetil (MMF) is matched as a
# unit. Generic comparators (placebo / standard-of-care / control) included so a
# drug-vs-placebo 2x2 pairs.
_NEPHRO_ARM_FULL = [
    # SGLT2 inhibitors
    (r"dapagliflozin|\bfarxiga\b|\bforxiga\b", "dapagliflozin"),
    (r"empagliflozin|\bjardiance\b", "empagliflozin"),
    (r"canagliflozin|\binvokana\b", "canagliflozin"),
    # Non-steroidal MRA / steroidal MRA (RAAS)
    (r"finerenone|\bkerendia\b", "finerenone"),
    (r"spironolactone|\baldactone\b", "spironolactone"),
    (r"eplerenone|\binspra\b", "eplerenone"),
    # ACE inhibitors / ARBs (RAAS)
    (r"ramipril", "ramipril"),
    (r"lisinopril", "lisinopril"),
    (r"enalapril", "enalapril"),
    (r"losartan", "losartan"),
    (r"irbesartan", "irbesartan"),
    (r"valsartan", "valsartan"),
    # Endothelin receptor antagonists
    (r"sparsentan|\bfilspari\b", "sparsentan"),
    (r"atrasentan", "atrasentan"),
    # Immunosuppressants (glomerular disease)
    (r"rituximab|\brituxan\b|\bmabthera\b", "rituximab"),
    (r"cyclophosphamide|\bcytoxan\b", "cyclophosphamide"),
    (r"mycophenolate\s+mofetil|mycophenolate|\bmmf\b|\bcellcept\b", "mycophenolate"),
    (r"tacrolimus|\bprograf\b", "tacrolimus"),
    (r"cyclosporine|cyclosporin|cic?losporin\w*|\bneoral\b|\bsandimmune\b", "cyclosporine"),
    (r"prednisone|prednisolone|corticosteroids?|glucocorticoids?", "corticosteroid"),
    # Anaemia / other
    (r"roxadustat", "roxadustat"),
    (r"tolvaptan|\bjynarque\b|\bjinarc\b", "tolvaptan"),
    (r"erythropoietin|erythropoiesis[- ]stimulating\s+agent|darbepoetin|epoetin|\besa\b",
     "erythropoietin"),
    # Generic comparators
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care|standard\s+(?:medical\s+)?(?:care|therapy)|"
     r"best\s+supportive\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_NEPHRO_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bMMF\b", "mycophenolate"),
    (r"\bRTX\b", "rituximab"),
    (r"\bCYC\b", "cyclophosphamide"),
    (r"\bESA\b", "erythropoietin"),
]
_NEPHRO_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _NEPHRO_ARM_FULL]
                        + [(re.compile(p), n) for p, n in _NEPHRO_ARM_ABBREV])

# Nephrology continuous outcomes. Urinary albumin/protein (UACR, UPCR, 24h
# protein) are right-skewed and LOG-NORMAL -- pool on the log scale (GMR), never
# as a raw MD. eGFR slope (mL/min/1.73m2) and Kt/V (dialysis adequacy) are NOT
# log-normal.
_NEPHRO_CONTINUOUS = {"EGFR_SLOPE", "ALBUMINURIA", "PROTEINURIA", "DIALYSIS_ADEQUACY"}
_NEPHRO_LOGNORMAL = {"ALBUMINURIA", "PROTEINURIA"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_NEPHRO_ENDPOINT_PATTERNS,
                                arm_compiled=_NEPHRO_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_NEPHRO_ENDPOINT_PATTERNS,
                               arm_compiled=_NEPHRO_ARM_COMPILED,
                               continuous_endpoints=_NEPHRO_CONTINUOUS,
                               lognormal_endpoints=_NEPHRO_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_NEPHRO_ENDPOINT_PATTERNS,
                              arm_compiled=_NEPHRO_ARM_COMPILED,
                              continuous_endpoints=_NEPHRO_CONTINUOUS,
                              lognormal_endpoints=_NEPHRO_LOGNORMAL)
