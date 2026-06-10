"""
Leukaemia Subspecialty Patterns and Endpoints

Per-disease profile (same shape as prostate_cancer / cervical_cancer). Leukaemia
RCTs report a distinct, heme-specific endpoint vocabulary — complete remission,
measurable (minimal) residual disease negativity, molecular and cytogenetic
response, relapse — that the generic oncology bucket does not split out.

Subspecialties (by leukaemia subtype):
- aml (acute myeloid leukaemia): complete remission (CR/CRi), overall survival,
  event-free survival, MRD negativity, relapse. Agents: cytarabine + daunorubicin
  ("7+3"), venetoclax + azacitidine, midostaurin, gemtuzumab ozogamicin, CPX-351.
- all (acute lymphoblastic leukaemia): complete remission, overall survival,
  event-free survival, MRD negativity. Agents: blinatumomab, inotuzumab
  ozogamicin, tisagenlecleucel (CAR-T), imatinib (Ph+).
- cll (chronic lymphocytic leukaemia): progression-free survival, overall
  survival, objective response, undetectable MRD. Agents: ibrutinib, acalabrutinib,
  venetoclax, obinutuzumab, rituximab, FCR, chlorambucil.
- cml (chronic myeloid leukaemia): major molecular response (MMR / MR3),
  deep molecular response (MR4.5), complete cytogenetic response, overall survival.
  Agents: imatinib, dasatinib, nilotinib, bosutinib, ponatinib, asciminib.

Effect measures: time-to-event (OS, EFS, PFS, relapse-free) -> HR; binary
(complete remission, MRD negativity, molecular/cytogenetic response, relapse) ->
RR/OR/RD/HR.
"""
from typing import Dict, List, Tuple, Optional
import re

LEUKAEMIA_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'aml', 'measure_types': ['HR', 'median', 'rate']},
    'EFS': {'aliases': ['event-free survival', 'efs'],
            'subspecialty': 'aml', 'measure_types': ['HR', 'median']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'progression free survival'],
            'subspecialty': 'cll', 'measure_types': ['HR', 'median']},
    'COMPLETE_REMISSION': {
        'aliases': ['complete remission', 'complete response', 'cr rate',
                    'complete remission rate', 'cr/cri', 'cri',
                    'complete remission with incomplete', 'morphologic complete remission'],
        'subspecialty': 'aml', 'measure_types': ['OR', 'RR', 'RD']},
    'MRD_NEGATIVITY': {
        'aliases': ['mrd negativity', 'measurable residual disease negativity',
                    'minimal residual disease negativity', 'undetectable mrd',
                    'umrd', 'mrd-negative', 'mrd negative response', 'negative mrd'],
        'subspecialty': 'aml', 'measure_types': ['OR', 'RR', 'RD']},
    'ORR': {'aliases': ['objective response rate', 'orr', 'overall response rate'],
            'subspecialty': 'cll', 'measure_types': ['OR', 'RR', 'rate']},
    'MMR': {'aliases': ['major molecular response', 'mmr', 'mr3',
                        'molecular response', 'deep molecular response', 'mr4.5'],
            'subspecialty': 'cml', 'measure_types': ['OR', 'RR', 'RD']},
    'CCYR': {'aliases': ['complete cytogenetic response', 'ccyr', 'ccgr',
                         'cytogenetic response'],
             'subspecialty': 'cml', 'measure_types': ['OR', 'RR', 'RD']},
    'RELAPSE': {'aliases': ['relapse', 'cumulative incidence of relapse',
                            'relapse rate', 'disease relapse', 'recurrence'],
                'subspecialty': 'aml', 'measure_types': ['HR', 'RR', 'OR']},
    'LEUKAEMIA_MORTALITY': {
        'aliases': ['leukemia mortality', 'leukaemia mortality',
                    'treatment-related mortality', 'leukemia-related mortality',
                    'non-relapse mortality', 'cancer-specific mortality'],
        'subspecialty': 'aml', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'aml', 'measure_types': ['HR', 'RR', 'OR']},
}

AML_PATTERNS = {
    'detection_keywords': [
        r'acute\s+myeloid\s+leuk(?:a)?emia|\baml\b', r'cytarabine',
        r'daunorubicin|idarubicin', r'\b7\s*\+\s*3\b', r'venetoclax',
        r'azacitidine|decitabine', r'midostaurin|gilteritinib|quizartinib',
        r'gemtuzumab|cpx[- ]?351|vyxeos', r'\bflt3\b|\bnpm1\b|\bidh[12]\b',
    ],
    'endpoint_patterns': [
        (r'complete\s+remission(?:\s+with\s+incomplete)?|\bcr/cri\b|\bcri\b|'
         r'morphologic\s+complete\s+remission|complete\s+response', 'COMPLETE_REMISSION'),
        (r'(?:measurable|minimal)\s+residual\s+disease\s+negativ|mrd[- ]negativ|'
         r'undetectable\s+mrd|\bumrd\b|negative\s+mrd', 'MRD_NEGATIVITY'),
        (r'event[- ]?free\s+survival', 'EFS'),
        (r'overall\s+survival', 'OS'),
        (r'(?:cumulative\s+incidence\s+of\s+)?relapse|disease\s+relapse', 'RELAPSE'),
    ],
    'context_patterns': [r'induction|consolidation', r'allogeneic\s+(?:hsct|transplant)']
}

