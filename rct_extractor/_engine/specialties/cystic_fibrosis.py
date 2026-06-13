"""
Cystic Fibrosis Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow as the other specialty profiles. CF RCTs
(CFTR modulators, mucoactive / inhaled-antibiotic therapy, nutrition) report a
distinct endpoint vocabulary - percent-predicted FEV1 (ppFEV1), pulmonary
exacerbations, lung clearance index (LCI), sweat chloride, Pseudomonas
eradication, CFQ-R respiratory domain - that is NOT covered by the general
respiratory specialty (asthma / COPD: ACQ, FEV1, exacerbations of a different
phenotype).

Subspecialties:
- pulmonary: ppFEV1 / FEV1, pulmonary exacerbations, lung clearance index,
  respiratory hospitalisation.
- nutrition: BMI / BMI z-score, body weight / weight-for-age.
- microbiology: Pseudomonas aeruginosa eradication / culture conversion, sputum
  bacterial density.
- systemic: sweat chloride concentration, CFQ-R respiratory domain (CFTR-function
  and quality-of-life readouts).

Drug / regimen classes (arm labels): CFTR modulators (elexacaftor/tezacaftor/
ivacaftor [ETI], ivacaftor, lumacaftor/ivacaftor, tezacaftor/ivacaftor),
mucoactive agents (dornase alfa, hypertonic saline, mannitol), inhaled
antibiotics (tobramycin, aztreonam, colistin), read-through (ataluren), placebo.

Effect measures: exacerbation / eradication / hospitalisation -> RR/OR/HR; ppFEV1
/ FEV1 / LCI / sweat chloride / BMI / weight / CFQ-R -> MD/SMD (continuous,
natural scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# CYSTIC-FIBROSIS ENDPOINTS
# ============================================================

CYSTIC_FIBROSIS_ENDPOINTS = {
    # --- pulmonary ---
    'PPFEV1': {
        'aliases': ['absolute change in percent predicted fev1', 'percent predicted fev1',
                    'percent-predicted fev1', 'ppfev1', 'pp fev1', 'fev1 percent predicted',
                    'fev1 % predicted', 'predicted fev1', 'predicted fev'],
        'subspecialty': 'pulmonary',
        'measure_types': ['MD', 'SMD']
    },
    'FEV1': {
        'aliases': ['forced expiratory volume in 1 second', 'forced expiratory volume',
                    'fev1', 'fev-1'],
        'subspecialty': 'pulmonary',
        'measure_types': ['MD', 'SMD']
    },
    'PULMONARY_EXACERBATION': {
        'aliases': ['protocol-defined pulmonary exacerbation', 'acute pulmonary exacerbation',
                    'pulmonary exacerbation', 'pulmonary exacerbations', 'respiratory exacerbation',
                    'exacerbation rate', 'time to first pulmonary exacerbation',
                    'time to first exacerbation'],
        'subspecialty': 'pulmonary',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'LCI': {
        'aliases': ['lung clearance index', 'lci2.5', 'lci 2.5', 'lci'],
        'subspecialty': 'pulmonary',
        'measure_types': ['MD', 'SMD']
    },
    'RESPIRATORY_HOSPITALISATION': {
        'aliases': ['respiratory hospitalisation', 'respiratory hospitalization',
                    'hospitalisation for respiratory', 'hospital admission', 'hospitalisation',
                    'hospitalization', 'intravenous antibiotic course', 'iv antibiotic course'],
        'subspecialty': 'pulmonary',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- nutrition ---
    'BMI': {
        'aliases': ['body mass index', 'body-mass index', 'bmi z-score', 'bmi z score', 'bmi'],
        'subspecialty': 'nutrition',
        'measure_types': ['MD', 'SMD']
    },
    'WEIGHT': {
        'aliases': ['weight-for-age z-score', 'weight for age z-score', 'change in body weight',
                    'body weight', 'weight gain', 'weight'],
        'subspecialty': 'nutrition',
        'measure_types': ['MD', 'SMD']
    },

    # --- microbiology ---
    'PSEUDOMONAS_ERADICATION': {
        'aliases': ['pseudomonas aeruginosa eradication', 'p. aeruginosa eradication',
                    'pseudomonas eradication', 'eradication of pseudomonas', 'culture conversion',
                    'sputum culture conversion', 'microbiological eradication'],
        'subspecialty': 'microbiology',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'SPUTUM_DENSITY': {
        'aliases': ['sputum bacterial density', 'pseudomonas density', 'sputum density',
                    'sputum p. aeruginosa density', 'bacterial density', 'colony-forming units'],
        'subspecialty': 'microbiology',
        'measure_types': ['MD', 'SMD']
    },

    # --- systemic (CFTR function & QoL) ---
    'SWEAT_CHLORIDE': {
        'aliases': ['sweat chloride concentration', 'sweat chloride', 'sweat [cl-]',
                    'sweat cl concentration'],
        'subspecialty': 'systemic',
        'measure_types': ['MD', 'SMD']
    },
    'CFQ_R': {
        'aliases': ['cfq-r respiratory domain score', 'cfq-r respiratory domain', 'cfq-r',
                    'cystic fibrosis questionnaire-revised', 'cystic fibrosis questionnaire',
                    'respiratory domain score'],
        'subspecialty': 'systemic',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# PULMONARY PATTERNS
# ============================================================

PULMONARY_PATTERNS = {
    'detection_keywords': [
        r'percent[- ]predicted\s+fev1|\bppfev1\b|fev1\s+(?:percent|%)\s+predicted',
        r'forced\s+expiratory\s+volume|\bfev1\b',
        r'pulmonary\s+exacerbation', r'lung\s+clearance\s+index|\blci\b',
        r'respiratory\s+hospitali[sz]ation|intravenous\s+antibiotic\s+course',
    ],
    'endpoint_patterns': [
        (r'percent[- ]predicted\s+fev1|\bppfev1\b|pp\s*fev1|fev1\s+(?:percent|%)\s+predicted|'
         r'predicted\s+fev1?', 'PPFEV1'),
        (r'protocol[- ]defined\s+pulmonary\s+exacerbation|(?:acute\s+)?(?:pulmonary|respiratory)\s+'
         r'exacerbation|exacerbation\s+rate|time\s+to\s+first\s+(?:pulmonary\s+)?exacerbation',
         'PULMONARY_EXACERBATION'),
        (r'lung\s+clearance\s+index|\blci\b', 'LCI'),
        (r'respiratory\s+hospitali[sz]ation|hospitali[sz]ation|hospital\s+admission|'
         r'(?:iv|intravenous)\s+antibiotic\s+course', 'RESPIRATORY_HOSPITALISATION'),
        (r'forced\s+expiratory\s+volume(?:\s+in\s+1\s+second)?|\bfev1\b', 'FEV1'),
    ],
    'context_patterns': [
        r'litres?|liters?|ml', r'percentage\s+points?', r'at\s+(?:week|month)\s+\d+',
    ]
}


# ============================================================
# NUTRITION PATTERNS
# ============================================================

NUTRITION_PATTERNS = {
    'detection_keywords': [
        r'body\s+mass\s+index|\bbmi\b', r'weight[- ]for[- ]age', r'body\s+weight|weight\s+gain',
        r'nutritional\s+status',
    ],
    'endpoint_patterns': [
        (r'body[- ]mass\s+index|\bbmi\b(?:\s+z[- ]score)?', 'BMI'),
        (r'weight[- ]for[- ]age\s+z[- ]score|(?:change\s+in\s+)?body\s+weight|weight\s+gain|'
         r'\bweight\b', 'WEIGHT'),
    ],
    'context_patterns': [
        r'kg|kilograms?', r'z[- ]score', r'percentile',
    ]
}


# ============================================================
# MICROBIOLOGY PATTERNS
# ============================================================

MICROBIOLOGY_PATTERNS = {
    'detection_keywords': [
        r'pseudomonas\s+aeruginosa', r'eradication', r'culture\s+conversion',
        r'sputum\s+(?:bacterial\s+)?density', r'colony[- ]forming\s+units|\bcfu\b',
    ],
    'endpoint_patterns': [
        (r'(?:pseudomonas\s+aeruginosa|p\.?\s*aeruginosa|pseudomonas)\s+eradication|'
         r'eradication\s+of\s+pseudomonas|(?:sputum\s+)?culture\s+conversion|'
         r'microbiological\s+eradication', 'PSEUDOMONAS_ERADICATION'),
        (r'sputum\s+(?:bacterial\s+)?density|pseudomonas\s+density|bacterial\s+density|'
         r'colony[- ]forming\s+units', 'SPUTUM_DENSITY'),
    ],
    'context_patterns': [
        r'log10', r'cfu/(?:g|ml)', r'\d+\s+weeks?\s+after',
    ]
}


# ============================================================
# SYSTEMIC PATTERNS (CFTR function & QoL)
# ============================================================

SYSTEMIC_PATTERNS = {
    'detection_keywords': [
        r'sweat\s+chloride', r'cfq[- ]r|cystic\s+fibrosis\s+questionnaire',
        r'respiratory\s+domain\s+score', r'\bcftr\b',
    ],
    'endpoint_patterns': [
        (r'sweat\s+chloride(?:\s+concentration)?|sweat\s+\[?cl', 'SWEAT_CHLORIDE'),
        (r'cfq[- ]r(?:\s+respiratory\s+domain)?(?:\s+score)?|cystic\s+fibrosis\s+questionnaire'
         r'(?:[- ]revised)?|respiratory\s+domain\s+score', 'CFQ_R'),
    ],
    'context_patterns': [
        r'mmol/l', r'points?', r'minimal\s+clinically\s+important\s+difference|\bmcid\b',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_cystic_fibrosis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect cystic-fibrosis trial subspecialty. Returns (subspecialty,
    confidence). Subspecialties: pulmonary, nutrition, microbiology, systemic,
    general_cf."""
    text_lower = text.lower()
    scores = {'pulmonary': 0, 'nutrition': 0, 'microbiology': 0, 'systemic': 0}
    for kw in PULMONARY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pulmonary'] += 1
    for kw in NUTRITION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['nutrition'] += 1
    for kw in MICROBIOLOGY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['microbiology'] += 1
    for kw in SYSTEMIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['systemic'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_cf', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_cystic_fibrosis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'pulmonary': PULMONARY_PATTERNS['endpoint_patterns'],
        'nutrition': NUTRITION_PATTERNS['endpoint_patterns'],
        'microbiology': MICROBIOLOGY_PATTERNS['endpoint_patterns'],
        'systemic': SYSTEMIC_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_cystic_fibrosis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical cystic-fibrosis endpoint, preferring the LONGEST
    matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in CYSTIC_FIBROSIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
