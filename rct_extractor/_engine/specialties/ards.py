"""
ARDS / Acute Respiratory Failure Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the tuberculosis / sepsis profiles.
Acute respiratory distress syndrome (ARDS) and acute respiratory-failure RCTs
report a distinct critical-care endpoint vocabulary (28-/90-day mortality,
ventilator-free days, oxygenation index / PaO2:FiO2, barotrauma, successful
extubation, ICU/hospital length of stay) that the generic effect-size engine
does not recognise on its own.

Subspecialties:
- Ventilation (mechanical-ventilation strategy): lung-protective / low tidal
  volume, higher vs lower PEEP, recruitment manoeuvres, prone positioning,
  high-frequency oscillatory ventilation (HFOV), driving-pressure-limited
  ventilation, ventilator-free days, barotrauma / pneumothorax.
- Pharmacotherapy: neuromuscular blockade (cisatracurium), corticosteroids
  (dexamethasone / methylprednisolone), inhaled pulmonary vasodilators (nitric
  oxide, epoprostenol), exogenous surfactant, statins / aspirin, vitamin C.
- Rescue / support (refractory hypoxaemia): veno-venous ECMO, extracorporeal
  CO2 removal (ECCO2R), prone positioning as rescue, oxygenation response.
- Supportive (general ICU management of respiratory failure): conservative vs
  liberal oxygen targets, conservative vs liberal fluid strategy, high-flow
  nasal oxygen vs NIV, sedation strategy, time to liberation from ventilation.

Effect measures follow what these trials report: binary (mortality, barotrauma,
successful extubation, treatment failure / intubation) -> RR/OR/RD/HR;
count/time outcomes (ventilator-free days, ICU-free days, length of stay,
PaO2:FiO2) -> mean difference, handled by the shared continuous augmenter.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# ARDS ENDPOINTS
# ============================================================

ARDS_ENDPOINTS = {
    # --- Mortality (the dominant ARDS RCT endpoint) ---
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality',
                    '28-day mortality', '28 day mortality', '28-day all-cause mortality',
                    '90-day mortality', '90 day mortality', '60-day mortality',
                    'icu mortality', 'in-icu mortality', 'hospital mortality',
                    'in-hospital mortality', 'intensive care unit mortality',
                    'mortality at day 28', 'mortality at day 90', 'overall survival',
                    'all-cause death'],
        'subspecialty': 'ventilation',
        'measure_types': ['RR', 'OR', 'HR', 'RD']
    },
    # --- Mechanical ventilation outcomes ---
    'VENTILATOR_FREE_DAYS': {
        'aliases': ['ventilator-free days', 'ventilator free days', 'vfd',
                    'ventilator-free days at day 28', 'days free of mechanical ventilation',
                    'days alive and free of ventilation',
                    'days alive without mechanical ventilation',
                    'ventilator-free days to day 28'],
        'subspecialty': 'ventilation',
        'measure_types': ['MD']
    },
    'BAROTRAUMA': {
        'aliases': ['barotrauma', 'pneumothorax', 'new pneumothorax',
                    'air leak', 'air-leak syndrome', 'subcutaneous emphysema',
                    'pneumomediastinum'],
        'subspecialty': 'ventilation',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'EXTUBATION': {
        'aliases': ['successful extubation', 'extubation', 'liberation from ventilation',
                    'liberation from mechanical ventilation',
                    'successful liberation', 'weaning success',
                    'time to extubation', 'time to liberation'],
        'subspecialty': 'ventilation',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'DRIVING_PRESSURE': {
        'aliases': ['driving pressure', 'plateau pressure', 'airway pressure'],
        'subspecialty': 'ventilation',
        'measure_types': ['MD']
    },

    # --- Pharmacotherapy outcomes ---
    'OXYGENATION': {
        'aliases': ['oxygenation', 'pao2:fio2', 'pao2/fio2', 'p/f ratio',
                    'pao2 to fio2 ratio', 'oxygenation index',
                    'partial pressure of oxygen to fraction of inspired oxygen',
                    'oxygenation improvement', 'change in oxygenation'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['MD']
    },
    'ORGAN_FAILURE': {
        'aliases': ['organ failure', 'new organ failure', 'organ-failure-free days',
                    'organ failure free days', 'multiorgan failure',
                    'multiple organ dysfunction', 'sofa score',
                    'non-pulmonary organ failure'],
        'subspecialty': 'pharmacotherapy',
        'measure_types': ['RR', 'OR', 'MD']
    },
    'TREATMENT_FAILURE': {
        'aliases': ['treatment failure', 'intubation', 'need for intubation',
                    'progression to intubation', 'rescue therapy',
                    'escalation of respiratory support', 'treatment escalation',
                    'requirement for invasive ventilation'],
        'subspecialty': 'supportive',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Rescue / support (refractory hypoxaemia) ---
    'RESCUE_THERAPY': {
        'aliases': ['rescue therapy', 'crossover to ecmo', 'use of ecmo',
                    'rescue ecmo', 'prone positioning as rescue',
                    'refractory hypoxaemia', 'refractory hypoxemia',
                    'salvage therapy'],
        'subspecialty': 'rescue',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Supportive / general ICU ---
    'ICU_FREE_DAYS': {
        'aliases': ['icu-free days', 'icu free days', 'intensive-care-unit-free days',
                    'days alive and out of the icu', 'icu-free days at day 28'],
        'subspecialty': 'supportive',
        'measure_types': ['MD']
    },
    'LENGTH_OF_STAY': {
        'aliases': ['length of stay', 'icu length of stay', 'hospital length of stay',
                    'duration of icu stay', 'duration of hospital stay',
                    'length of icu stay', 'length of hospital stay'],
        'subspecialty': 'supportive',
        'measure_types': ['MD']
    },
    'DURATION_VENTILATION': {
        'aliases': ['duration of mechanical ventilation', 'duration of ventilation',
                    'days of mechanical ventilation', 'time on the ventilator',
                    'duration of invasive ventilation'],
        'subspecialty': 'supportive',
        'measure_types': ['MD']
    },
    'ARDS_INCIDENCE': {
        'aliases': ['incidence of ards', 'development of ards', 'progression to ards',
                    'new ards', 'ards onset', 'acute respiratory distress syndrome'],
        'subspecialty': 'supportive',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# VENTILATION PATTERNS (mechanical-ventilation strategy)
# ============================================================

VENTILATION_PATTERNS = {
    'detection_keywords': [
        r'lung[- ]protective\s+ventilation|low\s+tidal\s+volume|tidal\s+volume',
        r'\bpeep\b|positive\s+end[- ]expiratory\s+pressure|higher\s+peep|lower\s+peep',
        r'recruitment\s+man(?:o?eu|eu)vre|recruitment\s+maneuver|open[- ]lung',
        r'prone\s+position(?:ing)?|proning',
        r'high[- ]frequency\s+oscillat\w+|\bhfov\b',
        r'driving\s+pressure|plateau\s+pressure',
        r'ventilator[- ]free\s+days|barotrauma|pneumothorax',
        r'mechanical\s+ventilation|mechanically\s+ventilated',
    ],
    'endpoint_patterns': [
        (r'ventilator[- ]free\s+days|days\s+(?:alive\s+and\s+)?free\s+of\s+(?:mechanical\s+)?ventilation',
         'VENTILATOR_FREE_DAYS'),
        (r'barotrauma|pneumothorax|air[- ]leak|pneumomediastinum|subcutaneous\s+emphysema',
         'BAROTRAUMA'),
        (r'successful\s+extubation|liberation\s+from\s+(?:mechanical\s+)?ventilation|'
         r'weaning\s+success|time\s+to\s+extubation', 'EXTUBATION'),
        (r'driving\s+pressure|plateau\s+pressure', 'DRIVING_PRESSURE'),
        (r'(?:28[- ]day|90[- ]day|60[- ]day|icu|in[- ]hospital|hospital|all[- ]cause)\s+'
         r'(?:mortality|death)|\bmortality\b|\bdeath\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'\d+\s*ml/kg\s+(?:predicted|ideal)\s+body\s+weight', r'berlin\s+definition',
        r'moderate[- ]to[- ]severe\s+ards', r'pao2[:/]fio2',
    ]
}


# ============================================================
# PHARMACOTHERAPY PATTERNS
# ============================================================

PHARMACOTHERAPY_PATTERNS = {
    'detection_keywords': [
        r'neuromuscular\s+block\w+|cisatracurium|\bnmba\b|muscle\s+relaxant',
        r'corticosteroid|dexamethasone|methylprednisolone|hydrocortisone',
        r'inhaled\s+nitric\s+oxide|\bino\b|epoprostenol|inhaled\s+prostacyclin',
        r'surfactant|exogenous\s+surfactant',
        r'\bstatin\b|simvastatin|rosuvastatin|aspirin|vitamin\s+c|ascorbic\s+acid',
        r'pao2[:/]fio2|oxygenation\s+index',
    ],
    'endpoint_patterns': [
        (r'pao2\s*[:/]\s*fio2|p\s*/\s*f\s+ratio|oxygenation\s+index|'
         r'(?:change\s+in\s+|improvement\s+in\s+)?oxygenation', 'OXYGENATION'),
        (r'organ[- ]failure[- ]free\s+days|new\s+organ\s+failure|multiorgan\s+failure|'
         r'multiple\s+organ\s+dysfunction|sofa\s+score', 'ORGAN_FAILURE'),
        (r'ventilator[- ]free\s+days', 'VENTILATOR_FREE_DAYS'),
        (r'(?:28[- ]day|90[- ]day|60[- ]day|icu|in[- ]hospital|hospital|all[- ]cause)\s+'
         r'(?:mortality|death)|\bmortality\b|\bdeath\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'continuous\s+infusion', r'48[- ]hour|early\s+course',
        r'moderate[- ]to[- ]severe\s+ards',
    ]
}


# ============================================================
# RESCUE PATTERNS (refractory hypoxaemia)
# ============================================================

RESCUE_PATTERNS = {
    'detection_keywords': [
        r'\becmo\b|extracorporeal\s+membrane\s+oxygenation|veno[- ]venous\s+ecmo|\bvv[- ]ecmo\b',
        r'extracorporeal\s+co2\s+removal|\becco2r\b',
        r'refractory\s+hypox(?:ae|e)mia|severe\s+hypox(?:ae|e)mia',
        r'rescue\s+(?:therapy|ecmo)|salvage\s+therapy',
        r'prone\s+position(?:ing)?',
    ],
    'endpoint_patterns': [
        (r'rescue\s+(?:therapy|ecmo)|crossover\s+to\s+ecmo|use\s+of\s+ecmo|'
         r'salvage\s+therapy|refractory\s+hypox(?:ae|e)mia', 'RESCUE_THERAPY'),
        (r'pao2\s*[:/]\s*fio2|oxygenation\s+index|oxygenation', 'OXYGENATION'),
        (r'(?:28[- ]day|90[- ]day|60[- ]day|icu|in[- ]hospital|hospital|all[- ]cause)\s+'
         r'(?:mortality|death)|\bmortality\b|\bdeath\b', 'MORTALITY'),
        (r'ventilator[- ]free\s+days', 'VENTILATOR_FREE_DAYS'),
    ],
    'context_patterns': [
        r'murray\s+score', r'pao2[:/]fio2\s*<\s*\d+', r'cesar|eolia',
    ]
}


# ============================================================
# SUPPORTIVE PATTERNS (general ICU management)
# ============================================================

SUPPORTIVE_PATTERNS = {
    'detection_keywords': [
        r'conservative\s+(?:vs\.?\s+liberal\s+)?oxygen|oxygen\s+target|spo2\s+target',
        r'conservative\s+(?:vs\.?\s+liberal\s+)?fluid|fluid\s+(?:strategy|management|balance)',
        r'high[- ]flow\s+nasal\s+(?:oxygen|cannula)|\bhfnc\b|\bhfno\b',
        r'non[- ]invasive\s+ventilation|\bniv\b|\bcpap\b',
        r'sedation\s+strategy|light\s+sedation',
        r'acute\s+(?:hypox(?:ae|e)mic\s+)?respiratory\s+failure|de[- ]novo\s+respiratory\s+failure',
    ],
    'endpoint_patterns': [
        (r'(?:need\s+for\s+|progression\s+to\s+|requirement\s+for\s+)?intubation|'
         r'treatment\s+failure|escalation\s+of\s+(?:respiratory\s+)?support|treatment\s+escalation',
         'TREATMENT_FAILURE'),
        (r'icu[- ]free\s+days|days\s+alive\s+and\s+out\s+of\s+the\s+icu', 'ICU_FREE_DAYS'),
        (r'(?:icu|hospital)\s+length\s+of\s+stay|length\s+of\s+(?:icu|hospital)\s+stay|'
         r'duration\s+of\s+(?:icu|hospital)\s+stay', 'LENGTH_OF_STAY'),
        (r'duration\s+of\s+(?:mechanical\s+|invasive\s+)?ventilation|'
         r'days\s+of\s+mechanical\s+ventilation', 'DURATION_VENTILATION'),
        (r'incidence\s+of\s+ards|development\s+of\s+ards|progression\s+to\s+ards|new\s+ards',
         'ARDS_INCIDENCE'),
        (r'(?:28[- ]day|90[- ]day|60[- ]day|icu|in[- ]hospital|hospital|all[- ]cause)\s+'
         r'(?:mortality|death)|\bmortality\b|\bdeath\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'spo2\s+(?:target|of)\s+\d+', r'liberal\s+vs\.?\s+conservative',
        r'p[- ]?sili|patient[- ]self[- ]inflicted\s+lung\s+injury',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_ards_subspecialty(text: str) -> Tuple[str, float]:
    """Detect ARDS / acute-respiratory-failure trial subspecialty.
    Returns (subspecialty, confidence).
    Subspecialties: ventilation, pharmacotherapy, rescue, supportive, general_ards."""
    text_lower = text.lower()
    scores = {'ventilation': 0, 'pharmacotherapy': 0, 'rescue': 0, 'supportive': 0}
    for kw in VENTILATION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['ventilation'] += 1
    for kw in PHARMACOTHERAPY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pharmacotherapy'] += 1
    for kw in RESCUE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['rescue'] += 1
    for kw in SUPPORTIVE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['supportive'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_ards', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_ards_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'ventilation': VENTILATION_PATTERNS['endpoint_patterns'],
        'pharmacotherapy': PHARMACOTHERAPY_PATTERNS['endpoint_patterns'],
        'rescue': RESCUE_PATTERNS['endpoint_patterns'],
        'supportive': SUPPORTIVE_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_ards_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical ARDS endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in ARDS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
