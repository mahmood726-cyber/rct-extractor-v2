"""
Emergency Medicine & Resuscitation Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow. Emergency / resuscitation RCTs
(out-of-hospital and in-hospital cardiac arrest, major trauma, emergency airway
management, acute undifferentiated presentations) report a distinct endpoint
vocabulary - return of spontaneous circulation, survival to hospital discharge,
favourable neurological outcome, first-pass intubation success, trauma mortality
- that is NOT covered by the sepsis or cardiology specialties.

Subspecialties:
- cardiac_arrest: return of spontaneous circulation (ROSC), survival to admission
  / discharge, favourable neurological outcome, 30-day survival.
- trauma: trauma mortality (24-hour / 28-day / in-hospital), massive transfusion.
- airway: first-pass / first-attempt intubation success.
- acute_care: emergency-department mortality, hospital admission, major adverse
  event in acute undifferentiated emergency presentations.

Drug / intervention classes (arm labels): vasopressors (adrenaline/epinephrine,
vasopressin), antiarrhythmics (amiodarone, lidocaine), tranexamic acid,
targeted temperature management / therapeutic hypothermia, mechanical CPR,
extracorporeal CPR (ECPR), airway devices (supraglottic airway, endotracheal
intubation, bag-valve-mask), placebo.

Effect measures: all resuscitation / trauma / airway endpoints -> RR/OR/HR.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# EMERGENCY / RESUSCITATION ENDPOINTS
# ============================================================

EMERGENCY_RESUSCITATION_ENDPOINTS = {
    # --- cardiac arrest ---
    'ROSC': {
        'aliases': ['return of spontaneous circulation', 'sustained return of spontaneous circulation',
                    'rosc', 'sustained rosc', 'any rosc', 'prehospital rosc'],
        'subspecialty': 'cardiac_arrest',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'SURVIVAL_TO_ADMISSION': {
        'aliases': ['survival to hospital admission', 'survival to admission',
                    'rosc at hospital arrival', 'admitted to hospital alive'],
        'subspecialty': 'cardiac_arrest',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'SURVIVAL_TO_DISCHARGE': {
        'aliases': ['survival to hospital discharge', 'survival to discharge',
                    'hospital survival', 'survived to discharge', 'discharge alive'],
        'subspecialty': 'cardiac_arrest',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'FAVOURABLE_NEURO_OUTCOME': {
        'aliases': ['favourable neurological outcome', 'favorable neurological outcome',
                    'good neurological outcome', 'favourable neurologic outcome',
                    'favorable neurologic outcome', 'cerebral performance category 1-2',
                    'cpc 1-2', 'good functional outcome', 'mrs 0-3'],
        'subspecialty': 'cardiac_arrest',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'SURVIVAL_30D': {
        'aliases': ['30-day survival', '30 day survival', '90-day survival',
                    'survival at 30 days', '180-day survival', 'one-year survival'],
        'subspecialty': 'cardiac_arrest',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- trauma ---
    'TRAUMA_MORTALITY': {
        'aliases': ['24-hour mortality', '24 hour mortality', '28-day mortality',
                    '28 day mortality', 'in-hospital mortality', 'all-cause mortality',
                    'all cause mortality', '30-day mortality', 'death due to bleeding',
                    'death from exsanguination'],
        'subspecialty': 'trauma',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'MASSIVE_TRANSFUSION': {
        'aliases': ['massive transfusion', 'massive blood transfusion',
                    'requirement for massive transfusion'],
        'subspecialty': 'trauma',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- airway ---
    'FIRST_PASS_SUCCESS': {
        'aliases': ['first-pass success', 'first pass success', 'first-attempt success',
                    'first attempt intubation success', 'successful first-pass intubation',
                    'first-pass intubation success'],
        'subspecialty': 'airway',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'INTUBATION_SUCCESS': {
        'aliases': ['successful intubation', 'overall intubation success',
                    'successful tracheal intubation', 'intubation success'],
        'subspecialty': 'airway',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- acute care ---
    'ED_MORTALITY': {
        'aliases': ['emergency department mortality', 'emergency-department mortality',
                    'ed mortality', 'early mortality', 'short-term mortality'],
        'subspecialty': 'acute_care',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HOSPITAL_ADMISSION': {
        'aliases': ['hospital admission', 'hospitalisation', 'hospitalization',
                    'admission to hospital', 'unplanned admission'],
        'subspecialty': 'acute_care',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# CARDIAC ARREST PATTERNS
# ============================================================

CARDIAC_ARREST_PATTERNS = {
    'detection_keywords': [
        r'return\s+of\s+spontaneous\s+circulation|\brosc\b',
        r'survival\s+to\s+(?:hospital\s+)?(?:admission|discharge)',
        r'(?:favou?rable|good)\s+neurolog(?:ical|ic)\s+outcome|cerebral\s+performance\s+category|\bcpc\b',
        r'cardiac\s+arrest|cardiopulmonary\s+resuscitation|\bcpr\b',
    ],
    'endpoint_patterns': [
        (r'sustained\s+return\s+of\s+spontaneous\s+circulation|return\s+of\s+spontaneous\s+circulation|'
         r'\brosc\b', 'ROSC'),
        (r'survival\s+to\s+(?:hospital\s+)?admission|rosc\s+at\s+hospital\s+arrival|'
         r'admitted\s+to\s+hospital\s+alive', 'SURVIVAL_TO_ADMISSION'),
        (r'survival\s+to\s+(?:hospital\s+)?discharge|hospital\s+survival|survived\s+to\s+discharge|'
         r'discharge\s+alive', 'SURVIVAL_TO_DISCHARGE'),
        (r'(?:favou?rable|good)\s+neurolog(?:ical|ic)\s+outcome|cerebral\s+performance\s+category\s*1[- ]2|'
         r'\bcpc\s*1[- ]2\b|good\s+functional\s+outcome|\bmrs\s*0[- ]3\b', 'FAVOURABLE_NEURO_OUTCOME'),
        (r'\d+[- ]day\s+survival|survival\s+at\s+\d+\s+days|one[- ]year\s+survival', 'SURVIVAL_30D'),
    ],
    'context_patterns': [
        r'out[- ]of[- ]hospital\s+cardiac\s+arrest|\bohca\b',
        r'in[- ]hospital\s+cardiac\s+arrest|\bihca\b', r'shockable\s+rhythm',
    ]
}


# ============================================================
# TRAUMA PATTERNS
# ============================================================

TRAUMA_PATTERNS = {
    'detection_keywords': [
        r'major\s+trauma|traumatic\s+(?:injury|h[ae]morrhage)', r'tranexamic\s+acid|\btxa\b',
        r'massive\s+(?:blood\s+)?transfusion', r'(?:24[- ]hour|28[- ]day|in[- ]hospital)\s+mortality',
        r'exsanguination|h[ae]morrhagic\s+shock',
    ],
    'endpoint_patterns': [
        (r'massive\s+(?:blood\s+)?transfusion|requirement\s+for\s+massive\s+transfusion',
         'MASSIVE_TRANSFUSION'),
        (r'24[- ]hour\s+mortality|28[- ]day\s+mortality|30[- ]day\s+mortality|in[- ]hospital\s+mortality|'
         r'all[- ]cause\s+mortality|death\s+(?:due\s+to\s+bleeding|from\s+exsanguination)',
         'TRAUMA_MORTALITY'),
    ],
    'context_patterns': [
        r'injury\s+severity\s+score|\biss\b', r'blunt\s+(?:or\s+penetrating\s+)?trauma',
        r'prehospital',
    ]
}


# ============================================================
# AIRWAY PATTERNS
# ============================================================

AIRWAY_PATTERNS = {
    'detection_keywords': [
        r'first[- ](?:pass|attempt)\s+(?:intubation\s+)?success', r'rapid\s+sequence\s+intubation',
        r'tracheal\s+intubation|endotracheal\s+intubation', r'video\s+laryngoscop|direct\s+laryngoscop',
        r'supraglottic\s+airway',
    ],
    'endpoint_patterns': [
        (r'first[- ](?:pass|attempt)\s+(?:intubation\s+)?success|successful\s+first[- ]pass\s+intubation',
         'FIRST_PASS_SUCCESS'),
        (r'(?:overall\s+|successful\s+)?(?:tracheal\s+)?intubation\s+success|successful\s+(?:tracheal\s+)?intubation',
         'INTUBATION_SUCCESS'),
    ],
    'context_patterns': [
        r'glottic\s+view', r'cormack[- ]lehane', r'emergency\s+(?:department|airway)',
    ]
}


# ============================================================
# ACUTE CARE PATTERNS
# ============================================================

ACUTE_CARE_PATTERNS = {
    'detection_keywords': [
        r'emergency\s+department|\bed\b\s+(?:visit|presentation|mortality)',
        r'hospital\s+admission|unplanned\s+admission', r'early\s+mortality|short[- ]term\s+mortality',
        r'acute\s+(?:undifferentiated\s+)?(?:presentation|illness)',
    ],
    'endpoint_patterns': [
        (r'emergency[- ]department\s+mortality|\bed\s+mortality\b|early\s+mortality|'
         r'short[- ]term\s+mortality', 'ED_MORTALITY'),
        (r'(?:unplanned\s+)?hospital(?:isation|ization)|(?:unplanned\s+)?(?:hospital\s+)?admission|'
         r'admission\s+to\s+hospital', 'HOSPITAL_ADMISSION'),
    ],
    'context_patterns': [
        r'triage', r'\bed\s+length\s+of\s+stay\b', r'\d+[- ]day\s+(?:revisit|readmission)',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_emergency_resuscitation_subspecialty(text: str) -> Tuple[str, float]:
    """Detect emergency/resuscitation trial subspecialty. Returns (subspecialty,
    confidence). Subspecialties: cardiac_arrest, trauma, airway, acute_care,
    general_emergency."""
    text_lower = text.lower()
    scores = {'cardiac_arrest': 0, 'trauma': 0, 'airway': 0, 'acute_care': 0}
    for kw in CARDIAC_ARREST_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['cardiac_arrest'] += 1
    for kw in TRAUMA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['trauma'] += 1
    for kw in AIRWAY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['airway'] += 1
    for kw in ACUTE_CARE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['acute_care'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_emergency', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_emergency_resuscitation_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'cardiac_arrest': CARDIAC_ARREST_PATTERNS['endpoint_patterns'],
        'trauma': TRAUMA_PATTERNS['endpoint_patterns'],
        'airway': AIRWAY_PATTERNS['endpoint_patterns'],
        'acute_care': ACUTE_CARE_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_emergency_resuscitation_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical emergency/resuscitation endpoint, preferring the
    LONGEST matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in EMERGENCY_RESUSCITATION_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
