"""
Rehabilitation & Physiotherapy Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow. Rehabilitation RCTs (neuro-, cardiac-,
pulmonary- and musculoskeletal-rehabilitation; physiotherapy / exercise therapy /
occupational therapy) report a distinct endpoint vocabulary - motor recovery /
functional independence, peak VO2 / exercise capacity, 6-minute walk distance,
return to work - that spans the rehabilitation modality rather than a single
disease. This profile targets the rehabilitation-specific outcomes not owned by an
acute-disease specialty.

Subspecialties:
- neuro: motor recovery (Fugl-Meyer), functional independence (FIM / Barthel),
  gait / walking ability (after stroke / SCI / TBI rehabilitation).
- cardiac: exercise-based cardiac rehabilitation - all-cause / cardiovascular
  mortality, hospital readmission (ratio), peak VO2 / exercise capacity.
- pulmonary: pulmonary rehabilitation - 6-minute walk distance, dyspnoea,
  respiratory quality of life.
- musculoskeletal: pain, physical function / disability, return to work / sport.

Drug / intervention classes (arm labels): physiotherapy / physical therapy,
exercise / aerobic / resistance training, occupational therapy, constraint-induced
movement therapy, robot-assisted therapy, virtual reality, electrical stimulation,
cardiac / pulmonary rehabilitation, usual care.

Effect measures: mortality / readmission / return-to-work -> RR/OR/HR; motor /
function / FIM / VO2 / 6MWD / pain / dyspnoea / QoL -> MD/SMD (continuous,
natural scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# REHABILITATION ENDPOINTS
# ============================================================

REHABILITATION_PHYSIOTHERAPY_ENDPOINTS = {
    # --- neuro ---
    'MOTOR_FUNCTION': {
        'aliases': ['fugl-meyer assessment', 'fugl-meyer', 'motor recovery', 'motor function',
                    'upper-limb function', 'upper limb function', 'arm motor function',
                    'action research arm test'],
        'subspecialty': 'neuro',
        'measure_types': ['MD', 'SMD']
    },
    'FUNCTIONAL_INDEPENDENCE': {
        'aliases': ['functional independence measure', 'fim', 'barthel index',
                    'functional independence', 'modified rankin scale', 'activities of daily living'],
        'subspecialty': 'neuro',
        'measure_types': ['MD', 'SMD']
    },
    'GAIT': {
        'aliases': ['gait speed', 'walking speed', 'walking ability', '10-metre walk',
                    '10 metre walk test', 'ten-metre walk', 'comfortable walking speed'],
        'subspecialty': 'neuro',
        'measure_types': ['MD', 'SMD']
    },

    # --- cardiac ---
    'CARDIAC_MORTALITY': {
        'aliases': ['all-cause mortality', 'all cause mortality', 'cardiovascular mortality',
                    'cardiac mortality', 'mortality', 'death'],
        'subspecialty': 'cardiac',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HOSPITAL_READMISSION': {
        'aliases': ['hospital readmission', 'readmission', 'hospitalisation', 'hospitalization',
                    'all-cause hospitalisation', 'cardiac hospitalisation'],
        'subspecialty': 'cardiac',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'EXERCISE_CAPACITY': {
        'aliases': ['peak oxygen uptake', 'peak vo2', 'vo2 peak', 'exercise capacity',
                    'peak exercise capacity', 'maximal oxygen uptake', 'vo2max'],
        'subspecialty': 'cardiac',
        'measure_types': ['MD', 'SMD']
    },

    # --- pulmonary ---
    'SIX_MWD': {
        'aliases': ['6-minute walk distance', 'six-minute walk distance', '6-minute walk test',
                    '6mwd', '6mwt', 'six minute walk distance'],
        'subspecialty': 'pulmonary',
        'measure_types': ['MD', 'SMD']
    },
    'DYSPNOEA': {
        'aliases': ['dyspnoea', 'dyspnea', 'breathlessness', 'mmrc dyspnoea', 'mmrc dyspnea',
                    'borg dyspnoea', 'dyspnoea score'],
        'subspecialty': 'pulmonary',
        'measure_types': ['MD', 'SMD']
    },
    'RESPIRATORY_QOL': {
        'aliases': ['chronic respiratory questionnaire', 'crq', 'st george respiratory questionnaire',
                    'sgrq', 'respiratory quality of life', 'health-related quality of life'],
        'subspecialty': 'pulmonary',
        'measure_types': ['MD', 'SMD']
    },

    # --- musculoskeletal ---
    'PAIN': {
        'aliases': ['pain intensity', 'visual analogue scale pain', 'vas pain', 'pain score',
                    'numerical rating scale pain', 'pain'],
        'subspecialty': 'musculoskeletal',
        'measure_types': ['MD', 'SMD']
    },
    'PHYSICAL_FUNCTION': {
        'aliases': ['physical function', 'physical functioning', 'disability', 'functional disability',
                    'function score', 'self-reported function'],
        'subspecialty': 'musculoskeletal',
        'measure_types': ['MD', 'SMD']
    },
    'RETURN_TO_WORK': {
        'aliases': ['return to work', 'return to sport', 'return to activity',
                    'return-to-work rate', 'returned to work'],
        'subspecialty': 'musculoskeletal',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# NEURO PATTERNS
# ============================================================

NEURO_PATTERNS = {
    'detection_keywords': [
        r'fugl[- ]meyer|motor\s+recovery|upper[- ]limb\s+function|action\s+research\s+arm\s+test',
        r'functional\s+independence\s+measure|\bfim\b|barthel\s+index',
        r'gait\s+(?:speed|training)|walking\s+(?:speed|ability)|10[- ]met(?:re|er)\s+walk',
        r'constraint[- ]induced|robot[- ]assisted|stroke\s+rehabilitation',
    ],
    'endpoint_patterns': [
        (r'fugl[- ]meyer(?:\s+assessment)?|motor\s+(?:recovery|function)|upper[- ]limb\s+function|'
         r'action\s+research\s+arm\s+test', 'MOTOR_FUNCTION'),
        (r'functional\s+independence(?:\s+measure)?|\bfim\b|barthel\s+index|modified\s+rankin\s+scale',
         'FUNCTIONAL_INDEPENDENCE'),
        (r'gait\s+speed|walking\s+(?:speed|ability)|10[- ]met(?:re|er)\s+walk(?:\s+test)?|'
         r'comfortable\s+walking\s+speed', 'GAIT'),
    ],
    'context_patterns': [
        r'after\s+stroke', r'spinal\s+cord\s+injury', r'm/s|metres?\s+per\s+second',
    ]
}


# ============================================================
# CARDIAC PATTERNS
# ============================================================

CARDIAC_PATTERNS = {
    'detection_keywords': [
        r'cardiac\s+rehabilitation', r'exercise[- ]based\s+(?:cardiac\s+)?rehabilitation',
        r'peak\s+(?:vo2|oxygen\s+uptake)|vo2\s*(?:peak|max)', r'(?:hospital\s+)?readmission',
        r'cardiovascular\s+mortality',
    ],
    'endpoint_patterns': [
        (r'peak\s+(?:vo2|oxygen\s+uptake)|vo2\s*(?:peak|max)|(?:peak\s+)?exercise\s+capacity|'
         r'maximal\s+oxygen\s+uptake', 'EXERCISE_CAPACITY'),
        (r'(?:hospital\s+|all[- ]cause\s+|cardiac\s+)?readmission|hospitali[sz]ation',
         'HOSPITAL_READMISSION'),
        (r'(?:all[- ]cause|cardiovascular|cardiac)\s+mortality|\bmortality\b|\bdeath\b',
         'CARDIAC_MORTALITY'),
    ],
    'context_patterns': [
        r'after\s+(?:myocardial\s+infarction|mi)', r'heart\s+failure', r'ml/kg/min',
    ]
}


# ============================================================
# PULMONARY PATTERNS
# ============================================================

PULMONARY_PATTERNS = {
    'detection_keywords': [
        r'pulmonary\s+rehabilitation', r'6[- ]min(?:ute)?\s+walk|six[- ]min(?:ute)?\s+walk|\b6mwd\b|\b6mwt\b',
        r'dyspn(?:oe|e)a|breathlessness|mmrc', r'chronic\s+respiratory\s+questionnaire|\bcrq\b',
    ],
    'endpoint_patterns': [
        (r'6[- ]min(?:ute)?\s+walk\s+(?:distance|test)|six[- ]min(?:ute)?\s+walk\s+(?:distance|test)|'
         r'\b6mwd\b|\b6mwt\b', 'SIX_MWD'),
        (r'chronic\s+respiratory\s+questionnaire|\bcrq\b|st\.?\s+george(?:\'s)?\s+respiratory\s+questionnaire|'
         r'\bsgrq\b|respiratory\s+quality\s+of\s+life', 'RESPIRATORY_QOL'),
        (r'(?:mmrc\s+|borg\s+)?dyspn(?:oe|e)a(?:\s+score)?|breathlessness', 'DYSPNOEA'),
    ],
    'context_patterns': [
        r'\bcopd\b', r'met(?:re|er)s', r'after\s+exacerbation',
    ]
}


# ============================================================
# MUSCULOSKELETAL PATTERNS
# ============================================================

MUSCULOSKELETAL_PATTERNS = {
    'detection_keywords': [
        r'pain\s+intensity|vas\s+pain|pain\s+score', r'physical\s+function(?:ing)?|disability',
        r'return\s+to\s+(?:work|sport|activity)', r'exercise\s+therapy|manual\s+therapy|physiotherapy',
    ],
    'endpoint_patterns': [
        (r'return\s+to\s+(?:work|sport|activity)|returned\s+to\s+work', 'RETURN_TO_WORK'),
        (r'physical\s+function(?:ing)?|(?:functional\s+)?disability|function\s+score|'
         r'self[- ]reported\s+function', 'PHYSICAL_FUNCTION'),
        (r'pain\s+intensity|(?:vas|visual\s+analogue\s+scale)\s+pain|pain\s+score|'
         r'(?:numerical\s+rating\s+scale\s+)?pain', 'PAIN'),
    ],
    'context_patterns': [
        r'\bweeks?\b', r'minimal\s+clinically\s+important', r'baseline',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_rehabilitation_physiotherapy_subspecialty(text: str) -> Tuple[str, float]:
    """Detect rehabilitation/physiotherapy trial subspecialty. Returns
    (subspecialty, confidence). Subspecialties: neuro, cardiac, pulmonary,
    musculoskeletal, general_rehabilitation."""
    text_lower = text.lower()
    scores = {'neuro': 0, 'cardiac': 0, 'pulmonary': 0, 'musculoskeletal': 0}
    for kw in NEURO_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['neuro'] += 1
    for kw in CARDIAC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['cardiac'] += 1
    for kw in PULMONARY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pulmonary'] += 1
    for kw in MUSCULOSKELETAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['musculoskeletal'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_rehabilitation', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_rehabilitation_physiotherapy_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'neuro': NEURO_PATTERNS['endpoint_patterns'],
        'cardiac': CARDIAC_PATTERNS['endpoint_patterns'],
        'pulmonary': PULMONARY_PATTERNS['endpoint_patterns'],
        'musculoskeletal': MUSCULOSKELETAL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_rehabilitation_physiotherapy_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical rehabilitation endpoint, preferring the LONGEST
    matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in REHABILITATION_PHYSIOTHERAPY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
