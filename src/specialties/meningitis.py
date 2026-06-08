"""
Meningitis Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV and
typhoid profiles. Meningitis is an Africa-priority topic: the sub-Saharan
"meningitis belt" (Neisseria meningitidis, Streptococcus pneumoniae, Haemophilus
influenzae type b) drives large epidemic and endemic burden, and meningitis RCTs
report a distinct endpoint vocabulary the generic effect-size engine does not
recognise on its own.

Subspecialties:
- Treatment (antibiotic / adjunctive therapy): clinical cure, treatment failure,
  CSF sterilisation, time to recovery / fever clearance. Drugs: ceftriaxone,
  cefotaxime, chloramphenicol (incl. single-dose oily chloramphenicol),
  benzylpenicillin / ampicillin, meropenem, vancomycin; adjunctive dexamethasone,
  glycerol.
- Vaccine (prevention): laboratory-confirmed meningitis / invasive disease
  incidence, vaccine efficacy, seroconversion (SBA seroresponse), immunogenicity
  (SBA / rSBA / hSBA GMT, GMC), nasopharyngeal carriage. Vaccines: meningococcal
  A conjugate (MenAfriVac / MenA-TT), MenACWY, MenB / 4CMenB, pneumococcal
  conjugate (PCV10 / PCV13), Hib conjugate.
- Mortality: all-cause mortality, case fatality, in-hospital death.
- Sequelae (neurological): hearing loss / deafness, seizures, hydrocephalus,
  focal neurological deficit, neurodevelopmental / cognitive impairment.

Effect measures follow what these trials report: binary (cure, failure, carriage,
death, hearing loss, seizures) -> RR/OR/RD; incidence -> IRR/HR; continuous (time
to recovery -> MD/SMD; SBA titres -> GMR, log-normal).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# MENINGITIS ENDPOINTS
# ============================================================

MENINGITIS_ENDPOINTS = {
    # --- Antibiotic / adjunctive treatment efficacy ---
    'CLINICAL_CURE': {
        'aliases': ['clinical cure', 'clinical success', 'clinical response',
                    'clinical recovery', 'favourable outcome', 'favorable outcome',
                    'good recovery', 'full recovery', 'cure rate'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TREATMENT_FAILURE': {
        'aliases': ['treatment failure', 'clinical failure', 'therapeutic failure',
                    'bacteriological failure', 'microbiological failure',
                    'persistent infection'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'CSF_STERILIZATION': {
        'aliases': ['csf sterilisation', 'csf sterilization', 'csf clearance',
                    'cerebrospinal fluid sterilisation', 'cerebrospinal fluid sterilization',
                    'bacteriological clearance', 'microbiological clearance',
                    'culture conversion', 'csf culture conversion'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TIME_TO_RECOVERY': {
        'aliases': ['time to recovery', 'time to clinical recovery',
                    'fever clearance time', 'time to defervescence',
                    'time to resolution', 'duration of fever',
                    'time to normalisation', 'time to normalization'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD', 'HR']
    },

    # --- Mortality ---
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'case fatality',
                    'case fatality rate', 'in-hospital mortality',
                    'in-hospital death', 'overall mortality', 'died'],
        'subspecialty': 'mortality',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Neurological sequelae ---
    'HEARING_LOSS': {
        'aliases': ['hearing loss', 'deafness', 'hearing impairment',
                    'sensorineural hearing loss', 'severe hearing loss',
                    'profound hearing loss', 'auditory impairment'],
        'subspecialty': 'sequelae',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'NEUROLOGICAL_SEQUELAE': {
        'aliases': ['neurological sequelae', 'neurologic sequelae',
                    'neurological sequela', 'neurological deficit',
                    'neurologic deficit', 'focal neurological deficit',
                    'focal deficit', 'any sequelae', 'major sequelae',
                    'neurological complication'],
        'subspecialty': 'sequelae',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SEIZURES': {
        'aliases': ['seizures', 'seizure', 'convulsions', 'convulsion',
                    'epilepsy', 'recurrent seizures'],
        'subspecialty': 'sequelae',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HYDROCEPHALUS': {
        'aliases': ['hydrocephalus', 'communicating hydrocephalus',
                    'obstructive hydrocephalus'],
        'subspecialty': 'sequelae',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'NEURODEVELOPMENTAL_IMPAIRMENT': {
        'aliases': ['neurodevelopmental impairment', 'developmental delay',
                    'cognitive impairment', 'intellectual disability',
                    'developmental impairment', 'neurodevelopmental sequelae',
                    'psychomotor delay'],
        'subspecialty': 'sequelae',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Vaccine (prevention) ---
    'MENINGITIS_INCIDENCE': {
        'aliases': ['bacterial meningitis', 'meningococcal meningitis',
                    'confirmed meningitis', 'laboratory-confirmed meningitis',
                    'invasive meningococcal disease', 'invasive pneumococcal disease',
                    'meningitis incidence', 'incident meningitis',
                    'incidence of meningitis', 'meningococcal disease',
                    'first episode of meningitis'],
        'subspecialty': 'vaccine',
        'measure_types': ['IRR', 'HR', 'RR']
    },
    'VACCINE_EFFICACY': {
        'aliases': ['vaccine efficacy', 'protective efficacy',
                    'efficacy against meningitis', 'efficacy against invasive disease',
                    'vaccine effectiveness'],
        'subspecialty': 'vaccine',
        'measure_types': ['HR', 'IRR', 'RR']
    },
    'SEROCONVERSION': {
        'aliases': ['seroconversion', 'seroconversion rate', 'seroresponse',
                    'sba seroresponse', 'four-fold rise', 'fourfold rise',
                    'protective titre', 'protective titer',
                    'sba titre >= 8', 'sba titer >= 8'],
        'subspecialty': 'vaccine',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'IMMUNOGENICITY': {
        'aliases': ['serum bactericidal antibody', 'bactericidal antibody',
                    'sba gmt', 'rsba', 'hsba', 'geometric mean titer',
                    'geometric mean titre', 'gmt', 'geometric mean concentration',
                    'gmc', 'immunogenicity', 'antibody titre', 'antibody titer'],
        'subspecialty': 'vaccine',
        'measure_types': ['GMR', 'MD', 'SMD']
    },
    'CARRIAGE': {
        'aliases': ['nasopharyngeal carriage', 'pharyngeal carriage',
                    'meningococcal carriage', 'carriage prevalence',
                    'carriage acquisition', 'oropharyngeal carriage', 'carriage'],
        'subspecialty': 'vaccine',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# TREATMENT PATTERNS (antibiotic / adjunctive therapy)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'ceftriaxone', r'cefotaxime', r'chloramphenicol', r'oily\s+chloramphenicol',
        r'benzylpenicillin', r'\bpenicillin\b', r'ampicillin', r'meropenem',
        r'vancomycin', r'ceftazidime', r'dexamethasone', r'glycerol',
        r'adjunctive\s+(?:dexamethasone|corticosteroid|steroid)',
        r'csf\s+(?:steril|clearance|culture)', r'cerebrospinal\s+fluid',
        r'clinical\s+cure', r'treatment\s+failure', r'time\s+to\s+recovery',
        r'fever\s+clearance', r'time\s+to\s+defervescence',
    ],
    'endpoint_patterns': [
        (r'clinical\s+(?:cure|success|response|recovery)|(?:good|full|favou?rable)\s+(?:recovery|outcome)|'
         r'cure\s+rate', 'CLINICAL_CURE'),
        (r'(?:treatment|clinical|therapeutic|bacteriological|microbiological)\s+failure', 'TREATMENT_FAILURE'),
        (r'csf\s+(?:steril[iz]|clearance|culture\s+conversion)|'
         r'cerebrospinal\s+fluid\s+steril|(?:bacteriological|microbiological)\s+clearance|'
         r'culture\s+conversion', 'CSF_STERILIZATION'),
        (r'time\s+to\s+(?:clinical\s+)?recovery|fever\s+clearance\s+time|'
         r'time\s+to\s+defervescence|duration\s+of\s+fever|'
         r'time\s+to\s+(?:resolution|normali[sz]ation)', 'TIME_TO_RECOVERY'),
    ],
    'context_patterns': [
        r'per[- ]protocol|intention[- ]to[- ]treat', r'lumbar\s+puncture',
        r'culture[- ]confirmed', r'gram[- ]stain', r'\bMIC\b|minimum\s+inhibitory',
    ]
}


# ============================================================
# VACCINE PATTERNS (prevention)
# ============================================================

VACCINE_PATTERNS = {
    'detection_keywords': [
        r'meningococcal\s+(?:a\s+)?conjugate\s+vaccine|menafrivac|\bmena[- ]?tt\b',
        r'\bmenacwy\b|\bmenc\b|\bmenb\b|4cmenb|bexsero|menveo|nimenrix',
        r'pneumococcal\s+conjugate\s+vaccine|\bpcv1[03]\b|\bpcv\b|prevnar|synflorix',
        r'\bhib\b|haemophilus\s+influenzae\s+type\s+b',
        r'polysaccharide\s+vaccine', r'vaccine\s+efficacy|protective\s+efficacy',
        r'seroconversion', r'serum\s+bactericidal|\bsba\b|\brsba\b|\bhsba\b',
        r'immunogenicity', r'geometric\s+mean\s+tit', r'nasopharyngeal\s+carriage',
    ],
    'endpoint_patterns': [
        (r'(?:laboratory[- ]|culture[- ])?confirmed\s+meningitis|bacterial\s+meningitis|'
         r'meningococcal\s+meningitis|invasive\s+(?:meningococcal|pneumococcal)\s+disease|'
         r'meningococcal\s+disease|meningitis\s+incidence|incident\s+meningitis|'
         r'incidence\s+of\s+meningitis', 'MENINGITIS_INCIDENCE'),
        (r'vaccine\s+(?:efficacy|effectiveness)|protective\s+efficacy|'
         r'efficacy\s+against\s+(?:meningitis|invasive)', 'VACCINE_EFFICACY'),
        (r'seroconversion|sero[- ]?response|four[- ]?fold\s+rise|protective\s+tit(?:re|er)',
         'SEROCONVERSION'),
        (r'serum\s+bactericidal\s+antibody|\b[rh]?sba\s+(?:gmt|tit)|geometric\s+mean\s+(?:tit|concentration)|'
         r'\bgmt\b|\bgmc\b|immunogenicity|antibody\s+tit(?:re|er)', 'IMMUNOGENICITY'),
        (r'(?:nasopharyngeal|pharyngeal|oropharyngeal|meningococcal)\s+carriage|'
         r'carriage\s+(?:prevalence|acquisition)', 'CARRIAGE'),
    ],
    'context_patterns': [
        r'per\s+(?:100,?000\s+)?person[- ]years', r'incidence\s+rate\s+ratio|\birr\b',
        r'\bsba\b|bactericidal\s+titre', r'cases\s+per\s+\d',
    ]
}


# ============================================================
# MORTALITY PATTERNS
# ============================================================

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'(?:all[- ]cause\s+)?mortality', r'case\s+fatality', r'\bdeath\b|\bdied\b',
        r'in[- ]hospital\s+(?:mortality|death)', r'fatal\s+outcome', r'survival',
    ],
    'endpoint_patterns': [
        (r'(?:all[- ]cause\s+|overall\s+|in[- ]hospital\s+)?mortality|case\s+fatality|'
         r'\bdeath\b|\bdied\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'day\s+(?:28|30)\s+mortality', r'at\s+discharge', r'follow[- ]up',
    ]
}


# ============================================================
# SEQUELAE PATTERNS (neurological)
# ============================================================

SEQUELAE_PATTERNS = {
    'detection_keywords': [
        r'(?:sensorineural\s+)?hearing\s+(?:loss|impairment)|deafness',
        r'neurological\s+sequela[e]?|neurologic\s+sequela[e]?|focal\s+(?:neurological\s+)?deficit',
        r'seizures?|convulsions?|epilepsy',
        r'hydrocephalus', r'neurodevelopmental\s+impairment|developmental\s+delay',
        r'cognitive\s+impairment', r'\bsequelae\b',
    ],
    'endpoint_patterns': [
        (r'(?:sensorineural\s+|severe\s+|profound\s+)?hearing\s+(?:loss|impairment)|deafness|'
         r'auditory\s+impairment', 'HEARING_LOSS'),
        (r'neurological?\s+sequela[e]?|neurologic\s+sequela[e]?|'
         r'focal\s+(?:neurological\s+)?deficit|neurological\s+(?:deficit|complication)|'
         r'(?:any|major)\s+sequelae', 'NEUROLOGICAL_SEQUELAE'),
        (r'seizures?|convulsions?|epilepsy', 'SEIZURES'),
        (r'hydrocephalus', 'HYDROCEPHALUS'),
        (r'neurodevelopmental\s+(?:impairment|sequelae)|developmental\s+(?:delay|impairment)|'
         r'cognitive\s+impairment|intellectual\s+disability|psychomotor\s+delay',
         'NEURODEVELOPMENTAL_IMPAIRMENT'),
    ],
    'context_patterns': [
        r'audiometry|auditory\s+brainstem', r'at\s+(?:discharge|follow[- ]up)',
        r'long[- ]term\s+outcome',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_meningitis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect meningitis trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: treatment, vaccine, mortality, sequelae, general_meningitis."""
    text_lower = text.lower()
    scores = {'treatment': 0, 'vaccine': 0, 'mortality': 0, 'sequelae': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in VACCINE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['vaccine'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    for kw in SEQUELAE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['sequelae'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_meningitis', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_meningitis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'vaccine': VACCINE_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
        'sequelae': SEQUELAE_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_meningitis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical meningitis endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in MENINGITIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
