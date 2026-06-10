"""
Rheumatology (inflammatory arthritis / connective-tissue disease) Subspecialty
Patterns and Endpoints.

Built for the same meta-analysis workflow as the malaria / HIV / hepatitis /
respiratory / stroke profiles. Rheumatology RCTs report an endpoint vocabulary
anchored on standardised composite responses and disease-activity indices (ACR
response, DAS28, HAQ-DI, modified total Sharp score, ASAS, BASDAI, ASDAS, SRI-4,
BICLA, SLEDAI, serum urate target) that the generic effect-size engine does not
recognise on its own. This module SUPERSEDES the thin generic `autoimmune`
bucket (ACR20/ACR50/ACR70/PASI90/SRI) with a full subspecialty implementation.

Subspecialties:
- ra (rheumatoid arthritis):
    ACR20 / ACR50 / ACR70 response (RR/OR), DAS28 remission (DAS28<2.6; RR/OR),
    DAS28 change (MD), HAQ-DI change (MD), radiographic progression (modified
    total Sharp score / mTSS; MD).
- psa (psoriatic arthritis):
    ACR20 in PsA (reuses the ACR20 canonical), minimal disease activity (MDA;
    RR/OR), PASI response (PASI75/90 in PsA skin; RR/OR).
- axspa (axial spondyloarthritis / ankylosing spondylitis):
    ASAS20 / ASAS40 (RR/OR), BASDAI change (MD), ASDAS change (MD).
- gout:
    gout flare rate (IRR/RR), serum-urate target attainment (<6 mg/dL; RR/OR),
    serum urate level (MD).
- sle (systemic lupus erythematosus):
    SLE Responder Index-4 (SRI-4; RR/OR), BICLA (RR/OR), SLE flare (HR/RR),
    SLEDAI change (MD).

Effect measures follow what these trials report: binary composite responses
(ACR, DAS28 remission, MDA, PASI, ASAS, urate target, SRI-4, BICLA) -> RR/OR/RD;
flare / time-to-event (gout flare, SLE flare) -> IRR/HR/RR; continuous indices
(DAS28, HAQ-DI, mTSS, BASDAI, ASDAS, SLEDAI, serum urate) -> MD/SMD. The
rheumatology continuous scales are bounded clinical indices, not log-normal, so
no log-scale pooling is needed (CRP would be log-normal but is not an endpoint
here).

Routing note (coordinated with future dermatology + gastroenterology):
- We deliberately do NOT claim bare 'psoriasis' / 'plaque psoriasis' (those route
  to a future dermatology specialty); rheumatology only claims 'psoriatic
  arthritis'. PASI here is the SKIN sub-response WITHIN a PsA arthritis trial.
- We deliberately do NOT claim bare 'inflammatory bowel disease' / 'crohn' /
  'colitis' (those route to gastroenterology), even though some IL-17/IL-23/JAKi
  drugs overlap. Rheumatology anchors on arthritis/spondyloarthritis/lupus/gout
  terms (rheumatoid arthritis, psoriatic arthritis, ankylosing spondylitis,
  axial spondyloarthritis, systemic lupus erythematosus, gout, ACR20/50/70,
  DAS28, ASAS, BASDAI, SLEDAI, serum urate, DMARD).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# RHEUMATOLOGY ENDPOINTS
# ============================================================

RHEUMATOLOGY_ENDPOINTS = {
    # --- Rheumatoid arthritis (ra) ---
    # ACR20/50/70 are shared by RA and PsA; the canonical ACR20 also serves PsA
    # (ACR20_PSA reuses ACR20 per spec).
    'ACR20': {
        'aliases': ['acr20', 'acr 20', 'acr20 response', 'acr-20',
                    'american college of rheumatology 20', '20% improvement in acr',
                    'acr20 response rate'],
        'subspecialty': 'ra',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ACR50': {
        'aliases': ['acr50', 'acr 50', 'acr50 response', 'acr-50',
                    'american college of rheumatology 50', '50% improvement in acr'],
        'subspecialty': 'ra',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ACR70': {
        'aliases': ['acr70', 'acr 70', 'acr70 response', 'acr-70',
                    'american college of rheumatology 70', '70% improvement in acr'],
        'subspecialty': 'ra',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'DAS28_REMISSION': {
        'aliases': ['das28 remission', 'das28 < 2.6', 'das28<2.6', 'das28-crp remission',
                    'das28-esr remission', 'disease activity score remission',
                    'das28 below 2.6', 'clinical remission das28', 'remission das28'],
        'subspecialty': 'ra',
        'measure_types': ['RR', 'OR']
    },
    'DAS28_CHANGE': {
        'aliases': ['change in das28', 'das28 change', 'das28 reduction',
                    'change from baseline in das28', 'mean change in das28',
                    'das28-crp change', 'das28-esr change', 'reduction in das28'],
        'subspecialty': 'ra',
        'measure_types': ['MD', 'SMD']
    },
    'HAQ_DI': {
        'aliases': ['haq-di', 'haq di', 'health assessment questionnaire disability index',
                    'haq disability index', 'change in haq-di', 'haq-di change',
                    'change from baseline in haq', 'haq score', 'haq-di score'],
        'subspecialty': 'ra',
        'measure_types': ['MD', 'SMD']
    },
    'RADIOGRAPHIC_PROGRESSION': {
        'aliases': ['radiographic progression', 'modified total sharp score',
                    'modified sharp score', 'mtss', 'total sharp score',
                    'van der heijde modified total sharp score', 'sharp score',
                    'change in modified total sharp score', 'structural progression'],
        'subspecialty': 'ra',
        'measure_types': ['MD', 'SMD']
    },

    # --- Psoriatic arthritis (psa) ---
    'MDA': {
        'aliases': ['minimal disease activity', 'mda', 'minimal disease activity response',
                    'achievement of minimal disease activity', 'very low disease activity',
                    'vlda'],
        'subspecialty': 'psa',
        'measure_types': ['RR', 'OR']
    },
    'PASI_RESPONSE': {
        'aliases': ['pasi response', 'pasi75', 'pasi 75', 'pasi90', 'pasi 90',
                    'pasi 100', 'pasi100', '75% improvement in pasi', '90% improvement in pasi',
                    'psoriasis area and severity index response', 'pasi-75', 'pasi-90'],
        'subspecialty': 'psa',
        'measure_types': ['RR', 'OR']
    },

    # --- Axial spondyloarthritis / ankylosing spondylitis (axspa) ---
    'ASAS20': {
        'aliases': ['asas20', 'asas 20', 'asas20 response', 'asas-20',
                    'assessment of spondyloarthritis 20', '20% asas response',
                    'asas20 improvement'],
        'subspecialty': 'axspa',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ASAS40': {
        'aliases': ['asas40', 'asas 40', 'asas40 response', 'asas-40',
                    'assessment of spondyloarthritis 40', '40% asas response',
                    'asas40 improvement'],
        'subspecialty': 'axspa',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BASDAI_CHANGE': {
        'aliases': ['change in basdai', 'basdai change', 'basdai reduction',
                    'bath ankylosing spondylitis disease activity index change',
                    'change from baseline in basdai', 'basdai50', 'basdai 50',
                    'mean change in basdai'],
        'subspecialty': 'axspa',
        'measure_types': ['MD', 'SMD']
    },
    'ASDAS_CHANGE': {
        'aliases': ['change in asdas', 'asdas change', 'asdas reduction',
                    'ankylosing spondylitis disease activity score change',
                    'change from baseline in asdas', 'asdas-crp change',
                    'mean change in asdas'],
        'subspecialty': 'axspa',
        'measure_types': ['MD', 'SMD']
    },

    # --- Gout ---
    'GOUT_FLARE': {
        'aliases': ['gout flare', 'gout flares', 'flare rate', 'acute gout flare',
                    'number of gout flares', 'gout flare rate', 'incidence of gout flares',
                    'flare incidence'],
        'subspecialty': 'gout',
        'measure_types': ['IRR', 'RR', 'OR']
    },
    'URATE_TARGET': {
        'aliases': ['urate target', 'serum urate < 6', 'serum urate <6 mg/dl',
                    'serum urate below 6', 'urate target attainment',
                    'achievement of target serum urate', 'sua < 6 mg/dl',
                    'target serum urate', 'serum urate target'],
        'subspecialty': 'gout',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SERUM_URATE': {
        'aliases': ['serum urate level', 'change in serum urate', 'serum uric acid',
                    'mean serum urate', 'serum urate reduction', 'change in serum uric acid',
                    'serum urate concentration'],
        'subspecialty': 'gout',
        'measure_types': ['MD', 'SMD']
    },

    # --- Systemic lupus erythematosus (sle) ---
    'SRI4': {
        'aliases': ['sri-4', 'sri4', 'sri 4', 'sle responder index-4', 'sle responder index 4',
                    'systemic lupus erythematosus responder index-4', 'sri-4 response',
                    'sri(4)', 'sle responder index'],
        'subspecialty': 'sle',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BICLA': {
        'aliases': ['bicla', 'bicla response', 'bila-based composite lupus assessment',
                    'bila-based combined lupus assessment',
                    'british isles lupus assessment group-based composite lupus assessment'],
        'subspecialty': 'sle',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SLE_FLARE': {
        'aliases': ['sle flare', 'lupus flare', 'severe flare', 'flare of lupus',
                    'time to first flare', 'time to severe flare', 'sfi flare',
                    'bilag flare', 'renal flare'],
        'subspecialty': 'sle',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'SLEDAI_CHANGE': {
        'aliases': ['change in sledai', 'sledai change', 'sledai reduction',
                    'sledai-2k change', 'systemic lupus erythematosus disease activity index change',
                    'change from baseline in sledai', 'mean change in sledai'],
        'subspecialty': 'sle',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# RHEUMATOID ARTHRITIS PATTERNS (ra)
# ============================================================

RA_PATTERNS = {
    'detection_keywords': [
        r'rheumatoid\s+arthritis|\bra\b',
        r'\bacr\s?(?:20|50|70)\b|acr[- ]?(?:20|50|70)',
        r'\bdas28\b|disease\s+activity\s+score',
        r'\bhaq[- ]?di\b|health\s+assessment\s+questionnaire',
        r'modified\s+(?:total\s+)?sharp\s+score|\bmtss\b',
        r'methotrexate|\bcsdmard\b|conventional\s+synthetic\s+dmard',
        r'\btnf\s*(?:inhibitor|i)\b|\bjak\s*(?:inhibitor|i)\b',
    ],
    'endpoint_patterns': [
        (r'\bacr\s?70\b|acr[- ]?70|70%\s+improvement\s+in\s+acr', 'ACR70'),
        (r'\bacr\s?50\b|acr[- ]?50|50%\s+improvement\s+in\s+acr', 'ACR50'),
        (r'\bacr\s?20\b|acr[- ]?20|20%\s+improvement\s+in\s+acr', 'ACR20'),
        (r'das28\s+remission|das28\s*(?:-(?:crp|esr))?\s*(?:<|below|less\s+than)\s*2\.6|'
         r'remission\s+das28|clinical\s+remission\s+das28', 'DAS28_REMISSION'),
        (r'change\s+(?:from\s+baseline\s+)?in\s+das28|das28\s+(?:change|reduction)|'
         r'reduction\s+in\s+das28|mean\s+change\s+in\s+das28', 'DAS28_CHANGE'),
        (r'\bhaq[- ]?di\b|health\s+assessment\s+questionnaire\s+disability|'
         r'change\s+(?:from\s+baseline\s+)?in\s+haq|haq\s+score', 'HAQ_DI'),
        (r'radiographic\s+progression|modified\s+(?:total\s+)?sharp\s+score|\bmtss\b|'
         r'total\s+sharp\s+score|structural\s+progression', 'RADIOGRAPHIC_PROGRESSION'),
    ],
    'context_patterns': [
        r'week\s+(?:12|24|52)', r'methotrexate[- ]naive|methotrexate[- ]experienced',
        r'inadequate\s+response', r'csdmard',
    ]
}


# ============================================================
# PSORIATIC ARTHRITIS PATTERNS (psa)
# ============================================================

PSA_PATTERNS = {
    'detection_keywords': [
        r'psoriatic\s+arthritis|\bpsa\b',
        r'minimal\s+disease\s+activity|\bmda\b',
        r'enthesitis|dactylitis',
        r'\bacr\s?(?:20|50|70)\b',
        r'\bpasi\s?(?:75|90|100)\b',
    ],
    'endpoint_patterns': [
        (r'minimal\s+disease\s+activity|\bmda\b|very\s+low\s+disease\s+activity|\bvlda\b',
         'MDA'),
        (r'pasi\s?(?:75|90|100)|pasi[- ](?:75|90|100)|(?:75|90)%\s+improvement\s+in\s+pasi|'
         r'pasi\s+response|psoriasis\s+area\s+and\s+severity\s+index\s+response', 'PASI_RESPONSE'),
        # ACR responses reused in PsA (longest/most-specific first)
        (r'\bacr\s?70\b|acr[- ]?70', 'ACR70'),
        (r'\bacr\s?50\b|acr[- ]?50', 'ACR50'),
        (r'\bacr\s?20\b|acr[- ]?20', 'ACR20'),
    ],
    'context_patterns': [
        r'week\s+(?:16|24)', r'skin\s+response', r'tnf[- ]?naive',
    ]
}


# ============================================================
# AXIAL SPONDYLOARTHRITIS PATTERNS (axspa)
# ============================================================

AXSPA_PATTERNS = {
    'detection_keywords': [
        r'axial\s+spondyloarthritis|ankylosing\s+spondylitis|\baxspa\b|\bas\b',
        r'spondyloarthritis|\bnr[- ]?axspa\b|non[- ]radiographic',
        r'\basas\s?(?:20|40)\b|asas[- ]?(?:20|40)',
        r'\bbasdai\b|bath\s+ankylosing\s+spondylitis',
        r'\basdas\b|ankylosing\s+spondylitis\s+disease\s+activity\s+score',
    ],
    'endpoint_patterns': [
        (r'\basas\s?40\b|asas[- ]?40|40%\s+asas|assessment\s+of\s+spondyloarthritis\s+40',
         'ASAS40'),
        (r'\basas\s?20\b|asas[- ]?20|20%\s+asas|assessment\s+of\s+spondyloarthritis\s+20',
         'ASAS20'),
        (r'change\s+(?:from\s+baseline\s+)?in\s+basdai|basdai\s+(?:change|reduction)|'
         r'\bbasdai\s?50\b|bath\s+ankylosing\s+spondylitis\s+disease\s+activity\s+index\s+change',
         'BASDAI_CHANGE'),
        (r'change\s+(?:from\s+baseline\s+)?in\s+asdas|asdas\s+(?:change|reduction)|'
         r'asdas[- ]?crp\s+change|ankylosing\s+spondylitis\s+disease\s+activity\s+score\s+change',
         'ASDAS_CHANGE'),
    ],
    'context_patterns': [
        r'week\s+(?:12|16)', r'hla[- ]?b27', r'sacroiliitis', r'mri\s+inflammation',
    ]
}


# ============================================================
# GOUT PATTERNS
# ============================================================

GOUT_PATTERNS = {
    'detection_keywords': [
        r'\bgout\b|gouty\s+arthritis', r'hyperuric[ae]?mia',
        r'serum\s+urate|serum\s+uric\s+acid|\bsua\b',
        r'urate[- ]lowering(?:\s+therapy)?|\bult\b',
        r'allopurinol|febuxostat|pegloticase|colchicine',
        r'tophus|tophi|tophaceous',
    ],
    'endpoint_patterns': [
        (r'gout\s+flares?|flare\s+rate|acute\s+gout\s+flare|number\s+of\s+gout\s+flares|'
         r'incidence\s+of\s+gout\s+flares|flare\s+incidence', 'GOUT_FLARE'),
        (r'serum\s+urate\s*(?:<|below|less\s+than)\s*6|urate\s+target|'
         r'target\s+serum\s+urate|achievement\s+of\s+target\s+serum\s+urate|'
         r'\bsua\s*(?:<|below)\s*6', 'URATE_TARGET'),
        (r'serum\s+urate\s+(?:level|reduction|concentration)|change\s+in\s+serum\s+urate|'
         r'serum\s+uric\s+acid\s+level|mean\s+serum\s+urate|change\s+in\s+serum\s+uric\s+acid',
         'SERUM_URATE'),
    ],
    'context_patterns': [
        r'\bmg/dl\b', r'week\s+(?:24|52)', r'prophylaxis', r'\bumol/l\b',
    ]
}


# ============================================================
# SYSTEMIC LUPUS ERYTHEMATOSUS PATTERNS (sle)
# ============================================================

SLE_PATTERNS = {
    'detection_keywords': [
        r'systemic\s+lupus\s+erythematosus|\bsle\b|\blupus\b',
        r'\bsri[- ]?4\b|sle\s+responder\s+index',
        r'\bbicla\b|bila[- ]based\s+composite',
        r'\bsledai\b|systemic\s+lupus\s+erythematosus\s+disease\s+activity\s+index',
        r'\bbilag\b|lupus\s+nephritis',
        r'belimumab|anifrolumab',
    ],
    'endpoint_patterns': [
        (r'\bsri[- ]?4\b|sri\s?4\b|sle\s+responder\s+index[- ]?4|'
         r'systemic\s+lupus\s+erythematosus\s+responder\s+index[- ]?4|sle\s+responder\s+index',
         'SRI4'),
        (r'\bbicla\b|bila[- ]based\s+(?:composite|combined)\s+lupus\s+assessment|'
         r'british\s+isles\s+lupus\s+assessment\s+group[- ]based', 'BICLA'),
        (r'(?:sle|lupus|severe|renal|bilag)\s+flare|flare\s+of\s+lupus|'
         r'time\s+to\s+(?:first\s+|severe\s+)?flare', 'SLE_FLARE'),
        (r'change\s+(?:from\s+baseline\s+)?in\s+sledai|sledai(?:-2k)?\s+(?:change|reduction)|'
         r'systemic\s+lupus\s+erythematosus\s+disease\s+activity\s+index\s+change', 'SLEDAI_CHANGE'),
    ],
    'context_patterns': [
        r'week\s+(?:24|52)', r'glucocorticoid\s+(?:taper|reduction)', r'anti[- ]dsdna',
        r'complement', r'standard\s+(?:of\s+)?care',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_rheumatology_subspecialty(text: str) -> Tuple[str, float]:
    """Detect rheumatology trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: ra, psa, axspa, gout, sle."""
    text_lower = text.lower()
    scores = {'ra': 0, 'psa': 0, 'axspa': 0, 'gout': 0, 'sle': 0}
    for kw in RA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['ra'] += 1
    for kw in PSA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['psa'] += 1
    for kw in AXSPA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['axspa'] += 1
    for kw in GOUT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['gout'] += 1
    for kw in SLE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['sle'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('ra', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_rheumatology_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'ra': RA_PATTERNS['endpoint_patterns'],
        'psa': PSA_PATTERNS['endpoint_patterns'],
        'axspa': AXSPA_PATTERNS['endpoint_patterns'],
        'gout': GOUT_PATTERNS['endpoint_patterns'],
        'sle': SLE_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_rheumatology_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical rheumatology endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in RHEUMATOLOGY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
