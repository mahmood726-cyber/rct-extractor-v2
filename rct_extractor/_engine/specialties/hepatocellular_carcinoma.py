"""
Hepatocellular Carcinoma (HCC) Subspecialty Patterns and Endpoints

Per-disease profile (same shape as prostate_cancer / cervical_cancer). HCC RCTs
report a distinct endpoint vocabulary — overall and progression-free survival,
time to progression, AFP response, recurrence-free survival after curative
therapy, locoregional control — and a distinct drug set (sorafenib, lenvatinib,
atezolizumab + bevacizumab, durvalumab + tremelimumab). NOTE: HCC overlaps the
`hepatitis` keyword bucket (both mention "hepatocellular carcinoma"/"cirrhosis");
the routing keywords below are deliberately rich (BCLC, Child-Pugh, TACE, AFP,
the HCC drug set) so an HCC trial outranks the hepatitis antiviral bucket.

Subspecialties:
- systemic (advanced / BCLC-C): overall survival, progression-free survival,
  time to progression, objective response, AFP response. Agents: sorafenib,
  lenvatinib, atezolizumab + bevacizumab, durvalumab + tremelimumab, regorafenib,
  cabozantinib, ramucirumab.
- locoregional (intermediate / BCLC-B): transarterial chemoembolization (TACE),
  transarterial radioembolization (TARE / Y90), objective response (mRECIST),
  time to progression.
- curative (early / BCLC-0-A): resection, transplantation, radiofrequency /
  microwave ablation; recurrence-free survival, recurrence.
- mortality: liver-cancer-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, TTP, RFS) -> HR; binary (objective
response, AFP response, recurrence, local control) -> RR/OR/RD/HR; continuous
serum AFP -> log-normal; QoL -> MD.
"""
from typing import Dict, List, Tuple, Optional
import re

HEPATOCELLULAR_CARCINOMA_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'systemic', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'disease progression or death',
                        'progression free survival'],
            'subspecialty': 'systemic', 'measure_types': ['HR', 'median']},
    'TTP': {'aliases': ['time to progression', 'ttp', 'time to radiologic progression'],
            'subspecialty': 'systemic', 'measure_types': ['HR', 'median']},
    'ORR': {'aliases': ['objective response rate', 'orr', 'overall response rate',
                        'tumor response', 'tumour response', 'mrecist response'],
            'subspecialty': 'systemic', 'measure_types': ['OR', 'RR', 'rate']},
    'AFP_RESPONSE': {'aliases': ['afp response', 'alpha-fetoprotein response',
                                 'afp decline', 'afp normalization', 'afp normalisation'],
                     'subspecialty': 'systemic', 'measure_types': ['OR', 'RR', 'rate']},
    'RFS': {'aliases': ['recurrence-free survival', 'rfs', 'disease-free survival', 'dfs',
                        'relapse-free survival'],
            'subspecialty': 'curative', 'measure_types': ['HR', 'median']},
    'RECURRENCE': {'aliases': ['recurrence', 'tumor recurrence', 'tumour recurrence',
                               'hcc recurrence', 'recurrence rate', 'relapse'],
                   'subspecialty': 'curative', 'measure_types': ['HR', 'RR', 'OR']},
    'LOCAL_CONTROL': {'aliases': ['local control', 'local tumor control',
                                  'local tumour control', 'complete response by mrecist',
                                  'locoregional control'],
                      'subspecialty': 'locoregional', 'measure_types': ['HR', 'RR', 'OR']},
    'LIVER_CANCER_MORTALITY': {
        'aliases': ['liver cancer mortality', 'liver-cancer mortality',
                    'hcc mortality', 'liver cancer death', 'death from liver cancer',
                    'cancer-specific survival', 'liver-related mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
    'AFP_LEVEL': {'aliases': ['afp level', 'alpha-fetoprotein level', 'serum afp',
                              'afp concentration'],
                  'subspecialty': 'systemic', 'measure_types': ['MD', 'GMR']},
    'QOL': {'aliases': ['quality of life', 'fact-hep', 'hrqol', 'eortc qlq-hcc18',
                        'health-related quality of life'],
            'subspecialty': 'systemic', 'measure_types': ['MD']},
}

SYSTEMIC_PATTERNS = {
    'detection_keywords': [
        r'advanced\s+(?:hepatocellular|hcc)', r'unresectable\s+(?:hepatocellular|hcc)',
        r'sorafenib|nexavar', r'lenvatinib|lenvima', r'atezolizumab|tecentriq',
        r'bevacizumab|avastin', r'durvalumab|imfinzi', r'tremelimumab',
        r'regorafenib|stivarga', r'cabozantinib|cabometyx', r'ramucirumab|cyramza',
        r'bclc[- ]?c', r'alpha[- ]?fetoprotein|\bafp\b',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'time\s+to\s+(?:radiologic\s+)?progression', 'TTP'),
        (r'objective\s+response\s+rate|overall\s+response\s+rate|tumou?r\s+response|'
         r'mrecist\s+response', 'ORR'),
        (r'(?:alpha[- ]?fetoprotein|afp)\s+(?:response|decline|normali[sz]ation)', 'AFP_RESPONSE'),
        (r'(?:alpha[- ]?fetoprotein|afp)\s+(?:level|concentration)|serum\s+afp', 'AFP_LEVEL'),
        (r'quality\s+of\s+life|fact-hep|hrqol|eortc\s+qlq', 'QOL'),
    ],
    'context_patterns': [r'recist|mrecist', r'child[- ]?pugh']
}

