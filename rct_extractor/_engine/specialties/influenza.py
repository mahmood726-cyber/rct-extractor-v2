"""
Influenza Subspecialty Patterns and Endpoints

Per-disease profile (same shape as the other infectious-disease specialties).
DISTINCT from `pneumonia` (bacterial), `covid19` (SARS-CoV-2) and `respiratory`
(COPD/asthma/IPF). Influenza RCTs report an antiviral / vaccine endpoint
vocabulary across treatment, prophylaxis and complication-prevention settings.

Subspecialties:
- treatment (antiviral treatment of acute influenza): time to symptom
  alleviation, viral clearance. Agents: oseltamivir, zanamivir, baloxavir
  marboxil, peramivir, laninamivir.
- prevention (vaccine efficacy / post-exposure prophylaxis): laboratory-confirmed
  influenza incidence, vaccine efficacy. Agents: inactivated / live-attenuated /
  recombinant vaccine, oseltamivir or baloxavir prophylaxis.
- complications (severe influenza / complications): hospitalisation, pneumonia,
  otitis media, antibiotic use.
- mortality: influenza-related mortality, all-cause mortality.

Effect measures: binary (laboratory-confirmed influenza, hospitalisation,
complications) -> RR/OR/RD; time-to-event / continuous (time to alleviation) ->
HR / median / mean difference.
"""
from typing import Dict, List, Tuple, Optional
import re

INFLUENZA_ENDPOINTS = {
    'INFLUENZA_INCIDENCE': {
        'aliases': ['laboratory-confirmed influenza', 'lab-confirmed influenza',
                    'influenza incidence', 'confirmed influenza', 'influenza infection',
                    'symptomatic influenza', 'influenza illness'],
        'subspecialty': 'prevention', 'measure_types': ['RR', 'OR', 'RD', 'rate']},
    'VACCINE_EFFICACY': {
        'aliases': ['vaccine efficacy', 'vaccine effectiveness', 've'],
        'subspecialty': 'prevention', 'measure_types': ['rate', 'RR']},
    'TIME_TO_ALLEVIATION': {
        'aliases': ['time to alleviation of symptoms', 'time to symptom alleviation',
                    'time to alleviation', 'time to resolution of symptoms',
                    'time to clinical improvement', 'symptom alleviation'],
        'subspecialty': 'treatment', 'measure_types': ['HR', 'median', 'MD']},
    'HOSPITALIZATION': {
        'aliases': ['hospitalisation', 'hospitalization', 'hospital admission',
                    'admission to hospital'],
        'subspecialty': 'complications', 'measure_types': ['RR', 'OR', 'RD']},
    'COMPLICATIONS': {
        'aliases': ['influenza-related complications', 'complications',
                    'lower respiratory tract complications', 'pneumonia',
                    'otitis media', 'antibiotic use'],
        'subspecialty': 'complications', 'measure_types': ['RR', 'OR', 'RD']},
    'INFLUENZA_MORTALITY': {
        'aliases': ['influenza-related mortality', 'influenza mortality',
                    'influenza death', 'death from influenza'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
}

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'oseltamivir|tamiflu', r'zanamivir|relenza', r'baloxavir(?:\s+marboxil)?|xofluza',
        r'peramivir|rapivab', r'laninamivir', r'neuraminidase\s+inhibitor',
        r'time\s+to\s+(?:alleviation|resolution)\s+of\s+symptoms',
        r'antiviral\s+(?:treatment|therapy)\s+(?:of|for)\s+influenza',
    ],
    'endpoint_patterns': [
        (r'time\s+to\s+(?:alleviation|resolution)\s+of\s+symptoms|'
         r'time\s+to\s+(?:symptom\s+)?(?:alleviation|clinical\s+improvement)',
         'TIME_TO_ALLEVIATION'),
        (r'laboratory[- ]confirmed\s+influenza|symptomatic\s+influenza', 'INFLUENZA_INCIDENCE'),
    ],
    'context_patterns': [r'viral\s+(?:load|titer|titre|clearance|shedding)', r'\bpcr\b']
}

PREVENTION_PATTERNS = {
    'detection_keywords': [
        r'influenza\s+vaccin', r'vaccine\s+(?:efficacy|effectiveness)',
        r'(?:inactivated|live[- ]attenuated|recombinant|quadrivalent|trivalent)\s+(?:influenza\s+)?vaccine',
        r'post[- ]exposure\s+prophylaxis', r'(?:chemo)?prophylaxis',
        r'(?:oseltamivir|baloxavir)\s+prophylaxis', r'\blaiv\b|\biiv\b',
    ],
    'endpoint_patterns': [
        (r'vaccine\s+(?:efficacy|effectiveness)', 'VACCINE_EFFICACY'),
        (r'laboratory[- ]confirmed\s+influenza|confirmed\s+influenza|influenza\s+'
         r'(?:incidence|infection|illness)|symptomatic\s+influenza', 'INFLUENZA_INCIDENCE'),
    ],
    'context_patterns': [r'h(?:a)?emagglutination\s+inhibition|\bhai\b', r'seroconversion']
}

COMPLICATIONS_PATTERNS = {
    'detection_keywords': [
        r'influenza[- ]related\s+complication', r'hospitali[sz]ation',
        r'lower\s+respiratory\s+tract\s+complication', r'secondary\s+(?:bacterial\s+)?pneumonia',
        r'otitis\s+media', r'antibiotic\s+use', r'severe\s+influenza',
        r'intensive\s+care|\bicu\b',
    ],
    'endpoint_patterns': [
        (r'hospitali[sz]ation|hospital\s+admission|admission\s+to\s+hospital', 'HOSPITALIZATION'),
        (r'influenza[- ]related\s+complication|lower\s+respiratory\s+tract\s+complication|'
         r'secondary\s+(?:bacterial\s+)?pneumonia|otitis\s+media|antibiotic\s+use|'
         r'\bcomplications?\b', 'COMPLICATIONS'),
    ],
    'context_patterns': [r'high[- ]risk\s+(?:patients|adults)', r'comorbidit']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'influenza[- ]?related\s+mortality|influenza\s+mortality',
        r'influenza\s+death|death\s+from\s+influenza', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'influenza[- ]?(?:related\s+)?(?:mortality|death)|death\s+from\s+influenza',
         'INFLUENZA_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_influenza_subspecialty(text: str) -> Tuple[str, float]:
    """Detect influenza trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: treatment, prevention, complications, mortality,
    general_influenza."""
    text_lower = text.lower()
    scores = {'treatment': 0, 'prevention': 0, 'complications': 0, 'mortality': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['prevention'] += 1
    for kw in COMPLICATIONS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['complications'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_influenza', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_influenza_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'prevention': PREVENTION_PATTERNS['endpoint_patterns'],
        'complications': COMPLICATIONS_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_influenza_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical influenza endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in INFLUENZA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
