"""
Obstructive sleep apnoea (OSA) Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the respiratory / cardiology
profiles, but for OBSTRUCTIVE SLEEP APNOEA specifically -- a sleep-medicine
disease not targeted by any existing profile. OSA RCTs report an endpoint
vocabulary anchored on the apnoea-hypopnoea index (AHI), oxygen desaturation
index (ODI), Epworth Sleepiness Scale (ESS), CPAP adherence, nocturnal oxygen
saturation and ambulatory blood pressure.

Subspecialties:
- cpap (positive-airway-pressure therapy):
    AHI (events/h; MD), ESS (MD), CPAP adherence (hours/night; MD), ambulatory
    blood pressure (mmHg; MD), responder / AHI normalisation (RR/OR).
- oral_appliance (mandibular advancement device, MAD):
    AHI (MD), ESS (MD), treatment response (RR/OR).
- intervention (surgery / hypoglossal nerve stimulation / pharmacotherapy /
  weight loss):
    AHI (MD), ODI (MD), >=50% AHI reduction responder (RR/OR).

Effect measures: binary (treatment response / AHI normalisation, >=50% AHI
reduction) -> RR/OR/RD; continuous (AHI, ODI, ESS, adherence, minimum SpO2,
blood pressure, FOSQ quality of life) -> MD/SMD. None is log-normal.

British/American spelling: APNOEA (British) vs APNEA (American) -- the British
form inserts an extra 'o' before 'ea' -> 'apno?ea', NOT '[oe]a'; likewise
HYPOPNOEA vs HYPOPNEA -> 'hypopno?ea'. Both handled in the patterns below.

Routing note: this profile claims the sleep-apnoea anchors (obstructive sleep
apnoea, OSA/OSAS, apnoea-hypopnoea index / AHI, CPAP, Epworth Sleepiness Scale,
polysomnography, mandibular advancement, hypoglossal nerve stimulation) that no
existing profile claims.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# OSA ENDPOINTS
# ============================================================

OBSTRUCTIVE_SLEEP_APNEA_ENDPOINTS = {
    'AHI': {
        'aliases': ['apnoea-hypopnoea index', 'apnea-hypopnea index', 'ahi',
                    'apnoea hypopnoea index', 'apnea hypopnea index',
                    'change in ahi', 'mean ahi', 'respiratory disturbance index', 'rdi'],
        'subspecialty': 'cpap',
        'measure_types': ['MD', 'SMD']
    },
    'ODI': {
        'aliases': ['oxygen desaturation index', 'odi', 'desaturation index',
                    '4% oxygen desaturation index', '3% oxygen desaturation index',
                    'change in odi', 'mean odi'],
        'subspecialty': 'cpap',
        'measure_types': ['MD', 'SMD']
    },
    'ESS': {
        'aliases': ['epworth sleepiness scale', 'epworth score', 'ess',
                    'epworth sleepiness score', 'daytime sleepiness', 'change in ess',
                    'mean epworth sleepiness scale'],
        'subspecialty': 'cpap',
        'measure_types': ['MD', 'SMD']
    },
    'CPAP_ADHERENCE': {
        'aliases': ['cpap adherence', 'cpap usage', 'cpap compliance',
                    'hours of cpap use', 'nightly cpap use', 'adherence to cpap',
                    'mean nightly usage', 'pap adherence'],
        'subspecialty': 'cpap',
        'measure_types': ['MD', 'SMD']
    },
    'BLOOD_PRESSURE': {
        'aliases': ['systolic blood pressure', 'diastolic blood pressure',
                    '24-hour blood pressure', 'ambulatory blood pressure',
                    'mean arterial pressure', 'blood pressure', 'nocturnal blood pressure',
                    'change in systolic blood pressure'],
        'subspecialty': 'cpap',
        'measure_types': ['MD', 'SMD']
    },
    'MINIMUM_SPO2': {
        'aliases': ['minimum oxygen saturation', 'nadir oxygen saturation',
                    'lowest oxygen saturation', 'minimum spo2', 'nadir spo2',
                    'mean oxygen saturation', 'nocturnal oxygen saturation',
                    'time below 90%'],
        'subspecialty': 'intervention',
        'measure_types': ['MD', 'SMD']
    },
    'FOSQ': {
        'aliases': ['functional outcomes of sleep questionnaire', 'fosq',
                    'sleep-related quality of life', 'fosq-10', 'fosq score',
                    'quality of life'],
        'subspecialty': 'cpap',
        'measure_types': ['MD', 'SMD']
    },
    'AHI_RESPONDER': {
        'aliases': ['treatment response', 'ahi responder', 'responder rate',
                    'ahi normalisation', 'ahi normalization', '50% reduction in ahi',
                    'reduction in ahi of at least 50%', 'surgical success',
                    'proportion of responders'],
        'subspecialty': 'intervention',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# CPAP PATTERNS (positive-airway-pressure therapy)
# ============================================================

CPAP_PATTERNS = {
    'detection_keywords': [
        r'continuous\s+positive\s+airway\s+pressure|\bcpap\b|\bpap\b\s+therapy',
        r'obstructive\s+sleep\s+apno?ea|\bosa\b|\bosas\b',
        r'apno?ea[- ]hypopno?ea\s+index|\bahi\b', r'epworth',
        r'auto[- ]?(?:titrating|adjusting)\s+pap|\bapap\b|\bbipap\b',
        r'polysomnograph', r'sleep[- ]disordered\s+breathing',
    ],
    'endpoint_patterns': [
        (r'apno?ea[- ]hypopno?ea\s+index|\bahi\b|respiratory\s+disturbance\s+index|\brdi\b',
         'AHI'),
        (r'oxygen\s+desaturation\s+index|\bodi\b|desaturation\s+index', 'ODI'),
        (r'epworth\s+sleepiness\s+(?:scale|score)|\bess\b|daytime\s+sleepiness', 'ESS'),
        (r'cpap\s+(?:adherence|usage|compliance)|pap\s+adherence|hours?\s+of\s+cpap\s+use|'
         r'nightly\s+(?:cpap\s+)?(?:use|usage)', 'CPAP_ADHERENCE'),
        (r'(?:systolic|diastolic|ambulatory|24[- ]hour|nocturnal)\s+blood\s+pressure|'
         r'mean\s+arterial\s+pressure', 'BLOOD_PRESSURE'),
        (r'functional\s+outcomes\s+of\s+sleep\s+questionnaire|\bfosq(?:-10)?\b', 'FOSQ'),
    ],
    'context_patterns': [
        r'events?\s+per\s+hour|events?/h', r'\bmmhg\b', r'at\s+(?:week|month)\s+\d+',
    ]
}


# ============================================================
# ORAL_APPLIANCE PATTERNS (mandibular advancement device)
# ============================================================

ORAL_APPLIANCE_PATTERNS = {
    'detection_keywords': [
        r'mandibular\s+advancement\s+device|\bmad\b', r'oral\s+appliance',
        r'mandibular\s+advancement\s+splint', r'dental\s+appliance',
        r'obstructive\s+sleep\s+apno?ea|\bosa\b', r'apno?ea[- ]hypopno?ea\s+index|\bahi\b',
    ],
    'endpoint_patterns': [
        (r'apno?ea[- ]hypopno?ea\s+index|\bahi\b', 'AHI'),
        (r'epworth\s+sleepiness\s+(?:scale|score)|\bess\b', 'ESS'),
        (r'treatment\s+response|ahi\s+normali[sz]ation|responder\s+rate', 'AHI_RESPONDER'),
    ],
    'context_patterns': [
        r'titration', r'mandibular\s+protrusion', r'at\s+(?:week|month)\s+\d+',
    ]
}


# ============================================================
# INTERVENTION PATTERNS (surgery / HNS / drug / weight loss)
# ============================================================

INTERVENTION_PATTERNS = {
    'detection_keywords': [
        r'hypoglossal\s+nerve\s+stimulation|upper[- ]airway\s+stimulation',
        r'uvulopalatopharyngoplasty|\buppp\b', r'maxillomandibular\s+advancement',
        r'tirzepatide|atomoxetine|oxybutynin', r'weight\s+loss',
        r'obstructive\s+sleep\s+apno?ea|\bosa\b',
    ],
    'endpoint_patterns': [
        (r'apno?ea[- ]hypopno?ea\s+index|\bahi\b', 'AHI'),
        (r'oxygen\s+desaturation\s+index|\bodi\b', 'ODI'),
        (r'(?:minimum|nadir|lowest)\s+(?:oxygen\s+saturation|spo2)|'
         r'time\s+below\s+90%|nocturnal\s+oxygen\s+saturation', 'MINIMUM_SPO2'),
        (r'(?:surgical\s+)?success|treatment\s+response|responder\s+rate|'
         r'(?:>=?\s*)?50%\s+reduction\s+in\s+ahi|ahi\s+normali[sz]ation', 'AHI_RESPONDER'),
    ],
    'context_patterns': [
        r'events?\s+per\s+hour', r'sher\s+criteria', r'at\s+(?:month|week)\s+\d+',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_obstructive_sleep_apnea_subspecialty(text: str) -> Tuple[str, float]:
    """Detect OSA trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: cpap, oral_appliance, intervention."""
    text_lower = text.lower()
    scores = {'cpap': 0, 'oral_appliance': 0, 'intervention': 0}
    for kw in CPAP_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['cpap'] += 1
    for kw in ORAL_APPLIANCE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['oral_appliance'] += 1
    for kw in INTERVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['intervention'] += 1

    # A device/surgery anchor must beat the generic OSA/AHI overlap (which is
    # shared with the cpap block).
    if re.search(r'mandibular\s+advancement|oral\s+appliance|dental\s+appliance', text_lower):
        scores['oral_appliance'] += 1
    elif re.search(r'hypoglossal\s+nerve\s+stimulation|uvulopalatopharyngoplasty|\buppp\b|'
                   r'maxillomandibular\s+advancement|tirzepatide|atomoxetine', text_lower):
        scores['intervention'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('cpap', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_obstructive_sleep_apnea_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'cpap': CPAP_PATTERNS['endpoint_patterns'],
        'oral_appliance': ORAL_APPLIANCE_PATTERNS['endpoint_patterns'],
        'intervention': INTERVENTION_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_obstructive_sleep_apnea_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical endpoint, preferring the LONGEST matching alias so
    specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in OBSTRUCTIVE_SLEEP_APNEA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
