"""
Bronchiectasis (non-CF) Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow. Non-cystic-fibrosis bronchiectasis RCTs
(inhaled antibiotics, macrolide maintenance, DPP-1 inhibitors, mucoactive agents,
airway clearance) report a distinct endpoint vocabulary - exacerbation frequency /
rate, time to first exacerbation, Pseudomonas eradication, quality of life
(QOL-B / SGRQ) - that is NOT covered by the general respiratory specialty (asthma/
COPD) or pneumonia.

Subspecialties:
- exacerbation: exacerbation frequency / annual rate, time to first exacerbation,
  severe exacerbation, hospitalisation.
- microbiology: Pseudomonas aeruginosa eradication, bacterial load / colony count,
  new infection.
- function: FEV1 / percent-predicted FEV1, disease-specific quality of life
  (QOL-B respiratory symptoms, SGRQ).
- symptoms: 24-hour sputum volume, cough (Leicester Cough Questionnaire).

Drug / regimen classes (arm labels): inhaled antibiotics (tobramycin, colistin,
aztreonam, gentamicin, ciprofloxacin dry powder), macrolides (azithromycin,
erythromycin, clarithromycin), DPP-1 inhibitor (brensocatib), mucoactive
(hypertonic saline, mannitol, carbocisteine), airway clearance, placebo.

Effect measures: exacerbation / eradication / hospitalisation -> RR/IRR/HR;
FEV1 / QoL / bacterial load / sputum / cough -> MD/SMD (continuous, natural scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# BRONCHIECTASIS ENDPOINTS
# ============================================================

BRONCHIECTASIS_ENDPOINTS = {
    # --- exacerbation ---
    'EXACERBATION': {
        'aliases': ['annual exacerbation rate', 'exacerbation frequency', 'exacerbation rate',
                    'frequency of exacerbations', 'number of exacerbations', 'pulmonary exacerbation',
                    'rate of exacerbations'],
        'subspecialty': 'exacerbation',
        'measure_types': ['RR', 'IRR', 'HR']
    },
    'TIME_TO_EXACERBATION': {
        'aliases': ['time to first exacerbation', 'time to first pulmonary exacerbation',
                    'time to next exacerbation'],
        'subspecialty': 'exacerbation',
        'measure_types': ['HR', 'RR']
    },
    'SEVERE_EXACERBATION': {
        'aliases': ['severe exacerbation', 'exacerbation requiring hospitalisation',
                    'exacerbation requiring hospitalization', 'hospitalised exacerbation',
                    'severe pulmonary exacerbation'],
        'subspecialty': 'exacerbation',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HOSPITALISATION': {
        'aliases': ['hospitalisation', 'hospitalization', 'hospital admission',
                    'respiratory hospitalisation', 'admission to hospital'],
        'subspecialty': 'exacerbation',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- microbiology ---
    'PSEUDOMONAS_ERADICATION': {
        'aliases': ['pseudomonas aeruginosa eradication', 'pseudomonas eradication',
                    'p. aeruginosa eradication', 'bacterial eradication', 'microbiological eradication',
                    'eradication of pseudomonas'],
        'subspecialty': 'microbiology',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'BACTERIAL_LOAD': {
        'aliases': ['bacterial load', 'sputum bacterial load', 'bacterial density',
                    'colony-forming units', 'sputum colony count', 'sputum density'],
        'subspecialty': 'microbiology',
        'measure_types': ['MD', 'SMD']
    },

    # --- function ---
    'FEV1': {
        'aliases': ['percent predicted fev1', 'percent-predicted fev1', 'ppfev1',
                    'forced expiratory volume in 1 second', 'forced expiratory volume', 'fev1'],
        'subspecialty': 'function',
        'measure_types': ['MD', 'SMD']
    },
    'QUALITY_OF_LIFE': {
        'aliases': ['qol-b respiratory symptoms', 'qol-b respiratory symptoms score',
                    'quality of life bronchiectasis', 'qol-b', 'st george respiratory questionnaire',
                    'sgrq', 'quality of life', 'health-related quality of life'],
        'subspecialty': 'function',
        'measure_types': ['MD', 'SMD']
    },

    # --- symptoms ---
    'SPUTUM_VOLUME': {
        'aliases': ['24-hour sputum volume', '24 hour sputum volume', 'sputum volume',
                    'daily sputum volume', 'sputum weight'],
        'subspecialty': 'symptoms',
        'measure_types': ['MD', 'SMD']
    },
    'COUGH': {
        'aliases': ['leicester cough questionnaire', 'lcq', 'cough severity', 'cough score',
                    'cough symptom score'],
        'subspecialty': 'symptoms',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# EXACERBATION PATTERNS
# ============================================================

EXACERBATION_PATTERNS = {
    'detection_keywords': [
        r'(?:annual\s+)?exacerbation\s+(?:rate|frequency)', r'frequency\s+of\s+exacerbations',
        r'time\s+to\s+(?:first\s+)?(?:pulmonary\s+)?exacerbation', r'pulmonary\s+exacerbation',
        r'severe\s+exacerbation|exacerbation\s+requiring\s+hospitali[sz]ation',
    ],
    'endpoint_patterns': [
        (r'time\s+to\s+(?:first\s+|next\s+)?(?:pulmonary\s+)?exacerbation', 'TIME_TO_EXACERBATION'),
        (r'severe\s+(?:pulmonary\s+)?exacerbation|exacerbation\s+requiring\s+hospitali[sz]ation|'
         r'hospitali[sz]ed\s+exacerbation', 'SEVERE_EXACERBATION'),
        (r'(?:annual\s+)?exacerbation\s+(?:rate|frequency)|frequency\s+of\s+exacerbations|'
         r'(?:number|rate)\s+of\s+exacerbations|pulmonary\s+exacerbation', 'EXACERBATION'),
        (r'respiratory\s+hospitali[sz]ation|hospitali[sz]ation|hospital\s+admission|'
         r'admission\s+to\s+hospital', 'HOSPITALISATION'),
    ],
    'context_patterns': [
        r'per\s+(?:year|patient[- ]year)', r'rate\s+ratio', r'over\s+\d+\s+(?:weeks|months)',
    ]
}


# ============================================================
# MICROBIOLOGY PATTERNS
# ============================================================

MICROBIOLOGY_PATTERNS = {
    'detection_keywords': [
        r'pseudomonas\s+aeruginosa', r'(?:bacterial|microbiological)\s+eradication',
        r'sputum\s+(?:bacterial\s+)?(?:load|density)', r'colony[- ]forming\s+units|\bcfu\b',
        r'new\s+infection|chronic\s+infection',
    ],
    'endpoint_patterns': [
        (r'(?:pseudomonas\s+aeruginosa|p\.?\s*aeruginosa|pseudomonas|bacterial|microbiological)\s+'
         r'eradication|eradication\s+of\s+pseudomonas', 'PSEUDOMONAS_ERADICATION'),
        (r'(?:sputum\s+)?(?:bacterial\s+)?(?:load|density)|colony[- ]forming\s+units|'
         r'(?:sputum\s+)?colony\s+count', 'BACTERIAL_LOAD'),
    ],
    'context_patterns': [
        r'log10', r'cfu/(?:g|ml)', r'chronic\s+pseudomonas',
    ]
}


# ============================================================
# FUNCTION PATTERNS (continuous)
# ============================================================

FUNCTION_PATTERNS = {
    'detection_keywords': [
        r'percent[- ]predicted\s+fev1|\bppfev1\b|\bfev1\b|forced\s+expiratory\s+volume',
        r'qol[- ]b|quality\s+of\s+life\s+bronchiectasis',
        r'st\.?\s+george(?:\'s)?\s+respiratory\s+questionnaire|\bsgrq\b',
        r'health[- ]related\s+quality\s+of\s+life',
    ],
    'endpoint_patterns': [
        (r'qol[- ]b(?:\s+respiratory\s+symptoms)?(?:\s+score)?|quality\s+of\s+life\s+bronchiectasis|'
         r'st\.?\s+george(?:\'s)?\s+respiratory\s+questionnaire|\bsgrq\b|'
         r'(?:health[- ]related\s+)?quality\s+of\s+life', 'QUALITY_OF_LIFE'),
        (r'percent[- ]predicted\s+fev1|\bppfev1\b|forced\s+expiratory\s+volume(?:\s+in\s+1\s+second)?|'
         r'\bfev1\b', 'FEV1'),
    ],
    'context_patterns': [
        r'litres?|liters?|ml', r'points?', r'minimal\s+clinically\s+important\s+difference',
    ]
}


# ============================================================
# SYMPTOMS PATTERNS (continuous)
# ============================================================

SYMPTOMS_PATTERNS = {
    'detection_keywords': [
        r'(?:24[- ]hour\s+|daily\s+)?sputum\s+(?:volume|weight)',
        r'leicester\s+cough\s+questionnaire|\blcq\b', r'cough\s+(?:severity|score|symptom)',
    ],
    'endpoint_patterns': [
        (r'leicester\s+cough\s+questionnaire|\blcq\b|cough\s+(?:severity|score|symptom\s+score)',
         'COUGH'),
        (r'(?:24[- ]hour\s+|daily\s+)?sputum\s+(?:volume|weight)', 'SPUTUM_VOLUME'),
    ],
    'context_patterns': [
        r'\bml\b|grams?', r'over\s+24\s+hours', r'change\s+from\s+baseline',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_bronchiectasis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect bronchiectasis trial subspecialty. Returns (subspecialty,
    confidence). Subspecialties: exacerbation, microbiology, function, symptoms,
    general_bronchiectasis."""
    text_lower = text.lower()
    scores = {'exacerbation': 0, 'microbiology': 0, 'function': 0, 'symptoms': 0}
    for kw in EXACERBATION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['exacerbation'] += 1
    for kw in MICROBIOLOGY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['microbiology'] += 1
    for kw in FUNCTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['function'] += 1
    for kw in SYMPTOMS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['symptoms'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_bronchiectasis', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_bronchiectasis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'exacerbation': EXACERBATION_PATTERNS['endpoint_patterns'],
        'microbiology': MICROBIOLOGY_PATTERNS['endpoint_patterns'],
        'function': FUNCTION_PATTERNS['endpoint_patterns'],
        'symptoms': SYMPTOMS_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_bronchiectasis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical bronchiectasis endpoint, preferring the LONGEST
    matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in BRONCHIECTASIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
