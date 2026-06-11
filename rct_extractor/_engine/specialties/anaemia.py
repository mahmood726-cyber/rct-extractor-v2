"""
Iron-Deficiency & Other Anaemia Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the tuberculosis / ARDS profiles.
Anaemia RCTs (iron-deficiency anaemia, anaemia of chronic kidney disease, cancer-
and inflammation-related anaemia, nutritional anaemia) report a distinct endpoint
vocabulary (haemoglobin change / response, proportion reaching a target Hb,
red-cell transfusion requirement, ferritin / transferrin saturation, anaemia
correction) that the generic effect-size engine does not recognise on its own.

Subspecialties:
- Iron therapy: oral iron (ferrous sulfate/fumarate) vs intravenous iron (ferric
  carboxymaltose, iron sucrose, ferric derisomaltose, iron isomaltoside), Hb
  response, ferritin / transferrin saturation repletion.
- ESA (erythropoiesis-stimulating agents): epoetin alfa/beta, darbepoetin,
  methoxy-PEG-epoetin and HIF-PHI (roxadustat, daprodustat, vadadustat) for
  anaemia of CKD / cancer.
- Nutritional: iron + folic acid supplementation, vitamin B12, fortification,
  deworming-linked anaemia control (maternal / paediatric / population).
- Transfusion-related anaemia: red-cell transfusion requirement / avoidance,
  perioperative and critical-illness anaemia management.

Effect measures follow what these trials report: binary (Hb / anaemia target
response, transfusion requirement, anaemia resolution) -> RR/OR/RD; continuous
(haemoglobin change, ferritin, transferrin saturation, reticulocyte) -> mean
difference, handled by the shared continuous augmenter.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# ANAEMIA ENDPOINTS
# ============================================================

ANAEMIA_ENDPOINTS = {
    'HB_CHANGE': {
        'aliases': ['haemoglobin change', 'hemoglobin change', 'change in haemoglobin',
                    'change in hemoglobin', 'haemoglobin increase', 'hemoglobin increase',
                    'mean haemoglobin', 'mean hemoglobin', 'haemoglobin level',
                    'hemoglobin level', 'hb change', 'hb increase', 'haemoglobin concentration',
                    'hemoglobin concentration', 'rise in haemoglobin', 'rise in hemoglobin'],
        'subspecialty': 'iron_therapy',
        'measure_types': ['MD']
    },
    'HB_RESPONSE': {
        'aliases': ['haemoglobin response', 'hemoglobin response', 'haematologic response',
                    'hematologic response', 'haematological response', 'hematological response',
                    'target haemoglobin', 'target hemoglobin', 'hb target',
                    'haemoglobin responders', 'hemoglobin responders',
                    'achieved target haemoglobin', 'haemoglobin normalization',
                    'hemoglobin normalization', 'erythroid response'],
        'subspecialty': 'esa',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ANAEMIA_CORRECTION': {
        'aliases': ['anaemia correction', 'anemia correction', 'correction of anaemia',
                    'correction of anemia', 'resolution of anaemia', 'resolution of anemia',
                    'anaemia resolution', 'anemia resolution', 'no longer anaemic',
                    'anaemia recovery', 'anemia recovery', 'cured of anaemia'],
        'subspecialty': 'nutritional',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TRANSFUSION': {
        'aliases': ['blood transfusion', 'red blood cell transfusion', 'rbc transfusion',
                    'transfusion requirement', 'need for transfusion',
                    'transfusion avoidance', 'transfusion rate', 'units transfused',
                    'allogeneic transfusion', 'transfusion of red cells',
                    'red-cell transfusion', 'proportion transfused'],
        'subspecialty': 'transfusion_anaemia',
        'measure_types': ['RR', 'OR', 'RD', 'MD']
    },
    'FERRITIN': {
        'aliases': ['ferritin', 'serum ferritin', 'ferritin level', 'iron stores',
                    'change in ferritin'],
        'subspecialty': 'iron_therapy',
        'measure_types': ['MD']
    },
    'TSAT': {
        'aliases': ['transferrin saturation', 'tsat', 'iron saturation',
                    'transferrin saturation index'],
        'subspecialty': 'iron_therapy',
        'measure_types': ['MD']
    },
    'RETICULOCYTE': {
        'aliases': ['reticulocyte', 'reticulocyte count', 'reticulocyte haemoglobin',
                    'reticulocyte hemoglobin', 'absolute reticulocyte count'],
        'subspecialty': 'iron_therapy',
        'measure_types': ['MD']
    },
    'IRON_DEFICIENCY': {
        'aliases': ['iron deficiency', 'iron-deficiency', 'iron repletion',
                    'resolution of iron deficiency', 'iron status'],
        'subspecialty': 'iron_therapy',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'FATIGUE': {
        'aliases': ['fatigue', 'fatigue score', 'facit-fatigue', 'quality of life',
                    'physical function', 'vitality'],
        'subspecialty': 'esa',
        'measure_types': ['MD']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'survival'],
        'subspecialty': 'transfusion_anaemia',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'serious adverse events', 'hypophosphataemia',
                    'hypophosphatemia', 'hypersensitivity', 'thromboembolic events',
                    'gastrointestinal adverse events', 'cardiovascular events',
                    'injection-site reactions'],
        'subspecialty': 'iron_therapy',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# IRON THERAPY PATTERNS
# ============================================================

IRON_THERAPY_PATTERNS = {
    'detection_keywords': [
        r'iron[- ]deficiency\s+an(?:ae|e)mia|\bida\b',
        r'intravenous\s+iron|\biv\s+iron\b|oral\s+iron|ferrous\s+(?:sulfate|sulphate|fumarate)',
        r'ferric\s+carboxymaltose|\bfcm\b|iron\s+sucrose|ferric\s+derisomaltose|iron\s+isomaltoside',
        r'ferric\s+(?:gluconate|maltol)|sodium\s+ferric',
        r'ferritin|transferrin\s+saturation|\btsat\b|iron\s+stores',
        r'h(?:ae|e)moglobin\s+(?:response|change|increase|increment)',
    ],
    'endpoint_patterns': [
        (r'transferrin\s+saturation|\btsat\b|iron\s+saturation', 'TSAT'),
        (r'(?:serum\s+)?ferritin|iron\s+stores', 'FERRITIN'),
        (r'reticulocyte', 'RETICULOCYTE'),
        (r'h(?:ae|e)moglobin\s+(?:response|target|responders|normali[sz]ation)|'
         r'h(?:ae|e)matolog\w+\s+response|target\s+h(?:ae|e)moglobin', 'HB_RESPONSE'),
        (r'(?:change\s+in\s+|increase\s+in\s+|rise\s+in\s+|mean\s+)?h(?:ae|e)moglobin'
         r'(?:\s+(?:change|increase|increment|level|concentration))?|\bhb\s+(?:change|increase)\b',
         'HB_CHANGE'),
        (r'iron\s+deficiency|iron\s+repletion|iron\s+status', 'IRON_DEFICIENCY'),
        (r'(?:red[- ](?:blood[- ])?cell\s+|rbc\s+|blood\s+)?transfusion', 'TRANSFUSION'),
        (r'hypophosphat(?:ae|e)mia|hypersensitivity|injection[- ]site|thromboembolic',
         'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'g/dl|g/l|mmol/l', r'baseline\s+h(?:ae|e)moglobin', r'week\s+(?:8|12)\s+h(?:ae|e)moglobin',
    ]
}


# ============================================================
# ESA PATTERNS
# ============================================================

ESA_PATTERNS = {
    'detection_keywords': [
        r'erythropoiesis[- ]stimulating\s+agent|\besa\b|erythropoietin',
        r'epoetin|darbepoetin|methoxy[- ]?polyethylene\s+glycol[- ]?epoetin',
        r'hif[- ]?ph(?:i|\s+inhibitor)|roxadustat|daprodustat|vadadustat|molidustat',
        r'an(?:ae|e)mia\s+of\s+(?:ckd|chronic\s+kidney|cancer|inflammation)',
        r'h(?:ae|e)moglobin\s+target|target\s+h(?:ae|e)moglobin',
    ],
    'endpoint_patterns': [
        (r'h(?:ae|e)moglobin\s+(?:response|target|responders|normali[sz]ation)|'
         r'h(?:ae|e)matolog\w+\s+response|target\s+h(?:ae|e)moglobin|erythroid\s+response',
         'HB_RESPONSE'),
        (r'(?:change\s+in\s+|mean\s+)?h(?:ae|e)moglobin(?:\s+(?:change|level|concentration))?',
         'HB_CHANGE'),
        (r'(?:red[- ](?:blood[- ])?cell\s+|rbc\s+|blood\s+)?transfusion', 'TRANSFUSION'),
        (r'fatigue|facit[- ]fatigue|quality\s+of\s+life|vitality', 'FATIGUE'),
        (r'thromboembolic|cardiovascular\s+events?|serious\s+adverse', 'ADVERSE_EVENTS'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)|survival', 'MORTALITY'),
    ],
    'context_patterns': [
        r'dialysis|non[- ]dialysis|ckd\s+stage', r'darbepoetin\s+alfa',
    ]
}


# ============================================================
# NUTRITIONAL PATTERNS
# ============================================================

NUTRITIONAL_PATTERNS = {
    'detection_keywords': [
        r'iron\s+(?:and\s+)?folic\s+acid|iron[- ]folate|folic\s+acid\s+supplement',
        r'micronutrient|multiple\s+micronutrient|fortif\w+',
        r'vitamin\s+b12|cobalamin|folate\s+deficiency',
        r'maternal\s+an(?:ae|e)mia|gestational\s+an(?:ae|e)mia|an(?:ae|e)mia\s+in\s+pregnancy',
        r'an(?:ae|e)mia\s+(?:prevalence|control|prevention)',
    ],
    'endpoint_patterns': [
        (r'an(?:ae|e)mia\s+(?:correction|resolution|recovery)|correction\s+of\s+an(?:ae|e)mia|'
         r'resolution\s+of\s+an(?:ae|e)mia|no\s+longer\s+an(?:ae|e)mic', 'ANAEMIA_CORRECTION'),
        (r'h(?:ae|e)moglobin\s+(?:response|target|responders)', 'HB_RESPONSE'),
        (r'(?:change\s+in\s+|increase\s+in\s+|mean\s+)?h(?:ae|e)moglobin'
         r'(?:\s+(?:change|increase|level|concentration))?', 'HB_CHANGE'),
        (r'(?:serum\s+)?ferritin|iron\s+stores', 'FERRITIN'),
        (r'iron\s+deficiency|iron\s+status', 'IRON_DEFICIENCY'),
        (r'an(?:ae|e)mia\s+(?:prevalence|at\s+endline)', 'ANAEMIA_CORRECTION'),
    ],
    'context_patterns': [
        r'antenatal|pregnant\s+women', r'preschool|school[- ]age\s+children', r'endline',
    ]
}


# ============================================================
# TRANSFUSION-RELATED ANAEMIA PATTERNS
# ============================================================

TRANSFUSION_ANAEMIA_PATTERNS = {
    'detection_keywords': [
        r'red[- ](?:blood[- ])?cell\s+transfusion|\brbc\s+transfusion\b|blood\s+transfusion',
        r'transfusion\s+(?:requirement|avoidance|rate|threshold)',
        r'perioperative\s+an(?:ae|e)mia|preoperative\s+an(?:ae|e)mia',
        r'patient\s+blood\s+management|allogeneic\s+(?:blood\s+)?transfusion',
        r'critical\s+illness\s+an(?:ae|e)mia|an(?:ae|e)mia\s+in\s+(?:the\s+)?(?:icu|critically\s+ill)',
    ],
    'endpoint_patterns': [
        (r'(?:red[- ](?:blood[- ])?cell\s+|rbc\s+|blood\s+|allogeneic\s+)?transfusion'
         r'(?:\s+(?:requirement|avoidance|rate))?|units\s+transfused|proportion\s+transfused',
         'TRANSFUSION'),
        (r'(?:change\s+in\s+|mean\s+)?h(?:ae|e)moglobin(?:\s+(?:change|level|concentration))?',
         'HB_CHANGE'),
        (r'h(?:ae|e)moglobin\s+(?:response|target)', 'HB_RESPONSE'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)|survival', 'MORTALITY'),
        (r'serious\s+adverse|cardiovascular\s+events?', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'restrictive\s+(?:vs\.?\s+)?liberal', r'transfusion\s+threshold\s+of\s+\d',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_anaemia_subspecialty(text: str) -> Tuple[str, float]:
    """Detect anaemia trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: iron_therapy, esa, nutritional, transfusion_anaemia,
    general_anaemia."""
    text_lower = text.lower()
    scores = {'iron_therapy': 0, 'esa': 0,
              'nutritional': 0, 'transfusion_anaemia': 0}
    for kw in IRON_THERAPY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['iron_therapy'] += 1
    for kw in ESA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['esa'] += 1
    for kw in NUTRITIONAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['nutritional'] += 1
    for kw in TRANSFUSION_ANAEMIA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['transfusion_anaemia'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_anaemia', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_anaemia_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'iron_therapy': IRON_THERAPY_PATTERNS['endpoint_patterns'],
        'esa': ESA_PATTERNS['endpoint_patterns'],
        'nutritional': NUTRITIONAL_PATTERNS['endpoint_patterns'],
        'transfusion_anaemia': TRANSFUSION_ANAEMIA_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_anaemia_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical anaemia endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in ANAEMIA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
