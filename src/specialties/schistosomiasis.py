"""
Schistosomiasis (bilharzia) Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV and
typhoid profiles. Schistosomiasis (Schistosoma haematobium / mansoni / japonicum)
RCTs report a distinct endpoint vocabulary the generic effect-size engine does not
recognise on its own. Schistosomiasis is a top-priority African neglected tropical
disease: ~90% of the global burden is in sub-Saharan Africa.

Subspecialties:
- Treatment (anthelmintic therapy): parasitological cure, egg reduction rate (ERR),
  egg count / infection intensity, treatment failure. Drugs: praziquantel (the
  mainstay), artemisinin derivatives (artesunate, artemether), oxamniquine,
  mefloquine, often co-administered with albendazole/mebendazole.
- Prevention / control (preventive chemotherapy / MDA): infection prevalence and
  prevalence reduction, reinfection / incidence of infection, heavy-intensity
  infection.
- Morbidity (chronic disease): hepatosplenic disease / periportal (liver) fibrosis
  (S. mansoni, S. japonicum), haematuria and urinary-tract / bladder pathology
  (S. haematobium), anaemia.
- Vaccine (prevention): protective efficacy, immunogenicity / antibody response
  (anti-Sh28GST, anti-Sm14), seroconversion. Candidates: Sh28GST (Bilhvax),
  Sm14, Sm-TSP-2.

Effect measures follow what these trials report: binary (cure, failure, prevalence,
reinfection, haematuria, fibrosis) -> RR/OR/RD; incidence/reinfection -> IRR/HR;
continuous (egg counts, egg reduction rate, haemoglobin -> MD/SMD; egg counts and
antibody titres are right-skewed -> log scale / GMR).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# SCHISTOSOMIASIS ENDPOINTS
# ============================================================

SCHISTOSOMIASIS_ENDPOINTS = {
    # --- Anthelmintic treatment efficacy ---
    'PARASITOLOGICAL_CURE': {
        'aliases': ['parasitological cure', 'parasitologic cure', 'cure rate',
                    'parasitological clearance', 'parasitological response',
                    'egg-negative', 'egg negative', 'negative conversion',
                    'parasitological cure rate', 'cured'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'EGG_REDUCTION_RATE': {
        'aliases': ['egg reduction rate', 'egg reduction', 'egg count reduction',
                    'reduction in egg count', 'reduction in egg counts',
                    'geometric mean egg reduction', 'egg reduction ratio',
                    'mean egg reduction'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'EGG_COUNT': {
        'aliases': ['egg count', 'egg counts', 'eggs per gram', 'eggs per gramme',
                    'mean egg count', 'geometric mean egg count', 'eggs per 10 ml',
                    'eggs per 10 millilitres', 'infection intensity',
                    'intensity of infection'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'TREATMENT_FAILURE': {
        'aliases': ['treatment failure', 'parasitological failure', 'therapeutic failure',
                    'clinical failure', 'overall treatment failure'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Prevention / control (preventive chemotherapy / MDA) ---
    'INFECTION_PREVALENCE': {
        'aliases': ['infection prevalence', 'prevalence of infection', 'prevalence',
                    'prevalence reduction', 'reduction in prevalence',
                    'schistosomiasis prevalence', 'prevalence of schistosomiasis'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'REINFECTION': {
        'aliases': ['reinfection', 're-infection', 'reinfection rate',
                    'incidence of infection', 'incident infection', 'new infection',
                    'infection incidence'],
        'subspecialty': 'prevention',
        'measure_types': ['IRR', 'HR', 'RR']
    },
    'HEAVY_INFECTION': {
        'aliases': ['heavy infection', 'heavy-intensity infection',
                    'heavy intensity infection', 'high-intensity infection',
                    'high intensity infection', 'heavy infection intensity'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Morbidity (chronic disease) ---
    'PERIPORTAL_FIBROSIS': {
        'aliases': ['periportal fibrosis', 'hepatic fibrosis', 'liver fibrosis',
                    'hepatosplenic disease', 'hepatosplenomegaly', 'hepatomegaly',
                    'splenomegaly', 'hepatosplenic schistosomiasis'],
        'subspecialty': 'morbidity',
        'measure_types': ['RR', 'OR']
    },
    'HAEMATURIA': {
        'aliases': ['haematuria', 'hematuria', 'microhaematuria', 'microhematuria',
                    'micro-haematuria', 'visible haematuria', 'macrohaematuria',
                    'blood in urine', 'gross haematuria'],
        'subspecialty': 'morbidity',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BLADDER_PATHOLOGY': {
        'aliases': ['bladder pathology', 'bladder wall', 'bladder lesion',
                    'urinary tract morbidity', 'urinary tract pathology',
                    'bladder abnormality', 'ultrasound abnormality',
                    'urinary tract lesion'],
        'subspecialty': 'morbidity',
        'measure_types': ['RR', 'OR']
    },
    'ANAEMIA': {
        'aliases': ['anaemia', 'anemia', 'haemoglobin', 'hemoglobin',
                    'haemoglobin concentration', 'hemoglobin concentration',
                    'anaemia prevalence'],
        'subspecialty': 'morbidity',
        'measure_types': ['RR', 'OR', 'MD']
    },

    # --- Vaccine (prevention) ---
    'VACCINE_EFFICACY': {
        'aliases': ['vaccine efficacy', 'protective efficacy',
                    'efficacy against infection', 'efficacy against schistosomiasis',
                    'protection against infection'],
        'subspecialty': 'vaccine',
        'measure_types': ['HR', 'IRR', 'RR']
    },
    'IMMUNOGENICITY': {
        'aliases': ['immunogenicity', 'antibody response', 'antibody titre',
                    'antibody titer', 'specific igg', 'igg response', 'igg antibody',
                    'geometric mean titre', 'geometric mean titer', 'gmt',
                    'anti-sh28gst', 'anti-sm14', 'igg geometric mean'],
        'subspecialty': 'vaccine',
        'measure_types': ['GMR', 'MD', 'SMD']
    },
    'SEROCONVERSION': {
        'aliases': ['seroconversion', 'seroconversion rate', 'seroresponse',
                    'sero-response rate', 'antibody response rate', 'four-fold rise',
                    'fourfold rise'],
        'subspecialty': 'vaccine',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# TREATMENT PATTERNS (anthelmintic therapy)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'praziquantel', r'\bpzq\b', r'artesunate', r'artemether', r'artemisinin',
        r'oxamniquine', r'mefloquine', r'albendazole', r'mebendazole',
        r'parasitological\s+cure', r'cure\s+rate', r'egg\s+reduction\s+rate',
        r'\berr\b', r'egg\s+count', r'eggs\s+per\s+gram', r'\bepg\b',
        r'kato[- ]?katz', r'infection\s+intensity', r'treatment\s+failure',
    ],
    'endpoint_patterns': [
        (r'parasitologic(?:al)?\s+(?:cure|clearance|response)|cure\s+rate|'
         r'egg[- ]negative|negative\s+conversion', 'PARASITOLOGICAL_CURE'),
        (r'egg\s+reduction\s+rate|\berr\b|egg\s+(?:count\s+)?reduction|'
         r'reduction\s+in\s+egg\s+counts?', 'EGG_REDUCTION_RATE'),
        (r'egg\s+counts?|eggs\s+per\s+gram|\bepg\b|eggs\s+per\s+10\s*ml|'
         r'(?:infection\s+intensity|intensity\s+of\s+infection)', 'EGG_COUNT'),
        (r'(?:treatment|parasitological|therapeutic|clinical)\s+failure', 'TREATMENT_FAILURE'),
    ],
    'context_patterns': [
        r'\d+\s*mg\/kg', r'kato[- ]?katz', r'\bweek\s+(?:3|4|6|8)\b',
        r'single\s+(?:oral\s+)?dose', r'geometric\s+mean',
    ]
}


# ============================================================
# PREVENTION PATTERNS (preventive chemotherapy / MDA / control)
# ============================================================

PREVENTION_PATTERNS = {
    'detection_keywords': [
        r'mass\s+drug\s+administration|\bmda\b', r'preventive\s+chemotherapy',
        r'prevalence\s+(?:of\s+)?(?:infection|schistosomiasis)', r'reinfection|re[- ]infection',
        r'snail\s+control', r'school[- ]based\s+treatment', r'community[- ]wide\s+treatment',
        r'incidence\s+of\s+infection', r'heavy[- ]intensity\s+infection', r'transmission',
    ],
    'endpoint_patterns': [
        (r'(?:infection\s+)?prevalence(?:\s+(?:of|reduction))?|reduction\s+in\s+prevalence',
         'INFECTION_PREVALENCE'),
        (r're[- ]?infection|incidence\s+of\s+infection|incident\s+infection|new\s+infection',
         'REINFECTION'),
        (r'heavy[- ](?:intensity\s+)?infection|high[- ]intensity\s+infection',
         'HEAVY_INFECTION'),
    ],
    'context_patterns': [
        r'per\s+(?:100\s+)?person[- ]years', r'incidence\s+rate\s+ratio|\birr\b',
        r'follow[- ]up\s+at\s+\d+\s+months', r'baseline\s+prevalence',
    ]
}


# ============================================================
# MORBIDITY PATTERNS (chronic disease)
# ============================================================

MORBIDITY_PATTERNS = {
    'detection_keywords': [
        r'periportal\s+fibrosis|(?:hepatic|liver)\s+fibrosis', r'hepatosplenic',
        r'hepato(?:spleno)?megaly|splenomegaly', r'h(?:ae|e)maturia',
        r'bladder\s+(?:wall|pathology|lesion)', r'urinary\s+tract\s+morbidity',
        r'an(?:ae|e)mia|h(?:ae|e)moglobin', r'ultrasound', r'morbidity',
    ],
    'endpoint_patterns': [
        (r'periportal\s+fibrosis|(?:hepatic|liver)\s+fibrosis|hepatosplenic|'
         r'hepato(?:spleno)?megaly|splenomegaly', 'PERIPORTAL_FIBROSIS'),
        (r'micro[- ]?h(?:ae|e)maturia|visible\s+h(?:ae|e)maturia|'
         r'gross\s+h(?:ae|e)maturia|h(?:ae|e)maturia|blood\s+in\s+urine', 'HAEMATURIA'),
        (r'bladder\s+(?:wall|pathology|lesion|abnormality)|urinary\s+tract\s+'
         r'(?:morbidity|pathology|lesion)', 'BLADDER_PATHOLOGY'),
        (r'an(?:ae|e)mia|h(?:ae|e)moglobin', 'ANAEMIA'),
    ],
    'context_patterns': [
        r'ultrasonograph|ultrasound', r'image\s+pattern', r'\bg\/dl\b|\bg\/l\b',
    ]
}


# ============================================================
# VACCINE PATTERNS (prevention)
# ============================================================

VACCINE_PATTERNS = {
    'detection_keywords': [
        r'sh28gst|bilhvax', r'\bsm14\b|sm-?14', r'sm[- ]?tsp[- ]?2', r'smp80',
        r'schistosomiasis\s+vaccine', r'vaccine\s+efficacy|protective\s+efficacy',
        r'immunogenicity', r'seroconversion', r'antibody\s+response',
        r'geometric\s+mean\s+tit', r'\bigg\b',
    ],
    'endpoint_patterns': [
        (r'vaccine\s+efficacy|protective\s+efficacy|efficacy\s+against\s+'
         r'(?:infection|schistosomiasis)|protection\s+against\s+infection',
         'VACCINE_EFFICACY'),
        (r'immunogenicity|antibody\s+(?:response|titre|titer)|specific\s+igg|'
         r'igg\s+(?:response|antibody|geometric)|geometric\s+mean\s+tit|\bgmt\b|'
         r'anti[- ]sh28gst|anti[- ]sm14', 'IMMUNOGENICITY'),
        (r'seroconversion|four[- ]?fold\s+rise|seroresponse|antibody\s+response\s+rate',
         'SEROCONVERSION'),
    ],
    'context_patterns': [
        r'eu\/ml|elisa\s+unit', r'\biu\/ml\b', r'antigen', r'adjuvant',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_schistosomiasis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect schistosomiasis trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: treatment, prevention, morbidity, vaccine, general_schistosomiasis."""
    text_lower = text.lower()
    scores = {'treatment': 0, 'prevention': 0, 'morbidity': 0, 'vaccine': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['prevention'] += 1
    for kw in MORBIDITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['morbidity'] += 1
    for kw in VACCINE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['vaccine'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_schistosomiasis', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_schistosomiasis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'prevention': PREVENTION_PATTERNS['endpoint_patterns'],
        'morbidity': MORBIDITY_PATTERNS['endpoint_patterns'],
        'vaccine': VACCINE_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_schistosomiasis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical schistosomiasis endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in SCHISTOSOMIASIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