ALL_PATTERNS = {
    'detection_keywords': [
        r'acute\s+lymph(?:o)?blastic\s+leuk(?:a)?emia|\ball\b(?=.*leuk)',
        r'blinatumomab', r'inotuzumab', r'tisagenlecleucel|car[- ]?t',
        r'vincristine|asparaginase', r'philadelphia[- ]chromosome|ph[- ]?positive|ph\+',
        r'imatinib|dasatinib(?=.*all)',
    ],
    'endpoint_patterns': [
        (r'complete\s+remission|complete\s+response|\bcr\s+rate\b', 'COMPLETE_REMISSION'),
        (r'(?:measurable|minimal)\s+residual\s+disease\s+negativ|mrd[- ]negativ|'
         r'undetectable\s+mrd|\bumrd\b', 'MRD_NEGATIVITY'),
        (r'event[- ]?free\s+survival', 'EFS'),
        (r'overall\s+survival', 'OS'),
    ],
    'context_patterns': [r'relapsed[- /]refractory|\br/r\b', r'paediatric|pediatric']
}

CLL_PATTERNS = {
    'detection_keywords': [
        r'chronic\s+lymphocytic\s+leuk(?:a)?emia|\bcll\b', r'small\s+lymphocytic\s+lymphoma',
        r'ibrutinib|acalabrutinib|zanubrutinib', r'venetoclax', r'obinutuzumab',
        r'rituximab', r'\bfcr\b|fludarabine', r'chlorambucil', r'\bbtk\b\s+inhibitor',
        r'del\(?17p\)?|tp53', r'\bigvh\b',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'objective\s+response\s+rate|overall\s+response\s+rate', 'ORR'),
        (r'undetectable\s+mrd|\bumrd\b|(?:measurable|minimal)\s+residual\s+disease\s+negativ|'
         r'mrd[- ]negativ', 'MRD_NEGATIVITY'),
    ],
    'context_patterns': [r'treatment[- ]naive|previously\s+untreated', r'fixed[- ]duration']
}

CML_PATTERNS = {
    'detection_keywords': [
        r'chronic\s+myeloid\s+leuk(?:a)?emia|\bcml\b', r'imatinib|gleevec|glivec',
        r'dasatinib|nilotinib|bosutinib|ponatinib|asciminib', r'bcr[- ]?abl',
        r'tyrosine[- ]kinase\s+inhibitor|\btki\b', r'chronic[- ]phase',
        r'major\s+molecular\s+response|\bmmr\b', r'cytogenetic\s+response',
    ],
    'endpoint_patterns': [
        (r'major\s+molecular\s+response|\bmmr\b|\bmr3\b|deep\s+molecular\s+response|'
         r'\bmr4\.?5?\b|molecular\s+response', 'MMR'),
        (r'complete\s+cytogenetic\s+response|\bccyr\b|\bccgr\b|cytogenetic\s+response',
         'CCYR'),
        (r'overall\s+survival', 'OS'),
        (r'progression[- ]?free\s+survival', 'PFS'),
    ],
    'context_patterns': [r'bcr[- ]?abl1?\s+transcript', r'international\s+scale|\bis\b']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'treatment[- ]related\s+mortality|non[- ]relapse\s+mortality',
        r'leuk(?:a)?emia[- ]related\s+mortality', r'all[- ]cause\s+mortality',
        r'cancer[- ]specific\s+(?:mortality|survival)',
    ],
    'endpoint_patterns': [
        (r'treatment[- ]related\s+mortality|non[- ]relapse\s+mortality|'
         r'leuk(?:a)?emia[- ]related\s+mortality|cancer[- ]specific\s+(?:mortality|survival)',
         'LEUKAEMIA_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'day[- ]?(?:30|60|100)\s+mortality']
}


def detect_leukaemia_subspecialty(text: str) -> Tuple[str, float]:
    """Detect leukaemia trial subspecialty by subtype. Returns (subspecialty, confidence).
    Subspecialties: aml, all, cll, cml, general_leukaemia."""
    text_lower = text.lower()
    scores = {'aml': 0, 'all': 0, 'cll': 0, 'cml': 0}
    for kw in AML_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['aml'] += 1
    for kw in ALL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['all'] += 1
    for kw in CLL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['cll'] += 1
    for kw in CML_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['cml'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_leukaemia', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_leukaemia_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'aml': AML_PATTERNS['endpoint_patterns'],
        'all': ALL_PATTERNS['endpoint_patterns'],
        'cll': CLL_PATTERNS['endpoint_patterns'],
        'cml': CML_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_leukaemia_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical leukaemia endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in LEUKAEMIA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
