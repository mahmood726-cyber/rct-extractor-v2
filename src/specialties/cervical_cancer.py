"""
Cervical Cancer / HPV Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV and
typhoid profiles. Cervical cancer / HPV is a top women's-health priority across
sub-Saharan Africa (highest incidence and mortality globally) and its RCTs report
a distinct endpoint vocabulary spanning prevention, screening, precancer treatment
and cancer outcomes that the generic effect-size engine does not recognise on its
own.

Subspecialties:
- Vaccine (HPV prevention): persistent HPV infection, vaccine-type infection,
  CIN2+/CIN3+ (high-grade precancer), genital warts, vaccine efficacy,
  seroconversion, anti-HPV immunogenicity (GMT/GMC). Vaccines: bivalent (Cervarix),
  quadrivalent (Gardasil), nonavalent (Gardasil 9), Cecolin, Walrinvax; HPV-16/18.
- Screening (test accuracy / VIA): VIA / VILI positivity, HPV DNA test, cytology
  (Pap), screen positivity, sensitivity/specificity for CIN2+, colposcopy referral,
  screening uptake/coverage, self-sampling. "Screen-and-treat" single-visit.
- Treatment (of precancer): cryotherapy, thermal ablation/thermocoagulation,
  LEEP/LLETZ, cold-knife conization; lesion/CIN clearance (cure), HPV clearance,
  residual/recurrent disease (treatment failure), recurrence.
- Mortality / incidence: invasive cervical cancer incidence, cervical cancer
  mortality, all-cause mortality.

Effect measures follow what these trials report: binary (infection, CIN2+, warts,
clearance, failure, recurrence, screen-positive) -> RR/OR/RD; incidence/time-to ->
IRR/HR; continuous (anti-HPV titres) -> GMR, log-normal. Diagnostic accuracy
(sensitivity/specificity) carries DTA-style measure tags.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# CERVICAL CANCER / HPV ENDPOINTS
# ============================================================

CERVICAL_CANCER_ENDPOINTS = {
    # --- Vaccine (HPV prevention) ---
    'PERSISTENT_HPV_INFECTION': {
        'aliases': ['persistent hpv infection', 'persistent infection',
                    'persistent hpv', '6-month persistent infection',
                    '12-month persistent infection', 'persistent vaccine-type infection',
                    'six-month persistent infection'],
        'subspecialty': 'vaccine',
        'measure_types': ['RR', 'OR', 'HR', 'IRR']
    },
    'HPV_INFECTION': {
        'aliases': ['incident hpv infection', 'incident infection', 'hpv infection',
                    'vaccine-type hpv infection', 'hpv 16/18 infection',
                    'hpv-16/18 infection', 'new hpv infection', 'hpv acquisition'],
        'subspecialty': 'vaccine',
        'measure_types': ['RR', 'OR', 'HR', 'IRR']
    },
    'CIN2_PLUS': {
        'aliases': ['cin2+', 'cin 2+', 'cin2 or worse', 'cin grade 2 or worse',
                    'high-grade cervical lesion', 'high-grade squamous intraepithelial lesion',
                    'high-grade precancer', 'hsil', 'cin3+', 'cin 3+', 'cin2/3',
                    'cervical intraepithelial neoplasia grade 2', 'high-grade lesion'],
        'subspecialty': 'vaccine',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'GENITAL_WARTS': {
        'aliases': ['genital warts', 'anogenital warts', 'condyloma',
                    'condylomata acuminata', 'external genital lesions'],
        'subspecialty': 'vaccine',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'VACCINE_EFFICACY': {
        'aliases': ['vaccine efficacy', 'protective efficacy',
                    'efficacy against hpv', 'efficacy against cin',
                    'efficacy against persistent infection'],
        'subspecialty': 'vaccine',
        'measure_types': ['HR', 'IRR', 'RR']
    },
    'HPV_SEROCONVERSION': {
        'aliases': ['seroconversion', 'anti-hpv seroconversion', 'seroresponse',
                    'seroconversion rate', 'sero-response rate'],
        'subspecialty': 'vaccine',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HPV_IMMUNOGENICITY': {
        'aliases': ['anti-hpv igg', 'anti-hpv antibody', 'geometric mean titer',
                    'geometric mean titre', 'gmt', 'geometric mean concentration', 'gmc',
                    'anti-hpv geometric mean', 'immunogenicity', 'hpv antibody titre',
                    'neutralizing antibody titre'],
        'subspecialty': 'vaccine',
        'measure_types': ['GMR', 'MD', 'SMD']
    },

    # --- Screening (test accuracy / VIA) ---
    'SCREEN_POSITIVITY': {
        'aliases': ['via positivity', 'via positive', 'vili positivity',
                    'screen positivity', 'screen positive', 'test positivity',
                    'hpv positivity', 'hpv-positive', 'positivity rate',
                    'screen-positive rate'],
        'subspecialty': 'screening',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SCREENING_SENSITIVITY': {
        'aliases': ['sensitivity', 'screening sensitivity', 'test sensitivity',
                    'sensitivity for cin2+', 'sensitivity to detect cin2+',
                    'sensitivity for high-grade lesions'],
        'subspecialty': 'screening',
        'measure_types': ['SENS', 'PROP']
    },
    'SCREENING_SPECIFICITY': {
        'aliases': ['specificity', 'screening specificity', 'test specificity',
                    'specificity for cin2+', 'specificity to detect cin2+'],
        'subspecialty': 'screening',
        'measure_types': ['SPEC', 'PROP']
    },
    'CIN_DETECTION': {
        'aliases': ['detection of cin2+', 'cin2+ detection', 'detection rate',
                    'cancer detection rate', 'lesion detection rate',
                    'detection of high-grade lesions', 'disease detection rate'],
        'subspecialty': 'screening',
        'measure_types': ['RR', 'OR']
    },
    'COLPOSCOPY_REFERRAL': {
        'aliases': ['colposcopy referral', 'referral for colposcopy', 'referral rate',
                    'colposcopy referral rate', 'colposcopy rate'],
        'subspecialty': 'screening',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SCREENING_UPTAKE': {
        'aliases': ['screening uptake', 'screening participation', 'screening attendance',
                    'screening coverage', 'participation rate', 'uptake rate',
                    'attendance rate'],
        'subspecialty': 'screening',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Treatment (of precancer) ---
    'LESION_CLEARANCE': {
        'aliases': ['lesion clearance', 'disease clearance', 'cin regression',
                    'lesion regression', 'histologic cure', 'cure rate', 'cure',
                    'complete response', 'lesion resolution', 'regression to normal'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HPV_CLEARANCE': {
        'aliases': ['hpv clearance', 'viral clearance', 'hpv dna clearance',
                    'clearance of hpv', 'hpv type-specific clearance',
                    'post-treatment hpv clearance'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'TREATMENT_FAILURE': {
        'aliases': ['treatment failure', 'residual disease', 'residual/recurrent disease',
                    'persistent disease', 'incomplete excision', 'positive margins',
                    'residual or recurrent disease', 'treatment failure rate'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'RECURRENCE': {
        'aliases': ['recurrence', 'recurrent cin', 'recurrent disease',
                    'disease recurrence', 'recurrence rate', 'recurrent high-grade lesion'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Mortality / incidence ---
    'CERVICAL_CANCER_INCIDENCE': {
        'aliases': ['invasive cervical cancer', 'cervical cancer incidence',
                    'incidence of cervical cancer', 'invasive cancer',
                    'cervical carcinoma', 'incident cervical cancer',
                    'invasive cervical carcinoma'],
        'subspecialty': 'mortality',
        'measure_types': ['HR', 'IRR', 'RR']
    },
    'CERVICAL_CANCER_MORTALITY': {
        'aliases': ['cervical cancer mortality', 'death from cervical cancer',
                    'cervical cancer death', 'cervical-cancer mortality',
                    'cervical cancer-specific mortality', 'mortality from cervical cancer'],
        'subspecialty': 'mortality',
        'measure_types': ['HR', 'RR', 'IRR']
    },
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all cause death',
                    'all-cause death', 'total mortality'],
        'subspecialty': 'mortality',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# VACCINE PATTERNS (HPV prevention)
# ============================================================

VACCINE_PATTERNS = {
    'detection_keywords': [
        r'hpv\s+vaccine', r'human\s+papillomavirus\s+vaccine',
        r'quadrivalent', r'bivalent', r'nonavalent|9[- ]valent|nine[- ]valent',
        r'gardasil(?:\s*9)?', r'cervarix', r'cecolin', r'walrinvax',
        r'l1\s+(?:vlp|virus[- ]like\s+particle)', r'as04', r'anti[- ]hpv',
        r'hpv[- ]?16(?:/18)?|hpv[- ]?18', r'persistent\s+(?:hpv\s+)?infection',
        r'vaccine\s+efficacy|protective\s+efficacy', r'seroconversion',
        r'immunogenicity', r'geometric\s+mean\s+tit', r'single[- ]dose\s+hpv',
    ],
    'endpoint_patterns': [
        (r'persistent\s+(?:hpv\s+|vaccine[- ]type\s+)?infection|'
         r'(?:6|12|six|twelve)[- ]month\s+persistent\s+infection', 'PERSISTENT_HPV_INFECTION'),
        (r'incident\s+(?:hpv\s+)?infection|hpv\s+acquisition|new\s+hpv\s+infection|'
         r'hpv[- ]?16/18\s+infection|vaccine[- ]type\s+hpv\s+infection', 'HPV_INFECTION'),
        (r'cin\s?2\+|cin\s?3\+|cin\s?2/3|high[- ]grade\s+(?:squamous\s+intraepithelial\s+lesion|'
         r'cervical\s+lesion|precancer|lesion)|\bhsil\b|cin\s+grade\s+2', 'CIN2_PLUS'),
        (r'genital\s+warts|anogenital\s+warts|condyloma', 'GENITAL_WARTS'),
        (r'vaccine\s+efficacy|protective\s+efficacy|efficacy\s+against\s+(?:hpv|cin|persistent)',
         'VACCINE_EFFICACY'),
        (r'seroconversion|seroresponse', 'HPV_SEROCONVERSION'),
        (r'anti[- ]hpv\s+(?:igg|antibody|geometric)|geometric\s+mean\s+(?:tit|concentration)|'
         r'\bgmt\b|\bgmc\b|neutrali[sz]ing\s+antibody\s+tit|immunogenicity', 'HPV_IMMUNOGENICITY'),
    ],
    'context_patterns': [
        r'per[- ]protocol|intention[- ]to[- ]treat|according[- ]to[- ]protocol',
        r'per\s+(?:100,?000\s+)?(?:woman|person)[- ]years', r'eu\/ml|elisa\s+unit',
        r'seronegative\s+at\s+baseline',
    ]
}


# ============================================================
# SCREENING PATTERNS (test accuracy / VIA)
# ============================================================

SCREENING_PATTERNS = {
    'detection_keywords': [
        r'visual\s+inspection\s+with\s+acetic\s+acid|\bvia\b',
        r'visual\s+inspection\s+with\s+lugol|\bvili\b',
        r'hpv\s+(?:dna\s+)?test|hpv\s+testing|care\s?hpv|gene\s?xpert',
        r'\bpap\b|pap\s+smear|cervical\s+cytology|liquid[- ]based\s+cytology|conventional\s+cytology',
        r'screen[- ]and[- ]treat|single[- ]visit\s+approach|see[- ]and[- ]treat',
        r'self[- ](?:sampling|collection|collected)', r'co[- ]testing',
        r'sensitivity|specificity', r'colposcopy', r'cervical\s+screening',
    ],
    'endpoint_patterns': [
        (r'via\s+positiv|vili\s+positiv|screen[- ]?positiv|test\s+positiv|'
         r'hpv\s+positiv|positivity\s+rate', 'SCREEN_POSITIVITY'),
        (r'sensitivity(?:\s+(?:for|to\s+detect)\s+cin\s?2\+)?', 'SCREENING_SENSITIVITY'),
        (r'specificity(?:\s+(?:for|to\s+detect)\s+cin\s?2\+)?', 'SCREENING_SPECIFICITY'),
        (r'detection\s+(?:rate|of\s+cin\s?2\+|of\s+high[- ]grade)|cin\s?2\+\s+detection|'
         r'cancer\s+detection\s+rate', 'CIN_DETECTION'),
        (r'colposcopy\s+referral|referral\s+(?:for\s+colposcopy|rate)|colposcopy\s+rate',
         'COLPOSCOPY_REFERRAL'),
        (r'screening\s+(?:uptake|participation|attendance|coverage)|participation\s+rate|'
         r'uptake\s+rate|attendance\s+rate', 'SCREENING_UPTAKE'),
    ],
    'context_patterns': [
        r'true\s+positive|false\s+positive', r'gold\s+standard|reference\s+standard',
        r'histolog(?:y|ical)\s+confirm', r'colposcop(?:y|ic)\s+biopsy',
    ]
}


# ============================================================
# TREATMENT PATTERNS (of precancer)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'cryotherapy|cryosurgery', r'thermal\s+ablation|thermocoagulation|cold\s+coagulation',
        r'\bleep\b|\blletz\b|loop\s+electrosurgical\s+excision|loop\s+excision',
        r'cold[- ]knife\s+coni[sz]ation|coni[sz]ation|cone\s+biopsy',
        r'ablative\s+treatment|excisional\s+treatment',
        r'treatment\s+of\s+(?:cin|precancer|cervical\s+intraepithelial)',
        r'lesion\s+clearance|cin\s+regression', r'residual\s+(?:or\s+recurrent\s+)?disease',
    ],
    'endpoint_patterns': [
        (r'lesion\s+clearance|disease\s+clearance|cin\s+regression|lesion\s+regression|'
         r'histolog(?:ic|ical)\s+cure|cure\s+rate|complete\s+response|regression\s+to\s+normal',
         'LESION_CLEARANCE'),
        (r'hpv\s+(?:dna\s+)?clearance|viral\s+clearance|clearance\s+of\s+hpv|'
         r'type[- ]specific\s+(?:hpv\s+)?clearance', 'HPV_CLEARANCE'),
        (r'treatment\s+failure|residual\s+(?:or\s+recurrent\s+)?disease|persistent\s+disease|'
         r'incomplete\s+excision|positive\s+margins', 'TREATMENT_FAILURE'),
        (r'recurrence|recurrent\s+(?:cin|disease|high[- ]grade)', 'RECURRENCE'),
    ],
    'context_patterns': [
        r'6[- ]month\s+follow[- ]up|12[- ]month\s+follow[- ]up',
        r'margin\s+status', r'see[- ]and[- ]treat|single[- ]visit',
    ]
}


# ============================================================
# MORTALITY / INCIDENCE PATTERNS
# ============================================================

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'cervical\s+cancer\s+mortality|cervical[- ]cancer\s+mortality',
        r'cervical\s+cancer\s+incidence|incidence\s+of\s+cervical\s+cancer',
        r'invasive\s+cervical\s+cancer|invasive\s+cervical\s+carcinoma',
        r'cervical\s+cancer\s+death|death\s+from\s+cervical\s+cancer',
        r'all[- ]cause\s+mortality', r'cancer[- ]specific\s+(?:mortality|survival)',
    ],
    'endpoint_patterns': [
        (r'invasive\s+cervical\s+(?:cancer|carcinoma)|cervical\s+cancer\s+incidence|'
         r'incidence\s+of\s+cervical\s+cancer|incident\s+cervical\s+cancer', 'CERVICAL_CANCER_INCIDENCE'),
        (r'cervical\s+cancer\s+mortality|death\s+from\s+cervical\s+cancer|'
         r'cervical\s+cancer\s+death|cervical\s+cancer[- ]specific\s+mortality', 'CERVICAL_CANCER_MORTALITY'),
        (r'all[- ]cause\s+mortality|overall\s+mortality|all[- ]cause\s+death', 'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [
        r'per\s+(?:100,?000\s+)?(?:woman|person)[- ]years', r'cumulative\s+incidence',
        r'follow[- ]up\s+of\s+\d+\s+years',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_cervical_cancer_subspecialty(text: str) -> Tuple[str, float]:
    """Detect cervical-cancer/HPV trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: vaccine, screening, treatment, mortality, general_cervical_cancer."""
    text_lower = text.lower()
    scores = {'vaccine': 0, 'screening': 0, 'treatment': 0, 'mortality': 0}
    for kw in VACCINE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['vaccine'] += 1
    for kw in SCREENING_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['screening'] += 1
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_cervical_cancer', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_cervical_cancer_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'vaccine': VACCINE_PATTERNS['endpoint_patterns'],
        'screening': SCREENING_PATTERNS['endpoint_patterns'],
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_cervical_cancer_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical cervical-cancer endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in CERVICAL_CANCER_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
