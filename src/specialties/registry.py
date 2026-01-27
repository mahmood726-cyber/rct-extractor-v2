"""
Specialty Registry - Central registry for all specialty patterns and endpoints.
"""

from typing import Dict, List, Tuple, Optional, Callable
import re

from .cardiology import (
    CARDIOLOGY_ENDPOINTS,
    HEART_FAILURE_PATTERNS,
    ACS_PATTERNS,
    AF_PATTERNS,
    VALVE_PATTERNS,
    detect_cardiology_subspecialty,
    normalize_cardiology_endpoint
)

from .oncology import (
    ONCOLOGY_ENDPOINTS,
    BREAST_CANCER_PATTERNS,
    LUNG_CANCER_PATTERNS,
    GI_ONCOLOGY_PATTERNS,
    detect_oncology_subspecialty,
    normalize_oncology_endpoint
)


# ============================================================
# SPECIALTY REGISTRY
# ============================================================

SPECIALTY_REGISTRY = {
    'cardiology': {
        'subspecialties': ['heart_failure', 'acs', 'af', 'valve'],
        'detection_function': detect_cardiology_subspecialty,
        'normalizer': normalize_cardiology_endpoint,
        'endpoints': CARDIOLOGY_ENDPOINTS,
        'patterns': {
            'heart_failure': HEART_FAILURE_PATTERNS,
            'acs': ACS_PATTERNS,
            'af': AF_PATTERNS,
            'valve': VALVE_PATTERNS
        }
    },
    'oncology': {
        'subspecialties': ['breast', 'lung', 'gi', 'gu', 'heme'],
        'detection_function': detect_oncology_subspecialty,
        'normalizer': normalize_oncology_endpoint,
        'endpoints': ONCOLOGY_ENDPOINTS,
        'patterns': {
            'breast': BREAST_CANCER_PATTERNS,
            'lung': LUNG_CANCER_PATTERNS,
            'gi': GI_ONCOLOGY_PATTERNS
        }
    },
    'infectious_disease': {
        'subspecialties': ['covid', 'hiv', 'hepatitis', 'bacterial'],
        'endpoints': {
            'MORTALITY': {'aliases': ['mortality', 'death', 'all-cause mortality']},
            'HOSPITALIZATION': {'aliases': ['hospitalization', 'hospital admission']},
            'RECOVERY': {'aliases': ['recovery', 'clinical recovery', 'time to recovery']},
            'VIROLOGIC_RESPONSE': {'aliases': ['virologic response', 'viral suppression', 'undetectable']}
        }
    },
    'diabetes': {
        'subspecialties': ['t2dm', 't1dm', 'obesity'],
        'endpoints': {
            'MACE': {'aliases': ['mace', 'major adverse cardiovascular events']},
            'HBA1C': {'aliases': ['hba1c', 'glycated hemoglobin', 'a1c']},
            'WEIGHT_LOSS': {'aliases': ['weight loss', 'body weight', 'weight reduction']},
            'RENAL_COMPOSITE': {'aliases': ['renal composite', 'kidney composite', 'ckd progression']}
        }
    },
    'neurology': {
        'subspecialties': ['alzheimers', 'ms', 'parkinsons', 'stroke'],
        'endpoints': {
            'CDR_SB': {'aliases': ['cdr-sb', 'clinical dementia rating', 'cdr sum of boxes']},
            'DISABILITY_PROGRESSION': {'aliases': ['disability progression', 'edss progression']},
            'ANNUALIZED_RELAPSE_RATE': {'aliases': ['annualized relapse rate', 'arr', 'relapse rate']},
            'BRAIN_ATROPHY': {'aliases': ['brain atrophy', 'brain volume loss']}
        }
    },
    'autoimmune': {
        'subspecialties': ['ra', 'sle', 'psoriasis', 'ibd'],
        'endpoints': {
            'ACR20': {'aliases': ['acr20', 'acr 20', 'acr20 response']},
            'ACR50': {'aliases': ['acr50', 'acr 50']},
            'ACR70': {'aliases': ['acr70', 'acr 70']},
            'PASI90': {'aliases': ['pasi90', 'pasi 90', '90% improvement in pasi']},
            'SRI': {'aliases': ['sri', 'sle responder index']}
        }
    },
    'respiratory': {
        'subspecialties': ['copd', 'asthma', 'ipf'],
        'endpoints': {
            'EXACERBATION': {'aliases': ['exacerbation', 'acute exacerbation', 'copd exacerbation']},
            'FEV1': {'aliases': ['fev1', 'forced expiratory volume']},
            'FVC': {'aliases': ['fvc', 'forced vital capacity']},
            'FVC_DECLINE': {'aliases': ['fvc decline', 'annual fvc decline', 'rate of fvc decline']}
        }
    }
}


# ============================================================
# REGISTRY FUNCTIONS
# ============================================================

