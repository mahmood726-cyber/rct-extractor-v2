"""
Kidney Transplantation Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow as the other cardio-metabolic & renal
profiles. Kidney-transplant RCTs (immunosuppression regimens, induction therapy,
rejection prophylaxis) report a distinct endpoint vocabulary (biopsy-proven acute
rejection, graft loss / survival, delayed graft function, eGFR, CMV / BK
infection) that is NOT covered by the general nephrology specialty
(ckd / dialysis / aki / glomerular).

Subspecialties:
- rejection: (biopsy-proven) acute rejection, antibody-mediated rejection, acute
  cellular rejection.
- graft: graft loss / failure / survival, death-censored graft loss, delayed
  graft function (DGF).
- function (continuous): estimated GFR, measured GFR, serum creatinine.
- complications: patient survival / all-cause mortality, CMV infection, BK
  viraemia / nephropathy, post-transplant lymphoproliferative disorder (PTLD),
  new-onset diabetes after transplant (NODAT).

Drug / regimen classes (arm labels): calcineurin inhibitors (tacrolimus,
ciclosporin), antiproliferatives (mycophenolate mofetil / MPA, azathioprine),
mTOR inhibitors (sirolimus, everolimus), costimulation blockade (belatacept),
induction (basiliximab, anti-thymocyte globulin / ATG, alemtuzumab),
corticosteroids, placebo.

Effect measures: rejection / graft / infection / survival -> RR/OR/HR; eGFR /
creatinine -> MD/SMD (continuous, natural scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# KIDNEY-TRANSPLANT ENDPOINTS
# ============================================================

KIDNEY_TRANSPLANT_ENDPOINTS = {
    # --- rejection ---
    'ACUTE_REJECTION': {
        'aliases': ['biopsy-proven acute rejection', 'biopsy proven acute rejection',
                    'acute rejection', 'bpar', 'acute cellular rejection', 'treated acute rejection',
                    'clinical acute rejection'],
        'subspecialty': 'rejection',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ANTIBODY_MEDIATED_REJECTION': {
        'aliases': ['antibody-mediated rejection', 'antibody mediated rejection', 'amr',
                    'humoral rejection'],
        'subspecialty': 'rejection',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- graft ---
    'GRAFT_LOSS': {
        'aliases': ['graft loss', 'graft failure', 'allograft loss', 'allograft failure',
                    'death-censored graft loss', 'death censored graft loss', 'graft survival',
                    'allograft survival'],
        'subspecialty': 'graft',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'DELAYED_GRAFT_FUNCTION': {
        'aliases': ['delayed graft function', 'dgf', 'delayed allograft function'],
        'subspecialty': 'graft',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- function (continuous) ---
    'EGFR': {
        'aliases': ['estimated glomerular filtration rate', 'estimated gfr', 'egfr',
                    'measured gfr', 'mgfr', 'glomerular filtration rate', 'gfr'],
        'subspecialty': 'function',
        'measure_types': ['MD', 'SMD']
    },
    'SERUM_CREATININE': {
        'aliases': ['serum creatinine', 'creatinine', 'plasma creatinine'],
        'subspecialty': 'function',
        'measure_types': ['MD', 'SMD']
    },

    # --- complications ---
    'PATIENT_SURVIVAL': {
        'aliases': ['patient survival', 'patient death', 'all-cause mortality', 'all cause mortality',
                    'death', 'mortality', 'patient mortality'],
        'subspecialty': 'complications',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'CMV_INFECTION': {
        'aliases': ['cytomegalovirus infection', 'cmv infection', 'cmv disease', 'cmv viraemia',
                    'cmv viremia'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'BK_INFECTION': {
        'aliases': ['bk virus', 'bk viraemia', 'bk viremia', 'bk nephropathy', 'bk viruria',
                    'polyomavirus nephropathy'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'NODAT': {
        'aliases': ['new-onset diabetes after transplantation', 'new onset diabetes after transplant',
                    'post-transplant diabetes', 'nodat', 'ptdm'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'PTLD': {
        'aliases': ['post-transplant lymphoproliferative disorder',
                    'posttransplant lymphoproliferative disorder', 'ptld'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# REJECTION PATTERNS
# ============================================================

REJECTION_PATTERNS = {
    'detection_keywords': [
        r'biopsy[- ]proven\s+acute\s+rejection|\bbpar\b', r'acute\s+rejection',
        r'antibody[- ]mediated\s+rejection|\bamr\b', r'acute\s+cellular\s+rejection',
        r'rejection\s+(?:episode|rate)',
    ],
    'endpoint_patterns': [
        (r'antibody[- ]mediated\s+rejection|\bamr\b|humoral\s+rejection',
         'ANTIBODY_MEDIATED_REJECTION'),
        (r'biopsy[- ]proven\s+acute\s+rejection|\bbpar\b|acute\s+cellular\s+rejection|'
         r'(?:treated\s+|clinical\s+)?acute\s+rejection', 'ACUTE_REJECTION'),
    ],
    'context_patterns': [
        r'banff', r'\d+\s*months?\s+post[- ]transplant', r'hazard\s+ratio|\bhr\b',
    ]
}


# ============================================================
# GRAFT PATTERNS
# ============================================================

GRAFT_PATTERNS = {
    'detection_keywords': [
        r'graft\s+(?:loss|failure|survival)', r'allograft\s+(?:loss|failure|survival)',
        r'death[- ]censored\s+graft', r'delayed\s+graft\s+function|\bdgf\b',
    ],
    'endpoint_patterns': [
        (r'delayed\s+(?:graft|allograft)\s+function|\bdgf\b', 'DELAYED_GRAFT_FUNCTION'),
        (r'(?:death[- ]censored\s+)?(?:graft|allograft)\s+(?:loss|failure|survival)', 'GRAFT_LOSS'),
    ],
    'context_patterns': [
        r'death[- ]censored', r'\d+[- ]year\s+graft', r'dialysis\s+initiation',
    ]
}


# ============================================================
# FUNCTION PATTERNS (continuous)
# ============================================================

FUNCTION_PATTERNS = {
    'detection_keywords': [
        r'estimated\s+glomerular\s+filtration\s+rate|\begfr\b', r'measured\s+gfr|\bmgfr\b',
        r'serum\s+creatinine', r'glomerular\s+filtration\s+rate|\bgfr\b', r'creatinine\s+clearance',
    ],
    'endpoint_patterns': [
        (r'estimated\s+glomerular\s+filtration\s+rate|\begfr\b|measured\s+gfr|\bmgfr\b|'
         r'glomerular\s+filtration\s+rate|\bgfr\b', 'EGFR'),
        (r'(?:serum\s+|plasma\s+)?creatinine', 'SERUM_CREATININE'),
    ],
    'context_patterns': [
        r'ml/min', r'mg/dl|µmol/l|umol/l', r'at\s+(?:12|24|36)\s+months',
    ]
}


# ============================================================
# COMPLICATIONS PATTERNS
# ============================================================

COMPLICATIONS_PATTERNS = {
    'detection_keywords': [
        r'patient\s+survival|patient\s+death', r'cytomegalovirus|\bcmv\b',
        r'\bbk\s+(?:virus|viru?[ae]mia|nephropathy)', r'new[- ]onset\s+diabetes|\bnodat\b|\bptdm\b',
        r'lymphoproliferative|\bptld\b', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'cytomegalovirus\s+(?:infection|disease)|cmv\s+(?:infection|disease|virae?mia)',
         'CMV_INFECTION'),
        (r'bk\s+(?:virus|virae?mia|nephropathy|viruria)|polyomavirus\s+nephropathy',
         'BK_INFECTION'),
        (r'new[- ]onset\s+diabetes\s+after\s+transplant\w*|post[- ]transplant\s+diabetes|'
         r'\bnodat\b|\bptdm\b', 'NODAT'),
        (r'post[- ]?transplant\s+lymphoproliferative\s+disorder|\bptld\b', 'PTLD'),
        (r'patient\s+survival|patient\s+(?:death|mortality)|all[- ]cause\s+(?:mortality|death)|'
         r'\bmortality\b', 'PATIENT_SURVIVAL'),
    ],
    'context_patterns': [
        r'prophylaxis', r'\d+[- ]year\s+(?:patient\s+)?survival', r'opportunistic\s+infection',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_kidney_transplant_subspecialty(text: str) -> Tuple[str, float]:
    """Detect kidney-transplant trial subspecialty. Returns (subspecialty,
    confidence). Subspecialties: rejection, graft, function, complications,
    general_transplant."""
    text_lower = text.lower()
    scores = {'rejection': 0, 'graft': 0, 'function': 0, 'complications': 0}
    for kw in REJECTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['rejection'] += 1
    for kw in GRAFT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['graft'] += 1
    for kw in FUNCTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['function'] += 1
    for kw in COMPLICATIONS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['complications'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_transplant', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_kidney_transplant_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'rejection': REJECTION_PATTERNS['endpoint_patterns'],
        'graft': GRAFT_PATTERNS['endpoint_patterns'],
        'function': FUNCTION_PATTERNS['endpoint_patterns'],
        'complications': COMPLICATIONS_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_kidney_transplant_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical kidney-transplant endpoint, preferring the LONGEST
    matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in KIDNEY_TRANSPLANT_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
