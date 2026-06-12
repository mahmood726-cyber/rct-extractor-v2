"""
Glioma / Glioblastoma Subspecialty Patterns and Endpoints

Per-disease profile (same shape as lymphoma / melanoma). Glioma RCTs report a
neuro-oncology endpoint vocabulary dominated by time-to-event survival (overall
survival, progression-free survival) plus objective response, across clinically
distinct entities.

Subspecialties:
- glioblastoma (newly diagnosed GBM): overall survival, progression-free
  survival. Agents: temozolomide + radiotherapy (Stupp protocol), tumour-treating
  fields (TTFields / Optune), bevacizumab, lomustine, carmustine wafers.
- recurrent (recurrent glioma / GBM): overall survival, progression-free
  survival, objective response. Agents: bevacizumab, regorafenib, lomustine.
- low_grade (lower-grade / IDH-mutant glioma): progression-free survival, overall
  survival. Agents: vorasidenib (IDH1/2 inhibitor), procarbazine-lomustine-
  vincristine (PCV), radiotherapy.
- mortality: glioma / brain-tumour mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS) -> HR; binary (objective response,
6-month PFS) -> RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

GLIOMA_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'glioblastoma', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'progression free survival',
                        'disease progression or death'],
            'subspecialty': 'glioblastoma', 'measure_types': ['HR', 'median']},
    'PFS6': {'aliases': ['6-month progression-free survival', 'pfs6',
                         'progression-free survival at 6 months', '6-month pfs'],
             'subspecialty': 'recurrent', 'measure_types': ['OR', 'RR', 'rate']},
    'ORR': {'aliases': ['objective response rate', 'orr', 'overall response rate',
                        'radiographic response'],
            'subspecialty': 'recurrent', 'measure_types': ['OR', 'RR', 'rate']},
    'TTP': {'aliases': ['time to progression', 'ttp'],
            'subspecialty': 'recurrent', 'measure_types': ['HR', 'median']},
    'GLIOMA_MORTALITY': {
        'aliases': ['glioma mortality', 'brain tumour mortality', 'brain tumor mortality',
                    'glioma death', 'cancer-specific mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
}

GLIOBLASTOMA_PATTERNS = {
    'detection_keywords': [
        r'glioblastoma(?:\s+multiforme)?|\bgbm\b', r'newly[- ]diagnosed\s+glioblastoma',
        r'temozolomide', r'stupp\s+(?:protocol|regimen)', r'concomitant\s+(?:and\s+adjuvant\s+)?'
        r'(?:chemo)?radio', r'tumou?r[- ]treating\s+fields|\bttfields\b|optune',
        r'carmustine\s+wafer|gliadel', r'mgmt(?:\s+(?:promoter\s+)?methylation)?',
    ],
    'endpoint_patterns': [
        (r'overall\s+survival', 'OS'),
        (r'(?:modified\s+)?progression[- ]?free\s+survival', 'PFS'),
    ],
    'context_patterns': [r'\bidh[- ]wild', r'extent\s+of\s+resection']
}

RECURRENT_PATTERNS = {
    'detection_keywords': [
        r'recurrent\s+glioblastoma|recurrent\s+(?:high[- ]grade\s+)?glioma',
        r'progressive\s+glioblastoma', r'bevacizumab|avastin', r'regorafenib',
        r'\blomustine\b|\bccnu\b', r'second[- ]line\s+(?:therapy|treatment)',
        r'radiographic\s+response|objective\s+response',
    ],
    'endpoint_patterns': [
        (r'overall\s+survival', 'OS'),
        (r'progression[- ]?free\s+survival\s+at\s+6\s+months|6[- ]month\s+progression|\bpfs6\b',
         'PFS6'),
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'objective\s+response(?:\s+rate)?|radiographic\s+response', 'ORR'),
        (r'time\s+to\s+progression', 'TTP'),
    ],
    'context_patterns': [r'rano\s+criteria', r'pseudoprogression']
}

LOW_GRADE_PATTERNS = {
    'detection_keywords': [
        r'low[- ]grade\s+glioma|lower[- ]grade\s+glioma|grade\s+(?:2|ii|3|iii)\s+glioma',
        r'\bidh[- ](?:1|2)?[- ]?mutant|idh\s+mutation', r'vorasidenib|ivosidenib',
        r'oligodendroglioma|astrocytoma', r'procarbazine[, /-]+lomustine[, /-]+vincristine|\bpcv\b',
        r'1p/19q\s+co[- ]?deletion',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'time\s+to\s+(?:next\s+intervention|progression)', 'TTP'),
    ],
    'context_patterns': [r'malignant\s+transformation', r'seizure\s+control']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'glioma[- ]?specific\s+mortality|glioma\s+mortality',
        r'brain[- ]tumou?r\s+mortality', r'glioma\s+death|death\s+from\s+glioma',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'glioma[- ]?(?:specific\s+)?(?:mortality|death)|brain[- ]tumou?r\s+mortality|'
         r'cancer[- ]specific\s+(?:mortality|survival)', 'GLIOMA_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_glioma_subspecialty(text: str) -> Tuple[str, float]:
    """Detect glioma trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: glioblastoma, recurrent, low_grade, mortality, general_glioma."""
    text_lower = text.lower()
    scores = {'glioblastoma': 0, 'recurrent': 0, 'low_grade': 0, 'mortality': 0}
    for kw in GLIOBLASTOMA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['glioblastoma'] += 1
    for kw in RECURRENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['recurrent'] += 1
    for kw in LOW_GRADE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['low_grade'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_glioma', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_glioma_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'glioblastoma': GLIOBLASTOMA_PATTERNS['endpoint_patterns'],
        'recurrent': RECURRENT_PATTERNS['endpoint_patterns'],
        'low_grade': LOW_GRADE_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_glioma_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical glioma endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in GLIOMA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
