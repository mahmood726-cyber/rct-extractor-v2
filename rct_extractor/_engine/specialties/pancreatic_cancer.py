"""
Pancreatic Cancer Subspecialty Patterns and Endpoints

Per-disease profile (same shape as prostate_cancer / cervical_cancer). Pancreatic
ductal adenocarcinoma RCTs report a distinct endpoint vocabulary — overall and
progression-free survival, CA19-9 response, R0 resection, disease-free survival
in the resected setting — that the generic oncology bucket does not split out.

Subspecialties:
- systemic (advanced / metastatic): overall survival, progression-free survival,
  objective response, CA19-9 response. Regimens: FOLFIRINOX, gemcitabine +
  nab-paclitaxel, gemcitabine, NALIRIFOX, olaparib maintenance, erlotinib.
- adjuvant (resected): disease-free survival, overall survival, recurrence.
  Regimens: mFOLFIRINOX, gemcitabine-capecitabine, S-1.
- locally_advanced (chemoradiation / conversion): local control, resection
  conversion rate after neoadjuvant therapy, chemoradiotherapy.
- mortality: pancreatic-cancer-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, DFS) -> HR; binary (objective response,
CA19-9 response, R0 resection, recurrence) -> RR/OR/RD/HR; continuous CA19-9 ->
log-normal; QoL -> MD.
"""
from typing import Dict, List, Tuple, Optional
import re

