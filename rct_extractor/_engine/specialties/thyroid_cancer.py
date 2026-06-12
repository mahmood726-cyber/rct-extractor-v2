"""
Thyroid Cancer Subspecialty Patterns and Endpoints

Per-disease profile (same shape as lymphoma / melanoma). DISTINCT from the
`thyroid` specialty, which covers benign thyroid dysfunction (hypo/hyperthyroidism,
thyroid function). Thyroid cancer RCTs report an oncology endpoint vocabulary
(progression-free survival, objective response, overall survival) across
clinically distinct histologies.

Subspecialties:
- differentiated (DTC: papillary / follicular, radioiodine-refractory):
  progression-free survival, objective response, overall survival. Agents:
  lenvatinib, sorafenib, selpercatinib (RET-altered), radioactive iodine (RAI).
- medullary (MTC): progression-free survival, objective response. Agents:
  vandetanib, cabozantinib, selpercatinib, pralsetinib (RET-mutant).
- anaplastic (ATC): overall survival, objective response. Agents: dabrafenib +
  trametinib (BRAF V600E).
- mortality: thyroid-cancer-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS) -> HR; binary (objective response) ->
RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

THYROID_CANCER_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'differentiated', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'progression free survival',
                        'disease progression or death'],
            'subspecialty': 'differentiated', 'measure_types': ['HR', 'median']},
    'ORR': {'aliases': ['objective response rate', 'orr', 'overall response rate',
                        'objective response'],
            'subspecialty': 'differentiated', 'measure_types': ['OR', 'RR', 'rate']},
    'TTP': {'aliases': ['time to progression', 'ttp'],
            'subspecialty': 'medullary', 'measure_types': ['HR', 'median']},
    'DCR': {'aliases': ['disease control rate', 'dcr', 'clinical benefit rate'],
            'subspecialty': 'differentiated', 'measure_types': ['OR', 'RR', 'rate']},
    'THYROID_CANCER_MORTALITY': {
        'aliases': ['thyroid cancer mortality', 'thyroid cancer-specific mortality',
                    'thyroid cancer death', 'cancer-specific mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
}

DIFFERENTIATED_PATTERNS = {
    'detection_keywords': [
        r'differentiated\s+thyroid\s+(?:cancer|carcinoma)|\bdtc\b',
        r'papillary\s+thyroid\s+(?:cancer|carcinoma)|follicular\s+thyroid\s+(?:cancer|carcinoma)',
        r'radioiodine[- ]refractory|radioactive\s+iodine[- ]refractory|\brai[- ]refractory',
        r'lenvatinib|lenvima', r'sorafenib|nexavar', r'selpercatinib|retevmo',
        r'radioactive\s+iodine|radioiodine|\bi[- ]?131\b',
    ],
    'endpoint_patterns': [
        (r'(?:modified\s+)?progression[- ]?free\s+survival', 'PFS'),
        (r'objective\s+response(?:\s+rate)?', 'ORR'),
        (r'overall\s+survival', 'OS'),
        (r'disease\s+control\s+rate', 'DCR'),
    ],
    'context_patterns': [r'thyroglobulin', r'recist']
}

MEDULLARY_PATTERNS = {
    'detection_keywords': [
        r'medullary\s+thyroid\s+(?:cancer|carcinoma)|\bmtc\b',
        r'vandetanib|caprelsa', r'cabozantinib|cabometyx', r'pralsetinib|gavreto',
        r'\bret\b[- ]?(?:mutant|altered|fusion|rearrang)', r'calcitonin',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'objective\s+response(?:\s+rate)?', 'ORR'),
        (r'time\s+to\s+progression', 'TTP'),
    ],
    'context_patterns': [r'carcinoembryonic\s+antigen|\bcea\b', r'\bmen2\b']
}

ANAPLASTIC_PATTERNS = {
    'detection_keywords': [
        r'anaplastic\s+thyroid\s+(?:cancer|carcinoma)|\batc\b',
        r'dabrafenib', r'trametinib', r'\bbraf\b\s*v?600',
        r'undifferentiated\s+thyroid',
    ],
    'endpoint_patterns': [
        (r'overall\s+survival', 'OS'),
        (r'objective\s+response(?:\s+rate)?', 'ORR'),
        (r'progression[- ]?free\s+survival', 'PFS'),
    ],
    'context_patterns': [r'rapidly\s+progressive', r'locally\s+advanced']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'thyroid[- ]cancer[- ]?specific\s+mortality|thyroid\s+cancer\s+mortality',
        r'thyroid\s+cancer\s+death|death\s+from\s+thyroid\s+cancer',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'thyroid[- ]cancer[- ]?(?:specific\s+)?(?:mortality|death)|'
         r'cancer[- ]specific\s+(?:mortality|survival)', 'THYROID_CANCER_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_thyroid_cancer_subspecialty(text: str) -> Tuple[str, float]:
    """Detect thyroid cancer trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: differentiated, medullary, anaplastic, mortality,
    general_thyroid_cancer."""
    text_lower = text.lower()
    scores = {'differentiated': 0, 'medullary': 0, 'anaplastic': 0, 'mortality': 0}
    for kw in DIFFERENTIATED_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['differentiated'] += 1
    for kw in MEDULLARY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['medullary'] += 1
    for kw in ANAPLASTIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['anaplastic'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_thyroid_cancer', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_thyroid_cancer_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'differentiated': DIFFERENTIATED_PATTERNS['endpoint_patterns'],
        'medullary': MEDULLARY_PATTERNS['endpoint_patterns'],
        'anaplastic': ANAPLASTIC_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_thyroid_cancer_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical thyroid cancer endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in THYROID_CANCER_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
