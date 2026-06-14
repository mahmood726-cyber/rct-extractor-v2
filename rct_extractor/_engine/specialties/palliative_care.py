"""
Palliative & End-of-Life Care Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow. Palliative-care RCTs (early / specialist
palliative care, advance care planning, symptom-control interventions in advanced
/ life-limiting illness) report a distinct endpoint vocabulary - symptom burden,
quality of life, place of death, aggressive end-of-life care, survival - that is
NOT covered by the oncology specialty (cancer-directed therapy).

Subspecialties:
- symptoms: pain, dyspnoea / breathlessness, total symptom burden (ESAS).
- quality_of_life: health-related quality of life (FACIT / EORTC QLQ-C30 /
  QUAL-E), depression / anxiety (HADS).
- care_utilisation: place of death (home death), hospital admission / ED visit,
  aggressive end-of-life care (ICU / chemotherapy near death), advance-care-
  planning completion (the binary process / utilisation outcomes).
- survival: overall survival / mortality, survival time.

Drug / intervention classes (arm labels): early palliative care, specialist
palliative care, advance care planning, hospice, opioid / morphine, oxygen / fan
therapy, methylnaltrexone, corticosteroid, usual oncology care.

Effect measures: place of death / hospital use / aggressive care / advance-care-
planning / survival -> RR/OR/HR; symptom / QoL / mood / survival-time -> MD/SMD
(continuous, natural scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# PALLIATIVE / END-OF-LIFE ENDPOINTS
# ============================================================

PALLIATIVE_CARE_ENDPOINTS = {
    # --- symptoms (continuous) ---
    'PAIN': {
        'aliases': ['pain intensity', 'pain score', 'average pain', 'worst pain', 'pain'],
        'subspecialty': 'symptoms',
        'measure_types': ['MD', 'SMD']
    },
    'DYSPNOEA': {
        'aliases': ['dyspnoea', 'dyspnea', 'breathlessness', 'dyspnoea intensity',
                    'breathlessness intensity', 'dyspnoea score'],
        'subspecialty': 'symptoms',
        'measure_types': ['MD', 'SMD']
    },
    'SYMPTOM_BURDEN': {
        'aliases': ['symptom burden', 'edmonton symptom assessment', 'esas',
                    'total symptom distress', 'symptom distress score', 'overall symptom burden'],
        'subspecialty': 'symptoms',
        'measure_types': ['MD', 'SMD']
    },

    # --- quality of life (continuous) ---
    'QUALITY_OF_LIFE': {
        'aliases': ['quality of life', 'health-related quality of life',
                    'facit-pal', 'facit', 'eortc qlq-c30', 'qual-e', 'qol'],
        'subspecialty': 'quality_of_life',
        'measure_types': ['MD', 'SMD']
    },
    'MOOD': {
        'aliases': ['hospital anxiety and depression scale', 'hads', 'depression',
                    'anxiety', 'psychological distress', 'depressive symptoms'],
        'subspecialty': 'quality_of_life',
        'measure_types': ['MD', 'SMD']
    },

    # --- care utilisation (ratio) ---
    'HOME_DEATH': {
        'aliases': ['death at home', 'home death', 'died at home', 'place of death',
                    'home as place of death'],
        'subspecialty': 'care_utilisation',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HOSPITAL_ADMISSION': {
        'aliases': ['hospital admission', 'hospitalisation', 'hospitalization',
                    'emergency department visit', 'emergency department visits', 'ed visit'],
        'subspecialty': 'care_utilisation',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'AGGRESSIVE_EOL_CARE': {
        'aliases': ['aggressive end-of-life care', 'aggressive end of life care',
                    'intensive care unit admission', 'icu admission near death',
                    'chemotherapy near the end of life', 'aggressive care'],
        'subspecialty': 'care_utilisation',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ADVANCE_CARE_PLANNING': {
        'aliases': ['advance care planning completion', 'advance directive completion',
                    'documented care preferences', 'advance care planning',
                    'goals-of-care documentation'],
        'subspecialty': 'care_utilisation',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- survival ---
    'SURVIVAL': {
        'aliases': ['overall survival', 'all-cause mortality', 'all cause mortality',
                    'mortality', 'survival', 'death'],
        'subspecialty': 'survival',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'SURVIVAL_TIME': {
        'aliases': ['median survival', 'median overall survival', 'survival time',
                    'median survival time', 'mean survival'],
        'subspecialty': 'survival',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# SYMPTOMS PATTERNS (continuous)
# ============================================================

SYMPTOMS_PATTERNS = {
    'detection_keywords': [
        r'pain\s+(?:intensity|score)|\bpain\b', r'dyspn(?:oe|e)a|breathlessness',
        r'symptom\s+burden|edmonton\s+symptom\s+assessment|\besas\b', r'symptom\s+distress',
    ],
    'endpoint_patterns': [
        (r'(?:total\s+)?symptom\s+(?:burden|distress)|edmonton\s+symptom\s+assessment|\besas\b',
         'SYMPTOM_BURDEN'),
        (r'dyspn(?:oe|e)a(?:\s+intensity|\s+score)?|breathlessness(?:\s+intensity)?', 'DYSPNOEA'),
        (r'(?:average\s+|worst\s+)?pain(?:\s+intensity|\s+score)?', 'PAIN'),
    ],
    'context_patterns': [
        r'numeric(?:al)?\s+rating\s+scale', r'\d+\s+points', r'advanced\s+(?:cancer|illness)',
    ]
}


# ============================================================
# QUALITY OF LIFE PATTERNS (continuous)
# ============================================================

QUALITY_OF_LIFE_PATTERNS = {
    'detection_keywords': [
        r'quality\s+of\s+life|health[- ]related\s+quality\s+of\s+life',
        r'facit(?:[- ]pal)?|eortc\s+qlq[- ]c30|qual[- ]e',
        r'hospital\s+anxiety\s+and\s+depression|\bhads\b', r'depression|anxiety',
    ],
    'endpoint_patterns': [
        (r'hospital\s+anxiety\s+and\s+depression(?:\s+scale)?|\bhads\b|depressive\s+symptoms|'
         r'depression|anxiety|psychological\s+distress', 'MOOD'),
        (r'(?:health[- ]related\s+)?quality\s+of\s+life|facit(?:[- ]pal)?|eortc\s+qlq[- ]c30|qual[- ]e',
         'QUALITY_OF_LIFE'),
    ],
    'context_patterns': [
        r'change\s+from\s+baseline', r'\d+\s+weeks', r'higher\s+scores',
    ]
}


# ============================================================
# CARE UTILISATION PATTERNS (ratio)
# ============================================================

CARE_UTILISATION_PATTERNS = {
    'detection_keywords': [
        r'(?:death\s+at\s+home|home\s+death|place\s+of\s+death)',
        r'hospital\s+admission|hospitali[sz]ation|emergency\s+department\s+visit',
        r'aggressive\s+(?:end[- ]of[- ]life\s+)?care|intensive\s+care\s+unit\s+admission|'
        r'chemotherapy\s+near\s+(?:the\s+)?end\s+of\s+life',
        r'advance\s+care\s+planning|advance\s+directive|goals[- ]of[- ]care',
    ],
    'endpoint_patterns': [
        (r'advance\s+care\s+planning(?:\s+completion)?|advance\s+directive(?:\s+completion)?|'
         r'documented\s+(?:care\s+)?preferences|goals[- ]of[- ]care\s+documentation',
         'ADVANCE_CARE_PLANNING'),
        (r'aggressive\s+(?:end[- ]of[- ]life\s+)?care|(?:intensive\s+care\s+unit|icu)\s+admission|'
         r'chemotherapy\s+near\s+(?:the\s+)?end\s+of\s+life', 'AGGRESSIVE_EOL_CARE'),
        (r'(?:death\s+at\s+home|home\s+death|died\s+at\s+home|home\s+as\s+place\s+of\s+death|'
         r'place\s+of\s+death)', 'HOME_DEATH'),
        (r'hospital\s+admission|hospitali[sz]ation|emergency\s+department\s+visits?|\bed\s+visits?\b',
         'HOSPITAL_ADMISSION'),
    ],
    'context_patterns': [
        r'last\s+(?:30\s+days|month)\s+of\s+life', r'preferred\s+place', r'within\s+\d+\s+days',
    ]
}


# ============================================================
# SURVIVAL PATTERNS
# ============================================================

SURVIVAL_PATTERNS = {
    'detection_keywords': [
        r'overall\s+survival|all[- ]cause\s+mortality|\bmortality\b',
        r'median\s+(?:overall\s+)?survival|survival\s+time', r'\bsurvival\b',
    ],
    'endpoint_patterns': [
        (r'median\s+(?:overall\s+)?survival(?:\s+time)?|survival\s+time|mean\s+survival',
         'SURVIVAL_TIME'),
        (r'overall\s+survival|all[- ]cause\s+mortality|\bmortality\b|\bsurvival\b|\bdeath\b',
         'SURVIVAL'),
    ],
    'context_patterns': [
        r'hazard\s+ratio', r'\d+[- ](?:day|month)\s+survival', r'kaplan[- ]meier',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_palliative_care_subspecialty(text: str) -> Tuple[str, float]:
    """Detect palliative/end-of-life trial subspecialty. Returns (subspecialty,
    confidence). Subspecialties: symptoms, quality_of_life, care_utilisation,
    survival, general_palliative."""
    text_lower = text.lower()
    scores = {'symptoms': 0, 'quality_of_life': 0, 'care_utilisation': 0, 'survival': 0}
    for kw in SYMPTOMS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['symptoms'] += 1
    for kw in QUALITY_OF_LIFE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['quality_of_life'] += 1
    for kw in CARE_UTILISATION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['care_utilisation'] += 1
    for kw in SURVIVAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['survival'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_palliative', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_palliative_care_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'symptoms': SYMPTOMS_PATTERNS['endpoint_patterns'],
        'quality_of_life': QUALITY_OF_LIFE_PATTERNS['endpoint_patterns'],
        'care_utilisation': CARE_UTILISATION_PATTERNS['endpoint_patterns'],
        'survival': SURVIVAL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_palliative_care_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical palliative-care endpoint, preferring the LONGEST
    matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in PALLIATIVE_CARE_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
