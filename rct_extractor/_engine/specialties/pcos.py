"""
Polycystic Ovary Syndrome (PCOS) Subspecialty Patterns and Endpoints

PCOS is the commonest metabolic-endocrine disorder of reproductive-age women
(insulin resistance, hyperandrogenism, anovulation). Its RCTs report a
ratio-rich reproductive vocabulary (ovulation, clinical pregnancy, live birth,
miscarriage) alongside continuous metabolic / androgen endpoints, which neither
the diabetes nor the maternal-neonatal specialty covers.

Subspecialties:
- reproductive: ovulation rate, clinical pregnancy, live birth, miscarriage,
  multiple pregnancy (ovulation-induction trials — letrozole, clomifene,
  metformin, gonadotropins, laparoscopic ovarian drilling).
- metabolic (continuous): body weight / BMI, HbA1c, fasting insulin / HOMA-IR.
- androgen (continuous + binary): total testosterone, SHBG, Ferriman-Gallwey
  hirsutism score; menstrual regularity.
- safety: ovarian hyperstimulation syndrome (OHSS), multiple pregnancy,
  gastrointestinal adverse events.

Effect measures: reproductive / menstrual / safety events -> RR/OR; weight / BMI /
HbA1c / HOMA-IR / testosterone / SHBG / hirsutism score -> MD/SMD (continuous).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# PCOS ENDPOINTS
# ============================================================

PCOS_ENDPOINTS = {
    # --- reproductive ---
    'OVULATION_RATE': {
        'aliases': ['ovulation rate', 'ovulation', 'ovulatory rate', 'cumulative ovulation rate',
                    'ovulation per cycle'],
        'subspecialty': 'reproductive',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'CLINICAL_PREGNANCY': {
        'aliases': ['clinical pregnancy rate', 'clinical pregnancy', 'pregnancy rate', 'pregnancy'],
        'subspecialty': 'reproductive',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'LIVE_BIRTH': {
        'aliases': ['live birth rate', 'live birth', 'live-birth rate', 'cumulative live birth'],
        'subspecialty': 'reproductive',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MISCARRIAGE': {
        'aliases': ['miscarriage rate', 'miscarriage', 'spontaneous abortion', 'pregnancy loss',
                    'early pregnancy loss'],
        'subspecialty': 'reproductive',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MULTIPLE_PREGNANCY': {
        'aliases': ['multiple pregnancy rate', 'multiple pregnancy', 'twin pregnancy',
                    'multiple gestation'],
        'subspecialty': 'reproductive',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- metabolic (continuous) ---
    'BMI_WEIGHT': {
        'aliases': ['body mass index', 'bmi', 'body weight', 'weight', 'change in body mass index',
                    'change in body weight'],
        'subspecialty': 'metabolic',
        'measure_types': ['MD', 'SMD']
    },
    'HOMA_IR': {
        'aliases': ['homa-ir', 'homeostatic model assessment of insulin resistance',
                    'insulin resistance index', 'fasting insulin', 'homa ir'],
        'subspecialty': 'metabolic',
        'measure_types': ['MD', 'SMD']
    },
    'HBA1C': {
        'aliases': ['hba1c', 'glycated haemoglobin', 'glycated hemoglobin',
                    'fasting plasma glucose', 'fasting glucose'],
        'subspecialty': 'metabolic',
        'measure_types': ['MD', 'SMD']
    },

    # --- androgen ---
    'TESTOSTERONE': {
        'aliases': ['total testosterone', 'testosterone', 'serum testosterone',
                    'free testosterone', 'free androgen index'],
        'subspecialty': 'androgen',
        'measure_types': ['MD', 'SMD']
    },
    'SHBG': {
        'aliases': ['sex hormone-binding globulin', 'sex hormone binding globulin', 'shbg'],
        'subspecialty': 'androgen',
        'measure_types': ['MD', 'SMD']
    },
    'HIRSUTISM': {
        'aliases': ['ferriman-gallwey score', 'ferriman gallwey', 'hirsutism score',
                    'modified ferriman-gallwey', 'mfg score'],
        'subspecialty': 'androgen',
        'measure_types': ['MD', 'SMD']
    },
    'MENSTRUAL_REGULARITY': {
        'aliases': ['menstrual regularity', 'menstrual cyclicity', 'regular menstrual cycles',
                    'menstrual frequency', 'restoration of menses', 'improved menstrual'],
        'subspecialty': 'androgen',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- safety ---
    'OHSS': {
        'aliases': ['ovarian hyperstimulation syndrome', 'ohss', 'ovarian hyperstimulation'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'GI_ADVERSE_EVENTS': {
        'aliases': ['gastrointestinal adverse events', 'gastrointestinal side effects', 'nausea',
                    'gastrointestinal disturbance'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# REPRODUCTIVE PATTERNS
# ============================================================

REPRODUCTIVE_PATTERNS = {
    'detection_keywords': [
        r'ovulation\s+(?:rate|induction)|ovulatory', r'clinical\s+pregnancy', r'live\s+birth',
        r'miscarriage|spontaneous\s+abortion', r'multiple\s+pregnancy', r'pregnancy\s+rate',
        r'ovulation\b',
    ],
    'endpoint_patterns': [
        (r'(?:cumulative\s+)?live[- ]birth(?:\s+rate)?', 'LIVE_BIRTH'),
        (r'clinical\s+pregnancy(?:\s+rate)?|pregnancy\s+rate', 'CLINICAL_PREGNANCY'),
        (r'(?:cumulative\s+)?ovulation(?:\s+rate|\s+per\s+cycle)?|ovulatory\s+rate', 'OVULATION_RATE'),
        (r'miscarriage(?:\s+rate)?|spontaneous\s+abortion|(?:early\s+)?pregnancy\s+loss', 'MISCARRIAGE'),
        (r'multiple\s+(?:pregnancy|gestation)(?:\s+rate)?|twin\s+pregnancy', 'MULTIPLE_PREGNANCY'),
    ],
    'context_patterns': [
        r'per\s+(?:woman|cycle|patient)', r'ovulation\s+induction', r'intention[- ]to[- ]treat',
    ]
}


# ============================================================
# METABOLIC PATTERNS (continuous)
# ============================================================

METABOLIC_PATTERNS = {
    'detection_keywords': [
        r'body\s+mass\s+index|\bbmi\b', r'body\s+weight', r'homa[- ]ir|insulin\s+resistance',
        r'fasting\s+insulin', r'hba1c|fasting\s+(?:plasma\s+)?glucose',
    ],
    'endpoint_patterns': [
        (r'homa[- ]ir|homeostatic\s+model\s+assessment|fasting\s+insulin|insulin\s+resistance\s+index',
         'HOMA_IR'),
        (r'hba1c|glycated\s+h[ae]moglobin|fasting\s+(?:plasma\s+)?glucose', 'HBA1C'),
        (r'(?:change\s+in\s+)?body\s+mass\s+index|\bbmi\b|(?:change\s+in\s+)?body\s+weight', 'BMI_WEIGHT'),
    ],
    'context_patterns': [
        r'kg/m', r'\bkg\b', r'mg/dl|µu/ml|uiu/ml',
    ]
}


# ============================================================
# ANDROGEN PATTERNS
# ============================================================

ANDROGEN_PATTERNS = {
    'detection_keywords': [
        r'total\s+testosterone|free\s+testosterone|testosterone',
        r'sex\s+hormone[- ]binding\s+globulin|\bshbg\b', r'free\s+androgen\s+index',
        r'ferriman[- ]gallwey|hirsutism', r'menstrual\s+(?:regularity|cyclicity|frequency)',
    ],
    'endpoint_patterns': [
        (r'sex\s+hormone[- ]binding\s+globulin|\bshbg\b', 'SHBG'),
        (r'ferriman[- ]gallwey(?:\s+score)?|hirsutism\s+score|\bmfg\s+score\b', 'HIRSUTISM'),
        (r'menstrual\s+(?:regularity|cyclicity|frequency)|regular\s+menstrual\s+cycles|'
         r'restoration\s+of\s+menses', 'MENSTRUAL_REGULARITY'),
        (r'(?:total\s+|free\s+|serum\s+)?testosterone|free\s+androgen\s+index', 'TESTOSTERONE'),
    ],
    'context_patterns': [
        r'nmol/l|ng/dl', r'androgen', r'biochemical\s+hyperandrogenism',
    ]
}


# ============================================================
# SAFETY PATTERNS
# ============================================================

SAFETY_PATTERNS = {
    'detection_keywords': [
        r'ovarian\s+hyperstimulation|\bohss\b', r'gastrointestinal\s+(?:adverse|side)',
        r'multiple\s+pregnancy', r'adverse\s+events',
    ],
    'endpoint_patterns': [
        (r'ovarian\s+hyperstimulation\s+syndrome|\bohss\b|ovarian\s+hyperstimulation', 'OHSS'),
        (r'gastrointestinal\s+(?:adverse\s+events|side\s+effects|disturbance)|\bnausea\b',
         'GI_ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'\bsafety\b', r'tolerability', r'most\s+common\s+adverse',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_pcos_subspecialty(text: str) -> Tuple[str, float]:
    """Detect PCOS trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: reproductive, metabolic, androgen, safety, general_pcos."""
    text_lower = text.lower()
    scores = {'reproductive': 0, 'metabolic': 0, 'androgen': 0, 'safety': 0}
    for kw in REPRODUCTIVE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['reproductive'] += 1
    for kw in METABOLIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['metabolic'] += 1
    for kw in ANDROGEN_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['androgen'] += 1
    for kw in SAFETY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['safety'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_pcos', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_pcos_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'reproductive': REPRODUCTIVE_PATTERNS['endpoint_patterns'],
        'metabolic': METABOLIC_PATTERNS['endpoint_patterns'],
        'androgen': ANDROGEN_PATTERNS['endpoint_patterns'],
        'safety': SAFETY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_pcos_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical PCOS endpoint, preferring the LONGEST matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in PCOS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
