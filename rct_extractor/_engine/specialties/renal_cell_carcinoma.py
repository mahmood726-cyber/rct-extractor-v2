"""
Renal Cell Carcinoma (RCC) Subspecialty Patterns and Endpoints

Per-disease profile (same shape as prostate_cancer / cervical_cancer). RCC RCTs
report a distinct endpoint vocabulary — overall and progression-free survival,
objective response, disease-free survival in the adjuvant setting — and a distinct
drug set (VEGF-TKIs and immune-checkpoint combinations). NOTE: RCC overlaps the
`nephrology` keyword bucket ("renal", "kidney"); the routing keywords here are rich
(RCC drug set, IMDC, nephrectomy, clear-cell) so an RCC trial outranks nephrology.

Subspecialties:
- advanced (first-line metastatic clear-cell RCC): overall survival, progression-
  free survival, objective response. Combinations: ipilimumab + nivolumab,
  pembrolizumab + axitinib, lenvatinib + pembrolizumab, cabozantinib + nivolumab;
  sunitinib, pazopanib.
- adjuvant (resected high-risk RCC): disease-free survival, overall survival.
  Agents: pembrolizumab, sunitinib.
- subsequent_line (VEGF/mTOR after prior therapy): progression-free survival,
  overall survival, objective response. Agents: cabozantinib, everolimus, axitinib,
  lenvatinib + everolimus, tivozanib, belzutifan.
- mortality: kidney-cancer-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, DFS) -> HR; binary (objective response,
recurrence) -> RR/OR/RD/HR.
"""
from typing import Dict, List, Tuple, Optional
import re

RENAL_CELL_CARCINOMA_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'advanced', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'progression free survival'],
            'subspecialty': 'advanced', 'measure_types': ['HR', 'median']},
    'ORR': {'aliases': ['objective response rate', 'orr', 'overall response rate',
                        'tumor response', 'tumour response'],
            'subspecialty': 'advanced', 'measure_types': ['OR', 'RR', 'rate']},
    'DFS': {'aliases': ['disease-free survival', 'dfs', 'recurrence-free survival', 'rfs'],
            'subspecialty': 'adjuvant', 'measure_types': ['HR', 'median']},
    'CR_RATE': {'aliases': ['complete response rate', 'complete response'],
                'subspecialty': 'advanced', 'measure_types': ['OR', 'RR', 'RD']},
    'KIDNEY_CANCER_MORTALITY': {
        'aliases': ['kidney cancer mortality', 'renal cancer mortality',
                    'kidney cancer-specific mortality', 'kidney cancer death',
                    'cancer-specific mortality', 'cancer-specific survival'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
}

ADVANCED_PATTERNS = {
    'detection_keywords': [
        r'(?:advanced|metastatic)\s+(?:clear[- ]cell\s+)?renal\s+cell|metastatic\s+rcc|\bmrcc\b',
        r'first[- ]line', r'ipilimumab(?:[- /]+nivolumab)?', r'nivolumab|opdivo',
        r'pembrolizumab(?:[- /]+axitinib)?|keytruda', r'lenvatinib(?:[- /]+pembrolizumab)?',
        r'cabozantinib(?:[- /]+nivolumab)?|cabometyx', r'axitinib', r'sunitinib|sutent',
        r'pazopanib|votrient', r'\bimdc\b|favou?rable[- ]risk|intermediate/poor[- ]risk',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'objective\s+response(?:\s+rate)?|overall\s+response\s+rate|tumou?r\s+response', 'ORR'),
        (r'complete\s+response(?:\s+rate)?', 'CR_RATE'),
    ],
    'context_patterns': [r'recist', r'clear[- ]cell|sarcomatoid']
}

ADJUVANT_PATTERNS = {
    'detection_keywords': [
        r'adjuvant\s+(?:therapy|treatment|pembrolizumab|sunitinib)',
        r'resected\s+(?:high[- ]risk\s+)?renal\s+cell|after\s+nephrectomy',
        r'nephrectomy', r'high[- ]risk\s+(?:of\s+)?recurrence',
    ],
    'endpoint_patterns': [
        (r'disease[- ]?free\s+survival|recurrence[- ]?free\s+survival', 'DFS'),
        (r'overall\s+survival', 'OS'),
    ],
    'context_patterns': [r'stage', r'fuhrman|grade']
}

SUBSEQUENT_LINE_PATTERNS = {
    'detection_keywords': [
        r'(?:second|subsequent|later)[- ]line|previously\s+treated|after\s+(?:prior\s+)?(?:vegf|tki)',
        r'cabozantinib', r'everolimus|afinitor', r'tivozanib|fotivda',
        r'lenvatinib[- /]+everolimus', r'belzutifan|welireg', r'\bmtor\b|\bvegf\b',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'objective\s+response(?:\s+rate)?|overall\s+response\s+rate', 'ORR'),
    ],
    'context_patterns': [r'refractory', r'crossover']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'kidney\s+cancer\s+mortality|renal\s+cancer\s+mortality',
        r'kidney\s+cancer\s+death|death\s+from\s+kidney\s+cancer',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'kidney\s+cancer\s+(?:mortality|death)|renal\s+cancer\s+mortality|'
         r'death\s+from\s+kidney\s+cancer|cancer[- ]specific\s+(?:mortality|survival)',
         'KIDNEY_CANCER_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_renal_cell_carcinoma_subspecialty(text: str) -> Tuple[str, float]:
    """Detect RCC trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: advanced, adjuvant, subsequent_line, mortality,
    general_renal_cell_carcinoma."""
    text_lower = text.lower()
    scores = {'advanced': 0, 'adjuvant': 0, 'subsequent_line': 0, 'mortality': 0}
    for kw in ADVANCED_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['advanced'] += 1
    for kw in ADJUVANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['adjuvant'] += 1
    for kw in SUBSEQUENT_LINE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['subsequent_line'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_renal_cell_carcinoma', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_renal_cell_carcinoma_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'advanced': ADVANCED_PATTERNS['endpoint_patterns'],
        'adjuvant': ADJUVANT_PATTERNS['endpoint_patterns'],
        'subsequent_line': SUBSEQUENT_LINE_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_renal_cell_carcinoma_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical RCC endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in RENAL_CELL_CARCINOMA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
