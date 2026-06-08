"""
Malnutrition (severe/moderate acute malnutrition, undernutrition) Subspecialty
Patterns and Endpoints.

Built for the same African-student meta-analysis workflow as the malaria, HIV and
typhoid profiles. Child-undernutrition RCTs (an Africa-priority topic) report a
distinct endpoint vocabulary -- nutritional recovery, weight-gain velocity,
anthropometric z-scores, oedema resolution -- that the generic effect-size engine
does not recognise on its own.

Subspecialties:
- Therapeutic feeding (RUTF / inpatient + outpatient SAM management): nutritional
  recovery / cure, weight-gain rate (g/kg/day), defaulting, relapse / readmission,
  length of stay. Products: ready-to-use therapeutic food (RUTF), ready-to-use
  supplementary food (RUSF), F-75 / F-100 therapeutic milk, corn-soy blend (CSB),
  CMAM programmes.
- Micronutrient supplementation: stunting, wasting, anaemia, serum micronutrient
  status (zinc, retinol, ferritin), morbidity (diarrhoea / respiratory infection).
  Products: zinc, vitamin A, iron, multiple micronutrient powders (MNP),
  lipid-based nutrient supplements (LNS / SQ-LNS).
- Mortality (severe malnutrition): all-cause mortality, case fatality, in-hospital
  / inpatient mortality.
- Recovery / growth (anthropometric outcomes): weight-for-height z-score (WHZ/WLZ),
  mid-upper-arm-circumference (MUAC) change, weight gain, height / length gain,
  oedema resolution, time to recovery.

Effect measures follow what these trials report: binary (recovery, default,
relapse, stunting, wasting, anaemia, oedema, mortality) -> RR/OR/RD; incidence
(morbidity) -> IRR; continuous (weight-gain rate, MUAC, WHZ, length of stay,
time to recovery) -> MD/SMD; skewed serum micronutrient titres -> GMR, log-normal.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# MALNUTRITION ENDPOINTS
# ============================================================

MALNUTRITION_ENDPOINTS = {
    # --- Therapeutic feeding (RUTF / SAM management) ---
    'NUTRITIONAL_RECOVERY': {
        'aliases': ['nutritional recovery', 'nutritional cure', 'recovery rate',
                    'recovered', 'proportion cured', 'proportion recovered',
                    'rate of recovery', 'treatment success', 'reaching recovery',
                    'cure rate'],
        'subspecialty': 'therapeutic_feeding',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'WEIGHT_GAIN_RATE': {
        'aliases': ['rate of weight gain', 'weight gain rate', 'weight-gain velocity',
                    'g/kg/day', 'g/kg per day', 'grams per kilogram per day',
                    'average weight gain', 'mean weight gain rate'],
        'subspecialty': 'therapeutic_feeding',
        'measure_types': ['MD', 'SMD']
    },
    'TREATMENT_DEFAULT': {
        'aliases': ['default', 'defaulting', 'defaulter rate', 'defaulted',
                    'lost to follow-up', 'lost to follow up', 'programme dropout',
                    'program dropout', 'non-completion'],
        'subspecialty': 'therapeutic_feeding',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RELAPSE': {
        'aliases': ['relapse', 'relapse rate', 'readmission', 'readmission rate',
                    'recurrence of malnutrition', 'readmission after recovery',
                    'recurrence'],
        'subspecialty': 'therapeutic_feeding',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'LENGTH_OF_STAY': {
        'aliases': ['length of stay', 'duration of treatment', 'length of treatment',
                    'time in programme', 'time in program', 'duration of hospitalization',
                    'duration of hospitalisation', 'time to discharge'],
        'subspecialty': 'therapeutic_feeding',
        'measure_types': ['MD', 'SMD']
    },

    # --- Micronutrient supplementation ---
    'STUNTING': {
        'aliases': ['stunting', 'stunted', 'prevalence of stunting', 'incidence of stunting',
                    'height-for-age', 'length-for-age', 'haz', 'laz',
                    'linear growth retardation'],
        'subspecialty': 'micronutrient',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'WASTING': {
        'aliases': ['wasting', 'wasted', 'prevalence of wasting', 'incidence of wasting',
                    'weight-for-height below', 'acute malnutrition incidence',
                    'incident wasting'],
        'subspecialty': 'micronutrient',
        'measure_types': ['RR', 'OR', 'IRR']
    },
    'ANAEMIA': {
        'aliases': ['anaemia', 'anemia', 'prevalence of anaemia', 'prevalence of anemia',
                    'low haemoglobin', 'low hemoglobin', 'haemoglobin concentration',
                    'hemoglobin concentration', 'iron-deficiency anaemia',
                    'iron-deficiency anemia'],
        'subspecialty': 'micronutrient',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MICRONUTRIENT_STATUS': {
        'aliases': ['serum zinc', 'plasma zinc', 'serum retinol', 'plasma retinol',
                    'serum ferritin', 'vitamin a status', 'serum vitamin a',
                    'micronutrient status', 'zinc concentration', 'retinol concentration',
                    'ferritin concentration'],
        'subspecialty': 'micronutrient',
        'measure_types': ['GMR', 'MD', 'SMD']
    },
    'MORBIDITY': {
        'aliases': ['diarrhoea incidence', 'diarrhea incidence', 'incidence of diarrhoea',
                    'incidence of diarrhea', 'episodes of diarrhoea', 'episodes of diarrhea',
                    'respiratory infection', 'morbidity', 'days of illness',
                    'diarrhoeal morbidity', 'diarrheal morbidity'],
        'subspecialty': 'micronutrient',
        'measure_types': ['IRR', 'RR', 'OR']
    },

    # --- Mortality (severe malnutrition) ---
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'died',
                    'mortality rate', 'risk of death'],
        'subspecialty': 'mortality',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CASE_FATALITY': {
        'aliases': ['case fatality', 'case-fatality rate', 'case fatality rate',
                    'in-hospital mortality', 'inpatient mortality', 'in-patient mortality',
                    'hospital mortality'],
        'subspecialty': 'mortality',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Recovery / growth (anthropometric outcomes) ---
    'WEIGHT_FOR_HEIGHT': {
        'aliases': ['weight-for-height z-score', 'weight-for-height z score', 'whz',
                    'wlz', 'weight-for-length', 'weight-for-height', 'change in whz',
                    'weight-for-height z-score change'],
        'subspecialty': 'recovery_growth',
        'measure_types': ['MD', 'SMD']
    },
    'MUAC_CHANGE': {
        'aliases': ['mid-upper arm circumference', 'mid upper arm circumference', 'muac',
                    'muac gain', 'change in muac', 'muac increase', 'muac change'],
        'subspecialty': 'recovery_growth',
        'measure_types': ['MD', 'SMD']
    },
    'WEIGHT_GAIN': {
        'aliases': ['weight gain', 'body weight gain', 'change in weight',
                    'weight increase', 'absolute weight gain', 'gain in weight'],
        'subspecialty': 'recovery_growth',
        'measure_types': ['MD', 'SMD']
    },
    'HEIGHT_GAIN': {
        'aliases': ['height gain', 'length gain', 'linear growth', 'change in height',
                    'change in length', 'height increase', 'gain in height'],
        'subspecialty': 'recovery_growth',
        'measure_types': ['MD', 'SMD']
    },
    'OEDEMA_RESOLUTION': {
        'aliases': ['oedema resolution', 'edema resolution', 'resolution of oedema',
                    'resolution of edema', 'oedema-free', 'edema-free',
                    'loss of oedema', 'loss of edema', 'time to oedema resolution'],
        'subspecialty': 'recovery_growth',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TIME_TO_RECOVERY': {
        'aliases': ['time to recovery', 'days to recovery', 'time to discharge',
                    'time to cure', 'time to nutritional recovery', 'days to discharge',
                    'recovery time'],
        'subspecialty': 'recovery_growth',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# THERAPEUTIC FEEDING PATTERNS (RUTF / SAM management)
# ============================================================

THERAPEUTIC_FEEDING_PATTERNS = {
    'detection_keywords': [
        r'ready[- ]to[- ]use\s+therapeutic\s+food', r'\brutf\b',
        r'ready[- ]to[- ]use\s+supplementary\s+food', r'\brusf\b',
        r'\bf-?75\b', r'\bf-?100\b', r'therapeutic\s+milk', r'therapeutic\s+feeding',
        r'\bcmam\b', r'community[- ]based\s+management\s+of\s+acute\s+malnutrition',
        r'outpatient\s+therapeutic', r'stabili[sz]ation\s+(?:centre|center)',
        r'nutritional\s+rehabilitation', r'supplementary\s+feeding',
        r'corn[- ]soy\s+blend', r'\bcsb\b', r'recovery\s+rate', r'weight\s+gain',
    ],
    'endpoint_patterns': [
        (r'nutritional\s+(?:recovery|cure)|recovery\s+rate|rate\s+of\s+recovery|'
         r'(?:proportion|rate)\s+(?:cured|recovered)|treatment\s+success', 'NUTRITIONAL_RECOVERY'),
        (r'rate\s+of\s+weight\s+gain|weight[- ]gain\s+(?:rate|velocity)|'
         r'g\s*\/\s*kg\s*\/\s*day|grams?\s+per\s+kilogram\s+per\s+day', 'WEIGHT_GAIN_RATE'),
        (r'default(?:ing|er|ed)?|lost\s+to\s+follow[- ]?up|programme?\s+dropout|'
         r'non[- ]completion', 'TREATMENT_DEFAULT'),
        (r'relapse|readmission|recurrence', 'RELAPSE'),
        (r'length\s+of\s+(?:stay|treatment)|duration\s+of\s+(?:treatment|hospitali[sz]ation)|'
         r'time\s+in\s+(?:the\s+)?programme?|time\s+to\s+discharge', 'LENGTH_OF_STAY'),
    ],
    'context_patterns': [
        r'discharge\s+criteria', r'inpatient|outpatient', r'\bsphere\b|sphere\s+standard',
        r'oedema[- ]free', r'15\s*%\s+weight\s+gain',
    ]
}


# ============================================================
# MICRONUTRIENT PATTERNS (supplementation)
# ============================================================

MICRONUTRIENT_PATTERNS = {
    'detection_keywords': [
        r'\bzinc\b', r'vitamin\s+a', r'\biron\b', r'multiple\s+micronutrient',
        r'micronutrient\s+powder', r'\bmnp\b', r'lipid[- ]based\s+nutrient\s+supplement',
        r'\blns\b', r'sq[- ]lns', r'supplementation', r'fortif',
        r'\bstunting\b', r'ha?emoglobin', r'\bana?emia\b',
        r'serum\s+(?:zinc|retinol|ferritin)', r'plasma\s+(?:zinc|retinol)',
    ],
    'endpoint_patterns': [
        (r'stunting|stunted|height[- ]for[- ]age|length[- ]for[- ]age|\bhaz\b|\blaz\b|'
         r'linear\s+growth\s+retardation', 'STUNTING'),
        (r'\bwasting\b|wasted|incidence\s+of\s+wasting|prevalence\s+of\s+wasting|'
         r'weight[- ]for[- ]height\s+below', 'WASTING'),
        (r'ana?emia|low\s+ha?emoglobin|ha?emoglobin\s+concentration|'
         r'iron[- ]deficiency\s+ana?emia', 'ANAEMIA'),
        (r'serum\s+(?:zinc|retinol|ferritin)|plasma\s+(?:zinc|retinol)|'
         r'vitamin\s+a\s+status|micronutrient\s+status|(?:zinc|retinol|ferritin)\s+concentration',
         'MICRONUTRIENT_STATUS'),
        (r'diarrh(?:oea|ea)\s+(?:incidence|episodes?|morbidity)|'
         r'incidence\s+of\s+diarrh(?:oea|ea)|episodes?\s+of\s+diarrh(?:oea|ea)|'
         r'respiratory\s+infection|\bmorbidity\b|days\s+of\s+illness', 'MORBIDITY'),
    ],
    'context_patterns': [
        r'per\s+(?:child[- ])?year', r'incidence\s+rate\s+ratio|\birr\b',
        r'micromol\/l|µg\/dl|mcg\/dl|g\/dl', r'\bgr?owth\s+monitoring',
    ]
}


# ============================================================
# MORTALITY PATTERNS (severe malnutrition)
# ============================================================

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'\bmortality\b', r'case[- ]fatality', r'\bdeath\b', r'\bdied\b',
        r'in[- ]hospital\s+mortality', r'inpatient\s+mortality',
        r'risk\s+of\s+death', r'survival',
    ],
    'endpoint_patterns': [
        (r'case[- ]fatality(?:\s+rate)?|in[- ]hospital\s+mortality|'
         r'in[- ]?patient\s+mortality|hospital\s+mortality', 'CASE_FATALITY'),
        (r'(?:all[- ]cause\s+)?mortality|\bdeath\b|\bdied\b|risk\s+of\s+death', 'MORTALITY'),
    ],
    'context_patterns': [
        r'kaplan[- ]meier', r'hazard\s+ratio|\bhr\b', r'person[- ]time',
    ]
}


# ============================================================
# RECOVERY / GROWTH PATTERNS (anthropometric outcomes)
# ============================================================

RECOVERY_GROWTH_PATTERNS = {
    'detection_keywords': [
        r'weight[- ]for[- ]height', r'\bwhz\b', r'\bwlz\b', r'weight[- ]for[- ]length',
        r'mid[- ]upper\s+arm\s+circumference', r'\bmuac\b', r'weight\s+gain',
        r'time\s+to\s+recovery', r'o?edema', r'linear\s+growth',
        r'length\s+gain', r'height\s+gain', r'catch[- ]up\s+growth',
        r'anthropometric',
    ],
    'endpoint_patterns': [
        (r'weight[- ]for[- ]height\s+z[- ]?score|\bwhz\b|\bwlz\b|weight[- ]for[- ]length',
         'WEIGHT_FOR_HEIGHT'),
        (r'mid[- ]upper\s+arm\s+circumference|\bmuac\b', 'MUAC_CHANGE'),
        (r'weight\s+gain|body\s+weight|change\s+in\s+weight|gain\s+in\s+weight', 'WEIGHT_GAIN'),
        (r'height\s+gain|length\s+gain|linear\s+growth|change\s+in\s+(?:height|length)',
         'HEIGHT_GAIN'),
        (r'o?edema\s+resolution|resolution\s+of\s+o?edema|o?edema[- ]free|loss\s+of\s+o?edema',
         'OEDEMA_RESOLUTION'),
        (r'time\s+to\s+(?:recovery|discharge|cure)|days\s+to\s+(?:recovery|discharge)',
         'TIME_TO_RECOVERY'),
    ],
    'context_patterns': [
        r'z[- ]?score', r'who\s+(?:child\s+)?growth\s+standard', r'standard\s+deviation\s+score',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_malnutrition_subspecialty(text: str) -> Tuple[str, float]:
    """Detect malnutrition trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: therapeutic_feeding, micronutrient, mortality, recovery_growth,
    general_malnutrition."""
    text_lower = text.lower()
    scores = {'therapeutic_feeding': 0, 'micronutrient': 0,
              'mortality': 0, 'recovery_growth': 0}
    for kw in THERAPEUTIC_FEEDING_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['therapeutic_feeding'] += 1
    for kw in MICRONUTRIENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['micronutrient'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    for kw in RECOVERY_GROWTH_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['recovery_growth'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_malnutrition', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_malnutrition_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'therapeutic_feeding': THERAPEUTIC_FEEDING_PATTERNS['endpoint_patterns'],
        'micronutrient': MICRONUTRIENT_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
        'recovery_growth': RECOVERY_GROWTH_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_malnutrition_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical malnutrition endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in MALNUTRITION_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
