"""
Cardiology Subspecialty Patterns and Endpoints

Subspecialties:
- Heart Failure (HFrEF, HFpEF, HFmrEF)
- Acute Coronary Syndrome (STEMI, NSTEMI, UA)
- Atrial Fibrillation (paroxysmal, persistent, permanent)
- Valvular Heart Disease (AS, MR, AR, MS, TAVR, SAVR)
- Structural Heart Disease
- Coronary Artery Disease (stable CAD, CTO)
"""

from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# CARDIOLOGY ENDPOINTS
# ============================================================

CARDIOLOGY_ENDPOINTS = {
    # Primary Composites
    'CV_DEATH_OR_HF_HOSP': {
        'aliases': ['cardiovascular death or hospitalization for heart failure',
                    'cv death or hf hospitalization', 'cv death or hfh',
                    'primary composite', 'primary outcome'],
        'subspecialty': 'heart_failure',
        'measure_types': ['HR', 'RR']
    },
    'MACE_3PT': {
        'aliases': ['mace', 'major adverse cardiovascular events',
                    'cv death, mi, or stroke', '3-point mace'],
        'subspecialty': 'acs',
        'measure_types': ['HR', 'RR']
    },
    'MACE_4PT': {
        'aliases': ['4-point mace', 'cv death, mi, stroke, or ua'],
        'subspecialty': 'acs',
        'measure_types': ['HR', 'RR']
    },

    # Death Endpoints
    'ALL_CAUSE_DEATH': {
        'aliases': ['all-cause mortality', 'death from any cause',
                    'all-cause death', 'total mortality'],
        'subspecialty': 'all',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'CV_DEATH': {
        'aliases': ['cardiovascular death', 'cv death', 'cardiac death',
                    'death from cardiovascular causes'],
        'subspecialty': 'all',
        'measure_types': ['HR', 'RR']
    },

    # Heart Failure Specific
    'HF_HOSPITALIZATION': {
        'aliases': ['hospitalization for heart failure', 'hf hospitalization',
                    'hfh', 'heart failure hospitalization', 'worsening heart failure'],
        'subspecialty': 'heart_failure',
        'measure_types': ['HR', 'RR', 'RD']
    },
    'KCCQ_CSS': {
        'aliases': ['kccq clinical summary score', 'kccq-css', 'kccq score',
                    'kansas city cardiomyopathy questionnaire'],
        'subspecialty': 'heart_failure',
        'measure_types': ['MD']
    },
    'NT_PROBNP': {
        'aliases': ['nt-probnp', 'n-terminal pro-bnp', 'bnp'],
        'subspecialty': 'heart_failure',
        'measure_types': ['MD', 'ratio']
    },
    'LVEF': {
        'aliases': ['left ventricular ejection fraction', 'lvef', 'ef'],
        'subspecialty': 'heart_failure',
        'measure_types': ['MD']
    },

    # ACS Specific
    'MI': {
        'aliases': ['myocardial infarction', 'mi', 'heart attack',
                    'nonfatal mi', 'fatal or nonfatal mi'],
        'subspecialty': 'acs',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'STENT_THROMBOSIS': {
        'aliases': ['stent thrombosis', 'definite stent thrombosis',
                    'probable stent thrombosis'],
        'subspecialty': 'acs',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'BLEEDING_MAJOR': {
        'aliases': ['major bleeding', 'timi major bleeding', 'barc 3-5',
                    'gusto severe bleeding', 'isth major bleeding'],
        'subspecialty': 'acs',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'REVASCULARIZATION': {
        'aliases': ['urgent revascularization', 'target vessel revascularization',
                    'tvr', 'tlr', 'target lesion revascularization'],
        'subspecialty': 'acs',
        'measure_types': ['HR', 'RR']
    },

    # AF Specific
    'STROKE_SYSTEMIC_EMBOLISM': {
        'aliases': ['stroke or systemic embolism', 'stroke/se',
                    'stroke or systemic embolic event'],
        'subspecialty': 'af',
        'measure_types': ['HR', 'RR']
    },
    'STROKE': {
        'aliases': ['stroke', 'ischemic stroke', 'hemorrhagic stroke',
                    'any stroke', 'disabling stroke'],
        'subspecialty': 'af',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'INTRACRANIAL_HEMORRHAGE': {
        'aliases': ['intracranial hemorrhage', 'ich', 'intracranial bleeding'],
        'subspecialty': 'af',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # Valve Specific
    'VALVE_MORTALITY': {
        'aliases': ['all-cause mortality', 'death', '30-day mortality',
                    '1-year mortality'],
        'subspecialty': 'valve',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'VALVE_COMPOSITE': {
        'aliases': ['death, stroke, or rehospitalization',
                    'all-cause mortality or disabling stroke'],
        'subspecialty': 'valve',
        'measure_types': ['HR', 'RR']
    }
}


# ============================================================
# HEART FAILURE PATTERNS
# ============================================================

HEART_FAILURE_PATTERNS = {
    'detection_keywords': [
        r'heart\s+failure',
        r'hfref', r'hfpef', r'hfmref',
        r'reduced\s+ejection\s+fraction',
        r'preserved\s+ejection\s+fraction',
        r'lvef\s*[<≤]\s*\d+',
        r'nyha\s+class',
        r'nt-?pro\s*bnp',
        r'sglt2\s+inhibitor',
        r'empagliflozin|dapagliflozin|canagliflozin|sotagliflozin',
        r'sacubitril|valsartan|entresto',
        r'arni'
    ],

    'endpoint_patterns': [
        # Primary composite
        (r'cardiovascular\s+death\s+or\s+(?:first\s+)?hospitalization\s+for\s+(?:worsening\s+)?heart\s+failure',
         'CV_DEATH_OR_HF_HOSP'),
        (r'cv\s+death\s+or\s+hf\s+hosp', 'CV_DEATH_OR_HF_HOSP'),
        (r'primary\s+(?:composite\s+)?(?:end\s*point|outcome)', 'CV_DEATH_OR_HF_HOSP'),

        # Individual endpoints
        (r'(?:total\s+)?(?:first\s+and\s+recurrent\s+)?hospitalizations?\s+for\s+(?:worsening\s+)?heart\s+failure',
         'HF_HOSPITALIZATION'),
        (r'worsening\s+heart\s+failure\s+events?', 'HF_HOSPITALIZATION'),
        (r'urgent\s+heart\s+failure\s+visit', 'HF_HOSPITALIZATION'),

        # Quality of life
        (r'kccq(?:-css)?\s+(?:clinical\s+summary\s+)?score', 'KCCQ_CSS'),
        (r'kansas\s+city\s+cardiomyopathy', 'KCCQ_CSS'),

        # Biomarkers
        (r'nt-?pro\s*bnp', 'NT_PROBNP'),
        (r'ejection\s+fraction|lvef', 'LVEF')
    ],

    'context_patterns': [
        r'ef\s*[<≤]\s*40\s*%?',  # HFrEF
        r'ef\s*[≥>]\s*50\s*%?',  # HFpEF
        r'ef\s*(?:40|41|42|43|44|45|46|47|48|49)\s*%?',  # HFmrEF
        r'nyha\s+(?:class\s+)?(?:ii|iii|iv|2|3|4)'
    ]
}


# ============================================================
# ACS PATTERNS (STEMI, NSTEMI, UA)
# ============================================================

ACS_PATTERNS = {
    'detection_keywords': [
        r'acute\s+coronary\s+syndrome',
        r'acs',
        r'stemi', r'nstemi',
        r'st[- ]?elevation\s+myocardial\s+infarction',
        r'non[- ]?st[- ]?elevation',
        r'unstable\s+angina',
        r'myocardial\s+infarction',
        r'troponin',
        r'pci|percutaneous\s+coronary\s+intervention',
        r'dual\s+antiplatelet',
        r'ticagrelor|prasugrel|clopidogrel',
        r'p2y12\s+inhibitor'
    ],

    'endpoint_patterns': [
        # MACE composites
        (r'major\s+adverse\s+card(?:iac|iovascular)\s+events?', 'MACE_3PT'),
        (r'mace', 'MACE_3PT'),
        (r'cv\s+death[,\s]+(?:nonfatal\s+)?mi[,\s]+(?:or\s+)?(?:nonfatal\s+)?stroke', 'MACE_3PT'),

        # Individual endpoints
        (r'myocardial\s+infarction|(?:nonfatal\s+)?mi', 'MI'),
        (r'stent\s+thrombosis', 'STENT_THROMBOSIS'),
        (r'(?:definite|probable)\s+stent\s+thrombosis', 'STENT_THROMBOSIS'),

        # Revascularization
        (r'urgent\s+(?:coronary\s+)?revascularization', 'REVASCULARIZATION'),
        (r'target\s+(?:vessel|lesion)\s+revascularization', 'REVASCULARIZATION'),

        # Bleeding
        (r'(?:timi|barc|gusto|isth)\s+(?:major\s+)?bleeding', 'BLEEDING_MAJOR'),
        (r'major\s+bleeding', 'BLEEDING_MAJOR'),
        (r'life[- ]?threatening\s+bleeding', 'BLEEDING_MAJOR')
    ],

    'context_patterns': [
        r'within\s+\d+\s+(?:hours?|days?)\s+of\s+(?:symptom\s+onset|admission)',
        r'troponin[- ]?(?:positive|elevated)',
        r'st[- ]?(?:segment\s+)?(?:elevation|depression)',
        r'index\s+(?:event|pci|hospitalization)'
    ]
}


# ============================================================
# AF PATTERNS
# ============================================================

AF_PATTERNS = {
    'detection_keywords': [
        r'atrial\s+fibrillation',
        r'\baf\b',
        r'afib',
        r'paroxysmal|persistent|permanent',
        r'nonvalvular\s+af',
        r'nvaf',
        r'cha2ds2[- ]?vasc',
        r'has[- ]?bled',
        r'direct\s+oral\s+anticoagulant',
        r'doac|noac',
        r'apixaban|rivaroxaban|dabigatran|edoxaban',
        r'warfarin|vitamin\s+k\s+antagonist'
    ],

    'endpoint_patterns': [
        # Primary stroke prevention
        (r'stroke\s+or\s+systemic\s+embol', 'STROKE_SYSTEMIC_EMBOLISM'),
        (r'stroke/se', 'STROKE_SYSTEMIC_EMBOLISM'),

        # Stroke subtypes
        (r'(?:ischemic|hemorrhagic|any)\s+stroke', 'STROKE'),
        (r'disabling\s+stroke', 'STROKE'),

        # Bleeding
        (r'intracranial\s+(?:hemorrhage|bleeding)', 'INTRACRANIAL_HEMORRHAGE'),
        (r'\bich\b', 'INTRACRANIAL_HEMORRHAGE'),
        (r'major\s+bleeding', 'BLEEDING_MAJOR'),
        (r'(?:timi|isth|barc)\s+major', 'BLEEDING_MAJOR')
    ],

    'context_patterns': [
        r'cha2ds2[- ]?vasc\s*(?:score\s*)?(?:[≥>]\s*)?\d',
        r'has[- ]?bled\s*(?:score\s*)?(?:[≥>]\s*)?\d',
        r'(?:paroxysmal|persistent|permanent)\s+af',
        r'time\s+in\s+therapeutic\s+range|ttr'
    ]
}


# ============================================================
# VALVE PATTERNS (AS, MR, TAVR, SAVR)
# ============================================================

VALVE_PATTERNS = {
    'detection_keywords': [
        r'aortic\s+stenosis',
        r'\bas\b',
        r'mitral\s+regurgitation',
        r'\bmr\b',
        r'tavr|tavi',
        r'transcatheter\s+aortic\s+valve',
        r'savr',
        r'surgical\s+aortic\s+valve',
        r'mitraclip|pascal',
        r'transcatheter\s+mitral',
        r'valve[- ]?in[- ]?valve'
    ],

    'endpoint_patterns': [
        # Mortality
        (r'(?:30[- ]?day|1[- ]?year|2[- ]?year)\s+(?:all[- ]?cause\s+)?mortality', 'VALVE_MORTALITY'),
        (r'death\s+(?:at|within|by)\s+\d+', 'VALVE_MORTALITY'),

        # Composites
        (r'death(?:,?\s+(?:or\s+)?stroke)?(?:,?\s+(?:or\s+)?rehospitalization)?', 'VALVE_COMPOSITE'),
        (r'all[- ]?cause\s+mortality\s+(?:or|and)\s+disabling\s+stroke', 'VALVE_COMPOSITE'),

        # Procedural outcomes
        (r'device\s+success', 'DEVICE_SUCCESS'),
        (r'valve\s+(?:area|gradient)', 'VALVE_HEMODYNAMICS'),
        (r'paravalvular\s+(?:leak|regurgitation)', 'PARAVALVULAR_LEAK')
    ],

    'context_patterns': [
        r'severe\s+(?:aortic\s+stenosis|as|mr)',
        r'(?:prohibitive|high|intermediate|low)\s+(?:surgical\s+)?risk',
        r'sts[- ]?prom\s*(?:score\s*)?',
        r'euroscore',
        r'aortic\s+valve\s+area|ava'
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_cardiology_subspecialty(text: str) -> Tuple[str, float]:
    """
    Detect cardiology subspecialty from text.

    Returns:
        Tuple of (subspecialty, confidence)
        Subspecialties: 'heart_failure', 'acs', 'af', 'valve', 'general_cardiology'
    """
    text_lower = text.lower()

    scores = {
        'heart_failure': 0,
        'acs': 0,
        'af': 0,
        'valve': 0
    }

    # Score each subspecialty
    for keyword in HEART_FAILURE_PATTERNS['detection_keywords']:
        if re.search(keyword, text_lower):
            scores['heart_failure'] += 1

    for keyword in ACS_PATTERNS['detection_keywords']:
        if re.search(keyword, text_lower):
            scores['acs'] += 1

    for keyword in AF_PATTERNS['detection_keywords']:
        if re.search(keyword, text_lower):
            scores['af'] += 1

    for keyword in VALVE_PATTERNS['detection_keywords']:
        if re.search(keyword, text_lower):
            scores['valve'] += 1

    # Find best match
    best_subspecialty = max(scores, key=scores.get)
    best_score = scores[best_subspecialty]
    total = sum(scores.values())

    if best_score == 0:
        return ('general_cardiology', 0.5)

    confidence = best_score / total if total > 0 else 0.5
    return (best_subspecialty, confidence)


def get_cardiology_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    """Get endpoint patterns for a specific subspecialty."""
    patterns_map = {
        'heart_failure': HEART_FAILURE_PATTERNS['endpoint_patterns'],
        'acs': ACS_PATTERNS['endpoint_patterns'],
        'af': AF_PATTERNS['endpoint_patterns'],
        'valve': VALVE_PATTERNS['endpoint_patterns']
    }
    return patterns_map.get(subspecialty, [])


def normalize_cardiology_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize endpoint name to canonical form."""
    endpoint_lower = endpoint.lower()

    for canonical, info in CARDIOLOGY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower:
                return canonical

    return endpoint.upper()
