"""
Heart & Lung Transplantation Subspecialty Patterns and Endpoints

Built on the same transplant meta-analysis workflow. Thoracic-organ transplant
RCTs (heart, lung, heart-lung; immunosuppression, induction, CNI/mTOR regimens)
report a distinct endpoint vocabulary - acute cellular / antibody-mediated
rejection, primary graft dysfunction, cardiac allograft vasculopathy (heart),
chronic lung allograft dysfunction / bronchiolitis obliterans (lung), graft loss
- that is NOT covered by kidney_transplant (renal allograft) or liver_transplant
(hepatic graft).

Subspecialties:
- rejection: (treated / ISHLT-graded) acute cellular rejection, antibody-mediated
  rejection.
- graft: graft loss / failure / survival / retransplantation, primary graft
  dysfunction (PGD), cardiac allograft vasculopathy (CAV), chronic lung allograft
  dysfunction (CLAD) / bronchiolitis obliterans syndrome (BOS).
- function (continuous): estimated GFR / serum creatinine (CNI nephrotoxicity
  surrogate, shared across thoracic transplant).
- complications: patient survival / all-cause mortality, CMV infection, new-onset
  diabetes after transplant, post-transplant lymphoproliferative disorder.

Drug / regimen classes (arm labels): calcineurin inhibitors (tacrolimus,
ciclosporin), antiproliferatives (mycophenolate, azathioprine), mTOR inhibitors
(everolimus, sirolimus), induction (basiliximab, anti-thymocyte globulin),
corticosteroids, placebo.

Effect measures: rejection / graft / PGD / CAV / CLAD / survival / CMV ->
RR/OR/HR; eGFR / creatinine -> MD/SMD (continuous, natural scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# HEART/LUNG-TRANSPLANT ENDPOINTS
# ============================================================

HEART_LUNG_TRANSPLANT_ENDPOINTS = {
    # --- rejection ---
    'ACUTE_REJECTION': {
        'aliases': ['acute cellular rejection', 'biopsy-proven acute rejection',
                    'biopsy proven acute rejection', 'treated acute rejection',
                    'acute rejection', 'bpar', 'is4r rejection', 'grade 2r rejection',
                    'cellular rejection'],
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
                    're-transplantation'],
        'subspecialty': 'graft',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'PRIMARY_GRAFT_DYSFUNCTION': {
        'aliases': ['primary graft dysfunction', 'pgd', 'severe primary graft dysfunction',
                    'grade 3 primary graft dysfunction', 'primary graft failure'],
        'subspecialty': 'graft',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CARDIAC_ALLOGRAFT_VASCULOPATHY': {
        'aliases': ['cardiac allograft vasculopathy', 'cav', 'coronary allograft vasculopathy',
                    'transplant coronary artery disease', 'allograft vasculopathy'],
        'subspecialty': 'graft',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CHRONIC_LUNG_ALLOGRAFT_DYSFUNCTION': {
        'aliases': ['chronic lung allograft dysfunction', 'clad',
                    'bronchiolitis obliterans syndrome', 'bos',
                    'bronchiolitis obliterans', 'obliterative bronchiolitis'],
        'subspecialty': 'graft',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- function (continuous) ---
    'EGFR': {
        'aliases': ['estimated glomerular filtration rate', 'estimated gfr', 'egfr',
                    'measured gfr', 'glomerular filtration rate', 'gfr'],
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
        r'acute\s+cellular\s+rejection', r'biopsy[- ]proven\s+acute\s+rejection|\bbpar\b',
        r'acute\s+rejection', r'antibody[- ]mediated\s+rejection|\bamr\b',
        r'(?:is4r|grade\s+[23]r)\s+rejection|endomyocardial\s+biopsy',
    ],
    'endpoint_patterns': [
        (r'antibody[- ]mediated\s+rejection|\bamr\b|humoral\s+rejection',
         'ANTIBODY_MEDIATED_REJECTION'),
        (r'acute\s+cellular\s+rejection|biopsy[- ]proven\s+acute\s+rejection|\bbpar\b|'
         r'(?:is4r|grade\s+[23]r)\s+rejection|(?:treated\s+)?acute\s+rejection|'
         r'cellular\s+rejection', 'ACUTE_REJECTION'),
    ],
    'context_patterns': [
        r'ishlt', r'\d+\s*months?\s+post[- ]transplant', r'hazard\s+ratio|\bhr\b',
    ]
}


# ============================================================
# GRAFT PATTERNS
# ============================================================

GRAFT_PATTERNS = {
    'detection_keywords': [
        r'graft\s+(?:loss|failure|survival)', r'allograft\s+(?:loss|failure|survival)',
        r'primary\s+graft\s+dysfunction|\bpgd\b',
        r'cardiac\s+allograft\s+vasculopathy|\bcav\b',
        r'chronic\s+lung\s+allograft\s+dysfunction|\bclad\b|'
        r'bronchiolitis\s+obliterans(?:\s+syndrome)?|\bbos\b',
    ],
    'endpoint_patterns': [
        (r'primary\s+graft\s+(?:dysfunction|failure)|\bpgd\b', 'PRIMARY_GRAFT_DYSFUNCTION'),
        (r'(?:cardiac|coronary)\s+allograft\s+vasculopathy|\bcav\b|'
         r'transplant\s+coronary\s+artery\s+disease', 'CARDIAC_ALLOGRAFT_VASCULOPATHY'),
        (r'chronic\s+lung\s+allograft\s+dysfunction|\bclad\b|'
         r'bronchiolitis\s+obliterans(?:\s+syndrome)?|\bbos\b|obliterative\s+bronchiolitis',
         'CHRONIC_LUNG_ALLOGRAFT_DYSFUNCTION'),
        (r'(?:graft|allograft)\s+(?:loss|failure|survival)|retransplant\w*|'
         r're[- ]transplant\w*', 'GRAFT_LOSS'),
    ],
    'context_patterns': [
        r'\d+[- ]year\s+graft', r'angiograph', r'spirometr',
    ]
}


# ============================================================
# FUNCTION PATTERNS (continuous)
# ============================================================

FUNCTION_PATTERNS = {
    'detection_keywords': [
        r'estimated\s+glomerular\s+filtration\s+rate|\begfr\b', r'measured\s+gfr',
        r'serum\s+creatinine', r'glomerular\s+filtration\s+rate|\bgfr\b',
        r'renal\s+(?:dysfunction|impairment)|nephrotoxicity',
    ],
    'endpoint_patterns': [
        (r'estimated\s+glomerular\s+filtration\s+rate|\begfr\b|measured\s+gfr|'
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
        r'new[- ]onset\s+diabetes|\bnodat\b|\bptdm\b',
        r'lymphoproliferative|\bptld\b', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'cytomegalovirus\s+(?:infection|disease)|cmv\s+(?:infection|disease|virae?mia)',
         'CMV_INFECTION'),
        (r'new[- ]onset\s+diabetes\s+after\s+transplant\w*|post[- ]transplant\s+diabetes|'
         r'\bnodat\b|\bptdm\b', 'NODAT'),
        (r'post[- ]?transplant\s+lymphoproliferative\s+disorder|\bptld\b', 'PTLD'),
        (r'patient\s+survival|patient\s+(?:death|mortality)|all[- ]cause\s+(?:mortality|death)|'
         r'overall\s+survival|\bmortality\b', 'PATIENT_SURVIVAL'),
    ],
    'context_patterns': [
        r'prophylaxis', r'\d+[- ]year\s+(?:patient\s+)?survival', r'opportunistic\s+infection',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_heart_lung_transplant_subspecialty(text: str) -> Tuple[str, float]:
    """Detect heart/lung-transplant trial subspecialty. Returns (subspecialty,
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


def get_heart_lung_transplant_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'rejection': REJECTION_PATTERNS['endpoint_patterns'],
        'graft': GRAFT_PATTERNS['endpoint_patterns'],
        'function': FUNCTION_PATTERNS['endpoint_patterns'],
        'complications': COMPLICATIONS_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_heart_lung_transplant_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical heart/lung-transplant endpoint, preferring the
    LONGEST matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in HEART_LUNG_TRANSPLANT_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
