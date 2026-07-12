"""
Leishmaniasis (visceral + cutaneous) Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV,
typhoid and schistosomiasis profiles. Leishmaniasis is a top-priority neglected
tropical disease: visceral leishmaniasis (VL / kala-azar, Leishmania donovani) is
endemic and frequently fatal across East Africa (Sudan, South Sudan, Ethiopia,
Kenya, Somalia) and the Indian subcontinent; cutaneous leishmaniasis (CL) is the
most common form worldwide. Treatment RCTs report a distinct endpoint vocabulary
the generic effect-size engine does not recognise on its own.

Subspecialties:
- Visceral (VL / kala-azar) treatment: the two-stage cure structure these trials
  always use -- INITIAL cure (end of treatment, clinically well + parasite-free
  aspirate) and DEFINITIVE / FINAL cure (6 months / Day 210, alive with no
  relapse) -- plus relapse, parasitological (splenic / bone-marrow aspirate)
  clearance, and post-kala-azar dermal leishmaniasis (PKDL). Drugs: liposomal
  amphotericin B (AmBisome), miltefosine, paromomycin (aminosidine), pentavalent
  antimonials (sodium stibogluconate / meglumine antimoniate), pentamidine.
- Cutaneous (CL) treatment: complete cure / re-epithelialisation (cure rate),
  lesion healing, lesion size / induration (continuous). Drugs: as above plus
  intralesional antimony, topical paromomycin, thermotherapy.
- Combination / duration: combination therapy (the East-African SSG+PM standard),
  treatment duration, hospital stay -- the shortened-regimen question.
- Safety: mortality / case fatality, adverse and serious adverse events, and the
  drug-class toxicities that drive VL regimen choice -- antimonial cardiotoxicity
  (QT prolongation), amphotericin / paromomycin nephrotoxicity, hepatotoxicity.

Effect measures follow what these trials report: binary (cure, relapse, clearance,
PKDL, mortality, adverse events) -> RR/OR/RD; relapse over time -> HR; continuous
(lesion size, treatment duration, hospital stay) -> MD/SMD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# LEISHMANIASIS ENDPOINTS
# ============================================================

LEISHMANIASIS_ENDPOINTS = {
    # --- Visceral leishmaniasis (VL / kala-azar) treatment ---
    'DEFINITIVE_CURE': {
        'aliases': ['definitive cure', 'final cure', 'final definitive cure',
                    'definitive parasitological cure', 'cure at 6 months',
                    'cure at day 210', 'cure at month 6', 'six-month cure',
                    '6-month cure rate', 'final cure rate', 'definitive cure rate'],
        'subspecialty': 'visceral',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'INITIAL_CURE': {
        'aliases': ['initial cure', 'initial parasitological cure', 'apparent cure',
                    'cure at end of treatment', 'end-of-treatment cure',
                    'end of treatment cure', 'initial cure rate', 'day 30 cure'],
        'subspecialty': 'visceral',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RELAPSE': {
        'aliases': ['relapse', 'relapse rate', 'relapsed', 'parasitological relapse',
                    'clinical relapse', 'reactivation', 'recurrence of infection',
                    'vl relapse'],
        'subspecialty': 'visceral',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'PARASITE_CLEARANCE': {
        'aliases': ['parasite clearance', 'parasitological clearance',
                    'splenic parasite clearance', 'splenic aspirate',
                    'bone marrow aspirate', 'parasite clearance rate',
                    'parasitological response', 'parasitologically cured'],
        'subspecialty': 'visceral',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PKDL': {
        'aliases': ['post-kala-azar dermal leishmaniasis', 'post kala-azar dermal',
                    'pkdl', 'post-kala-azar'],
        'subspecialty': 'visceral',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Cutaneous leishmaniasis (CL) treatment ---
    'CUTANEOUS_CURE': {
        'aliases': ['complete cure', 'complete re-epithelialization',
                    'complete re-epithelialisation', 'complete healing',
                    'complete clinical cure', 'cure rate', 'clinical cure',
                    'lesion cure', 'cured lesions', 'complete response'],
        'subspecialty': 'cutaneous',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'LESION_HEALING': {
        'aliases': ['lesion healing', 'healing of lesions', 'healing rate',
                    'lesion improvement', 'partial cure', 'partial response',
                    'healed lesions', 're-epithelialization', 're-epithelialisation'],
        'subspecialty': 'cutaneous',
        'measure_types': ['RR', 'OR']
    },
    'LESION_SIZE': {
        'aliases': ['lesion size', 'lesion diameter', 'lesion area',
                    'reduction in lesion size', 'lesion size reduction',
                    'induration', 'induration diameter', 'ulcer size'],
        'subspecialty': 'cutaneous',
        'measure_types': ['MD', 'SMD']
    },

    # --- Combination / duration ---
    'COMBINATION_THERAPY': {
        'aliases': ['combination therapy', 'combination treatment',
                    'combined regimen', 'combination regimen', 'combined therapy',
                    'multidrug therapy', 'combination cure'],
        'subspecialty': 'combination',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TREATMENT_DURATION': {
        'aliases': ['treatment duration', 'duration of treatment',
                    'length of treatment', 'days of treatment', 'treatment days',
                    'shortened regimen', 'shortened treatment', 'short-course'],
        'subspecialty': 'combination',
        'measure_types': ['MD', 'SMD']
    },
    'HOSPITAL_STAY': {
        'aliases': ['hospital stay', 'length of hospital stay', 'length of stay',
                    'duration of hospitalization', 'duration of hospitalisation',
                    'hospitalization duration'],
        'subspecialty': 'combination',
        'measure_types': ['MD', 'SMD']
    },

    # --- Safety ---
    'MORTALITY': {
        'aliases': ['mortality', 'case fatality', 'case-fatality',
                    'all-cause mortality', 'death', 'deaths', 'died',
                    'treatment-related death', 'fatal'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse event', 'adverse events', 'adverse drug reaction',
                    'treatment-emergent adverse', 'any adverse event',
                    'drug-related adverse'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SERIOUS_ADVERSE_EVENTS': {
        'aliases': ['serious adverse event', 'serious adverse events',
                    'severe adverse event', 'grade 3 adverse', 'grade 4 adverse',
                    'life-threatening adverse'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'NEPHROTOXICITY': {
        'aliases': ['nephrotoxicity', 'renal toxicity', 'acute kidney injury',
                    'renal impairment', 'nephrotoxic', 'raised creatinine',
                    'creatinine elevation'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR']
    },
    'CARDIOTOXICITY': {
        'aliases': ['cardiotoxicity', 'qt prolongation', 'qtc prolongation',
                    'cardiac toxicity', 'qtc interval', 'electrocardiographic change',
                    'qt interval prolongation'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR']
    },
    'HEPATOTOXICITY': {
        'aliases': ['hepatotoxicity', 'liver toxicity', 'hepatic toxicity',
                    'transaminase elevation', 'alt elevation', 'ast elevation',
                    'raised transaminases'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR']
    },
}


# ============================================================
# VISCERAL (VL / KALA-AZAR) TREATMENT PATTERNS
# ============================================================

VISCERAL_PATTERNS = {
    'detection_keywords': [
        r'visceral\s+leishmaniasis', r'kala[- ]?azar', r'\bvl\b',
        r'l(?:eishmania)?\.?\s*donovani', r'l(?:eishmania)?\.?\s*infantum',
        r'splenic\s+(?:aspirate|parasite)', r'bone\s+marrow\s+aspirate',
        r'definitive\s+cure', r'initial\s+cure', r'\brelapse', r'\bpkdl\b',
        r'post[- ]kala[- ]?azar', r'parasitolog(?:ical|ically)\s+cur',
    ],
    'endpoint_patterns': [
        (r'definitive\s+(?:parasitological\s+)?cure|final\s+(?:definitive\s+)?cure|'
         r'cure\s+at\s+(?:6\s*months?|day\s*210|month\s*6)|six[- ]month\s+cure', 'DEFINITIVE_CURE'),
        (r'initial\s+(?:parasitological\s+)?cure|apparent\s+cure|'
         r'(?:cure\s+at\s+)?end[- ]of[- ]treatment\s+cure|end\s+of\s+treatment\s+cure', 'INITIAL_CURE'),
        (r'\brelaps|reactivation|recurrence\s+of\s+infection', 'RELAPSE'),
        (r'parasit(?:e|ological)\s+clearance|splenic\s+(?:aspirate|parasite\s+clearance)|'
         r'bone\s+marrow\s+aspirate|parasitological\s+response|parasitologically\s+cured', 'PARASITE_CLEARANCE'),
        (r'post[- ]kala[- ]?azar\s+dermal\s+leishmaniasis|\bpkdl\b|post[- ]kala[- ]?azar', 'PKDL'),
    ],
    'context_patterns': [
        r'\d+\s*mg\/kg', r'day\s+(?:30|210)', r'6[- ]month\s+follow[- ]up',
        r'splenic\s+grade', r'intention[- ]to[- ]treat',
    ]
}


# ============================================================
# CUTANEOUS (CL) TREATMENT PATTERNS
# ============================================================

CUTANEOUS_PATTERNS = {
    'detection_keywords': [
        r'cutaneous\s+leishmaniasis', r'\bcl\b', r'skin\s+lesion', r'oriental\s+sore',
        r'l(?:eishmania)?\.?\s*major', r'l(?:eishmania)?\.?\s*tropica',
        r'l(?:eishmania)?\.?\s*braziliensis', r'l(?:eishmania)?\.?\s*mexicana',
        r'l(?:eishmania)?\.?\s*aethiopica', r're[- ]epithelial(?:ization|isation)',
        r'lesion\s+(?:healing|size|diameter|area)', r'mucocutaneous', r'induration',
    ],
    'endpoint_patterns': [
        (r'complete\s+(?:clinical\s+)?(?:cure|healing|response|re[- ]epithelial(?:ization|isation))|'
         r'cure\s+rate|clinical\s+cure|lesion\s+cure|cured\s+lesions', 'CUTANEOUS_CURE'),
        (r'lesion\s+(?:healing|improvement)|healing\s+(?:of\s+lesions|rate)|'
         r'partial\s+(?:cure|response)|healed\s+lesions|re[- ]epithelial(?:ization|isation)', 'LESION_HEALING'),
        (r'lesion\s+(?:size|diameter|area)|induration(?:\s+diameter)?|ulcer\s+size|'
         r'reduction\s+in\s+lesion\s+size', 'LESION_SIZE'),
    ],
    'context_patterns': [
        r'\bmm\b', r'intralesional', r'thermotherapy', r'topical', r'week\s+\d+',
    ]
}


# ============================================================
# COMBINATION / DURATION PATTERNS
# ============================================================

COMBINATION_PATTERNS = {
    'detection_keywords': [
        r'combination\s+(?:therapy|treatment|regimen)', r'combined\s+(?:therapy|regimen)',
        r'multidrug', r'ssg\s*(?:\+|/|and|plus)\s*(?:pm|paromomycin)',
        r'sodium\s+stibogluconate\s+(?:and|plus|\+)\s+paromomycin',
        r'treatment\s+duration', r'duration\s+of\s+treatment', r'shortened\s+regimen',
        r'short[- ]course', r'days\s+of\s+treatment', r'length\s+of\s+(?:hospital\s+)?stay',
    ],
    'endpoint_patterns': [
        (r'combination\s+(?:therapy|treatment|regimen|cure)|combined\s+(?:therapy|regimen)|'
         r'multidrug\s+therapy', 'COMBINATION_THERAPY'),
        (r'treatment\s+duration|duration\s+of\s+treatment|length\s+of\s+treatment|'
         r'(?:days|treatment\s+days)\s+of\s+treatment|shortened\s+(?:regimen|treatment)|short[- ]course', 'TREATMENT_DURATION'),
        (r'(?:length|duration)\s+of\s+(?:hospital\s+)?(?:stay|hospitali[sz]ation)|'
         r'hospital\s+stay|hospitali[sz]ation\s+duration', 'HOSPITAL_STAY'),
    ],
    'context_patterns': [
        r'\bdays\b', r'17[- ]day', r'30[- ]day', r'cost[- ]effective', r'\+',
    ]
}


# ============================================================
# SAFETY PATTERNS
# ============================================================

SAFETY_PATTERNS = {
    'detection_keywords': [
        r'adverse\s+(?:event|drug\s+reaction)', r'serious\s+adverse', r'\bsae\b',
        r'mortality', r'case[- ]fatality', r'nephrotoxicity|renal\s+(?:toxicity|impairment)',
        r'cardiotoxicity|qtc?\s+(?:prolongation|interval)', r'hepatotoxicity|transaminase',
        r'tolerability', r'safety\s+profile', r'\bvomiting\b', r'injection[- ]site',
    ],
    'endpoint_patterns': [
        (r'all[- ]cause\s+mortality|case[- ]fatality|mortality|treatment[- ]related\s+death|'
         r'\bdeaths?\b|\bdied\b', 'MORTALITY'),
        (r'serious\s+adverse\s+events?|severe\s+adverse\s+event|life[- ]threatening\s+adverse|'
         r'grade\s+[34]\s+adverse', 'SERIOUS_ADVERSE_EVENTS'),
        (r'(?:any\s+|drug[- ]related\s+|treatment[- ]emergent\s+)?adverse\s+events?|'
         r'adverse\s+drug\s+reaction', 'ADVERSE_EVENTS'),
        (r'nephrotoxic(?:ity)?|renal\s+(?:toxicity|impairment)|acute\s+kidney\s+injury|'
         r'(?:raised|elevated)\s+creatinine|creatinine\s+elevation', 'NEPHROTOXICITY'),
        (r'cardiotoxic(?:ity)?|qtc?\s+(?:interval\s+)?prolongation|cardiac\s+toxicity|'
         r'qtc?\s+interval|electrocardiographic\s+change', 'CARDIOTOXICITY'),
        (r'hepatotoxic(?:ity)?|(?:liver|hepatic)\s+toxicity|transaminase\s+elevation|'
         r'(?:alt|ast)\s+elevation|raised\s+transaminases', 'HEPATOTOXICITY'),
    ],
    'context_patterns': [
        r'grade\s+[1-4]', r'\bqtc?\b', r'\bg\/dl\b', r'serum\s+creatinine', r'\bctcae\b',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_leishmaniasis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect leishmaniasis trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: visceral, cutaneous, combination, safety, general_leishmaniasis."""
    text_lower = text.lower()
    scores = {'visceral': 0, 'cutaneous': 0, 'combination': 0, 'safety': 0}
    for kw in VISCERAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['visceral'] += 1
    for kw in CUTANEOUS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['cutaneous'] += 1
    for kw in COMBINATION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['combination'] += 1
    for kw in SAFETY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['safety'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_leishmaniasis', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_leishmaniasis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'visceral': VISCERAL_PATTERNS['endpoint_patterns'],
        'cutaneous': CUTANEOUS_PATTERNS['endpoint_patterns'],
        'combination': COMBINATION_PATTERNS['endpoint_patterns'],
        'safety': SAFETY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_leishmaniasis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical leishmaniasis endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings (e.g.
    'final cure rate' -> DEFINITIVE_CURE beats the bare 'cure rate' -> CUTANEOUS_CURE)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in LEISHMANIASIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
