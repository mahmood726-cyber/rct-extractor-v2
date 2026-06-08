"""
Hypertension / Cardiovascular-Disease Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV and
typhoid profiles. Hypertension is a rising NCD priority across Africa; its RCTs
report a distinct endpoint vocabulary (blood-pressure reduction, BP control,
cardiovascular events, adherence) that the generic effect-size engine does not
recognise on its own.

Subspecialties:
- BP-lowering (drug classes / treatment efficacy): blood-pressure control / target
  attainment, treatment (responder) response. Drug classes: ACE inhibitors
  (lisinopril, enalapril, ramipril, perindopril, captopril), ARBs (losartan,
  valsartan, candesartan, telmisartan, olmesartan, irbesartan), calcium-channel
  blockers (amlodipine, nifedipine, felodipine), thiazide/thiazide-like diuretics
  (hydrochlorothiazide, chlorthalidone, indapamide), beta-blockers (atenolol,
  metoprolol, bisoprolol, carvedilol), MRAs (spironolactone, eplerenone), ARNI
  (sacubitril/valsartan), single-pill combinations.
- Cardiovascular events / mortality: major adverse cardiovascular events (MACE),
  stroke, myocardial infarction, cardiovascular death, all-cause mortality,
  heart-failure hospitalisation.
- BP reduction (continuous): change in systolic / diastolic blood pressure, mean
  arterial pressure, 24-hour ambulatory blood pressure.
- Adherence: medication adherence / compliance (proportion of days covered,
  medication possession ratio), persistence / discontinuation.

Effect measures follow what these trials report: binary (BP control, response,
adherence, stroke, MI, CV death) -> RR/OR/RD; time-to-event (MACE, stroke, MI,
mortality) -> HR; continuous (SBP/DBP/MAP/ambulatory reduction) -> MD/SMD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# HYPERTENSION ENDPOINTS
# ============================================================

HYPERTENSION_ENDPOINTS = {
    # --- BP-lowering (drug-class treatment efficacy) ---
    'BP_CONTROL': {
        'aliases': ['blood pressure control', 'bp control', 'controlled blood pressure',
                    'controlled bp', 'blood pressure controlled', 'target blood pressure',
                    'blood pressure target', 'bp target', 'blood pressure goal', 'bp goal',
                    'target bp achieved', 'achieved target blood pressure', 'goal attainment',
                    'blood pressure normalization', 'blood pressure normalisation',
                    'normalisation of blood pressure', 'normalization of blood pressure'],
        'subspecialty': 'bp_lowering',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BP_RESPONSE': {
        'aliases': ['blood pressure response', 'antihypertensive response', 'treatment response',
                    'responder rate', 'response rate', 'proportion of responders',
                    'therapeutic response'],
        'subspecialty': 'bp_lowering',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- BP reduction (continuous) ---
    'SBP_REDUCTION': {
        'aliases': ['systolic blood pressure reduction', 'reduction in systolic blood pressure',
                    'systolic bp reduction', 'change in systolic blood pressure',
                    'systolic blood pressure change', 'fall in systolic blood pressure',
                    'office systolic blood pressure', 'seated systolic blood pressure',
                    'sitting systolic blood pressure', 'clinic systolic blood pressure',
                    'systolic blood pressure'],
        'subspecialty': 'bp_reduction',
        'measure_types': ['MD', 'SMD']
    },
    'DBP_REDUCTION': {
        'aliases': ['diastolic blood pressure reduction', 'reduction in diastolic blood pressure',
                    'diastolic bp reduction', 'change in diastolic blood pressure',
                    'diastolic blood pressure change', 'fall in diastolic blood pressure',
                    'office diastolic blood pressure', 'seated diastolic blood pressure',
                    'sitting diastolic blood pressure', 'clinic diastolic blood pressure',
                    'diastolic blood pressure'],
        'subspecialty': 'bp_reduction',
        'measure_types': ['MD', 'SMD']
    },
    'MAP_REDUCTION': {
        'aliases': ['mean arterial pressure reduction', 'reduction in mean arterial pressure',
                    'change in mean arterial pressure', 'mean arterial pressure'],
        'subspecialty': 'bp_reduction',
        'measure_types': ['MD', 'SMD']
    },
    'AMBULATORY_SBP': {
        'aliases': ['24-hour ambulatory systolic blood pressure', '24-h ambulatory systolic',
                    'ambulatory systolic blood pressure', '24-hour systolic blood pressure',
                    'daytime systolic blood pressure', 'nighttime systolic blood pressure',
                    'night-time systolic blood pressure', 'ambulatory blood pressure',
                    '24-hour blood pressure'],
        'subspecialty': 'bp_reduction',
        'measure_types': ['MD', 'SMD']
    },

    # --- Cardiovascular events / mortality ---
    'MACE': {
        'aliases': ['major adverse cardiovascular events', 'major adverse cardiac events',
                    'mace', 'cardiovascular composite', 'composite cardiovascular outcome',
                    'composite cardiovascular endpoint', 'primary cardiovascular composite',
                    'cardiovascular events', 'major cardiovascular events'],
        'subspecialty': 'cv_events',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'STROKE': {
        'aliases': ['stroke', 'fatal stroke', 'nonfatal stroke', 'non-fatal stroke',
                    'first stroke', 'incident stroke', 'cerebrovascular accident',
                    'ischemic stroke', 'ischaemic stroke', 'hemorrhagic stroke',
                    'haemorrhagic stroke'],
        'subspecialty': 'cv_events',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'MYOCARDIAL_INFARCTION': {
        'aliases': ['myocardial infarction', 'fatal myocardial infarction',
                    'nonfatal myocardial infarction', 'non-fatal myocardial infarction',
                    'acute myocardial infarction', 'heart attack', 'coronary event',
                    'coronary heart disease event'],
        'subspecialty': 'cv_events',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'CV_MORTALITY': {
        'aliases': ['cardiovascular death', 'cardiovascular mortality', 'cv death',
                    'death from cardiovascular causes', 'cardiovascular cause of death',
                    'fatal cardiovascular event'],
        'subspecialty': 'cv_events',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'all cause mortality', 'total mortality',
                    'death from any cause', 'overall mortality', 'all-cause death',
                    'mortality'],
        'subspecialty': 'cv_events',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'HF_HOSPITALIZATION': {
        'aliases': ['heart failure hospitalization', 'hospitalization for heart failure',
                    'heart failure hospitalisation', 'hospitalisation for heart failure',
                    'hf hospitalization', 'heart failure admission', 'incident heart failure',
                    'new-onset heart failure'],
        'subspecialty': 'cv_events',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- Adherence ---
    'MEDICATION_ADHERENCE': {
        'aliases': ['medication adherence', 'antihypertensive adherence', 'adherence',
                    'medication compliance', 'compliance', 'proportion of days covered',
                    'medication possession ratio', 'pill count', 'adherent',
                    'good adherence', 'optimal adherence'],
        'subspecialty': 'adherence',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PERSISTENCE': {
        'aliases': ['treatment persistence', 'medication persistence', 'persistence',
                    'treatment discontinuation', 'medication discontinuation',
                    'discontinuation', 'non-persistence', 'drug survival'],
        'subspecialty': 'adherence',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# BP-LOWERING PATTERNS (drug-class treatment efficacy)
# ============================================================

BP_LOWERING_PATTERNS = {
    'detection_keywords': [
        r'antihypertensive', r'blood[- ]pressure[- ]lowering', r'bp[- ]lowering',
        r'angiotensin[- ]converting[- ]enzyme\s+inhibitor|\bace\s+inhibitor',
        r'angiotensin[- ]receptor\s+blocker|\barb\b',
        r'calcium[- ]channel\s+blocker|\bccb\b', r'thiazide', r'beta[- ]blocker',
        r'amlodipine|nifedipine|felodipine|lisinopril|enalapril|ramipril|perindopril|captopril',
        r'losartan|valsartan|candesartan|telmisartan|olmesartan|irbesartan',
        r'hydrochlorothiazide|chlorthalidone|chlortalidone|indapamide|bendroflumethiazide',
        r'atenolol|metoprolol|bisoprolol|carvedilol|nebivolol',
        r'spironolactone|eplerenone|sacubitril', r'single[- ]pill\s+combination',
        r'blood\s+pressure\s+control|target\s+blood\s+pressure|blood\s+pressure\s+goal',
        r'monotherapy|dual\s+(?:therapy|combination)|fixed[- ]dose\s+combination',
    ],
    'endpoint_patterns': [
        (r'blood\s+pressure\s+control|controlled\s+blood\s+pressure|'
         r'blood\s+pressure\s+(?:was\s+|were\s+)?controlled|bp\s+control(?:led)?|'
         r'target\s+blood\s+pressure|blood\s+pressure\s+(?:target|goal)|'
         r'blood\s+pressure\s+normali[sz]ation|goal\s+attainment', 'BP_CONTROL'),
        (r'(?:blood\s+pressure|antihypertensive|treatment|therapeutic)\s+response|'
         r'responder\s+rate|proportion\s+of\s+responders', 'BP_RESPONSE'),
    ],
    'context_patterns': [
        r'<\s*140\s*\/\s*90|<\s*130\s*\/\s*80', r'per[- ]protocol|intention[- ]to[- ]treat',
        r'week\s+(?:8|12|24)\s+(?:outcome|endpoint)', r'mm\s?hg',
    ]
}


# ============================================================
# CV-EVENTS PATTERNS (cardiovascular events / mortality)
# ============================================================

CV_EVENTS_PATTERNS = {
    'detection_keywords': [
        r'major\s+adverse\s+cardiovascular\s+events|\bmace\b',
        r'cardiovascular\s+(?:events|death|mortality|outcome)',
        r'\bstroke\b', r'myocardial\s+infarction|heart\s+attack',
        r'all[- ]cause\s+mortality', r'heart\s+failure\s+hospitali[sz]ation',
        r'fatal\s+(?:or\s+)?non[- ]?fatal', r'cardiovascular\s+composite',
        r'coronary\s+(?:event|heart\s+disease)',
    ],
    'endpoint_patterns': [
        (r'major\s+adverse\s+cardiovascular\s+events|major\s+adverse\s+cardiac\s+events|'
         r'\bmace\b|cardiovascular\s+composite|composite\s+cardiovascular\s+(?:outcome|endpoint)|'
         r'(?:major\s+)?cardiovascular\s+events', 'MACE'),
        (r'(?:fatal\s+|nonfatal\s+|non[- ]fatal\s+|first\s+|incident\s+|ischa?emic\s+|'
         r'h[ae]morrhagic\s+|cerebrovascular\s+)?stroke|cerebrovascular\s+accident', 'STROKE'),
        (r'(?:acute\s+|fatal\s+|nonfatal\s+|non[- ]fatal\s+)?myocardial\s+infarction|'
         r'heart\s+attack|coronary\s+(?:event|heart\s+disease\s+event)', 'MYOCARDIAL_INFARCTION'),
        (r'cardiovascular\s+(?:death|mortality)|cv\s+death|death\s+from\s+cardiovascular',
         'CV_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|total\s+mortality|death\s+from\s+any\s+cause|'
         r'overall\s+mortality', 'ALL_CAUSE_MORTALITY'),
        (r'heart\s+failure\s+hospitali[sz]ation|hospitali[sz]ation\s+for\s+heart\s+failure|'
         r'heart\s+failure\s+admission|incident\s+heart\s+failure', 'HF_HOSPITALIZATION'),
    ],
    'context_patterns': [
        r'hazard\s+ratio|\bhr\b', r'person[- ]years', r'median\s+follow[- ]up',
        r'time[- ]to[- ]event|kaplan[- ]meier',
    ]
}


# ============================================================
# BP-REDUCTION PATTERNS (continuous)
# ============================================================

BP_REDUCTION_PATTERNS = {
    'detection_keywords': [
        r'systolic\s+blood\s+pressure', r'diastolic\s+blood\s+pressure',
        r'mean\s+arterial\s+pressure', r'ambulatory\s+blood\s+pressure',
        r'mm\s?hg', r'blood\s+pressure\s+reduction|reduction\s+in\s+blood\s+pressure',
        r'change\s+in\s+(?:systolic|diastolic)\s+blood\s+pressure',
        r'24[- ]?h(?:our)?\s+(?:systolic|blood\s+pressure)', r'office\s+blood\s+pressure',
    ],
    'endpoint_patterns': [
        (r'(?:24[- ]?h(?:our)?\s+|daytime\s+|night[- ]?time\s+)?ambulatory\s+'
         r'(?:systolic\s+)?blood\s+pressure|24[- ]?h(?:our)?\s+systolic\s+blood\s+pressure',
         'AMBULATORY_SBP'),
        (r'(?:reduction\s+in\s+|change\s+in\s+|fall\s+in\s+|office\s+|seated\s+|sitting\s+|'
         r'clinic\s+)?systolic\s+blood\s+pressure(?:\s+reduction|\s+change)?|'
         r'systolic\s+bp\s+reduction', 'SBP_REDUCTION'),
        (r'(?:reduction\s+in\s+|change\s+in\s+|fall\s+in\s+|office\s+|seated\s+|sitting\s+|'
         r'clinic\s+)?diastolic\s+blood\s+pressure(?:\s+reduction|\s+change)?|'
         r'diastolic\s+bp\s+reduction', 'DBP_REDUCTION'),
        (r'mean\s+arterial\s+pressure(?:\s+reduction)?', 'MAP_REDUCTION'),
    ],
    'context_patterns': [
        r'mean\s+difference|\bmd\b', r'\bsd\b|standard\s+deviation',
        r'baseline\s+to\s+(?:week|month)', r'mm\s?hg',
    ]
}


# ============================================================
# ADHERENCE PATTERNS
# ============================================================

ADHERENCE_PATTERNS = {
    'detection_keywords': [
        r'medication\s+adherence|antihypertensive\s+adherence', r'\badherence\b',
        r'medication\s+compliance|\bcompliance\b', r'proportion\s+of\s+days\s+covered|\bpdc\b',
        r'medication\s+possession\s+ratio|\bmpr\b', r'persistence',
        r'(?:treatment|medication)\s+discontinuation', r'pill\s+count',
    ],
    'endpoint_patterns': [
        (r'medication\s+adherence|antihypertensive\s+adherence|\badherence\b|'
         r'medication\s+compliance|\bcompliance\b|proportion\s+of\s+days\s+covered|'
         r'medication\s+possession\s+ratio|pill\s+count', 'MEDICATION_ADHERENCE'),
        (r'(?:treatment|medication)\s+persistence|\bpersistence\b|non[- ]persistence|'
         r'(?:treatment|medication)\s+discontinuation|\bdiscontinuation\b|drug\s+survival',
         'PERSISTENCE'),
    ],
    'context_patterns': [
        r'self[- ]reported', r'pharmacy\s+(?:refill|claims)', r'\bmems\b|electronic\s+monitoring',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_hypertension_subspecialty(text: str) -> Tuple[str, float]:
    """Detect hypertension trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: bp_lowering, cv_events, bp_reduction, adherence,
    general_hypertension."""
    text_lower = text.lower()
    scores = {'bp_lowering': 0, 'cv_events': 0, 'bp_reduction': 0, 'adherence': 0}
    for kw in BP_LOWERING_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['bp_lowering'] += 1
    for kw in CV_EVENTS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['cv_events'] += 1
    for kw in BP_REDUCTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['bp_reduction'] += 1
    for kw in ADHERENCE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['adherence'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_hypertension', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_hypertension_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'bp_lowering': BP_LOWERING_PATTERNS['endpoint_patterns'],
        'cv_events': CV_EVENTS_PATTERNS['endpoint_patterns'],
        'bp_reduction': BP_REDUCTION_PATTERNS['endpoint_patterns'],
        'adherence': ADHERENCE_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_hypertension_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical hypertension endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in HYPERTENSION_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
