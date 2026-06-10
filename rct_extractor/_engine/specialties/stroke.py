"""
Stroke (cerebrovascular) Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the malaria / HIV / hepatitis /
respiratory profiles. Stroke RCTs report an endpoint vocabulary anchored on a
handful of standardised scales (modified Rankin Scale [mRS], NIHSS, Barthel
Index, Fugl-Meyer) that the generic effect-size engine does not recognise on its
own.

Subspecialties:
- Acute ischemic stroke (thrombolysis / thrombectomy):
    functional independence (mRS 0-2 at 90 days; RR/OR), ordinal mRS shift
    (common odds ratio cOR -- its OWN estimand, never pooled with the dichotomy),
    successful recanalisation/reperfusion (TICI 2b-3; RR/OR), early neurological
    improvement (NIHSS; MD), symptomatic intracranial haemorrhage (sICH safety
    harm; RR/OR), 90-day / all-cause mortality (RR/HR/OR).
- Hemorrhagic stroke (intracerebral haemorrhage):
    haematoma expansion (RR/OR), poor outcome (mRS 3-6; RR/OR), mortality.
- Secondary prevention (recurrent-event prevention after stroke/TIA):
    recurrent stroke (HR/RR), composite major vascular events (HR/RR), major
    bleeding (HR/RR), mortality.
- Recovery / rehabilitation:
    motor function (Fugl-Meyer; MD), Barthel Index (MD), NIHSS (MD).

Effect measures follow what these trials report: binary (mRS 0-2, recanalisation,
sICH, recurrent stroke, mortality) -> RR/OR/RD; ordinal mRS shift -> common OR;
time-to-event (recurrent stroke, MACE, mortality) -> HR; continuous (NIHSS,
Fugl-Meyer, Barthel) -> MD/SMD. None of the stroke continuous scales are
log-normal (bounded ordinal/interval scores), so no log-scale pooling is needed.

Routing note (coordinated with cardiology): atrial-fibrillation anticoagulation
trials whose PRIMARY estimand is stroke PREVENTION (e.g. apixaban vs warfarin in
AF) belong to cardiology's `af` subspecialty. We deliberately do NOT claim bare
'atrial fibrillation', 'anticoagulation', 'MACE', or 'major bleeding' as stroke
detection keywords; stroke anchors on stroke-specific terms (NIHSS, modified
Rankin, thrombectomy, thrombolysis, alteplase, tenecteplase, TICI, recurrent
stroke, intracerebral haemorrhage). A trial that mentions a *recurrent stroke*
endpoint in a stroke/TIA population routes to stroke secondary_prevention; a pure
AF-anticoagulation trial stays with cardiology.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# STROKE ENDPOINTS
# ============================================================

STROKE_ENDPOINTS = {
    # --- Acute ischemic stroke ---
    'FUNCTIONAL_INDEPENDENCE': {
        'aliases': ['functional independence', 'good functional outcome',
                    'good outcome', 'favourable outcome', 'favorable outcome',
                    'modified rankin scale 0-2', 'modified rankin scale 0 to 2',
                    'mrs 0-2', 'mrs 0 to 2', 'mrs 0-1', 'mrs of 0 to 2',
                    'mrs score of 0-2', 'excellent outcome'],
        'subspecialty': 'acute_ischemic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MRS_SHIFT': {
        'aliases': ['ordinal mrs shift', 'mrs shift', 'shift in the modified rankin scale',
                    'ordinal shift', 'shift analysis', 'modified rankin scale shift',
                    'rankin shift', 'distribution of modified rankin scale scores',
                    'ordinal analysis of the modified rankin scale'],
        'subspecialty': 'acute_ischemic',
        'measure_types': ['cOR', 'OR']
    },
    'RECANALIZATION': {
        'aliases': ['successful recanalization', 'successful recanalisation',
                    'successful reperfusion', 'recanalization', 'recanalisation',
                    'reperfusion', 'tici 2b-3', 'tici 2b/3', 'tici 2b to 3',
                    'modified tici 2b-3', 'mtici 2b-3', 'substantial reperfusion'],
        'subspecialty': 'acute_ischemic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'EARLY_NEURO_IMPROVEMENT': {
        'aliases': ['early neurological improvement', 'early neurologic improvement',
                    'nihss', 'nih stroke scale', 'national institutes of health stroke scale',
                    'change in nihss', 'nihss score', 'reduction in nihss',
                    'early neurological recovery'],
        'subspecialty': 'acute_ischemic',
        'measure_types': ['MD', 'SMD', 'RR', 'OR']
    },
    'SYMPTOMATIC_ICH': {
        'aliases': ['symptomatic intracranial hemorrhage', 'symptomatic intracranial haemorrhage',
                    'symptomatic intracerebral hemorrhage', 'symptomatic intracerebral haemorrhage',
                    'sich', 'symptomatic ich', 'symptomatic hemorrhage', 'symptomatic haemorrhage',
                    'any intracranial hemorrhage', 'any intracranial haemorrhage'],
        'subspecialty': 'acute_ischemic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MORTALITY': {
        'aliases': ['all-cause mortality', 'all-cause death', '90-day mortality',
                    '90 day mortality', 'mortality at 90 days', 'overall survival',
                    'mortality', 'death'],
        'subspecialty': 'acute_ischemic',
        'measure_types': ['RR', 'HR', 'OR']
    },

    # --- Hemorrhagic stroke (intracerebral haemorrhage) ---
    'HEMATOMA_EXPANSION': {
        'aliases': ['hematoma expansion', 'haematoma expansion', 'hematoma growth',
                    'haematoma growth', 'hemorrhage expansion', 'haemorrhage expansion',
                    'ich growth', 'significant hematoma expansion', 'significant haematoma expansion'],
        'subspecialty': 'hemorrhagic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'POOR_OUTCOME': {
        'aliases': ['poor outcome', 'poor functional outcome', 'unfavourable outcome',
                    'unfavorable outcome', 'modified rankin scale 3-6', 'mrs 3-6',
                    'mrs 3 to 6', 'death or disability', 'death or dependency',
                    'mrs 4-6', 'mrs 5-6'],
        'subspecialty': 'hemorrhagic',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Secondary prevention ---
    'RECURRENT_STROKE': {
        'aliases': ['recurrent stroke', 'stroke recurrence', 'recurrent ischemic stroke',
                    'recurrent ischaemic stroke', 'new stroke', 'subsequent stroke',
                    'stroke or transient ischemic attack', 'stroke or tia',
                    'ischemic stroke recurrence', 'recurrent cerebrovascular event'],
        'subspecialty': 'secondary_prevention',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'MACE': {
        'aliases': ['major adverse cardiovascular events', 'composite vascular events',
                    'major vascular events', 'major adverse cardiovascular event',
                    'mace', 'composite of vascular death', 'vascular events composite',
                    'composite cardiovascular outcome'],
        'subspecialty': 'secondary_prevention',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'MAJOR_BLEEDING': {
        'aliases': ['major bleeding', 'major haemorrhage', 'major hemorrhage',
                    'major bleeding event', 'clinically relevant bleeding',
                    'major or clinically relevant bleeding', 'fatal bleeding'],
        'subspecialty': 'secondary_prevention',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- Recovery / rehabilitation ---
    'MOTOR_FUNCTION': {
        'aliases': ['fugl-meyer assessment', 'fugl meyer assessment', 'fugl-meyer',
                    'fugl meyer', 'fma', 'fma-ue', 'motor function', 'upper extremity motor',
                    'motor recovery', 'fugl-meyer motor score'],
        'subspecialty': 'recovery',
        'measure_types': ['MD', 'SMD']
    },
    'BARTHEL_INDEX': {
        'aliases': ['barthel index', 'barthel index score', 'modified barthel index',
                    'activities of daily living', 'adl score'],
        'subspecialty': 'recovery',
        'measure_types': ['MD', 'SMD']
    },
    'NIHSS': {
        'aliases': ['nihss score', 'nihss', 'nih stroke scale',
                    'national institutes of health stroke scale', 'change in nihss',
                    'nihss at 90 days'],
        'subspecialty': 'recovery',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# ACUTE ISCHEMIC STROKE PATTERNS
# ============================================================

ACUTE_ISCHEMIC_PATTERNS = {
    'detection_keywords': [
        r'acute\s+ischa?emic\s+stroke', r'ischa?emic\s+stroke',
        r'large\s+vessel\s+occlusion|\blvo\b',
        r'thrombectomy|endovascular\s+(?:therapy|treatment|thrombectomy)|\bevt\b',
        r'thrombolysis|thrombolytic',
        r'alteplase|tenecteplase|\btpa\b|\btnk\b',
        r'\btici\b|reperfusion|recanali[sz]ation',
        r'\bnihss\b|nih\s+stroke\s+scale',
        r'modified\s+rankin|\bmrs\b',
        r'time\s+to\s+(?:reperfusion|recanali[sz]ation|treatment)',
    ],
    'endpoint_patterns': [
        # ordinal mRS shift BEFORE the 0-2 dichotomy (the shift phrase contains
        # "modified rankin scale" too, and the longest/nearest match must be the
        # shift estimand, not functional independence -- they must never pool).
        (r'ordinal\s+(?:mrs\s+)?shift|shift\s+(?:analysis|in\s+the\s+modified\s+rankin)|'
         r'(?:modified\s+rankin\s+scale|rankin)\s+shift|ordinal\s+analysis\s+of\s+the\s+'
         r'modified\s+rankin|distribution\s+of\s+modified\s+rankin', 'MRS_SHIFT'),
        (r'functional\s+independence|good\s+functional\s+outcome|good\s+outcome|'
         r'fa?vou?rable\s+outcome|excellent\s+outcome|'
         r'(?:modified\s+rankin\s+scale|mrs)\s*(?:score\s*)?(?:of\s*)?0\s*(?:-|to|–)\s*[12]', 'FUNCTIONAL_INDEPENDENCE'),
        (r'successful\s+recanali[sz]ation|successful\s+reperfusion|recanali[sz]ation|'
         r'(?<!no\s)reperfusion|m?tici\s*2b(?:\s*(?:-|/|to|–)\s*3)?|substantial\s+reperfusion',
         'RECANALIZATION'),
        (r'symptomatic\s+intra(?:cranial|cerebral)\s+ha?emorrhage|symptomatic\s+ich|'
         r'\bsich\b|symptomatic\s+ha?emorrhage|any\s+intracranial\s+ha?emorrhage',
         'SYMPTOMATIC_ICH'),
        (r'early\s+neurolog(?:ical|ic)\s+(?:improvement|recovery)|change\s+in\s+nihss|'
         r'reduction\s+in\s+nihss|\bnihss\b|nih\s+stroke\s+scale', 'EARLY_NEURO_IMPROVEMENT'),
        # Generic mortality, but NOT when qualified as a haemorrhage-specific harm.
        (r'(?:all[- ]cause\s+|90[- ]day\s+)?(?:mortality|death)\b|overall\s+survival', 'MORTALITY'),
    ],
    'context_patterns': [
        r'within\s+\d+\s+hours?\s+of\s+(?:symptom\s+)?onset', r'last\s+known\s+well',
        r'90\s+days?', r'aspects', r'collateral',
    ]
}


# ============================================================
# HEMORRHAGIC STROKE PATTERNS (intracerebral haemorrhage)
# ============================================================

HEMORRHAGIC_PATTERNS = {
    'detection_keywords': [
        r'intracerebral\s+ha?emorrhage|\bich\b', r'intraparenchymal\s+ha?emorrhage',
        r'ha?ematoma\s+(?:expansion|growth|volume)', r'spontaneous\s+intracerebral',
        r'ha?emorrhagic\s+stroke', r'subarachnoid\s+ha?emorrhage|\bsah\b',
        r'tranexamic\s+acid', r'andexanet', r'nimodipine',
    ],
    'endpoint_patterns': [
        (r'ha?ematoma\s+(?:expansion|growth)|ha?emorrhage\s+expansion|ich\s+growth|'
         r'significant\s+ha?ematoma\s+expansion', 'HEMATOMA_EXPANSION'),
        (r'poor\s+(?:functional\s+)?outcome|unfa?vou?rable\s+outcome|'
         r'death\s+or\s+(?:disability|dependency)|'
         r'(?:modified\s+rankin\s+scale|mrs)\s*(?:score\s*)?(?:of\s*)?[345]\s*(?:-|to|–)\s*6',
         'POOR_OUTCOME'),
        (r'symptomatic\s+intra(?:cranial|cerebral)\s+ha?emorrhage|\bsich\b', 'SYMPTOMATIC_ICH'),
        (r'(?:all[- ]cause\s+|90[- ]day\s+|30[- ]day\s+)?(?:mortality|death)\b|overall\s+survival',
         'MORTALITY'),
    ],
    'context_patterns': [
        r'baseline\s+ha?ematoma\s+volume', r'spot\s+sign', r'ich\s+score',
    ]
}


# ============================================================
# SECONDARY PREVENTION PATTERNS
# ============================================================

SECONDARY_PREVENTION_PATTERNS = {
    'detection_keywords': [
        r'secondary\s+(?:stroke\s+)?prevention', r'recurrent\s+stroke|stroke\s+recurrence',
        r'transient\s+ischa?emic\s+attack|\btia\b',
        r'(?:dual\s+)?antiplatelet|\bdapt\b', r'aspirin\s+(?:and|plus|-)\s*clopidogrel',
        r'clopidogrel|ticagrelor', r'after\s+(?:ischa?emic\s+)?stroke\s+or\s+tia',
        r'minor\s+stroke', r'\bcryptogenic\s+stroke\b', r'\bpfo\b|patent\s+foramen\s+ovale',
    ],
    'endpoint_patterns': [
        (r'recurrent\s+(?:ischa?emic\s+)?stroke|stroke\s+recurrence|new\s+stroke|'
         r'subsequent\s+stroke|stroke\s+or\s+(?:transient\s+ischa?emic\s+attack|tia)|'
         r'recurrent\s+cerebrovascular\s+event', 'RECURRENT_STROKE'),
        (r'major\s+adverse\s+cardiovascular\s+events?|composite\s+(?:of\s+)?vascular|'
         r'major\s+vascular\s+events?|\bmace\b|composite\s+cardiovascular\s+outcome',
         'MACE'),
        (r'major\s+(?:or\s+clinically\s+relevant\s+)?bleeding|major\s+ha?emorrhage|'
         r'clinically\s+relevant\s+bleeding|fatal\s+bleeding', 'MAJOR_BLEEDING'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)\b|overall\s+survival', 'MORTALITY'),
    ],
    'context_patterns': [
        r'90\s+days?', r'1\s+year', r'follow[- ]up', r'time\s+to\s+(?:first\s+)?event',
    ]
}


# ============================================================
# RECOVERY / REHABILITATION PATTERNS
# ============================================================

RECOVERY_PATTERNS = {
    'detection_keywords': [
        r'stroke\s+rehabilitation|neurorehabilitation', r'fugl[- ]meyer',
        r'motor\s+(?:recovery|function|impairment)', r'barthel\s+index',
        r'upper\s+(?:limb|extremity)\s+(?:function|recovery|motor)',
        r'constraint[- ]induced\s+movement', r'robot[- ]assisted\s+(?:therapy|training)',
        r'gait\s+training', r'activities\s+of\s+daily\s+living',
    ],
    'endpoint_patterns': [
        (r'fugl[- ]meyer(?:\s+(?:assessment|motor|score))?|\bfma(?:-ue)?\b|'
         r'motor\s+function|motor\s+recovery|upper\s+extremity\s+motor', 'MOTOR_FUNCTION'),
        (r'(?:modified\s+)?barthel\s+index(?:\s+score)?|activities\s+of\s+daily\s+living|'
         r'\badl\s+score\b', 'BARTHEL_INDEX'),
        (r'\bnihss\b|nih\s+stroke\s+scale|change\s+in\s+nihss', 'NIHSS'),
    ],
    'context_patterns': [
        r'at\s+(?:3|6)\s+months', r'baseline\s+to', r'rehabilitation\s+program',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_stroke_subspecialty(text: str) -> Tuple[str, float]:
    """Detect stroke trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: acute_ischemic, hemorrhagic, secondary_prevention, recovery."""
    text_lower = text.lower()
    scores = {'acute_ischemic': 0, 'hemorrhagic': 0,
              'secondary_prevention': 0, 'recovery': 0}
    for kw in ACUTE_ISCHEMIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['acute_ischemic'] += 1
    for kw in HEMORRHAGIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['hemorrhagic'] += 1
    for kw in SECONDARY_PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['secondary_prevention'] += 1
    for kw in RECOVERY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['recovery'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('acute_ischemic', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_stroke_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'acute_ischemic': ACUTE_ISCHEMIC_PATTERNS['endpoint_patterns'],
        'hemorrhagic': HEMORRHAGIC_PATTERNS['endpoint_patterns'],
        'secondary_prevention': SECONDARY_PREVENTION_PATTERNS['endpoint_patterns'],
        'recovery': RECOVERY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_stroke_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical stroke endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in STROKE_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
