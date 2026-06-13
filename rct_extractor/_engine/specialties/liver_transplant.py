"""
Liver Transplantation Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow as the other transplant profiles. Liver-
transplant RCTs (immunosuppression regimens, induction therapy, CNI minimisation)
report a distinct endpoint vocabulary - biopsy-proven acute rejection, graft loss
/ retransplantation, hepatic artery thrombosis, biliary complications, primary
non-function, hepatocellular-carcinoma recurrence, CNI-related renal dysfunction -
that is NOT covered by the kidney-transplant profile (rejection/eGFR/DGF), by
cirrhosis (decompensation), or by hepatocellular_carcinoma (loco-regional /
systemic tumour therapy).

Subspecialties:
- rejection: (biopsy-proven) acute rejection, T-cell-mediated rejection,
  antibody-mediated rejection.
- graft: graft loss / failure / survival, retransplantation, hepatic artery
  thrombosis, biliary stricture / complication, primary non-function.
- function (continuous): estimated GFR / measured GFR, serum creatinine
  (CNI nephrotoxicity surrogate).
- complications: patient survival / all-cause mortality, hepatocellular-carcinoma
  recurrence, CMV infection, new-onset diabetes after transplant (NODAT/PTDM).

Drug / regimen classes (arm labels): calcineurin inhibitors (tacrolimus,
ciclosporin), antiproliferatives (mycophenolate / MPA, azathioprine), mTOR
inhibitors (everolimus, sirolimus), induction (basiliximab, anti-thymocyte
globulin), corticosteroids, placebo.

Effect measures: rejection / graft / HAT / biliary / survival / HCC recurrence /
CMV -> RR/OR/HR; eGFR / creatinine -> MD/SMD (continuous, natural scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# LIVER-TRANSPLANT ENDPOINTS
# ============================================================

LIVER_TRANSPLANT_ENDPOINTS = {
    # --- rejection ---
    'ACUTE_REJECTION': {
        'aliases': ['biopsy-proven acute rejection', 'biopsy proven acute rejection',
                    'acute rejection', 'bpar', 'acute cellular rejection',
                    't-cell-mediated rejection', 't cell mediated rejection',
                    'treated acute rejection', 'clinical acute rejection'],
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
                    'graft survival', 'allograft survival', 'retransplantation',
                    're-transplantation', 're-transplant'],
        'subspecialty': 'graft',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HEPATIC_ARTERY_THROMBOSIS': {
        'aliases': ['hepatic artery thrombosis', 'hepatic-artery thrombosis', 'hat',
                    'arterial thrombosis'],
        'subspecialty': 'graft',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'BILIARY_COMPLICATION': {
        'aliases': ['biliary complication', 'biliary complications', 'biliary stricture',
                    'anastomotic stricture', 'bile leak', 'biliary leak',
                    'biliary anastomotic stricture'],
        'subspecialty': 'graft',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'PRIMARY_NONFUNCTION': {
        'aliases': ['primary non-function', 'primary nonfunction', 'pnf',
                    'early allograft dysfunction', 'initial poor function'],
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
                    'death', 'mortality', 'patient mortality', 'overall survival'],
        'subspecialty': 'complications',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'HCC_RECURRENCE': {
        'aliases': ['hepatocellular carcinoma recurrence', 'hcc recurrence', 'tumour recurrence',
                    'tumor recurrence', 'recurrence of hepatocellular carcinoma',
                    'recurrence-free survival'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CMV_INFECTION': {
        'aliases': ['cytomegalovirus infection', 'cmv infection', 'cmv disease', 'cmv viraemia',
                    'cmv viremia'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'NODAT': {
        'aliases': ['new-onset diabetes after transplantation', 'new onset diabetes after transplant',
                    'post-transplant diabetes', 'nodat', 'ptdm'],
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
        r'antibody[- ]mediated\s+rejection|\bamr\b',
        r'(?:acute\s+cellular|t[- ]cell[- ]mediated)\s+rejection',
        r'rejection\s+(?:episode|rate)',
    ],
    'endpoint_patterns': [
        (r'antibody[- ]mediated\s+rejection|\bamr\b|humoral\s+rejection',
         'ANTIBODY_MEDIATED_REJECTION'),
        (r'biopsy[- ]proven\s+acute\s+rejection|\bbpar\b|acute\s+cellular\s+rejection|'
         r't[- ]cell[- ]mediated\s+rejection|(?:treated\s+|clinical\s+)?acute\s+rejection',
         'ACUTE_REJECTION'),
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
        r'retransplant\w*|re[- ]transplant\w*', r'hepatic\s+artery\s+thrombosis|\bhat\b',
        r'biliary\s+(?:complication|stricture|leak)|anastomotic\s+stricture',
        r'primary\s+non[- ]?function|\bpnf\b|early\s+allograft\s+dysfunction',
    ],
    'endpoint_patterns': [
        (r'hepatic[- ]artery\s+thrombosis|\bhat\b|arterial\s+thrombosis',
         'HEPATIC_ARTERY_THROMBOSIS'),
        (r'biliary\s+(?:complication|stricture|leak)|(?:biliary\s+)?anastomotic\s+stricture|'
         r'bile\s+leak', 'BILIARY_COMPLICATION'),
        (r'primary\s+non[- ]?function|\bpnf\b|early\s+allograft\s+dysfunction|'
         r'initial\s+poor\s+function', 'PRIMARY_NONFUNCTION'),
        (r'(?:graft|allograft)\s+(?:loss|failure|survival)|retransplant\w*|'
         r're[- ]transplant\w*', 'GRAFT_LOSS'),
    ],
    'context_patterns': [
        r'\d+[- ]year\s+graft', r'doppler', r'meld\s+score',
    ]
}


# ============================================================
# FUNCTION PATTERNS (continuous)
# ============================================================

FUNCTION_PATTERNS = {
    'detection_keywords': [
        r'estimated\s+glomerular\s+filtration\s+rate|\begfr\b', r'measured\s+gfr|\bmgfr\b',
        r'serum\s+creatinine', r'glomerular\s+filtration\s+rate|\bgfr\b',
        r'renal\s+(?:dysfunction|impairment)|nephrotoxicity',
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
        r'hepatocellular\s+carcinoma\s+recurrence|hcc\s+recurrence|tumou?r\s+recurrence',
        r'new[- ]onset\s+diabetes|\bnodat\b|\bptdm\b', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'cytomegalovirus\s+(?:infection|disease)|cmv\s+(?:infection|disease|virae?mia)',
         'CMV_INFECTION'),
        (r'hepatocellular\s+carcinoma\s+recurrence|hcc\s+recurrence|tumou?r\s+recurrence|'
         r'recurrence\s+of\s+hepatocellular\s+carcinoma|recurrence[- ]free\s+survival',
         'HCC_RECURRENCE'),
        (r'new[- ]onset\s+diabetes\s+after\s+transplant\w*|post[- ]transplant\s+diabetes|'
         r'\bnodat\b|\bptdm\b', 'NODAT'),
        (r'patient\s+survival|patient\s+(?:death|mortality)|all[- ]cause\s+(?:mortality|death)|'
         r'overall\s+survival|\bmortality\b', 'PATIENT_SURVIVAL'),
    ],
    'context_patterns': [
        r'prophylaxis', r'\d+[- ]year\s+(?:patient\s+)?survival', r'milan\s+criteria',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_liver_transplant_subspecialty(text: str) -> Tuple[str, float]:
    """Detect liver-transplant trial subspecialty. Returns (subspecialty,
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


def get_liver_transplant_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'rejection': REJECTION_PATTERNS['endpoint_patterns'],
        'graft': GRAFT_PATTERNS['endpoint_patterns'],
        'function': FUNCTION_PATTERNS['endpoint_patterns'],
        'complications': COMPLICATIONS_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_liver_transplant_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical liver-transplant endpoint, preferring the LONGEST
    matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in LIVER_TRANSPLANT_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
