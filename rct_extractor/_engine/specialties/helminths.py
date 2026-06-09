"""
Soil-Transmitted Helminths (STH) / Deworming Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV,
typhoid and schistosomiasis profiles. Soil-transmitted helminth (STH) /
deworming RCTs report a distinct endpoint vocabulary the generic effect-size
engine does not recognise on its own. STH (Ascaris lumbricoides / roundworm,
Trichuris trichiura / whipworm, hookworm: Necator americanus & Ancylostoma
duodenale, plus Strongyloides stercoralis) is a top-priority African neglected
tropical disease: the bulk of the >1.5 billion infected live in sub-Saharan
Africa and South/Southeast Asia, and school-based deworming is a WHO-recommended
mass intervention.

Subspecialties:
- Treatment (anthelmintic therapy): parasitological cure rate (CR), egg
  reduction rate (ERR), egg count / infection intensity (eggs per gram, EPG by
  Kato-Katz), treatment failure. Drugs: albendazole and mebendazole (the
  benzimidazole mainstays), pyrantel pamoate, levamisole, ivermectin,
  tribendimidine, oxantel pamoate, nitazoxanide, often in combination.
- Mass deworming (preventive chemotherapy / MDA / school-based deworming):
  infection prevalence and prevalence reduction, heavy-intensity (moderate-to-
  heavy) infection, programme coverage.
- Nutrition / growth (the rationale for community deworming): weight gain,
  height / height-for-age (stunting), haemoglobin / anaemia, mid-upper-arm
  circumference (MUAC), cognition / school attendance.
- Reinfection (post-treatment): reinfection rate, incidence of (re)infection,
  time to reinfection, reinfection intensity.

Effect measures follow what these trials report: binary (cure, failure,
prevalence, heavy infection, reinfection, stunting, anaemia) -> RR/OR/RD;
incidence / reinfection -> IRR/HR; continuous (egg reduction rate, weight,
height, haemoglobin, MUAC, cognition) -> MD/SMD; egg counts (EPG) are
right-skewed -> log scale / GMR.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# HELMINTHS (STH / DEWORMING) ENDPOINTS
# ============================================================

HELMINTHS_ENDPOINTS = {
    # --- Anthelmintic treatment efficacy ---
    'CURE_RATE': {
        'aliases': ['cure rate', 'parasitological cure', 'parasitologic cure',
                    'parasitological cure rate', 'parasitological clearance',
                    'parasitological response', 'egg-negative', 'egg negative',
                    'negative conversion', 'cured', 'worm clearance'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'EGG_REDUCTION_RATE': {
        'aliases': ['egg reduction rate', 'egg reduction', 'egg count reduction',
                    'reduction in egg count', 'reduction in egg counts',
                    'geometric mean egg reduction', 'egg reduction ratio',
                    'fecal egg count reduction', 'faecal egg count reduction',
                    'mean egg reduction'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'EGG_COUNT': {
        'aliases': ['egg count', 'egg counts', 'eggs per gram', 'eggs per gramme',
                    'mean egg count', 'geometric mean egg count', 'epg',
                    'fecal egg count', 'faecal egg count', 'infection intensity',
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

    # --- Mass deworming (preventive chemotherapy / MDA / school-based) ---
    'INFECTION_PREVALENCE': {
        'aliases': ['infection prevalence', 'prevalence of infection', 'prevalence',
                    'prevalence reduction', 'reduction in prevalence',
                    'helminth prevalence', 'sth prevalence',
                    'prevalence of any sth', 'prevalence of infection with any'],
        'subspecialty': 'mass_deworming',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HEAVY_INFECTION': {
        'aliases': ['heavy infection', 'heavy-intensity infection',
                    'heavy intensity infection', 'high-intensity infection',
                    'high intensity infection', 'moderate-to-heavy infection',
                    'moderate to heavy infection', 'heavy infection intensity'],
        'subspecialty': 'mass_deworming',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'COVERAGE': {
        'aliases': ['treatment coverage', 'deworming coverage', 'programme coverage',
                    'program coverage', 'coverage rate', 'population coverage'],
        'subspecialty': 'mass_deworming',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Nutrition / growth ---
    'WEIGHT': {
        'aliases': ['weight gain', 'weight', 'body weight', 'change in weight',
                    'weight-for-age', 'weight for age', 'weight-for-age z-score',
                    'mean weight'],
        'subspecialty': 'nutrition',
        'measure_types': ['MD', 'SMD']
    },
    'HEIGHT': {
        'aliases': ['height', 'height gain', 'change in height', 'linear growth',
                    'height-for-age', 'height for age', 'height-for-age z-score',
                    'stunting', 'stunted'],
        'subspecialty': 'nutrition',
        'measure_types': ['MD', 'SMD', 'RR']
    },
    'ANAEMIA': {
        'aliases': ['anaemia', 'anemia', 'haemoglobin', 'hemoglobin',
                    'haemoglobin concentration', 'hemoglobin concentration',
                    'anaemia prevalence', 'mean haemoglobin', 'mean hemoglobin'],
        'subspecialty': 'nutrition',
        'measure_types': ['RR', 'OR', 'MD']
    },
    'MUAC': {
        'aliases': ['mid-upper-arm circumference', 'mid upper arm circumference',
                    'mid-upper arm circumference', 'muac', 'arm circumference'],
        'subspecialty': 'nutrition',
        'measure_types': ['MD', 'SMD']
    },
    'COGNITION': {
        'aliases': ['cognitive function', 'cognition', 'cognitive performance',
                    'school attendance', 'school performance', 'attendance',
                    'test score', 'cognitive score', 'memory', 'attention'],
        'subspecialty': 'nutrition',
        'measure_types': ['MD', 'SMD']
    },

    # --- Reinfection (post-treatment) ---
    'REINFECTION': {
        'aliases': ['reinfection', 're-infection', 'reinfection rate',
                    'reinfection prevalence', 'prevalence of reinfection'],
        'subspecialty': 'reinfection',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'INFECTION_INCIDENCE': {
        'aliases': ['incidence of infection', 'incident infection', 'new infection',
                    'infection incidence', 'incidence of reinfection',
                    'time to reinfection'],
        'subspecialty': 'reinfection',
        'measure_types': ['IRR', 'HR', 'RR']
    },
    'REINFECTION_INTENSITY': {
        'aliases': ['reinfection intensity', 'intensity of reinfection',
                    'egg count at reinfection', 'reinfection egg count'],
        'subspecialty': 'reinfection',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# TREATMENT PATTERNS (anthelmintic therapy)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'albendazole', r'mebendazole', r'pyrantel', r'levamisole',
        r'ivermectin', r'tribendimidine', r'oxantel', r'nitazoxanide',
        r'benzimidazole', r'anthelmin(?:t|th)ic|antihelminthic',
        r'parasitological\s+cure', r'cure\s+rate', r'egg\s+reduction\s+rate',
        r'\berr\b', r'egg\s+count', r'eggs\s+per\s+gram', r'\bepg\b',
        r'kato[- ]?katz', r'fa?ecal\s+egg\s+count', r'infection\s+intensity',
        r'treatment\s+failure',
    ],
    'endpoint_patterns': [
        (r'cure\s+rate|parasitologic(?:al)?\s+(?:cure|clearance|response)|'
         r'egg[- ]negative|negative\s+conversion|worm\s+clearance', 'CURE_RATE'),
        (r'egg\s+reduction\s+rate|\berr\b|fa?ecal\s+egg\s+count\s+reduction|'
         r'egg\s+(?:count\s+)?reduction|reduction\s+in\s+egg\s+counts?',
         'EGG_REDUCTION_RATE'),
        (r'fa?ecal\s+egg\s+counts?|egg\s+counts?|eggs\s+per\s+gram|\bepg\b|'
         r'(?:infection\s+intensity|intensity\s+of\s+infection)', 'EGG_COUNT'),
        (r'(?:treatment|parasitological|therapeutic|clinical)\s+failure',
         'TREATMENT_FAILURE'),
    ],
    'context_patterns': [
        r'single\s+(?:oral\s+)?dose', r'\d+\s*mg(?:\/kg)?', r'kato[- ]?katz',
        r'mcmaster', r'geometric\s+mean', r'\bday\s+(?:14|21|28)\b',
    ]
}


# ============================================================
# MASS DEWORMING PATTERNS (preventive chemotherapy / MDA / school-based)
# ============================================================

MASS_DEWORMING_PATTERNS = {
    'detection_keywords': [
        r'mass\s+drug\s+administration|\bmda\b', r'preventive\s+chemotherapy',
        r'(?:mass\s+|community\s+|school[- ]based\s+)?deworming|de[- ]worming',
        r'school[- ]based\s+treatment', r'community[- ]wide\s+treatment',
        r'prevalence\s+(?:of\s+)?(?:infection|sth|helminth)',
        r'soil[- ]transmitted\s+helminth', r'\bsth\b', r'geohelminth',
        r'heavy[- ]intensity\s+infection', r'moderate[- ]to[- ]heavy',
        r'treatment\s+coverage|deworming\s+coverage',
    ],
    'endpoint_patterns': [
        (r'(?:infection\s+|helminth\s+|sth\s+)?prevalence(?:\s+(?:of|reduction))?|'
         r'reduction\s+in\s+prevalence', 'INFECTION_PREVALENCE'),
        (r'(?:moderate[- ]to[- ])?heavy[- ](?:intensity\s+)?infection|'
         r'high[- ]intensity\s+infection', 'HEAVY_INFECTION'),
        (r'(?:treatment|deworming|programme?|population)\s+coverage|coverage\s+rate',
         'COVERAGE'),
    ],
    'context_patterns': [
        r'school[- ]age\s+children', r'preschool', r'\bwho\b\s+threshold',
        r'baseline\s+prevalence', r'once[- ](?:or\s+twice[- ])?yearly',
    ]
}


# ============================================================
# NUTRITION / GROWTH PATTERNS
# ============================================================

NUTRITION_PATTERNS = {
    'detection_keywords': [
        r'weight\s+gain|body\s+weight|weight[- ]for[- ]age',
        r'height[- ]for[- ]age|linear\s+growth|\bstunt', r'\bheight\s+gain',
        r'an(?:ae|e)mia|h(?:ae|e)moglobin', r'mid[- ]upper[- ]arm\s+circumference|\bmuac\b',
        r'cogniti|school\s+(?:attendance|performance)', r'nutritional\s+status',
        r'growth', r'\bz[- ]score', r'appetite',
    ],
    'endpoint_patterns': [
        (r'weight\s+gain|body\s+weight|weight[- ]for[- ]age|change\s+in\s+weight',
         'WEIGHT'),
        (r'height[- ]for[- ]age|linear\s+growth|height\s+gain|change\s+in\s+height|'
         r'\bstunt(?:ing|ed)?\b|\bheight\b', 'HEIGHT'),
        (r'an(?:ae|e)mia|h(?:ae|e)moglobin', 'ANAEMIA'),
        (r'mid[- ]upper[- ]arm\s+circumference|\bmuac\b|arm\s+circumference', 'MUAC'),
        (r'cogniti(?:ve|on)|school\s+(?:attendance|performance)|test\s+score|'
         r'\battendance\b|\bmemory\b|\battention\b', 'COGNITION'),
    ],
    'context_patterns': [
        r'\bkg\b|\bg\/dl\b|\bg\/l\b|\bcm\b', r'\bz[- ]score', r'preschool|school[- ]age',
    ]
}


# ============================================================
# REINFECTION PATTERNS (post-treatment)
# ============================================================

REINFECTION_PATTERNS = {
    'detection_keywords': [
        r're[- ]?infection', r'incidence\s+of\s+(?:re)?infection',
        r'incident\s+infection', r'new\s+infection', r'time\s+to\s+reinfection',
        r'reinfection\s+(?:rate|prevalence|intensity)',
        r'post[- ]treatment\s+(?:infection|reinfection)', r'transmission',
    ],
    'endpoint_patterns': [
        (r're[- ]?infection\s+intensity|intensity\s+of\s+reinfection|'
         r'egg\s+count\s+at\s+reinfection', 'REINFECTION_INTENSITY'),
        (r'incidence\s+of\s+(?:re)?infection|incident\s+infection|new\s+infection|'
         r'infection\s+incidence|time\s+to\s+reinfection', 'INFECTION_INCIDENCE'),
        (r're[- ]?infection(?:\s+(?:rate|prevalence))?', 'REINFECTION'),
    ],
    'context_patterns': [
        r'per\s+(?:100\s+)?person[- ]years', r'incidence\s+rate\s+ratio|\birr\b',
        r'follow[- ]up\s+at\s+\d+\s+months', r'months\s+after\s+treatment',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_helminths_subspecialty(text: str) -> Tuple[str, float]:
    """Detect STH / deworming trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: treatment, mass_deworming, nutrition, reinfection,
    general_helminths."""
    text_lower = text.lower()
    scores = {'treatment': 0, 'mass_deworming': 0, 'nutrition': 0, 'reinfection': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in MASS_DEWORMING_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mass_deworming'] += 1
    for kw in NUTRITION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['nutrition'] += 1
    for kw in REINFECTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['reinfection'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_helminths', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_helminths_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'mass_deworming': MASS_DEWORMING_PATTERNS['endpoint_patterns'],
        'nutrition': NUTRITION_PATTERNS['endpoint_patterns'],
        'reinfection': REINFECTION_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_helminths_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical STH / deworming endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in HELMINTHS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
