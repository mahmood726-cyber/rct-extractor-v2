"""
Endometrial Cancer Subspecialty Patterns and Endpoints

Per-disease profile (same shape as cervical_cancer / ovarian_cancer). DISTINCT
from the `endometriosis` specialty (a benign gynaecological condition).
Endometrial (uterine) cancer RCTs report an oncology endpoint vocabulary
(progression-free survival, overall survival, objective response) across
clinically distinct settings.

Subspecialties:
- advanced (advanced / metastatic / recurrent endometrial carcinoma):
  progression-free survival, overall survival, objective response. Agents:
  carboplatin-paclitaxel, pembrolizumab + lenvatinib, hormonal therapy.
- adjuvant (early-stage, post-surgery): recurrence-free survival, overall
  survival. Agents: (chemo)radiotherapy (PORTEC-type), carboplatin-paclitaxel.
- immunotherapy (mismatch-repair-deficient / MSI-high; checkpoint blockade):
  progression-free survival, overall survival, objective response. Agents:
  dostarlimab, pembrolizumab, durvalumab.
- mortality: endometrial-cancer-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, RFS) -> HR; binary (objective response)
-> RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

ENDOMETRIAL_CANCER_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'advanced', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'progression free survival',
                        'disease progression or death'],
            'subspecialty': 'advanced', 'measure_types': ['HR', 'median']},
    'RFS': {'aliases': ['recurrence-free survival', 'rfs', 'relapse-free survival',
                        'disease-free survival', 'dfs', 'failure-free survival'],
            'subspecialty': 'adjuvant', 'measure_types': ['HR', 'median']},
    'ORR': {'aliases': ['objective response rate', 'orr', 'overall response rate',
                        'objective response'],
            'subspecialty': 'immunotherapy', 'measure_types': ['OR', 'RR', 'rate']},
    'TTP': {'aliases': ['time to progression', 'ttp'],
            'subspecialty': 'advanced', 'measure_types': ['HR', 'median']},
    'ENDOMETRIAL_CANCER_MORTALITY': {
        'aliases': ['endometrial cancer mortality', 'endometrial cancer-specific mortality',
                    'uterine cancer mortality', 'cancer-specific mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
}

ADVANCED_PATTERNS = {
    'detection_keywords': [
        r'advanced\s+endometrial\s+(?:cancer|carcinoma)|metastatic\s+endometrial',
        r'recurrent\s+endometrial\s+(?:cancer|carcinoma)',
        r'carboplatin[, /-]+paclitaxel|paclitaxel[, /-]+carboplatin',
        r'lenvatinib', r'megestrol|medroxyprogesterone|hormonal\s+therapy',
        r'serous\s+endometrial|carcinosarcoma',
    ],
    'endpoint_patterns': [
        (r'(?:modified\s+)?progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'objective\s+response(?:\s+rate)?', 'ORR'),
        (r'time\s+to\s+progression', 'TTP'),
    ],
    'context_patterns': [r'figo\s+stage', r'recist']
}

ADJUVANT_PATTERNS = {
    'detection_keywords': [
        r'early[- ]stage\s+endometrial', r'(?:adjuvant|postoperative)\s+(?:radiotherapy|'
        r'chemoradi|chemotherapy)', r'vaginal\s+brachytherapy', r'pelvic\s+(?:external\s+beam\s+)?'
        r'radiotherapy', r'\bportec\b', r'high[- ]intermediate[- ]risk',
        r'recurrence[- ]free\s+survival|failure[- ]free\s+survival',
    ],
    'endpoint_patterns': [
        (r'recurrence[- ]?free\s+survival|relapse[- ]?free\s+survival|'
         r'disease[- ]?free\s+survival|failure[- ]?free\s+survival', 'RFS'),
        (r'overall\s+survival', 'OS'),
        (r'(?:loco[- ]?regional\s+|vaginal\s+|pelvic\s+)?recurrence', 'RFS'),
    ],
    'context_patterns': [r'lymphovascular\s+(?:space\s+)?invasion', r'myometrial\s+invasion']
}

IMMUNOTHERAPY_PATTERNS = {
    'detection_keywords': [
        r'mismatch[- ]repair[- ]deficient|\bdmmr\b|\bmmrd\b|mismatch\s+repair\s+deficien',
        r'microsatellite[- ]instability[- ]high|\bmsi[- ]?h\b|\bmsi[- ]high\b',
        r'dostarlimab|jemperli', r'pembrolizumab|keytruda', r'durvalumab|imfinzi',
        r'checkpoint\s+(?:inhibitor|blockade)|immune\s+checkpoint',
        r'pembrolizumab[, /-]+lenvatinib',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'objective\s+response(?:\s+rate)?', 'ORR'),
    ],
    'context_patterns': [r'\bpd[- ]?l1\b', r'tumou?r\s+mutational\s+burden']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'endometrial[- ]cancer[- ]?specific\s+mortality|endometrial\s+cancer\s+mortality',
        r'uterine\s+cancer\s+mortality', r'death\s+from\s+endometrial\s+cancer',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'endometrial[- ]cancer[- ]?(?:specific\s+)?(?:mortality|death)|'
         r'uterine\s+cancer\s+mortality|cancer[- ]specific\s+(?:mortality|survival)',
         'ENDOMETRIAL_CANCER_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_endometrial_cancer_subspecialty(text: str) -> Tuple[str, float]:
    """Detect endometrial cancer trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: advanced, adjuvant, immunotherapy, mortality,
    general_endometrial_cancer."""
    text_lower = text.lower()
    scores = {'advanced': 0, 'adjuvant': 0, 'immunotherapy': 0, 'mortality': 0}
    for kw in ADVANCED_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['advanced'] += 1
    for kw in ADJUVANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['adjuvant'] += 1
    for kw in IMMUNOTHERAPY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['immunotherapy'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_endometrial_cancer', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_endometrial_cancer_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'advanced': ADVANCED_PATTERNS['endpoint_patterns'],
        'adjuvant': ADJUVANT_PATTERNS['endpoint_patterns'],
        'immunotherapy': IMMUNOTHERAPY_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_endometrial_cancer_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical endometrial cancer endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in ENDOMETRIAL_CANCER_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
