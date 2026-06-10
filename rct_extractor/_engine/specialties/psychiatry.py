"""
Psychiatry Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the malaria / HIV / hepatitis /
respiratory / stroke profiles. Psychiatry RCTs report an endpoint vocabulary
anchored on a handful of standardised rating scales (MADRS, HAM-D/HDRS, PHQ-9,
HAM-A, GAD-7, YMRS, PANSS, CGI) plus dichotomised response/remission/relapse
outcomes that the generic effect-size engine does not recognise on its own.

Subspecialties:
- Depression (major depressive disorder):
    treatment response (>=50% reduction in a depression score; RR/OR),
    remission (RR/OR), MADRS change (Montgomery-Asberg; MD), HAM-D / HDRS change
    (Hamilton depression; MD), PHQ-9 change (MD), relapse/recurrence of
    depression (HR/RR).
- Anxiety (generalized anxiety disorder):
    HAM-A change (Hamilton anxiety; MD), GAD-7 change (MD), anxiety response
    (RR/OR).
- Bipolar disorder (mania / mood relapse):
    YMRS change (Young Mania Rating Scale; MD), mania response (RR/OR),
    recurrence of a mood episode (HR/RR).
- Psychosis (schizophrenia):
    PANSS total change (Positive and Negative Syndrome Scale; MD), psychosis
    response (>=30% PANSS reduction; RR/OR), psychotic relapse (HR/RR),
    CGI (Clinical Global Impression; MD).

Effect measures follow what these trials report: binary (response, remission,
mania response, psychosis response) -> RR/OR/RD; time-to-event / recurrence
(relapse of depression, mood relapse, psychotic relapse) -> HR/RR; continuous
(MADRS, HAM-D, PHQ-9, HAM-A, GAD-7, YMRS, PANSS, CGI) -> MD/SMD. All psychiatric
rating scales are bounded interval scales, NOT log-normal, so no log-scale
pooling is needed (the log-normal set is empty).

Routing note (coordinated with neurology): neurology's bucket also carries a bare
'relapse' keyword (multiple-sclerosis annualized relapse rate). To avoid stealing
MS trials, psychiatry NEVER claims bare 'relapse', 'response', or 'remission' as
detection keywords; it anchors on psych-specific terms (depression, major
depressive disorder, MDD, schizophrenia, bipolar, mania/manic, psychosis,
antidepressant, antipsychotic, MADRS, HAM-D, Hamilton depression, PANSS, YMRS,
anxiety disorder, GAD). Relapse endpoints are matched only when qualified
('relapse of depression', 'mood relapse', 'psychotic relapse').
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# PSYCHIATRY ENDPOINTS
# ============================================================

PSYCHIATRY_ENDPOINTS = {
    # --- Depression (MDD) ---
    'RESPONSE': {
        'aliases': ['treatment response', 'clinical response', 'response rate',
                    'antidepressant response', '>=50% reduction', '50% reduction',
                    'at least 50% reduction', 'responders', 'response'],
        'subspecialty': 'depression',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'REMISSION': {
        'aliases': ['remission', 'clinical remission', 'depression remission',
                    'remitters', 'remission rate', 'sustained remission'],
        'subspecialty': 'depression',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MADRS_CHANGE': {
        'aliases': ['montgomery-asberg depression rating scale', 'montgomery asberg',
                    'montgomery-asberg', 'madrs', 'madrs total score',
                    'change in madrs', 'madrs change', 'change from baseline in madrs'],
        'subspecialty': 'depression',
        'measure_types': ['MD', 'SMD']
    },
    'HAMD_CHANGE': {
        'aliases': ['hamilton depression rating scale', 'hamilton rating scale for depression',
                    'hamilton depression', 'ham-d', 'hamd', 'hdrs', 'hdrs-17', 'ham-d17',
                    'change in ham-d', 'change in hamd', 'hamd change'],
        'subspecialty': 'depression',
        'measure_types': ['MD', 'SMD']
    },
    'PHQ9_CHANGE': {
        'aliases': ['patient health questionnaire-9', 'patient health questionnaire 9',
                    'phq-9', 'phq9', 'phq-9 score', 'change in phq-9', 'phq-9 change'],
        'subspecialty': 'depression',
        'measure_types': ['MD', 'SMD']
    },
    'RELAPSE_DEPRESSION': {
        'aliases': ['relapse of depression', 'depressive relapse', 'relapse of major depression',
                    'recurrence of depression', 'depression recurrence', 'depressive recurrence',
                    'relapse or recurrence of depression'],
        'subspecialty': 'depression',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- Anxiety (GAD) ---
    'HAMA_CHANGE': {
        'aliases': ['hamilton anxiety rating scale', 'hamilton rating scale for anxiety',
                    'hamilton anxiety', 'ham-a', 'hama', 'change in ham-a', 'hama change',
                    'change from baseline in ham-a'],
        'subspecialty': 'anxiety',
        'measure_types': ['MD', 'SMD']
    },
    'GAD7_CHANGE': {
        'aliases': ['generalized anxiety disorder 7-item scale', 'gad-7', 'gad7',
                    'gad-7 score', 'change in gad-7', 'gad-7 change'],
        'subspecialty': 'anxiety',
        'measure_types': ['MD', 'SMD']
    },
    'ANXIETY_RESPONSE': {
        'aliases': ['anxiety response', 'anxiety treatment response',
                    'anxiety remission', 'response in anxiety'],
        'subspecialty': 'anxiety',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Bipolar disorder ---
    'YMRS_CHANGE': {
        'aliases': ['young mania rating scale', 'young mania', 'ymrs', 'ymrs total score',
                    'change in ymrs', 'ymrs change', 'change from baseline in ymrs'],
        'subspecialty': 'bipolar',
        'measure_types': ['MD', 'SMD']
    },
    'MANIA_RESPONSE': {
        'aliases': ['mania response', 'manic response', 'antimanic response',
                    'response in mania', 'remission of mania', 'manic remission'],
        'subspecialty': 'bipolar',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MOOD_RELAPSE': {
        'aliases': ['mood relapse', 'mood episode relapse', 'recurrence of mood episode',
                    'recurrence of a mood episode', 'mood episode recurrence',
                    'relapse to any mood episode', 'recurrence of any mood episode'],
        'subspecialty': 'bipolar',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- Psychosis (schizophrenia) ---
    'PANSS_CHANGE': {
        'aliases': ['positive and negative syndrome scale', 'panss', 'panss total score',
                    'panss total', 'change in panss', 'panss change',
                    'change from baseline in panss', 'panss total change'],
        'subspecialty': 'psychosis',
        'measure_types': ['MD', 'SMD']
    },
    'PSYCHOSIS_RESPONSE': {
        'aliases': ['psychosis response', 'treatment response in schizophrenia',
                    '>=30% reduction in panss', '30% reduction in panss',
                    'at least 30% reduction in panss', 'panss response', 'responders'],
        'subspecialty': 'psychosis',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PSYCHOSIS_RELAPSE': {
        'aliases': ['psychotic relapse', 'relapse of psychosis', 'schizophrenia relapse',
                    'relapse of schizophrenia', 'psychosis relapse', 'time to relapse'],
        'subspecialty': 'psychosis',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'CGI': {
        'aliases': ['clinical global impression', 'clinical global impression-severity',
                    'clinical global impression severity', 'cgi-s', 'cgi-i', 'cgi severity',
                    'cgi improvement', 'cgi score', 'cgi'],
        'subspecialty': 'psychosis',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# DEPRESSION PATTERNS (MDD)
# ============================================================

DEPRESSION_PATTERNS = {
    'detection_keywords': [
        r'major\s+depressive\s+disorder|\bmdd\b', r'depression|depressive\s+(?:disorder|episode|symptoms?)',
        r'antidepressant', r'treatment[- ]resistant\s+depression|\btrd\b',
        r'montgomery[- ]asberg|\bmadrs\b',
        r'hamilton\s+depression|hamilton\s+rating\s+scale\s+for\s+depression|\bham-?d\b|\bhdrs\b',
        r'patient\s+health\s+questionnaire|\bphq-?9\b',
        r'\bssri\b|\bsnri\b', r'esketamine|ketamine', r'zuranolone|brexanolone',
    ],
    'endpoint_patterns': [
        # MADRS before generic response/remission so the scale wins its own tag.
        (r'montgomery[- ]asberg(?:\s+depression\s+rating\s+scale)?|\bmadrs\b|'
         r'change\s+(?:from\s+baseline\s+)?in\s+madrs', 'MADRS_CHANGE'),
        (r'hamilton\s+(?:depression\s+)?rating\s+scale(?:\s+for\s+depression)?|hamilton\s+depression|'
         r'\bham-?d(?:17|-17)?\b|\bhdrs(?:-17)?\b|change\s+in\s+ham-?d', 'HAMD_CHANGE'),
        (r'patient\s+health\s+questionnaire-?9?|\bphq-?9\b|change\s+in\s+phq-?9', 'PHQ9_CHANGE'),
        (r'relapse\s+(?:or\s+recurrence\s+)?of\s+(?:major\s+)?depression|depressive\s+relapse|'
         r'recurrence\s+of\s+depression|depressi(?:ve|on)\s+recurrence', 'RELAPSE_DEPRESSION'),
        (r'clinical\s+remission|depression\s+remission|sustained\s+remission|'
         r'remission\s+rate|remitters?|\bremission\b', 'REMISSION'),
        (r'treatment\s+response|clinical\s+response|antidepressant\s+response|response\s+rate|'
         r'(?:at\s+least\s+|>=|≥)?\s*50%\s+reduction|responders?', 'RESPONSE'),
    ],
    'context_patterns': [
        r'change\s+from\s+baseline', r'week\s+(?:6|8|12)', r'double[- ]blind',
    ]
}


# ============================================================
# ANXIETY PATTERNS (GAD)
# ============================================================

ANXIETY_PATTERNS = {
    'detection_keywords': [
        r'generali[sz]ed\s+anxiety\s+disorder|\bgad\b', r'anxiety\s+disorder',
        r'anxiety\s+symptoms?', r'anxiolytic',
        r'hamilton\s+anxiety|\bham-?a\b|\bhama\b',
        r'\bgad-?7\b',
    ],
    'endpoint_patterns': [
        (r'hamilton\s+(?:rating\s+scale\s+for\s+)?anxiety|\bham-?a\b|\bhama\b|'
         r'change\s+(?:from\s+baseline\s+)?in\s+ham-?a', 'HAMA_CHANGE'),
        (r'generali[sz]ed\s+anxiety\s+disorder\s+7|\bgad-?7\b|change\s+in\s+gad-?7', 'GAD7_CHANGE'),
        (r'anxiety\s+(?:treatment\s+)?response|response\s+in\s+anxiety|anxiety\s+remission',
         'ANXIETY_RESPONSE'),
    ],
    'context_patterns': [
        r'change\s+from\s+baseline', r'week\s+(?:6|8)', r'double[- ]blind',
    ]
}


# ============================================================
# BIPOLAR PATTERNS
# ============================================================

BIPOLAR_PATTERNS = {
    'detection_keywords': [
        r'bipolar(?:\s+(?:disorder|i|ii|depression|mania))?', r'\bmania\b|\bmanic\b',
        r'acute\s+mania', r'mood\s+stabili[sz]er', r'young\s+mania\s+rating\s+scale|\bymrs\b',
        r'lithium', r'valproate|divalproex|valproic', r'lamotrigine',
    ],
    'endpoint_patterns': [
        (r'young\s+mania\s+rating\s+scale|\bymrs\b|change\s+(?:from\s+baseline\s+)?in\s+ymrs',
         'YMRS_CHANGE'),
        (r'mood\s+(?:episode\s+)?relapse|recurrence\s+of\s+(?:a\s+|any\s+)?mood\s+episode|'
         r'mood\s+episode\s+recurrence|relapse\s+to\s+any\s+mood\s+episode', 'MOOD_RELAPSE'),
        (r'manic?\s+response|antimanic\s+response|response\s+in\s+mania|'
         r'remission\s+of\s+mania|manic\s+remission', 'MANIA_RESPONSE'),
    ],
    'context_patterns': [
        r'change\s+from\s+baseline', r'week\s+3', r'double[- ]blind',
    ]
}


# ============================================================
# PSYCHOSIS PATTERNS (schizophrenia)
# ============================================================

PSYCHOSIS_PATTERNS = {
    'detection_keywords': [
        r'schizophrenia|schizoaffective', r'\bpsychosis\b|psychotic\s+(?:disorder|symptoms?|episode)',
        r'antipsychotic', r'positive\s+and\s+negative\s+syndrome\s+scale|\bpanss\b',
        r'clinical\s+global\s+impression|\bcgi(?:-[si])?\b',
        r'risperidone|paliperidone|olanzapine|quetiapine|aripiprazole|brexpiprazole',
        r'cariprazine|lurasidone|lumateperone|haloperidol|clozapine',
    ],
    'endpoint_patterns': [
        (r'positive\s+and\s+negative\s+syndrome\s+scale|\bpanss(?:\s+total)?\b|'
         r'change\s+(?:from\s+baseline\s+)?in\s+panss', 'PANSS_CHANGE'),
        (r'psychotic\s+relapse|relapse\s+of\s+(?:psychosis|schizophrenia)|'
         r'schizophrenia\s+relapse|psychosis\s+relapse', 'PSYCHOSIS_RELAPSE'),
        (r'(?:at\s+least\s+|>=|≥)?\s*30%\s+reduction\s+in\s+panss|panss\s+response|'
         r'(?:treatment\s+)?response\s+in\s+schizophrenia|psychosis\s+response', 'PSYCHOSIS_RESPONSE'),
        (r'clinical\s+global\s+impression(?:[- ](?:severity|improvement))?|\bcgi(?:-[si])?\b',
         'CGI'),
    ],
    'context_patterns': [
        r'change\s+from\s+baseline', r'week\s+6', r'double[- ]blind', r'acute\s+exacerbation',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_psychiatry_subspecialty(text: str) -> Tuple[str, float]:
    """Detect psychiatry trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: depression, anxiety, bipolar, psychosis."""
    text_lower = text.lower()
    scores = {'depression': 0, 'anxiety': 0, 'bipolar': 0, 'psychosis': 0}
    for kw in DEPRESSION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['depression'] += 1
    for kw in ANXIETY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['anxiety'] += 1
    for kw in BIPOLAR_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['bipolar'] += 1
    for kw in PSYCHOSIS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['psychosis'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('depression', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_psychiatry_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'depression': DEPRESSION_PATTERNS['endpoint_patterns'],
        'anxiety': ANXIETY_PATTERNS['endpoint_patterns'],
        'bipolar': BIPOLAR_PATTERNS['endpoint_patterns'],
        'psychosis': PSYCHOSIS_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_psychiatry_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical psychiatry endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in PSYCHIATRY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
