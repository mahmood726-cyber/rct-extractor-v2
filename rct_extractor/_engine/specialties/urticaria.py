"""
Anaphylaxis / Chronic Urticaria Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the tuberculosis / ARDS profiles.
Chronic-urticaria and anaphylaxis RCTs report a distinct endpoint vocabulary
(7-day urticaria activity score UAS7, itch severity score ISS7, hives severity
score, urticaria control test UCT, complete response / well-controlled disease,
angioedema, dermatology life quality index, anaphylaxis recurrence) that the
generic effect-size engine does not recognise on its own.

Subspecialties:
- Antihistamine: H1-antihistamines at licensed and updosed (2-4x) doses for
  chronic spontaneous urticaria (cetirizine, levocetirizine, bilastine,
  fexofenadine, rupatadine, desloratadine).
- Biologic: omalizumab, ligelizumab, dupilumab and BTK inhibitors (remibrutinib,
  fenebrutinib) for antihistamine-refractory chronic spontaneous urticaria.
- Anaphylaxis: adrenaline / epinephrine (auto-injector, intranasal), prevention
  of recurrent / biphasic reactions, food and venom anaphylaxis, mast-cell
  activation, peri-procedural prophylaxis.
- Other / immunomodulator: ciclosporin, omalizumab in chronic inducible
  urticaria (cold / cholinergic / symptomatic dermographism).

Effect measures follow what these trials report: continuous (UAS7, ISS7, hives
score, UCT, DLQI) -> mean difference; binary (complete response / UAS7=0,
well-controlled / UAS7<=6, angioedema, anaphylaxis recurrence, responder) ->
RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# URTICARIA / ANAPHYLAXIS ENDPOINTS
# ============================================================

URTICARIA_ENDPOINTS = {
    'UAS7': {
        'aliases': ['uas7', 'urticaria activity score', 'weekly urticaria activity score',
                    '7-day urticaria activity score', 'uas7 score',
                    'urticaria activity score over 7 days', 'change in uas7'],
        'subspecialty': 'antihistamine',
        'measure_types': ['MD']
    },
    'ISS7': {
        'aliases': ['iss7', 'itch severity score', 'weekly itch severity score',
                    'pruritus severity score', 'itch score', 'weekly itch score'],
        'subspecialty': 'antihistamine',
        'measure_types': ['MD']
    },
    'HSS7': {
        'aliases': ['hss7', 'hives severity score', 'weekly hives severity score',
                    'hives score', 'wheal score'],
        'subspecialty': 'antihistamine',
        'measure_types': ['MD']
    },
    'UCT': {
        'aliases': ['urticaria control test', 'uct', 'uct score', 'disease control'],
        'subspecialty': 'biologic',
        'measure_types': ['MD']
    },
    'COMPLETE_RESPONSE': {
        'aliases': ['complete response', 'uas7=0', 'uas7 of 0', 'uas7 = 0',
                    'complete control', 'urticaria-free', 'wheal-free',
                    'symptom-free', 'itch-free and hive-free'],
        'subspecialty': 'biologic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'WELL_CONTROLLED': {
        'aliases': ['well-controlled', 'well controlled disease', 'uas7<=6', 'uas7 <=6',
                    'well-controlled urticaria', 'controlled disease', 'uct >=12',
                    'minimal disease activity'],
        'subspecialty': 'biologic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ANGIOEDEMA': {
        'aliases': ['angioedema', 'angioedema-free days', 'angioedema activity score',
                    'aas', 'angioedema burden', 'angioedema episodes'],
        'subspecialty': 'antihistamine',
        'measure_types': ['RR', 'OR', 'MD']
    },
    'DLQI': {
        'aliases': ['dermatology life quality index', 'dlqi', 'quality of life',
                    'cu-q2ol', 'chronic urticaria quality of life'],
        'subspecialty': 'antihistamine',
        'measure_types': ['MD']
    },
    'ANAPHYLAXIS_RECURRENCE': {
        'aliases': ['anaphylaxis recurrence', 'recurrent anaphylaxis', 'biphasic reaction',
                    'recurrent reaction', 'breakthrough reaction', 'systemic reaction',
                    'anaphylactic reaction', 'allergic reaction'],
        'subspecialty': 'anaphylaxis',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'SYMPTOM_RESOLUTION': {
        'aliases': ['symptom resolution', 'resolution of symptoms', 'time to resolution',
                    'treatment response', 'responder', 'response rate'],
        'subspecialty': 'anaphylaxis',
        'measure_types': ['RR', 'OR', 'MD']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'serious adverse events', 'treatment-related adverse events',
                    'headache', 'injection-site reaction', 'somnolence', 'sedation'],
        'subspecialty': 'biologic',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# ANTIHISTAMINE PATTERNS
# ============================================================

ANTIHISTAMINE_PATTERNS = {
    'detection_keywords': [
        r'h1[- ]?antihistamine|second[- ]generation\s+antihistamine|non[- ]sedating\s+antihistamine',
        r'cetirizine|levocetirizine|bilastine|fexofenadine|rupatadine|desloratadine|loratadine|ebastine',
        r'updos\w+|up[- ]dosing|4[- ]fold|quadruple\s+dose|higher[- ]dose\s+antihistamine',
        r'chronic\s+spontaneous\s+urticaria|\bcsu\b|chronic\s+idiopathic\s+urticaria|\bciu\b',
        r'urticaria\s+activity\s+score|\buas7\b',
    ],
    'endpoint_patterns': [
        (r'\buas7\b|(?:weekly\s+|7[- ]day\s+)?urticaria\s+activity\s+score', 'UAS7'),
        (r'\biss7\b|(?:weekly\s+)?itch\s+severity\s+score|pruritus\s+severity\s+score|itch\s+score',
         'ISS7'),
        (r'\bhss7\b|(?:weekly\s+)?hives\s+severity\s+score|hives\s+score|wheal\s+score', 'HSS7'),
        (r'complete\s+response|uas7\s*=?\s*0|urticaria[- ]free|wheal[- ]free|symptom[- ]free',
         'COMPLETE_RESPONSE'),
        (r'well[- ]controlled|uas7\s*<=?\s*6|controlled\s+disease|uct\s*>=?\s*12', 'WELL_CONTROLLED'),
        (r'angio[- ]?edema(?:[- ]free\s+days|\s+activity\s+score)?|\baas\b', 'ANGIOEDEMA'),
        (r'dermatology\s+life\s+quality\s+index|\bdlqi\b|cu[- ]q2ol|quality\s+of\s+life', 'DLQI'),
        (r'urticaria\s+control\s+test|\buct\b', 'UCT'),
    ],
    'context_patterns': [
        r'antihistamine[- ]refractory', r'licensed\s+dose|standard\s+dose',
    ]
}


# ============================================================
# BIOLOGIC PATTERNS
# ============================================================

BIOLOGIC_PATTERNS = {
    'detection_keywords': [
        r'omalizumab|anti[- ]ige', r'ligelizumab|dupilumab|tezepelumab',
        r'remibrutinib|fenebrutinib|rilzabrutinib|\bbtk\s+inhibitor\b|bruton',
        r'antihistamine[- ]refractory|refractory\s+chronic\s+(?:spontaneous\s+)?urticaria',
        r'urticaria\s+control\s+test|\buct\b|complete\s+response',
        r'barzolvolimab|\bcdx[- ]?0159\b',
    ],
    'endpoint_patterns': [
        (r'\buas7\b|(?:weekly\s+|7[- ]day\s+)?urticaria\s+activity\s+score', 'UAS7'),
        (r'\biss7\b|(?:weekly\s+)?itch\s+severity\s+score', 'ISS7'),
        (r'\bhss7\b|(?:weekly\s+)?hives\s+severity\s+score', 'HSS7'),
        (r'complete\s+response|uas7\s*=?\s*0|urticaria[- ]free|wheal[- ]free', 'COMPLETE_RESPONSE'),
        (r'well[- ]controlled|uas7\s*<=?\s*6|uct\s*>=?\s*12|minimal\s+disease\s+activity',
         'WELL_CONTROLLED'),
        (r'urticaria\s+control\s+test|\buct\b', 'UCT'),
        (r'angio[- ]?edema', 'ANGIOEDEMA'),
        (r'dermatology\s+life\s+quality\s+index|\bdlqi\b|quality\s+of\s+life', 'DLQI'),
        (r'injection[- ]site\s+reaction|serious\s+adverse|headache', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'every\s+4\s+weeks|q4w', r'\d+\s*mg\s+(?:subcutaneous|every)',
    ]
}


# ============================================================
# ANAPHYLAXIS PATTERNS
# ============================================================

ANAPHYLAXIS_PATTERNS = {
    'detection_keywords': [
        r'anaphylaxis|anaphylactic', r'(?:adrenaline|epinephrine)\s+(?:auto[- ]?injector|autoinjector)',
        r'intranasal\s+(?:adrenaline|epinephrine)|neffy',
        r'biphasic\s+reaction|recurrent\s+anaphylaxis',
        r'food\s+(?:allergy|anaphylaxis)|venom\s+(?:allergy|immunotherapy)|peanut\s+allergy',
        r'mast\s+cell\s+activation|systemic\s+mastocytosis',
    ],
    'endpoint_patterns': [
        (r'(?:recurrent\s+)?anaphylaxis(?:\s+recurrence)?|biphasic\s+reaction|recurrent\s+reaction|'
         r'breakthrough\s+reaction|systemic\s+(?:allergic\s+)?reaction|anaphylactic\s+reaction',
         'ANAPHYLAXIS_RECURRENCE'),
        (r'symptom\s+resolution|resolution\s+of\s+symptoms|time\s+to\s+resolution|'
         r'treatment\s+response|responder|response\s+rate', 'SYMPTOM_RESOLUTION'),
        (r'serious\s+adverse|injection[- ]site\s+reaction|treatment[- ]related\s+adverse',
         'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'pharmacokinetic|cmax|tmax', r'oral\s+(?:food\s+)?challenge|sustained\s+unresponsiveness',
    ]
}


# ============================================================
# OTHER / INDUCIBLE PATTERNS
# ============================================================

OTHER_PATTERNS = {
    'detection_keywords': [
        r'ciclosporin|cyclosporine', r'chronic\s+inducible\s+urticaria|\bcindu\b',
        r'cold\s+urticaria|cholinergic\s+urticaria|symptomatic\s+dermographism|'
        r'delayed\s+pressure\s+urticaria|solar\s+urticaria',
        r'critical\s+temperature\s+threshold|trigger\s+threshold',
    ],
    'endpoint_patterns': [
        (r'\buas7\b|urticaria\s+activity\s+score', 'UAS7'),
        (r'critical\s+temperature\s+threshold|trigger\s+threshold|complete\s+response|'
         r'urticaria[- ]free', 'COMPLETE_RESPONSE'),
        (r'well[- ]controlled|uct\s*>=?\s*12', 'WELL_CONTROLLED'),
        (r'urticaria\s+control\s+test|\buct\b', 'UCT'),
        (r'\biss7\b|itch\s+severity\s+score', 'ISS7'),
        (r'dermatology\s+life\s+quality\s+index|\bdlqi\b|quality\s+of\s+life', 'DLQI'),
    ],
    'context_patterns': [
        r'provocation\s+test', r'temp[- ]?test|friction',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_urticaria_subspecialty(text: str) -> Tuple[str, float]:
    """Detect chronic-urticaria / anaphylaxis trial subspecialty.
    Returns (subspecialty, confidence). Subspecialties: antihistamine, biologic,
    anaphylaxis, other, general_urticaria."""
    text_lower = text.lower()
    scores = {'antihistamine': 0, 'biologic': 0, 'anaphylaxis': 0, 'other': 0}
    for kw in ANTIHISTAMINE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['antihistamine'] += 1
    for kw in BIOLOGIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['biologic'] += 1
    for kw in ANAPHYLAXIS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['anaphylaxis'] += 1
    for kw in OTHER_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['other'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_urticaria', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_urticaria_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'antihistamine': ANTIHISTAMINE_PATTERNS['endpoint_patterns'],
        'biologic': BIOLOGIC_PATTERNS['endpoint_patterns'],
        'anaphylaxis': ANAPHYLAXIS_PATTERNS['endpoint_patterns'],
        'other': OTHER_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_urticaria_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical urticaria/anaphylaxis endpoint, preferring the
    LONGEST matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in URTICARIA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
