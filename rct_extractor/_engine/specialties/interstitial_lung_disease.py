"""
Interstitial Lung Disease / Pulmonary Fibrosis Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow. ILD / pulmonary-fibrosis RCTs
(idiopathic pulmonary fibrosis, progressive fibrosing ILD, connective-tissue-
disease ILD; antifibrotics, immunosuppression) report a distinct endpoint
vocabulary - forced vital capacity (FVC) decline, DLCO, disease progression /
progression-free survival, acute exacerbation of IPF, transplant-free survival -
that is NOT covered by the general respiratory specialty (asthma/COPD) or
pulmonary_hypertension.

Subspecialties:
- function: forced vital capacity / percent-predicted FVC, DLCO (diffusing
  capacity) - the continuous lung-function readouts.
- progression: disease progression, >=10% relative FVC decline, progression-free
  survival, time to progression.
- mortality: all-cause / respiratory mortality, transplant-free survival.
- acute_events: acute exacerbation of IPF, respiratory hospitalisation.

Drug / regimen classes (arm labels): antifibrotics (nintedanib, pirfenidone),
corticosteroids, immunosuppressants (azathioprine, mycophenolate,
cyclophosphamide), biologics (rituximab, tocilizumab), N-acetylcysteine, placebo.

Effect measures: progression / mortality / acute exacerbation / hospitalisation
-> RR/OR/HR; FVC / ppFVC / DLCO -> MD/SMD (continuous, natural scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# ILD / PULMONARY-FIBROSIS ENDPOINTS
# ============================================================

INTERSTITIAL_LUNG_DISEASE_ENDPOINTS = {
    # --- function (continuous) ---
    'FVC': {
        'aliases': ['forced vital capacity', 'fvc decline', 'change in fvc', 'fvc',
                    'annual rate of decline in fvc', 'rate of fvc decline'],
        'subspecialty': 'function',
        'measure_types': ['MD', 'SMD']
    },
    'PPFVC': {
        'aliases': ['percent predicted fvc', 'percent-predicted fvc', 'ppfvc',
                    'fvc percent predicted', 'fvc % predicted'],
        'subspecialty': 'function',
        'measure_types': ['MD', 'SMD']
    },
    'DLCO': {
        'aliases': ['diffusing capacity of the lung for carbon monoxide',
                    'diffusing capacity', 'dlco', 'transfer factor', 'tlco'],
        'subspecialty': 'function',
        'measure_types': ['MD', 'SMD']
    },

    # --- progression ---
    'PROGRESSION': {
        'aliases': ['disease progression', 'progression', '10% relative fvc decline',
                    'relative decline in fvc of at least 10', 'absolute fvc decline',
                    'categorical fvc decline'],
        'subspecialty': 'progression',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'PROGRESSION_FREE_SURVIVAL': {
        'aliases': ['progression-free survival', 'progression free survival', 'pfs',
                    'time to progression', 'time to disease progression'],
        'subspecialty': 'progression',
        'measure_types': ['HR', 'RR']
    },

    # --- mortality ---
    'MORTALITY': {
        'aliases': ['all-cause mortality', 'all cause mortality', 'respiratory mortality',
                    'mortality', 'death', 'overall survival'],
        'subspecialty': 'mortality',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'TRANSPLANT_FREE_SURVIVAL': {
        'aliases': ['transplant-free survival', 'transplant free survival',
                    'death or lung transplantation', 'lung-transplant-free survival'],
        'subspecialty': 'mortality',
        'measure_types': ['HR', 'RR']
    },

    # --- acute events ---
    'ACUTE_EXACERBATION': {
        'aliases': ['acute exacerbation of idiopathic pulmonary fibrosis',
                    'acute exacerbation of ipf', 'acute exacerbation', 'acute exacerbations'],
        'subspecialty': 'acute_events',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HOSPITALISATION': {
        'aliases': ['respiratory hospitalisation', 'respiratory hospitalization',
                    'hospitalisation', 'hospitalization', 'hospital admission',
                    'all-cause hospitalisation'],
        'subspecialty': 'acute_events',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# FUNCTION PATTERNS (continuous)
# ============================================================

FUNCTION_PATTERNS = {
    'detection_keywords': [
        r'forced\s+vital\s+capacity|\bfvc\b', r'percent[- ]predicted\s+fvc|\bppfvc\b',
        r'diffusing\s+capacity|\bdlco\b|\btlco\b|transfer\s+factor',
        r'rate\s+of\s+(?:fvc\s+)?decline',
    ],
    'endpoint_patterns': [
        (r'percent[- ]predicted\s+fvc|\bppfvc\b|fvc\s+(?:percent|%)\s+predicted', 'PPFVC'),
        (r'diffusing\s+capacity(?:\s+of\s+the\s+lung)?|\bdlco\b|\btlco\b|transfer\s+factor', 'DLCO'),
        (r'forced\s+vital\s+capacity|\bfvc\b(?:\s+decline)?|(?:annual\s+)?rate\s+of\s+(?:fvc\s+)?decline',
         'FVC'),
    ],
    'context_patterns': [
        r'\bml\b|millilitres?|milliliters?', r'per\s+year|over\s+52\s+weeks', r'mcid',
    ]
}


# ============================================================
# PROGRESSION PATTERNS
# ============================================================

PROGRESSION_PATTERNS = {
    'detection_keywords': [
        r'disease\s+progression', r'progression[- ]free\s+survival|\bpfs\b',
        r'(?:>=?\s*)?10\s*%\s+(?:relative\s+)?(?:fvc\s+)?decline',
        r'time\s+to\s+(?:disease\s+)?progression', r'progressive\s+(?:fibrosing|pulmonary)',
    ],
    'endpoint_patterns': [
        (r'progression[- ]free\s+survival|\bpfs\b|time\s+to\s+(?:disease\s+)?progression',
         'PROGRESSION_FREE_SURVIVAL'),
        (r'disease\s+progression|(?:>=?\s*)?10\s*%\s+relative\s+(?:fvc\s+)?decline|'
         r'(?:absolute|categorical)\s+fvc\s+decline|\bprogression\b', 'PROGRESSION'),
    ],
    'context_patterns': [
        r'composite', r'\d+\s+weeks', r'fibrosing',
    ]
}


# ============================================================
# MORTALITY PATTERNS
# ============================================================

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'all[- ]cause\s+mortality|respiratory\s+mortality', r'transplant[- ]free\s+survival',
        r'\bmortality\b|\bdeath\b', r'death\s+or\s+lung\s+transplant',
    ],
    'endpoint_patterns': [
        (r'transplant[- ]free\s+survival|death\s+or\s+lung\s+transplant(?:ation)?',
         'TRANSPLANT_FREE_SURVIVAL'),
        (r'all[- ]cause\s+mortality|respiratory\s+mortality|overall\s+survival|\bmortality\b|'
         r'\bdeath\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'\d+[- ](?:week|month|year)\s+mortality', r'hazard\s+ratio', r'kaplan[- ]meier',
    ]
}


# ============================================================
# ACUTE EVENTS PATTERNS
# ============================================================

ACUTE_EVENTS_PATTERNS = {
    'detection_keywords': [
        r'acute\s+exacerbation(?:\s+of\s+(?:idiopathic\s+pulmonary\s+fibrosis|ipf))?',
        r'respiratory\s+hospitali[sz]ation', r'hospitali[sz]ation|hospital\s+admission',
    ],
    'endpoint_patterns': [
        (r'acute\s+exacerbation(?:s)?(?:\s+of\s+(?:idiopathic\s+pulmonary\s+fibrosis|ipf))?',
         'ACUTE_EXACERBATION'),
        (r'(?:respiratory\s+|all[- ]cause\s+)?hospitali[sz]ation|hospital\s+admission',
         'HOSPITALISATION'),
    ],
    'context_patterns': [
        r'first\s+acute\s+exacerbation', r'time\s+to', r'\d+\s+weeks',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_interstitial_lung_disease_subspecialty(text: str) -> Tuple[str, float]:
    """Detect ILD / pulmonary-fibrosis trial subspecialty. Returns (subspecialty,
    confidence). Subspecialties: function, progression, mortality, acute_events,
    general_ild."""
    text_lower = text.lower()
    scores = {'function': 0, 'progression': 0, 'mortality': 0, 'acute_events': 0}
    for kw in FUNCTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['function'] += 1
    for kw in PROGRESSION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['progression'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    for kw in ACUTE_EVENTS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['acute_events'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_ild', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_interstitial_lung_disease_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'function': FUNCTION_PATTERNS['endpoint_patterns'],
        'progression': PROGRESSION_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
        'acute_events': ACUTE_EVENTS_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_interstitial_lung_disease_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical ILD endpoint, preferring the LONGEST matching
    alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in INTERSTITIAL_LUNG_DISEASE_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