PANCREATIC_CANCER_ENDPOINTS = {
    'OS': {
        'aliases': ['overall survival', 'os', 'death from any cause'],
        'subspecialty': 'systemic', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {
        'aliases': ['progression-free survival', 'pfs',
                    'disease progression or death', 'progression free survival'],
        'subspecialty': 'systemic', 'measure_types': ['HR', 'median']},
    'ORR': {
        'aliases': ['objective response rate', 'orr', 'overall response rate',
                    'tumor response', 'tumour response'],
        'subspecialty': 'systemic', 'measure_types': ['OR', 'RR', 'rate']},
    'CA199_RESPONSE': {
        'aliases': ['ca19-9 response', 'ca 19-9 response', 'ca19.9 response',
                    'ca19-9 decline', 'carbohydrate antigen 19-9 response',
                    'ca19-9 normalization', 'ca19-9 normalisation'],
        'subspecialty': 'systemic', 'measure_types': ['OR', 'RR', 'rate']},
    'DFS': {
        'aliases': ['disease-free survival', 'dfs', 'recurrence-free survival',
                    'rfs', 'relapse-free survival'],
        'subspecialty': 'adjuvant', 'measure_types': ['HR', 'median']},
    'R0_RESECTION': {
        'aliases': ['r0 resection', 'margin-negative resection',
                    'complete resection', 'negative resection margin',
                    'r0 resection rate'],
        'subspecialty': 'adjuvant', 'measure_types': ['RR', 'OR', 'RD']},
    'RECURRENCE': {
        'aliases': ['recurrence', 'disease recurrence', 'recurrent disease',
                    'recurrence rate', 'relapse'],
        'subspecialty': 'adjuvant', 'measure_types': ['HR', 'RR', 'OR']},
    'RESECTION_CONVERSION': {
        'aliases': ['resection conversion rate', 'conversion to resection',
                    'resection rate', 'surgical resection rate',
                    'resectability rate', 'r0/r1 resection rate'],
        'subspecialty': 'locally_advanced', 'measure_types': ['RR', 'OR', 'RD']},
    'LOCAL_CONTROL': {
        'aliases': ['local control', 'locoregional control',
                    'local progression-free', 'local failure'],
        'subspecialty': 'locally_advanced', 'measure_types': ['HR', 'RR', 'OR']},
    'PANCREATIC_CANCER_MORTALITY': {
        'aliases': ['pancreatic cancer mortality', 'pancreatic-cancer mortality',
                    'pancreatic cancer-specific mortality',
                    'pancreatic cancer death', 'death from pancreatic cancer',
                    'cancer-specific survival'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
    'CA199_LEVEL': {
        'aliases': ['ca19-9 level', 'ca 19-9 level', 'serum ca19-9',
                    'carbohydrate antigen 19-9 level', 'ca19-9 concentration'],
        'subspecialty': 'systemic', 'measure_types': ['MD', 'GMR']},
    'QOL': {
        'aliases': ['quality of life', 'fact-hep', 'hrqol', 'eortc qlq-pan26',
                    'health-related quality of life'],
        'subspecialty': 'systemic', 'measure_types': ['MD']},
}


SYSTEMIC_PATTERNS = {
    'detection_keywords': [
        r'metastatic\s+pancreatic', r'advanced\s+pancreatic', r'folfirinox',
        r'nab[- ]?paclitaxel|abraxane', r'gemcitabine', r'nalirifox',
        r'liposomal\s+irinotecan|nal[- ]?iri|onivyde', r'oxaliplatin|irinotecan',
        r'erlotinib', r'ca\s?19[-. ]?9', r'olaparib',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'objective\s+response\s+rate|overall\s+response\s+rate|tumou?r\s+response', 'ORR'),
        (r'ca\s?19[-. ]?9\s+(?:response|decline|normali[sz]ation)', 'CA199_RESPONSE'),
        (r'ca\s?19[-. ]?9\s+(?:level|concentration)|serum\s+ca\s?19[-. ]?9', 'CA199_LEVEL'),
        (r'quality\s+of\s+life|fact-hep|hrqol|eortc\s+qlq', 'QOL'),
    ],
    'context_patterns': [r'recist', r'per[- ]protocol|intention[- ]to[- ]treat']
}

ADJUVANT_PATTERNS = {
    'detection_keywords': [
        r'adjuvant\s+(?:chemo)?therapy', r'resected\s+pancreatic',
        r'mfolfirinox|modified\s+folfirinox', r'gemcitabine[- ]capecitabine|gemcap',
        r'\bs-?1\b', r'after\s+(?:surgical\s+)?resection', r'pancreaticoduodenectomy|whipple',
    ],
    'endpoint_patterns': [
        (r'disease[- ]?free\s+survival|recurrence[- ]?free\s+survival|'
         r'relapse[- ]?free\s+survival', 'DFS'),
        (r'r0\s+resection|margin[- ]negative\s+resection|negative\s+resection\s+margin|'
         r'complete\s+resection', 'R0_RESECTION'),
        (r'recurrence|recurrent\s+disease|relapse', 'RECURRENCE'),
    ],
    'context_patterns': [r'margin\s+status', r'lymph[- ]node']
}

LOCALLY_ADVANCED_PATTERNS = {
    'detection_keywords': [
        r'locally\s+advanced\s+pancreatic|\blapc\b', r'borderline\s+resectable',
        r'chemoradi(?:o|ation)therapy|chemoradiation', r'neoadjuvant',
        r'stereotactic\s+body\s+radi|\bsbrt\b', r'conversion\s+(?:to\s+)?(?:surgery|resection)',
    ],
    'endpoint_patterns': [
        (r'resect(?:ion|ability)\s+rate|conversion\s+(?:to\s+)?resection|'
         r'surgical\s+resection\s+rate|r0/r1\s+resection', 'RESECTION_CONVERSION'),
        (r'local(?:[- ]?regional)?\s+(?:control|failure|progression[- ]?free)', 'LOCAL_CONTROL'),
    ],
    'context_patterns': [r'gy\b|gray', r'fraction']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'pancreatic\s+cancer[- ]?specific\s+mortality|pancreatic[- ]cancer\s+mortality',
        r'pancreatic\s+cancer\s+death|death\s+from\s+pancreatic\s+cancer',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'pancreatic\s+cancer[- ]?(?:specific\s+)?(?:mortality|death)|'
         r'death\s+from\s+pancreatic\s+cancer|cancer[- ]specific\s+(?:mortality|survival)',
         'PANCREATIC_CANCER_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_pancreatic_cancer_subspecialty(text: str) -> Tuple[str, float]:
    """Detect pancreatic-cancer trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: systemic, adjuvant, locally_advanced, mortality, general_pancreatic_cancer."""
    text_lower = text.lower()
    scores = {'systemic': 0, 'adjuvant': 0, 'locally_advanced': 0, 'mortality': 0}
    for kw in SYSTEMIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['systemic'] += 1
    for kw in ADJUVANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['adjuvant'] += 1
    for kw in LOCALLY_ADVANCED_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['locally_advanced'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_pancreatic_cancer', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_pancreatic_cancer_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'systemic': SYSTEMIC_PATTERNS['endpoint_patterns'],
        'adjuvant': ADJUVANT_PATTERNS['endpoint_patterns'],
        'locally_advanced': LOCALLY_ADVANCED_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_pancreatic_cancer_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical pancreatic-cancer endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in PANCREATIC_CANCER_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
