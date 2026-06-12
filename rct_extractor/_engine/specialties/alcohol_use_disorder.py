"""
Alcohol use disorder (AUD) Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the psychiatry profile, but for
ALCOHOL USE DISORDER specifically -- an addiction-medicine disease not targeted
by any existing profile (the cirrhosis profile covers alcohol-related LIVER
disease; this one covers the drinking disorder and its treatment). AUD RCTs
report an endpoint vocabulary anchored on abstinence, heavy-drinking days,
percent days abstinent, drinks per drinking day, relapse to heavy drinking,
craving and alcohol-withdrawal severity (CIWA-Ar).

Subspecialties:
- pharmacotherapy (anti-craving / aversive agents):
    abstinence (RR/OR), percent heavy-drinking days (MD), drinks per drinking day
    (MD), relapse to heavy drinking (RR/OR). Naltrexone, acamprosate, nalmefene,
    disulfiram, baclofen, topiramate, gabapentin.
- psychosocial (behavioural / brief intervention):
    abstinence (RR/OR), percent days abstinent (MD), treatment retention (RR/OR).
    CBT, motivational enhancement, contingency management, brief intervention.
- withdrawal (acute alcohol-withdrawal management):
    alcohol-withdrawal severity (CIWA-Ar; MD), seizures / delirium (RR/OR).
    Benzodiazepine regimens.

Effect measures: binary (abstinence, relapse, retention, seizures) -> RR/OR/RD;
continuous (heavy-drinking days, percent days abstinent, drinks per day, craving,
CIWA-Ar) -> MD/SMD. None is log-normal.

Spelling note: the only en-GB/en-US split is 'behaviour'/'behavior' -> handled as
'behaviou?r' inline. No ae/oe vowel traps in this domain.

Routing note: this profile claims the AUD-specific anchors (alcohol use disorder,
alcohol dependence, heavy drinking, percent days abstinent, naltrexone /
acamprosate / nalmefene / disulfiram, CIWA-Ar) that no existing profile claims; an
alcohol-associated cirrhosis / hepatitis trial stays with cirrhosis.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# ALCOHOL USE DISORDER ENDPOINTS
# ============================================================

ALCOHOL_USE_DISORDER_ENDPOINTS = {
    'ABSTINENCE': {
        'aliases': ['abstinence', 'total abstinence', 'complete abstinence',
                    'continuous abstinence', 'abstinence rate', 'sustained abstinence',
                    'point-prevalence abstinence', 'proportion abstinent'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HEAVY_DRINKING_DAYS': {
        'aliases': ['heavy drinking days', 'percentage of heavy drinking days',
                    'percent heavy drinking days', 'heavy-drinking days', 'phdd',
                    'number of heavy drinking days', 'proportion of heavy drinking days'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD', 'SMD']
    },
    'PCT_DAYS_ABSTINENT': {
        'aliases': ['percent days abstinent', 'percentage of days abstinent',
                    'percentage days abstinent', 'pda', 'proportion of days abstinent',
                    'days abstinent'],
        'subspecialty': 'psychosocial',
        'measure_types': ['MD', 'SMD']
    },
    'DRINKS_PER_DAY': {
        'aliases': ['drinks per drinking day', 'drinks per day', 'dpdd',
                    'number of drinks per day', 'mean drinks per drinking day',
                    'standard drinks per day'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD', 'SMD']
    },
    'RELAPSE': {
        'aliases': ['relapse', 'relapse to heavy drinking', 'return to heavy drinking',
                    'relapse rate', 'time to relapse', 'return to drinking',
                    'time to first heavy drinking day'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CRAVING': {
        'aliases': ['craving', 'alcohol craving', 'craving score', 'penn alcohol craving scale',
                    'pacs', 'obsessive compulsive drinking scale', 'ocds', 'craving reduction'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD', 'SMD']
    },
    'WITHDRAWAL_SEVERITY': {
        'aliases': ['ciwa-ar', 'ciwa', 'alcohol withdrawal severity',
                    'clinical institute withdrawal assessment', 'withdrawal severity',
                    'ciwa-ar score', 'withdrawal score'],
        'subspecialty': 'withdrawal',
        'measure_types': ['MD', 'SMD']
    },
    'RETENTION': {
        'aliases': ['treatment retention', 'retention', 'retention in treatment',
                    'treatment completion', 'study retention', 'retained in treatment',
                    'retention rate'],
        'subspecialty': 'psychosocial',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# PHARMACOTHERAPY PATTERNS (anti-craving / aversive)
# ============================================================

PHARMACOTHERAPY_PATTERNS = {
    'detection_keywords': [
        r'alcohol\s+use\s+disorder|\baud\b', r'alcohol\s+dependence|alcoholism',
        r'heavy\s+drinking', r'abstinence',
        r'naltrexone|acamprosate|nalmefene|disulfiram|baclofen|topiramate',
        r'drinks?\s+per\s+(?:drinking\s+)?day', r'percent\s+days\s+abstinent',
    ],
    'endpoint_patterns': [
        (r'(?:percentage|percent|proportion|number)\s+of\s+heavy[- ]drinking\s+days|'
         r'heavy[- ]drinking\s+days|\bphdd\b', 'HEAVY_DRINKING_DAYS'),
        (r'(?:percentage|percent|proportion)\s+(?:of\s+)?days\s+abstinent|\bpda\b|'
         r'days\s+abstinent', 'PCT_DAYS_ABSTINENT'),
        (r'drinks?\s+per\s+(?:drinking\s+)?day|\bdpdd\b|standard\s+drinks?\s+per\s+day',
         'DRINKS_PER_DAY'),
        (r'relapse(?:\s+(?:to|rate))?|return\s+to\s+(?:heavy\s+)?drinking|'
         r'time\s+to\s+(?:relapse|first\s+heavy\s+drinking)', 'RELAPSE'),
        (r'craving(?:\s+(?:score|reduction))?|penn\s+alcohol\s+craving\s+scale|\bpacs\b|'
         r'obsessive\s+compulsive\s+drinking', 'CRAVING'),
        (r'(?:total|complete|continuous|sustained)?\s*abstinence(?:\s+rate)?|'
         r'proportion\s+abstinent', 'ABSTINENCE'),
    ],
    'context_patterns': [
        r'timeline\s+followback|\btlfb\b', r'at\s+(?:week|month)\s+\d+', r'standard\s+drinks?',
    ]
}


# ============================================================
# PSYCHOSOCIAL PATTERNS (behavioural)
# ============================================================

PSYCHOSOCIAL_PATTERNS = {
    'detection_keywords': [
        r'cognitive\s+behaviou?ral\s+therapy', r'motivational\s+(?:enhancement|interviewing)',
        r'brief\s+intervention', r'contingency\s+management',
        r'alcohol\s+use\s+disorder|\baud\b', r'percent\s+days\s+abstinent',
        r'treatment\s+retention',
    ],
    'endpoint_patterns': [
        (r'(?:percentage|percent|proportion)\s+(?:of\s+)?days\s+abstinent|\bpda\b|'
         r'days\s+abstinent', 'PCT_DAYS_ABSTINENT'),
        (r'treatment\s+(?:retention|completion)|retention(?:\s+(?:in\s+treatment|rate))?|'
         r'retained\s+in\s+treatment', 'RETENTION'),
        (r'(?:total|complete|continuous)?\s*abstinence(?:\s+rate)?', 'ABSTINENCE'),
    ],
    'context_patterns': [
        r'\bsessions?\b', r'at\s+(?:week|month)\s+\d+', r'follow[- ]up',
    ]
}


# ============================================================
# WITHDRAWAL PATTERNS (acute management)
# ============================================================

WITHDRAWAL_PATTERNS = {
    'detection_keywords': [
        r'alcohol\s+withdrawal', r'ciwa[- ]?ar|ciwa',
        r'delirium\s+tremens', r'withdrawal\s+seizures?',
        r'benzodiazepine', r'(?:chlordiazepoxide|diazepam|lorazepam)\s+(?:for|in)\s+(?:alcohol|withdrawal)',
    ],
    'endpoint_patterns': [
        (r'ciwa[- ]?ar(?:\s+score)?|alcohol\s+withdrawal\s+severity|withdrawal\s+severity|'
         r'clinical\s+institute\s+withdrawal\s+assessment', 'WITHDRAWAL_SEVERITY'),
        (r'(?:withdrawal\s+)?seizures?|delirium\s+tremens', 'RELAPSE'),
    ],
    'context_patterns': [
        r'symptom[- ]triggered', r'fixed[- ]schedule', r'within\s+\d+\s+hours',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_alcohol_use_disorder_subspecialty(text: str) -> Tuple[str, float]:
    """Detect AUD trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: pharmacotherapy, psychosocial, withdrawal."""
    text_lower = text.lower()
    scores = {'pharmacotherapy': 0, 'psychosocial': 0, 'withdrawal': 0}
    for kw in PHARMACOTHERAPY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pharmacotherapy'] += 1
    for kw in PSYCHOSOCIAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['psychosocial'] += 1
    for kw in WITHDRAWAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['withdrawal'] += 1

    # An acute-withdrawal anchor must beat the generic AUD overlap.
    if re.search(r'alcohol\s+withdrawal|ciwa|delirium\s+tremens|withdrawal\s+seizure',
                 text_lower):
        scores['withdrawal'] += 1
    elif re.search(r'motivational\s+(?:enhancement|interviewing)|brief\s+intervention|'
                   r'contingency\s+management', text_lower):
        scores['psychosocial'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('pharmacotherapy', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_alcohol_use_disorder_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'pharmacotherapy': PHARMACOTHERAPY_PATTERNS['endpoint_patterns'],
        'psychosocial': PSYCHOSOCIAL_PATTERNS['endpoint_patterns'],
        'withdrawal': WITHDRAWAL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_alcohol_use_disorder_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical endpoint, preferring the LONGEST matching alias so
    specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in ALCOHOL_USE_DISORDER_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
