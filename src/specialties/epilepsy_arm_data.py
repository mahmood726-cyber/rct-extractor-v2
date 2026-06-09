"""
Arm-level / 2x2 + continuous extraction for epilepsy / AED trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with epilepsy
endpoints and antiepileptic-drug / status-epilepticus arm labels:

  binary outcomes (seizure freedom, >=50% responder, treatment withdrawal,
    adverse event, seizure cessation, recurrence, adherence, retention) -> 2x2
    events/N per arm
  continuous (time to seizure cessation, quality of life -> mean+SD / median+IQR;
    seizure frequency -> log-normal / count, pool on the log scale as a ratio,
    not as a raw mean difference).
"""
import re
from typing import Dict, List

from .epilepsy import get_epilepsy_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Epilepsy endpoint patterns (string, endpoint) across all subspecialties.
_EPILEPSY_ENDPOINT_PATTERNS = []
for _sub in ("efficacy", "tolerability", "status_epilepticus", "treatment_gap"):
    _EPILEPSY_ENDPOINT_PATTERNS.extend(get_epilepsy_endpoint_patterns(_sub))

# Antiepileptic-drug / status-epilepticus arm labels. Full names case-insensitive;
# bare UPPERCASE abbreviations CASE-SENSITIVE (so a stray lowercase token won't match).
_EPILEPSY_ARM_FULL = [
    # chronic AEDs
    (r"carbamazepine", "carbamazepine"),
    (r"sodium\s+valproate|valproic\s+acid|divalproex|valproate", "valproate"),
    (r"levetiracetam", "levetiracetam"),
    (r"phenobarbit(?:al|one)", "phenobarbital"),
    (r"lamotrigine", "lamotrigine"),
    (r"fosphenytoin", "fosphenytoin"),
    (r"phenytoin", "phenytoin"),
    (r"topiramate", "topiramate"),
    (r"oxcarbazepine", "oxcarbazepine"),
    (r"eslicarbazepine", "eslicarbazepine"),
    (r"gabapentin", "gabapentin"),
    (r"pregabalin", "pregabalin"),
    (r"lacosamide", "lacosamide"),
    (r"zonisamide", "zonisamide"),
    (r"perampanel", "perampanel"),
    (r"brivaracetam", "brivaracetam"),
    (r"ethosuximide", "ethosuximide"),
    (r"clobazam", "clobazam"),
    (r"vigabatrin", "vigabatrin"),
    (r"cenobamate", "cenobamate"),
    # status epilepticus emergency arms
    (r"lorazepam", "lorazepam"),
    (r"diazepam", "diazepam"),
    (r"midazolam", "midazolam"),
    # controls / generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_EPILEPSY_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bCBZ\b", "carbamazepine"),
    (r"\bVPA\b", "valproate"),
    (r"\bLEV\b", "levetiracetam"),
    (r"\bPB\b", "phenobarbital"),
    (r"\bLTG\b", "lamotrigine"),
    (r"\bPHT\b", "phenytoin"),
    (r"\bTPM\b", "topiramate"),
    (r"\bOXC\b", "oxcarbazepine"),
    (r"\bLCM\b", "lacosamide"),
    (r"\bZNS\b", "zonisamide"),
]
_EPILEPSY_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _EPILEPSY_ARM_FULL]
                          + [(re.compile(p), n) for p, n in _EPILEPSY_ARM_ABBREV])

# Epilepsy continuous outcomes; seizure frequency is count / log-normal data
# (over-dispersed seizure counts) and must be pooled on the log scale as a ratio,
# not as a raw mean difference.
_EPILEPSY_CONTINUOUS = {"SEIZURE_FREQUENCY", "TIME_TO_CESSATION", "QUALITY_OF_LIFE"}
_EPILEPSY_LOGNORMAL = {"SEIZURE_FREQUENCY"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_EPILEPSY_ENDPOINT_PATTERNS,
                                arm_compiled=_EPILEPSY_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_EPILEPSY_ENDPOINT_PATTERNS,
                               arm_compiled=_EPILEPSY_ARM_COMPILED,
                               continuous_endpoints=_EPILEPSY_CONTINUOUS,
                               lognormal_endpoints=_EPILEPSY_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_EPILEPSY_ENDPOINT_PATTERNS,
                              arm_compiled=_EPILEPSY_ARM_COMPILED,
                              continuous_endpoints=_EPILEPSY_CONTINUOUS,
                              lognormal_endpoints=_EPILEPSY_LOGNORMAL)
