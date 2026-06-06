"""
Cholera (Vibrio cholerae) Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV and
typhoid profiles. Cholera RCTs report a distinct endpoint vocabulary the generic
effect-size engine does not recognise on its own. Cholera is an Africa-priority
topic (recurrent outbreaks across sub-Saharan Africa) and a large, well-studied
RCT literature spanning antibiotic therapy, oral rehydration, and oral cholera
vaccines.

Subspecialties:
- Treatment (antibiotic therapy): clinical cure, bacteriological / stool-culture
  clearance, duration of diarrhoea, treatment failure, hospital stay. Drugs:
  doxycycline (incl. single-dose), azithromycin, ciprofloxacin, erythromycin,
  tetracycline, norfloxacin, furazolidone, co-trimoxazole, ampicillin,
  chloramphenicol.
- Rehydration (fluid / ORS therapy): total stool output, ORS / fluid intake,
  need for unscheduled IV fluid, vomiting. Arms: rice-based ORS, reduced-osmolarity
  (hypo-osmolar) ORS, standard / glucose ORS, Ringer's lactate.
- Vaccine (prevention): culture-confirmed cholera incidence, vaccine efficacy /
  effectiveness, vibriocidal seroconversion, vibriocidal antibody immunogenicity
  (GMT). Vaccines: oral cholera vaccine (OCV) — Dukoral (WC-rBS), Shanchol,
  Euvichol(-Plus), Hillchol (BivWC killed whole-cell), CVD 103-HgR / Vaxchora.
- Severe (severe disease): severe dehydration, mortality / case fatality,
  hypovolaemic shock, acute kidney injury.

Effect measures follow what these trials report: binary (cure, clearance,
failure, seroconversion, severe dehydration, shock, death) -> RR/OR/RD; incidence
-> IRR/HR; continuous (duration of diarrhoea, stool output, ORS intake, hospital
stay) -> MD/SMD; vibriocidal titres -> GMR, log-normal.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# CHOLERA ENDPOINTS
# ============================================================

CHOLERA_ENDPOINTS = {
    # --- Antibiotic treatment efficacy ---
    'CLINICAL_CURE': {
        'aliases': ['clinical cure', 'clinical success', 'clinical response',
                    'clinical resolution', 'overall cure', 'cure rate',
                    'favourable clinical outcome', 'favorable clinical outcome'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BACTERIOLOGICAL_CLEARANCE': {
        'aliases': ['bacteriological cure', 'bacteriological clearance',
                    'bacteriologic cure', 'bacteriological success',
                    'bacteriological eradication', 'stool culture clearance',
                    'stool culture conversion', 'culture conversion',
                    'vibrio clearance', 'vibrio eradication',
                    'negative stool culture'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'DIARRHEA_DURATION': {
        'aliases': ['duration of diarrhoea', 'duration of diarrhea',
                    'duration of purging', 'duration of illness',
                    'diarrhoea duration', 'diarrhea duration',
                    'time to cessation of diarrhoea',
                    'time to cessation of diarrhea',
                    'time to resolution of diarrhoea'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'TREATMENT_FAILURE': {
        'aliases': ['treatment failure', 'clinical failure',
                    'bacteriological failure', 'therapeutic failure',
                    'overall treatment failure'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'HOSPITAL_STAY': {
        'aliases': ['length of hospital stay', 'duration of hospitalization',
                    'duration of hospitalisation', 'length of stay', 'hospital stay',
                    'hospitalization duration', 'time to discharge'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },

    # --- Rehydration (fluid / ORS therapy) ---
    'STOOL_OUTPUT': {
        'aliases': ['total stool output', 'stool output', 'stool volume',
                    'stool weight', 'purging volume', 'diarrhoeal stool output',
                    'diarrheal stool output', 'rate of stool output',
                    'mean stool output'],
        'subspecialty': 'rehydration',
        'measure_types': ['MD', 'SMD']
    },
    'ORS_INTAKE': {
        'aliases': ['ors intake', 'ors volume', 'oral rehydration solution intake',
                    'oral rehydration solution volume', 'total fluid intake',
                    'fluid intake', 'rehydration fluid intake'],
        'subspecialty': 'rehydration',
        'measure_types': ['MD', 'SMD']
    },
    'UNSCHEDULED_IV': {
        'aliases': ['unscheduled intravenous', 'unscheduled iv',
                    'need for intravenous', 'need for iv fluid',
                    'additional intravenous', 'rescue intravenous',
                    'intravenous fluid requirement', 'unscheduled intravenous fluid'],
        'subspecialty': 'rehydration',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'VOMITING': {
        'aliases': ['vomiting', 'emesis', 'vomiting episodes',
                    'persistent vomiting'],
        'subspecialty': 'rehydration',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Vaccine (prevention) ---
    'CHOLERA_INCIDENCE': {
        'aliases': ['culture-confirmed cholera', 'culture confirmed cholera',
                    'confirmed cholera', 'cholera incidence', 'incident cholera',
                    'incidence of cholera', 'cholera episode', 'cholera case',
                    'first episode of cholera', 'severe cholera', 'cholera'],
        'subspecialty': 'vaccine',
        'measure_types': ['IRR', 'HR', 'RR']
    },
    'VACCINE_EFFICACY': {
        'aliases': ['vaccine efficacy', 'protective efficacy',
                    'vaccine effectiveness', 'efficacy against cholera',
                    'protection against cholera', 'cumulative efficacy'],
        'subspecialty': 'vaccine',
        'measure_types': ['HR', 'IRR', 'RR']
    },
    'VIBRIOCIDAL_SEROCONVERSION': {
        'aliases': ['vibriocidal seroconversion', 'seroconversion',
                    'vibriocidal seroresponse', 'seroresponse',
                    'four-fold rise', 'fourfold rise', 'seroconversion rate'],
        'subspecialty': 'vaccine',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'IMMUNOGENICITY': {
        'aliases': ['vibriocidal antibody titre', 'vibriocidal antibody titer',
                    'vibriocidal titre', 'vibriocidal titer',
                    'vibriocidal geometric mean', 'geometric mean titre',
                    'geometric mean titer', 'gmt', 'anti-lps igg', 'anti-lps',
                    'anti-ctb', 'anti-cholera toxin', 'immunogenicity'],
        'subspecialty': 'vaccine',
        'measure_types': ['GMR', 'MD', 'SMD']
    },

    # --- Severe disease ---
    'SEVERE_DEHYDRATION': {
        'aliases': ['severe dehydration', 'severe dehydrating diarrhoea',
                    'severe dehydrating diarrhea', 'severe volume depletion'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'case fatality',
                    'case fatality rate', 'cholera-related death',
                    'in-hospital mortality'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HYPOVOLEMIC_SHOCK': {
        'aliases': ['hypovolemic shock', 'hypovolaemic shock',
                    'circulatory collapse', 'shock'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ACUTE_KIDNEY_INJURY': {
        'aliases': ['acute kidney injury', 'acute renal failure',
                    'acute kidney failure', 'renal failure'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# TREATMENT PATTERNS (antibiotic therapy)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'doxycycline', r'azithromycin', r'ciprofloxacin', r'erythromycin',
        r'tetracycline', r'norfloxacin', r'furazolidone', r'ampicillin',
        r'chloramphenicol', r'co[- ]?trimoxazole|trimethoprim',
        r'single[- ]dose\s+doxycycline', r'antibiotic',
        r'bacteriolog(?:ical|ic)\s+(?:cure|clearance|failure)',
        r'stool\s+culture', r'clinical\s+cure', r'duration\s+of\s+diarrh',
    ],
    'endpoint_patterns': [
        (r'clinical\s+(?:cure|success|response|resolution)|cure\s+rate', 'CLINICAL_CURE'),
        (r'bacteriolog(?:ical|ic)\s+(?:cure|clearance|success|eradication)|'
         r'stool\s+culture\s+(?:clearance|conversion|cure)|culture\s+conversion|'
         r'vibrio\s+(?:clearance|eradication)|negative\s+stool\s+culture',
         'BACTERIOLOGICAL_CLEARANCE'),
        (r'duration\s+of\s+(?:diarrh(?:oea|ea)|purging|illness)|'
         r'diarrh(?:oea|ea)\s+duration|'
         r'time\s+to\s+(?:cessation|resolution)\s+of\s+diarrh(?:oea|ea)',
         'DIARRHEA_DURATION'),
        (r'(?:treatment|clinical|bacteriological|therapeutic)\s+failure', 'TREATMENT_FAILURE'),
        (r'length\s+of\s+(?:hospital\s+)?stay|duration\s+of\s+hospitali[sz]ation|'
         r'time\s+to\s+discharge', 'HOSPITAL_STAY'),
    ],
    'context_patterns': [
        r'per[- ]protocol|intention[- ]to[- ]treat', r'culture[- ]confirmed',
        r'\bMIC\b|minimum\s+inhibitory', r'single[- ]dose',
    ]
}


# ============================================================
# REHYDRATION PATTERNS (fluid / ORS therapy)
# ============================================================

REHYDRATION_PATTERNS = {
    'detection_keywords': [
        r'oral\s+rehydration', r'\bors\b', r'rice[- ]based',
        r'reduced[- ]osmolarity|hypo[- ]?osmolar|low[- ]osmolarity',
        r'glucose[- ]based\s+(?:ors|solution)', r'ringer', r'rehydration',
        r'stool\s+output|purging\s+(?:rate|volume)', r'\bresomal\b',
        r'intravenous\s+fluid|\biv\s+fluid',
    ],
    'endpoint_patterns': [
        (r'(?:total\s+|rate\s+of\s+|mean\s+)?stool\s+(?:output|volume|weight)|'
         r'purging\s+(?:volume|rate)|diarrh(?:oea|ea)l\s+stool\s+output',
         'STOOL_OUTPUT'),
        (r'ors\s+(?:intake|volume)|oral\s+rehydration\s+solution\s+(?:intake|volume)|'
         r'(?:total\s+)?fluid\s+intake|rehydration\s+fluid\s+intake', 'ORS_INTAKE'),
        (r'unscheduled\s+(?:intravenous|iv)|need\s+for\s+(?:intravenous|iv)\b|'
         r'additional\s+(?:intravenous|iv)|rescue\s+(?:intravenous|iv)|'
         r'intravenous\s+fluid\s+requirement', 'UNSCHEDULED_IV'),
        (r'vomiting|emesis', 'VOMITING'),
    ],
    'context_patterns': [
        r'ml/kg|millilit', r'osmolarity', r'per\s+kg\s+(?:body\s+)?weight',
    ]
}


# ============================================================
# VACCINE PATTERNS (prevention)
# ============================================================

VACCINE_PATTERNS = {
    'detection_keywords': [
        r'oral\s+cholera\s+vaccine|\bocv\b', r'dukoral|wc[- ]?rbs',
        r'shanchol', r'euvichol', r'hillchol|\bbivwc\b',
        r'killed\s+whole[- ]cell', r'cvd\s*103|vaxchora',
        r'vaccine\s+(?:efficacy|effectiveness)|protective\s+efficacy',
        r'vibriocidal', r'seroconversion', r'immunogenicity',
    ],
    'endpoint_patterns': [
        (r'culture[- ]confirmed\s+cholera|confirmed\s+cholera|'
         r'cholera\s+(?:incidence|episode|case)|incidence\s+of\s+cholera|'
         r'incident\s+cholera|severe\s+cholera', 'CHOLERA_INCIDENCE'),
        (r'vaccine\s+(?:efficacy|effectiveness)|protective\s+efficacy|'
         r'efficacy\s+against\s+cholera|protection\s+against\s+cholera',
         'VACCINE_EFFICACY'),
        (r'vibriocidal\s+seroconversion|seroconversion|four[- ]?fold\s+rise|'
         r'seroresponse', 'VIBRIOCIDAL_SEROCONVERSION'),
        (r'vibriocidal\s+(?:antibody\s+)?(?:tit(?:re|er)|geometric)|'
         r'geometric\s+mean\s+tit(?:re|er)|\bgmt\b|anti[- ]lps|anti[- ]ctb|'
         r'immunogenicity', 'IMMUNOGENICITY'),
    ],
    'context_patterns': [
        r'per\s+(?:100,?000\s+)?person[- ]years', r'incidence\s+rate\s+ratio|\birr\b',
        r'cases\s+per\s+\d', r'El\s+Tor|Ogawa|Inaba',
    ]
}


# ============================================================
# SEVERE PATTERNS (severe disease)
# ============================================================

SEVERE_PATTERNS = {
    'detection_keywords': [
        r'severe\s+dehydrat', r'hypovol[ae]?emic\s+shock|circulatory\s+collapse',
        r'acute\s+kidney\s+injury|acute\s+renal\s+failure',
        r'(?:case\s+)?fatality|mortality', r'severe\s+cholera',
        r'volume\s+depletion',
    ],
    'endpoint_patterns': [
        (r'severe\s+dehydrat(?:ion|ing)|severe\s+volume\s+depletion',
         'SEVERE_DEHYDRATION'),
        (r'(?:all[- ]cause\s+)?mortality|case\s+fatality|\bdeath\b', 'MORTALITY'),
        (r'hypovol[ae]?emic\s+shock|circulatory\s+collapse|\bshock\b',
         'HYPOVOLEMIC_SHOCK'),
        (r'acute\s+kidney\s+injury|acute\s+renal\s+failure|renal\s+failure',
         'ACUTE_KIDNEY_INJURY'),
    ],
    'context_patterns': [
        r'intensive\s+care', r'dehydration\s+(?:status|severity)', r'\bWHO\s+plan\b',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_cholera_subspecialty(text: str) -> Tuple[str, float]:
    """Detect cholera trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: treatment, rehydration, vaccine, severe, general_cholera."""
    text_lower = text.lower()
    scores = {'treatment': 0, 'rehydration': 0, 'vaccine': 0, 'severe': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in REHYDRATION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['rehydration'] += 1
    for kw in VACCINE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['vaccine'] += 1
    for kw in SEVERE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['severe'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_cholera', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_cholera_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'rehydration': REHYDRATION_PATTERNS['endpoint_patterns'],
        'vaccine': VACCINE_PATTERNS['endpoint_patterns'],
        'severe': SEVERE_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_cholera_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical cholera endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in CHOLERA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
