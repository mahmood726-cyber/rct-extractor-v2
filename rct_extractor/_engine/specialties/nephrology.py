"""
Nephrology (kidney) Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the malaria / HIV / hepatitis /
respiratory / stroke profiles. Nephrology RCTs report an endpoint vocabulary
anchored on kidney-function measures (eGFR slope, doubling of serum creatinine,
albuminuria/proteinuria, progression to ESKD/dialysis) that the generic
effect-size engine does not recognise on its own.

Subspecialties:
- Chronic kidney disease (CKD progression / cardiorenal protection):
    kidney failure / ESKD (HR/RR), composite kidney outcome (sustained 40%/50%
    eGFR decline, doubling of serum creatinine; HR/RR), annual eGFR slope (MD),
    albuminuria / UACR reduction (MD/GMR -- LOG-NORMAL), all-cause mortality
    (HR/RR).
- Dialysis (haemodialysis / peritoneal dialysis populations):
    dialysis mortality (HR/RR), dialysis adequacy (Kt/V; MD), hospitalisation
    (RR/HR), vascular access failure / patency (RR/HR).
- Acute kidney injury (AKI):
    AKI incidence (RR/OR), need for renal replacement therapy / dialysis
    initiation (RR/OR), recovery of kidney function (RR/OR), AKI mortality
    (HR/RR).
- Glomerular disease (glomerulonephritis / nephrotic syndrome):
    complete / partial remission of proteinuria (RR/OR), relapse (RR/HR),
    proteinuria / UPCR (MD/GMR -- LOG-NORMAL).

Effect measures follow what these trials report: binary (kidney failure,
remission, AKI, need for RRT, mortality) -> RR/OR/HR; time-to-event (ESKD,
mortality, relapse) -> HR; continuous (eGFR slope, Kt/V) -> MD. Urinary
albumin/protein (UACR, UPCR, 24h protein) are right-skewed and LOG-NORMAL --
pool on the log scale (GMR), never as a raw-scale MD.

Routing note (coordinated with diabetes / cardiology): a type-2-diabetes trial
whose PRIMARY estimand is a KIDNEY outcome (e.g. dapagliflozin/finerenone in
diabetic kidney disease with a composite kidney endpoint) routes here because it
carries kidney-specific anchors (CKD, eGFR, albuminuria, ESKD, nephropathy). A
PURE glycaemic diabetes trial (HbA1c, hypoglycaemia, weight loss with no kidney
primary outcome) stays with diabetes. We deliberately do NOT claim bare
'diabetes', 'SGLT2', 'gliflozin', or 'finerenone' as nephrology detection
keywords (those belong to diabetes / cardiology); nephrology anchors strictly on
kidney-specific terms (chronic kidney disease, CKD, eGFR, ESKD/ESRD, dialysis,
albuminuria, proteinuria, nephropathy, glomerulonephritis, KDIGO, UACR).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# NEPHROLOGY ENDPOINTS
# ============================================================

NEPHROLOGY_ENDPOINTS = {
    # --- Chronic kidney disease (CKD progression) ---
    'KIDNEY_FAILURE': {
        'aliases': ['end-stage kidney disease', 'end stage kidney disease',
                    'end-stage renal disease', 'end stage renal disease',
                    'kidney failure', 'eskd', 'esrd', 'progression to dialysis',
                    'initiation of dialysis', 'chronic dialysis', 'sustained eskd'],
        'subspecialty': 'ckd',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'COMPOSITE_KIDNEY': {
        'aliases': ['composite kidney outcome', 'composite renal outcome',
                    'composite kidney endpoint', 'composite renal endpoint',
                    'kidney composite outcome', 'sustained 40% decline in egfr',
                    'sustained 50% decline in egfr', '40% decline in egfr',
                    '50% decline in egfr', 'doubling of serum creatinine',
                    'doubling of creatinine'],
        'subspecialty': 'ckd',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'EGFR_SLOPE': {
        'aliases': ['annual egfr slope', 'egfr slope', 'rate of egfr decline',
                    'estimated gfr slope', 'chronic egfr slope', 'total egfr slope',
                    'annual rate of egfr decline', 'egfr decline rate',
                    'slope of egfr'],
        'subspecialty': 'ckd',
        'measure_types': ['MD', 'SMD']
    },
    'ALBUMINURIA': {
        'aliases': ['urinary albumin-to-creatinine ratio', 'urinary albumin to creatinine ratio',
                    'albumin-to-creatinine ratio', 'albumin to creatinine ratio',
                    'uacr', 'urine albumin-to-creatinine', 'albuminuria',
                    'urinary albumin excretion', 'reduction in albuminuria',
                    'albuminuria reduction', 'change in uacr'],
        'subspecialty': 'ckd',
        'measure_types': ['MD', 'SMD', 'GMR']
    },
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'all-cause death', 'overall survival',
                    'mortality', 'death'],
        'subspecialty': 'ckd',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- Dialysis ---
    'DIALYSIS_MORTALITY': {
        'aliases': ['dialysis mortality', 'mortality on dialysis',
                    'death on dialysis', 'all-cause mortality on dialysis',
                    'cardiovascular mortality on dialysis', 'mortality in dialysis patients'],
        'subspecialty': 'dialysis',
        'measure_types': ['HR', 'RR']
    },
    'DIALYSIS_ADEQUACY': {
        'aliases': ['dialysis adequacy', 'kt/v', 'single-pool kt/v', 'spkt/v',
                    'equilibrated kt/v', 'ektv', 'urea reduction ratio',
                    'dialysis dose'],
        'subspecialty': 'dialysis',
        'measure_types': ['MD', 'SMD']
    },
    'HOSPITALIZATION': {
        'aliases': ['hospitalization', 'hospitalisation', 'hospital admission',
                    'all-cause hospitalization', 'all-cause hospitalisation',
                    'rate of hospitalization', 'hospitalization rate'],
        'subspecialty': 'dialysis',
        'measure_types': ['RR', 'HR', 'IRR']
    },
    'VASCULAR_ACCESS': {
        'aliases': ['vascular access failure', 'access failure', 'access patency',
                    'arteriovenous fistula patency', 'av fistula patency',
                    'graft patency', 'primary patency', 'access thrombosis',
                    'fistula failure', 'loss of patency'],
        'subspecialty': 'dialysis',
        'measure_types': ['RR', 'HR', 'OR']
    },

    # --- Acute kidney injury ---
    'AKI_INCIDENCE': {
        'aliases': ['acute kidney injury', 'aki incidence', 'incident aki',
                    'incidence of acute kidney injury', 'development of aki',
                    'aki', 'postoperative acute kidney injury'],
        'subspecialty': 'aki',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'NEED_FOR_RRT': {
        'aliases': ['need for renal replacement therapy', 'renal replacement therapy',
                    'need for rrt', 'initiation of renal replacement therapy',
                    'dialysis initiation', 'need for dialysis', 'requirement for dialysis',
                    'rrt initiation', 'use of renal replacement therapy'],
        'subspecialty': 'aki',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'KIDNEY_RECOVERY': {
        'aliases': ['recovery of kidney function', 'kidney recovery',
                    'recovery of renal function', 'renal recovery',
                    'recovery from acute kidney injury', 'renal function recovery',
                    'complete renal recovery'],
        'subspecialty': 'aki',
        'measure_types': ['RR', 'OR']
    },
    'AKI_MORTALITY': {
        'aliases': ['aki mortality', 'mortality after acute kidney injury',
                    'death after acute kidney injury', 'aki-associated mortality',
                    'mortality associated with aki'],
        'subspecialty': 'aki',
        'measure_types': ['HR', 'RR']
    },

    # --- Glomerular disease ---
    'COMPLETE_REMISSION': {
        'aliases': ['complete remission', 'partial remission', 'proteinuria remission',
                    'complete remission of proteinuria', 'partial remission of proteinuria',
                    'complete or partial remission', 'remission of proteinuria',
                    'complete renal remission'],
        'subspecialty': 'glomerular',
        'measure_types': ['RR', 'OR']
    },
    'RELAPSE': {
        'aliases': ['relapse', 'disease relapse', 'proteinuric relapse',
                    'nephrotic relapse', 'relapse of nephrotic syndrome',
                    'time to relapse', 'relapse-free survival'],
        'subspecialty': 'glomerular',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'PROTEINURIA': {
        'aliases': ['urinary protein-to-creatinine ratio', 'urinary protein to creatinine ratio',
                    'protein-to-creatinine ratio', 'protein to creatinine ratio',
                    'upcr', '24-hour urine protein', '24 hour urine protein',
                    '24-h urine protein', '24h urine protein', 'proteinuria',
                    'urinary protein excretion', 'change in proteinuria'],
        'subspecialty': 'glomerular',
        'measure_types': ['MD', 'SMD', 'GMR']
    },
}


# ============================================================
# CKD PATTERNS (chronic kidney disease progression)
# ============================================================

CKD_PATTERNS = {
    'detection_keywords': [
        r'chronic\s+kidney\s+disease|\bckd\b',
        r'diabetic\s+kidney\s+disease|diabetic\s+nephropathy',
        r'\begfr\b|estimated\s+glomerular\s+filtration\s+rate',
        r'end[- ]stage\s+(?:kidney|renal)\s+disease|\beskd\b|\besrd\b',
        r'albuminuria|\buacr\b|urinary\s+albumin',
        r'nephropathy', r'\bkdigo\b',
        r'doubling\s+of\s+serum\s+creatinine|doubling\s+of\s+creatinine',
        r'sustained\s+(?:40|50)%\s+(?:decline|reduction)\s+in\s+egfr',
        r'progression\s+(?:of|to)\s+(?:chronic\s+)?kidney\s+disease',
    ],
    'endpoint_patterns': [
        # composite kidney outcome BEFORE bare kidney-failure / mortality so the
        # longest/nearest match is the composite estimand when present.
        (r'composite\s+(?:kidney|renal)\s+(?:outcome|endpoint)|'
         r'(?:kidney|renal)\s+composite\s+outcome|'
         r'sustained\s+(?:40|50)%\s+(?:decline|reduction)\s+in\s+egfr|'
         r'(?:40|50)%\s+(?:decline|reduction)\s+in\s+egfr|'
         r'doubling\s+of\s+(?:serum\s+)?creatinine', 'COMPOSITE_KIDNEY'),
        (r'end[- ]stage\s+(?:kidney|renal)\s+disease|\beskd\b|\besrd\b|'
         r'kidney\s+failure|progression\s+to\s+dialysis|initiation\s+of\s+dialysis',
         'KIDNEY_FAILURE'),
        (r'(?:annual\s+)?egfr\s+slope|rate\s+of\s+egfr\s+decline|'
         r'slope\s+of\s+egfr|egfr\s+decline\s+rate', 'EGFR_SLOPE'),
        (r'urinary\s+albumin[- ]to[- ]creatinine\s+ratio|albumin[- ]to[- ]creatinine\s+ratio|'
         r'\buacr\b|albuminuria|urinary\s+albumin\s+excretion', 'ALBUMINURIA'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)\b|overall\s+survival', 'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [
        r'ml/min/1\.73\s*m', r'per\s+1\.73\s*m', r'mg/g|mg/mmol',
        r'baseline\s+egfr', r'stage\s+[1-5]\s+ckd',
    ]
}


# ============================================================
# DIALYSIS PATTERNS
# ============================================================

DIALYSIS_PATTERNS = {
    'detection_keywords': [
        r'\bdialysis\b', r'h?emodialysis', r'peritoneal\s+dialysis',
        r'maintenance\s+dialysis', r'kt/v', r'dialysis\s+adequacy',
        r'arteriovenous\s+fistula|av\s+fistula', r'vascular\s+access',
        r'dialysis\s+patients?', r'incident\s+dialysis',
    ],
    'endpoint_patterns': [
        (r'dialysis\s+adequacy|\bkt/v\b|single[- ]pool\s+kt/v|equilibrated\s+kt/v|'
         r'urea\s+reduction\s+ratio', 'DIALYSIS_ADEQUACY'),
        (r'vascular\s+access\s+(?:failure|patency)|access\s+(?:failure|patency|thrombosis)|'
         r'(?:av\s+)?fistula\s+(?:patency|failure)|graft\s+patency|primary\s+patency',
         'VASCULAR_ACCESS'),
        (r'hospitali[sz]ation|hospital\s+admission', 'HOSPITALIZATION'),
        (r'(?:all[- ]cause\s+|cardiovascular\s+)?(?:mortality|death)\b(?:\s+(?:on|in)\s+dialysis)?|'
         r'mortality\s+in\s+dialysis', 'DIALYSIS_MORTALITY'),
    ],
    'context_patterns': [
        r'per\s+(?:patient[- ])?year', r'thrice[- ]weekly', r'session',
    ]
}


# ============================================================
# AKI PATTERNS (acute kidney injury)
# ============================================================

AKI_PATTERNS = {
    'detection_keywords': [
        r'acute\s+kidney\s+injury|\baki\b', r'acute\s+renal\s+failure',
        r'renal\s+replacement\s+therapy|\brrt\b',
        r'recovery\s+of\s+(?:kidney|renal)\s+function',
        r'contrast[- ]induced\s+(?:nephropathy|acute\s+kidney)',
        r'postoperative\s+acute\s+kidney', r'\bkdigo\s+stage\b',
        r'serum\s+creatinine\s+(?:increase|rise)',
    ],
    'endpoint_patterns': [
        (r'need\s+for\s+renal\s+replacement\s+therapy|renal\s+replacement\s+therapy|'
         r'need\s+for\s+(?:rrt|dialysis)|dialysis\s+initiation|initiation\s+of\s+rrt|'
         r'requirement\s+for\s+dialysis', 'NEED_FOR_RRT'),
        (r'recovery\s+of\s+(?:kidney|renal)\s+function|(?:kidney|renal)\s+recovery|'
         r'recovery\s+from\s+acute\s+kidney\s+injury', 'KIDNEY_RECOVERY'),
        (r'acute\s+kidney\s+injury|incidence\s+of\s+acute\s+kidney\s+injury|'
         r'incident\s+aki|development\s+of\s+aki|\baki\b', 'AKI_INCIDENCE'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)\b(?:\s+after\s+(?:acute\s+kidney|aki))?|'
         r'aki[- ]associated\s+mortality', 'AKI_MORTALITY'),
    ],
    'context_patterns': [
        r'within\s+\d+\s+(?:hours?|days?)', r'kdigo\s+stage\s+[123]', r'postoperative',
    ]
}


# ============================================================
# GLOMERULAR PATTERNS (glomerulonephritis / nephrotic syndrome)
# ============================================================

GLOMERULAR_PATTERNS = {
    'detection_keywords': [
        r'glomerulonephritis', r'iga\s+nephropathy', r'iga\s+nephritis',
        r'nephrotic\s+syndrome', r'membranous\s+nephropathy',
        r'lupus\s+nephritis', r'focal\s+segmental\s+glomeruloscler\w+|\bfsgs\b',
        r'minimal\s+change\s+disease', r'proteinuria|\bupcr\b',
        r'anca[- ]associated\s+vasculitis', r'24[- ]?h(?:our)?\s+urine\s+protein',
    ],
    'endpoint_patterns': [
        (r'complete\s+(?:and\s+partial\s+|or\s+partial\s+)?remission|partial\s+remission|'
         r'remission\s+of\s+proteinuria|proteinuria\s+remission|complete\s+renal\s+remission',
         'COMPLETE_REMISSION'),
        (r'urinary\s+protein[- ]to[- ]creatinine\s+ratio|protein[- ]to[- ]creatinine\s+ratio|'
         r'\bupcr\b|24[- ]?h(?:our)?\s+urine\s+protein|proteinuria|'
         r'urinary\s+protein\s+excretion', 'PROTEINURIA'),
        (r'relapse[- ]free\s+survival|disease\s+relapse|proteinuric\s+relapse|'
         r'nephrotic\s+relapse|time\s+to\s+relapse|\brelapse\b', 'RELAPSE'),
    ],
    'context_patterns': [
        r'g/g|g/day|mg/mmol', r'biopsy[- ]proven', r'baseline\s+proteinuria',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_nephrology_subspecialty(text: str) -> Tuple[str, float]:
    """Detect nephrology trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: ckd, dialysis, aki, glomerular."""
    text_lower = text.lower()
    scores = {'ckd': 0, 'dialysis': 0, 'aki': 0, 'glomerular': 0}
    for kw in CKD_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['ckd'] += 1
    for kw in DIALYSIS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['dialysis'] += 1
    for kw in AKI_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['aki'] += 1
    for kw in GLOMERULAR_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['glomerular'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('ckd', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_nephrology_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'ckd': CKD_PATTERNS['endpoint_patterns'],
        'dialysis': DIALYSIS_PATTERNS['endpoint_patterns'],
        'aki': AKI_PATTERNS['endpoint_patterns'],
        'glomerular': GLOMERULAR_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_nephrology_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical nephrology endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in NEPHROLOGY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
