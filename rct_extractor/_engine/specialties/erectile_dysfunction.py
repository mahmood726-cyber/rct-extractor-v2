"""
Erectile Dysfunction (ED) Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the BPH / women's-health profiles.
Erectile dysfunction RCTs (PDE5 inhibitors, intracavernosal/intraurethral
alprostadil, low-intensity shockwave, regenerative therapies, vacuum devices and
penile prostheses) report a distinct validated-questionnaire endpoint vocabulary
(IIEF, SEP, GAQ, EHS) that the generic effect-size engine does not recognise on
its own.

Subspecialties:
- Pharmacologic: oral PDE5 inhibitors (sildenafil, tadalafil, vardenafil,
  avanafil, udenafil), intracavernosal / intraurethral alprostadil, testosterone.
- Shockwave: low-intensity extracorporeal shockwave therapy (Li-ESWT), platelet-
  rich plasma, stem-cell / regenerative therapy.
- Device: vacuum erection device, penile prosthesis / implant, constriction ring.
- Safety: PDE5-class adverse events - headache, flushing, dyspepsia, nasal
  congestion, visual disturbance, priapism, back pain.

Endpoints (shared across subspecialties): IIEF erectile-function domain score,
SEP question 2 (penetration) and question 3 (successful intercourse) success
rates, Global Assessment Question (GAQ) responder, Erection Hardness Score (EHS),
successful-intercourse rate, treatment satisfaction (EDITS).

Effect measures: continuous (IIEF-EF, EHS, EDITS) -> MD/SMD; binary (SEP2, SEP3,
GAQ responder, successful intercourse, class adverse events) -> RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# ERECTILE DYSFUNCTION ENDPOINTS
# ============================================================

ERECTILE_DYSFUNCTION_ENDPOINTS = {
    # --- Efficacy questionnaires (shared) ---
    'IIEF_EF': {
        'aliases': ['iief-ef', 'iief erectile function', 'erectile function domain',
                    'international index of erectile function', 'iief',
                    'iief-5', 'iief ef domain', 'ef domain score'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['MD', 'SMD']
    },
    'SEP2': {
        'aliases': ['sep2', 'sep question 2', 'sexual encounter profile question 2',
                    'penetration success', 'sep q2', 'successful penetration'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SEP3': {
        'aliases': ['sep3', 'sep question 3', 'sexual encounter profile question 3',
                    'successful intercourse', 'sep q3', 'maintenance of erection',
                    'completion of intercourse'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'GAQ': {
        'aliases': ['gaq', 'global assessment question', 'global efficacy question',
                    'improved erection', 'improvement in erection', 'responder rate'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'EHS': {
        'aliases': ['ehs', 'erection hardness score', 'erection hardness grade',
                    'hardness score', 'ehs >= 3', 'ehs grade'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['MD', 'SMD', 'RR', 'OR']
    },
    'SUCCESSFUL_INTERCOURSE': {
        'aliases': ['successful sexual intercourse', 'successful intercourse attempts',
                    'intercourse success rate', 'successful attempts',
                    'successful sexual attempts'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TREATMENT_SATISFACTION': {
        'aliases': ['treatment satisfaction', 'edits', 'satisfaction score',
                    'erectile dysfunction inventory of treatment satisfaction',
                    'overall satisfaction'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['MD', 'SMD']
    },

    # --- Safety (PDE5-class adverse events) ---
    'HEADACHE': {
        'aliases': ['headache', 'cephalalgia'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'FLUSHING': {
        'aliases': ['flushing', 'facial flushing', 'hot flush'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'DYSPEPSIA': {
        'aliases': ['dyspepsia', 'indigestion', 'gastrointestinal upset'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'NASAL_CONGESTION': {
        'aliases': ['nasal congestion', 'rhinitis', 'stuffy nose'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'VISUAL_DISTURBANCE': {
        'aliases': ['visual disturbance', 'abnormal vision', 'chromatopsia',
                    'blue vision', 'visual adverse event'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PRIAPISM': {
        'aliases': ['priapism', 'prolonged erection'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# PHARMACOLOGIC PATTERNS
# ============================================================

PHARMACOLOGIC_PATTERNS = {
    'detection_keywords': [
        # intervention-based only; shared outcome measures (IIEF / SEP / EHS)
        # appear in EVERY ED trial regardless of arm, so they are deliberately
        # NOT detection keywords (they would dilute shockwave/device routing).
        r'sildenafil|tadalafil|vardenafil|avanafil|udenafil|mirodenafil',
        r'phosphodiesterase[- ]?5|pde[- ]?5\s+inhibitor', r'alprostadil',
        r'intracavernosal|intraurethral', r'testosterone(?:\s+(?:therapy|replacement))?',
        r'oral\s+pde5|on[- ]demand\s+(?:sildenafil|tadalafil|vardenafil)',
    ],
    'endpoint_patterns': [
        (r'iief[- ]?ef|erectile\s+function\s+domain|international\s+index\s+of\s+erectile\s+function|'
         r'\biief(?:[- ]?5)?\b|ef\s+domain', 'IIEF_EF'),
        (r'\bsep\s?2\b|sep\s+question\s+2|penetration\s+success|successful\s+penetration',
         'SEP2'),
        (r'\bsep\s?3\b|sep\s+question\s+3|successful\s+(?:sexual\s+)?intercourse|'
         r'maintenance\s+of\s+erection|completion\s+of\s+intercourse', 'SEP3'),
        (r'global\s+(?:assessment|efficacy)\s+question|\bgaq\b|improved?\s+erection|'
         r'improvement\s+in\s+erection', 'GAQ'),
        (r'erection\s+hardness\s+(?:score|grade)|\behs\b|hardness\s+score', 'EHS'),
        (r'successful\s+(?:sexual\s+)?(?:intercourse|attempts)|intercourse\s+success',
         'SUCCESSFUL_INTERCOURSE'),
        (r'treatment\s+satisfaction|\bedits\b|satisfaction\s+score|overall\s+satisfaction',
         'TREATMENT_SATISFACTION'),
    ],
    'context_patterns': [
        r'on[- ]demand|once[- ]daily', r'change\s+from\s+baseline', r'per\s+attempt',
    ]
}


# ============================================================
# SHOCKWAVE PATTERNS
# ============================================================

SHOCKWAVE_PATTERNS = {
    'detection_keywords': [
        r'shock\s*wave|shockwave|li[- ]?eswt|extracorporeal\s+shock',
        r'low[- ]intensity\s+(?:extracorporeal\s+)?shock',
        r'platelet[- ]rich\s+plasma|\bprp\b', r'stem[- ]cell|regenerative',
    ],
    'endpoint_patterns': [
        (r'iief[- ]?ef|erectile\s+function\s+domain|\biief(?:[- ]?5)?\b', 'IIEF_EF'),
        (r'erection\s+hardness\s+(?:score|grade)|\behs\b', 'EHS'),
        (r'\bsep\s?3\b|successful\s+(?:sexual\s+)?intercourse', 'SEP3'),
        (r'global\s+(?:assessment|efficacy)\s+question|\bgaq\b', 'GAQ'),
    ],
    'context_patterns': [
        r'energy\s+flux\s+density', r'sessions?', r'sham[- ]controlled',
    ]
}


# ============================================================
# DEVICE PATTERNS
# ============================================================

DEVICE_PATTERNS = {
    'detection_keywords': [
        r'vacuum\s+erection\s+device|vacuum\s+constriction', r'penile\s+prosthesis|penile\s+implant',
        r'constriction\s+ring', r'inflatable\s+penile',
    ],
    'endpoint_patterns': [
        (r'iief[- ]?ef|erectile\s+function\s+domain|\biief(?:[- ]?5)?\b', 'IIEF_EF'),
        (r'\bsep\s?3\b|successful\s+(?:sexual\s+)?intercourse', 'SEP3'),
        (r'treatment\s+satisfaction|\bedits\b|satisfaction\s+score', 'TREATMENT_SATISFACTION'),
        (r'erection\s+hardness\s+(?:score|grade)|\behs\b', 'EHS'),
    ],
    'context_patterns': [
        r'mechanical\s+failure', r'device\s+satisfaction',
    ]
}


# ============================================================
# SAFETY PATTERNS
# ============================================================

SAFETY_PATTERNS = {
    'detection_keywords': [
        r'headache', r'flushing', r'dyspepsia', r'nasal\s+congestion',
        r'visual\s+disturbance|chromatopsia', r'priapism|prolonged\s+erection',
        r'adverse\s+events?',
    ],
    'endpoint_patterns': [
        (r'headache|cephalalgia', 'HEADACHE'),
        (r'(?:facial\s+)?flushing|hot\s+flush', 'FLUSHING'),
        (r'dyspepsia|indigestion', 'DYSPEPSIA'),
        (r'nasal\s+congestion|rhinitis|stuffy\s+nose', 'NASAL_CONGESTION'),
        (r'visual\s+disturbance|abnormal\s+vision|chromatopsia|blue\s+vision',
         'VISUAL_DISTURBANCE'),
        (r'priapism|prolonged\s+erection', 'PRIAPISM'),
    ],
    'context_patterns': [
        r'treatment[- ]emergent', r'most\s+common\s+adverse',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_erectile_dysfunction_subspecialty(text: str) -> Tuple[str, float]:
    """Detect ED trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: pharmacologic, shockwave, device, safety, general_ed."""
    text_lower = text.lower()
    scores = {'pharmacologic': 0, 'shockwave': 0, 'device': 0, 'safety': 0}
    for kw in PHARMACOLOGIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pharmacologic'] += 1
    for kw in SHOCKWAVE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['shockwave'] += 1
    for kw in DEVICE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['device'] += 1
    for kw in SAFETY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['safety'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_ed', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_erectile_dysfunction_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'pharmacologic': PHARMACOLOGIC_PATTERNS['endpoint_patterns'],
        'shockwave': SHOCKWAVE_PATTERNS['endpoint_patterns'],
        'device': DEVICE_PATTERNS['endpoint_patterns'],
        'safety': SAFETY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_erectile_dysfunction_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical ED endpoint, preferring the LONGEST matching alias
    so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in ERECTILE_DYSFUNCTION_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
