"""
Dermatology (inflammatory skin disease) Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the malaria / HIV / hepatitis /
respiratory / stroke / nephrology / rheumatology profiles. Dermatology RCTs report
an endpoint vocabulary anchored on standardised skin-severity responses (PASI75/90/
100, IGA/sPGA clear-or-almost-clear, EASI75/90, vIGA-AD, SCORAD, itch NRS, acne IGA
success, lesion counts, HiSCR) that the generic effect-size engine does not
recognise on its own.

Subspecialties:
- psoriasis (plaque psoriasis, skin):
    PASI75 / PASI90 / PASI100 (>=75/90/100% improvement in Psoriasis Area and
    Severity Index; RR/OR), IGA response (sPGA/IGA 0 or 1, clear-or-almost-clear;
    RR/OR), PASI change (MD).
- atopic_dermatitis (eczema):
    EASI75 / EASI90 (>=75/90% improvement in Eczema Area and Severity Index;
    RR/OR), vIGA-AD response (vIGA-AD 0/1; RR/OR), pruritus NRS (>=4-point itch
    NRS improvement; RR/OR), EASI change (MD), SCORAD (MD).
- acne (acne vulgaris):
    acne IGA success (clear-almost-clear / 2-grade improvement; RR/OR),
    inflammatory / total lesion-count reduction (MD / percent).
- hidradenitis (hidradenitis suppurativa):
    HiSCR -- Hidradenitis Suppurativa Clinical Response (RR/OR).

Effect measures follow what these trials report: binary composite responses
(PASI75/90/100, IGA, EASI75/90, vIGA-AD, pruritus-NRS responder, acne IGA success,
HiSCR) -> RR/OR/RD; continuous severity indices (PASI change, EASI change, SCORAD,
lesion count) -> MD/SMD. The dermatology continuous scales are bounded clinical
severity indices / counts, not right-skewed log-normal biomarkers, so NO log-scale
pooling is needed (the LOG-NORMAL set is empty).

Routing note (coordinated with rheumatology): dermatology claims SKIN disease only
-- (plaque) psoriasis, PASI, atopic dermatitis / eczema, EASI, SCORAD, acne
(vulgaris), hidradenitis suppurativa, HiSCR, IGA, vIGA. We deliberately do NOT
claim 'psoriatic arthritis' or bare 'ACR' (those belong to rheumatology). Plain
plaque psoriasis (skin) is ours; psoriatic ARTHRITIS is rheumatology's. The
keyword anchors are 'psoriasis' / 'plaque psoriasis' (the stem 'psorias-' does NOT
match the distinct stem 'psoriatic'), so a psoriatic-arthritis / ACR20 trial never
out-scores rheumatology.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# DERMATOLOGY ENDPOINTS
# ============================================================

DERMATOLOGY_ENDPOINTS = {
    # --- Psoriasis (plaque psoriasis, skin) ---
    'PASI75': {
        'aliases': ['pasi75', 'pasi 75', 'pasi-75', 'pasi 75 response',
                    '75% improvement in pasi', '75% reduction in pasi',
                    '>=75% improvement in psoriasis area and severity index',
                    'psoriasis area and severity index 75'],
        'subspecialty': 'psoriasis',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PASI90': {
        'aliases': ['pasi90', 'pasi 90', 'pasi-90', 'pasi 90 response',
                    '90% improvement in pasi', '90% reduction in pasi',
                    '>=90% improvement in psoriasis area and severity index',
                    'psoriasis area and severity index 90'],
        'subspecialty': 'psoriasis',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PASI100': {
        'aliases': ['pasi100', 'pasi 100', 'pasi-100', 'pasi 100 response',
                    '100% improvement in pasi', 'complete skin clearance',
                    '100% improvement in psoriasis area and severity index',
                    'psoriasis area and severity index 100'],
        'subspecialty': 'psoriasis',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'IGA_RESPONSE': {
        'aliases': ['iga response', 'iga 0 or 1', 'iga 0/1', 'spga 0 or 1',
                    'spga 0/1', 'physician global assessment 0 or 1',
                    "investigator's global assessment 0 or 1",
                    'static physician global assessment', 'iga clear or almost clear',
                    'clear or almost clear', 'iga of clear or almost clear',
                    'pga 0 or 1'],
        'subspecialty': 'psoriasis',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PASI_CHANGE': {
        'aliases': ['pasi change', 'change in pasi', 'mean change in pasi',
                    'change from baseline in pasi', 'pasi score change',
                    'absolute pasi', 'change in psoriasis area and severity index',
                    'reduction in pasi score'],
        'subspecialty': 'psoriasis',
        'measure_types': ['MD', 'SMD']
    },

    # --- Atopic dermatitis (eczema) ---
    'EASI75': {
        'aliases': ['easi75', 'easi 75', 'easi-75', 'easi 75 response',
                    '75% improvement in easi', '75% reduction in easi',
                    '>=75% improvement in eczema area and severity index',
                    'eczema area and severity index 75'],
        'subspecialty': 'atopic_dermatitis',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'EASI90': {
        'aliases': ['easi90', 'easi 90', 'easi-90', 'easi 90 response',
                    '90% improvement in easi', '90% reduction in easi',
                    '>=90% improvement in eczema area and severity index',
                    'eczema area and severity index 90'],
        'subspecialty': 'atopic_dermatitis',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'IGA_AD_RESPONSE': {
        'aliases': ['viga-ad', 'viga ad', 'viga-ad 0/1', 'viga-ad 0 or 1',
                    'validated investigator global assessment for atopic dermatitis',
                    'iga-ad 0/1', 'iga-ad 0 or 1', 'iga ad response',
                    'viga-ad response', 'viga-ad of 0 or 1'],
        'subspecialty': 'atopic_dermatitis',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PRURITUS_NRS': {
        'aliases': ['pruritus nrs', 'itch nrs', 'peak pruritus nrs',
                    'numerical rating scale for itch', 'numeric rating scale for itch',
                    '4-point improvement in pruritus', '>=4-point improvement in pruritus',
                    '4-point itch improvement', 'pruritus numerical rating scale',
                    'itch numerical rating scale', 'peak pruritus numerical rating scale'],
        'subspecialty': 'atopic_dermatitis',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'EASI_CHANGE': {
        'aliases': ['easi change', 'change in easi', 'mean change in easi',
                    'change from baseline in easi', 'easi score change',
                    'change in eczema area and severity index',
                    'percent change in easi', 'reduction in easi score'],
        'subspecialty': 'atopic_dermatitis',
        'measure_types': ['MD', 'SMD']
    },
    'SCORAD': {
        'aliases': ['scorad', 'scoring atopic dermatitis', 'scorad index',
                    'change in scorad', 'scorad change', 'scorad score',
                    'objective scorad', 'mean scorad'],
        'subspecialty': 'atopic_dermatitis',
        'measure_types': ['MD', 'SMD']
    },

    # --- Acne (acne vulgaris) ---
    'IGA_ACNE_SUCCESS': {
        'aliases': ['iga acne success', 'acne iga success', 'iga success',
                    'investigator global assessment success', 'iga treatment success',
                    'clear or almost clear and at least 2-grade improvement',
                    'acne global assessment success', '2-grade improvement in iga',
                    'two-grade improvement in iga'],
        'subspecialty': 'acne',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'LESION_COUNT': {
        'aliases': ['inflammatory lesion count', 'total lesion count',
                    'noninflammatory lesion count', 'non-inflammatory lesion count',
                    'lesion count reduction', 'reduction in inflammatory lesions',
                    'reduction in total lesions', 'percent change in lesion count',
                    'change in lesion count', 'absolute lesion count change'],
        'subspecialty': 'acne',
        'measure_types': ['MD', 'SMD', 'percent']
    },

    # --- Hidradenitis suppurativa ---
    'HISCR': {
        'aliases': ['hiscr', 'hi-scr', 'hidradenitis suppurativa clinical response',
                    'hs clinical response', 'hiscr response', 'hiscr50',
                    'hiscr achievement'],
        'subspecialty': 'hidradenitis',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# PSORIASIS PATTERNS (plaque psoriasis, skin)
# ============================================================

PSORIASIS_PATTERNS = {
    'detection_keywords': [
        # 'plaque psoriasis' / 'psoriasis' (SKIN). The 'psorias-' stem does NOT
        # match 'psoriatic' (arthritis) -- that belongs to rheumatology.
        r'plaque\s+psoriasis', r'\bpsoriasis\b', r'psoriasis\s+vulgaris',
        r'\bpasi\b', r'psoriasis\s+area\s+and\s+severity\s+index',
        r'body\s+surface\s+area\s+(?:affected|involved)',
        r'\bspga\b|static\s+physician\s+global\s+assessment',
    ],
    'endpoint_patterns': [
        # Most-specific (PASI100/90/75) BEFORE the generic IGA so the numeric
        # PASI threshold wins when present.
        (r'pasi\s*-?\s*100|100%\s+(?:improvement|reduction)\s+in\s+pasi|'
         r'complete\s+skin\s+clearance', 'PASI100'),
        (r'pasi\s*-?\s*90|90%\s+(?:improvement|reduction)\s+in\s+pasi', 'PASI90'),
        (r'pasi\s*-?\s*75|75%\s+(?:improvement|reduction)\s+in\s+pasi', 'PASI75'),
        (r'change\s+(?:from\s+baseline\s+)?in\s+pasi|pasi\s+(?:score\s+)?change|'
         r'mean\s+change\s+in\s+pasi|absolute\s+pasi|reduction\s+in\s+pasi\s+score',
         'PASI_CHANGE'),
        (r'(?:s?pga|iga|physician\s+global\s+assessment|'
         r"investigator'?s?\s+global\s+assessment)\s*(?:score\s*)?'?\s*'?"
         r'(?:of\s+)?0\s*(?:or|/|,)\s*1|clear\s+or\s+almost\s+clear|'
         r'clear[- ]or[- ]almost[- ]clear', 'IGA_RESPONSE'),
    ],
    'context_patterns': [
        r'at\s+week\s+(?:12|16|24)', r'moderate[- ]to[- ]severe\s+(?:plaque\s+)?psoriasis',
        r'baseline\s+pasi',
    ]
}


# ============================================================
# ATOPIC DERMATITIS PATTERNS (eczema)
# ============================================================

ATOPIC_DERMATITIS_PATTERNS = {
    'detection_keywords': [
        r'atopic\s+dermatitis', r'\beczema\b', r'atopic\s+eczema',
        r'\beasi\b', r'eczema\s+area\s+and\s+severity\s+index',
        r'\bscorad\b', r'scoring\s+atopic\s+dermatitis',
        r'viga[- ]ad|validated\s+investigator\s+global\s+assessment',
        r'pruritus\s+nrs|itch\s+nrs|peak\s+pruritus',
    ],
    'endpoint_patterns': [
        (r'easi\s*-?\s*90|90%\s+(?:improvement|reduction)\s+in\s+easi', 'EASI90'),
        (r'easi\s*-?\s*75|75%\s+(?:improvement|reduction)\s+in\s+easi', 'EASI75'),
        (r'viga[- ]ad(?:\s*(?:score\s*)?(?:of\s+)?0\s*(?:or|/|,)\s*1)?|'
         r'validated\s+investigator\s+global\s+assessment\s+for\s+atopic\s+dermatitis|'
         r'iga[- ]ad\s+(?:0\s*(?:or|/)\s*1|response)', 'IGA_AD_RESPONSE'),
        (r'(?:peak\s+)?pruritus\s+nrs|itch\s+nrs|'
         r'(?:>=?\s*)?4[- ]point\s+improvement\s+in\s+pruritus|'
         r'(?:peak\s+)?pruritus\s+numerical\s+rating\s+scale|'
         r'itch\s+numerical\s+rating\s+scale', 'PRURITUS_NRS'),
        (r'change\s+(?:from\s+baseline\s+)?in\s+easi|easi\s+(?:score\s+)?change|'
         r'mean\s+change\s+in\s+easi|percent\s+change\s+in\s+easi|'
         r'reduction\s+in\s+easi\s+score', 'EASI_CHANGE'),
        (r'\bscorad\b|scoring\s+atopic\s+dermatitis|objective\s+scorad', 'SCORAD'),
    ],
    'context_patterns': [
        r'at\s+week\s+16', r'moderate[- ]to[- ]severe\s+atopic\s+dermatitis',
        r'baseline\s+easi',
    ]
}


# ============================================================
# ACNE PATTERNS (acne vulgaris)
# ============================================================

ACNE_PATTERNS = {
    'detection_keywords': [
        r'acne\s+vulgaris', r'\bacne\b', r'inflammatory\s+(?:acne\s+)?lesions?',
        r'(?:non[- ]?)?inflammatory\s+lesion\s+count',
        r'comedon\w+', r'acne\s+(?:iga|global\s+assessment)',
    ],
    'endpoint_patterns': [
        (r'(?:acne\s+)?iga\s+success|iga\s+treatment\s+success|'
         r'investigator\s+global\s+assessment\s+success|'
         r'(?:two|2)[- ]grade\s+improvement\s+in\s+iga|'
         r'acne\s+global\s+assessment\s+success', 'IGA_ACNE_SUCCESS'),
        (r'(?:non[- ]?)?inflammatory\s+lesion\s+count|total\s+lesion\s+count|'
         r'lesion\s+count\s+reduction|reduction\s+in\s+(?:inflammatory|total)\s+lesions|'
         r'(?:percent\s+|absolute\s+)?change\s+in\s+lesion\s+count', 'LESION_COUNT'),
    ],
    'context_patterns': [
        r'at\s+week\s+12', r'facial\s+acne', r'baseline\s+lesion\s+count',
    ]
}


# ============================================================
# HIDRADENITIS PATTERNS (hidradenitis suppurativa)
# ============================================================

HIDRADENITIS_PATTERNS = {
    'detection_keywords': [
        r'hidradenitis\s+suppurativa', r'\bhiscr\b|hi-scr',
        r'hurley\s+stage', r'abscess\s+and\s+inflammatory\s+nodule',
        r'\bhs\b\s+clinical\s+response',
    ],
    'endpoint_patterns': [
        (r'\bhi-?scr\b|hidradenitis\s+suppurativa\s+clinical\s+response|'
         r'hs\s+clinical\s+response|hiscr\s*-?\s*50', 'HISCR'),
    ],
    'context_patterns': [
        r'at\s+week\s+(?:12|16)', r'moderate[- ]to[- ]severe\s+hidradenitis',
        r'abscess.{0,20}nodule\s+count',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_dermatology_subspecialty(text: str) -> Tuple[str, float]:
    """Detect dermatology trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: psoriasis, atopic_dermatitis, acne, hidradenitis."""
    text_lower = text.lower()
    scores = {'psoriasis': 0, 'atopic_dermatitis': 0, 'acne': 0, 'hidradenitis': 0}
    for kw in PSORIASIS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['psoriasis'] += 1
    for kw in ATOPIC_DERMATITIS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['atopic_dermatitis'] += 1
    for kw in ACNE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['acne'] += 1
    for kw in HIDRADENITIS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['hidradenitis'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('psoriasis', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_dermatology_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'psoriasis': PSORIASIS_PATTERNS['endpoint_patterns'],
        'atopic_dermatitis': ATOPIC_DERMATITIS_PATTERNS['endpoint_patterns'],
        'acne': ACNE_PATTERNS['endpoint_patterns'],
        'hidradenitis': HIDRADENITIS_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_dermatology_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical dermatology endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in DERMATOLOGY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
