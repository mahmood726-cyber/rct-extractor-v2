"""
Osteoporosis / Metabolic Bone Disease Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow as the other cardio-metabolic profiles.
Osteoporosis RCTs (anti-resorptive and anabolic therapy in postmenopausal women
and others) report a distinct endpoint vocabulary (vertebral / hip / non-vertebral
fracture, bone mineral density at spine and hip, bone-turnover markers) that the
generic effect-size engine does not recognise.

Subspecialties:
- fracture: vertebral, non-vertebral, hip, clinical and any fracture (the primary
  hard endpoints).
- bmd (continuous): percent change in bone mineral density at the lumbar spine,
  total hip and femoral neck.
- bone_turnover (continuous): bone-turnover markers — serum CTX (C-telopeptide),
  P1NP (procollagen type-1 N-propeptide), bone-specific alkaline phosphatase.
- safety: osteonecrosis of the jaw, atypical femoral fracture, hypocalcaemia,
  injection-site / GI adverse events, treatment discontinuation.

Drug classes (arm labels): bisphosphonates (alendronate, risedronate, ibandronate,
zoledronic acid), denosumab (RANKL inhibitor), anabolics (teriparatide,
abaloparatide), romosozumab (sclerostin inhibitor), SERMs (raloxifene,
bazedoxifene), strontium ranelate, calcium + vitamin D, hormone therapy, placebo.

Effect measures: fractures and safety events -> RR/OR/HR (binary / time-to-event);
BMD percent change and bone-turnover markers -> MD/SMD (continuous, natural scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# OSTEOPOROSIS ENDPOINTS
# ============================================================

OSTEOPOROSIS_ENDPOINTS = {
    # --- fracture ---
    'VERTEBRAL_FRACTURE': {
        'aliases': ['vertebral fracture', 'new vertebral fracture', 'morphometric vertebral fracture',
                    'radiographic vertebral fracture', 'clinical vertebral fracture',
                    'new morphometric vertebral fracture'],
        'subspecialty': 'fracture',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'NONVERTEBRAL_FRACTURE': {
        'aliases': ['non-vertebral fracture', 'nonvertebral fracture', 'non vertebral fracture'],
        'subspecialty': 'fracture',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HIP_FRACTURE': {
        'aliases': ['hip fracture', 'femoral neck fracture', 'proximal femur fracture'],
        'subspecialty': 'fracture',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CLINICAL_FRACTURE': {
        'aliases': ['clinical fracture', 'symptomatic fracture', 'major osteoporotic fracture',
                    'clinical osteoporotic fracture'],
        'subspecialty': 'fracture',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ANY_FRACTURE': {
        'aliases': ['any fracture', 'all fractures', 'fragility fracture', 'osteoporotic fracture',
                    'total fractures', 'incident fracture'],
        'subspecialty': 'fracture',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- bmd (continuous) ---
    'BMD_LUMBAR_SPINE': {
        'aliases': ['lumbar spine bone mineral density', 'lumbar spine bmd',
                    'spine bone mineral density', 'lumbar bmd',
                    'bone mineral density at the lumbar spine', 'change in lumbar spine bmd'],
        'subspecialty': 'bmd',
        'measure_types': ['MD', 'SMD']
    },
    'BMD_TOTAL_HIP': {
        'aliases': ['total hip bone mineral density', 'total hip bmd', 'hip bone mineral density',
                    'bone mineral density at the total hip', 'change in total hip bmd'],
        'subspecialty': 'bmd',
        'measure_types': ['MD', 'SMD']
    },
    'BMD_FEMORAL_NECK': {
        'aliases': ['femoral neck bone mineral density', 'femoral neck bmd',
                    'bone mineral density at the femoral neck'],
        'subspecialty': 'bmd',
        'measure_types': ['MD', 'SMD']
    },

    # --- bone_turnover (continuous) ---
    'CTX': {
        'aliases': ['serum ctx', 'c-telopeptide', 'ctx', 'beta-ctx', 's-ctx',
                    'carboxy-terminal collagen crosslinks', 'serum c-telopeptide'],
        'subspecialty': 'bone_turnover',
        'measure_types': ['MD', 'SMD']
    },
    'P1NP': {
        'aliases': ['p1np', 'pinp', 'procollagen type 1 n-propeptide',
                    'procollagen type i n-terminal propeptide', 'serum p1np'],
        'subspecialty': 'bone_turnover',
        'measure_types': ['MD', 'SMD']
    },

    # --- safety ---
    'OSTEONECROSIS_JAW': {
        'aliases': ['osteonecrosis of the jaw', 'osteonecrosis of jaw', 'onj',
                    'jaw osteonecrosis'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ATYPICAL_FEMORAL_FRACTURE': {
        'aliases': ['atypical femoral fracture', 'atypical femur fracture',
                    'atypical subtrochanteric fracture'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HYPOCALCEMIA': {
        'aliases': ['hypocalcaemia', 'hypocalcemia', 'low serum calcium'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# FRACTURE PATTERNS
# ============================================================

FRACTURE_PATTERNS = {
    'detection_keywords': [
        r'vertebral\s+fracture', r'non[- ]?vertebral\s+fracture', r'hip\s+fracture',
        r'fragility\s+fracture', r'osteoporotic\s+fracture', r'clinical\s+fracture',
        r'major\s+osteoporotic\s+fracture', r'incident\s+fracture',
    ],
    'endpoint_patterns': [
        (r'(?:new\s+|morphometric\s+|radiographic\s+|clinical\s+)?vertebral\s+fracture',
         'VERTEBRAL_FRACTURE'),
        (r'non[- ]?vertebral\s+fracture', 'NONVERTEBRAL_FRACTURE'),
        (r'hip\s+fracture|femoral\s+neck\s+fracture|proximal\s+femur\s+fracture', 'HIP_FRACTURE'),
        (r'(?:major\s+)?(?:clinical|symptomatic)\s+(?:osteoporotic\s+)?fracture|'
         r'major\s+osteoporotic\s+fracture', 'CLINICAL_FRACTURE'),
        (r'(?:any|all|total|incident|fragility|osteoporotic)\s+fractures?', 'ANY_FRACTURE'),
    ],
    'context_patterns': [
        r'hazard\s+ratio|\bhr\b', r'risk\s+reduction', r'over\s+\d+\s+(?:months|years)',
    ]
}


# ============================================================
# BMD PATTERNS (continuous)
# ============================================================

BMD_PATTERNS = {
    'detection_keywords': [
        r'bone\s+mineral\s+density|\bbmd\b', r'lumbar\s+spine', r'total\s+hip',
        r'femoral\s+neck', r't[- ]score', r'dual[- ]energy\s+x[- ]ray|\bdxa\b|\bdexa\b',
    ],
    'endpoint_patterns': [
        (r'(?:change\s+in\s+)?lumbar\s+spine\s+(?:bone\s+mineral\s+density|bmd)|'
         r'(?:bone\s+mineral\s+density|bmd)\s+at\s+the\s+lumbar\s+spine|lumbar\s+bmd',
         'BMD_LUMBAR_SPINE'),
        (r'(?:change\s+in\s+)?total\s+hip\s+(?:bone\s+mineral\s+density|bmd)|'
         r'(?:bone\s+mineral\s+density|bmd)\s+at\s+the\s+total\s+hip', 'BMD_TOTAL_HIP'),
        (r'femoral\s+neck\s+(?:bone\s+mineral\s+density|bmd)|'
         r'(?:bone\s+mineral\s+density|bmd)\s+at\s+the\s+femoral\s+neck', 'BMD_FEMORAL_NECK'),
    ],
    'context_patterns': [
        r'percent\s+change|percentage\s+change', r'g/cm', r'baseline\s+to\s+(?:month|year)',
    ]
}


# ============================================================
# BONE-TURNOVER PATTERNS (continuous)
# ============================================================

BONE_TURNOVER_PATTERNS = {
    'detection_keywords': [
        r'bone[- ]turnover\s+marker', r'\bctx\b|c[- ]telopeptide', r'\bp1np\b|\bpinp\b',
        r'procollagen', r'bone[- ]specific\s+alkaline\s+phosphatase',
    ],
    'endpoint_patterns': [
        (r'(?:serum\s+|beta[- ]|s[- ])?ctx|c[- ]telopeptide|carboxy[- ]terminal\s+collagen',
         'CTX'),
        (r'\bp1np\b|\bpinp\b|procollagen\s+type\s+(?:1|i)\s+n', 'P1NP'),
    ],
    'context_patterns': [
        r'percent\s+change', r'ng/ml|µg/l|ug/l', r'bone\s+formation|bone\s+resorption',
    ]
}


# ============================================================
# SAFETY PATTERNS
# ============================================================

SAFETY_PATTERNS = {
    'detection_keywords': [
        r'osteonecrosis\s+of\s+the\s+jaw|\bonj\b', r'atypical\s+fem(?:oral|ur)\s+fracture',
        r'hypocalca?emia', r'injection[- ]site\s+reaction', r'adverse\s+events',
    ],
    'endpoint_patterns': [
        (r'osteonecrosis\s+of\s+(?:the\s+)?jaw|\bonj\b|jaw\s+osteonecrosis', 'OSTEONECROSIS_JAW'),
        (r'atypical\s+(?:fem(?:oral|ur)|subtrochanteric)\s+fracture', 'ATYPICAL_FEMORAL_FRACTURE'),
        (r'hypocalca?emia|low\s+serum\s+calcium', 'HYPOCALCEMIA'),
    ],
    'context_patterns': [
        r'\bsafety\b', r'rare', r'per\s+10,?000\s+patient[- ]years',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_osteoporosis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect osteoporosis trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: fracture, bmd, bone_turnover, safety, general_osteoporosis."""
    text_lower = text.lower()
    scores = {'fracture': 0, 'bmd': 0, 'bone_turnover': 0, 'safety': 0}
    for kw in FRACTURE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['fracture'] += 1
    for kw in BMD_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['bmd'] += 1
    for kw in BONE_TURNOVER_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['bone_turnover'] += 1
    for kw in SAFETY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['safety'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_osteoporosis', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_osteoporosis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'fracture': FRACTURE_PATTERNS['endpoint_patterns'],
        'bmd': BMD_PATTERNS['endpoint_patterns'],
        'bone_turnover': BONE_TURNOVER_PATTERNS['endpoint_patterns'],
        'safety': SAFETY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_osteoporosis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical osteoporosis endpoint, preferring the LONGEST matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in OSTEOPOROSIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
