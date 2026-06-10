"""
Oesophageal Cancer Subspecialty Patterns and Endpoints

Per-disease profile (same shape as prostate_cancer / cervical_cancer). Oesophageal
(squamous-cell and adenocarcinoma) and gastro-oesophageal-junction cancer RCTs
report a distinct endpoint vocabulary across definitive, perioperative and advanced
settings.

Subspecialties:
- definitive (locally advanced, neoadjuvant chemoradiation — CROSS): overall
  survival, progression-free survival, pathological complete response.
  Regimens: carboplatin + paclitaxel + radiotherapy, cisplatin + 5-FU.
- adjuvant (after oesophagectomy): disease-free survival, overall survival.
  Agents: adjuvant nivolumab (CheckMate-577).
- advanced (recurrent / metastatic oesophageal): overall survival, progression-
  free survival, objective response. Agents: pembrolizumab, nivolumab, tislelizumab,
  platinum + 5-FU; squamous vs adenocarcinoma.
- mortality: oesophageal-cancer-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, DFS) -> HR; binary (objective response,
pathological complete response, recurrence) -> RR/OR/RD/HR.
"""
from typing import Dict, List, Tuple, Optional
import re

OESOPHAGEAL_CANCER_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'definitive', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'progression free survival'],
            'subspecialty': 'definitive', 'measure_types': ['HR', 'median']},
    'PCR': {'aliases': ['pathological complete response', 'pathologic complete response',
                        'pcr', 'pathological complete remission', 'ypt0'],
            'subspecialty': 'definitive', 'measure_types': ['OR', 'RR', 'RD']},
    'DFS': {'aliases': ['disease-free survival', 'dfs', 'recurrence-free survival', 'rfs',
                        'relapse-free survival'],
            'subspecialty': 'adjuvant', 'measure_types': ['HR', 'median']},
    'ORR': {'aliases': ['objective response rate', 'orr', 'overall response rate',
                        'tumor response', 'tumour response'],
            'subspecialty': 'advanced', 'measure_types': ['OR', 'RR', 'rate']},
    'RECURRENCE': {'aliases': ['recurrence', 'disease recurrence', 'recurrent disease',
                               'relapse', 'locoregional recurrence'],
                   'subspecialty': 'adjuvant', 'measure_types': ['HR', 'RR', 'OR']},
    'OESOPHAGEAL_CANCER_MORTALITY': {
        'aliases': ['oesophageal cancer mortality', 'esophageal cancer mortality',
                    'oesophageal cancer death', 'esophageal cancer death',
                    'cancer-specific mortality', 'cancer-specific survival',
                    'disease-specific mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
}

DEFINITIVE_PATTERNS = {
    'detection_keywords': [
        r'neoadjuvant\s+chemoradi', r'\bcross\s+(?:trial|regimen)?\b',
        r'carboplatin[- ,/]+paclitaxel', r'cisplatin[- ,/]+(?:5[- ]?fu|fluorouracil)',
        r'definitive\s+chemoradi', r'locally\s+advanced\s+(?:o?esophageal|esophageal)',
        r'concurrent\s+chemoradi', r'trimodality',
    ],
    'endpoint_patterns': [
        (r'patholog(?:ic|ical)\s+complete\s+(?:response|remission)|\bpcr\b|\bypt0\b', 'PCR'),
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
    ],
    'context_patterns': [r'\bgy\b|gray', r'squamous|adenocarcinoma']
}

ADJUVANT_PATTERNS = {
    'detection_keywords': [
        r'adjuvant\s+(?:therapy|treatment|nivolumab|chemo)', r'(?:o?esophagectomy|esophagectomy)',
        r'after\s+(?:o?esophagectomy|surgery|resection)', r'resected\s+(?:o?esophageal|esophageal)',
        r'checkmate[- ]?577', r'residual\s+(?:pathological\s+)?disease',
    ],
    'endpoint_patterns': [
        (r'disease[- ]?free\s+survival|recurrence[- ]?free\s+survival|relapse[- ]?free\s+survival',
         'DFS'),
        (r'recurrence|recurrent\s+disease|locoregional\s+recurrence', 'RECURRENCE'),
        (r'overall\s+survival', 'OS'),
    ],
    'context_patterns': [r'r0\s+resection', r'lymph[- ]node']
}

ADVANCED_PATTERNS = {
    'detection_keywords': [
        r'(?:advanced|metastatic|recurrent)\s+(?:o?esophageal|esophageal)',
        r'pembrolizumab|keytruda', r'nivolumab|opdivo', r'tislelizumab',
        r'(?:o?esophageal|esophageal)\s+squamous\s+cell\s+carcinoma|\boescc\b|\bescc\b',
        r'first[- ]line', r'platinum[- ]based',
    ],
    'endpoint_patterns': [
        (r'overall\s+survival', 'OS'),
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'objective\s+response\s+rate|overall\s+response\s+rate|tumou?r\s+response', 'ORR'),
    ],
    'context_patterns': [r'pd[- ]?l1|combined\s+positive\s+score|\bcps\b', r'recist']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'(?:o?esophageal|esophageal)\s+cancer[- ]?specific\s+mortality|'
        r'(?:o?esophageal|esophageal)[- ]cancer\s+mortality',
        r'(?:o?esophageal|esophageal)\s+cancer\s+death',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'(?:o?esophageal|esophageal)\s+cancer\s+(?:mortality|death)|'
         r'cancer[- ]specific\s+(?:mortality|survival)|disease[- ]specific\s+mortality',
         'OESOPHAGEAL_CANCER_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_oesophageal_cancer_subspecialty(text: str) -> Tuple[str, float]:
    """Detect oesophageal-cancer trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: definitive, adjuvant, advanced, mortality, general_oesophageal_cancer."""
    text_lower = text.lower()
    scores = {'definitive': 0, 'adjuvant': 0, 'advanced': 0, 'mortality': 0}
    for kw in DEFINITIVE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['definitive'] += 1
    for kw in ADJUVANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['adjuvant'] += 1
    for kw in ADVANCED_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['advanced'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_oesophageal_cancer', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_oesophageal_cancer_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'definitive': DEFINITIVE_PATTERNS['endpoint_patterns'],
        'adjuvant': ADJUVANT_PATTERNS['endpoint_patterns'],
        'advanced': ADVANCED_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_oesophageal_cancer_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical oesophageal-cancer endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in OESOPHAGEAL_CANCER_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
