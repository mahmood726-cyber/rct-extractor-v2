"""
Blood Transfusion Strategies Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the tuberculosis / ARDS profiles.
Transfusion-medicine RCTs (restrictive vs liberal red-cell transfusion
thresholds, platelet / plasma transfusion, massive-transfusion / trauma
resuscitation, blood-product processing) report a distinct endpoint vocabulary
(mortality, transfusion exposure, units transfused, ischaemic / cardiac events,
infection, transfusion reactions, rebleeding) that the generic effect-size
engine does not recognise on its own.

Subspecialties:
- Threshold: restrictive vs liberal red blood cell transfusion threshold across
  settings (cardiac surgery, GI bleeding, critical illness, sepsis, myocardial
  infarction, oncology, hip fracture).
- Platelet / plasma: prophylactic vs therapeutic platelet transfusion, fresh
  frozen plasma / plasma transfusion, fibrinogen / cryoprecipitate.
- Massive / trauma: massive-transfusion protocols, fixed product ratios
  (1:1:1), whole blood, tranexamic acid, damage-control resuscitation.
- Processing / storage: fresh vs standard-age stored blood, leukoreduction,
  washed red cells, pathogen reduction.

Effect measures follow what these trials report: binary (mortality, transfusion
exposure / avoidance, ischaemic events, MACE, infection, transfusion reaction,
rebleeding) -> RR/OR/RD/HR; count/continuous (units transfused, haemoglobin,
length of stay) -> mean difference, handled by the shared continuous augmenter.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# TRANSFUSION ENDPOINTS
# ============================================================

TRANSFUSION_ENDPOINTS = {
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', '30-day mortality',
                    '90-day mortality', '28-day mortality', 'in-hospital mortality',
                    '60-day mortality', 'one-year mortality', 'overall survival'],
        'subspecialty': 'threshold',
        'measure_types': ['RR', 'OR', 'HR', 'RD']
    },
    'TRANSFUSION_EXPOSURE': {
        'aliases': ['transfusion', 'red blood cell transfusion', 'rbc transfusion',
                    'transfusion exposure', 'received a transfusion', 'any transfusion',
                    'proportion transfused', 'patients transfused', 'transfusion rate',
                    'allogeneic transfusion', 'transfusion avoidance', 'avoided transfusion'],
        'subspecialty': 'threshold',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'UNITS_TRANSFUSED': {
        'aliases': ['units transfused', 'number of units', 'red cell units',
                    'rbc units', 'units of blood', 'mean units transfused',
                    'volume transfused'],
        'subspecialty': 'threshold',
        'measure_types': ['MD']
    },
    'ISCHAEMIC_EVENTS': {
        'aliases': ['ischaemic events', 'ischemic events', 'myocardial infarction',
                    'acute coronary syndrome', 'ischaemia', 'ischemia',
                    'cerebrovascular events', 'composite ischaemic outcome'],
        'subspecialty': 'threshold',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'MACE': {
        'aliases': ['major adverse cardiac events', 'major adverse cardiovascular events',
                    'mace', 'cardiovascular events', 'cardiac death',
                    'death or myocardial infarction'],
        'subspecialty': 'threshold',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'INFECTION': {
        'aliases': ['infection', 'nosocomial infection', 'healthcare-associated infection',
                    'serious infection', 'pneumonia', 'sepsis', 'wound infection',
                    'bloodstream infection'],
        'subspecialty': 'threshold',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'REBLEEDING': {
        'aliases': ['rebleeding', 're-bleeding', 'recurrent bleeding',
                    'further bleeding', 'recurrent haemorrhage', 'recurrent hemorrhage',
                    'bleeding control', 'failure to control bleeding'],
        'subspecialty': 'massive',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'TRANSFUSION_REACTION': {
        'aliases': ['transfusion reaction', 'transfusion-related reaction',
                    'transfusion-associated circulatory overload', 'taco',
                    'transfusion-related acute lung injury', 'trali',
                    'febrile reaction', 'allergic transfusion reaction'],
        'subspecialty': 'platelet_plasma',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BLEEDING': {
        'aliases': ['bleeding', 'clinically significant bleeding', 'who bleeding',
                    'major bleeding', 'haemorrhage', 'hemorrhage', 'bleeding events',
                    'grade 2 bleeding'],
        'subspecialty': 'platelet_plasma',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HB_LEVEL': {
        'aliases': ['haemoglobin', 'hemoglobin', 'haemoglobin level', 'hemoglobin level',
                    'haemoglobin concentration', 'nadir haemoglobin', 'mean haemoglobin'],
        'subspecialty': 'threshold',
        'measure_types': ['MD']
    },
    'LENGTH_OF_STAY': {
        'aliases': ['length of stay', 'hospital length of stay', 'icu length of stay',
                    'duration of hospital stay', 'time to discharge'],
        'subspecialty': 'threshold',
        'measure_types': ['MD']
    },
    'ORGAN_DYSFUNCTION': {
        'aliases': ['organ dysfunction', 'multiple organ failure', 'organ failure',
                    'acute kidney injury', 'respiratory failure',
                    'multiorgan dysfunction'],
        'subspecialty': 'massive',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# THRESHOLD PATTERNS
# ============================================================

THRESHOLD_PATTERNS = {
    'detection_keywords': [
        r'restrictive\s+(?:vs\.?\s+liberal\s+)?(?:transfusion|strategy|threshold)',
        r'liberal\s+(?:transfusion|strategy|threshold)',
        r'transfusion\s+threshold|h(?:ae|e)moglobin\s+(?:trigger|threshold)',
        r'red[- ](?:blood[- ])?cell\s+transfusion|\brbc\s+transfusion\b',
        r'transfusion\s+strategy', r'\d\s*g/dl\s+(?:threshold|trigger)',
    ],
    'endpoint_patterns': [
        (r'major\s+adverse\s+(?:cardiac|cardiovascular)\s+events?|\bmace\b|'
         r'death\s+or\s+myocardial\s+infarction', 'MACE'),
        (r'isch(?:ae|e)mic\s+events?|myocardial\s+(?:infarction|isch(?:ae|e)mia)|'
         r'acute\s+coronary\s+syndrome|cerebrovascular\s+events?', 'ISCHAEMIC_EVENTS'),
        (r'(?:nosocomial\s+|healthcare[- ]associated\s+|serious\s+|wound\s+|bloodstream\s+)?'
         r'infection|\bsepsis\b', 'INFECTION'),
        (r'units?\s+transfused|number\s+of\s+units|red\s+cell\s+units|units\s+of\s+blood',
         'UNITS_TRANSFUSED'),
        (r'(?:received\s+a\s+|any\s+|proportion\s+|patients\s+)?transfus(?:ion|ed)'
         r'(?:\s+(?:exposure|rate|avoidance))?|avoided\s+transfusion', 'TRANSFUSION_EXPOSURE'),
        (r'(?:nadir\s+|mean\s+)?h(?:ae|e)moglobin(?:\s+(?:level|concentration))?', 'HB_LEVEL'),
        (r'(?:hospital\s+|icu\s+)?length\s+of\s+stay|time\s+to\s+discharge', 'LENGTH_OF_STAY'),
        (r'(?:30[- ]day|90[- ]day|28[- ]day|60[- ]day|in[- ]hospital|all[- ]cause)\s+'
         r'(?:mortality|death)|\bmortality\b|\bdeath\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'7\s*g/dl|8\s*g/dl|9\s*g/dl|70\s*g/l|80\s*g/l', r'cardiac\s+surgery|hip\s+fracture',
    ]
}


# ============================================================
# PLATELET / PLASMA PATTERNS
# ============================================================

PLATELET_PLASMA_PATTERNS = {
    'detection_keywords': [
        r'platelet\s+transfusion|prophylactic\s+platelet|therapeutic\s+platelet',
        r'fresh\s+frozen\s+plasma|\bffp\b|plasma\s+transfusion',
        r'fibrinogen\s+concentrate|cryoprecipitate',
        r'transfusion\s+reaction|\btaco\b|\btrali\b',
        r'platelet\s+count\s+threshold|prophylactic\s+transfusion',
    ],
    'endpoint_patterns': [
        (r'transfusion[- ](?:related|associated)\s+(?:reaction|circulatory\s+overload|'
         r'acute\s+lung\s+injury)|\btaco\b|\btrali\b|febrile\s+reaction|'
         r'allergic\s+transfusion\s+reaction', 'TRANSFUSION_REACTION'),
        (r'(?:clinically\s+significant\s+|who\s+|major\s+|grade\s+2\s+)?bleeding|'
         r'h(?:ae|e)morrhage', 'BLEEDING'),
        (r'(?:received\s+a\s+|any\s+|proportion\s+)?transfus(?:ion|ed)', 'TRANSFUSION_EXPOSURE'),
        (r'units?\s+transfused|number\s+of\s+units', 'UNITS_TRANSFUSED'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)|survival', 'MORTALITY'),
    ],
    'context_patterns': [
        r'10\s*x\s*10\^?9|platelet\s+count\s*<\s*\d+', r'haematolog\w+|stem[- ]cell',
    ]
}


# ============================================================
# MASSIVE / TRAUMA PATTERNS
# ============================================================

MASSIVE_PATTERNS = {
    'detection_keywords': [
        r'massive\s+transfusion|massive[- ]transfusion\s+protocol',
        r'1\s*:\s*1\s*:\s*1|fixed[- ]ratio|product\s+ratio|balanced\s+resuscitation',
        r'whole\s+blood|damage[- ]control\s+resuscitation',
        r'tranexamic\s+acid|\btxa\b', r'trauma\s+(?:resuscitation|h(?:ae|e)morrhage)',
        r'major\s+h(?:ae|e)morrhage',
    ],
    'endpoint_patterns': [
        (r're[- ]?bleeding|recurrent\s+(?:bleeding|h(?:ae|e)morrhage)|further\s+bleeding|'
         r'failure\s+to\s+control\s+bleeding|bleeding\s+control', 'REBLEEDING'),
        (r'(?:multiple\s+)?organ\s+(?:dysfunction|failure)|acute\s+kidney\s+injury|'
         r'multiorgan\s+dysfunction', 'ORGAN_DYSFUNCTION'),
        (r'units?\s+transfused|number\s+of\s+units|volume\s+transfused', 'UNITS_TRANSFUSED'),
        (r'(?:received\s+a\s+|any\s+)?transfus(?:ion|ed)', 'TRANSFUSION_EXPOSURE'),
        (r'(?:24[- ]hour|30[- ]day|in[- ]hospital|all[- ]cause)\s+(?:mortality|death)|'
         r'\bmortality\b|\bdeath\b', 'MORTALITY'),
        (r'(?:serious\s+)?infection|\bsepsis\b', 'INFECTION'),
    ],
    'context_patterns': [
        r'proper|prbc:ffp:platelet', r'exsanguination|coagulopathy',
    ]
}


# ============================================================
# PROCESSING / STORAGE PATTERNS
# ============================================================

PROCESSING_PATTERNS = {
    'detection_keywords': [
        r'fresh(?:er)?\s+(?:vs\.?\s+(?:older|standard)\s+)?(?:blood|red\s+cells)|'
        r'(?:storage\s+age|age\s+of\s+blood)\s+of\s+(?:red\s+cells|blood)',
        r'standard[- ]age\s+blood|stored\s+(?:red\s+cells|blood)',
        r'leukoreduc\w+|leucoreduc\w+|washed\s+red\s+cells',
        r'pathogen[- ](?:reduced|inactivat\w+)|irradiated\s+(?:blood|red\s+cells)',
    ],
    'endpoint_patterns': [
        (r'(?:serious\s+|nosocomial\s+)?infection|\bsepsis\b', 'INFECTION'),
        (r'(?:multiple\s+)?organ\s+(?:dysfunction|failure)', 'ORGAN_DYSFUNCTION'),
        (r'transfusion[- ](?:related|associated)\s+(?:reaction|circulatory\s+overload)|'
         r'\btaco\b|\btrali\b', 'TRANSFUSION_REACTION'),
        (r'units?\s+transfused', 'UNITS_TRANSFUSED'),
        (r'(?:all[- ]cause\s+|in[- ]hospital\s+|90[- ]day\s+)?(?:mortality|death)|survival',
         'MORTALITY'),
    ],
    'context_patterns': [
        r'mean\s+storage\s+(?:age|duration)', r'days\s+of\s+storage',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_transfusion_subspecialty(text: str) -> Tuple[str, float]:
    """Detect transfusion-strategy trial subspecialty.
    Returns (subspecialty, confidence). Subspecialties: threshold,
    platelet_plasma, massive, processing, general_transfusion."""
    text_lower = text.lower()
    scores = {'threshold': 0, 'platelet_plasma': 0, 'massive': 0, 'processing': 0}
    for kw in THRESHOLD_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['threshold'] += 1
    for kw in PLATELET_PLASMA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['platelet_plasma'] += 1
    for kw in MASSIVE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['massive'] += 1
    for kw in PROCESSING_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['processing'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_transfusion', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_transfusion_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'threshold': THRESHOLD_PATTERNS['endpoint_patterns'],
        'platelet_plasma': PLATELET_PLASMA_PATTERNS['endpoint_patterns'],
        'massive': MASSIVE_PATTERNS['endpoint_patterns'],
        'processing': PROCESSING_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_transfusion_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical transfusion endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in TRANSFUSION_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
