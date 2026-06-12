"""
Allergic conjunctivitis (ocular allergy) Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the ophthalmology / allergic_rhinitis
profiles, but for OCULAR-ALLERGY trials specifically -- a domain neither the
generic ophthalmology profile (AMD / DME / glaucoma / dry eye) nor the
allergic_rhinitis profile (nasal symptoms, TNSS, immunotherapy) targets. Allergic
conjunctivitis RCTs report an endpoint vocabulary anchored on ocular itching,
conjunctival hypera?emia (redness), tearing/lacrimation, chemosis (conjunctival
o?edema), eyelid swelling and composite ocular symptom scores, frequently in a
conjunctival allergen challenge (CAC) model.

Subspecialties:
- seasonal_perennial (SAC / PAC):
    ocular itching (MD; primary), conjunctival hypera?emia / redness (MD),
    tearing (MD), composite ocular symptom relief / responder (RR/OR).
- vernal_atopic (VKC / AKC):
    corneal involvement / keratopathy (RR/OR), ocular itching (MD), plus the
    shared redness / tearing measures.
- challenge_model (conjunctival allergen challenge, CAC):
    onset ocular itching score (MD), conjunctival hypera?emia (MD) at fixed
    post-challenge time points.

Effect measures: binary (composite symptom responder, corneal involvement) ->
RR/OR/RD; continuous (ocular itching, hypera?emia, tearing, chemosis, eyelid
swelling, total ocular symptom score) -> MD/SMD. None is treated as log-normal
(all the ocular symptom scales are bounded and pooled on the raw scale).

British/American spelling: conjunctival HYPERAEMIA vs HYPEREMIA (the British form
inserts an extra 'a' -> 'hypera?emia', NOT '[ae]'); chemosis is a conjunctival
EDEMA vs OEDEMA ('o?edema'); 'lacrimation'. All handled in the patterns below.

Routing note: this profile claims the specific ocular-allergy anchors (allergic
conjunctivitis, ocular allergy, conjunctival allergen challenge, ocular itching,
vernal/atopic keratoconjunctivitis, ocular antihistamine drops) that neither the
ophthalmology nor allergic_rhinitis profile claims.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# ALLERGIC CONJUNCTIVITIS ENDPOINTS
# ============================================================

ALLERGIC_CONJUNCTIVITIS_ENDPOINTS = {
    'OCULAR_ITCHING': {
        'aliases': ['ocular itching', 'ocular itch', 'eye itching', 'itching score',
                    'ocular itching score', 'conjunctival itching', 'itch score',
                    'mean ocular itching', 'change in ocular itching'],
        'subspecialty': 'seasonal_perennial',
        'measure_types': ['MD', 'SMD']
    },
    'CONJUNCTIVAL_HYPERAEMIA': {
        'aliases': ['conjunctival hyperaemia', 'conjunctival hyperemia',
                    'conjunctival redness', 'ocular redness', 'ocular hyperaemia',
                    'ocular hyperemia', 'bulbar hyperaemia', 'bulbar hyperemia',
                    'conjunctival injection', 'redness score'],
        'subspecialty': 'seasonal_perennial',
        'measure_types': ['MD', 'SMD']
    },
    'TEARING': {
        'aliases': ['tearing', 'lacrimation', 'tearing score', 'watering eyes',
                    'epiphora', 'ocular tearing', 'mean tearing score'],
        'subspecialty': 'seasonal_perennial',
        'measure_types': ['MD', 'SMD']
    },
    'CHEMOSIS': {
        'aliases': ['chemosis', 'conjunctival edema', 'conjunctival oedema',
                    'conjunctival o?edema', 'chemosis score'],
        'subspecialty': 'seasonal_perennial',
        'measure_types': ['MD', 'SMD']
    },
    'EYELID_SWELLING': {
        'aliases': ['eyelid swelling', 'lid swelling', 'eyelid o?edema',
                    'eyelid edema', 'eyelid oedema', 'palpebral swelling',
                    'eyelid swelling score'],
        'subspecialty': 'seasonal_perennial',
        'measure_types': ['MD', 'SMD']
    },
    'TOSS': {
        'aliases': ['total ocular symptom score', 'toss', 'composite ocular symptom score',
                    'ocular symptom score', 'total ophthalmic symptom score',
                    'mean total ocular symptom score'],
        'subspecialty': 'seasonal_perennial',
        'measure_types': ['MD', 'SMD']
    },
    'SYMPTOM_RESPONDER': {
        'aliases': ['symptom responder', 'composite symptom relief', 'treatment responder',
                    'clinical response', 'responder rate', 'symptom-free',
                    'proportion of responders', 'achieved response'],
        'subspecialty': 'seasonal_perennial',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'CORNEAL_INVOLVEMENT': {
        'aliases': ['corneal involvement', 'corneal keratopathy', 'keratopathy',
                    'shield ulcer', 'corneal epitheliopathy', 'punctate keratitis',
                    'corneal complication'],
        'subspecialty': 'vernal_atopic',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# SEASONAL / PERENNIAL PATTERNS (SAC / PAC)
# ============================================================

SEASONAL_PERENNIAL_PATTERNS = {
    'detection_keywords': [
        r'seasonal\s+allergic\s+conjunctivitis|\bsac\b',
        r'perennial\s+allergic\s+conjunctivitis|\bpac\b',
        r'allergic\s+conjunctivitis', r'ocular\s+allerg(?:y|ic)',
        r'ocular\s+itch(?:ing)?', r'conjunctival\s+hypera?emia',
        r'olopatadine|ketotifen|bepotastine|alcaftadine|epinastine|emedastine|levocabastine',
    ],
    'endpoint_patterns': [
        (r'ocular\s+itch(?:ing)?(?:\s+score)?|conjunctival\s+itching|\bitch(?:ing)?\s+score\b',
         'OCULAR_ITCHING'),
        (r'conjunctival\s+hypera?emia|conjunctival\s+redness|ocular\s+(?:redness|hypera?emia)|'
         r'bulbar\s+hypera?emia|conjunctival\s+injection|redness\s+score', 'CONJUNCTIVAL_HYPERAEMIA'),
        (r'\btearing(?:\s+score)?\b|lacrimation|epiphora|watering\s+eyes', 'TEARING'),
        (r'chemosis(?:\s+score)?|conjunctival\s+o?edema', 'CHEMOSIS'),
        (r'eyelid\s+(?:swelling|o?edema)|lid\s+swelling|palpebral\s+swelling', 'EYELID_SWELLING'),
        (r'total\s+ocular\s+symptom\s+score|\btoss\b|composite\s+ocular\s+symptom\s+score|'
         r'ocular\s+symptom\s+score', 'TOSS'),
        (r'symptom\s+responder|composite\s+symptom\s+relief|responder\s+rate|'
         r'proportion\s+of\s+responders', 'SYMPTOM_RESPONDER'),
    ],
    'context_patterns': [
        r'conjunctival\s+allergen\s+challenge|\bcac\b', r'eye\s+drops?',
        r'at\s+(?:day|week)\s+\d+', r'allergen\s+season',
    ]
}


# ============================================================
# VERNAL / ATOPIC PATTERNS (VKC / AKC)
# ============================================================

VERNAL_ATOPIC_PATTERNS = {
    'detection_keywords': [
        r'vernal\s+keratoconjunctivitis|\bvkc\b',
        r'atopic\s+keratoconjunctivitis|\bakc\b',
        r'shield\s+ulcer', r'giant\s+papill\w+', r'corneal\s+involvement',
        r'ciclosporin|cyclosporine|cyclosporin|tacrolimus', r'limbal',
    ],
    'endpoint_patterns': [
        (r'corneal\s+(?:involvement|keratopathy|epitheliopathy|complication)|keratopathy|'
         r'shield\s+ulcer|punctate\s+keratitis', 'CORNEAL_INVOLVEMENT'),
        (r'ocular\s+itch(?:ing)?(?:\s+score)?', 'OCULAR_ITCHING'),
        (r'conjunctival\s+hypera?emia|conjunctival\s+redness|ocular\s+(?:redness|hypera?emia)',
         'CONJUNCTIVAL_HYPERAEMIA'),
    ],
    'context_patterns': [
        r'limbal\s+(?:papillae|trantas)', r'at\s+(?:week|month)\s+\d+',
        r'photophobia', r'severe\s+ocular\s+allergy',
    ]
}


# ============================================================
# CHALLENGE-MODEL PATTERNS (conjunctival allergen challenge, CAC)
# ============================================================

CHALLENGE_MODEL_PATTERNS = {
    'detection_keywords': [
        r'conjunctival\s+allergen\s+challenge|\bcac\b',
        r'allergen\s+challenge', r'environmental\s+exposure\s+chamber',
        r'ocular\s+itch(?:ing)?', r'onset\s+of\s+action',
    ],
    'endpoint_patterns': [
        (r'ocular\s+itch(?:ing)?(?:\s+score)?', 'OCULAR_ITCHING'),
        (r'conjunctival\s+hypera?emia|conjunctival\s+redness|ocular\s+(?:redness|hypera?emia)|'
         r'bulbar\s+hypera?emia', 'CONJUNCTIVAL_HYPERAEMIA'),
        (r'\btearing(?:\s+score)?\b|lacrimation', 'TEARING'),
    ],
    'context_patterns': [
        r'minutes?\s+post[- ]challenge', r'\d+\s+min(?:utes)?\s+after', r'onset\s+of\s+action',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_allergic_conjunctivitis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect ocular-allergy trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: seasonal_perennial, vernal_atopic, challenge_model."""
    text_lower = text.lower()
    scores = {'seasonal_perennial': 0, 'vernal_atopic': 0, 'challenge_model': 0}
    for kw in SEASONAL_PERENNIAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['seasonal_perennial'] += 1
    for kw in VERNAL_ATOPIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['vernal_atopic'] += 1
    for kw in CHALLENGE_MODEL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['challenge_model'] += 1

    # A vernal/atopic anchor is severe-disease-specific and must tip the tie.
    if re.search(r'vernal\s+keratoconjunctivitis|\bvkc\b|atopic\s+keratoconjunctivitis|\bakc\b|'
                 r'shield\s+ulcer', text_lower):
        scores['vernal_atopic'] += 1
    # An explicit conjunctival-allergen-challenge anchor identifies the CAC study
    # model and must tip the tie toward challenge_model over the generic SAC/PAC.
    elif re.search(r'conjunctival\s+allergen\s+challenge|\bcac\b|'
                   r'environmental\s+exposure\s+chamber', text_lower):
        scores['challenge_model'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('seasonal_perennial', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_allergic_conjunctivitis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'seasonal_perennial': SEASONAL_PERENNIAL_PATTERNS['endpoint_patterns'],
        'vernal_atopic': VERNAL_ATOPIC_PATTERNS['endpoint_patterns'],
        'challenge_model': CHALLENGE_MODEL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_allergic_conjunctivitis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical endpoint, preferring the LONGEST matching alias so
    specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in ALLERGIC_CONJUNCTIVITIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
