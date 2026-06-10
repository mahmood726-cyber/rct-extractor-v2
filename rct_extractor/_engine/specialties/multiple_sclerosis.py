"""
Multiple Sclerosis Subspecialty Patterns and Endpoints

Built for the same meta-analysis extraction workflow as the malaria / TB / HIV
profiles. MS RCTs report a distinct endpoint vocabulary (annualized relapse rate,
confirmed disability progression on EDSS, gadolinium-enhancing and new/enlarging
T2 lesions, brain atrophy, NEDA, SDMT, timed 25-foot walk) that the generic
effect-size engine does not recognise.

Subspecialties (mapped onto the registry's generic pattern slots):
- relapsing  (TREATMENT slot): disease-modifying therapy for relapsing-remitting
  MS — interferon beta, glatiramer, S1P modulators (fingolimod/ozanimod/ponesimod),
  fumarates, teriflunomide, natalizumab, anti-CD20 (ocrelizumab/ofatumumab/
  rituximab), cladribine, alemtuzumab. Endpoints: ARR, relapse, Gd+ / new-T2
  lesions, NEDA.
- progressive (DRUG_RESISTANT slot): SPMS / PPMS — confirmed disability
  progression (CDP) on EDSS, siponimod, ocrelizumab, BTK inhibitors (tolebrutinib).
- symptomatic (PREVENTION slot): walking speed (fampridine/dalfampridine),
  spasticity (nabiximols), fatigue, bladder.
- acute_relapse (LATENT slot): acute relapse management — corticosteroids,
  plasma exchange; relapse recovery.

Effect measures: ARR -> rate ratio (IRR); relapse / CDP / time-to-event -> HR/RR;
lesion counts -> rate ratio / RR; NEDA / relapse-free -> RR/OR; EDSS / SDMT /
T25FW / brain-atrophy change -> mean difference via the core engine.
"""
from typing import Dict, List, Tuple, Optional
import re

MULTIPLE_SCLEROSIS_ENDPOINTS = {
    'ARR': {
        'aliases': ['annualized relapse rate', 'annualised relapse rate',
                    'annual relapse rate', 'adjusted annualized relapse rate', 'arr'],
        'subspecialty': 'relapsing',
        'measure_types': ['IRR', 'RR']
    },
    'RELAPSE': {
        'aliases': ['relapse', 'confirmed relapse', 'protocol-defined relapse',
                    'time to first relapse', 'relapse risk', 'proportion relapse-free',
                    'relapse-free', 'relapse free'],
        'subspecialty': 'relapsing',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'CDP': {
        'aliases': ['confirmed disability progression', 'disability progression',
                    'edss progression', '3-month confirmed disability progression',
                    '6-month confirmed disability progression', 'cdp',
                    'time to confirmed disability progression',
                    'sustained disability progression', 'disability worsening',
                    'confirmed disability worsening', 'progression of disability'],
        'subspecialty': 'progressive',
        'measure_types': ['HR', 'RR']
    },
    'EDSS_CHANGE': {
        'aliases': ['edss change', 'change in edss', 'expanded disability status scale',
                    'edss score change', 'mean edss change'],
        'subspecialty': 'progressive',
        'measure_types': ['MD']
    },
    'GAD_LESIONS': {
        'aliases': ['gadolinium-enhancing lesions', 'gd-enhancing lesions',
                    'gadolinium enhancing lesions', 'gd+ lesions',
                    't1 gadolinium-enhancing', 'enhancing lesions'],
        'subspecialty': 'relapsing',
        'measure_types': ['RR', 'IRR', 'MD']
    },
    'T2_LESIONS': {
        'aliases': ['new or enlarging t2 lesions', 'new t2 lesions',
                    'new/enlarging t2 lesions', 't2 lesions', 't2 lesion count',
                    'new or newly enlarging t2'],
        'subspecialty': 'relapsing',
        'measure_types': ['RR', 'IRR', 'MD']
    },
    'BRAIN_ATROPHY': {
        'aliases': ['brain atrophy', 'brain volume loss', 'percentage brain volume change',
                    'whole brain volume', 'brain volume change', 'pbvc'],
        'subspecialty': 'progressive',
        'measure_types': ['MD']
    },
    'NEDA': {
        'aliases': ['neda', 'no evidence of disease activity', 'neda-3', 'neda-4'],
        'subspecialty': 'relapsing',
        'measure_types': ['RR', 'OR']
    },
    'SDMT': {
        'aliases': ['sdmt', 'symbol digit modalities test', 'cognitive processing speed'],
        'subspecialty': 'progressive',
        'measure_types': ['MD']
    },
    'T25FW': {
        'aliases': ['timed 25-foot walk', 't25fw', 'timed 25 foot walk',
                    'walking speed', '25-foot walk', 'walking ability'],
        'subspecialty': 'symptomatic',
        'measure_types': ['MD', 'RR']
    },
    'FATIGUE': {
        'aliases': ['fatigue', 'fatigue severity scale', 'modified fatigue impact scale',
                    'mfis', 'fss'],
        'subspecialty': 'symptomatic',
        'measure_types': ['MD', 'SMD']
    },
    'SPASTICITY': {
        'aliases': ['spasticity', 'ashworth scale', 'modified ashworth',
                    'spasticity numerical rating'],
        'subspecialty': 'symptomatic',
        'measure_types': ['MD', 'RR']
    },
    'RELAPSE_RECOVERY': {
        'aliases': ['relapse recovery', 'recovery from relapse', 'complete recovery',
                    'functional recovery', 'improvement after relapse'],
        'subspecialty': 'acute_relapse',
        'measure_types': ['RR', 'OR']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'serious adverse events', 'serious adverse event',
                    'treatment-emergent adverse events', 'infusion-related reactions',
                    'discontinuation due to adverse'],
        'subspecialty': 'relapsing',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'overall survival'],
        'subspecialty': 'progressive',
        'measure_types': ['HR', 'RR', 'OR']
    },
}


