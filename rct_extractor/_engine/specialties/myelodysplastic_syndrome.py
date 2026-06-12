"""
Myelodysplastic Syndrome (MDS) Subspecialty Patterns and Endpoints

Per-disease profile (same shape as leukaemia / lymphoma). DISTINCT from the
`leukaemia` specialty (AML/ALL/CLL/CML), though MDS can transform to AML. MDS RCTs
report a haematology endpoint vocabulary built on transfusion independence,
haematologic improvement, and survival, across risk-stratified settings.

Subspecialties:
- lower_risk (low / intermediate-1 risk, IPSS-R very-low to intermediate):
  red-cell transfusion independence, haematologic improvement. Agents:
  luspatercept, erythropoiesis-stimulating agents (epoetin / darbepoetin),
  lenalidomide (del(5q)), imetelstat.
- higher_risk (high / intermediate-2 risk MDS): overall survival, complete
  remission, AML-free survival. Agents: azacitidine, decitabine, venetoclax
  combinations.
- response (haematologic improvement / transfusion independence, any setting):
  RBC transfusion independence, haematologic improvement, complete remission,
  marrow complete remission.
- mortality: MDS mortality, AML transformation, all-cause mortality.

British/American spelling: ha?ematolog (haematologic/hematologic), ana?emia
(anaemia/anemia) handled in the keyword patterns.

Effect measures: time-to-event (OS, AML-free survival) -> HR; binary (transfusion
independence, haematologic improvement, complete remission) -> RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

MYELODYSPLASTIC_SYNDROME_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'higher_risk', 'measure_types': ['HR', 'median', 'rate']},
    'RBC_TI': {'aliases': ['transfusion independence', 'rbc transfusion independence',
                           'red blood cell transfusion independence', 'rbc-ti',
                           'red-cell transfusion independence', 'transfusion-independence'],
               'subspecialty': 'lower_risk', 'measure_types': ['OR', 'RR', 'RD', 'rate']},
    'HI': {'aliases': ['haematologic improvement', 'hematologic improvement',
                       'haematological improvement', 'hematological improvement',
                       'erythroid response'],
           'subspecialty': 'response', 'measure_types': ['OR', 'RR', 'RD', 'rate']},
    'CR_RATE': {'aliases': ['complete remission', 'complete response', 'cr rate',
                            'marrow complete remission', 'complete remission rate'],
                'subspecialty': 'higher_risk', 'measure_types': ['OR', 'RR', 'RD']},
    'AML_FREE': {'aliases': ['aml-free survival', 'leukaemia-free survival',
                             'leukemia-free survival', 'progression to aml',
                             'aml transformation', 'time to aml'],
                 'subspecialty': 'higher_risk', 'measure_types': ['HR', 'median']},
    'MDS_MORTALITY': {
        'aliases': ['mds mortality', 'mds-specific mortality', 'myelodysplastic mortality',
                    'disease-specific mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
}

LOWER_RISK_PATTERNS = {
    'detection_keywords': [
        r'low(?:er)?[- ]risk\s+(?:mds|myelodysplastic)',
        r'intermediate[- ]1\s+risk|ipss[- ]r?\s+(?:very[- ]low|low|intermediate)',
        r'luspatercept|reblozyl', r'erythropoiesis[- ]stimulating\s+agent|\besa\b|'
        r'epoetin|darbepoetin', r'ring(?:ed)?\s+sideroblast|mds[- ]rs',
        r'lenalidomide.{0,20}del\s*\(?5q\)?|del\s*\(?5q\)?', r'imetelstat|rytelo',
    ],
    'endpoint_patterns': [
        (r'(?:rbc\s+|red[- ](?:blood[- ])?cell\s+)?transfusion[- ]independenc', 'RBC_TI'),
        (r'h(?:a)?ematolog(?:ic|ical)\s+improvement|erythroid\s+response', 'HI'),
    ],
    'context_patterns': [r'serum\s+erythropoietin', r'transfusion\s+burden']
}

HIGHER_RISK_PATTERNS = {
    'detection_keywords': [
        r'high(?:er)?[- ]risk\s+(?:mds|myelodysplastic)',
        r'intermediate[- ]2\s+risk|ipss[- ]r?\s+(?:high|very[- ]high)',
        r'azacitidine|vidaza', r'decitabine|dacogen', r'hypomethylating\s+agent|\bhma\b',
        r'venetoclax', r'excess\s+blasts|mds[- ]eb',
    ],
    'endpoint_patterns': [
        (r'overall\s+survival', 'OS'),
        (r'(?:marrow\s+)?complete\s+remission|complete\s+response', 'CR_RATE'),
        (r'aml[- ]free\s+survival|leuk(?:a)?emia[- ]free\s+survival|'
         r'(?:progression|transformation)\s+to\s+aml|time\s+to\s+aml', 'AML_FREE'),
    ],
    'context_patterns': [r'bone\s+marrow\s+blast', r'allogeneic\s+(?:stem[- ]cell\s+)?transplant']
}

RESPONSE_PATTERNS = {
    'detection_keywords': [
        r'transfusion[- ]independenc', r'h(?:a)?ematolog(?:ic|ical)\s+improvement',
        r'erythroid\s+response', r'\brbc[- ]ti\b', r'(?:marrow\s+)?complete\s+remission',
        r'iwg\s+(?:2006\s+)?(?:response\s+)?criteria', r'overall\s+h(?:a)?ematologic\s+response',
    ],
    'endpoint_patterns': [
        (r'(?:rbc\s+|red[- ](?:blood[- ])?cell\s+)?transfusion[- ]independenc', 'RBC_TI'),
        (r'h(?:a)?ematolog(?:ic|ical)\s+improvement|erythroid\s+response', 'HI'),
        (r'(?:marrow\s+)?complete\s+remission|complete\s+response', 'CR_RATE'),
    ],
    'context_patterns': [r'\b8[- ]week\b|\b24[- ]week\b', r'transfusion\s+independence\s+rate']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'mds[- ]?specific\s+mortality|myelodysplastic\s+mortality',
        r'disease[- ]specific\s+(?:mortality|survival)',
        r'aml\s+transformation|leuk(?:a)?emic\s+transformation', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'mds[- ]?(?:specific\s+)?mortality|myelodysplastic\s+mortality|'
         r'disease[- ]specific\s+(?:mortality|survival)', 'MDS_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_myelodysplastic_syndrome_subspecialty(text: str) -> Tuple[str, float]:
    """Detect MDS trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: lower_risk, higher_risk, response, mortality, general_mds."""
    text_lower = text.lower()
    scores = {'lower_risk': 0, 'higher_risk': 0, 'response': 0, 'mortality': 0}
    for kw in LOWER_RISK_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['lower_risk'] += 1
    for kw in HIGHER_RISK_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['higher_risk'] += 1
    for kw in RESPONSE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['response'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_mds', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_myelodysplastic_syndrome_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'lower_risk': LOWER_RISK_PATTERNS['endpoint_patterns'],
        'higher_risk': HIGHER_RISK_PATTERNS['endpoint_patterns'],
        'response': RESPONSE_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_myelodysplastic_syndrome_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical MDS endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in MYELODYSPLASTIC_SYNDROME_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
