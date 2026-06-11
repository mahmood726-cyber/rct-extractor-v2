"""
Alzheimer's Disease / Dementia Subspecialty Patterns and Endpoints

Built for the same meta-analysis extraction workflow as the malaria / TB / HIV
profiles. Alzheimer's disease (AD) and dementia RCTs report a distinct endpoint
vocabulary (ADAS-Cog, CDR-SB, MMSE, ADCS-ADL, iADRS, NPI, CMAI, amyloid PET
centiloids, ARIA) that the generic effect-size engine does not recognise.

Subspecialties:
- Symptomatic (cognitive enhancers): cholinesterase inhibitors (donepezil,
  rivastigmine, galantamine) and memantine. Endpoints: ADAS-Cog, MMSE, ADCS-ADL,
  CIBIC-plus.
- Disease-modifying (anti-amyloid / anti-tau): monoclonal antibodies (lecanemab,
  aducanumab, donanemab, gantenerumab, solanezumab). Endpoints: CDR-SB and iADRS
  change/slowing, amyloid PET (centiloids), plasma p-tau, ARIA-E/ARIA-H safety.
- Neuropsychiatric (BPSD): agitation, psychosis, depression in dementia
  (brexpiprazole, citalopram, pimavanserin). Endpoints: NPI, CMAI agitation.
- Prevention / MCI: cognitively unimpaired or mild cognitive impairment;
  progression to dementia / clinical progression, time to diagnosis.

Effect measures: binary (responder, progression-to-dementia, ARIA, adverse
events) -> RR/OR/RD; time-to-event (progression, mortality) -> HR; continuous
cognitive/functional scale change (ADAS-Cog, CDR-SB, MMSE, ADCS-ADL, NPI,
centiloids) pools as a mean difference via the core effect-size engine.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# ALZHEIMER'S DISEASE ENDPOINTS
# ============================================================

ALZHEIMERS_ENDPOINTS = {
    # --- Cognitive scales ---
    'ADAS_COG': {
        'aliases': ['adas-cog', 'adas cog', 'adas-cog11', 'adas-cog13', 'adas-cog14',
                    'alzheimer disease assessment scale', 'cognitive subscale'],
        'subspecialty': 'symptomatic',
        'measure_types': ['MD', 'SMD']
    },
    'CDR_SB': {
        'aliases': ['cdr-sb', 'cdr-sob', 'cdr sum of boxes', 'cdr sum-of-boxes',
                    'clinical dementia rating sum of boxes',
                    'clinical dementia rating-sum of boxes'],
        'subspecialty': 'disease_modifying',
        'measure_types': ['MD']
    },
    'MMSE': {
        'aliases': ['mmse', 'mini-mental state examination', 'mini mental state',
                    'mini-mental state', 'mini-mental'],
        'subspecialty': 'symptomatic',
        'measure_types': ['MD']
    },
    'ADCS_ADL': {
        'aliases': ['adcs-adl', 'adcs adl', 'activities of daily living',
                    'adcs-mci-adl', 'adcs-adl-mci', 'instrumental activities of daily living',
                    'functional activities'],
        'subspecialty': 'symptomatic',
        'measure_types': ['MD']
    },
    'IADRS': {
        'aliases': ['iadrs', 'integrated alzheimer disease rating scale',
                    'integrated ad rating scale'],
        'subspecialty': 'disease_modifying',
        'measure_types': ['MD']
    },

    # --- Disease-modifying biomarkers / imaging ---
    'AMYLOID_PET': {
        'aliases': ['amyloid pet', 'centiloid', 'centiloids', 'amyloid burden',
                    'amyloid plaque', 'brain amyloid', 'amyloid load',
                    'pet amyloid', 'standardized uptake value ratio', 'suvr'],
        'subspecialty': 'disease_modifying',
        'measure_types': ['MD']
    },
    'ARIA': {
        'aliases': ['aria', 'amyloid-related imaging abnormalities', 'aria-e',
                    'aria-h', 'aria-e or aria-h', 'vasogenic edema', 'vasogenic oedema',
                    'microha?emorrhage', 'cerebral microhemorrhage'],
        'subspecialty': 'disease_modifying',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Neuropsychiatric (BPSD) ---
    'NPI': {
        'aliases': ['npi', 'neuropsychiatric inventory', 'npi-nh', 'npi-q',
                    'behavioral symptoms', 'behavioural symptoms'],
        'subspecialty': 'neuropsychiatric',
        'measure_types': ['MD', 'SMD']
    },
    'AGITATION': {
        'aliases': ['agitation', 'cmai', 'cohen-mansfield agitation inventory',
                    'agitation/aggression', 'aggression'],
        'subspecialty': 'neuropsychiatric',
        'measure_types': ['MD', 'RR', 'OR']
    },
    'PSYCHOSIS': {
        'aliases': ['psychosis', 'dementia-related psychosis', 'hallucinations',
                    'delusions', 'psychotic symptoms'],
        'subspecialty': 'neuropsychiatric',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Prevention / MCI ---
    'PROGRESSION_TO_DEMENTIA': {
        'aliases': ['progression to dementia', 'conversion to dementia',
                    'incident dementia', 'progression to alzheimer',
                    'clinical progression', 'time to dementia diagnosis',
                    'progression of disease'],
        'subspecialty': 'prevention_mci',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- Responder / global ---
    'RESPONDER': {
        'aliases': ['responder', 'responder rate', 'cibic-plus responder',
                    'global response', 'clinical response',
                    'clinically meaningful response'],
        'subspecialty': 'symptomatic',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Safety / shared ---
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'serious adverse events', 'serious adverse event',
                    'treatment-emergent adverse events', 'discontinuation due to adverse',
                    'infusion-related reactions'],
        'subspecialty': 'symptomatic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'overall survival',
                    'all-cause death'],
        'subspecialty': 'prevention_mci',
        'measure_types': ['HR', 'RR', 'OR']
    },
}


# ============================================================
# SYMPTOMATIC PATTERNS (cholinesterase inhibitors / memantine)
# ============================================================

TREATMENT_PATTERNS = {  # = symptomatic
    'detection_keywords': [
        r'donepezil|rivastigmine|galantamine|memantine',
        r'cholinesterase\s+inhibitor|acetylcholinesterase|\bachei?\b',
        r'\bnmda\b\s+(?:receptor\s+)?antagonist',
        r'mild[- ]to[- ]moderate\s+(?:alzheimer|dementia)',
        r'adas[- ]?cog|\bmmse\b|adcs[- ]?adl|cibic',
        r'cognitive\s+(?:enhance|function|decline)',
    ],
    'endpoint_patterns': [
        (r'adas[- ]?cog(?:1[134])?|cognitive\s+subscale|'
         r'alzheimer\s+disease\s+assessment\s+scale', 'ADAS_COG'),
        (r'\bmmse\b|mini[- ]mental', 'MMSE'),
        (r'adcs[- ]?(?:mci[- ]?)?adl|activities\s+of\s+daily\s+living|'
         r'functional\s+activities', 'ADCS_ADL'),
        (r'cdr[- ]?s[ob]b|cdr\s+sum[- ]of[- ]boxes|sum\s+of\s+boxes', 'CDR_SB'),
        (r'responder\s+rate|cibic[- ]?plus|\bresponders?\b|global\s+response',
         'RESPONDER'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'change\s+from\s+baseline', r'week\s+\d+\s+change',
        r'mild[- ]to[- ]moderate', r'add[- ]on|adjunct',
    ]
}


# ============================================================
# DISEASE-MODIFYING PATTERNS (anti-amyloid / anti-tau mAbs)
# ============================================================

DRUG_RESISTANT_PATTERNS = {  # = disease_modifying
    'detection_keywords': [
        r'lecanemab|aducanumab|donanemab|gantenerumab|solanezumab|crenezumab|'
        r'bapineuzumab|remternetug',
        r'anti[- ]amyloid|amyloid[- ]beta|a[βb]?42|monoclonal\s+antibod',
        r'anti[- ]tau|tau\s+(?:pathology|aggregation)',
        r'amyloid\s+pet|centiloid|plasma\s+p[- ]?tau|\bsuvr\b',
        r'\baria[- ]?[eh]?\b|amyloid[- ]related\s+imaging',
        r'early\s+(?:symptomatic\s+)?alzheimer|\bmci\s+due\s+to\b',
    ],
    'endpoint_patterns': [
        (r'cdr[- ]?s[ob]b|cdr\s+sum[- ]of[- ]boxes|clinical\s+dementia\s+rating\s+sum',
         'CDR_SB'),
        (r'\biadrs\b|integrated\s+alzheimer', 'IADRS'),
        (r'amyloid\s+pet|centiloids?|amyloid\s+(?:burden|load|plaque)|\bsuvr\b|'
         r'standardized\s+uptake\s+value', 'AMYLOID_PET'),
        (r'\baria(?:[- ]?[eh])?\b|amyloid[- ]related\s+imaging|vasogenic\s+o?edema|'
         r'micro\s?ha?emorrhage|cerebral\s+micro\s?hemorrhage', 'ARIA'),
        (r'adas[- ]?cog(?:1[134])?', 'ADAS_COG'),
        (r'serious\s+adverse\s+events?|infusion[- ]related\s+reactions?|'
         r'\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'slowing\s+of\s+(?:clinical\s+)?decline', r'percent\s+slowing',
        r'apoe\s*[εe]?4|apolipoprotein', r'every\s+(?:two|four|2|4)\s+weeks',
    ]
}


# ============================================================
# NEUROPSYCHIATRIC PATTERNS (BPSD: agitation / psychosis / depression)
# ============================================================

PREVENTION_PATTERNS = {  # = neuropsychiatric
    'detection_keywords': [
        r'agitation|\bcmai\b|cohen[- ]mansfield|aggression',
        r'dementia[- ]related\s+psychosis|psychosis|hallucinations|delusions',
        r'brexpiprazole|pimavanserin|citalopram|risperidone|quetiapine',
        r'neuropsychiatric\s+(?:inventory|symptoms)|\bnpi\b|\bbpsd\b',
        r'behaviou?ral\s+and\s+psychological\s+symptoms',
        r'depression\s+in\s+(?:alzheimer|dementia)',
    ],
    'endpoint_patterns': [
        (r'\bcmai\b|cohen[- ]mansfield|\bagitation\b|aggression', 'AGITATION'),
        (r'dementia[- ]related\s+psychosis|\bpsychosis\b|hallucinations|delusions',
         'PSYCHOSIS'),
        (r'\bnpi(?:[- ]?(?:nh|q))?\b|neuropsychiatric\s+inventory|'
         r'behaviou?ral\s+symptoms', 'NPI'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)', 'MORTALITY'),
    ],
    'context_patterns': [
        r'nursing\s+home|long[- ]term\s+care', r'caregiver\s+(?:burden|distress)',
        r'placebo[- ]controlled',
    ]
}


# ============================================================
# PREVENTION / MCI PATTERNS
# ============================================================

LATENT_PATTERNS = {  # = prevention_mci
    'detection_keywords': [
        r'mild\s+cognitive\s+impairment|\bmci\b',
        r'cognitively\s+(?:unimpaired|normal|healthy)|preclinical\s+alzheimer',
        r'prevention\s+of\s+(?:dementia|alzheimer|cognitive\s+decline)',
        r'progression\s+to\s+(?:dementia|alzheimer)|conversion\s+to\s+dementia',
        r'incident\s+dementia|time\s+to\s+(?:dementia|diagnosis)',
        r'at[- ]risk|amyloid[- ]positive\s+cognitively',
    ],
    'endpoint_patterns': [
        (r'progression\s+to\s+(?:dementia|alzheimer)|conversion\s+to\s+dementia|'
         r'incident\s+dementia|clinical\s+progression|time\s+to\s+dementia',
         'PROGRESSION_TO_DEMENTIA'),
        (r'cdr[- ]?s[ob]b|cdr\s+sum[- ]of[- ]boxes', 'CDR_SB'),
        (r'adas[- ]?cog(?:1[134])?', 'ADAS_COG'),
        (r'\bmmse\b|mini[- ]mental', 'MMSE'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)', 'MORTALITY'),
    ],
    'context_patterns': [
        r'amyloid[- ]positive', r'apoe', r'years\s+of\s+follow[- ]up',
        r'cognitively\s+unimpaired',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_alzheimers_subspecialty(text: str) -> Tuple[str, float]:
    """Detect AD/dementia trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: symptomatic, disease_modifying, neuropsychiatric,
    prevention_mci, general_ad."""
    text_lower = text.lower()
    scores = {'symptomatic': 0, 'disease_modifying': 0, 'neuropsychiatric': 0,
              'prevention_mci': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['symptomatic'] += 1
    for kw in DRUG_RESISTANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['disease_modifying'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['neuropsychiatric'] += 1
    for kw in LATENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['prevention_mci'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_ad', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_alzheimers_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'symptomatic': TREATMENT_PATTERNS['endpoint_patterns'],
        'disease_modifying': DRUG_RESISTANT_PATTERNS['endpoint_patterns'],
        'neuropsychiatric': PREVENTION_PATTERNS['endpoint_patterns'],
        'prevention_mci': LATENT_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_alzheimers_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical AD endpoint, preferring the LONGEST matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in ALZHEIMERS_ENDPOINTS.items():
        for alias in info['aliases']:
            # alias may itself be a tiny regex fragment (microha?emorrhage); use a
            # plain substring test on the literalised form to stay catastrophic-safe
            a = alias.replace('?', '')
            if a in endpoint_lower and len(a) > best_len:
                best, best_len = canonical, len(a)
    return best if best else endpoint.upper()
