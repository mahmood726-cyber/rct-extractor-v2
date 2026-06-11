"""
Schizophrenia Subspecialty Patterns and Endpoints

Built for the same meta-analysis extraction workflow as the malaria / TB / HIV
profiles. Schizophrenia RCTs report a distinct endpoint vocabulary (PANSS total /
positive / negative change, >=30%/>=50% PANSS response, CGI, relapse, all-cause
discontinuation, antipsychotic-induced weight gain / EPS / akathisia / prolactin)
that the generic effect-size engine does not recognise.

Subspecialties (mapped onto the registry's generic pattern slots):
- acute (TREATMENT slot): acute-episode / acute-exacerbation treatment — change in
  PANSS total, >=30%/>=50% PANSS responder, CGI-I/CGI-S. Atypical and typical
  antipsychotics; xanomeline-trospium (KarXT).
- maintenance (DRUG_RESISTANT slot): relapse prevention / maintenance — relapse,
  time to relapse, rehospitalization, all-cause discontinuation; long-acting
  injectables (LAIs).
- negative_cognitive (PREVENTION slot): negative-symptom and cognitive endpoints —
  PANSS negative, SANS, MCCB cognition, social functioning.
- safety (LATENT slot): antipsychotic safety / treatment-resistant — clozapine in
  treatment-resistant schizophrenia, weight gain, metabolic, EPS / akathisia,
  prolactin.

Effect measures: PANSS / CGI / weight / cognition change -> mean difference;
response / relapse / discontinuation / rehospitalization -> RR/OR/HR; EPS /
akathisia / weight-gain incidence -> RR/OR via the core engine.
"""
from typing import Dict, List, Tuple, Optional
import re

