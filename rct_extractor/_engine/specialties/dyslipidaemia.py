"""
Dyslipidaemia / Lipid-Lowering Subspecialty Patterns and Endpoints

Built on the same African-student meta-analysis workflow as the hypertension,
diabetes and malaria profiles. Lipid-lowering RCTs report a distinct endpoint
vocabulary (LDL-C / non-HDL / ApoB reduction, LDL-goal attainment, cardiovascular
events, and statin-class safety signals such as new-onset diabetes and myopathy)
that the generic effect-size engine does not recognise on its own.

Subspecialties:
- lipid_lowering (continuous lipid change): LDL cholesterol, non-HDL cholesterol,
  HDL cholesterol, triglycerides, total cholesterol, apolipoprotein B,
  lipoprotein(a). Drug classes: statins (atorvastatin, rosuvastatin, simvastatin,
  pravastatin, lovastatin, pitavastatin, fluvastatin), cholesterol-absorption
  inhibitors (ezetimibe), PCSK9 inhibitors (evolocumab, alirocumab) and siRNA
  (inclisiran), bempedoic acid, fibrates (fenofibrate, gemfibrozil), bile-acid
  sequestrants (colesevelam, cholestyramine), niacin, omega-3 / icosapent ethyl,
  CETP inhibitors (anacetrapib, obicetrapib).
- ldl_target (binary goal attainment): proportion achieving an LDL-C goal /
  target (e.g. <70 mg/dL, <1.8 mmol/L) or a stated percentage LDL reduction.
- cv_events / mortality: major adverse cardiovascular events (MACE), myocardial
  infarction, stroke, cardiovascular death, all-cause mortality, coronary
  revascularisation.
- safety: new-onset (incident) diabetes, myopathy / myalgia / rhabdomyolysis,
  transaminase (ALT/AST) elevation, treatment discontinuation.

Effect measures follow what these trials report: continuous (LDL/HDL/TG/total
cholesterol/non-HDL/ApoB/Lp(a) change) -> MD/SMD on the natural scale; binary
(LDL-goal attainment, new-onset diabetes, myopathy, ALT elevation,
discontinuation) -> RR/OR/RD; time-to-event (MACE, MI, stroke, CV death,
revascularisation, mortality) -> HR.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# DYSLIPIDAEMIA ENDPOINTS
# ============================================================

DYSLIPIDAEMIA_ENDPOINTS = {
    # --- lipid_lowering (continuous) ---
    'LDL_REDUCTION': {
        'aliases': ['ldl cholesterol reduction', 'reduction in ldl cholesterol',
                    'ldl-c reduction', 'reduction in ldl-c', 'change in ldl cholesterol',
                    'ldl cholesterol change', 'percent change in ldl cholesterol',
                    'percentage change in ldl-c', 'low-density lipoprotein cholesterol',
                    'low density lipoprotein cholesterol', 'ldl cholesterol', 'ldl-c', 'ldl'],
        'subspecialty': 'lipid_lowering',
        'measure_types': ['MD', 'SMD']
    },
    'NON_HDL_REDUCTION': {
        'aliases': ['non-hdl cholesterol reduction', 'reduction in non-hdl cholesterol',
                    'change in non-hdl cholesterol', 'non-hdl cholesterol', 'non-hdl-c',
                    'non hdl cholesterol'],
        'subspecialty': 'lipid_lowering',
        'measure_types': ['MD', 'SMD']
    },
    'HDL_CHANGE': {
        'aliases': ['hdl cholesterol change', 'change in hdl cholesterol',
                    'increase in hdl cholesterol', 'high-density lipoprotein cholesterol',
                    'high density lipoprotein cholesterol', 'hdl cholesterol', 'hdl-c', 'hdl'],
        'subspecialty': 'lipid_lowering',
        'measure_types': ['MD', 'SMD']
    },
    'TG_REDUCTION': {
        'aliases': ['triglyceride reduction', 'reduction in triglycerides',
                    'change in triglycerides', 'triglyceride change', 'triglycerides',
                    'triglyceride', 'fasting triglycerides'],
        'subspecialty': 'lipid_lowering',
        'measure_types': ['MD', 'SMD']
    },
    'TOTAL_CHOL_REDUCTION': {
        'aliases': ['total cholesterol reduction', 'reduction in total cholesterol',
                    'change in total cholesterol', 'total cholesterol'],
        'subspecialty': 'lipid_lowering',
        'measure_types': ['MD', 'SMD']
    },
    'APOB_REDUCTION': {
        'aliases': ['apolipoprotein b reduction', 'reduction in apolipoprotein b',
                    'change in apolipoprotein b', 'apolipoprotein b', 'apob', 'apo b'],
        'subspecialty': 'lipid_lowering',
        'measure_types': ['MD', 'SMD']
    },
    'LPA_REDUCTION': {
        'aliases': ['lipoprotein(a) reduction', 'reduction in lipoprotein(a)',
                    'change in lipoprotein(a)', 'lipoprotein(a)', 'lipoprotein a', 'lp(a)'],
        'subspecialty': 'lipid_lowering',
        'measure_types': ['MD', 'SMD']
    },

    # --- ldl_target (binary goal attainment) ---
    'LDL_GOAL_ATTAINMENT': {
        'aliases': ['ldl goal attainment', 'ldl-c goal attainment', 'ldl target attainment',
                    'achieved ldl goal', 'achieved ldl-c goal', 'ldl goal achieved',
                    'ldl target achieved', 'attained ldl target', 'lipid goal attainment',
                    'ldl-c target', 'reached ldl target', 'ldl cholesterol goal'],
        'subspecialty': 'ldl_target',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- cardiovascular events / mortality ---
    'MACE': {
        'aliases': ['major adverse cardiovascular events', 'major adverse cardiac events',
                    'mace', 'cardiovascular composite', 'composite cardiovascular outcome',
                    'composite cardiovascular endpoint', 'primary cardiovascular composite',
                    'major cardiovascular events', 'cardiovascular events'],
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
    'STROKE': {
        'aliases': ['stroke', 'fatal stroke', 'nonfatal stroke', 'non-fatal stroke',
                    'ischemic stroke', 'ischaemic stroke', 'cerebrovascular accident',
                    'first stroke'],
        'subspecialty': 'cv_events',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'CV_MORTALITY': {
        'aliases': ['cardiovascular death', 'cardiovascular mortality', 'cv death',
                    'death from cardiovascular causes', 'fatal cardiovascular event',
                    'coronary death'],
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
    'REVASCULARIZATION': {
        'aliases': ['coronary revascularization', 'coronary revascularisation',
                    'revascularization', 'revascularisation', 'percutaneous coronary intervention',
                    'coronary artery bypass', 'unstable angina hospitalization'],
        'subspecialty': 'cv_events',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- safety ---
    'NEW_ONSET_DIABETES': {
        'aliases': ['new-onset diabetes', 'new onset diabetes', 'incident diabetes',
                    'new-onset type 2 diabetes', 'diabetes mellitus diagnosis',
                    'new cases of diabetes', 'incident type 2 diabetes'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'MYOPATHY': {
        'aliases': ['myopathy', 'myalgia', 'muscle symptoms', 'muscle-related adverse events',
                    'muscle related adverse events', 'rhabdomyolysis', 'statin-associated muscle',
                    'creatine kinase elevation'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ALT_ELEVATION': {
        'aliases': ['alanine aminotransferase elevation', 'transaminase elevation',
                    'liver enzyme elevation', 'alt elevation', 'aminotransferase elevation',
                    'hepatic transaminase', 'elevated transaminases'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'DISCONTINUATION': {
        'aliases': ['treatment discontinuation', 'drug discontinuation', 'discontinuation',
                    'discontinuation due to adverse events', 'study drug discontinuation',
                    'permanent discontinuation'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# LIPID-LOWERING PATTERNS (continuous lipid change)
# ============================================================

LIPID_LOWERING_PATTERNS = {
    'detection_keywords': [
        r'ldl[- ]?c\b|ldl\s+cholesterol|low[- ]density\s+lipoprotein',
        r'hdl[- ]?c\b|hdl\s+cholesterol|high[- ]density\s+lipoprotein',
        r'non[- ]hdl', r'triglycerid', r'total\s+cholesterol',
        r'apolipoprotein\s+b|\bapob\b', r'lipoprotein\s*\(a\)|\blp\(a\)',
        r'\bstatin\b|atorvastatin|rosuvastatin|simvastatin|pravastatin|lovastatin|pitavastatin|fluvastatin',
        r'ezetimibe', r'pcsk9|evolocumab|alirocumab|inclisiran',
        r'bempedoic\s+acid', r'fenofibrate|gemfibrozil|fibrate',
        r'colesevelam|cholestyramine', r'icosapent\s+ethyl|omega[- ]3',
        r'hypercholesterol(?:emia|aemia)|hyperlipid(?:emia|aemia)|dyslipid(?:emia|aemia)',
        r'lipid[- ]lowering|cholesterol[- ]lowering|lipid\s+profile',
    ],
    'endpoint_patterns': [
        (r'non[- ]hdl(?:\s+cholesterol)?(?:\s+reduction|\s+change)?', 'NON_HDL_REDUCTION'),
        (r'(?:reduction\s+in\s+|change\s+in\s+|percent(?:age)?\s+change\s+in\s+)?'
         r'(?:ldl[- ]?c\b|ldl\s+cholesterol|low[- ]density\s+lipoprotein(?:\s+cholesterol)?)'
         r'(?:\s+reduction|\s+change)?', 'LDL_REDUCTION'),
        (r'(?:reduction\s+in\s+|change\s+in\s+|increase\s+in\s+)?'
         r'(?:hdl[- ]?c\b|hdl\s+cholesterol|high[- ]density\s+lipoprotein(?:\s+cholesterol)?)'
         r'(?:\s+change)?', 'HDL_CHANGE'),
        (r'(?:reduction\s+in\s+|change\s+in\s+|fasting\s+)?triglycerides?(?:\s+reduction|\s+change)?',
         'TG_REDUCTION'),
        (r'(?:reduction\s+in\s+|change\s+in\s+)?total\s+cholesterol(?:\s+reduction|\s+change)?',
         'TOTAL_CHOL_REDUCTION'),
        (r'apolipoprotein\s+b(?:\s+reduction|\s+change)?|\bapob\b', 'APOB_REDUCTION'),
        (r'lipoprotein\s*\(a\)(?:\s+reduction|\s+change)?|\blp\(a\)', 'LPA_REDUCTION'),
    ],
    'context_patterns': [
        r'mg/dl|mmol/l', r'baseline\s+to\s+(?:week|month)', r'percent\s+change',
        r'mean\s+difference|\bmd\b',
    ]
}


# ============================================================
# LDL-TARGET PATTERNS (binary goal attainment)
# ============================================================

LDL_TARGET_PATTERNS = {
    'detection_keywords': [
        r'ldl(?:[- ]c)?\s+(?:goal|target)', r'goal\s+attainment', r'target\s+attainment',
        r'achieved\s+(?:an?\s+)?ldl', r'ldl(?:[- ]c)?\s+(?:<|below|less\s+than)',
        r'lipid\s+goal', r'reached\s+(?:the\s+)?ldl',
    ],
    'endpoint_patterns': [
        (r'ldl(?:[- ]c)?\s+(?:goal|target)\s+attainment|(?:achieved|attained|reached)\s+'
         r'(?:an?\s+|the\s+)?ldl(?:[- ]c)?\s+(?:goal|target)|ldl(?:[- ]c)?\s+goal\s+achieved|'
         r'lipid\s+goal\s+attainment', 'LDL_GOAL_ATTAINMENT'),
    ],
    'context_patterns': [
        r'<\s*70\s*mg/dl|<\s*1\.8\s*mmol/l|<\s*55\s*mg/dl|<\s*1\.4\s*mmol/l',
        r'proportion\s+(?:of\s+patients\s+)?(?:achieving|reaching)',
    ]
}


# ============================================================
# CV-EVENTS PATTERNS (cardiovascular events / mortality)
# ============================================================

CV_EVENTS_PATTERNS = {
    'detection_keywords': [
        r'major\s+adverse\s+cardiovascular\s+events|\bmace\b',
        r'myocardial\s+infarction|heart\s+attack', r'\bstroke\b',
        r'cardiovascular\s+(?:death|mortality)', r'all[- ]cause\s+mortality',
        r'coronary\s+revascular[is]ation|revascular[is]ation',
        r'cardiovascular\s+(?:events|outcome)', r'coronary\s+(?:event|heart\s+disease)',
    ],
    'endpoint_patterns': [
        (r'major\s+adverse\s+cardiovascular\s+events|major\s+adverse\s+cardiac\s+events|'
         r'\bmace\b|cardiovascular\s+composite|composite\s+cardiovascular\s+(?:outcome|endpoint)|'
         r'(?:major\s+)?cardiovascular\s+events', 'MACE'),
        (r'(?:acute\s+|fatal\s+|nonfatal\s+|non[- ]fatal\s+)?myocardial\s+infarction|'
         r'heart\s+attack|coronary\s+(?:event|heart\s+disease\s+event)', 'MYOCARDIAL_INFARCTION'),
        (r'(?:fatal\s+|nonfatal\s+|non[- ]fatal\s+|ischa?emic\s+|first\s+)?stroke|'
         r'cerebrovascular\s+accident', 'STROKE'),
        (r'cardiovascular\s+(?:death|mortality)|cv\s+death|death\s+from\s+cardiovascular|'
         r'coronary\s+death', 'CV_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|total\s+mortality|death\s+from\s+any\s+cause|'
         r'overall\s+mortality', 'ALL_CAUSE_MORTALITY'),
        (r'coronary\s+revascular[is]ation|revascular[is]ation|percutaneous\s+coronary\s+intervention|'
         r'coronary\s+artery\s+bypass|unstable\s+angina\s+hospitali[sz]ation', 'REVASCULARIZATION'),
    ],
    'context_patterns': [
        r'hazard\s+ratio|\bhr\b', r'person[- ]years', r'median\s+follow[- ]up',
        r'secondary\s+prevention|primary\s+prevention',
    ]
}


# ============================================================
# SAFETY PATTERNS
# ============================================================

SAFETY_PATTERNS = {
    'detection_keywords': [
        r'new[- ]onset\s+diabetes|incident\s+diabetes|new\s+cases\s+of\s+diabetes',
        r'myopathy|myalgia|muscle\s+(?:symptoms|pain)|rhabdomyolysis|creatine\s+kinase',
        r'(?:alanine\s+)?aminotransferase|transaminase|liver\s+enzyme|\balt\b',
        r'(?:treatment|drug|study\s+drug)\s+discontinuation', r'adverse\s+events',
    ],
    'endpoint_patterns': [
        (r'new[- ]onset\s+(?:type\s+2\s+)?diabetes|incident\s+(?:type\s+2\s+)?diabetes|'
         r'new\s+cases\s+of\s+diabetes|diabetes\s+mellitus\s+diagnosis', 'NEW_ONSET_DIABETES'),
        (r'myopathy|myalgia|muscle[- ](?:related\s+)?(?:symptoms|adverse\s+events)|'
         r'rhabdomyolysis|statin[- ]associated\s+muscle|creatine\s+kinase\s+elevation', 'MYOPATHY'),
        (r'(?:alanine\s+)?aminotransferase\s+elevation|transaminase\s+elevation|'
         r'liver\s+enzyme\s+elevation|alt\s+elevation|elevated\s+transaminases|'
         r'hepatic\s+transaminase', 'ALT_ELEVATION'),
        (r'(?:treatment|drug|study\s+drug|permanent)\s+discontinuation|'
         r'discontinuation\s+due\s+to\s+adverse\s+events|\bdiscontinuation\b', 'DISCONTINUATION'),
    ],
    'context_patterns': [
        r'safety', r'tolerability', r'adverse\s+event', r'per\s+1000\s+person[- ]years',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_dyslipidaemia_subspecialty(text: str) -> Tuple[str, float]:
    """Detect dyslipidaemia trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: lipid_lowering, ldl_target, cv_events, safety,
    general_dyslipidaemia."""
    text_lower = text.lower()
    scores = {'lipid_lowering': 0, 'ldl_target': 0, 'cv_events': 0, 'safety': 0}
    for kw in LIPID_LOWERING_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['lipid_lowering'] += 1
    for kw in LDL_TARGET_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['ldl_target'] += 1
    for kw in CV_EVENTS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['cv_events'] += 1
    for kw in SAFETY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['safety'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_dyslipidaemia', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_dyslipidaemia_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'lipid_lowering': LIPID_LOWERING_PATTERNS['endpoint_patterns'],
        'ldl_target': LDL_TARGET_PATTERNS['endpoint_patterns'],
        'cv_events': CV_EVENTS_PATTERNS['endpoint_patterns'],
        'safety': SAFETY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_dyslipidaemia_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical dyslipidaemia endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in DYSLIPIDAEMIA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
