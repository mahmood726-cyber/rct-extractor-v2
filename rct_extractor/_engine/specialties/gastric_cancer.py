"""
Gastric Cancer Subspecialty Patterns and Endpoints

Per-disease profile (same shape as prostate_cancer / cervical_cancer). Gastric and
gastro-oesophageal junction adenocarcinoma RCTs report a distinct endpoint
vocabulary — overall and progression-free survival, pathological complete response,
R0 resection, HER2/PD-L1 response — that the generic oncology bucket does not split.

Subspecialties:
- systemic (advanced / metastatic): overall survival, progression-free survival,
  objective response. Agents: trastuzumab (HER2+), nivolumab / pembrolizumab
  (PD-L1), ramucirumab, FOLFOX / CAPOX / cisplatin-5FU, trastuzumab deruxtecan.
- perioperative (neoadjuvant / adjuvant): pathological complete response,
  disease-free survival, R0 resection. Regimens: FLOT, S-1, capecitabine-oxaliplatin.
- surgical (gastrectomy / lymphadenectomy): recurrence, complete resection,
  D2 vs D1 lymphadenectomy.
- mortality: gastric-cancer-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, DFS) -> HR; binary (objective response,
pCR, R0 resection, recurrence) -> RR/OR/RD/HR; QoL -> MD.
"""
from typing import Dict, List, Tuple, Optional
import re

GASTRIC_CANCER_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'systemic', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'disease progression or death',
                        'progression free survival'],
            'subspecialty': 'systemic', 'measure_types': ['HR', 'median']},
    'ORR': {'aliases': ['objective response rate', 'orr', 'overall response rate',
                        'tumor response', 'tumour response'],
            'subspecialty': 'systemic', 'measure_types': ['OR', 'RR', 'rate']},
    'PCR': {'aliases': ['pathological complete response', 'pathologic complete response',
                        'pcr', 'complete pathological response'],
            'subspecialty': 'perioperative', 'measure_types': ['OR', 'RR', 'RD']},
    'DFS': {'aliases': ['disease-free survival', 'dfs', 'recurrence-free survival', 'rfs',
                        'relapse-free survival'],
            'subspecialty': 'perioperative', 'measure_types': ['HR', 'median']},
    'R0_RESECTION': {'aliases': ['r0 resection', 'margin-negative resection',
                                 'complete resection', 'negative resection margin',
                                 'r0 resection rate', 'curative resection'],
                     'subspecialty': 'perioperative', 'measure_types': ['RR', 'OR', 'RD']},
    'RECURRENCE': {'aliases': ['recurrence', 'disease recurrence', 'recurrent disease',
                               'recurrence rate', 'relapse'],
                   'subspecialty': 'surgical', 'measure_types': ['HR', 'RR', 'OR']},
    'GASTRIC_CANCER_MORTALITY': {
        'aliases': ['gastric cancer mortality', 'gastric-cancer mortality',
                    'gastric cancer-specific mortality', 'gastric cancer death',
                    'death from gastric cancer', 'cancer-specific survival'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
    'QOL': {'aliases': ['quality of life', 'fact-ga', 'hrqol', 'eortc qlq-sto22',
                        'health-related quality of life'],
            'subspecialty': 'systemic', 'measure_types': ['MD']},
}

SYSTEMIC_PATTERNS = {
    'detection_keywords': [
        r'metastatic\s+gastric|advanced\s+gastric', r'her2[- ]?(?:positive|negative|\+)',
        r'trastuzumab(?:\s+deruxtecan)?|herceptin|enhertu', r'nivolumab|opdivo',
        r'pembrolizumab|keytruda', r'ramucirumab|cyramza', r'pd[- ]?l1',
        r'folfox|capox|xelox|cisplatin', r'fluorouracil|5[- ]?fu|capecitabine',
        r'objective\s+response',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'objective\s+response\s+rate|overall\s+response\s+rate|tumou?r\s+response', 'ORR'),
        (r'quality\s+of\s+life|fact-ga|hrqol|eortc\s+qlq', 'QOL'),
    ],
    'context_patterns': [r'recist', r'per[- ]protocol|intention[- ]to[- ]treat']
}

PERIOPERATIVE_PATTERNS = {
    'detection_keywords': [
        r'neoadjuvant', r'perioperative\s+(?:chemo)?therapy', r'adjuvant\s+(?:chemo)?therapy',
        r'\bflot\b', r'\bs-?1\b', r'capecitabine[- ]oxaliplatin|\bxelox\b',
        r'epirubicin', r'resectable\s+gastric',
    ],
    'endpoint_patterns': [
        (r'patholog(?:ic|ical)\s+complete\s+response|complete\s+patholog(?:ic|ical)\s+response|'
         r'\bpcr\b', 'PCR'),
        (r'disease[- ]?free\s+survival|recurrence[- ]?free\s+survival|relapse[- ]?free\s+survival',
         'DFS'),
        (r'r0\s+resection|margin[- ]negative\s+resection|curative\s+resection|'
         r'negative\s+resection\s+margin|complete\s+resection', 'R0_RESECTION'),
    ],
    'context_patterns': [r'margin\s+status', r'downstaging']
}

SURGICAL_PATTERNS = {
    'detection_keywords': [
        r'gastrectomy', r'd2\s+(?:lymphadenectomy|dissection)|d1\s+(?:lymphadenectomy|dissection)',
        r'lymphadenectomy', r'laparoscopic\s+gastrectomy', r'subtotal\s+gastrectomy|total\s+gastrectomy',
    ],
    'endpoint_patterns': [
        (r'recurrence|recurrent\s+disease|relapse', 'RECURRENCE'),
        (r'r0\s+resection|complete\s+resection|curative\s+resection', 'R0_RESECTION'),
    ],
    'context_patterns': [r'lymph[- ]node\s+(?:yield|harvest)', r'anastomotic']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'gastric\s+cancer[- ]?specific\s+mortality|gastric[- ]cancer\s+mortality',
        r'gastric\s+cancer\s+death|death\s+from\s+gastric\s+cancer',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'gastric\s+cancer[- ]?(?:specific\s+)?(?:mortality|death)|'
         r'death\s+from\s+gastric\s+cancer|cancer[- ]specific\s+(?:mortality|survival)',
         'GASTRIC_CANCER_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_gastric_cancer_subspecialty(text: str) -> Tuple[str, float]:
    """Detect gastric-cancer trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: systemic, perioperative, surgical, mortality, general_gastric_cancer."""
    text_lower = text.lower()
    scores = {'systemic': 0, 'perioperative': 0, 'surgical': 0, 'mortality': 0}
    for kw in SYSTEMIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['systemic'] += 1
    for kw in PERIOPERATIVE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['perioperative'] += 1
    for kw in SURGICAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['surgical'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_gastric_cancer', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_gastric_cancer_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'systemic': SYSTEMIC_PATTERNS['endpoint_patterns'],
        'perioperative': PERIOPERATIVE_PATTERNS['endpoint_patterns'],
        'surgical': SURGICAL_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_gastric_cancer_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical gastric-cancer endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in GASTRIC_CANCER_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
