"""
Chronic rhinosinusitis (CRS) Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the allergic_rhinitis / respiratory
profiles, but for CHRONIC RHINOSINUSITIS specifically -- a distinct ENT disease
(inflammation of the paranasal sinuses) that neither the nasal allergic_rhinitis
profile (hay fever, TNSS, allergen immunotherapy) nor the lower-airway respiratory
profile (COPD, asthma, FEV1) targets. CRS RCTs report an endpoint vocabulary
anchored on the Sino-Nasal Outcome Test (SNOT-22), nasal polyp score (NPS),
nasal congestion, loss of smell, Lund-Mackay CT score, Lund-Kennedy endoscopic
score and the need for rescue surgery / systemic corticosteroids.

Subspecialties:
- crswnp (CRS with nasal polyps):
    nasal polyp score (NPS; MD), SNOT-22 (MD), nasal congestion (MD), loss of
    smell (MD), need for rescue surgery / systemic steroids (RR/OR). Biologics
    (dupilumab, omalizumab, mepolizumab) dominate.
- crssnp (CRS without nasal polyps):
    SNOT-22 (MD), nasal congestion (MD), Lund-Mackay CT score (MD); medical
    therapy (intranasal steroids, saline, macrolides).
- surgery (functional endoscopic sinus surgery, FESS):
    Lund-Kennedy endoscopic score (MD), Lund-Mackay CT score (MD), revision
    surgery (RR/OR).

Effect measures: binary (rescue surgery / systemic steroids, revision surgery)
-> RR/OR/RD; continuous (SNOT-22, NPS, nasal congestion, smell, Lund-Mackay,
Lund-Kennedy) -> MD/SMD. None is log-normal (all bounded clinical scores pooled
on the raw scale).

Routing note: this profile claims the CRS-specific anchors (chronic
rhinosinusitis, nasal polyp(s) / polyposis, SNOT-22, Lund-Mackay, Lund-Kennedy,
functional endoscopic sinus surgery / FESS) that neither allergic_rhinitis nor
respiratory claims, so a CRS trial routes here and a hay-fever trial stays with
allergic_rhinitis.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# CHRONIC RHINOSINUSITIS ENDPOINTS
# ============================================================

CHRONIC_RHINOSINUSITIS_ENDPOINTS = {
    'SNOT22': {
        'aliases': ['sino-nasal outcome test', 'sinonasal outcome test', 'snot-22',
                    'snot 22', 'snot-20', 'snot22', 'change in snot-22',
                    'mean snot-22', 'snot-22 total score'],
        'subspecialty': 'crswnp',
        'measure_types': ['MD', 'SMD']
    },
    'NPS': {
        'aliases': ['nasal polyp score', 'nasal polyps score', 'total nasal polyp score',
                    'nps', 'bilateral nasal polyp score', 'endoscopic nasal polyp score',
                    'change in nasal polyp score', 'mean nasal polyp score'],
        'subspecialty': 'crswnp',
        'measure_types': ['MD', 'SMD']
    },
    'NASAL_CONGESTION': {
        'aliases': ['nasal congestion score', 'nasal congestion', 'nasal obstruction',
                    'congestion/obstruction', 'nasal blockage', 'nasal congestion/obstruction',
                    'change in nasal congestion'],
        'subspecialty': 'crswnp',
        'measure_types': ['MD', 'SMD']
    },
    'SMELL': {
        'aliases': ['loss of smell', 'sense of smell', 'olfaction', 'smell identification',
                    'upsit', 'sniffin sticks', 'university of pennsylvania smell identification',
                    'olfactory score', 'smell score', 'anosmia'],
        'subspecialty': 'crswnp',
        'measure_types': ['MD', 'SMD']
    },
    'LUND_MACKAY': {
        'aliases': ['lund-mackay', 'lund mackay', 'lund-mackay ct score',
                    'lund-mackay score', 'ct score', 'sinus ct score',
                    'change in lund-mackay'],
        'subspecialty': 'crssnp',
        'measure_types': ['MD', 'SMD']
    },
    'LUND_KENNEDY': {
        'aliases': ['lund-kennedy', 'lund kennedy', 'lund-kennedy endoscopic score',
                    'endoscopic score', 'nasal endoscopy score', 'lund-kennedy score',
                    'total endoscopic score'],
        'subspecialty': 'surgery',
        'measure_types': ['MD', 'SMD']
    },
    'RESCUE_INTERVENTION': {
        'aliases': ['rescue surgery', 'need for surgery', 'systemic corticosteroid use',
                    'systemic steroid use', 'rescue treatment', 'sinus surgery',
                    'need for sinus surgery', 'rescue systemic corticosteroids',
                    'proportion requiring surgery'],
        'subspecialty': 'crswnp',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'REVISION_SURGERY': {
        'aliases': ['revision surgery', 'revision sinus surgery', 'reoperation',
                    'recurrence requiring surgery', 'revision rate', 'revision fess'],
        'subspecialty': 'surgery',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# CRSwNP PATTERNS (with nasal polyps)
# ============================================================

CRSWNP_PATTERNS = {
    'detection_keywords': [
        r'chronic\s+rhinosinusitis\s+with\s+nasal\s+polyps|\bcrswnp\b',
        r'nasal\s+polyp(?:s|osis)?', r'nasal\s+polyp\s+score|\bnps\b',
        r'chronic\s+rhinosinusitis|\bcrs\b',
        r'dupilumab|omalizumab|mepolizumab|benralizumab',
        r'loss\s+of\s+smell|olfaction|anosmia',
    ],
    'endpoint_patterns': [
        (r'nasal\s+polyp(?:s)?\s+score|total\s+nasal\s+polyp\s+score|\bnps\b|'
         r'bilateral\s+nasal\s+polyp\s+score', 'NPS'),
        (r'sino-?nasal\s+outcome\s+test|snot[- ]?2[02]', 'SNOT22'),
        (r'nasal\s+congestion(?:/obstruction)?(?:\s+score)?|nasal\s+obstruction|'
         r'nasal\s+blockage', 'NASAL_CONGESTION'),
        (r'loss\s+of\s+smell|sense\s+of\s+smell|olfaction|smell\s+(?:identification|score)|'
         r'\bupsit\b|sniffin\s+sticks|olfactory\s+score|anosmia', 'SMELL'),
        (r'rescue\s+(?:surgery|treatment|systemic\s+cortico?steroids?)|need\s+for\s+(?:sinus\s+)?surgery|'
         r'systemic\s+(?:cortico)?steroid\s+use', 'RESCUE_INTERVENTION'),
    ],
    'context_patterns': [
        r'\beosinophil', r'type\s+2\s+inflammation', r'at\s+week\s+(?:24|52)',
        r'intranasal\s+cortico?steroid',
    ]
}


# ============================================================
# CRSsNP PATTERNS (without nasal polyps)
# ============================================================

CRSSNP_PATTERNS = {
    'detection_keywords': [
        r'chronic\s+rhinosinusitis\s+without\s+nasal\s+polyps|\bcrssnp\b',
        r'chronic\s+rhinosinusitis|\bcrs\b',
        r'lund[- ]mackay', r'sino-?nasal\s+outcome\s+test|snot[- ]?2[02]',
        r'saline\s+irrigation|nasal\s+irrigation', r'macrolide|doxycycline',
    ],
    'endpoint_patterns': [
        (r'lund[- ]mackay(?:\s+(?:ct\s+)?score)?|sinus\s+ct\s+score', 'LUND_MACKAY'),
        (r'sino-?nasal\s+outcome\s+test|snot[- ]?2[02]', 'SNOT22'),
        (r'nasal\s+congestion(?:\s+score)?|nasal\s+obstruction|nasal\s+blockage',
         'NASAL_CONGESTION'),
    ],
    'context_patterns': [
        r'paranasal\s+sinus', r'nasal\s+lavage', r'at\s+(?:week|month)\s+\d+',
    ]
}


# ============================================================
# SURGERY PATTERNS (FESS)
# ============================================================

SURGERY_PATTERNS = {
    'detection_keywords': [
        r'functional\s+endoscopic\s+sinus\s+surgery|\bfess\b', r'sinus\s+surgery',
        r'lund[- ]kennedy', r'endoscopic\s+score', r'revision\s+surgery',
        r'polypectomy',
    ],
    'endpoint_patterns': [
        (r'revision\s+(?:sinus\s+)?surgery|reoperation|revision\s+fess|revision\s+rate',
         'REVISION_SURGERY'),
        (r'lund[- ]kennedy(?:\s+(?:endoscopic\s+)?score)?|nasal\s+endoscopy\s+score|'
         r'total\s+endoscopic\s+score|endoscopic\s+score', 'LUND_KENNEDY'),
        (r'lund[- ]mackay(?:\s+(?:ct\s+)?score)?', 'LUND_MACKAY'),
    ],
    'context_patterns': [
        r'postoperative', r'middle\s+meatus', r'at\s+(?:month|year)\s+\d+',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_chronic_rhinosinusitis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect CRS trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: crswnp, crssnp, surgery."""
    text_lower = text.lower()
    scores = {'crswnp': 0, 'crssnp': 0, 'surgery': 0}
    for kw in CRSWNP_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['crswnp'] += 1
    for kw in CRSSNP_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['crssnp'] += 1
    for kw in SURGERY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['surgery'] += 1

    # An explicit "without nasal polyps" anchor must beat the generic CRS overlap.
    if re.search(r'without\s+nasal\s+polyps|\bcrssnp\b', text_lower):
        scores['crssnp'] += 2
    elif re.search(r'with\s+nasal\s+polyps|\bcrswnp\b|nasal\s+polyp(?:s|osis)', text_lower):
        scores['crswnp'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('crswnp', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_chronic_rhinosinusitis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'crswnp': CRSWNP_PATTERNS['endpoint_patterns'],
        'crssnp': CRSSNP_PATTERNS['endpoint_patterns'],
        'surgery': SURGERY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_chronic_rhinosinusitis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical endpoint, preferring the LONGEST matching alias so
    specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in CHRONIC_RHINOSINUSITIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
