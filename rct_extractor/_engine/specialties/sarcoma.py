"""
Soft-Tissue Sarcoma Subspecialty Patterns and Endpoints

Per-disease profile (same shape as lymphoma / melanoma). Soft-tissue sarcoma
RCTs report a time-to-event endpoint vocabulary (progression-free survival,
overall survival) plus objective response and recurrence-free survival, across
clinically distinct entities.

Subspecialties:
- advanced (advanced / metastatic soft-tissue sarcoma): progression-free
  survival, overall survival, objective response. Agents: doxorubicin,
  ifosfamide, pazopanib, trabectedin, eribulin, olaratumab.
- gist (gastrointestinal stromal tumour): progression-free survival, overall
  survival, objective response. Agents: imatinib, sunitinib, regorafenib,
  ripretinib, avapritinib.
- localized (resectable / adjuvant soft-tissue sarcoma): recurrence-free
  survival, overall survival. Agents: doxorubicin-ifosfamide, (neo)adjuvant
  radiotherapy.
- mortality: sarcoma-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, RFS) -> HR; binary (objective response)
-> RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

SARCOMA_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'advanced', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'progression free survival',
                        'disease progression or death'],
            'subspecialty': 'advanced', 'measure_types': ['HR', 'median']},
    'RFS': {'aliases': ['recurrence-free survival', 'rfs', 'relapse-free survival',
                        'disease-free survival', 'dfs'],
            'subspecialty': 'localized', 'measure_types': ['HR', 'median']},
    'ORR': {'aliases': ['objective response rate', 'orr', 'overall response rate',
                        'objective response'],
            'subspecialty': 'advanced', 'measure_types': ['OR', 'RR', 'rate']},
    'TTP': {'aliases': ['time to progression', 'ttp'],
            'subspecialty': 'gist', 'measure_types': ['HR', 'median']},
    'SARCOMA_MORTALITY': {
        'aliases': ['sarcoma mortality', 'sarcoma-specific mortality',
                    'sarcoma death', 'death from sarcoma', 'cancer-specific mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
}

ADVANCED_PATTERNS = {
    'detection_keywords': [
        r'advanced\s+soft[- ]tissue\s+sarcoma|metastatic\s+soft[- ]tissue\s+sarcoma',
        r'\bsoft[- ]tissue\s+sarcoma\b', r'leiomyosarcoma|liposarcoma|synovial\s+sarcoma',
        r'angiosarcoma|undifferentiated\s+pleomorphic', r'doxorubicin',
        r'ifosfamide', r'pazopanib|votrient', r'trabectedin|yondelis',
        r'eribulin|halaven', r'olaratumab',
    ],
    'endpoint_patterns': [
        (r'(?:modified\s+)?progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'objective\s+response(?:\s+rate)?', 'ORR'),
    ],
    'context_patterns': [r'recist', r'choi\s+criteria']
}

GIST_PATTERNS = {
    'detection_keywords': [
        r'gastrointestinal\s+stromal\s+tumou?r|\bgist\b', r'imatinib|gleevec|glivec',
        r'sunitinib|sutent', r'regorafenib|stivarga', r'ripretinib|qinlock',
        r'avapritinib|ayvakit', r'\bkit\b|\bpdgfra\b', r'c-kit',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'time\s+to\s+progression', 'TTP'),
        (r'objective\s+response(?:\s+rate)?', 'ORR'),
    ],
    'context_patterns': [r'exon\s+(?:9|11)', r'mutational\s+status']
}

LOCALIZED_PATTERNS = {
    'detection_keywords': [
        r'resect(?:able|ed|ion)', r'localized\s+sarcoma|localised\s+sarcoma',
        r'(?:neo[- ]?)?adjuvant', r'\bextremity\b', r'limb[- ]sparing',
        r'wide\s+(?:local\s+)?excision',
        r'recurrence[- ]free\s+survival|disease[- ]free\s+survival|relapse[- ]free\s+survival',
        r'\bobservation\b', r'local\s+recurrence',
    ],
    'endpoint_patterns': [
        (r'recurrence[- ]?free\s+survival|relapse[- ]?free\s+survival|'
         r'disease[- ]?free\s+survival', 'RFS'),
        (r'overall\s+survival', 'OS'),
        (r'local\s+recurrence', 'RFS'),
    ],
    'context_patterns': [r'grade\s+(?:2|3|ii|iii)', r'margin\s+status']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'sarcoma[- ]?specific\s+mortality|sarcoma\s+mortality',
        r'sarcoma\s+death|death\s+from\s+sarcoma',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'sarcoma[- ]?(?:specific\s+)?(?:mortality|death)|death\s+from\s+sarcoma|'
         r'cancer[- ]specific\s+(?:mortality|survival)', 'SARCOMA_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_sarcoma_subspecialty(text: str) -> Tuple[str, float]:
    """Detect soft-tissue sarcoma trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: advanced, gist, localized, mortality, general_sarcoma."""
    text_lower = text.lower()
    scores = {'advanced': 0, 'gist': 0, 'localized': 0, 'mortality': 0}
    for kw in ADVANCED_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['advanced'] += 1
    for kw in GIST_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['gist'] += 1
    for kw in LOCALIZED_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['localized'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_sarcoma', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_sarcoma_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'advanced': ADVANCED_PATTERNS['endpoint_patterns'],
        'gist': GIST_PATTERNS['endpoint_patterns'],
        'localized': LOCALIZED_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_sarcoma_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical soft-tissue sarcoma endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in SARCOMA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
