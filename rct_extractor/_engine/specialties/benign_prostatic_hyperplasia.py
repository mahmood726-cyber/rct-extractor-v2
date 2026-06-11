"""
Benign Prostatic Hyperplasia (BPH / LUTS) Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the urology / women's-health
profiles. BPH with lower-urinary-tract symptoms (LUTS) is one of the commonest
conditions in ageing men and its RCTs (alpha-blockers, 5-alpha-reductase
inhibitors, PDE5 inhibitors, combination therapy, and the surgical/minimally
invasive procedures TURP, HoLEP, GreenLight PVP, UroLift, Rezum, prostatic artery
embolisation) report a distinct symptom / flow / progression endpoint vocabulary
the generic effect-size engine does not recognise on its own.

Subspecialties:
- Symptoms (LUTS): International Prostate Symptom Score (IPSS) total and
  storage/voiding subscores, IPSS quality-of-life index, symptom responder.
  Interventions: tamsulosin, alfuzosin, silodosin, doxazosin, terazosin
  (alpha-blockers); finasteride, dutasteride (5-ARI); tadalafil (PDE5);
  combination.
- Flow (urodynamic): maximum urinary flow rate (Qmax), post-void residual (PVR),
  prostate volume.
- Progression (clinical progression / surgery): acute urinary retention (AUR),
  BPH-related surgery, clinical progression, treatment failure.
- Sexual (ejaculatory / safety): ejaculatory dysfunction / retrograde
  ejaculation, erectile dysfunction as an adverse event.

Effect measures follow what these trials report: binary / time-to-event (acute
urinary retention, BPH surgery, clinical progression, symptom responder,
ejaculatory dysfunction) -> RR/OR/HR; continuous (IPSS total/subscore, IPSS QoL,
Qmax, post-void residual, prostate volume) -> MD/SMD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# BPH / LUTS ENDPOINTS
# ============================================================

BENIGN_PROSTATIC_HYPERPLASIA_ENDPOINTS = {
    # --- Symptoms (LUTS) ---
    'IPSS_TOTAL': {
        'aliases': ['ipss', 'international prostate symptom score', 'total ipss',
                    'ipss total score', 'total symptom score', 'aua symptom index',
                    'aua-si', 'ipss total'],
        'subspecialty': 'symptoms',
        'measure_types': ['MD', 'SMD']
    },
    'IPSS_STORAGE': {
        'aliases': ['ipss storage', 'storage subscore', 'storage symptom score',
                    'irritative symptom score', 'storage ipss'],
        'subspecialty': 'symptoms',
        'measure_types': ['MD', 'SMD']
    },
    'IPSS_VOIDING': {
        'aliases': ['ipss voiding', 'voiding subscore', 'voiding symptom score',
                    'obstructive symptom score', 'voiding ipss'],
        'subspecialty': 'symptoms',
        'measure_types': ['MD', 'SMD']
    },
    'IPSS_QOL': {
        'aliases': ['ipss quality of life', 'quality of life index', 'qol index',
                    'ipss qol', 'quality-of-life score', 'bother score'],
        'subspecialty': 'symptoms',
        'measure_types': ['MD', 'SMD']
    },
    'SYMPTOM_RESPONSE': {
        'aliases': ['symptom response', 'responder', 'response rate', 'responders',
                    'clinically meaningful improvement', 'treatment response',
                    'at least 25% improvement', '3-point improvement'],
        'subspecialty': 'symptoms',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Flow (urodynamic) ---
    'QMAX': {
        'aliases': ['maximum flow rate', 'maximum urinary flow rate', 'qmax',
                    'peak flow rate', 'maximum flow', 'peak urinary flow'],
        'subspecialty': 'flow',
        'measure_types': ['MD', 'SMD']
    },
    'POST_VOID_RESIDUAL': {
        'aliases': ['post-void residual', 'postvoid residual', 'post void residual',
                    'residual urine volume', 'pvr'],
        'subspecialty': 'flow',
        'measure_types': ['MD', 'SMD']
    },
    'PROSTATE_VOLUME': {
        'aliases': ['prostate volume', 'prostatic volume', 'total prostate volume',
                    'prostate size', 'change in prostate volume'],
        'subspecialty': 'flow',
        'measure_types': ['MD', 'SMD']
    },

    # --- Progression (clinical progression / surgery) ---
    'ACUTE_URINARY_RETENTION': {
        'aliases': ['acute urinary retention', 'urinary retention', 'aur',
                    'episodes of retention'],
        'subspecialty': 'progression',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'BPH_SURGERY': {
        'aliases': ['bph surgery', 'bph-related surgery', 'surgery for bph',
                    'need for surgery', 'surgical intervention', 'invasive therapy',
                    'prostate surgery'],
        'subspecialty': 'progression',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CLINICAL_PROGRESSION': {
        'aliases': ['clinical progression', 'bph progression',
                    'disease progression', 'overall clinical progression',
                    'progression of bph'],
        'subspecialty': 'progression',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'TREATMENT_FAILURE': {
        'aliases': ['treatment failure', 'therapeutic failure',
                    'lack of efficacy', 'failure of medical therapy'],
        'subspecialty': 'progression',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Sexual (ejaculatory / safety) ---
    'EJACULATORY_DYSFUNCTION': {
        'aliases': ['ejaculatory dysfunction', 'retrograde ejaculation',
                    'abnormal ejaculation', 'anejaculation', 'ejaculation disorder',
                    'reduced ejaculate'],
        'subspecialty': 'sexual',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ERECTILE_DYSFUNCTION_AE': {
        'aliases': ['erectile dysfunction', 'impotence', 'decreased libido',
                    'sexual dysfunction'],
        'subspecialty': 'sexual',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# SYMPTOMS (LUTS) PATTERNS
# ============================================================

SYMPTOMS_PATTERNS = {
    'detection_keywords': [
        r'international\s+prostate\s+symptom\s+score|\bipss\b',
        r'lower\s+urinary\s+tract\s+symptoms?|\bluts\b', r'aua\s+symptom',
        r'tamsulosin|alfuzosin|silodosin|doxazosin|terazosin',
        r'finasteride|dutasteride', r'tadalafil', r'alpha[- ]?blocker',
        r'5[- ]?alpha[- ]?reductase|5[- ]?ari', r'symptom\s+score',
    ],
    'endpoint_patterns': [
        (r'storage\s+(?:subscore|symptom\s+score)|irritative\s+symptom|ipss\s+storage',
         'IPSS_STORAGE'),
        (r'voiding\s+(?:subscore|symptom\s+score)|obstructive\s+symptom|ipss\s+voiding',
         'IPSS_VOIDING'),
        (r'ipss\s+(?:quality\s+of\s+life|qol)|quality[- ]of[- ]life\s+(?:index|score)|'
         r'\bqol\s+index\b|bother\s+score', 'IPSS_QOL'),
        (r'international\s+prostate\s+symptom\s+score|\bipss\b(?:\s+total)?|'
         r'total\s+symptom\s+score|aua\s+symptom\s+index|aua[- ]si', 'IPSS_TOTAL'),
        (r'symptom\s+respon(?:se|der)|respon(?:se|der)s?(?:\s+rate)?|'
         r'clinically\s+meaningful\s+improvement|treatment\s+response|'
         r'(?:25%|3[- ]point)\s+improvement', 'SYMPTOM_RESPONSE'),
    ],
    'context_patterns': [
        r'change\s+from\s+baseline', r'week\s+(?:12|24)|month\s+(?:6|12)',
        r'points?\b',
    ]
}


# ============================================================
# FLOW (urodynamic) PATTERNS
# ============================================================

FLOW_PATTERNS = {
    'detection_keywords': [
        r'maximum\s+(?:urinary\s+)?flow\s+rate|\bqmax\b|peak\s+flow',
        r'post[- ]?void\s+residual|\bpvr\b', r'prostate\s+volume|prostatic\s+volume',
        r'uroflow', r'urodynamic',
    ],
    'endpoint_patterns': [
        (r'maximum\s+(?:urinary\s+)?flow\s+rate|\bqmax\b|peak\s+(?:urinary\s+)?flow',
         'QMAX'),
        (r'post[- ]?void\s+residual|residual\s+urine\s+volume|\bpvr\b',
         'POST_VOID_RESIDUAL'),
        (r'(?:total\s+)?prostat(?:e|ic)\s+volume|prostate\s+size|change\s+in\s+prostate\s+volume',
         'PROSTATE_VOLUME'),
    ],
    'context_patterns': [
        r'ml\/s|millilit\w+\s+per\s+second', r'\bml\b', r'transrectal\s+ultrasound',
    ]
}


# ============================================================
# PROGRESSION PATTERNS
# ============================================================

PROGRESSION_PATTERNS = {
    'detection_keywords': [
        r'acute\s+urinary\s+retention|\baur\b', r'bph[- ]related\s+surgery|surgery\s+for\s+bph',
        r'clinical\s+progression', r'transurethral\s+resection|\bturp\b',
        r'need\s+for\s+surgery', r'invasive\s+therapy', r'treatment\s+failure',
        r'holep|greenlight|photoselective|prostatic\s+urethral\s+lift|urolift|rezum|'
        r'prostatic\s+artery\s+emboli[sz]ation',
    ],
    'endpoint_patterns': [
        (r'acute\s+urinary\s+retention|\baur\b|episodes?\s+of\s+(?:urinary\s+)?retention|'
         r'urinary\s+retention', 'ACUTE_URINARY_RETENTION'),
        (r'bph[- ]?(?:related\s+)?surgery|surgery\s+for\s+bph|need\s+for\s+surgery|'
         r'surgical\s+intervention|invasive\s+therapy|prostate\s+surgery', 'BPH_SURGERY'),
        (r'clinical\s+progression|bph\s+progression|disease\s+progression|'
         r'progression\s+of\s+bph', 'CLINICAL_PROGRESSION'),
        (r'treatment\s+failure|therapeutic\s+failure|lack\s+of\s+efficacy|'
         r'failure\s+of\s+medical\s+therapy', 'TREATMENT_FAILURE'),
    ],
    'context_patterns': [
        r'over\s+\d+\s+years', r'per\s+(?:100\s+)?(?:patient|person)[- ]years',
        r'time\s+to',
    ]
}


# ============================================================
# SEXUAL PATTERNS
# ============================================================

SEXUAL_PATTERNS = {
    'detection_keywords': [
        r'ejaculatory\s+dysfunction|retrograde\s+ejaculation|abnormal\s+ejaculation',
        r'anejaculation', r'erectile\s+dysfunction', r'sexual\s+dysfunction',
        r'decreased\s+libido',
    ],
    'endpoint_patterns': [
        (r'ejaculatory\s+dysfunction|retrograde\s+ejaculation|abnormal\s+ejaculation|'
         r'anejaculation|ejaculation\s+disorder|reduced\s+ejaculate', 'EJACULATORY_DYSFUNCTION'),
        (r'erectile\s+dysfunction|\bimpotence\b|decreased\s+libido|sexual\s+dysfunction',
         'ERECTILE_DYSFUNCTION_AE'),
    ],
    'context_patterns': [
        r'adverse\s+event', r'treatment[- ]emergent',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_benign_prostatic_hyperplasia_subspecialty(text: str) -> Tuple[str, float]:
    """Detect BPH/LUTS trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: symptoms, flow, progression, sexual, general_bph."""
    text_lower = text.lower()
    scores = {'symptoms': 0, 'flow': 0, 'progression': 0, 'sexual': 0}
    for kw in SYMPTOMS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['symptoms'] += 1
    for kw in FLOW_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['flow'] += 1
    for kw in PROGRESSION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['progression'] += 1
    for kw in SEXUAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['sexual'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_bph', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_benign_prostatic_hyperplasia_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'symptoms': SYMPTOMS_PATTERNS['endpoint_patterns'],
        'flow': FLOW_PATTERNS['endpoint_patterns'],
        'progression': PROGRESSION_PATTERNS['endpoint_patterns'],
        'sexual': SEXUAL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_benign_prostatic_hyperplasia_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical BPH endpoint, preferring the LONGEST matching alias
    so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in BENIGN_PROSTATIC_HYPERPLASIA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
