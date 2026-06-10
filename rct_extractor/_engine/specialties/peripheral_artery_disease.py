"""
Peripheral Artery Disease (PAD) Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow as the hypertension / dyslipidaemia /
VTE profiles. PAD RCTs (medical therapy and lower-limb revascularisation for
intermittent claudication and chronic limb-threatening ischaemia) report a
distinct endpoint vocabulary (major adverse limb events, amputation, target-lesion
revascularisation, primary patency, walking distance, ankle-brachial index) that
the generic effect-size engine does not recognise.

Subspecialties:
- limb_outcomes: major adverse limb events (MALE), major amputation, amputation-
  free survival, acute limb ischaemia, limb salvage.
- revascularisation: primary patency, target-lesion / target-vessel
  revascularisation, restenosis (endovascular vs surgical, drug-coated devices).
- medical_therapy: cardiovascular events (MACE, MI, stroke, CV/all-cause death)
  and major bleeding under antiplatelet / anticoagulant / statin / cilostazol.
- functional (continuous): maximal (absolute) walking distance, pain-free /
  initial claudication distance, ankle-brachial index, treadmill walking time.

Effect measures: limb / revascularisation / CV endpoints are events -> RR/OR/HR;
functional endpoints (walking distance, ABI, treadmill time) are continuous ->
MD/SMD on the natural scale.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# PAD ENDPOINTS
# ============================================================

PAD_ENDPOINTS = {
    # --- limb_outcomes ---
    'MALE': {
        'aliases': ['major adverse limb events', 'major adverse limb event', 'male',
                    'major adverse limb', 'composite of major adverse limb events',
                    'major adverse limb or amputation'],
        'subspecialty': 'limb_outcomes',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'AMPUTATION': {
        'aliases': ['major amputation', 'amputation', 'limb amputation', 'lower-limb amputation',
                    'major lower extremity amputation', 'above-ankle amputation', 'limb loss'],
        'subspecialty': 'limb_outcomes',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'AMPUTATION_FREE_SURVIVAL': {
        'aliases': ['amputation-free survival', 'amputation free survival', 'afs',
                    'amputation-free survival rate'],
        'subspecialty': 'limb_outcomes',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'ACUTE_LIMB_ISCHEMIA': {
        'aliases': ['acute limb ischemia', 'acute limb ischaemia', 'acute limb ischaemic event',
                    'acute lower limb ischemia'],
        'subspecialty': 'limb_outcomes',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'LIMB_SALVAGE': {
        'aliases': ['limb salvage', 'limb salvage rate', 'limb preservation'],
        'subspecialty': 'limb_outcomes',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- revascularisation ---
    'PRIMARY_PATENCY': {
        'aliases': ['primary patency', 'primary patency rate', 'patency', 'vessel patency',
                    'primary-assisted patency', 'secondary patency'],
        'subspecialty': 'revascularisation',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'TLR': {
        'aliases': ['target lesion revascularization', 'target-lesion revascularisation',
                    'target lesion revascularisation', 'tlr', 'target vessel revascularization',
                    'target-vessel revascularisation', 'tvr',
                    'clinically driven target lesion revascularization'],
        'subspecialty': 'revascularisation',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'RESTENOSIS': {
        'aliases': ['restenosis', 'binary restenosis', 'in-stent restenosis',
                    'late lumen loss'],
        'subspecialty': 'revascularisation',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- medical_therapy (CV + safety) ---
    'MACE': {
        'aliases': ['major adverse cardiovascular events', 'major adverse cardiac events',
                    'mace', 'cardiovascular composite', 'major cardiovascular events',
                    'cardiovascular events'],
        'subspecialty': 'medical_therapy',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'MYOCARDIAL_INFARCTION': {
        'aliases': ['myocardial infarction', 'nonfatal myocardial infarction',
                    'non-fatal myocardial infarction', 'acute myocardial infarction',
                    'heart attack'],
        'subspecialty': 'medical_therapy',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'STROKE': {
        'aliases': ['stroke', 'ischemic stroke', 'ischaemic stroke', 'nonfatal stroke',
                    'non-fatal stroke', 'cerebrovascular accident'],
        'subspecialty': 'medical_therapy',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'CV_MORTALITY': {
        'aliases': ['cardiovascular death', 'cardiovascular mortality', 'cv death',
                    'death from cardiovascular causes'],
        'subspecialty': 'medical_therapy',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'all cause mortality', 'total mortality',
                    'death from any cause', 'overall mortality', 'all-cause death',
                    'mortality'],
        'subspecialty': 'medical_therapy',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'MAJOR_BLEEDING': {
        'aliases': ['major bleeding', 'major haemorrhage', 'major hemorrhage',
                    'tims major bleeding', 'major bleeding event'],
        'subspecialty': 'medical_therapy',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- functional (continuous) ---
    'MAX_WALKING_DISTANCE': {
        'aliases': ['maximal walking distance', 'maximum walking distance',
                    'absolute claudication distance', 'total walking distance',
                    'peak walking distance', 'maximal walking time', 'peak walking time'],
        'subspecialty': 'functional',
        'measure_types': ['MD', 'SMD']
    },
    'PAIN_FREE_WALKING_DISTANCE': {
        'aliases': ['pain-free walking distance', 'pain free walking distance',
                    'initial claudication distance', 'claudication onset distance',
                    'pain-free walking time'],
        'subspecialty': 'functional',
        'measure_types': ['MD', 'SMD']
    },
    'ABI': {
        'aliases': ['ankle-brachial index', 'ankle brachial index', 'abi',
                    'ankle-brachial pressure index', 'abpi'],
        'subspecialty': 'functional',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# LIMB-OUTCOMES PATTERNS
# ============================================================

LIMB_OUTCOMES_PATTERNS = {
    'detection_keywords': [
        r'major\s+adverse\s+limb\s+events?|\bmale\b', r'amputation', r'limb\s+loss',
        r'amputation[- ]free\s+survival', r'acute\s+limb\s+isch[ae]mia',
        r'limb\s+salvage', r'chronic\s+limb[- ]threatening\s+isch[ae]mia|\bclti\b',
        r'critical\s+limb\s+isch[ae]mia|\bcli\b',
    ],
    'endpoint_patterns': [
        (r'amputation[- ]free\s+survival', 'AMPUTATION_FREE_SURVIVAL'),
        (r'major\s+adverse\s+limb\s+events?|major\s+adverse\s+limb', 'MALE'),
        (r'acute\s+limb\s+isch[ae]mia', 'ACUTE_LIMB_ISCHEMIA'),
        (r'limb\s+salvage(?:\s+rate)?|limb\s+preservation', 'LIMB_SALVAGE'),
        (r'(?:major\s+|lower[- ](?:limb|extremity)\s+|above[- ]ankle\s+)?amputation|limb\s+loss',
         'AMPUTATION'),
    ],
    'context_patterns': [
        r'rutherford|fontaine', r'hazard\s+ratio|\bhr\b', r'below[- ]the[- ]knee',
    ]
}


# ============================================================
# REVASCULARISATION PATTERNS
# ============================================================

REVASCULARISATION_PATTERNS = {
    'detection_keywords': [
        r'primary\s+patency|patency\s+rate', r'target[- ](?:lesion|vessel)\s+revascular[is]ation',
        r'\btlr\b|\btvr\b', r'restenosis', r'drug[- ]coated\s+balloon|drug[- ]eluting\s+stent',
        r'endovascular', r'angioplasty', r'femoropopliteal|infrainguinal|infrapopliteal',
        r'bypass\s+(?:surgery|graft)',
    ],
    'endpoint_patterns': [
        (r'(?:clinically[- ]driven\s+)?target[- ](?:lesion|vessel)\s+revascular[is]ation|'
         r'\btlr\b|\btvr\b', 'TLR'),
        (r'(?:primary[- ]assisted\s+|secondary\s+|vessel\s+)?primary\s+patency(?:\s+rate)?|'
         r'patency(?:\s+rate)?', 'PRIMARY_PATENCY'),
        (r'(?:binary\s+|in[- ]stent\s+)?restenosis|late\s+lumen\s+loss', 'RESTENOSIS'),
    ],
    'context_patterns': [
        r'duplex\s+ultrasound', r'peak\s+systolic\s+velocity', r'12[- ]month\s+patency',
    ]
}


# ============================================================
# MEDICAL-THERAPY PATTERNS (CV events + bleeding)
# ============================================================

MEDICAL_THERAPY_PATTERNS = {
    'detection_keywords': [
        r'major\s+adverse\s+cardiovascular\s+events|\bmace\b',
        r'myocardial\s+infarction', r'\bstroke\b', r'cardiovascular\s+(?:death|mortality)',
        r'all[- ]cause\s+mortality', r'major\s+bleeding', r'antiplatelet|antithrombotic',
        r'cilostazol|clopidogrel|ticagrelor|vorapaxar|rivaroxaban',
    ],
    'endpoint_patterns': [
        (r'major\s+adverse\s+cardiovascular\s+events|major\s+adverse\s+cardiac\s+events|'
         r'\bmace\b|cardiovascular\s+composite|(?:major\s+)?cardiovascular\s+events', 'MACE'),
        (r'(?:acute\s+|fatal\s+|nonfatal\s+|non[- ]fatal\s+)?myocardial\s+infarction|heart\s+attack',
         'MYOCARDIAL_INFARCTION'),
        (r'(?:fatal\s+|nonfatal\s+|non[- ]fatal\s+|ischa?emic\s+)?stroke|cerebrovascular\s+accident',
         'STROKE'),
        (r'cardiovascular\s+(?:death|mortality)|cv\s+death|death\s+from\s+cardiovascular',
         'CV_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|total\s+mortality|death\s+from\s+any\s+cause|'
         r'overall\s+mortality', 'ALL_CAUSE_MORTALITY'),
        (r'(?:timi\s+)?major\s+(?:bleeding|h[ae]morrhage|bleed)(?:\s+event)?', 'MAJOR_BLEEDING'),
    ],
    'context_patterns': [
        r'hazard\s+ratio|\bhr\b', r'secondary\s+prevention', r'person[- ]years',
    ]
}


# ============================================================
# FUNCTIONAL PATTERNS (continuous)
# ============================================================

FUNCTIONAL_PATTERNS = {
    'detection_keywords': [
        r'maxim(?:al|um)\s+walking\s+(?:distance|time)', r'pain[- ]free\s+walking\s+(?:distance|time)',
        r'(?:absolute|initial)\s+claudication\s+distance', r'claudication\s+onset\s+distance',
        r'ankle[- ]brachial\s+(?:index|pressure\s+index)', r'\babi\b|\babpi\b',
        r'treadmill\s+(?:walking|test)', r'peak\s+walking\s+(?:distance|time)',
        r'walking\s+(?:distance|impairment)', r'claudication',
    ],
    'endpoint_patterns': [
        (r'pain[- ]free\s+walking\s+(?:distance|time)|initial\s+claudication\s+distance|'
         r'claudication\s+onset\s+distance', 'PAIN_FREE_WALKING_DISTANCE'),
        (r'maxim(?:al|um)\s+walking\s+(?:distance|time)|absolute\s+claudication\s+distance|'
         r'total\s+walking\s+distance|peak\s+walking\s+(?:distance|time)', 'MAX_WALKING_DISTANCE'),
        (r'ankle[- ]brachial\s+(?:pressure\s+)?index|\babi\b|\babpi\b', 'ABI'),
    ],
    'context_patterns': [
        r'\bmeters?\b|\bmetres?\b', r'baseline\s+to\s+(?:week|month)', r'mean\s+difference',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_peripheral_artery_disease_subspecialty(text: str) -> Tuple[str, float]:
    """Detect PAD trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: limb_outcomes, revascularisation, medical_therapy, functional,
    general_pad."""
    text_lower = text.lower()
    scores = {'limb_outcomes': 0, 'revascularisation': 0, 'medical_therapy': 0,
              'functional': 0}
    for kw in LIMB_OUTCOMES_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['limb_outcomes'] += 1
    for kw in REVASCULARISATION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['revascularisation'] += 1
    for kw in MEDICAL_THERAPY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['medical_therapy'] += 1
    for kw in FUNCTIONAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['functional'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_pad', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_peripheral_artery_disease_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'limb_outcomes': LIMB_OUTCOMES_PATTERNS['endpoint_patterns'],
        'revascularisation': REVASCULARISATION_PATTERNS['endpoint_patterns'],
        'medical_therapy': MEDICAL_THERAPY_PATTERNS['endpoint_patterns'],
        'functional': FUNCTIONAL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_peripheral_artery_disease_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical PAD endpoint, preferring the LONGEST matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in PAD_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
