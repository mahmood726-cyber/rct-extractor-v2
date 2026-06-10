"""
Prostate Cancer Subspecialty Patterns and Endpoints

Built on the same per-disease-profile pattern as the cervical-cancer, HIV and
malaria profiles. Prostate cancer is the most common male cancer worldwide and
its RCTs report a distinct endpoint vocabulary — radiographic progression-free
survival, PSA response, biochemical recurrence, metastasis-free survival,
time to castration resistance — that the generic oncology bucket does not split
out on its own.

Subspecialties:
- systemic (advanced / metastatic CRPC & HSPC): overall survival, radiographic
  PFS, PSA response (PSA50 / >=50% PSA decline), time to PSA progression,
  objective response, skeletal-related events, time to next therapy. Agents:
  abiraterone, enzalutamide, apalutamide, darolutamide, docetaxel, cabazitaxel,
  olaparib, [177Lu]Lu-PSMA-617, sipuleucel-T, radium-223.
- localized (radiotherapy / prostatectomy / active surveillance): biochemical
  recurrence / failure, biochemical recurrence-free survival, metastasis-free
  survival, local recurrence. Modalities: radical prostatectomy, EBRT/IMRT,
  brachytherapy, dose escalation, active surveillance.
- hormonal (androgen-deprivation therapy): castrate testosterone level /
  suppression, time to castration resistance. Agents: leuprolide, goserelin,
  triptorelin, degarelix, relugolix.
- mortality / metastasis: prostate-cancer-specific mortality, all-cause
  mortality, distant metastasis.

Effect measures follow what these trials report: time-to-event endpoints (OS,
rPFS, MFS, BRFS, time-to-progression) -> HR; binary (PSA response, biochemical
recurrence, SRE, metastasis) -> RR/OR/RD/HR; continuous PSA -> log-normal (PSA is
conventionally analysed on the log scale); testosterone / QoL (FACT-P) -> MD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# PROSTATE CANCER ENDPOINTS
# ============================================================

PROSTATE_CANCER_ENDPOINTS = {
    # --- systemic (advanced / metastatic) ---
    'OS': {
        'aliases': ['overall survival', 'os', 'death from any cause',
                    'all-cause death'],
        'subspecialty': 'systemic',
        'measure_types': ['HR', 'median', 'rate']
    },
    'RPFS': {
        'aliases': ['radiographic progression-free survival', 'rpfs',
                    'radiologic progression-free survival',
                    'imaging-based progression-free survival',
                    'radiographic progression'],
        'subspecialty': 'systemic',
        'measure_types': ['HR', 'median']
    },
    'PFS': {
        'aliases': ['progression-free survival', 'pfs',
                    'disease progression or death'],
        'subspecialty': 'systemic',
        'measure_types': ['HR', 'median']
    },
    'PSA_RESPONSE': {
        'aliases': ['psa response', 'psa50', 'psa-50', '>=50% psa decline',
                    '50% psa decline', 'psa decline', 'psa response rate',
                    'prostate-specific antigen response', 'psa90'],
        'subspecialty': 'systemic',
        'measure_types': ['OR', 'RR', 'RD', 'rate']
    },
    'TIME_TO_PSA_PROGRESSION': {
        'aliases': ['time to psa progression', 'psa progression-free survival',
                    'time to prostate-specific antigen progression',
                    'psa progression'],
        'subspecialty': 'systemic',
        'measure_types': ['HR', 'median']
    },
    'ORR': {
        'aliases': ['objective response rate', 'orr', 'overall response rate',
                    'radiographic response rate'],
        'subspecialty': 'systemic',
        'measure_types': ['OR', 'RR', 'rate']
    },
    'SRE': {
        'aliases': ['skeletal-related event', 'skeletal related event',
                    'symptomatic skeletal event', 'sse', 'time to first sre',
                    'time to skeletal-related event'],
        'subspecialty': 'systemic',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'TIME_TO_NEXT_THERAPY': {
        'aliases': ['time to next therapy', 'time to subsequent therapy',
                    'time to next systemic therapy', 'ttnt'],
        'subspecialty': 'systemic',
        'measure_types': ['HR', 'median']
    },

    # --- localized (radiotherapy / surgery) ---
    'BIOCHEMICAL_RECURRENCE': {
        'aliases': ['biochemical recurrence', 'biochemical failure',
                    'biochemical relapse', 'psa recurrence', 'psa failure',
                    'biochemical progression'],
        'subspecialty': 'localized',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'BRFS': {
        'aliases': ['biochemical recurrence-free survival',
                    'biochemical relapse-free survival',
                    'biochemical failure-free survival', 'brfs',
                    'biochemical disease-free survival', 'bdfs',
                    'biochemical progression-free survival'],
        'subspecialty': 'localized',
        'measure_types': ['HR', 'median']
    },
    'MFS': {
        'aliases': ['metastasis-free survival', 'metastasis free survival',
                    'mfs', 'distant metastasis-free survival', 'dmfs'],
        'subspecialty': 'localized',
        'measure_types': ['HR', 'median']
    },
    'LOCAL_RECURRENCE': {
        'aliases': ['local recurrence', 'local failure', 'locoregional recurrence',
                    'local control'],
        'subspecialty': 'localized',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- hormonal (androgen-deprivation therapy) ---
    'TESTOSTERONE_SUPPRESSION': {
        'aliases': ['castrate testosterone', 'testosterone suppression',
                    'castration level', 'castrate level of testosterone',
                    'sustained castration', 'testosterone <50 ng/dl',
                    'serum testosterone'],
        'subspecialty': 'hormonal',
        'measure_types': ['RR', 'RD', 'OR', 'MD']
    },
    'TIME_TO_CRPC': {
        'aliases': ['time to castration resistance',
                    'time to castration-resistant prostate cancer',
                    'castration-resistance-free survival',
                    'time to crpc'],
        'subspecialty': 'hormonal',
        'measure_types': ['HR', 'median']
    },

    # --- mortality / metastasis ---
    'PROSTATE_CANCER_MORTALITY': {
        'aliases': ['prostate cancer mortality', 'prostate-cancer mortality',
                    'prostate cancer-specific mortality',
                    'prostate cancer death', 'death from prostate cancer',
                    'cancer-specific mortality', 'cancer-specific survival'],
        'subspecialty': 'mortality',
        'measure_types': ['HR', 'RR', 'IRR']
    },
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'METASTASIS': {
        'aliases': ['distant metastasis', 'distant metastases',
                    'metastatic progression', 'development of metastases',
                    'time to metastasis', 'bone metastasis'],
        'subspecialty': 'mortality',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- continuous / QoL ---
    'PSA_LEVEL': {
        'aliases': ['psa level', 'prostate-specific antigen level',
                    'psa nadir', 'serum psa', 'psa concentration'],
        'subspecialty': 'systemic',
        'measure_types': ['MD', 'GMR']
    },
    'QOL': {
        'aliases': ['quality of life', 'fact-p', 'hrqol', 'eortc qlq',
                    'health-related quality of life'],
        'subspecialty': 'systemic',
        'measure_types': ['MD']
    },
}


# ============================================================
# SYSTEMIC (advanced / metastatic) PATTERNS
# ============================================================

SYSTEMIC_PATTERNS = {
    'detection_keywords': [
        r'metastatic\s+(?:castration[- ]?resistant|castrate[- ]?resistant|'
        r'hormone[- ]?sensitive|castration[- ]?sensitive)\s+prostate',
        r'\bm?crpc\b', r'\bm?hspc\b', r'\bnmcrpc\b', r'castration[- ]?resistant',
        r'abiraterone|zytiga', r'enzalutamide|xtandi', r'apalutamide|erleada',
        r'darolutamide|nubeqa', r'docetaxel', r'cabazitaxel|jevtana',
        r'olaparib|talazoparib|niraparib', r'lutetium[- ]?177|177lu|psma[- ]?617|pluvicto',
        r'sipuleucel[- ]?t|provenge', r'radium[- ]?223|xofigo',
        r'psa\s+(?:response|decline|progression)', r'radiographic\s+progression',
    ],
    'endpoint_patterns': [
        (r'radiographic\s+progression[- ]?free\s+survival|imaging[- ]based\s+progression',
         'RPFS'),
        (r'(?<!radiographic\s)progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'psa\s*(?:50|90)|psa\s+response|(?:50|90)\s*%\s+(?:decline\s+in\s+)?psa|'
         r'prostate[- ]specific\s+antigen\s+response|psa\s+decline', 'PSA_RESPONSE'),
        (r'time\s+to\s+psa\s+progression|psa\s+progression[- ]?free\s+survival|'
         r'time\s+to\s+prostate[- ]specific\s+antigen\s+progression', 'TIME_TO_PSA_PROGRESSION'),
        (r'objective\s+response\s+rate|radiographic\s+response\s+rate', 'ORR'),
        (r'skeletal[- ]?related\s+event|symptomatic\s+skeletal\s+event|\bsse\b',
         'SRE'),
        (r'time\s+to\s+(?:next|subsequent)\s+(?:systemic\s+)?therapy|\bttnt\b',
         'TIME_TO_NEXT_THERAPY'),
        (r'psa\s+(?:level|nadir|concentration)|serum\s+psa|'
         r'prostate[- ]specific\s+antigen\s+level', 'PSA_LEVEL'),
        (r'quality\s+of\s+life|fact-p|hrqol|eortc\s+qlq', 'QOL'),
    ],
    'context_patterns': [
        r'per[- ]protocol|intention[- ]to[- ]treat', r'recist',
        r'pcwg[- ]?[23]|prostate\s+cancer\s+working\s+group',
    ]
}


# ============================================================
# LOCALIZED (radiotherapy / surgery) PATTERNS
# ============================================================

LOCALIZED_PATTERNS = {
    'detection_keywords': [
        r'radical\s+prostatectomy', r'external[- ]beam\s+radi[o]?therapy|\bebrt\b',
        r'intensity[- ]modulated\s+radi|\bimrt\b', r'brachytherapy',
        r'dose[- ]escalat', r'active\s+surveillance', r'localized\s+prostate\s+cancer',
        r'localised\s+prostate\s+cancer', r'biochemical\s+(?:recurrence|failure|relapse)',
        r'low[- ]risk\s+prostate|intermediate[- ]risk\s+prostate|high[- ]risk\s+prostate',
        r'\bgleason\b', r'stereotactic\s+body\s+radi|\bsbrt\b',
    ],
    'endpoint_patterns': [
        (r'biochemical\s+(?:recurrence|relapse|failure|progression)[- ]?free\s+survival|'
         r'biochemical\s+disease[- ]?free\s+survival|\bb[dr]fs\b', 'BRFS'),
        (r'biochemical\s+(?:recurrence|failure|relapse|progression)|psa\s+(?:recurrence|failure)',
         'BIOCHEMICAL_RECURRENCE'),
        (r'(?:distant\s+)?metastasis[- ]?free\s+survival|\bdmfs\b|\bmfs\b', 'MFS'),
        (r'local(?:[- ]?regional)?\s+(?:recurrence|failure|control)', 'LOCAL_RECURRENCE'),
    ],
    'context_patterns': [
        r'phoenix\s+(?:definition|criteria)', r'nadir\s*\+\s*2',
        r'gy\b|gray', r'fraction',
    ]
}


# ============================================================
# HORMONAL (ADT) PATTERNS
# ============================================================

HORMONAL_PATTERNS = {
    'detection_keywords': [
        r'androgen[- ]deprivation\s+therapy|\badt\b',
        r'luteinizing[- ]hormone[- ]releasing[- ]hormone|lhrh|gnrh',
        r'leuprolide|leuprorelin|goserelin|zoladex|triptorelin',
        r'degarelix|firmagon', r'relugolix|orgovyx',
        r'castrate\s+(?:level|testosterone)|testosterone\s+suppression',
        r'medical\s+castration|orchiectomy|orchidectomy',
        r'bicalutamide|flutamide|nilutamide',
    ],
    'endpoint_patterns': [
        (r'castrate\s+(?:level|testosterone)|testosterone\s+suppression|'
         r'sustained\s+castration|testosterone\s*<\s*50|serum\s+testosterone',
         'TESTOSTERONE_SUPPRESSION'),
        (r'time\s+to\s+castration[- ]?resistance|time\s+to\s+crpc|'
         r'castration[- ]?resistance[- ]?free\s+survival|'
         r'time\s+to\s+castration[- ]?resistant\s+prostate', 'TIME_TO_CRPC'),
    ],
    'context_patterns': [
        r'ng/dl|nmol/l', r'intermittent|continuous\s+androgen',
    ]
}


# ============================================================
# MORTALITY / METASTASIS PATTERNS
# ============================================================

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'prostate\s+cancer[- ]?specific\s+mortality|prostate[- ]cancer\s+mortality',
        r'prostate\s+cancer\s+death|death\s+from\s+prostate\s+cancer',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
        r'distant\s+metastas[ie]s', r'bone\s+metastas[ie]s',
        r'time\s+to\s+metastasis',
    ],
    'endpoint_patterns': [
        (r'prostate\s+cancer[- ]?(?:specific\s+)?(?:mortality|death)|'
         r'death\s+from\s+prostate\s+cancer|cancer[- ]specific\s+(?:mortality|survival)',
         'PROSTATE_CANCER_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
        (r'(?:distant|bone)\s+metastas[ie]s|metastatic\s+progression|'
         r'time\s+to\s+metastasis|development\s+of\s+metastas', 'METASTASIS'),
    ],
    'context_patterns': [
        r'per\s+(?:100,?000\s+)?person[- ]years', r'cumulative\s+incidence',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_prostate_cancer_subspecialty(text: str) -> Tuple[str, float]:
    """Detect prostate-cancer trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: systemic, localized, hormonal, mortality, general_prostate_cancer."""
    text_lower = text.lower()
    scores = {'systemic': 0, 'localized': 0, 'hormonal': 0, 'mortality': 0}
    for kw in SYSTEMIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['systemic'] += 1
    for kw in LOCALIZED_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['localized'] += 1
    for kw in HORMONAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['hormonal'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_prostate_cancer', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_prostate_cancer_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'systemic': SYSTEMIC_PATTERNS['endpoint_patterns'],
        'localized': LOCALIZED_PATTERNS['endpoint_patterns'],
        'hormonal': HORMONAL_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_prostate_cancer_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical prostate-cancer endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in PROSTATE_CANCER_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
