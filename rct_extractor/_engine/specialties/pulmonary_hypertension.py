"""
Pulmonary Hypertension (PH / PAH) Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow as the other cardio-metabolic profiles.
Pulmonary arterial hypertension RCTs report a distinct endpoint vocabulary
(6-minute walk distance, WHO functional class, pulmonary vascular resistance and
mean pulmonary arterial pressure, time to clinical worsening, NT-proBNP) that the
generic effect-size engine — and the cardiology / respiratory specialties — do
not recognise.

Subspecialties:
- functional: 6-minute walk distance (6MWD), WHO/NYHA functional-class improvement,
  Borg dyspnoea score.
- hemodynamics (continuous): pulmonary vascular resistance (PVR), mean pulmonary
  arterial pressure (mPAP), cardiac index / cardiac output.
- clinical_worsening: time to clinical worsening, PH-related hospitalisation,
  all-cause mortality.
- biomarker (continuous): NT-proBNP / BNP.

Drug classes (arm labels): PDE5 inhibitors (sildenafil, tadalafil), endothelin
receptor antagonists (bosentan, ambrisentan, macitentan), prostacyclin-pathway
agents (epoprostenol, treprostinil, iloprost, selexipag, beraprost), sGC
stimulator (riociguat), activin-signalling inhibitor (sotatercept), placebo.

Effect measures: 6MWD / PVR / mPAP / cardiac index / NT-proBNP -> MD/SMD
(continuous); WHO-FC improvement, clinical worsening, hospitalisation, mortality
-> RR/OR/HR (binary / time-to-event).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# PULMONARY-HYPERTENSION ENDPOINTS
# ============================================================

PULMONARY_HYPERTENSION_ENDPOINTS = {
    # --- functional ---
    'SIX_MWD': {
        'aliases': ['6-minute walk distance', 'six-minute walk distance', '6 minute walk distance',
                    'six minute walk distance', '6mwd', 'six-minute walking distance',
                    '6-min walk distance', 'change in 6-minute walk distance', 'walk distance'],
        'subspecialty': 'functional',
        'measure_types': ['MD', 'SMD']
    },
    'WHO_FC': {
        'aliases': ['who functional class', 'world health organization functional class',
                    'nyha functional class', 'functional class improvement', 'who-fc',
                    'functional class'],
        'subspecialty': 'functional',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BORG_DYSPNEA': {
        'aliases': ['borg dyspnea score', 'borg dyspnoea score', 'borg score', 'dyspnea score'],
        'subspecialty': 'functional',
        'measure_types': ['MD', 'SMD']
    },

    # --- hemodynamics (continuous) ---
    'PVR': {
        'aliases': ['pulmonary vascular resistance', 'pvr', 'change in pulmonary vascular resistance',
                    'pulmonary vascular resistance index'],
        'subspecialty': 'hemodynamics',
        'measure_types': ['MD', 'SMD']
    },
    'MPAP': {
        'aliases': ['mean pulmonary arterial pressure', 'mean pulmonary artery pressure', 'mpap',
                    'pulmonary arterial pressure', 'mean pap'],
        'subspecialty': 'hemodynamics',
        'measure_types': ['MD', 'SMD']
    },
    'CARDIAC_INDEX': {
        'aliases': ['cardiac index', 'cardiac output', 'change in cardiac index'],
        'subspecialty': 'hemodynamics',
        'measure_types': ['MD', 'SMD']
    },

    # --- clinical_worsening ---
    'CLINICAL_WORSENING': {
        'aliases': ['clinical worsening', 'time to clinical worsening', 'morbidity/mortality event',
                    'morbidity and mortality', 'first morbidity or mortality event',
                    'disease progression'],
        'subspecialty': 'clinical_worsening',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'PH_HOSPITALIZATION': {
        'aliases': ['hospitalization for pulmonary hypertension', 'hospitalisation for pulmonary hypertension',
                    'ph-related hospitalization', 'pah-related hospitalization',
                    'hospitalization for worsening', 'hospitalisation'],
        'subspecialty': 'clinical_worsening',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'all cause mortality', 'death from any cause',
                    'overall mortality', 'all-cause death', 'mortality'],
        'subspecialty': 'clinical_worsening',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- biomarker (continuous) ---
    'NT_PROBNP': {
        'aliases': ['nt-probnp', 'n-terminal pro-b-type natriuretic peptide', 'nt-pro-bnp',
                    'brain natriuretic peptide', 'bnp', 'change in nt-probnp'],
        'subspecialty': 'biomarker',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# FUNCTIONAL PATTERNS
# ============================================================

FUNCTIONAL_PATTERNS = {
    'detection_keywords': [
        r'6[- ]min(?:ute)?\s+walk|six[- ]min(?:ute)?\s+walk|\b6mwd\b|\b6mwt\b',
        r'who\s+functional\s+class|nyha\s+functional\s+class|functional\s+class',
        r'borg\s+dyspn(?:o)?ea', r'exercise\s+capacity',
    ],
    'endpoint_patterns': [
        (r'(?:change\s+in\s+)?(?:6[- ]min(?:ute)?|six[- ]min(?:ute)?)\s+walk(?:ing)?\s+distance|'
         r'\b6mwd\b', 'SIX_MWD'),
        (r'(?:who|world\s+health\s+organization|nyha)\s+functional\s+class(?:\s+improvement)?|'
         r'functional\s+class\s+improvement|\bwho[- ]fc\b', 'WHO_FC'),
        (r'borg\s+dyspn(?:o)?ea\s+score|borg\s+score|dyspn(?:o)?ea\s+score', 'BORG_DYSPNEA'),
    ],
    'context_patterns': [
        r'\bmeters?\b|\bmetres?\b', r'baseline\s+to\s+week\s+\d+', r'placebo[- ]corrected',
    ]
}


# ============================================================
# HEMODYNAMICS PATTERNS (continuous)
# ============================================================

HEMODYNAMICS_PATTERNS = {
    'detection_keywords': [
        r'pulmonary\s+vascular\s+resistance|\bpvr\b', r'mean\s+pulmonary\s+arter(?:ial|y)\s+pressure|\bmpap\b',
        r'cardiac\s+index|cardiac\s+output', r'right\s+heart\s+catheter', r'h(?:a)?emodynamic',
    ],
    'endpoint_patterns': [
        (r'pulmonary\s+vascular\s+resistance(?:\s+index)?|\bpvr\b', 'PVR'),
        (r'mean\s+pulmonary\s+arter(?:ial|y)\s+pressure|\bmpap\b|mean\s+pap', 'MPAP'),
        (r'cardiac\s+index|cardiac\s+output', 'CARDIAC_INDEX'),
    ],
    'context_patterns': [
        r'dyn|wood\s+units|mmhg', r'right\s+heart\s+catheter', r'l/min',
    ]
}


# ============================================================
# CLINICAL-WORSENING PATTERNS
# ============================================================

CLINICAL_WORSENING_PATTERNS = {
    'detection_keywords': [
        r'clinical\s+worsening', r'morbidity\s+(?:and|/|or)\s+mortality',
        r'time\s+to\s+(?:clinical\s+)?worsening', r'hospitali[sz]ation', r'disease\s+progression',
        r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'(?:time\s+to\s+)?clinical\s+worsening|(?:first\s+)?morbidity\s*(?:and|/|or)\s*mortality'
         r'(?:\s+event)?|disease\s+progression', 'CLINICAL_WORSENING'),
        (r'hospitali[sz]ation\s+for\s+(?:pulmonary\s+hypertension|worsening)|'
         r'(?:ph|pah)[- ]related\s+hospitali[sz]ation', 'PH_HOSPITALIZATION'),
        (r'all[- ]cause\s+(?:mortality|death)|death\s+from\s+any\s+cause|overall\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [
        r'hazard\s+ratio|\bhr\b', r'kaplan[- ]meier', r'event[- ]driven',
    ]
}


# ============================================================
# BIOMARKER PATTERNS (continuous)
# ============================================================

BIOMARKER_PATTERNS = {
    'detection_keywords': [
        r'nt[- ]pro[- ]?bnp', r'n[- ]terminal\s+pro[- ]b[- ]type', r'natriuretic\s+peptide',
        r'\bbnp\b',
    ],
    'endpoint_patterns': [
        (r'nt[- ]pro[- ]?bnp|n[- ]terminal\s+pro[- ]b[- ]type\s+natriuretic\s+peptide|'
         r'brain\s+natriuretic\s+peptide|\bbnp\b', 'NT_PROBNP'),
    ],
    'context_patterns': [
        r'pg/ml|ng/l', r'percent\s+change', r'geometric\s+mean',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_pulmonary_hypertension_subspecialty(text: str) -> Tuple[str, float]:
    """Detect pulmonary-hypertension trial subspecialty. Returns (subspecialty,
    confidence). Subspecialties: functional, hemodynamics, clinical_worsening,
    biomarker, general_ph."""
    text_lower = text.lower()
    scores = {'functional': 0, 'hemodynamics': 0, 'clinical_worsening': 0, 'biomarker': 0}
    for kw in FUNCTIONAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['functional'] += 1
    for kw in HEMODYNAMICS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['hemodynamics'] += 1
    for kw in CLINICAL_WORSENING_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['clinical_worsening'] += 1
    for kw in BIOMARKER_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['biomarker'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_ph', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_pulmonary_hypertension_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'functional': FUNCTIONAL_PATTERNS['endpoint_patterns'],
        'hemodynamics': HEMODYNAMICS_PATTERNS['endpoint_patterns'],
        'clinical_worsening': CLINICAL_WORSENING_PATTERNS['endpoint_patterns'],
        'biomarker': BIOMARKER_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_pulmonary_hypertension_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical PH endpoint, preferring the LONGEST matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in PULMONARY_HYPERTENSION_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
