"""
Sepsis / Septic Shock Subspecialty Patterns and Endpoints

Built for the same meta-analysis extraction workflow as the malaria / TB / HIV
profiles. Sepsis RCTs report a distinct endpoint vocabulary (28-/90-day mortality,
shock reversal, vasopressor-/ventilator-/organ-support-free days, new renal
replacement therapy, SOFA score) that the generic `infectious_disease` catch-all
does not capture.

Subspecialties (mapped onto the registry's generic pattern slots):
- hemodynamic (TREATMENT slot): vasopressors and fluid resuscitation —
  norepinephrine, vasopressin, angiotensin II, balanced crystalloid vs saline,
  early goal-directed therapy. Endpoints: 28-day mortality, shock reversal,
  vasopressor-free days.
- adjunctive (DRUG_RESISTANT slot): adjunctive immunomodulation — hydrocortisone
  (± fludrocortisone), vitamin C / thiamine, IVIG. Endpoints: 90-day mortality,
  time to shock reversal.
- antimicrobial_source (PREVENTION slot): antibiotic strategy / source control —
  early or broad-spectrum antibiotics, procalcitonin-guided therapy, antibiotic
  duration, source control.
- organ_support (LATENT slot): organ support — renal replacement therapy timing,
  sepsis-associated AKI/ARDS, mechanical ventilation, organ-support-free days.

British/American spelling handled (septicaemia/septicemia via `septica?emia`,
haemodynamic/hemodynamic via `ha?emodynamic`). Effect measures: mortality /
shock reversal / new RRT -> OR/RR/HR; free-days and SOFA change -> mean difference.
"""
from typing import Dict, List, Tuple, Optional
import re

