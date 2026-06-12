"""
Insomnia Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the psychiatry / respiratory
profiles, but for INSOMNIA specifically -- a sleep-medicine disorder not targeted
by any existing profile. Insomnia RCTs report an endpoint vocabulary anchored on
the Insomnia Severity Index (ISI), sleep-onset latency (SOL), wake after sleep
onset (WASO), total sleep time (TST), sleep efficiency (SE), the Pittsburgh Sleep
Quality Index (PSQI), and polysomnographic latency to persistent sleep (LPS).

Subspecialties:
- pharmacotherapy (hypnotics):
    ISI (MD), SOL (min; MD), WASO (min; MD), TST (min; MD), responder/remission
    (RR/OR). Dual orexin-receptor antagonists, Z-drugs, melatonin agonists,
    low-dose doxepin.
- cbt_i (cognitive behavioural therapy for insomnia / digital):
    ISI (MD), sleep efficiency (%; MD), WASO (MD), response/remission (RR/OR).
- objective (polysomnography / actigraphy primary):
    latency to persistent sleep (min; MD), WASO (MD), TST (MD).

Effect measures: binary (treatment response, remission [e.g. ISI < 8]) -> RR/OR/RD;
continuous (ISI, SOL, WASO, TST, sleep efficiency, PSQI, LPS) -> MD/SMD. None is
log-normal (all are bounded scores / minutes / percentages pooled on the raw scale).

Spelling note: 'insomnia' has no British/American vowel variant; the only
en-GB/en-US split in this domain is 'behaviour'/'behavior' (handled inline as
'behaviou?r' where it appears).

Routing note: this profile claims the insomnia-specific anchors (insomnia
disorder, Insomnia Severity Index / ISI, sleep-onset latency, wake after sleep
onset / WASO, sleep efficiency, hypnotic/orexin-antagonist/Z-drug, CBT-I) that
no existing profile claims; a depression/anxiety trial stays with psychiatry.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# INSOMNIA ENDPOINTS
# ============================================================

INSOMNIA_ENDPOINTS = {
    'ISI': {
        'aliases': ['insomnia severity index', 'isi', 'isi score', 'isi total score',
                    'change in isi', 'mean insomnia severity index'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD', 'SMD']
    },
    'SOL': {
        'aliases': ['sleep onset latency', 'sleep-onset latency', 'sol',
                    'latency to sleep onset', 'subjective sleep latency',
                    'time to fall asleep', 'change in sleep onset latency'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD', 'SMD']
    },
    'WASO': {
        'aliases': ['wake after sleep onset', 'waso', 'wakefulness after sleep onset',
                    'wake time after sleep onset', 'change in waso',
                    'minutes of wake after sleep onset'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD', 'SMD']
    },
    'TST': {
        'aliases': ['total sleep time', 'tst', 'total sleep duration',
                    'change in total sleep time', 'mean total sleep time',
                    'subjective total sleep time'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD', 'SMD']
    },
    'SLEEP_EFFICIENCY': {
        'aliases': ['sleep efficiency', 'sleep-efficiency',
                    'change in sleep efficiency', 'mean sleep efficiency'],
        'subspecialty': 'cbt_i',
        'measure_types': ['MD', 'SMD']
    },
    'PSQI': {
        'aliases': ['pittsburgh sleep quality index', 'psqi', 'psqi score',
                    'pittsburgh sleep quality index global score',
                    'change in psqi', 'global psqi'],
        'subspecialty': 'cbt_i',
        'measure_types': ['MD', 'SMD']
    },
    'LPS': {
        'aliases': ['latency to persistent sleep', 'lps', 'persistent sleep latency',
                    'polysomnographic sleep latency', 'change in latency to persistent sleep'],
        'subspecialty': 'objective',
        'measure_types': ['MD', 'SMD']
    },
    'INSOMNIA_RESPONSE': {
        'aliases': ['treatment response', 'insomnia response', 'responder rate',
                    'remission', 'insomnia remission', 'response rate',
                    'proportion of responders', 'remitter rate'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# PHARMACOTHERAPY PATTERNS (hypnotics)
# ============================================================

PHARMACOTHERAPY_PATTERNS = {
    'detection_keywords': [
        r'insomnia(?:\s+disorder)?', r'chronic\s+insomnia',
        r'insomnia\s+severity\s+index|\bisi\b',
        r'suvorexant|lemborexant|daridorexant|orexin\s+(?:receptor\s+)?antagonist',
        r'zolpidem|zopiclone|eszopiclone|zaleplon|\bz[- ]drug',
        r'ramelteon|melatonin|low[- ]dose\s+doxepin',
        r'sleep[- ]onset\s+latency|wake\s+after\s+sleep\s+onset|\bwaso\b',
    ],
    'endpoint_patterns': [
        (r'insomnia\s+severity\s+index|\bisi\b(?:\s+(?:total\s+)?score)?', 'ISI'),
        (r'sleep[- ]onset\s+latency|latency\s+to\s+sleep\s+onset|\bsol\b|time\s+to\s+fall\s+asleep',
         'SOL'),
        (r'wake(?:fulness)?\s+(?:time\s+)?after\s+sleep\s+onset|\bwaso\b', 'WASO'),
        (r'total\s+sleep\s+time|\btst\b|total\s+sleep\s+duration', 'TST'),
        (r'treatment\s+response|insomnia\s+(?:response|remission)|responder\s+rate|'
         r'remitter\s+rate', 'INSOMNIA_RESPONSE'),
    ],
    'context_patterns': [
        r'\bminutes?\b|\bmin\b', r'at\s+(?:week|month)\s+\d+', r'sleep\s+diary',
    ]
}


# ============================================================
# CBT-I PATTERNS (cognitive behavioural therapy for insomnia)
# ============================================================

CBT_I_PATTERNS = {
    'detection_keywords': [
        r'cognitive\s+behaviou?ral\s+therapy\s+for\s+insomnia|\bcbt[- ]?i\b',
        r'digital\s+(?:cbt|cognitive)', r'sleep\s+restriction',
        r'stimulus\s+control', r'insomnia(?:\s+disorder)?',
        r'sleep\s+efficiency', r'pittsburgh\s+sleep\s+quality\s+index|\bpsqi\b',
    ],
    'endpoint_patterns': [
        (r'insomnia\s+severity\s+index|\bisi\b', 'ISI'),
        (r'sleep[- ]efficiency', 'SLEEP_EFFICIENCY'),
        (r'pittsburgh\s+sleep\s+quality\s+index|\bpsqi\b', 'PSQI'),
        (r'wake(?:fulness)?\s+after\s+sleep\s+onset|\bwaso\b', 'WASO'),
        (r'treatment\s+response|insomnia\s+(?:response|remission)|responder\s+rate', 'INSOMNIA_RESPONSE'),
    ],
    'context_patterns': [
        r'sleep\s+diary', r'at\s+(?:week|month)\s+\d+', r'therapist[- ]guided',
    ]
}


# ============================================================
# OBJECTIVE PATTERNS (polysomnography / actigraphy primary)
# ============================================================

OBJECTIVE_PATTERNS = {
    'detection_keywords': [
        r'polysomnograph', r'latency\s+to\s+persistent\s+sleep|\blps\b',
        r'actigraph', r'insomnia(?:\s+disorder)?', r'wake\s+after\s+sleep\s+onset',
    ],
    'endpoint_patterns': [
        (r'latency\s+to\s+persistent\s+sleep|\blps\b|persistent\s+sleep\s+latency',
         'LPS'),
        (r'wake(?:fulness)?\s+after\s+sleep\s+onset|\bwaso\b', 'WASO'),
        (r'total\s+sleep\s+time|\btst\b', 'TST'),
    ],
    'context_patterns': [
        r'\bminutes?\b', r'overnight\s+psg', r'at\s+(?:night|week)\s+\d+',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_insomnia_subspecialty(text: str) -> Tuple[str, float]:
    """Detect insomnia trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: pharmacotherapy, cbt_i, objective."""
    text_lower = text.lower()
    scores = {'pharmacotherapy': 0, 'cbt_i': 0, 'objective': 0}
    for kw in PHARMACOTHERAPY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pharmacotherapy'] += 1
    for kw in CBT_I_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['cbt_i'] += 1
    for kw in OBJECTIVE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['objective'] += 1

    # A CBT-I anchor (behavioural therapy) must beat the generic insomnia overlap;
    # a polysomnography-primary anchor tips toward objective.
    if re.search(r'cognitive\s+behaviou?ral\s+therapy\s+for\s+insomnia|\bcbt[- ]?i\b|'
                 r'sleep\s+restriction|stimulus\s+control', text_lower):
        scores['cbt_i'] += 1
    elif re.search(r'latency\s+to\s+persistent\s+sleep|\blps\b|polysomnograph', text_lower):
        scores['objective'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('pharmacotherapy', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_insomnia_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'pharmacotherapy': PHARMACOTHERAPY_PATTERNS['endpoint_patterns'],
        'cbt_i': CBT_I_PATTERNS['endpoint_patterns'],
        'objective': OBJECTIVE_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_insomnia_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical endpoint, preferring the LONGEST matching alias so
    specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in INSOMNIA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
