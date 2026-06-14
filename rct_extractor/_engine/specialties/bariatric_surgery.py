"""
Bariatric / Metabolic Surgery Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow. Bariatric-surgery RCTs (Roux-en-Y
gastric bypass, sleeve gastrectomy, one-anastomosis gastric bypass, gastric
banding, vs each other or vs medical therapy) report a distinct endpoint
vocabulary - percent total / excess weight loss, type-2-diabetes remission,
anastomotic leak, reoperation, nutritional deficiency - that is NOT covered by
the pharmacological obesity specialty (GLP-1 / weight-loss drugs) or diabetes.

Subspecialties:
- weight: percent total weight loss (%TWL), percent excess weight loss (%EWL),
  BMI change - the continuous weight readouts.
- metabolic: type-2-diabetes remission, hypertension / dyslipidaemia remission,
  HbA1c (glycaemic control).
- complications: postoperative / major complications, anastomotic / staple-line
  leak, reoperation, 30-day mortality.
- nutritional: nutritional / micronutrient deficiency, iron-deficiency anaemia.

Drug / procedure classes (arm labels): Roux-en-Y gastric bypass (RYGB), sleeve
gastrectomy (SG), one-anastomosis gastric bypass (OAGB), adjustable gastric
banding (LAGB), biliopancreatic diversion / duodenal switch (BPD/DS), intragastric
balloon, medical / lifestyle therapy.

Effect measures: remission / complication / leak / reoperation / mortality ->
RR/OR/HR; %TWL / %EWL / BMI / HbA1c -> MD/SMD (continuous, natural scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# BARIATRIC-SURGERY ENDPOINTS
# ============================================================

BARIATRIC_SURGERY_ENDPOINTS = {
    # --- weight (continuous) ---
    'TOTAL_WEIGHT_LOSS': {
        'aliases': ['percent total weight loss', 'percentage total weight loss',
                    'total body weight loss', 'total weight loss', '%twl', 'twl'],
        'subspecialty': 'weight',
        'measure_types': ['MD', 'SMD']
    },
    'EXCESS_WEIGHT_LOSS': {
        'aliases': ['percent excess weight loss', 'percentage excess weight loss',
                    'excess weight loss', 'excess body weight loss', '%ewl', 'ewl'],
        'subspecialty': 'weight',
        'measure_types': ['MD', 'SMD']
    },
    'BMI_CHANGE': {
        'aliases': ['change in body mass index', 'change in bmi', 'bmi reduction',
                    'body mass index', 'bmi'],
        'subspecialty': 'weight',
        'measure_types': ['MD', 'SMD']
    },

    # --- metabolic ---
    'DIABETES_REMISSION': {
        'aliases': ['type 2 diabetes remission', 'remission of type 2 diabetes',
                    'diabetes remission', 'remission of diabetes', 'glycaemic remission',
                    'glycemic remission', 'complete diabetes remission'],
        'subspecialty': 'metabolic',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HYPERTENSION_REMISSION': {
        'aliases': ['hypertension remission', 'remission of hypertension',
                    'resolution of hypertension'],
        'subspecialty': 'metabolic',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'DYSLIPIDAEMIA_REMISSION': {
        'aliases': ['dyslipidaemia remission', 'dyslipidemia remission',
                    'resolution of dyslipidaemia', 'resolution of dyslipidemia'],
        'subspecialty': 'metabolic',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HBA1C': {
        'aliases': ['glycated haemoglobin', 'glycated hemoglobin', 'haemoglobin a1c',
                    'hemoglobin a1c', 'hba1c'],
        'subspecialty': 'metabolic',
        'measure_types': ['MD', 'SMD']
    },

    # --- complications ---
    'POSTOP_COMPLICATION': {
        'aliases': ['postoperative complications', 'postoperative complication',
                    'major complications', 'major complication', 'overall complications',
                    'clavien-dindo', '30-day complications'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ANASTOMOTIC_LEAK': {
        'aliases': ['anastomotic leak', 'staple-line leak', 'staple line leak',
                    'gastric leak', 'leak'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'REOPERATION': {
        'aliases': ['reoperation', 're-operation', 'revisional surgery', 'revision surgery',
                    'reintervention'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'MORTALITY': {
        'aliases': ['30-day mortality', '30 day mortality', 'all-cause mortality',
                    'all cause mortality', 'perioperative mortality', 'mortality', 'death'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- nutritional ---
    'NUTRITIONAL_DEFICIENCY': {
        'aliases': ['nutritional deficiency', 'micronutrient deficiency', 'vitamin deficiency',
                    'iron deficiency', 'protein malnutrition', 'nutritional deficiencies'],
        'subspecialty': 'nutritional',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ANAEMIA': {
        'aliases': ['iron-deficiency anaemia', 'iron deficiency anemia', 'anaemia', 'anemia'],
        'subspecialty': 'nutritional',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# WEIGHT PATTERNS (continuous)
# ============================================================

WEIGHT_PATTERNS = {
    'detection_keywords': [
        r'(?:percent(?:age)?\s+)?total\s+(?:body\s+)?weight\s+loss|\btwl\b',
        r'(?:percent(?:age)?\s+)?excess\s+(?:body\s+)?weight\s+loss|\bewl\b',
        r'change\s+in\s+(?:body\s+mass\s+index|bmi)|bmi\s+reduction', r'weight\s+loss',
    ],
    'endpoint_patterns': [
        (r'(?:percent(?:age)?\s+)?excess\s+(?:body\s+)?weight\s+loss|%?\s*ewl', 'EXCESS_WEIGHT_LOSS'),
        (r'(?:percent(?:age)?\s+)?total\s+(?:body\s+)?weight\s+loss|%?\s*twl', 'TOTAL_WEIGHT_LOSS'),
        (r'change\s+in\s+(?:body\s+mass\s+index|bmi)|bmi\s+reduction|body\s+mass\s+index|\bbmi\b',
         'BMI_CHANGE'),
    ],
    'context_patterns': [
        r'kg|kg/m2', r'at\s+(?:12|24|36|60)\s+months', r'percentage\s+points',
    ]
}


# ============================================================
# METABOLIC PATTERNS
# ============================================================

METABOLIC_PATTERNS = {
    'detection_keywords': [
        r'(?:type\s+2\s+)?diabetes\s+remission|remission\s+of\s+(?:type\s+2\s+)?diabetes',
        r'gly(?:ca|ce)emic\s+remission', r'hypertension\s+remission|remission\s+of\s+hypertension',
        r'dyslipid(?:ae|e)mia\s+remission', r'gly(?:ca|ce)ted\s+h(?:ae|e)moglobin|\bhba1c\b',
    ],
    'endpoint_patterns': [
        (r'(?:complete\s+)?(?:type\s+2\s+)?diabetes\s+remission|remission\s+of\s+(?:type\s+2\s+)?diabetes|'
         r'gly(?:ca|ce)emic\s+remission', 'DIABETES_REMISSION'),
        (r'hypertension\s+remission|remission\s+of\s+hypertension|resolution\s+of\s+hypertension',
         'HYPERTENSION_REMISSION'),
        (r'dyslipid(?:ae|e)mia\s+remission|resolution\s+of\s+dyslipid(?:ae|e)mia',
         'DYSLIPIDAEMIA_REMISSION'),
        (r'gly(?:ca|ce)ted\s+h(?:ae|e)moglobin|h(?:ae|e)moglobin\s+a1c|\bhba1c\b', 'HBA1C'),
    ],
    'context_patterns': [
        r'hba1c\s*<\s*6', r'off\s+(?:diabetes\s+)?medication', r'\d+\s+months',
    ]
}


# ============================================================
# COMPLICATIONS PATTERNS
# ============================================================

COMPLICATIONS_PATTERNS = {
    'detection_keywords': [
        r'postoperative\s+complications?|major\s+complications?', r'clavien[- ]dindo',
        r'anastomotic\s+leak|staple[- ]line\s+leak', r'reoperation|revisional\s+surgery',
        r'30[- ]day\s+mortality|perioperative\s+mortality',
    ],
    'endpoint_patterns': [
        (r'anastomotic\s+leak|staple[- ]line\s+leak|gastric\s+leak', 'ANASTOMOTIC_LEAK'),
        (r'reoperation|re[- ]operation|revisional?\s+surgery|reintervention', 'REOPERATION'),
        (r'30[- ]day\s+mortality|perioperative\s+mortality|all[- ]cause\s+mortality|\bmortality\b',
         'MORTALITY'),
        (r'(?:postoperative|major|overall|30[- ]day)\s+complications?|clavien[- ]dindo', 'POSTOP_COMPLICATION'),
    ],
    'context_patterns': [
        r'grade\s+(?:ii?i?|[1-4])', r'within\s+30\s+days', r'reintervention',
    ]
}


# ============================================================
# NUTRITIONAL PATTERNS
# ============================================================

NUTRITIONAL_PATTERNS = {
    'detection_keywords': [
        r'(?:nutritional|micronutrient|vitamin|iron)\s+deficienc(?:y|ies)',
        r'iron[- ]deficiency\s+an(?:ae|e)mia|\ban(?:ae|e)mia\b', r'protein\s+malnutrition',
    ],
    'endpoint_patterns': [
        (r'iron[- ]deficiency\s+an(?:ae|e)mia|\ban(?:ae|e)mia\b', 'ANAEMIA'),
        (r'(?:nutritional|micronutrient|vitamin|iron)\s+deficienc(?:y|ies)|protein\s+malnutrition',
         'NUTRITIONAL_DEFICIENCY'),
    ],
    'context_patterns': [
        r'supplement', r'serum\s+(?:ferritin|vitamin)', r'\d+\s+months',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_bariatric_surgery_subspecialty(text: str) -> Tuple[str, float]:
    """Detect bariatric-surgery trial subspecialty. Returns (subspecialty,
    confidence). Subspecialties: weight, metabolic, complications, nutritional,
    general_bariatric."""
    text_lower = text.lower()
    scores = {'weight': 0, 'metabolic': 0, 'complications': 0, 'nutritional': 0}
    for kw in WEIGHT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['weight'] += 1
    for kw in METABOLIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['metabolic'] += 1
    for kw in COMPLICATIONS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['complications'] += 1
    for kw in NUTRITIONAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['nutritional'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_bariatric', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_bariatric_surgery_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'weight': WEIGHT_PATTERNS['endpoint_patterns'],
        'metabolic': METABOLIC_PATTERNS['endpoint_patterns'],
        'complications': COMPLICATIONS_PATTERNS['endpoint_patterns'],
        'nutritional': NUTRITIONAL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_bariatric_surgery_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical bariatric-surgery endpoint, preferring the LONGEST
    matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in BARIATRIC_SURGERY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
