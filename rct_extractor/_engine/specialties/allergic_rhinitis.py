"""
Allergic Rhinitis Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the tuberculosis / ARDS profiles.
Allergic-rhinitis (and rhinoconjunctivitis) RCTs report a distinct endpoint
vocabulary (total nasal symptom score, combined symptom-medication score, rescue
medication use, rhinoconjunctivitis quality of life, responder rates) that the
generic effect-size engine does not recognise on its own.

Subspecialties:
- Pharmacotherapy: intranasal corticosteroids (fluticasone, mometasone),
  oral / intranasal antihistamines (cetirizine, loratadine, azelastine),
  leukotriene receptor antagonists (montelukast), decongestants, combination
  intranasal antihistamine-steroid.
- Immunotherapy: subcutaneous (SCIT) and sublingual (SLIT, tablet / drops)
  allergen immunotherapy for grass / house-dust-mite / ragweed / birch.
- Biologics: omalizumab (anti-IgE), dupilumab and other monoclonal antibodies
  in allergic rhinitis / chronic rhinosinusitis with nasal polyps.
- Environmental / other: allergen avoidance, nasal saline, intranasal capsaicin,
  novel routes.

Effect measures follow what these trials report: continuous (total nasal symptom
score, combined symptom-medication score, rhinoconjunctivitis QoL) -> mean
difference; binary (responders, rescue medication use, symptom-free days) ->
RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# ALLERGIC RHINITIS ENDPOINTS
# ============================================================

ALLERGIC_RHINITIS_ENDPOINTS = {
    'TNSS': {
        'aliases': ['total nasal symptom score', 'tnss', 'nasal symptom score',
                    'reflective total nasal symptom score', 'rtnss',
                    'instantaneous total nasal symptom score', 'itnss',
                    'daily nasal symptom score', 'nasal symptoms'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD']
    },
    'CSMS': {
        'aliases': ['combined symptom and medication score', 'combined symptom-medication score',
                    'csms', 'symptom medication score', 'combined score',
                    'daily combined score', 'total combined rhinitis score'],
        'subspecialty': 'immunotherapy',
        'measure_types': ['MD']
    },
    'TOSS': {
        'aliases': ['total ocular symptom score', 'toss', 'ocular symptom score',
                    'eye symptom score', 'conjunctivitis symptom score'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD']
    },
    'TSS': {
        'aliases': ['total symptom score', 'tss', 'rhinitis total symptom score',
                    'total rhinoconjunctivitis symptom score', 'trss', 'symptom score'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD']
    },
    'RESCUE_MEDICATION': {
        'aliases': ['rescue medication use', 'rescue medication score',
                    'use of rescue medication', 'medication score', 'rescue medication',
                    'days of rescue medication', 'antihistamine use'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD', 'RR']
    },
    'RQLQ': {
        'aliases': ['rhinoconjunctivitis quality of life', 'rqlq',
                    'rhinoconjunctivitis quality of life questionnaire',
                    'quality of life', 'mini-rqlq', 'health-related quality of life'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD']
    },
    'RESPONDER': {
        'aliases': ['responder', 'responder rate', 'treatment responders',
                    'clinical responder', 'proportion of responders',
                    'well-controlled', 'symptom control'],
        'subspecialty': 'immunotherapy',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SYMPTOM_FREE_DAYS': {
        'aliases': ['symptom-free days', 'symptom free days', 'well days',
                    'days with no symptoms', 'rescue-free days'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD', 'RR']
    },
    'NASAL_CONGESTION': {
        'aliases': ['nasal congestion', 'nasal congestion score', 'congestion',
                    'nasal obstruction', 'peak nasal inspiratory flow', 'pnif'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'treatment-related adverse events',
                    'local reactions', 'oral pruritus', 'systemic reactions',
                    'application-site reactions', 'epistaxis'],
        'subspecialty': 'immunotherapy',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ASTHMA_DEVELOPMENT': {
        'aliases': ['development of asthma', 'onset of asthma', 'new-onset asthma',
                    'asthma symptoms', 'progression to asthma'],
        'subspecialty': 'immunotherapy',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# PHARMACOTHERAPY PATTERNS
# ============================================================

PHARMACOTHERAPY_PATTERNS = {
    'detection_keywords': [
        r'intranasal\s+corticosteroid|fluticasone|mometasone|budesonide|triamcinolone',
        r'antihistamine|cetirizine|levocetirizine|loratadine|desloratadine|fexofenadine|azelastine|bilastine',
        r'leukotriene\s+receptor\s+antagonist|montelukast',
        r'decongestant|oxymetazoline|pseudoephedrine',
        r'\bmp[- ]?azpd\b|azelastine[- ]fluticasone|intranasal\s+antihistamine',
        r'total\s+nasal\s+symptom\s+score|\btnss\b',
    ],
    'endpoint_patterns': [
        (r'combined\s+symptom(?:[- ]and)?[- ]medication\s+score|\bcsms\b|combined\s+score',
         'CSMS'),
        (r'(?:reflective\s+|instantaneous\s+|daily\s+)?total\s+nasal\s+symptom\s+score|'
         r'\b[ri]?tnss\b|nasal\s+symptom\s+score', 'TNSS'),
        (r'total\s+ocular\s+symptom\s+score|\btoss\b|ocular\s+symptom\s+score|eye\s+symptom',
         'TOSS'),
        (r'rhinoconjunctivitis\s+quality\s+of\s+life|\brqlq\b|mini[- ]rqlq', 'RQLQ'),
        (r'rescue\s+medication(?:\s+(?:use|score))?|medication\s+score|antihistamine\s+use',
         'RESCUE_MEDICATION'),
        (r'nasal\s+congestion(?:\s+score)?|nasal\s+obstruction|peak\s+nasal\s+inspiratory\s+flow|\bpnif\b',
         'NASAL_CONGESTION'),
        (r'symptom[- ]free\s+days|rescue[- ]free\s+days|well\s+days', 'SYMPTOM_FREE_DAYS'),
        (r'total\s+(?:rhinoconjunctivitis\s+)?symptom\s+score|\b[t]?[rt]ss\b', 'TSS'),
    ],
    'context_patterns': [
        r'0\s*[-–]\s*12\s+scale|0\s*[-–]\s*3\s+per\s+symptom', r'pollen\s+season|seasonal',
    ]
}


# ============================================================
# IMMUNOTHERAPY PATTERNS
# ============================================================

IMMUNOTHERAPY_PATTERNS = {
    'detection_keywords': [
        r'allergen\s+immunotherapy|specific\s+immunotherapy|\bait\b',
        r'sublingual\s+immunotherapy|\bslit\b|sublingual\s+tablet',
        r'subcutaneous\s+immunotherapy|\bscit\b',
        r'grass\s+pollen|house\s+dust\s+mite|\bhdm\b|ragweed|birch\s+pollen',
        r'combined\s+symptom(?:[- ]and)?[- ]medication\s+score|\bcsms\b',
        r'allergoid|depigmented',
    ],
    'endpoint_patterns': [
        (r'combined\s+symptom(?:[- ]and)?[- ]medication\s+score|\bcsms\b|combined\s+score|'
         r'total\s+combined\s+rhinitis\s+score', 'CSMS'),
        (r'(?:reflective\s+|daily\s+)?total\s+nasal\s+symptom\s+score|\b[ri]?tnss\b', 'TNSS'),
        (r'rhinoconjunctivitis\s+quality\s+of\s+life|\brqlq\b', 'RQLQ'),
        (r'responder|well[- ]controlled|symptom\s+control', 'RESPONDER'),
        (r'rescue\s+medication(?:\s+(?:use|score))?|medication\s+score', 'RESCUE_MEDICATION'),
        (r'development\s+of\s+asthma|onset\s+of\s+asthma|new[- ]onset\s+asthma|progression\s+to\s+asthma',
         'ASTHMA_DEVELOPMENT'),
        (r'(?:local|systemic|application[- ]site)\s+reactions?|oral\s+pruritus|serious\s+adverse',
         'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'maintenance\s+(?:dose|phase)', r'\d+\s+sq[- ]?(?:t|hdm)|\biR\b|standardized\s+quality',
    ]
}


# ============================================================
# BIOLOGICS PATTERNS
# ============================================================

BIOLOGICS_PATTERNS = {
    'detection_keywords': [
        r'omalizumab', r'anti[- ]ige', r'dupilumab|mepolizumab|benralizumab',
        r'monoclonal\s+antibody', r'nasal\s+polyp|chronic\s+rhinosinusitis',
        r'biologic\s+(?:therapy|agent)', r'add[- ]on\s+(?:therapy|biologic)',
    ],
    'endpoint_patterns': [
        (r'nasal\s+congestion(?:\s+score)?|nasal\s+polyp\s+score|\bnps\b', 'NASAL_CONGESTION'),
        (r'(?:reflective\s+)?total\s+nasal\s+symptom\s+score|\b[ri]?tnss\b', 'TNSS'),
        (r'combined\s+symptom(?:[- ]and)?[- ]medication\s+score|\bcsms\b', 'CSMS'),
        (r'rhinoconjunctivitis\s+quality\s+of\s+life|\brqlq\b|quality\s+of\s+life', 'RQLQ'),
        (r'responder|well[- ]controlled', 'RESPONDER'),
        (r'rescue\s+medication|medication\s+score', 'RESCUE_MEDICATION'),
        (r'serious\s+adverse|injection[- ]site|systemic\s+reactions?', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'every\s+\d+\s+weeks', r'add[- ]on\s+therapy',
    ]
}


# ============================================================
# ENVIRONMENTAL / OTHER PATTERNS
# ============================================================

ENVIRONMENTAL_PATTERNS = {
    'detection_keywords': [
        r'allergen\s+avoidance|mite[- ]impermeable|air\s+(?:filtration|purif\w+)',
        r'nasal\s+saline|saline\s+irrigation|nasal\s+douching',
        r'intranasal\s+capsaicin|nasal\s+filter',
        r'probiotic|environmental\s+control',
    ],
    'endpoint_patterns': [
        (r'(?:reflective\s+)?total\s+nasal\s+symptom\s+score|\b[ri]?tnss\b|nasal\s+symptom\s+score',
         'TNSS'),
        (r'total\s+(?:rhinoconjunctivitis\s+)?symptom\s+score|\b[t]?[rt]ss\b', 'TSS'),
        (r'rhinoconjunctivitis\s+quality\s+of\s+life|\brqlq\b|quality\s+of\s+life', 'RQLQ'),
        (r'rescue\s+medication|medication\s+score', 'RESCUE_MEDICATION'),
        (r'nasal\s+congestion|nasal\s+obstruction', 'NASAL_CONGESTION'),
        (r'symptom[- ]free\s+days|well\s+days', 'SYMPTOM_FREE_DAYS'),
    ],
    'context_patterns': [
        r'home\s+environment', r'allergen\s+load',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_allergic_rhinitis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect allergic-rhinitis trial subspecialty.
    Returns (subspecialty, confidence). Subspecialties: pharmacotherapy,
    immunotherapy, biologics, environmental, general_ar."""
    text_lower = text.lower()
    scores = {'pharmacotherapy': 0, 'immunotherapy': 0,
              'biologics': 0, 'environmental': 0}
    for kw in PHARMACOTHERAPY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pharmacotherapy'] += 1
    for kw in IMMUNOTHERAPY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['immunotherapy'] += 1
    for kw in BIOLOGICS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['biologics'] += 1
    for kw in ENVIRONMENTAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['environmental'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_ar', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_allergic_rhinitis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'pharmacotherapy': PHARMACOTHERAPY_PATTERNS['endpoint_patterns'],
        'immunotherapy': IMMUNOTHERAPY_PATTERNS['endpoint_patterns'],
        'biologics': BIOLOGICS_PATTERNS['endpoint_patterns'],
        'environmental': ENVIRONMENTAL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_allergic_rhinitis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical allergic-rhinitis endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in ALLERGIC_RHINITIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
