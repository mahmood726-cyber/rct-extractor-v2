"""
Venous Thromboembolism (VTE) Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow as the hypertension, diabetes and
dyslipidaemia profiles. VTE RCTs (anticoagulation for deep-vein thrombosis and
pulmonary embolism, and thromboprophylaxis) report a distinct endpoint vocabulary
(recurrent VTE, DVT, PE, major / clinically-relevant non-major bleeding,
post-thrombotic syndrome) that the generic effect-size engine does not recognise.

Subspecialties:
- treatment (anticoagulation for established VTE): recurrent VTE, recurrent DVT,
  recurrent / fatal PE, VTE-related death.
- prevention (thromboprophylaxis in surgical / medical / cancer patients):
  incident VTE, symptomatic VTE, asymptomatic DVT.
- bleeding (the dominant safety trade-off): major bleeding, clinically relevant
  non-major (CRNM) bleeding, intracranial haemorrhage, fatal bleeding.
- mortality: all-cause mortality, PE-related / VTE-related death.

Drug classes (arm labels): direct oral anticoagulants / DOACs (apixaban,
rivaroxaban, edoxaban, dabigatran, betrixaban), vitamin-K antagonists (warfarin,
acenocoumarol), low-molecular-weight heparin (enoxaparin, dalteparin, tinzaparin,
nadroparin), unfractionated heparin, fondaparinux, aspirin, placebo, standard care.

Effect measures: VTE endpoints are events -> binary (RR/OR/RD) or time-to-event
(HR). Post-thrombotic syndrome scores are occasionally continuous but are pooled
here as event proportions (the usual reported form).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# VTE ENDPOINTS
# ============================================================

VTE_ENDPOINTS = {
    # --- treatment (recurrent / established VTE) ---
    'RECURRENT_VTE': {
        'aliases': ['recurrent venous thromboembolism', 'recurrent vte',
                    'vte recurrence', 'recurrence of venous thromboembolism',
                    'symptomatic recurrent venous thromboembolism', 'recurrent thromboembolism',
                    'venous thromboembolism recurrence'],
        'subspecialty': 'treatment',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'RECURRENT_DVT': {
        'aliases': ['recurrent deep vein thrombosis', 'recurrent deep-vein thrombosis',
                    'recurrent dvt', 'recurrent proximal dvt'],
        'subspecialty': 'treatment',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'RECURRENT_PE': {
        'aliases': ['recurrent pulmonary embolism', 'recurrent pe', 'fatal pulmonary embolism',
                    'fatal pe', 'nonfatal pulmonary embolism', 'non-fatal pulmonary embolism',
                    'pulmonary embolism recurrence'],
        'subspecialty': 'treatment',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- prevention (thromboprophylaxis) ---
    'INCIDENT_VTE': {
        'aliases': ['venous thromboembolism', 'symptomatic venous thromboembolism',
                    'symptomatic vte', 'incident venous thromboembolism', 'any venous thromboembolism',
                    'total venous thromboembolism', 'composite venous thromboembolism'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'DVT': {
        'aliases': ['deep vein thrombosis', 'deep-vein thrombosis', 'proximal deep vein thrombosis',
                    'asymptomatic deep vein thrombosis', 'distal deep vein thrombosis', 'dvt'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'PE': {
        'aliases': ['pulmonary embolism', 'symptomatic pulmonary embolism',
                    'nonfatal pulmonary embolism', 'pe'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- bleeding (safety) ---
    'MAJOR_BLEEDING': {
        'aliases': ['major bleeding', 'major haemorrhage', 'major hemorrhage',
                    'major bleeding event', 'major bleed', 'isth major bleeding'],
        'subspecialty': 'bleeding',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CRNM_BLEEDING': {
        'aliases': ['clinically relevant non-major bleeding', 'clinically relevant nonmajor bleeding',
                    'crnm bleeding', 'clinically relevant non-major haemorrhage',
                    'non-major bleeding', 'minor bleeding'],
        'subspecialty': 'bleeding',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'MAJOR_OR_CRNM_BLEEDING': {
        'aliases': ['major or clinically relevant non-major bleeding',
                    'major and clinically relevant non-major bleeding',
                    'composite bleeding', 'any bleeding', 'total bleeding'],
        'subspecialty': 'bleeding',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'INTRACRANIAL_HEMORRHAGE': {
        'aliases': ['intracranial haemorrhage', 'intracranial hemorrhage', 'intracranial bleeding',
                    'ich', 'haemorrhagic stroke', 'hemorrhagic stroke'],
        'subspecialty': 'bleeding',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'FATAL_BLEEDING': {
        'aliases': ['fatal bleeding', 'fatal haemorrhage', 'fatal hemorrhage',
                    'bleeding-related death'],
        'subspecialty': 'bleeding',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- mortality ---
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'all cause mortality', 'total mortality',
                    'death from any cause', 'overall mortality', 'all-cause death',
                    'mortality'],
        'subspecialty': 'mortality',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'PE_RELATED_DEATH': {
        'aliases': ['pulmonary embolism-related death', 'pe-related death',
                    'vte-related death', 'venous thromboembolism-related death',
                    'fatal venous thromboembolism', 'death from pulmonary embolism'],
        'subspecialty': 'mortality',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'POST_THROMBOTIC_SYNDROME': {
        'aliases': ['post-thrombotic syndrome', 'postthrombotic syndrome', 'pts',
                    'post thrombotic syndrome'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# TREATMENT PATTERNS (anticoagulation for established VTE)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'recurrent\s+venous\s+thromboembolism|recurrent\s+vte|vte\s+recurrence',
        r'recurrent\s+(?:deep[- ]vein\s+thrombosis|dvt)',
        r'recurrent\s+(?:pulmonary\s+embolism|pe)', r'extended\s+anticoagulation',
        r'treatment\s+of\s+(?:acute\s+)?venous\s+thromboembolism',
        r'post[- ]?thrombotic\s+syndrome', r'anticoagulation\s+(?:duration|therapy)',
    ],
    'endpoint_patterns': [
        (r'recurrent\s+venous\s+thromboembolism|recurrent\s+vte|'
         r'(?:symptomatic\s+)?venous\s+thromboembolism\s+recurrence|recurrent\s+thromboembolism',
         'RECURRENT_VTE'),
        (r'recurrent\s+(?:proximal\s+)?(?:deep[- ]vein\s+thrombosis|dvt)', 'RECURRENT_DVT'),
        (r'(?:fatal\s+|nonfatal\s+|non[- ]fatal\s+)?recurrent\s+pulmonary\s+embolism|'
         r'recurrent\s+pe|pulmonary\s+embolism\s+recurrence', 'RECURRENT_PE'),
        (r'post[- ]?thrombotic\s+syndrome', 'POST_THROMBOTIC_SYNDROME'),
    ],
    'context_patterns': [
        r'hazard\s+ratio|\bhr\b', r'\d+\s*months?\s+of\s+(?:anticoagulation|treatment)',
        r'index\s+event', r'unprovoked',
    ]
}


# ============================================================
# PREVENTION PATTERNS (thromboprophylaxis)
# ============================================================

PREVENTION_PATTERNS = {
    'detection_keywords': [
        r'thromboprophylaxis', r'venous\s+thromboembolism\s+prophylaxis',
        r'vte\s+prophylaxis', r'prevention\s+of\s+venous\s+thromboembolism',
        r'prophylactic\s+anticoagulation', r'extended\s+prophylaxis',
        r'post[- ]operative\s+(?:dvt|vte)', r'surgical\s+thromboprophylaxis',
    ],
    'endpoint_patterns': [
        # `(?<!recurrent )` keeps these PREVENTION (incident) endpoints from
        # swallowing the tail of a TREATMENT phrase ("recurrent venous
        # thromboembolism" must stay RECURRENT_VTE, not INCIDENT_VTE).
        (r'(?:symptomatic\s+|incident\s+|any\s+|total\s+|composite\s+)?'
         r'(?<!recurrent )venous\s+thromboembolism|symptomatic\s+vte', 'INCIDENT_VTE'),
        (r'(?:proximal\s+|distal\s+|asymptomatic\s+|symptomatic\s+)?'
         r'(?<!recurrent )deep[- ]vein\s+thrombosis|(?<!recurrent )\bdvt\b', 'DVT'),
        (r'(?:symptomatic\s+|nonfatal\s+)?(?<!recurrent )pulmonary\s+embolism|'
         r'(?<!recurrent )\bpe\b', 'PE'),
    ],
    'context_patterns': [
        r'venographic|venography', r'after\s+(?:hip|knee)\s+(?:replacement|arthroplasty|surgery)',
        r'medically\s+ill|surgical\s+patients', r'per[- ]protocol|intention[- ]to[- ]treat',
    ]
}


# ============================================================
# BLEEDING PATTERNS (safety)
# ============================================================

BLEEDING_PATTERNS = {
    'detection_keywords': [
        r'major\s+bleeding|major\s+h[ae]morrhage', r'clinically\s+relevant\s+non[- ]?major',
        r'\bcrnm\b', r'intracranial\s+h[ae]morrhage', r'fatal\s+bleeding|fatal\s+h[ae]morrhage',
        r'gastrointestinal\s+bleeding', r'bleeding\s+(?:event|outcome|risk)',
    ],
    'endpoint_patterns': [
        (r'major\s+(?:or|and)\s+clinically\s+relevant\s+non[- ]?major\s+bleeding|'
         r'composite\s+bleeding|any\s+bleeding|total\s+bleeding', 'MAJOR_OR_CRNM_BLEEDING'),
        (r'clinically\s+relevant\s+non[- ]?major\s+(?:bleeding|h[ae]morrhage)|crnm\s+bleeding|'
         r'non[- ]major\s+bleeding|minor\s+bleeding', 'CRNM_BLEEDING'),
        (r'intracranial\s+(?:h[ae]morrhage|bleeding)|h[ae]morrhagic\s+stroke|\bich\b',
         'INTRACRANIAL_HEMORRHAGE'),
        (r'fatal\s+(?:bleeding|h[ae]morrhage)|bleeding[- ]related\s+death', 'FATAL_BLEEDING'),
        (r'(?:isth\s+)?major\s+(?:bleeding|h[ae]morrhage|bleed)(?:\s+event)?', 'MAJOR_BLEEDING'),
    ],
    'context_patterns': [
        r'isth\s+(?:criteria|definition)', r'hemoglobin\s+drop|h[ae]moglobin\s+(?:fall|decrease)',
        r'transfusion', r'\bsafety\b',
    ]
}


# ============================================================
# MORTALITY PATTERNS
# ============================================================

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'all[- ]cause\s+mortality', r'pulmonary\s+embolism[- ]related\s+death',
        r'(?:pe|vte)[- ]related\s+death', r'fatal\s+(?:pulmonary\s+embolism|venous\s+thromboembolism)',
        r'death\s+from\s+pulmonary\s+embolism',
    ],
    'endpoint_patterns': [
        (r'pulmonary\s+embolism[- ]related\s+death|(?:pe|vte)[- ]related\s+death|'
         r'venous\s+thromboembolism[- ]related\s+death|fatal\s+(?:pulmonary\s+embolism|'
         r'venous\s+thromboembolism)|death\s+from\s+pulmonary\s+embolism', 'PE_RELATED_DEATH'),
        (r'all[- ]cause\s+(?:mortality|death)|total\s+mortality|death\s+from\s+any\s+cause|'
         r'overall\s+mortality', 'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [
        r'hazard\s+ratio|\bhr\b', r'person[- ]years', r'median\s+follow[- ]up',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_venous_thromboembolism_subspecialty(text: str) -> Tuple[str, float]:
    """Detect VTE trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: treatment, prevention, bleeding, mortality,
    general_vte."""
    text_lower = text.lower()
    scores = {'treatment': 0, 'prevention': 0, 'bleeding': 0, 'mortality': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['prevention'] += 1
    for kw in BLEEDING_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['bleeding'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_vte', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_venous_thromboembolism_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'prevention': PREVENTION_PATTERNS['endpoint_patterns'],
        'bleeding': BLEEDING_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_venous_thromboembolism_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical VTE endpoint, preferring the LONGEST matching alias
    so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in VTE_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
