"""
Obesity / Weight-Management Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow as the diabetes / dyslipidaemia profiles.
Obesity RCTs (anti-obesity pharmacotherapy, lifestyle, bariatric surgery) report a
distinct endpoint vocabulary (percent body-weight change, categorical weight-loss
responder thresholds, waist circumference, GI tolerability) that overlaps but is
NOT identical to the diabetes glycaemic vocabulary.

Subspecialties:
- weight_loss: percent change in body weight, absolute weight change (kg), BMI
  change, and the categorical responder thresholds (>=5% / >=10% / >=15% / >=20%
  weight loss) that anti-obesity trials adjudicate as primary endpoints.
- body_composition: waist circumference, fat mass, visceral adipose tissue.
- cardiometabolic: secondary metabolic outcomes reported in weight trials —
  systolic blood pressure, HbA1c, lipids (as continuous change).
- safety: gastrointestinal adverse events (nausea, vomiting, diarrhoea — the
  GLP-1/GIP class signal), treatment discontinuation, gallbladder events.

Drug / intervention classes (arm labels): GLP-1 receptor agonists (semaglutide,
liraglutide, dulaglutide, exenatide), dual GIP/GLP-1 (tirzepatide) and triple
agonist (retatrutide), orlistat, phentermine-topiramate, naltrexone-bupropion,
setmelanotide, lifestyle / diet, bariatric surgery, placebo.

Effect measures: weight (%/kg), BMI, waist, fat mass, SBP, HbA1c, lipids ->
MD/SMD (continuous, natural scale); responder thresholds, GI adverse events,
discontinuation -> RR/OR/RD (binary).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# OBESITY ENDPOINTS
# ============================================================

OBESITY_ENDPOINTS = {
    # --- weight_loss ---
    'BODY_WEIGHT_PCT_CHANGE': {
        'aliases': ['percent change in body weight', 'percentage change in body weight',
                    'percent body weight change', 'percent weight loss', 'percentage weight loss',
                    'percent reduction in body weight', 'body weight reduction', 'relative weight change',
                    'change in body weight', 'body weight change', 'weight loss'],
        'subspecialty': 'weight_loss',
        'measure_types': ['MD', 'SMD']
    },
    'WEIGHT_CHANGE_KG': {
        'aliases': ['absolute weight change', 'weight change in kg', 'change in weight',
                    'absolute change in body weight', 'weight loss in kilograms', 'body weight (kg)'],
        'subspecialty': 'weight_loss',
        'measure_types': ['MD', 'SMD']
    },
    'BMI_CHANGE': {
        'aliases': ['change in body mass index', 'bmi change', 'change in bmi',
                    'reduction in body mass index', 'body mass index change', 'body mass index'],
        'subspecialty': 'weight_loss',
        'measure_types': ['MD', 'SMD']
    },
    'WEIGHT_LOSS_5PCT': {
        'aliases': ['weight loss of at least 5%', 'at least 5% weight loss', '5% weight loss',
                    '>=5% weight loss', 'achieving 5% weight loss', '5% or greater weight loss',
                    'weight loss >=5%'],
        'subspecialty': 'weight_loss',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'WEIGHT_LOSS_10PCT': {
        'aliases': ['weight loss of at least 10%', 'at least 10% weight loss', '10% weight loss',
                    '>=10% weight loss', 'achieving 10% weight loss', '10% or greater weight loss',
                    'weight loss >=10%'],
        'subspecialty': 'weight_loss',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'WEIGHT_LOSS_15PCT': {
        'aliases': ['weight loss of at least 15%', 'at least 15% weight loss', '15% weight loss',
                    '>=15% weight loss', 'achieving 15% weight loss', '15% or greater weight loss',
                    'weight loss >=15%', 'weight loss of at least 20%', '20% weight loss',
                    '>=20% weight loss'],
        'subspecialty': 'weight_loss',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- body_composition ---
    'WAIST_CIRCUMFERENCE': {
        'aliases': ['waist circumference reduction', 'change in waist circumference',
                    'reduction in waist circumference', 'waist circumference change',
                    'waist circumference'],
        'subspecialty': 'body_composition',
        'measure_types': ['MD', 'SMD']
    },
    'FAT_MASS': {
        'aliases': ['fat mass reduction', 'change in fat mass', 'total fat mass',
                    'body fat mass', 'fat mass', 'visceral adipose tissue', 'visceral fat'],
        'subspecialty': 'body_composition',
        'measure_types': ['MD', 'SMD']
    },

    # --- cardiometabolic (secondary continuous) ---
    'SBP_CHANGE': {
        'aliases': ['change in systolic blood pressure', 'systolic blood pressure reduction',
                    'reduction in systolic blood pressure', 'systolic blood pressure'],
        'subspecialty': 'cardiometabolic',
        'measure_types': ['MD', 'SMD']
    },
    'HBA1C_CHANGE': {
        'aliases': ['change in hba1c', 'hba1c reduction', 'reduction in hba1c',
                    'glycated haemoglobin change', 'glycated hemoglobin change', 'hba1c'],
        'subspecialty': 'cardiometabolic',
        'measure_types': ['MD', 'SMD']
    },

    # --- safety ---
    'GI_ADVERSE_EVENTS': {
        'aliases': ['gastrointestinal adverse events', 'nausea', 'vomiting', 'diarrhoea',
                    'diarrhea', 'gastrointestinal adverse event', 'gi adverse events',
                    'gastrointestinal disorders'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'DISCONTINUATION': {
        'aliases': ['treatment discontinuation', 'discontinuation due to adverse events',
                    'study drug discontinuation', 'discontinuation', 'permanent discontinuation'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'GALLBLADDER_EVENTS': {
        'aliases': ['gallbladder-related events', 'cholelithiasis', 'cholecystitis',
                    'gallbladder disorders', 'gallstones'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# WEIGHT-LOSS PATTERNS
# ============================================================

WEIGHT_LOSS_PATTERNS = {
    'detection_keywords': [
        r'body\s+weight', r'weight\s+loss', r'weight\s+reduction', r'percent\s+weight',
        r'body\s+mass\s+index|\bbmi\b', r'(?:>=?|at\s+least\s+)\s*\d+\s*%\s+weight',
        r'weight\s+management', r'weight[- ]loss\s+(?:of|threshold)',
    ],
    'endpoint_patterns': [
        (r'(?:weight\s+loss\s+of\s+at\s+least\s+|at\s+least\s+|>=?\s*|achieving\s+)?'
         r'(?:5|five)\s*%(?:\s+(?:or\s+greater\s+)?weight\s+loss)?|weight\s+loss\s+(?:of\s+)?(?:>=?\s*)?5\s*%',
         'WEIGHT_LOSS_5PCT'),
        (r'(?:weight\s+loss\s+of\s+at\s+least\s+|at\s+least\s+|>=?\s*|achieving\s+)?'
         r'(?:10|ten)\s*%(?:\s+(?:or\s+greater\s+)?weight\s+loss)?|weight\s+loss\s+(?:of\s+)?(?:>=?\s*)?10\s*%',
         'WEIGHT_LOSS_10PCT'),
        (r'(?:weight\s+loss\s+of\s+at\s+least\s+|at\s+least\s+|>=?\s*|achieving\s+)?'
         r'(?:15|20|fifteen|twenty)\s*%(?:\s+(?:or\s+greater\s+)?weight\s+loss)?', 'WEIGHT_LOSS_15PCT'),
        (r'(?:percent(?:age)?\s+(?:change|reduction)\s+in\s+body\s+weight|percent\s+body\s+weight\s+change|'
         r'percent(?:age)?\s+weight\s+loss|body\s+weight\s+reduction|change\s+in\s+body\s+weight|'
         r'body\s+weight\s+change)', 'BODY_WEIGHT_PCT_CHANGE'),
        (r'change\s+in\s+body\s+mass\s+index|bmi\s+change|change\s+in\s+bmi|'
         r'reduction\s+in\s+body\s+mass\s+index', 'BMI_CHANGE'),
        (r'absolute\s+(?:weight\s+change|change\s+in\s+body\s+weight)|weight\s+change\s+in\s+kg|'
         r'weight\s+loss\s+in\s+kilograms', 'WEIGHT_CHANGE_KG'),
    ],
    'context_patterns': [
        r'\bkg\b|kilograms?', r'baseline\s+to\s+week\s+\d+', r'percent\s+change', r'co[- ]primary',
    ]
}


# ============================================================
# BODY-COMPOSITION PATTERNS
# ============================================================

BODY_COMPOSITION_PATTERNS = {
    'detection_keywords': [
        r'waist\s+circumference', r'fat\s+mass', r'visceral\s+(?:adipose|fat)',
        r'body\s+composition', r'lean\s+(?:body\s+)?mass',
    ],
    'endpoint_patterns': [
        (r'(?:reduction\s+in\s+|change\s+in\s+)?waist\s+circumference(?:\s+reduction|\s+change)?',
         'WAIST_CIRCUMFERENCE'),
        (r'(?:total\s+|body\s+)?fat\s+mass(?:\s+reduction)?|visceral\s+(?:adipose\s+tissue|fat)',
         'FAT_MASS'),
    ],
    'context_patterns': [
        r'\bcm\b|centimet', r'dxa|dual[- ]energy', r'\bkg\b',
    ]
}


# ============================================================
# CARDIOMETABOLIC PATTERNS (secondary continuous)
# ============================================================

CARDIOMETABOLIC_PATTERNS = {
    'detection_keywords': [
        r'systolic\s+blood\s+pressure', r'hba1c|glycated\s+h[ae]moglobin',
        r'lipid|cholesterol|triglycerid', r'cardiometabolic',
    ],
    'endpoint_patterns': [
        (r'(?:reduction\s+in\s+|change\s+in\s+)?systolic\s+blood\s+pressure(?:\s+reduction)?',
         'SBP_CHANGE'),
        (r'(?:change\s+in\s+|reduction\s+in\s+)?hba1c|glycated\s+h[ae]moglobin\s+change', 'HBA1C_CHANGE'),
    ],
    'context_patterns': [
        r'mm\s?hg', r'mmol/mol|%', r'secondary\s+(?:outcome|endpoint)',
    ]
}


# ============================================================
# SAFETY PATTERNS
# ============================================================

SAFETY_PATTERNS = {
    'detection_keywords': [
        r'gastrointestinal\s+adverse', r'\bnausea\b', r'\bvomiting\b', r'diarrh',
        r'(?:treatment|study\s+drug)\s+discontinuation', r'gallbladder|cholelithiasis|cholecystitis',
        r'adverse\s+events',
    ],
    'endpoint_patterns': [
        (r'gastrointestinal\s+(?:adverse\s+events?|disorders)|\bnausea\b|\bvomiting\b|'
         r'diarrh(?:oea|ea)', 'GI_ADVERSE_EVENTS'),
        (r'gallbladder[- ]related\s+events|gallbladder\s+disorders|cholelithiasis|cholecystitis|'
         r'gallstones', 'GALLBLADDER_EVENTS'),
        (r'(?:treatment|study\s+drug|permanent)\s+discontinuation|'
         r'discontinuation\s+due\s+to\s+adverse\s+events|\bdiscontinuation\b', 'DISCONTINUATION'),
    ],
    'context_patterns': [
        r'tolerability', r'most\s+common\s+adverse', r'\bsafety\b',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_obesity_subspecialty(text: str) -> Tuple[str, float]:
    """Detect obesity trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: weight_loss, body_composition, cardiometabolic, safety,
    general_obesity."""
    text_lower = text.lower()
    scores = {'weight_loss': 0, 'body_composition': 0, 'cardiometabolic': 0, 'safety': 0}
    for kw in WEIGHT_LOSS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['weight_loss'] += 1
    for kw in BODY_COMPOSITION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['body_composition'] += 1
    for kw in CARDIOMETABOLIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['cardiometabolic'] += 1
    for kw in SAFETY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['safety'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_obesity', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_obesity_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'weight_loss': WEIGHT_LOSS_PATTERNS['endpoint_patterns'],
        'body_composition': BODY_COMPOSITION_PATTERNS['endpoint_patterns'],
        'cardiometabolic': CARDIOMETABOLIC_PATTERNS['endpoint_patterns'],
        'safety': SAFETY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_obesity_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical obesity endpoint, preferring the LONGEST matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in OBESITY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
