"""
Onchocerciasis (river blindness) Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV,
typhoid and schistosomiasis profiles. Onchocerciasis (Onchocerca volvulus,
transmitted by Simulium blackflies) RCTs report a distinct endpoint vocabulary
the generic effect-size engine does not recognise on its own. Onchocerciasis is a
top-priority African neglected tropical disease: >99% of the ~21 million infected
people live in sub-Saharan Africa, and it is the world's second leading
infectious cause of blindness.

Subspecialties:
- Treatment (microfilaricidal / macrofilaricidal therapy): skin microfilarial
  clearance (skin-snip negative / amicrofilaridermic), skin microfilarial density
  / community microfilarial load (CMFL) by skin snip, microfilarial-density
  reduction, adult-worm (macrofilaricidal) effect / worm sterility. Drugs:
  ivermectin (the microfilaricidal mainstay), moxidectin (longer-acting
  microfilaricide), doxycycline (anti-Wolbachia, macrofilaricidal / sterilising),
  diethylcarbamazine (DEC, historical, causes Mazzotti reactions), suramin
  (historical macrofilaricide), often with albendazole.
- MDA / control (mass drug administration / community-directed treatment with
  ivermectin, CDTI): microfilarial / skin-snip prevalence, palpable-nodule
  (onchocercoma) prevalence, transmission (annual transmission potential, infective
  blackflies, biting rate), incidence of new infection / OV-16 seroconversion.
- Morbidity (chronic disease): ocular onchocerciasis (microfilariae in the cornea /
  anterior chamber, punctate / sclerosing keratitis, iridocyclitis, optic atrophy),
  visual impairment / blindness, onchocercal skin disease (onchodermatitis, severe
  itching / pruritus, reactive skin lesions, depigmentation / leopard skin, hanging
  groin / sowda), onchocerciasis-associated epilepsy / nodding syndrome.
- Safety: adverse events, Mazzotti reaction, serious adverse events (notably
  post-ivermectin encephalopathy in Loa loa co-endemic areas).

Effect measures follow what these trials report: binary (microfilarial clearance,
prevalence, blindness, skin disease, adverse events) -> RR/OR/RD;
incidence / transmission -> IRR/HR/RR; continuous (skin microfilarial density,
microfilarial reduction, transmission potential, ocular microfilariae) -> MD/SMD;
skin microfilarial densities, loads and transmission potentials are right-skewed
-> log scale / GMR.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# ONCHOCERCIASIS ENDPOINTS
# ============================================================

ONCHOCERCIASIS_ENDPOINTS = {
    # --- Microfilaricidal / macrofilaricidal treatment ---
    'MICROFILARIAL_CLEARANCE': {
        'aliases': ['microfilarial clearance', 'skin microfilarial clearance',
                    'microfiladermia clearance', 'skin-snip negative',
                    'skin snip negative', 'amicrofilaridermic', 'amicrofilaremic',
                    'amicrofilaraemic', 'cleared microfilariae', 'mf clearance',
                    'clearance of microfilariae', 'complete clearance of microfilariae'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SKIN_MF_DENSITY': {
        'aliases': ['skin microfilarial density', 'microfilarial density', 'mf density',
                    'community microfilarial load', 'cmfl', 'microfilarial load',
                    'skin microfilarial load', 'microfilariae per mg',
                    'microfilariae per milligram', 'mf per mg', 'skin snip density',
                    'geometric mean microfilarial density', 'microfilariae per mg of skin'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'MICROFILARIAL_REDUCTION': {
        'aliases': ['microfilarial reduction', 'microfilarial density reduction',
                    'reduction in microfilarial density', 'reduction in microfilariae',
                    'percentage reduction in microfilariae', 'percent reduction in microfilariae',
                    'mf reduction', 'reduction in skin microfilariae'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'ADULT_WORM_EFFECT': {
        'aliases': ['adult worm', 'adult female worm', 'macrofilaricidal',
                    'macrofilaricidal effect', 'live female worms', 'live adult worms',
                    'worm sterility', 'female worm viability', 'worm viability',
                    'embryogenesis', 'embryogram', 'normal embryogenesis',
                    'live microfilariae in nodules'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },

    # --- MDA / control (CDTI / mass drug administration) ---
    'MF_PREVALENCE': {
        'aliases': ['microfilarial prevalence', 'prevalence of microfilariae',
                    'skin-snip prevalence', 'skin snip prevalence', 'mf prevalence',
                    'prevalence of infection', 'prevalence of onchocerciasis',
                    'microfilaridermia prevalence', 'infection prevalence'],
        'subspecialty': 'mda',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'NODULE_PREVALENCE': {
        'aliases': ['nodule prevalence', 'palpable nodule', 'nodule rate',
                    'onchocercoma', 'onchocercoma prevalence', 'prevalence of nodules',
                    'palpable nodules', 'nodule palpation'],
        'subspecialty': 'mda',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TRANSMISSION': {
        'aliases': ['annual transmission potential', 'transmission potential', 'atp',
                    'infective blackflies', 'infective flies', 'biting rate',
                    'annual biting rate', 'transmission index', 'infective biting rate',
                    'l3 larvae per fly'],
        'subspecialty': 'mda',
        'measure_types': ['IRR', 'RR', 'MD']
    },
    'INFECTION_INCIDENCE': {
        'aliases': ['incidence of infection', 'incident infection', 'new infection',
                    'infection incidence', 'incidence of onchocerciasis',
                    'ov-16 seroconversion', 'ov16 seroconversion', 'ov-16 seropositivity',
                    'seroconversion to ov-16'],
        'subspecialty': 'mda',
        'measure_types': ['IRR', 'HR', 'RR']
    },

    # --- Morbidity (chronic disease) ---
    'OCULAR_MICROFILARIAE': {
        'aliases': ['ocular microfilariae', 'microfilariae in the cornea',
                    'microfilariae in the anterior chamber', 'anterior chamber microfilariae',
                    'corneal microfilariae', 'punctate keratitis', 'sclerosing keratitis',
                    'iridocyclitis', 'ocular onchocerciasis'],
        'subspecialty': 'morbidity',
        'measure_types': ['RR', 'OR', 'MD']
    },
    'VISUAL_IMPAIRMENT': {
        'aliases': ['visual impairment', 'visual acuity', 'visual loss', 'vision loss',
                    'blindness', 'blind', 'optic atrophy', 'chorioretinitis',
                    'chorioretinopathy', 'visual field loss', 'low vision'],
        'subspecialty': 'morbidity',
        'measure_types': ['RR', 'OR']
    },
    'SKIN_DISEASE': {
        'aliases': ['onchodermatitis', 'onchocercal skin disease', 'onchocercal dermatitis',
                    'severe itching', 'severe pruritus', 'pruritus', 'itching',
                    'reactive skin lesions', 'papular dermatitis', 'acute papular onchodermatitis',
                    'lichenified onchodermatitis', 'depigmentation', 'leopard skin',
                    'hanging groin', 'sowda', 'troublesome itching'],
        'subspecialty': 'morbidity',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'EPILEPSY': {
        'aliases': ['onchocerciasis-associated epilepsy', 'oae', 'nodding syndrome',
                    'epilepsy', 'seizures', 'seizure frequency'],
        'subspecialty': 'morbidity',
        'measure_types': ['RR', 'OR']
    },

    # --- Safety ---
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'adverse event', 'adverse reactions',
                    'adverse reaction', 'treatment-emergent adverse events',
                    'post-treatment reactions', 'tolerability', 'any adverse event'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MAZZOTTI_REACTION': {
        'aliases': ['mazzotti reaction', 'mazzotti', 'mazzotti test',
                    'post-treatment mazzotti reaction'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR']
    },
    'SERIOUS_ADVERSE_EVENTS': {
        'aliases': ['serious adverse events', 'serious adverse event', 'sae',
                    'encephalopathy', 'post-ivermectin encephalopathy',
                    'severe adverse events', 'life-threatening adverse events'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR']
    },
}


# ============================================================
# TREATMENT PATTERNS (microfilaricidal / macrofilaricidal therapy)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'\bivermectin\b', r'\bivm\b', r'moxidectin', r'doxycycline',
        r'diethylcarbamazine', r'\bdec\b', r'suramin', r'anti[- ]?wolbachia',
        r'microfilaricid', r'macrofilaricid', r'skin\s+snip', r'skin[- ]microfilar',
        r'microfilarial\s+(?:density|clearance|load|reduction)',
        r'community\s+microfilarial\s+load|\bcmfl\b', r'amicrofilar',
        r'adult\s+(?:female\s+)?worm', r'mf\s*\/\s*mg|microfilariae\s+per\s+(?:mg|milligram)',
    ],
    'endpoint_patterns': [
        (r'skin[- ]?snip\s+negativ|amicrofilar(?:idermic|emic|aemic)|'
         r'microfilarial\s+clearance|clearance\s+of\s+(?:skin\s+)?microfilariae|'
         r'microfiladermia\s+clearance|cleared\s+microfilariae|mf\s+clearance',
         'MICROFILARIAL_CLEARANCE'),
        (r'microfilarial\s+(?:density\s+)?reduction|reduction\s+in\s+(?:skin\s+)?microfilar|'
         r'percent(?:age)?\s+reduction\s+in\s+microfilar|mf\s+reduction',
         'MICROFILARIAL_REDUCTION'),
        (r'community\s+microfilarial\s+load|\bcmfl\b|skin\s+microfilarial\s+(?:density|load)|'
         r'microfilarial\s+(?:density|load)|mf\s+density|microfilariae\s+per\s+(?:mg|milligram)|'
         r'mf\s*\/\s*mg', 'SKIN_MF_DENSITY'),
        (r'adult\s+(?:female\s+)?worm|macrofilaricid|live\s+(?:female\s+)?worms?|'
         r'worm\s+(?:sterilit|viabilit)|female\s+worm\s+(?:viabilit|fertilit)|'
         r'embryogenesis|embryogram', 'ADULT_WORM_EFFECT'),
    ],
    'context_patterns': [
        r'\d+\s*(?:µg|mcg|microgram)\s*\/\s*kg', r'single\s+(?:oral\s+)?dose',
        r'skin\s+snip', r'geometric\s+mean', r'\bmonth\s+(?:3|6|12)\b',
    ]
}


# ============================================================
# MDA / CONTROL PATTERNS (mass drug administration / CDTI)
# ============================================================

MDA_PATTERNS = {
    'detection_keywords': [
        r'mass\s+drug\s+administration|\bmda\b',
        r'community[- ]directed\s+treatment|\bcdti\b',
        r'ivermectin\s+(?:distribution|treatment\s+round)', r'annual\s+(?:mass\s+)?treatment',
        r'microfilarial\s+prevalence|prevalence\s+of\s+microfilar',
        r'nodule\s+prevalence|palpable\s+nodule|onchocercoma',
        r'transmission\s+(?:interruption|potential)|annual\s+transmission\s+potential|\batp\b',
        r'infective\s+(?:black)?fl(?:y|ies)|simulium', r'biting\s+rate',
        r'elimination|breakpoint', r'ov[- ]?16',
    ],
    'endpoint_patterns': [
        (r'microfilarial\s+prevalence|prevalence\s+of\s+(?:skin\s+)?microfilar|'
         r'skin[- ]?snip\s+prevalence|mf\s+prevalence|microfilaridermia\s+prevalence|'
         r'prevalence\s+of\s+(?:onchocerca|onchocerciasis|infection)', 'MF_PREVALENCE'),
        (r'nodule\s+(?:prevalence|rate)|palpable\s+nodules?|onchocercoma\s+prevalence|'
         r'prevalence\s+of\s+nodules?|onchocercoma', 'NODULE_PREVALENCE'),
        (r'annual\s+transmission\s+potential|\batp\b|transmission\s+(?:potential|index)|'
         r'infective\s+(?:black)?fl(?:y|ies)|annual\s+biting\s+rate|biting\s+rate|\babr\b|'
         r'l3\s+larvae\s+per\s+fly', 'TRANSMISSION'),
        (r'incidence\s+of\s+(?:infection|onchocerciasis|microfilar)|new\s+infection|'
         r'incident\s+infection|infection\s+incidence|seroconversion\s+to\s+ov[- ]?16|'
         r'ov[- ]?16\s+(?:seroconversion|seropositivit)', 'INFECTION_INCIDENCE'),
    ],
    'context_patterns': [
        r'per\s+(?:100\s+)?person[- ]years', r'incidence\s+rate\s+ratio|\birr\b',
        r'years?\s+of\s+(?:treatment|ivermectin)', r'baseline\s+prevalence',
    ]
}


# ============================================================
# MORBIDITY PATTERNS (chronic disease: eye, skin, epilepsy)
# ============================================================

MORBIDITY_PATTERNS = {
    'detection_keywords': [
        r'onchodermatitis|onchocercal\s+(?:skin|dermatitis)',
        r'pruritus|itching', r'reactive\s+skin\s+lesion|papular\s+dermatitis',
        r'lichenif|depigmentation|leopard\s+skin', r'hanging\s+groin|\bsowda\b',
        r'visual\s+(?:impairment|acuity|loss|field)|blindness|\bblind\b',
        r'ocular\s+(?:onchocerciasis|microfilar)|punctate\s+keratitis|'
        r'sclerosing\s+keratitis|iridocyclitis|optic\s+atrophy|chorioretin',
        r'microfilariae\s+in\s+the\s+(?:cornea|anterior\s+chamber)',
        r'epilepsy|nodding\s+syndrome|onchocerciasis[- ]associated\s+epilepsy|\boae\b',
    ],
    'endpoint_patterns': [
        (r'ocular\s+microfilar|microfilariae\s+in\s+the\s+(?:cornea|anterior\s+chamber)|'
         r'anterior\s+chamber\s+microfilar|corneal\s+microfilar|punctate\s+keratitis|'
         r'sclerosing\s+keratitis|iridocyclitis|ocular\s+onchocerciasis', 'OCULAR_MICROFILARIAE'),
        (r'visual\s+(?:impairment|acuity|loss|field)|blindness|\bblind\b|optic\s+atrophy|'
         r'chorioretin(?:itis|opathy)|vision\s+loss|low\s+vision', 'VISUAL_IMPAIRMENT'),
        (r'onchodermatitis|onchocercal\s+(?:skin\s+disease|dermatitis)|'
         r'severe\s+(?:itching|pruritus)|pruritus|itching|reactive\s+skin\s+lesions?|'
         r'papular\s+dermatitis|lichenif\w+|depigmentation|leopard\s+skin|'
         r'hanging\s+groin|\bsowda\b', 'SKIN_DISEASE'),
        (r'onchocerciasis[- ]associated\s+epilepsy|\boae\b|nodding\s+syndrome|'
         r'epilepsy|seizures?', 'EPILEPSY'),
    ],
    'context_patterns': [
        r'slit[- ]lamp', r'snellen|logmar', r'mini[- ]mental', r'severity\s+score',
    ]
}


# ============================================================
# SAFETY PATTERNS
# ============================================================

SAFETY_PATTERNS = {
    'detection_keywords': [
        r'adverse\s+events?|adverse\s+reactions?', r'\bae[s]?\b',
        r'mazzotti', r'serious\s+adverse\s+events?|\bsae[s]?\b',
        r'encephalopath', r'loa\s+loa|loiasis|loa\s+microfilar',
        r'post[- ](?:treatment|ivermectin)\s+(?:reaction|encephalopath)',
        r'tolerability|safety', r'o?edema|fever|headache|myalgia|arthralgia',
    ],
    'endpoint_patterns': [
        (r'mazzotti(?:\s+(?:reaction|test))?', 'MAZZOTTI_REACTION'),
        (r'serious\s+adverse\s+events?|\bsae[s]?\b|encephalopath(?:y|ies)|'
         r'life[- ]threatening\s+adverse|post[- ]ivermectin\s+(?:encephalopath|serious)',
         'SERIOUS_ADVERSE_EVENTS'),
        (r'adverse\s+events?|adverse\s+reactions?|\bae[s]?\b|treatment[- ]emergent|'
         r'post[- ]treatment\s+reactions?|tolerabilit', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'grade\s+[1-4]', r'within\s+\d+\s+(?:hours|days)\s+of\s+treatment',
        r'loa\s+loa\s+co[- ]?(?:infection|endemic)',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_onchocerciasis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect onchocerciasis trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: treatment, mda, morbidity, safety, general_onchocerciasis."""
    text_lower = text.lower()
    scores = {'treatment': 0, 'mda': 0, 'morbidity': 0, 'safety': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in MDA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mda'] += 1
    for kw in MORBIDITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['morbidity'] += 1
    for kw in SAFETY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['safety'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_onchocerciasis', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_onchocerciasis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'mda': MDA_PATTERNS['endpoint_patterns'],
        'morbidity': MORBIDITY_PATTERNS['endpoint_patterns'],
        'safety': SAFETY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_onchocerciasis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical onchocerciasis endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in ONCHOCERCIASIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
