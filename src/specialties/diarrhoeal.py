"""
Diarrhoeal Disease Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV and
typhoid profiles. Diarrhoeal disease (acute watery / dysenteric childhood
diarrhoea, rotavirus) is the second-leading infectious cause of under-5 mortality
worldwide and an Africa-priority topic; its RCTs report a distinct endpoint
vocabulary the generic effect-size engine does not recognise on its own.

Subspecialties:
- Rehydration (ORS / zinc): rehydration / treatment failure (need for IV),
  stool output / volume, ORS intake, vomiting. Interventions: oral rehydration
  solution (standard / reduced-osmolarity / hypo-osmolar / rice-based), zinc
  (sulphate / acetate / gluconate), probiotics, racecadotril, smectite.
- Rotavirus (vaccine / prevention): rotavirus gastroenteritis incidence, severe
  rotavirus gastroenteritis, vaccine efficacy, anti-rotavirus IgA seroconversion
  / immunogenicity (GMC/GMT). Vaccines: Rotarix (RV1), RotaTeq (RV5), Rotavac,
  Rotasiil.
- Treatment (antibiotics / antimicrobials for dysentery & invasive diarrhoea):
  clinical cure, bacteriological/microbiological cure, treatment failure, time to
  resolution. Drugs: azithromycin, ciprofloxacin, ceftriaxone, cefixime,
  nalidixic acid, co-trimoxazole, metronidazole, erythromycin.
- Mortality / duration (the childhood-mortality core): duration of diarrhoea,
  stool frequency, mortality / case fatality, hospitalisation, dehydration,
  persistent diarrhoea.

Effect measures follow what these trials report: binary (failure, cure,
vomiting, dehydration, persistent diarrhoea, mortality) -> RR/OR/RD; incidence
(rotavirus GE, hospitalisation) -> IRR/HR; continuous (duration, stool output,
stool frequency, ORS intake, time to resolution) -> MD/SMD; anti-rotavirus IgA
titres -> GMR, log-normal.

British / American spelling: "diarrhoea" inserts an extra 'o' before "ea"
relative to "diarrhea", so every alias/pattern uses `diarrho?ea` (and
`diarrho?eal?` for the adjective) to match BOTH forms -- per the lessons-file
double-vowel rule.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# DIARRHOEAL ENDPOINTS
# ============================================================

DIARRHOEAL_ENDPOINTS = {
    # --- Rehydration (ORS / zinc) ---
    'REHYDRATION_FAILURE': {
        'aliases': ['rehydration failure', 'treatment failure', 'ors failure',
                    'failure of oral rehydration', 'failure of ors',
                    'need for intravenous rehydration', 'need for iv rehydration',
                    'unscheduled intravenous', 'unscheduled iv', 'need for iv fluids'],
        'subspecialty': 'rehydration',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'STOOL_OUTPUT': {
        'aliases': ['stool output', 'stool volume', 'stool weight',
                    'total stool output', 'total stool volume',
                    'stool output volume', 'faecal output', 'fecal output'],
        'subspecialty': 'rehydration',
        'measure_types': ['MD', 'SMD']
    },
    'ORS_INTAKE': {
        'aliases': ['ors intake', 'ors volume', 'ors consumption',
                    'oral rehydration solution intake', 'fluid intake'],
        'subspecialty': 'rehydration',
        'measure_types': ['MD', 'SMD']
    },
    'VOMITING': {
        'aliases': ['vomiting', 'emesis', 'persistent vomiting', 'vomiting episodes'],
        'subspecialty': 'rehydration',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Rotavirus (vaccine / prevention) ---
    'SEVERE_RV_GE': {
        'aliases': ['severe rotavirus gastroenteritis', 'severe rotavirus diarrhoea',
                    'severe rotavirus diarrhea', 'severe rotavirus disease'],
        'subspecialty': 'rotavirus',
        'measure_types': ['IRR', 'HR', 'RR']
    },
    'ROTAVIRUS_GE': {
        'aliases': ['rotavirus gastroenteritis', 'rotavirus diarrhoea',
                    'rotavirus diarrhea', 'rotavirus disease', 'rv gastroenteritis',
                    'incidence of rotavirus', 'rotavirus infection'],
        'subspecialty': 'rotavirus',
        'measure_types': ['IRR', 'HR', 'RR']
    },
    'RV_VACCINE_EFFICACY': {
        'aliases': ['vaccine efficacy', 'protective efficacy',
                    'efficacy against rotavirus', 'efficacy against severe rotavirus',
                    'efficacy against severe rotavirus gastroenteritis'],
        'subspecialty': 'rotavirus',
        'measure_types': ['HR', 'IRR', 'RR']
    },
    'RV_SEROCONVERSION': {
        'aliases': ['seroconversion', 'seroconversion rate', 'iga seroconversion',
                    'anti-rotavirus iga seroconversion', 'four-fold rise',
                    'fourfold rise', 'seroresponse', 'sero-response rate'],
        'subspecialty': 'rotavirus',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RV_IMMUNOGENICITY': {
        'aliases': ['anti-rotavirus iga', 'rotavirus iga', 'iga geometric mean',
                    'geometric mean titer', 'geometric mean titre', 'gmt',
                    'geometric mean concentration', 'gmc', 'immunogenicity',
                    'iga antibody titre', 'iga antibody titer'],
        'subspecialty': 'rotavirus',
        'measure_types': ['GMR', 'MD', 'SMD']
    },

    # --- Treatment (antibiotics / antimicrobials) ---
    'CLINICAL_CURE': {
        'aliases': ['clinical cure', 'clinical success', 'clinical response',
                    'clinical resolution', 'cure rate', 'overall cure',
                    'favourable clinical outcome', 'favorable clinical outcome'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BACTERIOLOGICAL_CURE': {
        'aliases': ['bacteriological cure', 'microbiological cure',
                    'bacteriological clearance', 'microbiological clearance',
                    'stool culture clearance', 'stool culture conversion',
                    'pathogen eradication', 'bacteriological eradication'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TREATMENT_FAILURE': {
        'aliases': ['treatment failure', 'clinical failure', 'microbiological failure',
                    'bacteriological failure', 'therapeutic failure'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'TIME_TO_RESOLUTION': {
        'aliases': ['time to resolution of diarrhoea', 'time to resolution of diarrhea',
                    'time to cessation of diarrhoea', 'time to cessation of diarrhea',
                    'time to first formed stool', 'time to last unformed stool',
                    'time to last loose stool', 'time to recovery'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD', 'HR']
    },

    # --- Mortality / duration (childhood-mortality core) ---
    'DIARRHOEA_DURATION': {
        'aliases': ['duration of diarrhoea', 'duration of diarrhea',
                    'diarrhoeal duration', 'diarrheal duration', 'diarrhoea duration',
                    'diarrhea duration', 'duration of illness', 'illness duration'],
        'subspecialty': 'mortality_duration',
        'measure_types': ['MD', 'SMD']
    },
    'STOOL_FREQUENCY': {
        'aliases': ['stool frequency', 'number of stools', 'number of motions',
                    'frequency of diarrhoea', 'frequency of diarrhea',
                    'frequency of stools', 'stools per day', 'stool frequency per day'],
        'subspecialty': 'mortality_duration',
        'measure_types': ['MD', 'SMD', 'IRR']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'case fatality',
                    'case fatality rate', 'diarrhoea-related death',
                    'diarrhea-related death', 'in-hospital mortality'],
        'subspecialty': 'mortality_duration',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HOSPITALIZATION': {
        'aliases': ['hospitalization', 'hospitalisation', 'hospital admission',
                    'hospital admissions', 'admission to hospital',
                    'admission for diarrhoea', 'admission for diarrhea',
                    'diarrhoea hospitalisation', 'diarrhea hospitalization'],
        'subspecialty': 'mortality_duration',
        'measure_types': ['RR', 'OR', 'IRR']
    },
    'DEHYDRATION': {
        'aliases': ['dehydration', 'severe dehydration', 'moderate dehydration',
                    'moderate to severe dehydration', 'some dehydration'],
        'subspecialty': 'mortality_duration',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PERSISTENT_DIARRHOEA': {
        'aliases': ['persistent diarrhoea', 'persistent diarrhea',
                    'prolonged diarrhoea', 'prolonged diarrhea',
                    'persistent diarrhoeal illness'],
        'subspecialty': 'mortality_duration',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# REHYDRATION PATTERNS (ORS / zinc)
# ============================================================

REHYDRATION_PATTERNS = {
    'detection_keywords': [
        r'oral\s+rehydration', r'\bors\b', r'reduced[- ]osmolarity',
        r'hypo[- ]?osmolar', r'rice[- ]based\s+(?:ors|oral)', r'\bzinc\b',
        r'zinc\s+(?:sulphate|sulfate|acetate|gluconate)', r'racecadotril',
        r'probiotic', r'lactobacillus', r'saccharomyces\s+boulardii',
        r'smectite|diosmectite', r'rehydration\s+(?:failure|therapy)',
        r'stool\s+(?:output|volume|weight)',
    ],
    'endpoint_patterns': [
        (r'rehydration\s+failure|failure\s+of\s+(?:oral\s+rehydration|ors)|'
         r'\bors\s+failure|need\s+for\s+(?:intravenous|iv)\s+(?:rehydration|fluids?)|'
         r'unscheduled\s+(?:intravenous|iv)', 'REHYDRATION_FAILURE'),
        (r'(?:total\s+)?stool\s+(?:output|volume|weight)|fa?ecal\s+output',
         'STOOL_OUTPUT'),
        (r'\bors\s+(?:intake|volume|consumption)|oral\s+rehydration\s+solution\s+intake|'
         r'fluid\s+intake', 'ORS_INTAKE'),
        (r'vomiting|emesis', 'VOMITING'),
    ],
    'context_patterns': [
        r'ml\s*/\s*kg', r'g\s*/\s*kg', r'per[- ]protocol|intention[- ]to[- ]treat',
        r'acute\s+(?:watery\s+)?diarrho?ea',
    ]
}


# ============================================================
# ROTAVIRUS PATTERNS (vaccine / prevention)
# ============================================================

ROTAVIRUS_PATTERNS = {
    'detection_keywords': [
        r'rotavirus', r'rotarix|\brv1\b', r'rotateq|\brv5\b', r'rotavac',
        r'rotasiil', r'anti[- ]rotavirus', r'rotavirus\s+vaccine',
        r'seroconversion', r'\biga\b', r'geometric\s+mean\s+(?:tit|concentration)',
        r'vaccine\s+efficacy|protective\s+efficacy',
    ],
    'endpoint_patterns': [
        (r'severe\s+rotavirus\s+(?:gastroenteritis|diarrho?ea|disease)', 'SEVERE_RV_GE'),
        (r'(?<!severe )rotavirus\s+(?:gastroenteritis|diarrho?ea|disease|infection)|'
         r'\brv\s+gastroenteritis|incidence\s+of\s+rotavirus', 'ROTAVIRUS_GE'),
        (r'vaccine\s+efficacy|protective\s+efficacy|efficacy\s+against\s+(?:severe\s+)?rotavirus',
         'RV_VACCINE_EFFICACY'),
        (r'(?:iga\s+|anti[- ]rotavirus\s+iga\s+)?seroconversion|four[- ]?fold\s+rise|'
         r'seroresponse', 'RV_SEROCONVERSION'),
        (r'anti[- ]rotavirus\s+iga|rotavirus\s+iga|iga\s+(?:geometric|titre|titer)|'
         r'geometric\s+mean\s+(?:tit|concentration)|\bgmt\b|\bgmc\b|immunogenicity',
         'RV_IMMUNOGENICITY'),
    ],
    'context_patterns': [
        r'per[- ]protocol', r'incidence\s+rate\s+ratio|\birr\b',
        r'u\/ml|elisa\s+unit|cases\s+per\s+\d', r'person[- ]years',
    ]
}


# ============================================================
# TREATMENT PATTERNS (antibiotics / antimicrobials)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'azithromycin', r'ciprofloxacin', r'ofloxacin', r'ceftriaxone',
        r'cefixime', r'nalidixic\s+acid', r'co[- ]?trimoxazole|trimethoprim',
        r'metronidazole', r'erythromycin', r'dysentery', r'shigell',
        r'campylobacter', r'\bvibrio\b', r'bloody\s+diarrho?ea',
        r'(?:bacteriological|microbiological)\s+(?:cure|clearance)',
        r'clinical\s+cure', r'antibiotic',
    ],
    'endpoint_patterns': [
        (r'clinical\s+(?:cure|success|response|resolution)|cure\s+rate', 'CLINICAL_CURE'),
        (r'(?:bacteriological|microbiological)\s+(?:cure|clearance|eradication)|'
         r'stool\s+culture\s+(?:clearance|conversion)|pathogen\s+eradication',
         'BACTERIOLOGICAL_CURE'),
        (r'(?:treatment|clinical|microbiological|bacteriological|therapeutic)\s+failure',
         'TREATMENT_FAILURE'),
        (r'time\s+to\s+(?:resolution|cessation)\s+of\s+diarrho?ea|'
         r'time\s+to\s+(?:first\s+formed|last\s+(?:un|loose))\s+stool|'
         r'time\s+to\s+recovery', 'TIME_TO_RESOLUTION'),
    ],
    'context_patterns': [
        r'per[- ]protocol|intention[- ]to[- ]treat', r'\bMIC\b|minimum\s+inhibitory',
        r'stool\s+culture', r'antimicrobial\s+susceptibility',
    ]
}


# ============================================================
# MORTALITY / DURATION PATTERNS (childhood-mortality core)
# ============================================================

MORTALITY_DURATION_PATTERNS = {
    'detection_keywords': [
        r'duration\s+of\s+(?:diarrho?ea|illness)', r'diarrho?eal?\s+duration',
        r'stool\s+frequency', r'number\s+of\s+stools', r'stools?\s+per\s+day',
        r'(?:all[- ]cause\s+)?mortality', r'case\s+fatality', r'\bdeath\b',
        r'hospitali[sz]ation|hospital\s+admission', r'dehydration',
        r'persistent\s+diarrho?ea|prolonged\s+diarrho?ea',
        r'time\s+to\s+recovery',
    ],
    'endpoint_patterns': [
        (r'duration\s+of\s+(?:diarrho?ea|illness)|diarrho?eal?\s+duration|'
         r'illness\s+duration', 'DIARRHOEA_DURATION'),
        (r'stool\s+frequency|number\s+of\s+(?:stools|motions)|'
         r'frequency\s+of\s+(?:diarrho?ea|stools)|stools?\s+per\s+day', 'STOOL_FREQUENCY'),
        (r'(?:all[- ]cause\s+)?mortality|case\s+fatality|\bdeath\b|'
         r'diarrho?ea[- ]related\s+death', 'MORTALITY'),
        (r'hospitali[sz]ation|hospital\s+admission|admission\s+(?:to\s+hospital|'
         r'for\s+diarrho?ea)', 'HOSPITALIZATION'),
        (r'(?:severe\s+|moderate(?:[- ]to[- ]severe)?\s+|some\s+)?dehydration', 'DEHYDRATION'),
        (r'persistent\s+diarrho?ea|prolonged\s+diarrho?ea', 'PERSISTENT_DIARRHOEA'),
    ],
    'context_patterns': [
        r'under[- ]?(?:five|5)|children\s+aged', r'days?\b', r'intensive\s+care',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_diarrhoeal_subspecialty(text: str) -> Tuple[str, float]:
    """Detect diarrhoeal-disease trial subspecialty. Returns (subspecialty,
    confidence). Subspecialties: rehydration, rotavirus, treatment,
    mortality_duration, general_diarrhoeal."""
    text_lower = text.lower()
    scores = {'rehydration': 0, 'rotavirus': 0, 'treatment': 0, 'mortality_duration': 0}
    for kw in REHYDRATION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['rehydration'] += 1
    for kw in ROTAVIRUS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['rotavirus'] += 1
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in MORTALITY_DURATION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality_duration'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_diarrhoeal', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_diarrhoeal_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'rehydration': REHYDRATION_PATTERNS['endpoint_patterns'],
        'rotavirus': ROTAVIRUS_PATTERNS['endpoint_patterns'],
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'mortality_duration': MORTALITY_DURATION_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_diarrhoeal_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical diarrhoeal endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in DIARRHOEAL_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
