"""
Urinary Incontinence / Overactive Bladder (OAB) Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the BPH / women's-health profiles.
Urinary incontinence and OAB are highly prevalent (especially in women and older
adults) and their RCTs (antimuscarinics, beta-3 agonists, intradetrusor botulinum
toxin, sacral neuromodulation, tibial nerve stimulation, midurethral slings,
pelvic-floor muscle training, duloxetine) report a distinct bladder-diary and
continence endpoint vocabulary the generic effect-size engine does not recognise
on its own.

Subspecialties:
- Oab (overactive bladder / urgency): urgency urinary incontinence (UUI)
  episodes, micturition frequency, urgency episodes, nocturia, continence /
  dry rate, treatment response. Interventions: antimuscarinics (solifenacin,
  tolterodine, fesoterodine, oxybutynin, darifenacin, trospium), beta-3 agonists
  (mirabegron, vibegron). Class adverse events: dry mouth, constipation.
- Sui (stress urinary incontinence): incontinence episodes, pad test / pad
  weight, objective cure / continence. Interventions: midurethral sling
  (TVT/TOT), Burch colposuspension, duloxetine, pelvic-floor muscle training.
- Procedural (refractory / device): intradetrusor onabotulinumtoxinA, sacral
  neuromodulation, percutaneous tibial nerve stimulation (PTNS); response,
  continence, urinary retention / clean intermittent catheterisation, urinary
  tract infection.
- Qol (symptom & quality of life): ICIQ, OAB-q, King's Health Questionnaire
  (KHQ), patient perception of bladder condition, treatment benefit.

Effect measures: continuous (UUI / incontinence episodes per day, micturitions
per day, urgency episodes, nocturia, pad weight, ICIQ / OAB-q / KHQ scores) ->
MD/SMD; binary (continence / dry rate, objective cure, treatment response,
retention, UTI, dry mouth, constipation) -> RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# URINARY INCONTINENCE / OAB ENDPOINTS
# ============================================================

URINARY_INCONTINENCE_ENDPOINTS = {
    # --- OAB (overactive bladder / urgency) ---
    'UUI_EPISODES': {
        'aliases': ['urgency urinary incontinence episodes', 'uui episodes',
                    'urge incontinence episodes', 'incontinence episodes per day',
                    'urgency incontinence episodes', 'number of incontinence episodes',
                    'daily incontinence episodes'],
        'subspecialty': 'oab',
        'measure_types': ['MD', 'SMD']
    },
    'MICTURITION_FREQUENCY': {
        'aliases': ['micturition frequency', 'micturitions per day', 'voiding frequency',
                    'number of micturitions', 'daily micturitions', 'frequency of urination',
                    'voids per day'],
        'subspecialty': 'oab',
        'measure_types': ['MD', 'SMD']
    },
    'URGENCY_EPISODES': {
        'aliases': ['urgency episodes', 'urgency episodes per day', 'episodes of urgency',
                    'daily urgency episodes', 'number of urgency episodes'],
        'subspecialty': 'oab',
        'measure_types': ['MD', 'SMD']
    },
    'NOCTURIA': {
        'aliases': ['nocturia', 'nocturnal voids', 'nighttime voiding',
                    'nocturnal micturition', 'nocturia episodes'],
        'subspecialty': 'oab',
        'measure_types': ['MD', 'SMD']
    },
    'CONTINENCE': {
        'aliases': ['continence', 'dry rate', 'complete continence', 'fully continent',
                    'zero incontinence episodes', '100% reduction', 'continent',
                    'dryness'],
        'subspecialty': 'oab',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TREATMENT_RESPONSE': {
        'aliases': ['treatment response', 'responder', 'response rate', 'responders',
                    'positive response', '50% reduction', 'at least 50% reduction'],
        'subspecialty': 'oab',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'DRY_MOUTH': {
        'aliases': ['dry mouth', 'xerostomia'],
        'subspecialty': 'oab',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'CONSTIPATION': {
        'aliases': ['constipation'],
        'subspecialty': 'oab',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- SUI (stress urinary incontinence) ---
    'INCONTINENCE_EPISODES': {
        'aliases': ['stress incontinence episodes', 'leakage episodes',
                    'incontinence episode frequency', 'episodes of leakage'],
        'subspecialty': 'sui',
        'measure_types': ['MD', 'SMD']
    },
    'PAD_TEST': {
        'aliases': ['pad test', 'pad weight', '1-hour pad test', '24-hour pad test',
                    'pad weight gain', 'cough stress test', 'pad use'],
        'subspecialty': 'sui',
        'measure_types': ['MD', 'SMD', 'RR', 'OR']
    },
    'OBJECTIVE_CURE': {
        'aliases': ['objective cure', 'cure rate', 'cured', 'objective cure rate',
                    'subjective cure', 'negative cough stress test', 'continence rate'],
        'subspecialty': 'sui',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Procedural (refractory / device) ---
    'URINARY_RETENTION': {
        'aliases': ['urinary retention', 'acute retention', 'post-void residual',
                    'clean intermittent catheterisation', 'clean intermittent catheterization',
                    'need for catheterisation', 'need for catheterization',
                    'voiding difficulty'],
        'subspecialty': 'procedural',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'URINARY_TRACT_INFECTION': {
        'aliases': ['urinary tract infection', 'uti', 'symptomatic uti',
                    'culture-confirmed uti'],
        'subspecialty': 'procedural',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'REPEAT_TREATMENT': {
        'aliases': ['repeat treatment', 'reinjection', 're-injection', 'retreatment',
                    'repeat injection', 'further treatment', 'need for retreatment'],
        'subspecialty': 'procedural',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Qol (symptom & quality of life) ---
    'ICIQ': {
        'aliases': ['iciq', 'iciq-sf', 'iciq-ui', 'international consultation on incontinence',
                    'iciq score'],
        'subspecialty': 'qol',
        'measure_types': ['MD', 'SMD']
    },
    'OAB_Q': {
        'aliases': ['oab-q', 'oab-q sf', 'oab questionnaire', 'symptom bother',
                    'oabq', 'health-related quality of life'],
        'subspecialty': 'qol',
        'measure_types': ['MD', 'SMD']
    },
    'KHQ': {
        'aliases': ['khq', "king's health questionnaire", 'kings health questionnaire',
                    'quality of life'],
        'subspecialty': 'qol',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# OAB PATTERNS
# ============================================================

OAB_PATTERNS = {
    'detection_keywords': [
        r'overactive\s+bladder|\boab\b', r'urgency\s+urinary\s+incontinence|\buui\b',
        r'urge\s+incontinence', r'urinary\s+urgency', r'micturition\s+frequency',
        r'mirabegron|vibegron', r'solifenacin|tolterodine|fesoterodine|oxybutynin|'
        r'darifenacin|trospium', r'antimuscarinic|anticholinergic', r'beta[- ]?3\s+agonist',
        r'nocturia', r'detrusor\s+overactivity',
    ],
    'endpoint_patterns': [
        (r'urgency\s+urinary\s+incontinence\s+episodes|\buui\s+episodes|'
         r'urge\s+incontinence\s+episodes|incontinence\s+episodes(?:\s+per\s+day)?|'
         r'urgency\s+incontinence\s+episodes', 'UUI_EPISODES'),
        (r'micturition\s+frequency|micturitions?\s+per\s+day|voiding\s+frequency|'
         r'number\s+of\s+micturitions|voids?\s+per\s+day', 'MICTURITION_FREQUENCY'),
        (r'urgency\s+episodes(?:\s+per\s+day)?|episodes\s+of\s+urgency', 'URGENCY_EPISODES'),
        (r'nocturia|nocturnal\s+voids?|night[- ]?time\s+voiding|nocturnal\s+micturition',
         'NOCTURIA'),
        (r'\bcontinence\b|dry\s+rate|complete\s+continence|fully\s+continent|'
         r'100%\s+reduction|\bdryness\b', 'CONTINENCE'),
        (r'treatment\s+response|respon(?:se|der)s?(?:\s+rate)?|(?:at\s+least\s+)?50%\s+reduction',
         'TREATMENT_RESPONSE'),
        (r'dry\s+mouth|xerostomia', 'DRY_MOUTH'),
        (r'\bconstipation\b', 'CONSTIPATION'),
    ],
    'context_patterns': [
        r'bladder\s+diary', r'change\s+from\s+baseline', r'per\s+24\s+hours',
    ]
}


# ============================================================
# SUI PATTERNS
# ============================================================

SUI_PATTERNS = {
    'detection_keywords': [
        r'stress\s+urinary\s+incontinence|\bsui\b', r'midurethral\s+sling|\btvt\b|\btot\b',
        r'burch\s+colposuspension', r'duloxetine', r'pelvic\s+floor\s+muscle\s+training|\bpfmt\b',
        r'pad\s+test|pad\s+weight', r'cough\s+stress\s+test', r'leakage',
    ],
    'endpoint_patterns': [
        (r'stress\s+incontinence\s+episodes|leakage\s+episodes|'
         r'incontinence\s+episode\s+frequency|episodes\s+of\s+leakage', 'INCONTINENCE_EPISODES'),
        (r'(?:1|24)[- ]hour\s+pad\s+test|pad\s+(?:test|weight)(?:\s+gain)?|'
         r'cough\s+stress\s+test|pad\s+use', 'PAD_TEST'),
        (r'objective\s+cure(?:\s+rate)?|subjective\s+cure|\bcure\s+rate\b|\bcured\b|'
         r'negative\s+cough\s+stress\s+test|continence\s+rate', 'OBJECTIVE_CURE'),
    ],
    'context_patterns': [
        r'12[- ]month|24[- ]month|follow[- ]up', r'objective|subjective',
    ]
}


# ============================================================
# PROCEDURAL PATTERNS
# ============================================================

PROCEDURAL_PATTERNS = {
    'detection_keywords': [
        r'onabotulinumtoxin|botulinum\s+toxin|intradetrusor', r'sacral\s+neuromodulation',
        r'percutaneous\s+tibial\s+nerve|\bptns\b', r'tibial\s+nerve\s+stimulation',
        r'clean\s+intermittent\s+cath', r'refractory', r'reinjection|re[- ]injection',
    ],
    'endpoint_patterns': [
        (r'urinary\s+retention|acute\s+retention|clean\s+intermittent\s+cath\w+|'
         r'need\s+for\s+cath\w+|voiding\s+difficulty|elevated\s+post[- ]void\s+residual',
         'URINARY_RETENTION'),
        (r'urinary\s+tract\s+infection|\buti\b|symptomatic\s+uti', 'URINARY_TRACT_INFECTION'),
        (r'repeat\s+(?:treatment|injection)|re[- ]?injection|retreatment|'
         r'further\s+treatment|need\s+for\s+retreatment', 'REPEAT_TREATMENT'),
    ],
    'context_patterns': [
        r'100\s*(?:u|units)|200\s*(?:u|units)', r'duration\s+of\s+effect',
    ]
}


# ============================================================
# QOL PATTERNS
# ============================================================

QOL_PATTERNS = {
    'detection_keywords': [
        r'\biciq\b|international\s+consultation\s+on\s+incontinence', r'oab[- ]q',
        r"king'?s\s+health\s+questionnaire|\bkhq\b", r'quality\s+of\s+life',
        r'symptom\s+bother', r'patient\s+perception',
    ],
    'endpoint_patterns': [
        (r'\biciq(?:[- ](?:sf|ui))?\b|international\s+consultation\s+on\s+incontinence',
         'ICIQ'),
        (r'oab[- ]?q(?:\s+sf)?|oab\s+questionnaire|symptom\s+bother', 'OAB_Q'),
        (r"king'?s\s+health\s+questionnaire|\bkhq\b|quality\s+of\s+life", 'KHQ'),
    ],
    'context_patterns': [
        r'0[- ]to[- ]100', r'change\s+from\s+baseline',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_urinary_incontinence_subspecialty(text: str) -> Tuple[str, float]:
    """Detect UI/OAB trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: oab, sui, procedural, qol, general_incontinence."""
    text_lower = text.lower()
    scores = {'oab': 0, 'sui': 0, 'procedural': 0, 'qol': 0}
    for kw in OAB_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['oab'] += 1
    for kw in SUI_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['sui'] += 1
    for kw in PROCEDURAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['procedural'] += 1
    for kw in QOL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['qol'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_incontinence', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_urinary_incontinence_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'oab': OAB_PATTERNS['endpoint_patterns'],
        'sui': SUI_PATTERNS['endpoint_patterns'],
        'procedural': PROCEDURAL_PATTERNS['endpoint_patterns'],
        'qol': QOL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_urinary_incontinence_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical UI/OAB endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in URINARY_INCONTINENCE_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
