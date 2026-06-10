"""
Lymphoma Subspecialty Patterns and Endpoints

Per-disease profile (same shape as prostate_cancer / cervical_cancer). Lymphoma
RCTs report a distinct endpoint vocabulary — progression-free survival, complete
(metabolic) response by PET, event-free survival, overall survival — across
clinically distinct entities.

Subspecialties:
- hodgkin (Hodgkin lymphoma): progression-free survival, complete metabolic
  response, overall survival. Agents: ABVD, brentuximab vedotin + AVD (BV-AVD),
  escalated BEACOPP, nivolumab, pembrolizumab.
- aggressive (aggressive B-cell NHL, esp. DLBCL): event-free survival,
  progression-free survival, complete response, overall survival. Agents: R-CHOP,
  polatuzumab vedotin (pola-R-CHP), CAR-T (axicabtagene, tisagenlecleucel,
  lisocabtagene), tafasitamab.
- indolent (follicular / marginal-zone NHL): progression-free survival, objective
  response, time to next treatment. Agents: rituximab, obinutuzumab, bendamustine,
  lenalidomide (R2).
- mortality: lymphoma-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, EFS) -> HR; binary (complete response,
objective response, relapse) -> RR/OR/RD/HR.
"""
from typing import Dict, List, Tuple, Optional
import re

LYMPHOMA_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'aggressive', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'progression free survival',
                        'disease progression or death'],
            'subspecialty': 'aggressive', 'measure_types': ['HR', 'median']},
    'EFS': {'aliases': ['event-free survival', 'efs'],
            'subspecialty': 'aggressive', 'measure_types': ['HR', 'median']},
    'CR_RATE': {'aliases': ['complete response rate', 'complete response', 'cr rate',
                            'complete metabolic response', 'complete remission',
                            'cmr', 'pet-negative complete response'],
                'subspecialty': 'hodgkin', 'measure_types': ['OR', 'RR', 'RD']},
    'ORR': {'aliases': ['objective response rate', 'orr', 'overall response rate'],
            'subspecialty': 'indolent', 'measure_types': ['OR', 'RR', 'rate']},
    'TTNT': {'aliases': ['time to next treatment', 'time to next anti-lymphoma treatment',
                         'ttnt', 'time to next therapy'],
             'subspecialty': 'indolent', 'measure_types': ['HR', 'median']},
    'RELAPSE': {'aliases': ['relapse', 'relapse rate', 'disease relapse', 'recurrence',
                            'progression'],
                'subspecialty': 'aggressive', 'measure_types': ['HR', 'RR', 'OR']},
    'LYMPHOMA_MORTALITY': {
        'aliases': ['lymphoma mortality', 'lymphoma-specific mortality',
                    'lymphoma death', 'death from lymphoma', 'cancer-specific mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
}

HODGKIN_PATTERNS = {
    'detection_keywords': [
        r'hodgkin(?:\s+lymphoma|\'?s\s+(?:disease|lymphoma))?', r'\bhl\b(?=.{0,40}lymphoma)',
        r'\babvd\b|\bbeacopp\b', r'brentuximab(?:\s+vedotin)?|adcetris|bv[- ]?avd',
        r'nodular\s+sclerosis', r'reed[- ]sternberg', r'classical\s+hodgkin',
    ],
    'endpoint_patterns': [
        (r'complete\s+(?:metabolic\s+)?response|complete\s+remission|\bcmr\b|'
         r'pet[- ]negative', 'CR_RATE'),
        (r'(?:modified\s+)?progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
    ],
    'context_patterns': [r'deauville', r'interim\s+pet']
}

AGGRESSIVE_PATTERNS = {
    'detection_keywords': [
        r'diffuse\s+large\s+b[- ]?cell\s+lymphoma|\bdlbcl\b', r'\br[- ]?chop\b',
        r'polatuzumab(?:\s+vedotin)?|pola[- ]?r[- ]?chp', r'aggressive\s+(?:b[- ]?cell\s+)?lymphoma',
        r'mantle[- ]cell\s+lymphoma|\bmcl\b', r'burkitt', r'primary\s+mediastinal',
        r'axicabtagene|tisagenlecleucel|lisocabtagene|car[- ]?t', r'tafasitamab',
        r'high[- ]grade\s+b[- ]?cell',
    ],
    'endpoint_patterns': [
        (r'event[- ]?free\s+survival', 'EFS'),
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'complete\s+response(?:\s+rate)?|complete\s+remission', 'CR_RATE'),
    ],
    'context_patterns': [r'\bipi\b|international\s+prognostic\s+index', r'cell\s+of\s+origin']
}

INDOLENT_PATTERNS = {
    'detection_keywords': [
        r'follicular\s+lymphoma|\bfl\b(?=.{0,30}lymphoma)', r'marginal[- ]zone\s+lymphoma|\bmzl\b',
        r'indolent\s+(?:b[- ]?cell\s+)?lymphoma|low[- ]grade\s+lymphoma',
        r'rituximab', r'obinutuzumab', r'bendamustine', r'lenalidomide|\br2\b',
        r'waldenstrom|lymphoplasmacytic',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'objective\s+response\s+rate|overall\s+response\s+rate', 'ORR'),
        (r'time\s+to\s+next\s+(?:anti[- ]lymphoma\s+)?(?:treatment|therapy)|\bttnt\b', 'TTNT'),
        (r'complete\s+response(?:\s+rate)?', 'CR_RATE'),
    ],
    'context_patterns': [r'\bflipi\b', r'tumou?r\s+burden']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'lymphoma[- ]?specific\s+mortality|lymphoma\s+mortality',
        r'lymphoma\s+death|death\s+from\s+lymphoma',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'lymphoma[- ]?(?:specific\s+)?(?:mortality|death)|death\s+from\s+lymphoma|'
         r'cancer[- ]specific\s+(?:mortality|survival)', 'LYMPHOMA_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_lymphoma_subspecialty(text: str) -> Tuple[str, float]:
    """Detect lymphoma trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: hodgkin, aggressive, indolent, mortality, general_lymphoma."""
    text_lower = text.lower()
    scores = {'hodgkin': 0, 'aggressive': 0, 'indolent': 0, 'mortality': 0}
    for kw in HODGKIN_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['hodgkin'] += 1
    for kw in AGGRESSIVE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['aggressive'] += 1
    for kw in INDOLENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['indolent'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_lymphoma', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_lymphoma_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'hodgkin': HODGKIN_PATTERNS['endpoint_patterns'],
        'aggressive': AGGRESSIVE_PATTERNS['endpoint_patterns'],
        'indolent': INDOLENT_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_lymphoma_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical lymphoma endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in LYMPHOMA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
