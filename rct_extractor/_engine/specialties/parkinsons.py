"""
Parkinson's Disease Subspecialty Patterns and Endpoints

Built for the same meta-analysis extraction workflow as the malaria / TB / HIV
profiles. Parkinson's disease (PD) RCTs report a distinct endpoint vocabulary
(MDS-UPDRS parts, ON/OFF motor-fluctuation time, dyskinesia, levodopa-equivalent
daily dose, PDQ-39 quality of life, MoCA/MMSE cognition, SAPS-PD psychosis) that
the generic effect-size engine does not recognise on its own.

Subspecialties:
- Motor (symptomatic oral/transdermal therapy): MDS-UPDRS Part III (motor) and
  total score change, motor response, "responder" rate, treatment-emergent
  dyskinesia. Drugs: levodopa/carbidopa, dopamine agonists (pramipexole,
  ropinirole, rotigotine), MAO-B inhibitors (rasagiline, selegiline, safinamide),
  COMT inhibitors (entacapone, opicapone), amantadine, istradefylline.
- Device/advanced (device-aided therapy for motor fluctuations): deep brain
  stimulation (DBS), levodopa-carbidopa intestinal gel (LCIG), subcutaneous
  apomorphine/foslevodopa infusion, MR-guided focused ultrasound. Endpoints: ON
  time without troublesome dyskinesia, OFF time reduction.
- Non-motor (non-motor symptom control): PD psychosis (pimavanserin), depression,
  PD dementia / cognition (rivastigmine), REM sleep behaviour disorder, orthostatic
  hypotension, impulse-control disorder, constipation, sialorrhoea.
- Neuroprotection (disease modification): progression of MDS-UPDRS total, time to
  clinically meaningful progression / disability, need for symptomatic therapy
  (isradipine, exenatide, inosine, ambroxol, etc.).

Effect measures follow what these trials report: binary (responder, dyskinesia,
psychosis response, falls, adverse events) -> RR/OR/RD; time-to-event
(progression, need for dopaminergic therapy, mortality) -> HR/IRR; continuous
scale change (MDS-UPDRS, PDQ-39, ON/OFF hours) pools as a mean difference via the
core effect-size engine. Vaccine/efficacy framing does not apply.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# PARKINSON'S DISEASE ENDPOINTS
# ============================================================

PARKINSONS_ENDPOINTS = {
    # --- Motor (symptomatic) ---
    'UPDRS_III': {
        'aliases': ['updrs part iii', 'updrs iii', 'mds-updrs part iii',
                    'mds updrs part iii', 'updrs motor score', 'motor updrs',
                    'unified parkinson disease rating scale part iii',
                    'part iii motor score', 'updrs-iii'],
        'subspecialty': 'motor',
        'measure_types': ['MD', 'SMD']
    },
    'UPDRS_TOTAL': {
        'aliases': ['updrs total score', 'total updrs', 'mds-updrs total',
                    'mds updrs total score', 'total mds-updrs',
                    'updrs parts i-iii', 'updrs sum'],
        'subspecialty': 'motor',
        'measure_types': ['MD', 'SMD']
    },
    'MOTOR_RESPONDER': {
        'aliases': ['responder', 'responder rate', 'motor responder',
                    'clinically meaningful improvement', 'treatment response',
                    'cgi-i responder', 'much improved'],
        'subspecialty': 'motor',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'DYSKINESIA': {
        'aliases': ['dyskinesia', 'troublesome dyskinesia', 'levodopa-induced dyskinesia',
                    'treatment-emergent dyskinesia', 'motor complications',
                    'dyskinesia incidence', 'peak-dose dyskinesia'],
        'subspecialty': 'motor',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'LEDD': {
        'aliases': ['levodopa equivalent daily dose', 'levodopa-equivalent dose',
                    'led', 'ledd', 'daily levodopa dose', 'levodopa dose reduction'],
        'subspecialty': 'motor',
        'measure_types': ['MD']
    },

    # --- Device / advanced ---
    'ON_TIME': {
        'aliases': ['on time without troublesome dyskinesia',
                    'on time without dyskinesia', 'good on time',
                    'on-time', 'on time', 'increase in on time', 'awake on time'],
        'subspecialty': 'device_advanced',
        'measure_types': ['MD']
    },
    'OFF_TIME': {
        'aliases': ['off time', 'off-time', 'reduction in off time',
                    'daily off time', 'motor fluctuations', 'wearing-off',
                    'wearing off time'],
        'subspecialty': 'device_advanced',
        'measure_types': ['MD']
    },

    # --- Non-motor ---
    'PSYCHOSIS': {
        'aliases': ['parkinson disease psychosis', 'pd psychosis', 'psychosis',
                    'saps-pd', 'hallucinations', 'scale for assessment of positive symptoms',
                    'psychotic symptoms'],
        'subspecialty': 'nonmotor',
        'measure_types': ['MD', 'RR', 'OR']
    },
    'COGNITION': {
        'aliases': ['cognition', 'cognitive function', 'mmse', 'moca',
                    'montreal cognitive assessment', 'mini-mental state',
                    'adas-cog', 'cognitive decline', 'dementia'],
        'subspecialty': 'nonmotor',
        'measure_types': ['MD', 'HR', 'OR']
    },
    'QUALITY_OF_LIFE': {
        'aliases': ['pdq-39', 'pdq39', 'pdq-8', 'parkinson disease questionnaire',
                    'quality of life', 'health-related quality of life',
                    'pdq-39 summary index'],
        'subspecialty': 'nonmotor',
        'measure_types': ['MD', 'SMD']
    },
    'ORTHOSTATIC_HYPOTENSION': {
        'aliases': ['orthostatic hypotension', 'neurogenic orthostatic hypotension',
                    'postural hypotension', 'symptomatic orthostatic hypotension'],
        'subspecialty': 'nonmotor',
        'measure_types': ['RR', 'OR', 'MD']
    },

    # --- Neuroprotection / disease modification ---
    'DISEASE_PROGRESSION': {
        'aliases': ['disease progression', 'clinical progression',
                    'progression of parkinson', 'time to progression',
                    'progression of disability', 'mds-updrs progression',
                    'need for symptomatic therapy', 'need for dopaminergic therapy',
                    'time to initiation of dopaminergic therapy'],
        'subspecialty': 'neuroprotection',
        'measure_types': ['HR', 'MD', 'RR']
    },

    # --- Safety / shared ---
    'FALLS': {
        'aliases': ['falls', 'fall rate', 'number of falls', 'fallers',
                    'recurrent falls', 'injurious falls'],
        'subspecialty': 'motor',
        'measure_types': ['RR', 'IRR', 'HR']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'serious adverse events', 'serious adverse event',
                    'treatment-emergent adverse events', 'discontinuation due to adverse',
                    'impulse control disorder', 'impulse-control disorder'],
        'subspecialty': 'motor',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'overall survival',
                    'all-cause death'],
        'subspecialty': 'neuroprotection',
        'measure_types': ['HR', 'RR', 'OR']
    },
}


# ============================================================
# MOTOR PATTERNS (symptomatic oral/transdermal therapy)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'mds[- ]?updrs|\bupdrs\b|unified\s+parkinson',
        r'levodopa|carbidopa|l[- ]?dopa|benserazide',
        r'pramipexole|ropinirole|rotigotine|dopamine\s+agonist',
        r'rasagiline|selegiline|safinamide|mao[- ]?b\s+inhibitor',
        r'entacapone|opicapone|tolcapone|comt\s+inhibitor',
        r'amantadine|istradefylline',
        r'motor\s+score|dyskinesia|early\s+parkinson',
    ],
    'endpoint_patterns': [
        (r'updrs\s+(?:part\s+)?iii|mds[- ]?updrs\s+(?:part\s+)?iii|updrs[- ]iii|'
         r'motor\s+updrs|updrs\s+motor\s+score', 'UPDRS_III'),
        (r'(?:total|sum)\s+(?:mds[- ]?)?updrs|(?:mds[- ]?)?updrs\s+total|'
         r'updrs\s+parts?\s+i[- ]?iii', 'UPDRS_TOTAL'),
        (r'levodopa[- ]equivalent\s+(?:daily\s+)?dose|\bledd?\b|'
         r'daily\s+levodopa\s+dose', 'LEDD'),
        (r'levodopa[- ]induced\s+dyskinesia|troublesome\s+dyskinesia|'
         r'treatment[- ]emergent\s+dyskinesia|\bdyskinesia\b|motor\s+complications',
         'DYSKINESIA'),
        (r'responder\s+rate|\bresponders?\b|clinically\s+meaningful\s+improvement|'
         r'cgi[- ]i\s+responder', 'MOTOR_RESPONDER'),
        (r'\bfalls?\b|fallers?|injurious\s+falls', 'FALLS'),
        (r'impulse[- ]control\s+disorder|serious\s+adverse\s+events?|'
         r'treatment[- ]emergent\s+adverse|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'early\s+(?:untreated\s+)?parkinson', r'monotherapy|adjunct(?:ive)?\s+therapy',
        r'week\s+\d+\s+change', r'change\s+from\s+baseline',
    ]
}


# ============================================================
# DEVICE / ADVANCED PATTERNS (device-aided therapy)
# ============================================================

DRUG_RESISTANT_PATTERNS = {  # name kept generic for registry symmetry; = device/advanced
    'detection_keywords': [
        r'deep\s+brain\s+stimulation|\bdbs\b|subthalamic\s+(?:nucleus|stimulation)|\bstn\b',
        r'globus\s+pallidus|\bgpi\b',
        r'levodopa[- ]carbidopa\s+intestinal\s+gel|\blcig\b|intestinal\s+gel|duodopa',
        r'apomorphine\s+(?:infusion|pump)|subcutaneous\s+apomorphine',
        r'foslevodopa|foscarbidopa|continuous\s+subcutaneous',
        r'focused\s+ultrasound|\bmrgfus\b|pallidotomy|thalamotomy',
        r'motor\s+fluctuations|wearing[- ]off|advanced\s+parkinson',
    ],
    'endpoint_patterns': [
        (r'on\s+time\s+without\s+(?:troublesome\s+)?dyskinesia|good\s+on\s+time|'
         r'\bon[- ]time\b|increase\s+in\s+on\s+time', 'ON_TIME'),
        (r'\boff[- ]time\b|reduction\s+in\s+off\s+time|daily\s+off\s+time|'
         r'wearing[- ]off|motor\s+fluctuations', 'OFF_TIME'),
        (r'troublesome\s+dyskinesia|\bdyskinesia\b', 'DYSKINESIA'),
        (r'updrs\s+(?:part\s+)?iii|motor\s+updrs', 'UPDRS_III'),
        (r'pdq[- ]?39|quality\s+of\s+life', 'QUALITY_OF_LIFE'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'patient\s+diary|hauser\s+diary', r'stimulation\s+parameters',
        r'\bon\b\s+and\s+\boff\b\s+medication', r'best\s+medical\s+therapy',
    ]
}


# ============================================================
# NON-MOTOR PATTERNS (non-motor symptom control)
# ============================================================

PREVENTION_PATTERNS = {  # name kept generic for registry symmetry; = non-motor
    'detection_keywords': [
        r'parkinson\s+disease\s+psychosis|pd\s+psychosis|pimavanserin|saps[- ]?pd',
        r'hallucinations|psychotic\s+symptoms',
        r'parkinson\s+disease\s+dementia|\bpdd\b|rivastigmine|cognitive\s+(?:decline|impairment)',
        r'\bmoca\b|\bmmse\b|montreal\s+cognitive',
        r'rem\s+sleep\s+behaviou?r\s+disorder|\brbd\b|excessive\s+daytime\s+sleepiness',
        r'orthostatic\s+hypotension|droxidopa|depression|sialorrh(?:oea|ea)|constipation',
    ],
    'endpoint_patterns': [
        (r'pd\s+psychosis|parkinson\s+disease\s+psychosis|saps[- ]?pd|'
         r'hallucinations|psychotic\s+symptoms|\bpsychosis\b', 'PSYCHOSIS'),
        (r'\bmoca\b|\bmmse\b|montreal\s+cognitive|adas[- ]?cog|mini[- ]mental|'
         r'cognitive\s+(?:function|decline)|\bdementia\b|\bcognition\b', 'COGNITION'),
        (r'orthostatic\s+hypotension|postural\s+hypotension', 'ORTHOSTATIC_HYPOTENSION'),
        (r'pdq[- ]?39|pdq[- ]?8|quality\s+of\s+life', 'QUALITY_OF_LIFE'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'non[- ]motor\s+symptoms?', r'\bnms\b', r'caregiver\s+burden',
        r'placebo[- ]controlled',
    ]
}


# ============================================================
# NEUROPROTECTION PATTERNS (disease modification)
# ============================================================

LATENT_PATTERNS = {  # name kept generic for registry symmetry; = neuroprotection
    'detection_keywords': [
        r'disease[- ]modif|neuroprotect|slow\w*\s+(?:disease\s+)?progression',
        r'progression\s+of\s+parkinson|clinical\s+progression',
        r'isradipine|exenatide|inosine|ambroxol|nilotinib|deferiprone|terazosin',
        r'time\s+to\s+(?:initiation\s+of\s+)?(?:dopaminergic|symptomatic)\s+(?:therapy|treatment)',
        r'newly\s+diagnosed|de\s?novo\s+parkinson|early\s+untreated',
    ],
    'endpoint_patterns': [
        (r'disease\s+progression|clinical\s+progression|progression\s+of\s+(?:parkinson|disability)|'
         r'time\s+to\s+progression|mds[- ]?updrs\s+progression', 'DISEASE_PROGRESSION'),
        (r'need\s+for\s+(?:symptomatic|dopaminergic)\s+(?:therapy|treatment)|'
         r'time\s+to\s+(?:initiation\s+of\s+)?(?:dopaminergic|symptomatic)\s+(?:therapy|treatment)',
         'DISEASE_PROGRESSION'),
        (r'(?:total|sum)\s+(?:mds[- ]?)?updrs|(?:mds[- ]?)?updrs\s+total', 'UPDRS_TOTAL'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)|overall\s+survival', 'MORTALITY'),
        (r'\bcognition\b|cognitive\s+decline|\bdementia\b', 'COGNITION'),
    ],
    'context_patterns': [
        r'delayed[- ]start\s+design', r'futility\s+(?:study|design)',
        r'datscan|dat[- ]?spect|dopamine\s+transporter', r'biomarker',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_parkinsons_subspecialty(text: str) -> Tuple[str, float]:
    """Detect PD trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: motor, device_advanced, nonmotor, neuroprotection, general_pd."""
    text_lower = text.lower()
    scores = {'motor': 0, 'device_advanced': 0, 'nonmotor': 0, 'neuroprotection': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['motor'] += 1
    for kw in DRUG_RESISTANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['device_advanced'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['nonmotor'] += 1
    for kw in LATENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['neuroprotection'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_pd', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_parkinsons_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'motor': TREATMENT_PATTERNS['endpoint_patterns'],
        'device_advanced': DRUG_RESISTANT_PATTERNS['endpoint_patterns'],
        'nonmotor': PREVENTION_PATTERNS['endpoint_patterns'],
        'neuroprotection': LATENT_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_parkinsons_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical PD endpoint, preferring the LONGEST matching alias
    so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in PARKINSONS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
