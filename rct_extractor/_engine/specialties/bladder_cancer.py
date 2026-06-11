"""
Bladder Cancer Subspecialty Patterns and Endpoints

Per-disease profile (same shape as prostate_cancer / cervical_cancer). Urothelial
bladder cancer RCTs report a distinct endpoint vocabulary spanning non-muscle-
invasive, muscle-invasive and advanced/metastatic settings.

Subspecialties:
- nmibc (non-muscle-invasive bladder cancer): recurrence-free survival,
  progression to muscle-invasive disease, high-grade recurrence. Agents:
  intravesical BCG, mitomycin C, gemcitabine.
- mibc (muscle-invasive, neoadjuvant / cystectomy): pathological complete
  response, disease-free survival, overall survival. Regimens: neoadjuvant
  cisplatin-based chemotherapy (gemcitabine-cisplatin, ddMVAC), radical cystectomy.
- advanced (metastatic urothelial carcinoma): overall survival, progression-free
  survival, objective response. Agents: platinum, pembrolizumab, atezolizumab,
  avelumab maintenance, enfortumab vedotin, nivolumab.
- mortality: bladder-cancer-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, DFS, RFS) -> HR; binary (objective
response, pathological complete response, recurrence, progression) -> RR/OR/RD/HR.
"""
from typing import Dict, List, Tuple, Optional
import re

BLADDER_CANCER_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'advanced', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'progression free survival'],
            'subspecialty': 'advanced', 'measure_types': ['HR', 'median']},
    'ORR': {'aliases': ['objective response rate', 'orr', 'overall response rate',
                        'tumor response', 'tumour response'],
            'subspecialty': 'advanced', 'measure_types': ['OR', 'RR', 'rate']},
    'RFS': {'aliases': ['recurrence-free survival', 'rfs', 'event-free survival',
                        'high-grade recurrence-free survival', 'efs'],
            'subspecialty': 'nmibc', 'measure_types': ['HR', 'median']},
    'PROGRESSION_TO_MIBC': {
        'aliases': ['progression to muscle-invasive', 'progression to muscle invasive',
                    'progression-free survival to muscle-invasive',
                    'progression to muscle-invasive disease', 'disease progression'],
        'subspecialty': 'nmibc', 'measure_types': ['HR', 'RR', 'OR']},
    'PCR': {'aliases': ['pathological complete response', 'pathologic complete response',
                        'pcr', 'pathological downstaging', 'pt0 rate'],
            'subspecialty': 'mibc', 'measure_types': ['OR', 'RR', 'RD']},
    'DFS': {'aliases': ['disease-free survival', 'dfs', 'relapse-free survival'],
            'subspecialty': 'mibc', 'measure_types': ['HR', 'median']},
    'BLADDER_CANCER_MORTALITY': {
        'aliases': ['bladder cancer mortality', 'bladder-cancer mortality',
                    'bladder cancer-specific mortality', 'bladder cancer death',
                    'cancer-specific mortality', 'cancer-specific survival'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
}

NMIBC_PATTERNS = {
    'detection_keywords': [
        r'non[- ]?muscle[- ]?invasive\s+bladder|\bnmibc\b',
        r'intravesical\s+(?:bcg|bacillus|mitomycin|gemcitabine)',
        r'bacillus\s+calmette[- ]gu[ée]rin|\bbcg\b', r'mitomycin\s*c?',
        r'high[- ]grade\s+(?:ta|t1)|carcinoma\s+in\s+situ|\bcis\b',
        r'transurethral\s+resection|\bturbt\b',
    ],
    'endpoint_patterns': [
        (r'recurrence[- ]?free\s+survival|high[- ]grade\s+recurrence[- ]?free|'
         r'event[- ]?free\s+survival', 'RFS'),
        (r'progression\s+to\s+muscle[- ]?invasive|progression[- ]?free\s+survival\s+to\s+muscle',
         'PROGRESSION_TO_MIBC'),
    ],
    'context_patterns': [r'maintenance\s+bcg', r'induction\s+bcg']
}

MIBC_PATTERNS = {
    'detection_keywords': [
        r'muscle[- ]?invasive\s+bladder|\bmibc\b', r'neoadjuvant\s+(?:chemo)?therapy',
        r'radical\s+cystectomy', r'gemcitabine[- ,/]+cisplatin|\bddmvac\b|\bmvac\b',
        r'bladder[- ]preservation|trimodal', r'cisplatin[- ]based\s+(?:neoadjuvant|chemo)',
    ],
    'endpoint_patterns': [
        (r'patholog(?:ic|ical)\s+complete\s+response|\bpcr\b|pt0\s+rate|'
         r'patholog(?:ic|ical)\s+downstaging', 'PCR'),
        (r'disease[- ]?free\s+survival|relapse[- ]?free\s+survival', 'DFS'),
        (r'overall\s+survival', 'OS'),
    ],
    'context_patterns': [r'lymph[- ]node', r'downstaging']
}

ADVANCED_PATTERNS = {
    'detection_keywords': [
        r'metastatic\s+urothelial|advanced\s+urothelial|la/mUC|metastatic\s+bladder',
        r'pembrolizumab|keytruda', r'atezolizumab|tecentriq', r'avelumab|bavencio',
        r'nivolumab|opdivo', r'enfortumab(?:\s+vedotin)?|padcev', r'sacituzumab',
        r'platinum[- ](?:refractory|ineligible|based)', r'maintenance\s+(?:avelumab|immunotherapy)',
    ],
    'endpoint_patterns': [
        (r'overall\s+survival', 'OS'),
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'objective\s+response\s+rate|overall\s+response\s+rate|tumou?r\s+response', 'ORR'),
    ],
    'context_patterns': [r'pd[- ]?l1', r'recist']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'bladder\s+cancer[- ]?specific\s+mortality|bladder[- ]cancer\s+mortality',
        r'bladder\s+cancer\s+death|death\s+from\s+bladder\s+cancer',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'bladder\s+cancer[- ]?(?:specific\s+)?(?:mortality|death)|'
         r'death\s+from\s+bladder\s+cancer|cancer[- ]specific\s+(?:mortality|survival)',
         'BLADDER_CANCER_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_bladder_cancer_subspecialty(text: str) -> Tuple[str, float]:
    """Detect bladder-cancer trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: nmibc, mibc, advanced, mortality, general_bladder_cancer."""
    text_lower = text.lower()
    scores = {'nmibc': 0, 'mibc': 0, 'advanced': 0, 'mortality': 0}
    for kw in NMIBC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['nmibc'] += 1
    for kw in MIBC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mibc'] += 1
    for kw in ADVANCED_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['advanced'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_bladder_cancer', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_bladder_cancer_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'nmibc': NMIBC_PATTERNS['endpoint_patterns'],
        'mibc': MIBC_PATTERNS['endpoint_patterns'],
        'advanced': ADVANCED_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_bladder_cancer_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical bladder-cancer endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in BLADDER_CANCER_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
