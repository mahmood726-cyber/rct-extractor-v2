"""
Lymphatic Filariasis (LF / elephantiasis) Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV,
typhoid, schistosomiasis and soil-transmitted-helminth profiles. Lymphatic
filariasis (Wuchereria bancrofti / Brugia malayi / Brugia timori) RCTs report a
distinct endpoint vocabulary the generic effect-size engine does not recognise on
its own. LF is a top-priority African neglected tropical disease and a WHO
global-elimination target: the bulk of the global burden is in sub-Saharan
Africa, South Asia and Southeast Asia, and it is controlled by mass drug
administration (MDA / preventive chemotherapy).

Subspecialties:
- MDA / clearance (the core efficacy question): clearance of microfilaraemia
  (mf clearance / amicrofilaraemia / mf-negative conversion), microfilaria (mf)
  density reduction, circulating-filarial-antigen (CFA / antigenaemia) clearance,
  and adult-(macrofilaricidal) worm death. Drugs: diethylcarbamazine (DEC),
  albendazole (ALB) and ivermectin (IVM), given as the two-drug DA (DEC+ALB) or
  IA (IVM+ALB) regimens or the WHO-recommended triple-drug IDA (IVM+DEC+ALB),
  plus DEC-medicated salt and the anti-Wolbachia macrofilaricide doxycycline.
- Transmission / prevalence (the elimination endpoint): community microfilaria
  prevalence, circulating-filarial-antigen prevalence, incidence of (new)
  infection, and entomological transmission (transmission assessment survey /
  TAS, mosquito infection rate / xenomonitoring).
- Morbidity (chronic disease): lymphoedema / elephantiasis stage and progression,
  hydrocele, acute adenolymphangitis (ADL / acute filarial attacks / ADLA), and
  limb volume (morbidity management and disability prevention, MMDP).
- Safety: adverse events, serious adverse events, and systemic post-treatment
  (Mazzotti-type) reactions to dying microfilariae (fever, headache, myalgia).

Effect measures follow what these trials report: binary (mf clearance, antigen
clearance, mf / antigen prevalence, lymphoedema, hydrocele, adverse events) ->
RR/OR/RD; incidence / acute attacks / transmission -> IRR/HR; continuous (limb
volume) -> MD/SMD; microfilaria density is strongly right-skewed -> log scale /
geometric mean ratio (GMR), pooled on the log scale.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# LYMPHATIC FILARIASIS ENDPOINTS
# ============================================================

LYMPHATIC_FILARIASIS_ENDPOINTS = {
    # --- MDA / clearance (microfilaricidal & macrofilaricidal efficacy) ---
    'MF_CLEARANCE': {
        'aliases': ['microfilaria clearance', 'microfilarial clearance',
                    'microfilaraemia clearance', 'microfilaremia clearance',
                    'clearance of microfilaraemia', 'clearance of microfilaremia',
                    'mf clearance', 'amicrofilaraemia', 'amicrofilaremia',
                    'microfilaria-negative', 'microfilaria negative',
                    'mf-negative', 'parasitological clearance',
                    'cleared microfilaraemia', 'complete clearance'],
        'subspecialty': 'mda',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MF_DENSITY': {
        'aliases': ['microfilaria density', 'microfilarial density',
                    'microfilaraemia density', 'microfilaremia density',
                    'mf density', 'microfilaria count', 'mf count',
                    'mean microfilaria density', 'geometric mean microfilaria',
                    'microfilariae per ml', 'microfilariae per millilitre',
                    'mf/ml', 'microfilaria load'],
        'subspecialty': 'mda',
        'measure_types': ['MD', 'SMD']
    },
    'ANTIGEN_CLEARANCE': {
        'aliases': ['antigenaemia clearance', 'antigenemia clearance',
                    'antigen clearance', 'clearance of antigenaemia',
                    'circulating filarial antigen clearance', 'cfa clearance',
                    'antigen-negative', 'antigen negative', 'ict-negative',
                    'antigen clearance rate'],
        'subspecialty': 'mda',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ADULT_WORM': {
        'aliases': ['adult worm death', 'adult-worm death', 'macrofilaricidal',
                    'macrofilaricidal effect', 'adult worm', 'worm death',
                    'filarial dance sign', 'live adult worms', 'worm nest'],
        'subspecialty': 'mda',
        'measure_types': ['RR', 'OR']
    },

    # --- Transmission / prevalence (elimination endpoints) ---
    'MF_PREVALENCE': {
        'aliases': ['microfilaria prevalence', 'microfilarial prevalence',
                    'microfilaraemia prevalence', 'microfilaremia prevalence',
                    'mf prevalence', 'prevalence of microfilaraemia',
                    'prevalence of microfilaremia', 'microfilaria rate'],
        'subspecialty': 'transmission',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ANTIGEN_PREVALENCE': {
        'aliases': ['antigen prevalence', 'antigenaemia prevalence',
                    'antigenemia prevalence', 'cfa prevalence',
                    'circulating filarial antigen prevalence',
                    'antigen positivity', 'antigen-positive', 'ict prevalence',
                    'prevalence of antigenaemia'],
        'subspecialty': 'transmission',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'INFECTION_INCIDENCE': {
        'aliases': ['incidence of infection', 'incident infection',
                    'new infection', 'infection incidence',
                    'incidence of microfilaraemia', 'seroconversion'],
        'subspecialty': 'transmission',
        'measure_types': ['IRR', 'HR', 'RR']
    },
    'TRANSMISSION': {
        'aliases': ['transmission assessment survey', 'transmission interruption',
                    'mosquito infection rate', 'infection in mosquitoes',
                    'xenomonitoring', 'vector infection', 'infective larvae',
                    'entomological inoculation', 'transmission'],
        'subspecialty': 'transmission',
        'measure_types': ['RR', 'IRR', 'OR']
    },

    # --- Morbidity (chronic disease) ---
    'LYMPHOEDEMA': {
        'aliases': ['lymphoedema', 'lymphedema', 'elephantiasis', 'limb swelling',
                    'lymphoedema stage', 'lymphedema stage',
                    'lymphoedema progression', 'lymphoedema improvement',
                    'leg swelling', 'lymphatic dysfunction'],
        'subspecialty': 'morbidity',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HYDROCELE': {
        'aliases': ['hydrocele', 'hydrocoele', 'scrotal swelling',
                    'hydrocelectomy', 'hydrocele prevalence'],
        'subspecialty': 'morbidity',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ACUTE_ATTACK': {
        'aliases': ['acute adenolymphangitis', 'adenolymphangitis', 'acute attack',
                    'acute filarial attack', 'acute dermatolymphangioadenitis',
                    'acute dermato-lymphangio-adenitis', 'filarial fever',
                    'acute attacks', 'adla', 'adl episode'],
        'subspecialty': 'morbidity',
        'measure_types': ['IRR', 'RR', 'HR']
    },
    'LIMB_VOLUME': {
        'aliases': ['limb volume', 'leg volume', 'limb circumference',
                    'oedema volume', 'edema volume', 'affected limb volume'],
        'subspecialty': 'morbidity',
        'measure_types': ['MD', 'SMD']
    },

    # --- Safety ---
    'ADVERSE_EVENTS': {
        'aliases': ['adverse event', 'adverse events', 'adverse reaction',
                    'adverse reactions', 'systemic adverse event',
                    'treatment-related adverse event', 'any adverse event',
                    'overall adverse events'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SERIOUS_AE': {
        'aliases': ['serious adverse event', 'serious adverse events',
                    'serious adverse reaction', 'sae'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SYSTEMIC_REACTION': {
        'aliases': ['systemic reaction', 'mazzotti reaction',
                    'post-treatment reaction', 'post treatment reaction',
                    'systemic post-treatment reaction', 'fever', 'headache',
                    'myalgia', 'dizziness'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# MDA / CLEARANCE PATTERNS (microfilaricidal & macrofilaricidal)
# ============================================================

MDA_PATTERNS = {
    'detection_keywords': [
        r'diethylcarbamazine', r'\bdec\b', r'albendazole', r'ivermectin',
        r'\bida\b', r'triple[- ]drug|triple\s+therapy', r'\bdec\b[- ]+albendazole',
        r'dec[- ]medicated\s+salt', r'doxycycline', r'anti[- ]wolbachia',
        r'mass\s+drug\s+administration|\bmda\b', r'preventive\s+chemotherapy',
        r'microfilar(?:ia[el]?|a?emia)\s+clearance', r'mf\s+clearance',
        r'amicrofilar(?:ae|e)mia', r'microfilar(?:ia[el]?|a?emia)\s+density',
        r'\bmf\s+density', r'antigen(?:ae|e)mia\s+clearance', r'macrofilaricidal',
    ],
    'endpoint_patterns': [
        (r'(?:microfilar(?:ia[el]?|a?emia)|mf)\s+clearance|'
         r'clearance\s+of\s+microfilar(?:ia[el]?|a?emia)|'
         r'amicrofilar(?:ae|e)mia|microfilar(?:ia[el]?|a?emia)?[- ]negative|'
         r'mf[- ]negative|parasitological\s+clearance', 'MF_CLEARANCE'),
        (r'(?:microfilar(?:ia[el]?|a?emia)|mf)\s+(?:density|count|load)|'
         r'geometric\s+mean\s+microfilar|microfilariae\s+per\s+m(?:l|illilitre)',
         'MF_DENSITY'),
        (r'(?:antigen(?:ae|e)mia|antigen|circulating\s+filarial\s+antigen|cfa|'
         r'ict)[- ]?(?:clearance|negative)|clearance\s+of\s+antigen(?:ae|e)mia',
         'ANTIGEN_CLEARANCE'),
        (r'macrofilaricidal|adult[- ]worm\s+death|adult\s+worm|worm\s+death|'
         r'filarial\s+dance\s+sign', 'ADULT_WORM'),
    ],
    'context_patterns': [
        r'single\s+(?:oral\s+)?dose', r'\d+\s*mg(?:\/kg)?', r'night\s+blood',
        r'membrane\s+filtration', r'\bday\s+(?:7|14|28|30)\b', r'\bmonth\s+12\b',
        r'geometric\s+mean',
    ]
}


# ============================================================
# TRANSMISSION / PREVALENCE PATTERNS (elimination)
# ============================================================

TRANSMISSION_PATTERNS = {
    'detection_keywords': [
        r'microfilar(?:ia[el]?|a?emia)\s+prevalence', r'mf\s+prevalence',
        r'antigen(?:ae|e)mia\s+prevalence|antigen\s+prevalence',
        r'transmission\s+assessment\s+survey|\btas\b',
        r'transmission\s+interruption|transmission',
        r'xenomonitoring', r'mosquito\s+infection|infection\s+in\s+mosquitoes',
        r'vector\s+infection', r'infective\s+larvae',
        r'incidence\s+of\s+(?:infection|microfilar)', r'elimination',
    ],
    'endpoint_patterns': [
        (r'(?:microfilar(?:ia[el]?|a?emia)|mf)\s+prevalence|'
         r'prevalence\s+of\s+microfilar(?:ia[el]?|a?emia)|'
         r'microfilar(?:ia[el]?|a?emia)\s+rate', 'MF_PREVALENCE'),
        (r'(?:antigen(?:ae|e)mia|cfa|circulating\s+filarial\s+antigen|ict|antigen)\s+'
         r'prevalence|antigen\s+positivit|prevalence\s+of\s+antigen(?:ae|e)mia',
         'ANTIGEN_PREVALENCE'),
        (r'incidence\s+of\s+(?:infection|microfilar(?:ia[el]?|a?emia))|incident\s+infection|'
         r'new\s+infection|infection\s+incidence|seroconversion', 'INFECTION_INCIDENCE'),
        (r'transmission\s+assessment\s+survey|transmission\s+interruption|'
         r'mosquito\s+infection\s+rate|infection\s+in\s+mosquitoes|xenomonitoring|'
         r'vector\s+infection|infective\s+larvae|transmission', 'TRANSMISSION'),
    ],
    'context_patterns': [
        r'per\s+(?:100\s+)?person[- ]years', r'incidence\s+rate\s+ratio|\birr\b',
        r'sentinel\s+site', r'pre[- ]?tas|\btas\b', r'\bict\b',
    ]
}


# ============================================================
# MORBIDITY PATTERNS (chronic disease)
# ============================================================

MORBIDITY_PATTERNS = {
    'detection_keywords': [
        r'lymph(?:o)?(?:ae|e)dema|lymphedema', r'elephantiasis', r'limb\s+swelling',
        r'hydroc(?:o)?ele', r'scrotal\s+swelling', r'hydrocelectomy',
        r'aden(?:o)?lymphangitis|acute\s+attack|acute\s+filarial\s+attack',
        r'dermato[- ]?lymphangio[- ]?adenitis|\badla?\b',
        r'limb\s+volume|leg\s+volume|limb\s+circumference', r'filarial\s+fever',
        r'morbidity\s+management|disability\s+prevention|\bmmdp\b',
    ],
    'endpoint_patterns': [
        (r'lymph(?:o)?(?:ae|e)dema|lymphedema|elephantiasis|limb\s+swelling|'
         r'leg\s+swelling', 'LYMPHOEDEMA'),
        (r'hydroc(?:o)?ele|scrotal\s+swelling|hydrocelectomy', 'HYDROCELE'),
        (r'acute\s+aden(?:o)?lymphangitis|aden(?:o)?lymphangitis|acute\s+filarial\s+attack|'
         r'acute\s+dermato[- ]?lymphangio[- ]?adenitis|filarial\s+fever|'
         r'acute\s+attacks?|\badla?\b', 'ACUTE_ATTACK'),
        (r'limb\s+volume|leg\s+volume|limb\s+circumference|(?:o|oe)dema\s+volume',
         'LIMB_VOLUME'),
    ],
    'context_patterns': [
        r'stage\s+[1-7]\b', r'\bml\b|\bcm\b', r'perometr|water\s+displacement',
        r'episodes?\s+per\s+(?:year|patient)',
    ]
}


# ============================================================
# SAFETY PATTERNS
# ============================================================

SAFETY_PATTERNS = {
    'detection_keywords': [
        r'adverse\s+events?|adverse\s+reactions?', r'serious\s+adverse\s+event|\bsae\b',
        r'mazzotti\s+reaction', r'post[- ]treatment\s+reaction',
        r'systemic\s+(?:adverse\s+)?reaction', r'tolerability|safety\s+profile',
        r'\bfever\b', r'\bheadache\b', r'\bmyalgia\b', r'\bdizziness\b',
    ],
    'endpoint_patterns': [
        (r'serious\s+adverse\s+(?:event|reaction)|\bsae\b', 'SERIOUS_AE'),
        (r'mazzotti\s+reaction|post[- ]treatment\s+reaction|'
         r'systemic\s+(?:post[- ]treatment\s+)?reaction|\bfever\b|\bheadache\b|'
         r'\bmyalgia\b|\bdizziness\b', 'SYSTEMIC_REACTION'),
        (r'adverse\s+events?|adverse\s+reactions?', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'grade\s+[1-4]\b', r'within\s+\d+\s+(?:hours|days)\s+(?:of|after)',
        r'treatment[- ]emergent',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_lymphatic_filariasis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect lymphatic-filariasis trial subspecialty. Returns
    (subspecialty, confidence). Subspecialties: mda, transmission, morbidity,
    safety, general_lymphatic_filariasis."""
    text_lower = text.lower()
    scores = {'mda': 0, 'transmission': 0, 'morbidity': 0, 'safety': 0}
    for kw in MDA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mda'] += 1
    for kw in TRANSMISSION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['transmission'] += 1
    for kw in MORBIDITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['morbidity'] += 1
    for kw in SAFETY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['safety'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_lymphatic_filariasis', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_lymphatic_filariasis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'mda': MDA_PATTERNS['endpoint_patterns'],
        'transmission': TRANSMISSION_PATTERNS['endpoint_patterns'],
        'morbidity': MORBIDITY_PATTERNS['endpoint_patterns'],
        'safety': SAFETY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_lymphatic_filariasis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical lymphatic-filariasis endpoint, preferring the
    LONGEST matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in LYMPHATIC_FILARIASIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
