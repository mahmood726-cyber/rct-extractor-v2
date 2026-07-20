"""
Substance use disorder (SUD) Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the psychiatry profile, but for
SUBSTANCE / OPIOID USE DISORDER specifically -- an addiction-medicine disease not
targeted by any existing profile (the pain profiles use 'opioid' as an
ANALGESIC; this one is about opioid/stimulant USE DISORDER and its treatment).
SUD RCTs report an endpoint vocabulary anchored on treatment retention,
opioid/drug-negative urine drug screens, sustained abstinence, overdose, craving
and opioid-withdrawal severity (COWS/SOWS).

Subspecialties:
- opioid (opioid use disorder, OUD):
    treatment retention (RR/OR/HR), opioid-negative urine drug screen (RR/OR),
    abstinence (RR/OR), overdose / mortality (RR/OR/HR), opioid-withdrawal
    severity (COWS/SOWS; MD). Buprenorphine, methadone, extended-release
    naltrexone (medications for opioid use disorder, MOUD).
- stimulant (cocaine / methamphetamine use disorder):
    drug-negative urine drug screen (RR/OR), abstinence (RR/OR), retention
    (RR/OR). Contingency management, psychostimulant agonist therapy.
- general (cannabis / polysubstance / mixed):
    retention (RR/OR), abstinence (RR/OR), craving (MD).

Effect measures: binary (retention, negative UDS, abstinence, overdose, relapse)
-> RR/OR/RD (retention / overdose / relapse may be HR); continuous (craving,
withdrawal severity) -> MD/SMD. None is log-normal.

Spelling note: the only en-GB/en-US split is 'behaviour'/'behavior' -> handled as
'behaviou?r' inline. No ae/oe vowel traps in this domain.

Routing note: this profile claims the addiction anchors (opioid/substance use
disorder, OUD/SUD, buprenorphine/methadone/naltrexone for the disorder, urine
drug screen, treatment retention, COWS/SOWS) that no existing profile claims; a
chronic-pain trial that uses opioids as analgesics stays with chronic_pain.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# SUBSTANCE USE DISORDER ENDPOINTS
# ============================================================

SUBSTANCE_USE_DISORDER_ENDPOINTS = {
    'RETENTION': {
        'aliases': ['treatment retention', 'retention in treatment', 'retention',
                    'study retention', 'retained in treatment', 'treatment completion',
                    'retention rate', 'time in treatment'],
        'subspecialty': 'opioid',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'NEGATIVE_UDS': {
        'aliases': ['opioid-negative urine', 'opioid negative urine',
                    'negative urine drug screen', 'drug-negative urine',
                    'urine drug screen', 'negative urine drug test',
                    'opioid-negative urine drug screen', 'percentage of negative urine',
                    'abstinent urine samples'],
        'subspecialty': 'opioid',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ABSTINENCE': {
        'aliases': ['abstinence', 'sustained abstinence', 'continuous abstinence',
                    'drug abstinence', 'opioid abstinence', 'abstinence rate',
                    'point-prevalence abstinence', 'confirmed abstinence'],
        'subspecialty': 'opioid',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'OVERDOSE': {
        'aliases': ['overdose', 'fatal overdose', 'non-fatal overdose',
                    'overdose death', 'overdose event', 'all-cause mortality',
                    'drug-related death', 'overdose mortality'],
        'subspecialty': 'opioid',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'RELAPSE': {
        'aliases': ['relapse', 'relapse to use', 'return to use', 'relapse rate',
                    'time to relapse', 'return to drug use'],
        'subspecialty': 'opioid',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CRAVING': {
        'aliases': ['craving', 'drug craving', 'opioid craving', 'craving score',
                    'visual analogue craving', 'craving reduction', 'craving scale'],
        'subspecialty': 'general',
        'measure_types': ['MD', 'SMD']
    },
    'WITHDRAWAL_SEVERITY': {
        'aliases': ['withdrawal severity', 'opioid withdrawal', 'cows', 'sows',
                    'clinical opiate withdrawal scale', 'subjective opiate withdrawal scale',
                    'cows score', 'withdrawal score', 'objective opiate withdrawal scale'],
        'subspecialty': 'opioid',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# OPIOID PATTERNS (opioid use disorder)
# ============================================================

OPIOID_PATTERNS = {
    'detection_keywords': [
        r'opioid\s+use\s+disorder|\boud\b', r'opioid\s+dependence',
        r'medications?\s+for\s+opioid\s+use\s+disorder|\bmoud\b|\bmat\b',
        r'buprenorphine|methadone|(?:extended[- ]release\s+)?naltrexone',
        r'opioid[- ]negative\s+urine|urine\s+drug\s+(?:screen|test)',
        r'opioid\s+withdrawal|\bcows\b|\bsows\b', r'treatment\s+retention',
    ],
    'endpoint_patterns': [
        (r'treatment\s+(?:retention|completion)|retention(?:\s+(?:in\s+treatment|rate))?|'
         r'retained\s+in\s+treatment|time\s+in\s+treatment', 'RETENTION'),
        (r'opioid[- ]negative\s+urine(?:\s+drug\s+screen)?|negative\s+urine\s+drug\s+(?:screen|test)|'
         r'drug[- ]negative\s+urine|abstinent\s+urine\s+samples', 'NEGATIVE_UDS'),
        (r'(?:fatal|non[- ]fatal)?\s*overdose(?:\s+(?:death|event|mortality))?|'
         r'all[- ]cause\s+mortality|drug[- ]related\s+death', 'OVERDOSE'),
        (r'relapse(?:\s+(?:to\s+use|rate))?|return\s+to\s+(?:drug\s+)?use|'
         r'time\s+to\s+relapse', 'RELAPSE'),
        (r'opioid\s+withdrawal(?:\s+severity)?|\bcows\b(?:\s+score)?|\bsows\b|'
         r'clinical\s+opiate\s+withdrawal\s+scale', 'WITHDRAWAL_SEVERITY'),
        (r'(?:sustained|continuous|confirmed)?\s*abstinence(?:\s+rate)?', 'ABSTINENCE'),
        (r'(?:drug|opioid)\s+craving|craving(?:\s+(?:score|scale|reduction))?', 'CRAVING'),
    ],
    'context_patterns': [
        r'sublingual', r'depot', r'at\s+(?:week|month)\s+\d+', r'induction',
    ]
}


# ============================================================
# STIMULANT PATTERNS (cocaine / methamphetamine)
# ============================================================

STIMULANT_PATTERNS = {
    'detection_keywords': [
        r'cocaine\s+use\s+disorder', r'methamphetamine\s+use\s+disorder',
        r'stimulant\s+use\s+disorder', r'\bcocaine\b|\bmethamphetamine\b',
        r'contingency\s+management', r'urine\s+drug\s+(?:screen|test)',
    ],
    'endpoint_patterns': [
        (r'(?:cocaine|methamphetamine|stimulant)[- ]negative\s+urine|negative\s+urine\s+drug\s+(?:screen|test)|'
         r'drug[- ]negative\s+urine|abstinent\s+urine\s+samples', 'NEGATIVE_UDS'),
        (r'(?:sustained|continuous|confirmed)?\s*abstinence(?:\s+rate)?', 'ABSTINENCE'),
        (r'treatment\s+(?:retention|completion)|retention(?:\s+rate)?', 'RETENTION'),
        (r'(?:drug|stimulant)\s+craving|craving(?:\s+score)?', 'CRAVING'),
    ],
    'context_patterns': [
        r'\breinforcement\b', r'voucher', r'at\s+(?:week|month)\s+\d+',
    ]
}


# ============================================================
# GENERAL PATTERNS (cannabis / polysubstance / mixed)
# ============================================================

GENERAL_PATTERNS = {
    'detection_keywords': [
        r'substance\s+use\s+disorder|\bsud\b', r'drug\s+(?:use\s+disorder|dependence)',
        r'cannabis\s+use\s+disorder', r'polysubstance',
        r'urine\s+drug\s+(?:screen|test)', r'abstinence',
    ],
    'endpoint_patterns': [
        (r'treatment\s+(?:retention|completion)|retention(?:\s+rate)?', 'RETENTION'),
        (r'(?:sustained|continuous|confirmed)?\s*abstinence(?:\s+rate)?', 'ABSTINENCE'),
        (r'negative\s+urine\s+drug\s+(?:screen|test)|drug[- ]negative\s+urine', 'NEGATIVE_UDS'),
        (r'(?:drug)\s+craving|craving(?:\s+score)?', 'CRAVING'),
    ],
    'context_patterns': [
        r'at\s+(?:week|month)\s+\d+', r'follow[- ]up', r'self[- ]report',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_substance_use_disorder_subspecialty(text: str) -> Tuple[str, float]:
    """Detect SUD trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: opioid, stimulant, general."""
    text_lower = text.lower()
    scores = {'opioid': 0, 'stimulant': 0, 'general': 0}
    for kw in OPIOID_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['opioid'] += 1
    for kw in STIMULANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['stimulant'] += 1
    for kw in GENERAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['general'] += 1

    # An explicit opioid anchor must beat the generic SUD overlap; a stimulant
    # anchor tips toward stimulant.
    if re.search(r'opioid\s+use\s+disorder|\boud\b|buprenorphine|methadone|opioid\s+withdrawal',
                 text_lower):
        scores['opioid'] += 1
    elif re.search(r'cocaine\s+use\s+disorder|methamphetamine\s+use\s+disorder|'
                   r'stimulant\s+use\s+disorder', text_lower):
        scores['stimulant'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('opioid', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_substance_use_disorder_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'opioid': OPIOID_PATTERNS['endpoint_patterns'],
        'stimulant': STIMULANT_PATTERNS['endpoint_patterns'],
        'general': GENERAL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_substance_use_disorder_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical endpoint, preferring the LONGEST matching alias so
    specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in SUBSTANCE_USE_DISORDER_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
