"""
Melanoma Subspecialty Patterns and Endpoints

Per-disease profile (same shape as prostate_cancer / cervical_cancer). Cutaneous
melanoma RCTs report a distinct endpoint vocabulary — overall and progression-free
survival, recurrence-free survival and distant-metastasis-free survival in the
adjuvant setting, pathological response in the neoadjuvant setting — and a distinct
drug set (checkpoint inhibitors and BRAF/MEK-targeted therapy). The generic
oncology bucket has a bare `melanoma` keyword; the routing keywords here are richer
so a melanoma trial outranks the generic bucket.

Subspecialties:
- systemic (advanced / metastatic): overall survival, progression-free survival,
  objective response. Agents: pembrolizumab, nivolumab, ipilimumab, nivolumab +
  ipilimumab, relatlimab, dabrafenib + trametinib, encorafenib + binimetinib,
  vemurafenib + cobimetinib (BRAF V600).
- adjuvant (resected stage III/IV): recurrence-free survival, distant
  metastasis-free survival, overall survival.
- neoadjuvant: pathological complete response, major pathological response,
  event-free survival.
- mortality: melanoma-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, RFS, DMFS, EFS) -> HR; binary (objective
response, pathological response, recurrence) -> RR/OR/RD/HR; continuous serum LDH
-> log-normal; QoL -> MD.
"""
from typing import Dict, List, Tuple, Optional
import re

MELANOMA_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause', 'melanoma-specific survival'],
           'subspecialty': 'systemic', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'disease progression or death',
                        'progression free survival'],
            'subspecialty': 'systemic', 'measure_types': ['HR', 'median']},
    'ORR': {'aliases': ['objective response rate', 'orr', 'overall response rate',
                        'tumor response', 'tumour response'],
            'subspecialty': 'systemic', 'measure_types': ['OR', 'RR', 'rate']},
    'RFS': {'aliases': ['recurrence-free survival', 'rfs', 'relapse-free survival',
                        'disease-free survival', 'dfs'],
            'subspecialty': 'adjuvant', 'measure_types': ['HR', 'median']},
    'DMFS': {'aliases': ['distant metastasis-free survival', 'distant metastasis free survival',
                         'dmfs', 'distant-metastasis-free survival'],
             'subspecialty': 'adjuvant', 'measure_types': ['HR', 'median']},
    'EFS': {'aliases': ['event-free survival', 'efs'],
            'subspecialty': 'neoadjuvant', 'measure_types': ['HR', 'median']},
    'PATHOLOGICAL_RESPONSE': {
        'aliases': ['pathological complete response', 'pathologic complete response', 'pcr',
                    'major pathological response', 'major pathologic response', 'mpr',
                    'pathological response'],
        'subspecialty': 'neoadjuvant', 'measure_types': ['OR', 'RR', 'RD']},
    'MELANOMA_MORTALITY': {
        'aliases': ['melanoma mortality', 'melanoma-specific mortality',
                    'melanoma death', 'death from melanoma', 'cancer-specific mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
    'LDH_LEVEL': {'aliases': ['ldh level', 'lactate dehydrogenase level', 'serum ldh',
                              'ldh concentration'],
                  'subspecialty': 'systemic', 'measure_types': ['MD', 'GMR']},
    'QOL': {'aliases': ['quality of life', 'hrqol', 'eortc qlq-c30',
                        'health-related quality of life'],
            'subspecialty': 'systemic', 'measure_types': ['MD']},
}

SYSTEMIC_PATTERNS = {
    'detection_keywords': [
        r'metastatic\s+melanoma|advanced\s+(?:unresectable\s+)?melanoma|stage\s+iv\s+melanoma',
        r'pembrolizumab|keytruda', r'nivolumab|opdivo', r'ipilimumab|yervoy',
        r'relatlimab', r'dabrafenib|tafinlar', r'trametinib|mekinist',
        r'encorafenib|braftovi', r'binimetinib|mektovi', r'vemurafenib|cobimetinib',
        r'braf\s+v?600|braf[- ]?(?:mutant|mutation|positive)', r'checkpoint\s+inhibitor',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival|melanoma[- ]specific\s+survival', 'OS'),
        (r'objective\s+response\s+rate|overall\s+response\s+rate|tumou?r\s+response', 'ORR'),
        (r'(?:serum\s+)?(?:ldh|lactate\s+dehydrogenase)\s+(?:level|concentration)', 'LDH_LEVEL'),
        (r'quality\s+of\s+life|hrqol|eortc\s+qlq', 'QOL'),
    ],
    'context_patterns': [r'recist', r'pd[- ]?l1']
}

ADJUVANT_PATTERNS = {
    'detection_keywords': [
        r'adjuvant\s+(?:therapy|treatment|pembrolizumab|nivolumab|dabrafenib)',
        r'resected\s+(?:stage\s+(?:iii|iv)\s+)?melanoma', r'completely\s+resected',
        r'high[- ]risk\s+melanoma', r'sentinel[- ]node[- ]positive',
    ],
    'endpoint_patterns': [
        (r'recurrence[- ]?free\s+survival|relapse[- ]?free\s+survival|'
         r'disease[- ]?free\s+survival', 'RFS'),
        (r'distant[- ]?metastasis[- ]?free\s+survival', 'DMFS'),
    ],
    'context_patterns': [r'stage\s+iii', r'ulceration']
}

NEOADJUVANT_PATTERNS = {
    'detection_keywords': [
        r'neoadjuvant', r'pre[- ]?operative\s+(?:immuno|chemo)?therapy',
        r'patholog(?:ic|ical)\s+(?:complete\s+)?response', r'major\s+patholog(?:ic|ical)\s+response',
    ],
    'endpoint_patterns': [
        (r'patholog(?:ic|ical)\s+complete\s+response|major\s+patholog(?:ic|ical)\s+response|'
         r'\bpcr\b|\bmpr\b|patholog(?:ic|ical)\s+response', 'PATHOLOGICAL_RESPONSE'),
        (r'event[- ]?free\s+survival', 'EFS'),
    ],
    'context_patterns': [r'surgery', r'residual\s+viable\s+tumou?r']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'melanoma[- ]?specific\s+mortality|melanoma\s+mortality',
        r'melanoma\s+death|death\s+from\s+melanoma',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'melanoma[- ]?(?:specific\s+)?(?:mortality|death)|death\s+from\s+melanoma|'
         r'cancer[- ]specific\s+(?:mortality|survival)', 'MELANOMA_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_melanoma_subspecialty(text: str) -> Tuple[str, float]:
    """Detect melanoma trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: systemic, adjuvant, neoadjuvant, mortality, general_melanoma."""
    text_lower = text.lower()
    scores = {'systemic': 0, 'adjuvant': 0, 'neoadjuvant': 0, 'mortality': 0}
    for kw in SYSTEMIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['systemic'] += 1
    for kw in ADJUVANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['adjuvant'] += 1
    for kw in NEOADJUVANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['neoadjuvant'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    # neoadjuvant implies adjuvant keywords sometimes; prefer the more specific
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_melanoma', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_melanoma_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'systemic': SYSTEMIC_PATTERNS['endpoint_patterns'],
        'adjuvant': ADJUVANT_PATTERNS['endpoint_patterns'],
        'neoadjuvant': NEOADJUVANT_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_melanoma_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical melanoma endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in MELANOMA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
