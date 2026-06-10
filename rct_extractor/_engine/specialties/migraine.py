"""
Migraine Subspecialty Patterns and Endpoints

Built for the same meta-analysis extraction workflow as the malaria / TB / HIV
profiles. Migraine RCTs report a distinct endpoint vocabulary (2-hour pain
freedom / pain relief, most-bothersome-symptom freedom, monthly migraine days,
monthly headache days, >=50% responder rate, acute medication days) that the
generic effect-size engine does not recognise.

Subspecialties (mapped onto the registry's generic pattern slots):
- acute (TREATMENT slot): acute attack treatment — triptans, gepants (ubrogepant,
  rimegepant, zavegepant), lasmiditan. Endpoints: 2-h pain freedom, 2-h pain
  relief, MBS freedom, sustained pain freedom, freedom from rescue medication.
- preventive (DRUG_RESISTANT slot): episodic-migraine prevention — anti-CGRP mAbs
  (erenumab, fremanezumab, galcanezumab, eptinezumab), atogepant/rimegepant,
  topiramate, propranolol. Endpoints: monthly migraine days reduction,
  >=50% responder rate, acute medication days.
- chronic (PREVENTION slot): chronic migraine — onabotulinumtoxinA, anti-CGRP;
  monthly headache days, medication-overuse headache.
- device_neuromod (LATENT slot): neuromodulation (remote electrical / vagus /
  transcranial) and procedural/menstrual-migraine treatment.

Effect measures: pain freedom / pain relief / MBS / responder -> RR/OR/RD;
continuous day-count change (MMD, MHD, acute medication days) and disability
scores (MIDAS, HIT-6) -> mean difference via the core engine.
"""
from typing import Dict, List, Tuple, Optional
import re