def detect_specialty(text: str) -> Tuple[str, str, float]:
    """
    Detect therapeutic specialty and subspecialty from text.

    Returns:
        Tuple of (specialty, subspecialty, confidence)
    """
    text_lower = text.lower()

    specialty_scores = {}

    # Keywords for each specialty
    specialty_keywords = {
        'cardiology': [
            r'heart\s+failure', r'myocardial\s+infarction', r'atrial\s+fibrillation',
            r'coronary', r'cardiovascular', r'cardiac', r'lvef', r'ejection\s+fraction',
            r'arrhythmia', r'hypertension', r'valve', r'tavr', r'pci'
        ],
        'oncology': [
            r'cancer', r'tumor', r'carcinoma', r'adenocarcinoma', r'melanoma',
            r'chemotherapy', r'immunotherapy', r'progression[- ]?free', r'pfs',
            r'response\s+rate', r'her2', r'egfr', r'pd[- ]?l1', r'checkpoint'
        ],
        'infectious_disease': [
            r'covid', r'sars[- ]?cov', r'hiv', r'aids', r'hepatitis',
            r'viral', r'bacterial', r'antiviral', r'antibiotic', r'infection'
        ],
        'diabetes': [
            r'diabetes', r'diabetic', r'hba1c', r'glucose', r'insulin',
            r'sglt2', r'glp[- ]?1', r'metformin', r'obesity', r'weight\s+loss'
        ],
        'neurology': [
            r'alzheimer', r'dementia', r'multiple\s+sclerosis', r'\bms\b',
            r'parkinson', r'stroke', r'neurological', r'cognitive', r'relapse'
        ],
        'autoimmune': [
            r'rheumatoid\s+arthritis', r'lupus', r'psoriasis', r'psoriatic',
            r'inflammatory\s+bowel', r'crohn', r'colitis', r'acr\d{2}', r'pasi'
        ],
        'respiratory': [
            r'copd', r'asthma', r'pulmonary\s+fibrosis', r'ipf',
            r'exacerbation', r'fev1', r'fvc', r'broncho', r'inhale'
        ]
    }

    for specialty, keywords in specialty_keywords.items():
        score = sum(1 for kw in keywords if re.search(kw, text_lower))
        specialty_scores[specialty] = score

    best_specialty = max(specialty_scores, key=specialty_scores.get)
    best_score = specialty_scores[best_specialty]

    if best_score == 0:
        return ('unknown', None, 0.0)

    # Detect subspecialty
    subspecialty = None
    confidence = min(best_score / 5, 1.0)

    if best_specialty == 'cardiology':
        subspecialty, conf = detect_cardiology_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'oncology':
        subspecialty, _, conf = detect_oncology_subspecialty(text)
        confidence = max(confidence, conf)

    return (best_specialty, subspecialty, confidence)


def get_specialty_patterns(specialty: str, subspecialty: str = None) -> Dict:
    """Get patterns for a specific specialty/subspecialty."""
    spec_info = SPECIALTY_REGISTRY.get(specialty, {})

    if subspecialty and 'patterns' in spec_info:
        return spec_info['patterns'].get(subspecialty, {})

    return spec_info.get('patterns', {})


def get_endpoint_normalizer(specialty: str) -> Optional[Callable]:
    """Get the endpoint normalizer function for a specialty."""
    spec_info = SPECIALTY_REGISTRY.get(specialty, {})
    return spec_info.get('normalizer')


def normalize_endpoint_by_specialty(
    endpoint: str,
    specialty: str = None,
    subspecialty: str = None
) -> str:
    """
    Normalize endpoint using specialty-specific rules.

    Falls back to generic normalization if no specialty match.
    """
    if specialty:
        normalizer = get_endpoint_normalizer(specialty)
        if normalizer:
            return normalizer(endpoint, subspecialty)

    # Generic normalization
    endpoint_lower = endpoint.lower()

    generic_mappings = {
        'PRIMARY_OUTCOME': ['primary', 'primary outcome', 'primary endpoint'],
        'SECONDARY_OUTCOME': ['secondary', 'secondary outcome'],
        'MORTALITY': ['death', 'mortality', 'survival'],
        'COMPOSITE': ['composite', 'combined']
    }

    for canonical, aliases in generic_mappings.items():
        for alias in aliases:
            if alias in endpoint_lower:
                return canonical

    return endpoint.upper()


def get_all_endpoints(specialty: str = None) -> Dict:
    """Get all endpoints, optionally filtered by specialty."""
    if specialty:
        spec_info = SPECIALTY_REGISTRY.get(specialty, {})
        return spec_info.get('endpoints', {})

    # Return all endpoints
    all_endpoints = {}
    for spec_name, spec_info in SPECIALTY_REGISTRY.items():
        endpoints = spec_info.get('endpoints', {})
        all_endpoints.update(endpoints)

    return all_endpoints
