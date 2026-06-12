"""
Testicular Cancer (Germ Cell Tumour) Subspecialty Patterns and Endpoints

Per-disease profile (same shape as melanoma / prostate_cancer). Testicular germ
cell tumour RCTs report a curative-intent endpoint vocabulary built on
relapse/recurrence-free survival and overall survival, across clinically distinct
entities.

Subspecialties:
- seminoma (stage I-II seminoma): relapse-free survival, overall survival.
  Agents: adjuvant carboplatin (single-agent), para-aortic radiotherapy,
  surveillance.
- nonseminoma (non-seminomatous germ cell tumour, NSGCT): progression-free /
  relapse-free survival, overall survival. Agents: BEP (bleomycin-etoposide-
  cisplatin), EP, retroperitoneal lymph-node dissection (RPLND), surveillance.
- advanced (metastatic / poor-risk germ cell tumour): progression-free survival,
  overall survival, favourable response. Agents: BEP, VIP, TIP, high-dose
  chemotherapy.
- mortality: testicular-cancer-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, RFS) -> HR; binary (favourable /
complete response) -> RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

TESTICULAR_CANCER_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'advanced', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'progression free survival',
                        'disease progression or death'],
            'subspecialty': 'advanced', 'measure_types': ['HR', 'median']},
    'RFS': {'aliases': ['relapse-free survival', 'rfs', 'recurrence-free survival',
                        'disease-free survival', 'dfs', 'freedom from progression',
                        'failure-free survival'],
            'subspecialty': 'seminoma', 'measure_types': ['HR', 'median']},
    'ORR': {'aliases': ['favourable response', 'favorable response', 'complete response',
                        'objective response rate', 'orr', 'complete response rate'],
            'subspecialty': 'advanced', 'measure_types': ['OR', 'RR', 'rate']},
    'RELAPSE': {'aliases': ['relapse', 'relapse rate', 'recurrence', 'recurrence rate'],
                'subspecialty': 'seminoma', 'measure_types': ['HR', 'RR', 'OR']},
    'TESTICULAR_CANCER_MORTALITY': {
        'aliases': ['testicular cancer mortality', 'testicular cancer-specific mortality',
                    'germ cell tumour mortality', 'cancer-specific mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
}

SEMINOMA_PATTERNS = {
    'detection_keywords': [
        r'\bseminoma\b|seminomatous', r'stage\s+(?:i|1|ii|2)\s+seminoma',
        r'adjuvant\s+carboplatin', r'para[- ]aortic\s+(?:radiotherapy|irradiation)',
        r'single[- ]agent\s+carboplatin', r'surveillance',
    ],
    'endpoint_patterns': [
        (r'relapse[- ]?free\s+survival|recurrence[- ]?free\s+survival|'
         r'disease[- ]?free\s+survival', 'RFS'),
        (r'overall\s+survival', 'OS'),
        (r'\brelapse\b|recurrence', 'RELAPSE'),
    ],
    'context_patterns': [r'retroperitoneal', r'\bauc\s*7\b']
}

NONSEMINOMA_PATTERNS = {
    'detection_keywords': [
        r'non[- ]?seminoma(?:tous)?|\bnsgct\b',
        r'non[- ]?seminomatous\s+germ[- ]cell', r'\bbep\b|bleomycin[, /-]+etoposide[, /-]+cisplatin',
        r'retroperitoneal\s+lymph[- ]node\s+dissection|\brplnd\b',
        r'embryonal\s+carcinoma|teratoma|yolk\s+sac|choriocarcinoma',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'relapse[- ]?free\s+survival|recurrence[- ]?free\s+survival', 'RFS'),
        (r'overall\s+survival', 'OS'),
    ],
    'context_patterns': [r'\bafp\b|alpha[- ]fetoprotein', r'\bhcg\b']
}

ADVANCED_PATTERNS = {
    'detection_keywords': [
        r'metastatic\s+(?:germ[- ]cell|testicular)', r'poor[- ]risk\s+germ[- ]cell',
        r'advanced\s+(?:germ[- ]cell|testicular)', r'\bvip\b|etoposide[, /-]+ifosfamide',
        r'\btip\b|paclitaxel[, /-]+ifosfamide', r'high[- ]dose\s+chemotherapy',
        r'salvage\s+(?:chemotherapy|therapy)',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'fav(?:ou)?rable\s+response|complete\s+response(?:\s+rate)?', 'ORR'),
    ],
    'context_patterns': [r'igccc?g', r'international\s+germ\s+cell']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'testicular[- ]cancer[- ]?specific\s+mortality|testicular\s+cancer\s+mortality',
        r'germ[- ]cell\s+tumou?r\s+mortality', r'death\s+from\s+testicular\s+cancer',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'testicular[- ]cancer[- ]?(?:specific\s+)?(?:mortality|death)|'
         r'germ[- ]cell\s+tumou?r\s+mortality|cancer[- ]specific\s+(?:mortality|survival)',
         'TESTICULAR_CANCER_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_testicular_cancer_subspecialty(text: str) -> Tuple[str, float]:
    """Detect testicular cancer trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: seminoma, nonseminoma, advanced, mortality,
    general_testicular_cancer."""
    text_lower = text.lower()
    scores = {'seminoma': 0, 'nonseminoma': 0, 'advanced': 0, 'mortality': 0}
    for kw in SEMINOMA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['seminoma'] += 1
    for kw in NONSEMINOMA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['nonseminoma'] += 1
    for kw in ADVANCED_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['advanced'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_testicular_cancer', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_testicular_cancer_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'seminoma': SEMINOMA_PATTERNS['endpoint_patterns'],
        'nonseminoma': NONSEMINOMA_PATTERNS['endpoint_patterns'],
        'advanced': ADVANCED_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_testicular_cancer_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical testicular cancer endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in TESTICULAR_CANCER_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
