"""
Head and Neck Cancer Subspecialty Patterns and Endpoints

Per-disease profile (same shape as prostate_cancer / cervical_cancer). Head and
neck squamous cell carcinoma (HNSCC) and nasopharyngeal carcinoma (NPC) RCTs report
a distinct endpoint vocabulary — overall and progression-free survival, locoregional
control, distant-metastasis-free survival — across definitive, recurrent/metastatic
and nasopharyngeal settings.

Subspecialties:
- definitive (locally advanced, concurrent chemoradiation): overall survival,
  progression-free survival, locoregional control, disease-free survival. Modalities:
  cisplatin + radiotherapy, cetuximab + radiotherapy, TPF induction.
- recurrent_metastatic (R/M HNSCC): overall survival, progression-free survival,
  objective response. Agents: pembrolizumab, nivolumab, cetuximab + platinum + 5-FU
  (EXTREME), platinum.
- nasopharyngeal (NPC, EBV-related): overall survival, progression-free survival,
  distant-metastasis-free survival. Agents: gemcitabine + cisplatin, induction
  chemotherapy, concurrent chemoradiation.
- mortality: head-and-neck-cancer-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, DFS, DMFS, locoregional control) -> HR;
binary (objective response, locoregional control event) -> RR/OR/RD/HR.
"""
from typing import Dict, List, Tuple, Optional
import re

HEAD_NECK_CANCER_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'definitive', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'progression free survival'],
            'subspecialty': 'definitive', 'measure_types': ['HR', 'median']},
    'LOCOREGIONAL_CONTROL': {
        'aliases': ['locoregional control', 'loco-regional control', 'local control',
                    'locoregional failure', 'locoregional recurrence',
                    'locoregional control rate'],
        'subspecialty': 'definitive', 'measure_types': ['HR', 'RR', 'OR']},
    'DFS': {'aliases': ['disease-free survival', 'dfs', 'recurrence-free survival', 'rfs'],
            'subspecialty': 'definitive', 'measure_types': ['HR', 'median']},
    'ORR': {'aliases': ['objective response rate', 'orr', 'overall response rate',
                        'tumor response', 'tumour response'],
            'subspecialty': 'recurrent_metastatic', 'measure_types': ['OR', 'RR', 'rate']},
    'DMFS': {'aliases': ['distant metastasis-free survival', 'distant-metastasis-free survival',
                         'dmfs', 'distant failure-free survival'],
             'subspecialty': 'nasopharyngeal', 'measure_types': ['HR', 'median']},
    'HEAD_NECK_CANCER_MORTALITY': {
        'aliases': ['head and neck cancer mortality', 'cancer-specific mortality',
                    'head and neck cancer death', 'disease-specific mortality',
                    'cancer-specific survival'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
}

DEFINITIVE_PATTERNS = {
    'detection_keywords': [
        r'locally\s+advanced\s+(?:head\s+and\s+neck|hnscc)', r'concurrent\s+chemoradi',
        r'chemoradi(?:o|ation)therapy|chemoradiation', r'cisplatin(?:[- /]+radi)?',
        r'cetuximab(?:[- /]+radi)?', r'definitive\s+radi(?:o)?therapy',
        r'\btpf\b|docetaxel[- ,/]+cisplatin[- ,/]+(?:5[- ]?fu|fluorouracil)',
        r'induction\s+chemotherapy', r'oropharyngeal|laryngeal|hypopharyngeal|oral\s+cavity',
    ],
    'endpoint_patterns': [
        (r'loco[- ]?regional\s+(?:control|failure|recurrence)', 'LOCOREGIONAL_CONTROL'),
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'disease[- ]?free\s+survival|recurrence[- ]?free\s+survival', 'DFS'),
    ],
    'context_patterns': [r'\bgy\b|gray', r'p16|hpv']
}

RECURRENT_METASTATIC_PATTERNS = {
    'detection_keywords': [
        r'recurrent(?:\s+or)?\s+metastatic\s+(?:head\s+and\s+neck|hnscc)|\br/m\b',
        r'pembrolizumab|keytruda', r'nivolumab|opdivo', r'\bextreme\b',
        r'platinum[- ](?:refractory|resistant)', r'cetuximab',
        r'first[- ]line\s+(?:treatment|therapy)',
    ],
    'endpoint_patterns': [
        (r'overall\s+survival', 'OS'),
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'objective\s+response\s+rate|overall\s+response\s+rate|tumou?r\s+response', 'ORR'),
    ],
    'context_patterns': [r'pd[- ]?l1|combined\s+positive\s+score|\bcps\b', r'recist']
}

NASOPHARYNGEAL_PATTERNS = {
    'detection_keywords': [
        r'nasopharyngeal\s+(?:carcinoma|cancer)|\bnpc\b', r'epstein[- ]barr|\bebv\b',
        r'gemcitabine[- ,/]+cisplatin', r'endemic\s+nasopharyngeal',
        r'plasma\s+ebv\s+dna',
    ],
    'endpoint_patterns': [
        (r'distant[- ]?(?:metastasis|failure)[- ]?free\s+survival', 'DMFS'),
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'loco[- ]?regional\s+(?:control|failure|recurrence)', 'LOCOREGIONAL_CONTROL'),
    ],
    'context_patterns': [r'who\s+type', r'concurrent[- ]adjuvant']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'head\s+and\s+neck\s+cancer\s+mortality|disease[- ]specific\s+mortality',
        r'head\s+and\s+neck\s+cancer\s+death', r'cancer[- ]specific\s+(?:mortality|survival)',
        r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'head\s+and\s+neck\s+cancer\s+(?:mortality|death)|disease[- ]specific\s+mortality|'
         r'cancer[- ]specific\s+(?:mortality|survival)', 'HEAD_NECK_CANCER_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_head_neck_cancer_subspecialty(text: str) -> Tuple[str, float]:
    """Detect head-and-neck-cancer trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: definitive, recurrent_metastatic, nasopharyngeal, mortality,
    general_head_neck_cancer."""
    text_lower = text.lower()
    scores = {'definitive': 0, 'recurrent_metastatic': 0, 'nasopharyngeal': 0, 'mortality': 0}
    for kw in DEFINITIVE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['definitive'] += 1
    for kw in RECURRENT_METASTATIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['recurrent_metastatic'] += 1
    for kw in NASOPHARYNGEAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['nasopharyngeal'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_head_neck_cancer', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_head_neck_cancer_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'definitive': DEFINITIVE_PATTERNS['endpoint_patterns'],
        'recurrent_metastatic': RECURRENT_METASTATIC_PATTERNS['endpoint_patterns'],
        'nasopharyngeal': NASOPHARYNGEAL_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_head_neck_cancer_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical head-and-neck-cancer endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in HEAD_NECK_CANCER_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