SCHIZOPHRENIA_ENDPOINTS = {
    'PANSS_TOTAL': {
        'aliases': ['panss total', 'panss total score', 'change in panss',
                    'positive and negative syndrome scale', 'total panss',
                    'panss total change', 'panss'],
        'subspecialty': 'acute',
        'measure_types': ['MD', 'SMD']
    },
    'PANSS_POSITIVE': {
        'aliases': ['panss positive', 'panss positive subscale', 'positive symptoms',
                    'positive symptom score'],
        'subspecialty': 'acute',
        'measure_types': ['MD']
    },
    'PANSS_NEGATIVE': {
        'aliases': ['panss negative', 'panss negative subscale', 'negative symptoms',
                    'sans', 'negative symptom score', 'negative symptom factor'],
        'subspecialty': 'negative_cognitive',
        'measure_types': ['MD', 'SMD']
    },
    'CGI': {
        'aliases': ['cgi', 'cgi-s', 'cgi-i', 'clinical global impression',
                    'clinical global impressions severity'],
        'subspecialty': 'acute',
        'measure_types': ['MD', 'RR']
    },
    'RESPONSE': {
        'aliases': ['response', 'responder', 'responder rate', '30% reduction in panss',
                    '50% reduction in panss', 'treatment response', '>=30% panss',
                    'panss responder', 'clinical response'],
        'subspecialty': 'acute',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RELAPSE': {
        'aliases': ['relapse', 'time to relapse', 'relapse rate', 'risk of relapse',
                    'psychotic relapse', 'exacerbation or relapse', 'impending relapse'],
        'subspecialty': 'maintenance',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'HOSPITALIZATION': {
        'aliases': ['hospitalization', 'rehospitalization', 'hospital admission',
                    'psychiatric hospitalization', 'rehospitalisation', 'hospitalisation'],
        'subspecialty': 'maintenance',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'ALL_CAUSE_DISCONTINUATION': {
        'aliases': ['all-cause discontinuation', 'discontinuation for any cause',
                    'treatment discontinuation', 'all cause discontinuation',
                    'discontinuation due to any cause', 'time to discontinuation'],
        'subspecialty': 'maintenance',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'COGNITION': {
        'aliases': ['cognition', 'cognitive function', 'mccb', 'matrics',
                    'cognitive performance', 'neurocognition', 'cognitive composite'],
        'subspecialty': 'negative_cognitive',
        'measure_types': ['MD', 'SMD']
    },
    'FUNCTIONING': {
        'aliases': ['social functioning', 'psychosocial functioning', 'psp',
                    'personal and social performance', 'functional outcome'],
        'subspecialty': 'negative_cognitive',
        'measure_types': ['MD']
    },
    'WEIGHT_GAIN': {
        'aliases': ['weight gain', 'body weight change', 'clinically significant weight gain',
                    'weight increase', '7% weight gain', 'change in body weight'],
        'subspecialty': 'safety',
        'measure_types': ['MD', 'RR', 'OR']
    },
    'EPS': {
        'aliases': ['extrapyramidal symptoms', 'eps', 'akathisia', 'parkinsonism',
                    'extrapyramidal side effects', 'tardive dyskinesia', 'dystonia',
                    'use of anticholinergic'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'serious adverse events', 'serious adverse event',
                    'treatment-emergent adverse events', 'prolactin', 'discontinuation due to adverse'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'suicide'],
        'subspecialty': 'safety',
        'measure_types': ['HR', 'RR', 'OR']
    },
}


TREATMENT_PATTERNS = {  # = acute
    'detection_keywords': [
        r'acute\s+(?:episode|exacerbation|schizophreni)|acutely\s+(?:ill|psychotic)',
        r'\bpanss\b|positive\s+and\s+negative\s+syndrome',
        r'risperidone|olanzapine|quetiapine|aripiprazole|paliperidone|lurasidone|'
        r'cariprazine|brexpiprazole|ziprasidone|amisulpride|haloperidol|asenapine',
        r'xanomeline|karxt|muscarinic\s+agonist',
        r'\bcgi[- ]?[si]?\b|clinical\s+global\s+impression',
    ],
    'endpoint_patterns': [
        (r'panss\s+total|total\s+panss|change\s+in\s+panss|positive\s+and\s+negative\s+syndrome',
         'PANSS_TOTAL'),
        (r'panss\s+positive|positive\s+symptom', 'PANSS_POSITIVE'),
        (r'panss\s+negative|negative\s+symptom|\bsans\b', 'PANSS_NEGATIVE'),
        (r'(?:>=?\s*|at\s+least\s+)?(?:30|50)\s*%?\s+(?:reduction|response|responder)|'
         r'responder\s+rate|panss\s+responder|\bresponders?\b', 'RESPONSE'),
        (r'\bcgi[- ]?[si]?\b|clinical\s+global\s+impression', 'CGI'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'change\s+from\s+baseline', r'week\s+6\s+', r'double[- ]blind', r'\bDSM[- ]?(?:IV|5|V)\b',
    ]
}


DRUG_RESISTANT_PATTERNS = {  # = maintenance / relapse prevention
    'detection_keywords': [
        r'relapse\s+prevention|maintenance\s+(?:treatment|therapy|phase)',
        r'long[- ]acting\s+injectable|\blai\b|depot\s+antipsychotic',
        r'time\s+to\s+relapse|impending\s+relapse|rehospitali[sz]ation',
        r'all[- ]cause\s+discontinuation|discontinuation\s+for\s+any',
        r'paliperidone\s+palmitate|aripiprazole\s+(?:once[- ]monthly|lauroxil)|'
        r'risperidone\s+(?:long[- ]acting|microspheres)',
    ],
    'endpoint_patterns': [
        (r'time\s+to\s+relapse|relapse\s+(?:rate|risk)?|impending\s+relapse|'
         r'psychotic\s+relapse|\brelapse\b', 'RELAPSE'),
        (r'rehospitali[sz]ation|hospitali[sz]ation|hospital\s+admission', 'HOSPITALIZATION'),
        (r'all[- ]cause\s+discontinuation|discontinuation\s+(?:for|due\s+to)\s+any|'
         r'treatment\s+discontinuation|time\s+to\s+discontinuation', 'ALL_CAUSE_DISCONTINUATION'),
        (r'panss\s+total|change\s+in\s+panss', 'PANSS_TOTAL'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'every\s+(?:month|4\s+weeks|3\s+months)', r'stabilized\s+patients',
    ]
}


PREVENTION_PATTERNS = {  # = negative_cognitive
    'detection_keywords': [
        r'negative\s+symptoms?|predominant\s+negative|deficit\s+syndrome',
        r'\bsans\b|panss\s+negative|negative\s+symptom\s+factor',
        r'cognitive\s+(?:impairment|function|deficit)|\bmccb\b|matrics|neurocognition',
        r'social\s+functioning|psychosocial\s+functioning|\bpsp\b',
    ],
    'endpoint_patterns': [
        (r'panss\s+negative|negative\s+symptom|\bsans\b', 'PANSS_NEGATIVE'),
        (r'\bmccb\b|matrics|cognitive\s+(?:function|performance|composite)|neurocognition|'
         r'\bcognition\b', 'COGNITION'),
        (r'social\s+functioning|psychosocial\s+functioning|\bpsp\b|'
         r'personal\s+and\s+social\s+performance', 'FUNCTIONING'),
        (r'panss\s+total|change\s+in\s+panss', 'PANSS_TOTAL'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'predominant\s+negative\s+symptoms', r'stable\s+patients',
    ]
}


LATENT_PATTERNS = {  # = safety / treatment-resistant
    'detection_keywords': [
        r'treatment[- ]resistant\s+schizophreni|\btrs\b|clozapine',
        r'weight\s+gain|metabolic\s+(?:syndrome|adverse)|\bprolactin\b',
        r'extrapyramidal|\beps\b|akathisia|tardive\s+dyskinesia|parkinsonism',
        r'adverse\s+events|tolerability|discontinuation\s+due\s+to',
    ],
    'endpoint_patterns': [
        (r'(?:clinically\s+significant\s+)?weight\s+gain|7\s*%?\s+weight|'
         r'change\s+in\s+body\s+weight|weight\s+increase', 'WEIGHT_GAIN'),
        (r'extrapyramidal|\beps\b|akathisia|tardive\s+dyskinesia|parkinsonism|dystonia',
         'EPS'),
        (r'\bprolactin\b|serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
        (r'all[- ]cause\s+discontinuation', 'ALL_CAUSE_DISCONTINUATION'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)|\bsuicide\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'clozapine', r'metabolic\s+parameters', r'fasting\s+glucose|lipids',
    ]
}


def detect_schizophrenia_subspecialty(text: str) -> Tuple[str, float]:
    """Detect schizophrenia trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: acute, maintenance, negative_cognitive, safety, general_scz."""
    text_lower = text.lower()
    scores = {'acute': 0, 'maintenance': 0, 'negative_cognitive': 0, 'safety': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['acute'] += 1
    for kw in DRUG_RESISTANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['maintenance'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['negative_cognitive'] += 1
    for kw in LATENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['safety'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_scz', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_schizophrenia_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'acute': TREATMENT_PATTERNS['endpoint_patterns'],
        'maintenance': DRUG_RESISTANT_PATTERNS['endpoint_patterns'],
        'negative_cognitive': PREVENTION_PATTERNS['endpoint_patterns'],
        'safety': LATENT_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_schizophrenia_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical schizophrenia endpoint, preferring the LONGEST alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in SCHIZOPHRENIA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