LOCOREGIONAL_PATTERNS = {
    'detection_keywords': [
        r'transarterial\s+chemoembolization|\btace\b|transcatheter\s+arterial',
        r'transarterial\s+radioembolization|\btare\b|yttrium[- ]?90|\by90\b',
        r'drug[- ]eluting\s+bead', r'conventional\s+tace|\bctace\b',
        r'bclc[- ]?b|intermediate[- ]stage', r'selective\s+internal\s+radiation',
    ],
    'endpoint_patterns': [
        (r'time\s+to\s+(?:radiologic\s+)?progression', 'TTP'),
        (r'objective\s+response\s+rate|mrecist\s+response|tumou?r\s+response', 'ORR'),
        (r'local(?:[- ]?regional)?\s+(?:tumou?r\s+)?control|complete\s+response\s+by\s+mrecist',
         'LOCAL_CONTROL'),
    ],
    'context_patterns': [r'lipiodol', r'on[- ]demand|scheduled']
}

CURATIVE_PATTERNS = {
    'detection_keywords': [
        r'hepatic\s+resection|liver\s+resection|hepatectomy', r'liver\s+transplant',
        r'radiofrequency\s+ablation|\brfa\b', r'microwave\s+ablation|\bmwa\b',
        r'curative\s+(?:resection|treatment)', r'early[- ]stage\s+(?:hepatocellular|hcc)',
        r'bclc[- ]?(?:0|a)', r'adjuvant',
    ],
    'endpoint_patterns': [
        (r'recurrence[- ]?free\s+survival|disease[- ]?free\s+survival|'
         r'relapse[- ]?free\s+survival', 'RFS'),
        (r'(?:tumou?r\s+|hcc\s+)?recurrence|recurrent\s+disease|relapse', 'RECURRENCE'),
    ],
    'context_patterns': [r'milan\s+criteria', r'microvascular\s+invasion']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'liver\s+cancer\s+mortality|liver[- ]cancer\s+mortality|hcc\s+mortality',
        r'liver\s+cancer\s+death|death\s+from\s+liver\s+cancer',
        r'liver[- ]related\s+mortality', r'cancer[- ]specific\s+(?:mortality|survival)',
        r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'liver\s+cancer\s+(?:mortality|death)|hcc\s+mortality|'
         r'death\s+from\s+liver\s+cancer|liver[- ]related\s+mortality|'
         r'cancer[- ]specific\s+(?:mortality|survival)', 'LIVER_CANCER_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_hepatocellular_carcinoma_subspecialty(text: str) -> Tuple[str, float]:
    """Detect HCC trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: systemic, locoregional, curative, mortality, general_hepatocellular_carcinoma."""
    text_lower = text.lower()
    scores = {'systemic': 0, 'locoregional': 0, 'curative': 0, 'mortality': 0}
    for kw in SYSTEMIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['systemic'] += 1
    for kw in LOCOREGIONAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['locoregional'] += 1
    for kw in CURATIVE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['curative'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_hepatocellular_carcinoma', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_hepatocellular_carcinoma_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'systemic': SYSTEMIC_PATTERNS['endpoint_patterns'],
        'locoregional': LOCOREGIONAL_PATTERNS['endpoint_patterns'],
        'curative': CURATIVE_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_hepatocellular_carcinoma_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical HCC endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in HEPATOCELLULAR_CARCINOMA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
