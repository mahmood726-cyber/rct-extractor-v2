"""
Geriatrics & Frailty Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow. Geriatric-medicine RCTs (comprehensive
geriatric assessment, exercise / multicomponent interventions, deprescribing,
falls prevention, delirium prevention in older / frail adults) report a distinct
endpoint vocabulary - falls / fallers, incident delirium, frailty reversal,
institutionalisation - that is NOT covered by the existing disease specialties.

Subspecialties:
- falls: falls / fall rate, proportion of fallers, fall-related injury / fracture.
- cognition: incident / postoperative delirium, cognitive function (MMSE / MoCA).
- function: physical performance (SPPB / gait speed / grip strength), frailty
  status / reversal, activities of daily living (ADL / IADL).
- outcomes: all-cause mortality, hospitalisation / readmission,
  institutionalisation (nursing- / care-home admission).

Drug / intervention classes (arm labels): comprehensive geriatric assessment,
exercise / physical activity, multifactorial / multicomponent intervention,
vitamin D, medication review / deprescribing, nutritional supplementation,
usual care.

Effect measures: falls / fallers / injury / delirium / frailty / mortality /
hospitalisation / institutionalisation -> RR/IRR/OR/HR; cognitive & physical
function / ADL -> MD/SMD (continuous, natural scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# GERIATRICS / FRAILTY ENDPOINTS
# ============================================================

GERIATRICS_FRAILTY_ENDPOINTS = {
    # --- falls ---
    'FALLS': {
        'aliases': ['rate of falls', 'fall rate', 'number of falls', 'falls',
                    'incidence of falls', 'fall incidence'],
        'subspecialty': 'falls',
        'measure_types': ['RR', 'IRR', 'HR']
    },
    'FALLERS': {
        'aliases': ['proportion of fallers', 'number of fallers', 'fallers',
                    'recurrent fallers', 'at least one fall', 'one or more falls'],
        'subspecialty': 'falls',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'FALL_INJURY': {
        'aliases': ['fall-related injury', 'injurious falls', 'fall-related fracture',
                    'fall-related injuries', 'injurious fall', 'serious fall injury'],
        'subspecialty': 'falls',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- cognition ---
    'DELIRIUM': {
        'aliases': ['postoperative delirium', 'incident delirium', 'delirium incidence',
                    'delirium', 'in-hospital delirium'],
        'subspecialty': 'cognition',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'COGNITIVE_FUNCTION': {
        'aliases': ['mini-mental state examination', 'mmse', 'montreal cognitive assessment',
                    'moca', 'cognitive function', 'cognitive score'],
        'subspecialty': 'cognition',
        'measure_types': ['MD', 'SMD']
    },

    # --- function ---
    'PHYSICAL_FUNCTION': {
        'aliases': ['short physical performance battery', 'sppb', 'gait speed', 'walking speed',
                    'grip strength', 'handgrip strength', 'physical performance', 'timed up and go',
                    'timed up-and-go'],
        'subspecialty': 'function',
        'measure_types': ['MD', 'SMD']
    },
    'FRAILTY': {
        'aliases': ['frailty status', 'frailty reversal', 'frailty', 'frail',
                    'functional decline', 'frailty index'],
        'subspecialty': 'function',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ADL': {
        'aliases': ['activities of daily living', 'instrumental activities of daily living',
                    'adl', 'iadl', 'barthel index', 'functional dependency'],
        'subspecialty': 'function',
        'measure_types': ['MD', 'SMD']
    },

    # --- outcomes ---
    'MORTALITY': {
        'aliases': ['all-cause mortality', 'all cause mortality', 'mortality', 'death',
                    'overall survival'],
        'subspecialty': 'outcomes',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HOSPITALISATION': {
        'aliases': ['hospitalisation', 'hospitalization', 'hospital admission',
                    'unplanned readmission', 'readmission', 'hospital readmission'],
        'subspecialty': 'outcomes',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'INSTITUTIONALISATION': {
        'aliases': ['institutionalisation', 'institutionalization', 'nursing-home admission',
                    'nursing home admission', 'care-home admission', 'care home admission',
                    'long-term care admission'],
        'subspecialty': 'outcomes',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# FALLS PATTERNS
# ============================================================

FALLS_PATTERNS = {
    'detection_keywords': [
        r'(?:rate|number|incidence)\s+of\s+falls|fall\s+rate|\bfalls\b',
        r'(?:proportion\s+of\s+|recurrent\s+)?fallers?',
        r'fall[- ]related\s+(?:injur|fractur)', r'injurious\s+falls?',
    ],
    'endpoint_patterns': [
        (r'fall[- ]related\s+(?:injur(?:y|ies)|fractures?)|injurious\s+falls?|serious\s+fall\s+injury',
         'FALL_INJURY'),
        (r'(?:proportion\s+of\s+|recurrent\s+)?fallers?|at\s+least\s+one\s+fall|one\s+or\s+more\s+falls',
         'FALLERS'),
        (r'(?:rate|number|incidence)\s+of\s+falls|fall\s+rate|fall\s+incidence|\bfalls\b', 'FALLS'),
    ],
    'context_patterns': [
        r'per\s+person[- ]year', r'rate\s+ratio', r'community[- ]dwelling',
    ]
}


# ============================================================
# COGNITION PATTERNS
# ============================================================

COGNITION_PATTERNS = {
    'detection_keywords': [
        r'(?:postoperative|incident|in[- ]hospital)\s+delirium|\bdelirium\b',
        r'mini[- ]mental\s+state|\bmmse\b', r'montreal\s+cognitive\s+assessment|\bmoca\b',
        r'cognitive\s+(?:function|impairment|decline)',
    ],
    'endpoint_patterns': [
        (r'(?:postoperative|incident|in[- ]hospital)\s+delirium|delirium\s+incidence|\bdelirium\b',
         'DELIRIUM'),
        (r'mini[- ]mental\s+state(?:\s+examination)?|\bmmse\b|montreal\s+cognitive\s+assessment|\bmoca\b|'
         r'cognitive\s+(?:function|score)', 'COGNITIVE_FUNCTION'),
    ],
    'context_patterns': [
        r'cam(?:[- ]icu)?', r'\d+\s+points', r'baseline',
    ]
}


# ============================================================
# FUNCTION PATTERNS
# ============================================================

FUNCTION_PATTERNS = {
    'detection_keywords': [
        r'short\s+physical\s+performance\s+battery|\bsppb\b', r'gait\s+speed|walking\s+speed',
        r'(?:hand)?grip\s+strength', r'frailty|\bfrail\b', r'activities\s+of\s+daily\s+living|\biadl\b|\badl\b',
        r'timed\s+up[- ]and[- ]go|functional\s+decline',
    ],
    'endpoint_patterns': [
        (r'(?:instrumental\s+)?activities\s+of\s+daily\s+living|\biadl\b|\badl\b|barthel\s+index|'
         r'functional\s+dependency', 'ADL'),
        (r'frailty\s+(?:status|reversal|index)|\bfrailty\b|\bfrail\b|functional\s+decline', 'FRAILTY'),
        (r'short\s+physical\s+performance\s+battery|\bsppb\b|gait\s+speed|walking\s+speed|'
         r'(?:hand)?grip\s+strength|physical\s+performance|timed\s+up[- ]and[- ]go', 'PHYSICAL_FUNCTION'),
    ],
    'context_patterns': [
        r'm/s|metres?\s+per\s+second', r'\bkg\b', r'\d+\s+points',
    ]
}


# ============================================================
# OUTCOMES PATTERNS
# ============================================================

OUTCOMES_PATTERNS = {
    'detection_keywords': [
        r'all[- ]cause\s+mortality|\bmortality\b', r'hospitali[sz]ation|hospital\s+admission',
        r'(?:unplanned\s+)?readmission', r'institutionali[sz]ation|nursing[- ]home|care[- ]home',
    ],
    'endpoint_patterns': [
        (r'institutionali[sz]ation|(?:nursing|care)[- ]home\s+admission|long[- ]term\s+care\s+admission',
         'INSTITUTIONALISATION'),
        (r'(?:hospital\s+|unplanned\s+)?readmission|hospitali[sz]ation|hospital\s+admission',
         'HOSPITALISATION'),
        (r'all[- ]cause\s+mortality|overall\s+survival|\bmortality\b|\bdeath\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'\d+[- ](?:month|year)\s+mortality', r'community[- ]dwelling', r'discharge',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_geriatrics_frailty_subspecialty(text: str) -> Tuple[str, float]:
    """Detect geriatrics/frailty trial subspecialty. Returns (subspecialty,
    confidence). Subspecialties: falls, cognition, function, outcomes,
    general_geriatric."""
    text_lower = text.lower()
    scores = {'falls': 0, 'cognition': 0, 'function': 0, 'outcomes': 0}
    for kw in FALLS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['falls'] += 1
    for kw in COGNITION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['cognition'] += 1
    for kw in FUNCTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['function'] += 1
    for kw in OUTCOMES_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['outcomes'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_geriatric', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_geriatrics_frailty_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'falls': FALLS_PATTERNS['endpoint_patterns'],
        'cognition': COGNITION_PATTERNS['endpoint_patterns'],
        'function': FUNCTION_PATTERNS['endpoint_patterns'],
        'outcomes': OUTCOMES_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_geriatrics_frailty_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical geriatrics/frailty endpoint, preferring the LONGEST
    matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in GERIATRICS_FRAILTY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