SEPSIS_ENDPOINTS = {
    'MORTALITY_28': {
        'aliases': ['28-day mortality', '28 day mortality', 'day 28 mortality',
                    '28-day all-cause mortality', '30-day mortality', 'short-term mortality'],
        'subspecialty': 'hemodynamic',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'MORTALITY_90': {
        'aliases': ['90-day mortality', '90 day mortality', 'day 90 mortality',
                    '90-day all-cause mortality', 'long-term mortality', '6-month mortality'],
        'subspecialty': 'adjunctive',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'in-hospital mortality',
                    'icu mortality', 'hospital mortality', 'overall survival'],
        'subspecialty': 'hemodynamic',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'SHOCK_REVERSAL': {
        'aliases': ['shock reversal', 'resolution of shock', 'time to shock reversal',
                    'reversal of shock', 'vasopressor cessation', 'time to vasopressor cessation',
                    'haemodynamic stability', 'hemodynamic stability'],
        'subspecialty': 'hemodynamic',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'VASOPRESSOR_FREE_DAYS': {
        'aliases': ['vasopressor-free days', 'vasopressor free days',
                    'days free of vasopressors', 'pressor-free days'],
        'subspecialty': 'hemodynamic',
        'measure_types': ['MD']
    },
    'VENTILATOR_FREE_DAYS': {
        'aliases': ['ventilator-free days', 'ventilator free days',
                    'days free of mechanical ventilation', 'ventilation-free days'],
        'subspecialty': 'organ_support',
        'measure_types': ['MD']
    },
    'ORGAN_SUPPORT_FREE_DAYS': {
        'aliases': ['organ support-free days', 'organ-support-free days',
                    'days free of organ support', 'icu-free days'],
        'subspecialty': 'organ_support',
        'measure_types': ['MD']
    },
    'AKI_RRT': {
        'aliases': ['acute kidney injury', 'renal replacement therapy', 'new rrt',
                    'sepsis-associated aki', 'need for rrt', 'dialysis',
                    'major adverse kidney events', 'make30'],
        'subspecialty': 'organ_support',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'SOFA': {
        'aliases': ['sofa score', 'sofa', 'sequential organ failure assessment',
                    'change in sofa', 'delta sofa', 'apache ii'],
        'subspecialty': 'organ_support',
        'measure_types': ['MD']
    },
    'ANTIBIOTIC_DURATION': {
        'aliases': ['antibiotic duration', 'duration of antibiotic', 'days of antibiotic',
                    'antibiotic-free days', 'antimicrobial duration'],
        'subspecialty': 'antimicrobial_source',
        'measure_types': ['MD', 'RR']
    },
    'LENGTH_OF_STAY': {
        'aliases': ['length of stay', 'icu length of stay', 'hospital length of stay',
                    'los', 'icu stay', 'duration of icu'],
        'subspecialty': 'organ_support',
        'measure_types': ['MD']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'serious adverse events', 'serious adverse event',
                    'treatment-emergent adverse events', 'secondary infection',
                    'superinfection', 'discontinuation due to adverse'],
        'subspecialty': 'adjunctive',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


TREATMENT_PATTERNS = {  # = hemodynamic
    'detection_keywords': [
        r'septic\s+shock|vasopressor|vasoactive|noradrenaline|norepinephrine|'
        r'vasopressin|angiotensin\s+ii|terlipressin',
        r'fluid\s+resuscitation|balanced\s+crystalloid|crystalloid|colloid|'
        r'early\s+goal[- ]directed|fluid\s+bolus',
        r'mean\s+arterial\s+pressure|\bmap\b\s+target|ha?emodynamic',
        r'vasopressor[- ]free\s+days|shock\s+reversal',
    ],
    'endpoint_patterns': [
        (r'shock\s+reversal|resolution\s+of\s+shock|reversal\s+of\s+shock|'
         r'vasopressor\s+cessation|ha?emodynamic\s+stability', 'SHOCK_REVERSAL'),
        (r'vasopressor[- ]free\s+days|pressor[- ]free\s+days|days\s+free\s+of\s+vasopressors',
         'VASOPRESSOR_FREE_DAYS'),
        (r'28[- ]day\s+(?:all[- ]cause\s+)?mortality|30[- ]day\s+mortality|day\s+28\s+mortality',
         'MORTALITY_28'),
        (r'90[- ]day\s+(?:all[- ]cause\s+)?mortality|day\s+90\s+mortality', 'MORTALITY_90'),
        (r'(?:in[- ]hospital|icu|hospital|all[- ]cause)\s+mortality|\bmortality\b|\bdeath\b',
         'MORTALITY'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'mean\s+arterial\s+pressure', r'lactate', r'\bicu\b',
    ]
}


DRUG_RESISTANT_PATTERNS = {  # = adjunctive (steroids / immunomodulation)
    'detection_keywords': [
        r'hydrocortisone|corticosteroid|fludrocortisone|glucocorticoid',
        r'vitamin\s+c|ascorbic\s+acid|thiamine|metabolic\s+resuscitation',
        r'intravenous\s+immunoglobulin|\bivig\b|immunomodulat',
        r'adjunctive\s+(?:therapy|treatment)|hydrocortisone\s+in\s+sepsis',
    ],
    'endpoint_patterns': [
        (r'90[- ]day\s+(?:all[- ]cause\s+)?mortality|day\s+90\s+mortality|6[- ]month\s+mortality',
         'MORTALITY_90'),
        (r'28[- ]day\s+(?:all[- ]cause\s+)?mortality|30[- ]day\s+mortality', 'MORTALITY_28'),
        (r'shock\s+reversal|time\s+to\s+(?:shock\s+reversal|vasopressor\s+cessation)|'
         r'resolution\s+of\s+shock', 'SHOCK_REVERSAL'),
        (r'(?:in[- ]hospital|icu|hospital|all[- ]cause)\s+mortality|\bmortality\b|\bdeath\b',
         'MORTALITY'),
        (r'secondary\s+infection|superinfection|serious\s+adverse\s+events?|'
         r'\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'relative\s+adrenal', r'days\s+1[- ]7', r'hpa\s+axis',
    ]
}


PREVENTION_PATTERNS = {  # = antimicrobial_source
    'detection_keywords': [
        r'antibiotic|antimicrobial|broad[- ]spectrum|beta[- ]lactam|meropenem|'
        r'piperacillin',
        r'procalcitonin[- ]guided|procalcitonin|biomarker[- ]guided',
        r'source\s+control|empiric\s+(?:antibiotic|therapy)|early\s+antibiotic',
        r'antibiotic\s+(?:duration|de[- ]escalation|stewardship)',
    ],
    'endpoint_patterns': [
        (r'antibiotic\s+(?:duration|free\s+days)|duration\s+of\s+antibiotic|'
         r'days\s+of\s+antibiotic|antimicrobial\s+duration', 'ANTIBIOTIC_DURATION'),
        (r'28[- ]day\s+(?:all[- ]cause\s+)?mortality|30[- ]day\s+mortality', 'MORTALITY_28'),
        (r'90[- ]day\s+(?:all[- ]cause\s+)?mortality', 'MORTALITY_90'),
        (r'(?:in[- ]hospital|icu|hospital|all[- ]cause)\s+mortality|\bmortality\b|\bdeath\b',
         'MORTALITY'),
        (r'secondary\s+infection|superinfection|clostridi\w+|serious\s+adverse\s+events?|'
         r'\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'time\s+to\s+antibiotic', r'door[- ]to[- ]antibiotic', r'\bcfu\b|culture',
    ]
}


LATENT_PATTERNS = {  # = organ_support
    'detection_keywords': [
        r'renal\s+replacement\s+therapy|\brrt\b|dialysis|acute\s+kidney\s+injury|\baki\b',
        r'mechanical\s+ventilation|ventilator[- ]free|acute\s+respiratory\s+distress|\bards\b',
        r'organ\s+support|sequential\s+organ\s+failure|\bsofa\b',
        r'icu\s+(?:length\s+of\s+stay|mortality|admission)|length\s+of\s+stay',
    ],
    'endpoint_patterns': [
        (r'renal\s+replacement\s+therapy|new\s+rrt|need\s+for\s+rrt|acute\s+kidney\s+injury|'
         r'sepsis[- ]associated\s+aki|major\s+adverse\s+kidney|\bmake30\b|\bdialysis\b', 'AKI_RRT'),
        (r'ventilator[- ]free\s+days|days\s+free\s+of\s+mechanical\s+ventilation|'
         r'ventilation[- ]free\s+days', 'VENTILATOR_FREE_DAYS'),
        (r'organ[- ]support[- ]free\s+days|days\s+free\s+of\s+organ\s+support|icu[- ]free\s+days',
         'ORGAN_SUPPORT_FREE_DAYS'),
        (r'\bsofa\b\s+score|sequential\s+organ\s+failure|change\s+in\s+sofa|delta\s+sofa|'
         r'apache\s+ii', 'SOFA'),
        (r'(?:icu|hospital)\s+length\s+of\s+stay|length\s+of\s+stay|\blos\b|icu\s+stay',
         'LENGTH_OF_STAY'),
        (r'(?:in[- ]hospital|icu|all[- ]cause)\s+mortality|\bmortality\b|\bdeath\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'\bards\b', r'creatinine|urine\s+output', r'ventilator',
    ]
}


def detect_sepsis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect sepsis trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: hemodynamic, adjunctive, antimicrobial_source, organ_support,
    general_sepsis."""
    text_lower = text.lower()
    scores = {'hemodynamic': 0, 'adjunctive': 0, 'antimicrobial_source': 0,
              'organ_support': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['hemodynamic'] += 1
    for kw in DRUG_RESISTANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['adjunctive'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['antimicrobial_source'] += 1
    for kw in LATENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['organ_support'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_sepsis', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_sepsis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'hemodynamic': TREATMENT_PATTERNS['endpoint_patterns'],
        'adjunctive': DRUG_RESISTANT_PATTERNS['endpoint_patterns'],
        'antimicrobial_source': PREVENTION_PATTERNS['endpoint_patterns'],
        'organ_support': LATENT_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_sepsis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical sepsis endpoint, preferring the LONGEST matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in SEPSIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