TREATMENT_PATTERNS = {  # = relapsing
    'detection_keywords': [
        r'relapsing[- ]remitting|\brrms\b|relapsing\s+ms|relapsing\s+multiple\s+sclerosis',
        r'annuali[sz]ed\s+relapse\s+rate|\barr\b|relapse\s+rate',
        r'interferon\s+beta|glatiramer|natalizumab|fingolimod|ozanimod|ponesimod|'
        r'siponimod|dimethyl\s+fumarate|diroximel|teriflunomide|cladribine|'
        r'ocrelizumab|ofatumumab|rituximab|alemtuzumab|ublituximab',
        r'gadolinium[- ]enhancing|new\s+(?:or\s+(?:newly\s+)?enlarging\s+)?t2|\bneda\b',
        r'disease[- ]modifying\s+therapy|\bdmt\b',
    ],
    'endpoint_patterns': [
        (r'annuali[sz]ed\s+relapse\s+rate|\barr\b|annual\s+relapse\s+rate', 'ARR'),
        (r'gadolinium[- ]enhancing\s+lesions?|gd[- +]enhancing|enhancing\s+lesions?',
         'GAD_LESIONS'),
        (r'new\s+(?:or\s+(?:newly\s+)?enlarging\s+)?t2\s+lesions?|t2\s+lesion', 'T2_LESIONS'),
        (r'no\s+evidence\s+of\s+disease\s+activity|\bneda(?:-[34])?\b', 'NEDA'),
        (r'proportion\s+relapse[- ]free|relapse[- ]free|time\s+to\s+(?:first\s+)?relapse|'
         r'confirmed\s+relapse|\brelapse\b', 'RELAPSE'),
        (r'serious\s+adverse\s+events?|infusion[- ]related|\badverse\s+events?\b',
         'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'over\s+\d+\s+years', r'per\s+year', r'mri\s+activity', r'double[- ]blind',
    ]
}


DRUG_RESISTANT_PATTERNS = {  # = progressive
    'detection_keywords': [
        r'secondary\s+progressive|\bspms\b|primary\s+progressive|\bppms\b|'
        r'progressive\s+multiple\s+sclerosis|progressive\s+ms',
        r'confirmed\s+disability\s+progression|disability\s+progression|edss\s+progression|\bcdp\b',
        r'siponimod|tolebrutinib|fenebrutinib|masitinib|btk\s+inhibitor',
        r'expanded\s+disability\s+status\s+scale|\bedss\b',
        r'brain\s+atrophy|brain\s+volume',
    ],
    'endpoint_patterns': [
        (r'(?:3|6|three|six)[- ]month\s+confirmed\s+disability\s+progression|'
         r'confirmed\s+disability\s+(?:progression|worsening)|disability\s+progression|'
         r'edss\s+progression|sustained\s+disability|\bcdp\b', 'CDP'),
        (r'change\s+in\s+edss|edss\s+(?:score\s+)?change|expanded\s+disability\s+status',
         'EDSS_CHANGE'),
        (r'brain\s+atrophy|brain\s+volume(?:\s+loss|\s+change)?|percentage\s+brain\s+volume|'
         r'\bpbvc\b', 'BRAIN_ATROPHY'),
        (r'\bsdmt\b|symbol\s+digit\s+modalities|cognitive\s+processing\s+speed', 'SDMT'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)', 'MORTALITY'),
    ],
    'context_patterns': [
        r'wheelchair|ambulation', r'time\s+to\s+(?:6|six)[- ]month',
    ]
}


PREVENTION_PATTERNS = {  # = symptomatic
    'detection_keywords': [
        r'fampridine|dalfampridine|4[- ]aminopyridine',
        r'nabiximols|cannabinoid|baclofen',
        r'walking\s+speed|timed\s+25[- ]foot\s+walk|\bt25fw\b|ambulation',
        r'fatigue|modified\s+fatigue\s+impact|fatigue\s+severity\s+scale',
        r'spasticity|ashworth', r'bladder|urinary\s+(?:incontinence|symptoms)',
    ],
    'endpoint_patterns': [
        (r'timed\s+25[- ]foot\s+walk|\bt25fw\b|walking\s+speed|25[- ]foot\s+walk|'
         r'walking\s+ability', 'T25FW'),
        (r'\bfatigue\b|fatigue\s+severity|modified\s+fatigue\s+impact|\bmfis\b|\bfss\b',
         'FATIGUE'),
        (r'\bspasticity\b|ashworth', 'SPASTICITY'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'responder', r'symptom\s+(?:relief|management)', r'patient[- ]reported',
    ]
}


LATENT_PATTERNS = {  # = acute_relapse
    'detection_keywords': [
        r'acute\s+relapse|acute\s+exacerbation|relapse\s+treatment',
        r'methylprednisolone|corticosteroid|plasma\s+exchange|plasmapheresis',
        r'optic\s+neuritis|relapse\s+recovery|recovery\s+from\s+relapse',
        r'high[- ]dose\s+steroid',
    ],
    'endpoint_patterns': [
        (r'relapse\s+recovery|recovery\s+from\s+relapse|complete\s+recovery|'
         r'functional\s+recovery|improvement\s+after\s+relapse', 'RELAPSE_RECOVERY'),
        (r'change\s+in\s+edss|edss\s+(?:score\s+)?change', 'EDSS_CHANGE'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'days\s+after\s+onset', r'intravenous\s+(?:methylprednisolone|steroid)',
    ]
}


def detect_multiple_sclerosis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect MS trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: relapsing, progressive, symptomatic, acute_relapse, general_ms."""
    text_lower = text.lower()
    scores = {'relapsing': 0, 'progressive': 0, 'symptomatic': 0, 'acute_relapse': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['relapsing'] += 1
    for kw in DRUG_RESISTANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['progressive'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['symptomatic'] += 1
    for kw in LATENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['acute_relapse'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_ms', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_multiple_sclerosis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'relapsing': TREATMENT_PATTERNS['endpoint_patterns'],
        'progressive': DRUG_RESISTANT_PATTERNS['endpoint_patterns'],
        'symptomatic': PREVENTION_PATTERNS['endpoint_patterns'],
        'acute_relapse': LATENT_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_multiple_sclerosis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical MS endpoint, preferring the LONGEST matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in MULTIPLE_SCLEROSIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