MIGRAINE_ENDPOINTS = {
    'PAIN_FREEDOM_2H': {
        'aliases': ['2-hour pain freedom', '2-h pain freedom', 'pain freedom at 2 hours',
                    'pain freedom at 2 h', 'two-hour pain freedom', 'pain-free at 2 hours',
                    'pain freedom', 'freedom from pain'],
        'subspecialty': 'acute',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PAIN_RELIEF_2H': {
        'aliases': ['2-hour pain relief', '2-h pain relief', 'pain relief at 2 hours',
                    'headache relief at 2 hours', 'pain relief', 'headache relief'],
        'subspecialty': 'acute',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MBS_FREEDOM': {
        'aliases': ['most bothersome symptom', 'mbs freedom', 'freedom from most bothersome',
                    'most bothersome symptom freedom', 'absence of most bothersome'],
        'subspecialty': 'acute',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SUSTAINED_PAIN_FREEDOM': {
        'aliases': ['sustained pain freedom', '2-24 hour sustained pain freedom',
                    'sustained pain-free', '24-hour sustained pain freedom'],
        'subspecialty': 'acute',
        'measure_types': ['RR', 'OR']
    },
    'RESCUE_MEDICATION': {
        'aliases': ['rescue medication', 'use of rescue medication',
                    'freedom from rescue medication', 'rescue medication use'],
        'subspecialty': 'acute',
        'measure_types': ['RR', 'OR']
    },
    'MMD': {
        'aliases': ['monthly migraine days', 'mean monthly migraine days',
                    'change in monthly migraine days', 'migraine days per month',
                    'reduction in monthly migraine days', 'mmd'],
        'subspecialty': 'preventive',
        'measure_types': ['MD']
    },
    'MHD': {
        'aliases': ['monthly headache days', 'headache days per month',
                    'change in monthly headache days', 'mean monthly headache days',
                    'reduction in monthly headache days', 'mhd'],
        'subspecialty': 'chronic',
        'measure_types': ['MD']
    },
    'RESPONDER_50': {
        'aliases': ['50% responder', '>=50% responder', 'at least 50% reduction',
                    '50 % responder', '50% response rate', '50% responder rate',
                    'responder rate', '50-percent responder'],
        'subspecialty': 'preventive',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ACUTE_MED_DAYS': {
        'aliases': ['acute medication days', 'monthly acute medication days',
                    'acute medication use days', 'days of acute medication use',
                    'medication days'],
        'subspecialty': 'preventive',
        'measure_types': ['MD']
    },
    'DISABILITY': {
        'aliases': ['midas', 'hit-6', 'hit6', 'migraine disability assessment',
                    'headache impact test', 'disability score', 'mpfid', 'msq'],
        'subspecialty': 'preventive',
        'measure_types': ['MD', 'SMD']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'serious adverse events', 'serious adverse event',
                    'treatment-emergent adverse events', 'discontinuation due to adverse'],
        'subspecialty': 'acute',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


TREATMENT_PATTERNS = {  # = acute
    'detection_keywords': [
        r'acute\s+(?:treatment|migraine|attack)|migraine\s+attack',
        r'triptan|sumatriptan|rizatriptan|eletriptan|zolmitriptan|naratriptan',
        r'ubrogepant|rimegepant|zavegepant|gepant|lasmiditan',
        r'2[- ]h(?:our|r)?\s+pain\s+(?:freedom|relief)|pain\s+freedom|pain\s+relief',
        r'most\s+bothersome\s+symptom|\bmbs\b',
    ],
    'endpoint_patterns': [
        (r'sustained\s+pain[- ]free(?:dom)?|2[- ]?24\s*h(?:our)?\s+sustained',
         'SUSTAINED_PAIN_FREEDOM'),
        (r'2[- ]h(?:our|r)?\s+pain\s+freedom|pain\s+freedom\s+at\s+2|pain[- ]free\s+at\s+2|'
         r'\bpain\s+freedom\b|freedom\s+from\s+pain', 'PAIN_FREEDOM_2H'),
        (r'2[- ]h(?:our|r)?\s+pain\s+relief|pain\s+relief\s+at\s+2|headache\s+relief|'
         r'\bpain\s+relief\b', 'PAIN_RELIEF_2H'),
        (r'most\s+bothersome\s+symptom|\bmbs\b\s+freedom|freedom\s+from\s+most\s+bothersome',
         'MBS_FREEDOM'),
        (r'rescue\s+medication', 'RESCUE_MEDICATION'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'single\s+(?:migraine\s+)?attack', r'within\s+2\s+hours', r'placebo[- ]controlled',
    ]
}


DRUG_RESISTANT_PATTERNS = {  # = preventive (episodic)
    'detection_keywords': [
        r'migraine\s+prevention|preventive\s+treatment|prophylaxis',
        r'episodic\s+migraine',
        r'erenumab|fremanezumab|galcanezumab|eptinezumab|atogepant',
        r'anti[- ]cgrp|cgrp\s+(?:antagonist|antibody|monoclonal)|calcitonin\s+gene',
        r'topiramate|propranolol|amitriptyline|flunarizine',
        r'monthly\s+migraine\s+days|\bmmd\b|50\s*%\s+responder',
    ],
    'endpoint_patterns': [
        (r'monthly\s+migraine\s+days|migraine\s+days\s+per\s+month|\bmmd\b', 'MMD'),
        (r'(?:>=?\s*|at\s+least\s+)?50\s*%?\s+respon(?:der|se)|50[- ]percent\s+responder|'
         r'responder\s+rate', 'RESPONDER_50'),
        (r'acute\s+medication\s+days|medication\s+days|days\s+of\s+acute\s+medication',
         'ACUTE_MED_DAYS'),
        (r'\bmidas\b|hit[- ]?6|migraine\s+disability|headache\s+impact|\bmsq\b', 'DISABILITY'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'monthly\s+subcutaneous|quarterly', r'baseline\s+migraine\s+days',
    ]
}


PREVENTION_PATTERNS = {  # = chronic migraine
    'detection_keywords': [
        r'chronic\s+migraine',
        r'onabotulinumtoxin|botulinum\s+toxin|botox',
        r'monthly\s+headache\s+days|\bmhd\b',
        r'medication[- ]overuse(?:\s+headache)?|\bmoh\b',
        r'>=?\s*15\s+headache\s+days|15\s+or\s+more\s+headache',
    ],
    'endpoint_patterns': [
        (r'monthly\s+headache\s+days|headache\s+days\s+per\s+month|\bmhd\b', 'MHD'),
        (r'monthly\s+migraine\s+days|\bmmd\b', 'MMD'),
        (r'(?:>=?\s*|at\s+least\s+)?50\s*%?\s+respon(?:der|se)|responder\s+rate',
         'RESPONDER_50'),
        (r'acute\s+medication\s+days|medication\s+days', 'ACUTE_MED_DAYS'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'medication\s+overuse', r'15\s+(?:or\s+more\s+)?(?:headache\s+)?days',
    ]
}


LATENT_PATTERNS = {  # = device / neuromodulation / special populations
    'detection_keywords': [
        r'neuromodulation|remote\s+electrical\s+neuromodulation|\bren\b',
        r'vagus\s+nerve\s+stimulation|transcranial\s+magnetic|external\s+trigeminal',
        r'menstrual\s+migraine|menstrually[- ]related',
        r'occipital\s+nerve|sphenopalatine\s+ganglion',
    ],
    'endpoint_patterns': [
        (r'2[- ]h(?:our|r)?\s+pain\s+freedom|\bpain\s+freedom\b', 'PAIN_FREEDOM_2H'),
        (r'2[- ]h(?:our|r)?\s+pain\s+relief|\bpain\s+relief\b|headache\s+relief',
         'PAIN_RELIEF_2H'),
        (r'monthly\s+migraine\s+days|\bmmd\b', 'MMD'),
        (r'monthly\s+headache\s+days|\bmhd\b', 'MHD'),
        (r'most\s+bothersome\s+symptom|\bmbs\b', 'MBS_FREEDOM'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'device|stimulation', r'sham[- ]controlled',
    ]
}


def detect_migraine_subspecialty(text: str) -> Tuple[str, float]:
    """Detect migraine trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: acute, preventive, chronic, device_neuromod, general_migraine."""
    text_lower = text.lower()
    scores = {'acute': 0, 'preventive': 0, 'chronic': 0, 'device_neuromod': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['acute'] += 1
    for kw in DRUG_RESISTANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['preventive'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['chronic'] += 1
    for kw in LATENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['device_neuromod'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_migraine', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_migraine_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'acute': TREATMENT_PATTERNS['endpoint_patterns'],
        'preventive': DRUG_RESISTANT_PATTERNS['endpoint_patterns'],
        'chronic': PREVENTION_PATTERNS['endpoint_patterns'],
        'device_neuromod': LATENT_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_migraine_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical migraine endpoint, preferring the LONGEST matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in MIGRAINE_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
