"""
Ovarian Cancer Subspecialty Patterns and Endpoints

Built on the same per-disease-profile pattern as the prostate-cancer and
cervical-cancer profiles. Epithelial ovarian cancer (incl. fallopian-tube and
primary peritoneal carcinoma) RCTs report a distinct endpoint vocabulary —
progression-free survival, maintenance PFS, CA-125 (GCIG) response, complete
cytoreduction (R0), platinum-free interval — that the generic oncology bucket
does not split out on its own.

Subspecialties:
- systemic (first-line / relapse chemotherapy & targeted therapy): overall
  survival, progression-free survival, objective response, CA-125 response,
  PFS2. Agents: carboplatin/paclitaxel, bevacizumab, gemcitabine, pegylated
  liposomal doxorubicin, topotecan.
- maintenance (PARP inhibitor / anti-angiogenic maintenance): maintenance PFS,
  time to first subsequent therapy, duration of response. Agents: olaparib,
  niraparib, rucaparib, bevacizumab maintenance; BRCA / HRD biomarker.
- surgical (cytoreduction): complete cytoreduction (R0) / optimal debulking,
  recurrence, residual disease (interval vs primary debulking surgery).
- mortality: ovarian-cancer-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, MaintPFS, PFS2, TFST) -> HR; binary
(objective response, CA-125 response, complete resection, recurrence) ->
RR/OR/RD/HR; continuous CA-125 -> log-normal (tumour-marker level analysed on
the log scale); QoL -> MD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# OVARIAN CANCER ENDPOINTS
# ============================================================

OVARIAN_CANCER_ENDPOINTS = {
    # --- systemic ---
    'OS': {
        'aliases': ['overall survival', 'os', 'death from any cause'],
        'subspecialty': 'systemic',
        'measure_types': ['HR', 'median', 'rate']
    },
    'PFS': {
        'aliases': ['progression-free survival', 'pfs',
                    'disease progression or death', 'progression free survival'],
        'subspecialty': 'systemic',
        'measure_types': ['HR', 'median']
    },
    'ORR': {
        'aliases': ['objective response rate', 'orr', 'overall response rate',
                    'tumor response', 'tumour response'],
        'subspecialty': 'systemic',
        'measure_types': ['OR', 'RR', 'rate']
    },
    'CA125_RESPONSE': {
        'aliases': ['ca-125 response', 'ca125 response', 'gcig ca-125 response',
                    'ca-125 normalization', 'ca-125 normalisation',
                    'cancer antigen 125 response'],
        'subspecialty': 'systemic',
        'measure_types': ['OR', 'RR', 'rate']
    },
    'PFS2': {
        'aliases': ['pfs2', 'second progression-free survival',
                    'time to second progression', 'second progression'],
        'subspecialty': 'systemic',
        'measure_types': ['HR', 'median']
    },

    # --- maintenance ---
    'MAINTENANCE_PFS': {
        'aliases': ['maintenance progression-free survival',
                    'progression-free survival during maintenance',
                    'investigator-assessed progression-free survival'],
        'subspecialty': 'maintenance',
        'measure_types': ['HR', 'median']
    },
    'TFST': {
        'aliases': ['time to first subsequent therapy', 'tfst',
                    'time to first subsequent treatment'],
        'subspecialty': 'maintenance',
        'measure_types': ['HR', 'median']
    },
    'DOR': {
        'aliases': ['duration of response', 'dor'],
        'subspecialty': 'maintenance',
        'measure_types': ['HR', 'median']
    },

    # --- surgical ---
    'COMPLETE_RESECTION': {
        'aliases': ['complete cytoreduction', 'complete resection',
                    'no residual disease', 'r0 resection', 'optimal cytoreduction',
                    'optimal debulking', 'complete gross resection'],
        'subspecialty': 'surgical',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RECURRENCE': {
        'aliases': ['recurrence', 'disease recurrence', 'recurrent disease',
                    'recurrence rate', 'relapse'],
        'subspecialty': 'surgical',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- mortality ---
    'OVARIAN_CANCER_MORTALITY': {
        'aliases': ['ovarian cancer mortality', 'ovarian-cancer mortality',
                    'ovarian cancer-specific mortality', 'ovarian cancer death',
                    'death from ovarian cancer', 'cancer-specific survival'],
        'subspecialty': 'mortality',
        'measure_types': ['HR', 'RR', 'IRR']
    },
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- continuous / QoL ---
    'CA125_LEVEL': {
        'aliases': ['ca-125 level', 'ca125 level', 'serum ca-125',
                    'cancer antigen 125 level', 'ca-125 concentration'],
        'subspecialty': 'systemic',
        'measure_types': ['MD', 'GMR']
    },
    'QOL': {
        'aliases': ['quality of life', 'fact-o', 'hrqol', 'eortc qlq-ov28',
                    'health-related quality of life'],
        'subspecialty': 'systemic',
        'measure_types': ['MD']
    },
}


# ============================================================
# SYSTEMIC PATTERNS
# ============================================================

SYSTEMIC_PATTERNS = {
    'detection_keywords': [
        r'first[- ]line\s+(?:chemo)?therapy', r'platinum[- ](?:sensitive|resistant|refractory)',
        r'carboplatin|cisplatin', r'paclitaxel|docetaxel', r'bevacizumab|avastin',
        r'gemcitabine', r'(?:pegylated\s+)?liposomal\s+doxorubicin|caelyx|doxil',
        r'topotecan', r'recurrent\s+ovarian', r'relapsed\s+ovarian',
        r'ca[- ]?125', r'objective\s+response',
    ],
    'endpoint_patterns': [
        (r'(?<!maintenance\s)progression[- ]?free\s+survival(?!\s+during)', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'objective\s+response\s+rate|overall\s+response\s+rate|tumou?r\s+response', 'ORR'),
        (r'(?:gcig\s+)?ca[- ]?125\s+response|ca[- ]?125\s+normali[sz]ation', 'CA125_RESPONSE'),
        (r'\bpfs2\b|second\s+progression[- ]?free\s+survival|time\s+to\s+second\s+progression',
         'PFS2'),
        (r'ca[- ]?125\s+(?:level|concentration)|serum\s+ca[- ]?125', 'CA125_LEVEL'),
        (r'quality\s+of\s+life|fact-o|hrqol|eortc\s+qlq', 'QOL'),
    ],
    'context_patterns': [
        r'recist|gcig', r'per[- ]protocol|intention[- ]to[- ]treat',
    ]
}


# ============================================================
# MAINTENANCE PATTERNS
# ============================================================

MAINTENANCE_PATTERNS = {
    'detection_keywords': [
        r'maintenance\s+(?:therapy|treatment)', r'parp\s+inhibitor',
        r'olaparib|lynparza', r'niraparib|zejula', r'rucaparib|rubraca',
        r'\bbrca\b|brca1|brca2|homologous\s+recombination\s+deficien|\bhrd\b',
        r'bevacizumab\s+maintenance',
    ],
    'endpoint_patterns': [
        (r'maintenance\s+progression[- ]?free\s+survival|'
         r'progression[- ]?free\s+survival\s+during\s+maintenance', 'MAINTENANCE_PFS'),
        (r'time\s+to\s+first\s+subsequent\s+(?:therapy|treatment)|\btfst\b', 'TFST'),
        (r'duration\s+of\s+response', 'DOR'),
    ],
    'context_patterns': [
        r'germline|somatic', r'biomarker',
    ]
}


# ============================================================
# SURGICAL PATTERNS
# ============================================================

SURGICAL_PATTERNS = {
    'detection_keywords': [
        r'cytoreduction|cytoreductive\s+surgery', r'debulking',
        r'(?:primary|interval)\s+debulking\s+surgery|\bpds\b|\bids\b',
        r'residual\s+disease', r'r0\s+resection', r'neoadjuvant\s+chemotherapy',
        r'complete\s+gross\s+resection',
    ],
    'endpoint_patterns': [
        (r'complete\s+(?:cytoreduction|gross\s+resection|resection)|'
         r'optimal\s+(?:cytoreduction|debulking)|no\s+residual\s+disease|r0\s+resection',
         'COMPLETE_RESECTION'),
        (r'recurrence|recurrent\s+disease|relapse', 'RECURRENCE'),
    ],
    'context_patterns': [
        r'figo\s+stage', r'optimal\s+vs\s+suboptimal',
    ]
}


# ============================================================
# MORTALITY PATTERNS
# ============================================================

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'ovarian\s+cancer[- ]?specific\s+mortality|ovarian[- ]cancer\s+mortality',
        r'ovarian\s+cancer\s+death|death\s+from\s+ovarian\s+cancer',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'ovarian\s+cancer[- ]?(?:specific\s+)?(?:mortality|death)|'
         r'death\s+from\s+ovarian\s+cancer|cancer[- ]specific\s+(?:mortality|survival)',
         'OVARIAN_CANCER_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [
        r'cumulative\s+incidence', r'per\s+(?:100,?000\s+)?person[- ]years',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_ovarian_cancer_subspecialty(text: str) -> Tuple[str, float]:
    """Detect ovarian-cancer trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: systemic, maintenance, surgical, mortality, general_ovarian_cancer."""
    text_lower = text.lower()
    scores = {'systemic': 0, 'maintenance': 0, 'surgical': 0, 'mortality': 0}
    for kw in SYSTEMIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['systemic'] += 1
    for kw in MAINTENANCE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['maintenance'] += 1
    for kw in SURGICAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['surgical'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_ovarian_cancer', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_ovarian_cancer_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'systemic': SYSTEMIC_PATTERNS['endpoint_patterns'],
        'maintenance': MAINTENANCE_PATTERNS['endpoint_patterns'],
        'surgical': SURGICAL_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_ovarian_cancer_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical ovarian-cancer endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in OVARIAN_CANCER_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
