"""
Multiple Myeloma Subspecialty Patterns and Endpoints

Per-disease profile (same shape as lymphoma / leukaemia). Multiple myeloma RCTs
report a distinct endpoint vocabulary built around depth of response (overall
response, VGPR, complete response, MRD-negativity) and time-to-event survival
(progression-free survival, overall survival), across clinically distinct
treatment settings.

Subspecialties:
- newly_diagnosed (NDMM, transplant-eligible & ineligible): progression-free
  survival, overall survival, complete response, MRD-negativity. Agents:
  bortezomib-lenalidomide-dexamethasone (VRd), daratumumab combinations
  (D-VRd / D-Rd), carfilzomib-lenalidomide-dexamethasone (KRd), thalidomide,
  melphalan-prednisone, autologous stem-cell transplant (ASCT).
- relapsed_refractory (RRMM): progression-free survival, overall response,
  overall survival, time to progression. Agents: daratumumab, isatuximab,
  carfilzomib, pomalidomide, elotuzumab, selinexor, belantamab mafodotin,
  CAR-T (idecabtagene vicleucel, ciltacabtagene autoleucel), bispecific
  antibodies (teclistamab, talquetamab, elranatamab).
- response (depth of response, any setting): overall response rate, very good
  partial response, complete / stringent complete response, MRD-negativity.
- mortality: myeloma-specific mortality, all-cause mortality.

Effect measures: time-to-event (OS, PFS, TTP) -> HR; binary (ORR, VGPR, CR,
MRD-negativity) -> RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

MULTIPLE_MYELOMA_ENDPOINTS = {
    'OS': {'aliases': ['overall survival', 'os', 'death from any cause'],
           'subspecialty': 'newly_diagnosed', 'measure_types': ['HR', 'median', 'rate']},
    'PFS': {'aliases': ['progression-free survival', 'pfs', 'progression free survival',
                        'disease progression or death'],
            'subspecialty': 'newly_diagnosed', 'measure_types': ['HR', 'median']},
    'TTP': {'aliases': ['time to progression', 'ttp', 'time to disease progression'],
            'subspecialty': 'relapsed_refractory', 'measure_types': ['HR', 'median']},
    'ORR': {'aliases': ['overall response rate', 'orr', 'objective response rate',
                        'overall response', 'at least a partial response'],
            'subspecialty': 'response', 'measure_types': ['OR', 'RR', 'rate']},
    'VGPR': {'aliases': ['very good partial response', 'vgpr',
                         'very good partial response or better', '>=vgpr', 'at least vgpr'],
             'subspecialty': 'response', 'measure_types': ['OR', 'RR', 'RD']},
    'CR_RATE': {'aliases': ['complete response rate', 'complete response', 'cr rate',
                            'stringent complete response', 'scr', 'complete remission',
                            'complete response or better'],
                'subspecialty': 'response', 'measure_types': ['OR', 'RR', 'RD']},
    'MRD_NEG': {'aliases': ['mrd negativity', 'mrd-negativity', 'minimal residual disease',
                            'mrd-negative', 'mrd negative', 'measurable residual disease',
                            'undetectable mrd'],
                'subspecialty': 'response', 'measure_types': ['OR', 'RR', 'RD']},
    'MM_MORTALITY': {
        'aliases': ['myeloma mortality', 'myeloma-specific mortality',
                    'myeloma death', 'death from myeloma', 'cancer-specific mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'IRR']},
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'overall mortality', 'all-cause death',
                    'total mortality'],
        'subspecialty': 'mortality', 'measure_types': ['HR', 'RR', 'OR']},
}

NEWLY_DIAGNOSED_PATTERNS = {
    'detection_keywords': [
        r'newly[- ]diagnosed\s+(?:multiple\s+)?myeloma|\bndmm\b',
        r'transplant[- ](?:eligible|ineligible)', r'autologous\s+stem[- ]cell\s+transplant|\basct\b',
        r'\bvrd\b|bortezomib[, /-]+lenalidomide[, /-]+dexamethasone',
        r'\bkrd\b|carfilzomib[, /-]+lenalidomide', r'\bd[- ]?vrd\b|daratumumab[, /-]+(?:bortezomib|vrd)',
        r'melphalan[- ]+prednisone|\bmpt\b|\bvmp\b', r'maintenance\s+lenalidomide',
        r'induction\s+therapy', r'thalidomide',
    ],
    'endpoint_patterns': [
        (r'(?:modified\s+)?progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'(?:stringent\s+)?complete\s+response|complete\s+remission', 'CR_RATE'),
        (r'(?:mrd|minimal\s+residual\s+disease|measurable\s+residual\s+disease)[- ]?negativ',
         'MRD_NEG'),
    ],
    'context_patterns': [r'\biss\s+stage|international\s+staging\s+system', r'cytogenetic\s+risk']
}

RELAPSED_REFRACTORY_PATTERNS = {
    'detection_keywords': [
        r'relapsed(?:\s+(?:or|/|and))?\s+refractory\s+(?:multiple\s+)?myeloma|\brrmm\b',
        r'relapsed\s+(?:multiple\s+)?myeloma', r'lenalidomide[- ]refractory',
        r'daratumumab', r'isatuximab', r'pomalidomide', r'carfilzomib', r'elotuzumab',
        r'selinexor', r'belantamab(?:\s+mafodotin)?', r'\bbcma\b',
        r'idecabtagene(?:\s+vicleucel)?|ide[- ]?cel|ciltacabtagene(?:\s+autoleucel)?|cilta[- ]?cel',
        r'teclistamab|talquetamab|elranatamab|bispecific',
        r'previous\s+lines?\s+of\s+therapy|prior\s+lines?\s+of\s+therapy',
    ],
    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'time\s+to\s+(?:disease\s+)?progression', 'TTP'),
        (r'overall\s+response(?:\s+rate)?', 'ORR'),
        (r'overall\s+survival', 'OS'),
    ],
    'context_patterns': [r'triple[- ]class\s+(?:exposed|refractory)', r'penta[- ]refractory']
}

RESPONSE_PATTERNS = {
    'detection_keywords': [
        r'overall\s+response\s+rate|\borr\b', r'very\s+good\s+partial\s+response|\bvgpr\b',
        r'stringent\s+complete\s+response|\bscr\b', r'complete\s+response(?:\s+or\s+better)?',
        r'(?:mrd|minimal\s+residual\s+disease|measurable\s+residual\s+disease)[- ]?negativ',
        r'depth\s+of\s+response', r'imwg\s+(?:response\s+)?criteria',
        r'partial\s+response\s+or\s+better',
    ],
    'endpoint_patterns': [
        (r'overall\s+response(?:\s+rate)?|objective\s+response', 'ORR'),
        (r'very\s+good\s+partial\s+response|\bvgpr\b', 'VGPR'),
        (r'(?:stringent\s+)?complete\s+response(?:\s+rate)?|complete\s+remission', 'CR_RATE'),
        (r'(?:mrd|minimal\s+residual\s+disease|measurable\s+residual\s+disease)[- ]?negativ'
         r'\w*|undetectable\s+mrd', 'MRD_NEG'),
    ],
    'context_patterns': [r'\b10\^-?[56]\b|10[- ]?5|10[- ]?6', r'next[- ]generation\s+sequencing']
}

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'myeloma[- ]?specific\s+mortality|myeloma\s+mortality',
        r'myeloma\s+death|death\s+from\s+myeloma',
        r'cancer[- ]specific\s+(?:mortality|survival)', r'all[- ]cause\s+mortality',
    ],
    'endpoint_patterns': [
        (r'myeloma[- ]?(?:specific\s+)?(?:mortality|death)|death\s+from\s+myeloma|'
         r'cancer[- ]specific\s+(?:mortality|survival)', 'MM_MORTALITY'),
        (r'all[- ]cause\s+(?:mortality|death)|overall\s+mortality|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
    ],
    'context_patterns': [r'cumulative\s+incidence']
}


def detect_multiple_myeloma_subspecialty(text: str) -> Tuple[str, float]:
    """Detect multiple myeloma trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: newly_diagnosed, relapsed_refractory, response, mortality,
    general_myeloma."""
    text_lower = text.lower()
    scores = {'newly_diagnosed': 0, 'relapsed_refractory': 0, 'response': 0, 'mortality': 0}
    for kw in NEWLY_DIAGNOSED_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['newly_diagnosed'] += 1
    for kw in RELAPSED_REFRACTORY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['relapsed_refractory'] += 1
    for kw in RESPONSE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['response'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_myeloma', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_multiple_myeloma_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'newly_diagnosed': NEWLY_DIAGNOSED_PATTERNS['endpoint_patterns'],
        'relapsed_refractory': RELAPSED_REFRACTORY_PATTERNS['endpoint_patterns'],
        'response': RESPONSE_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_multiple_myeloma_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical multiple myeloma endpoint (longest alias wins)."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in MULTIPLE_MYELOMA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
