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

from .malaria import (
    MALARIA_ENDPOINTS,
    TREATMENT_PATTERNS as MALARIA_TREATMENT_PATTERNS,
    PREVENTION_PATTERNS as MALARIA_PREVENTION_PATTERNS,
    SEVERE_PATTERNS as MALARIA_SEVERE_PATTERNS,
    TRANSMISSION_PATTERNS as MALARIA_TRANSMISSION_PATTERNS,
    detect_malaria_subspecialty,
    normalize_malaria_endpoint
)

from .hiv import (
    HIV_ENDPOINTS,
    TREATMENT_PATTERNS as HIV_TREATMENT_PATTERNS,
    PREVENTION_PATTERNS as HIV_PREVENTION_PATTERNS,
    PMTCT_PATTERNS as HIV_PMTCT_PATTERNS,
    COINFECTION_PATTERNS as HIV_COINFECTION_PATTERNS,
    detect_hiv_subspecialty,
    normalize_hiv_endpoint
)

from .typhoid import (
    TYPHOID_ENDPOINTS,
    TREATMENT_PATTERNS as TYPHOID_TREATMENT_PATTERNS,
    VACCINE_PATTERNS as TYPHOID_VACCINE_PATTERNS,
    RESISTANCE_PATTERNS as TYPHOID_RESISTANCE_PATTERNS,
    COMPLICATIONS_PATTERNS as TYPHOID_COMPLICATIONS_PATTERNS,
    detect_typhoid_subspecialty,
    normalize_typhoid_endpoint
)

from .diabetes import (
    DIABETES_ENDPOINTS,
    GLYCEMIC_PATTERNS as DIABETES_GLYCEMIC_PATTERNS,
    CARDIORENAL_PATTERNS as DIABETES_CARDIORENAL_PATTERNS,
    HYPOGLYCEMIA_PATTERNS as DIABETES_HYPOGLYCEMIA_PATTERNS,
    COMPLICATIONS_PATTERNS as DIABETES_COMPLICATIONS_PATTERNS,
    detect_diabetes_subspecialty,
    normalize_diabetes_endpoint
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
    'malaria': {
        'subspecialties': ['treatment', 'prevention', 'severe', 'transmission'],
        'detection_function': detect_malaria_subspecialty,
        'normalizer': normalize_malaria_endpoint,
        'endpoints': MALARIA_ENDPOINTS,
        'patterns': {
            'treatment': MALARIA_TREATMENT_PATTERNS,
            'prevention': MALARIA_PREVENTION_PATTERNS,
            'severe': MALARIA_SEVERE_PATTERNS,
            'transmission': MALARIA_TRANSMISSION_PATTERNS
        }
    },
    'hiv': {
        'subspecialties': ['treatment', 'prevention', 'pmtct', 'coinfection'],
        'detection_function': detect_hiv_subspecialty,
        'normalizer': normalize_hiv_endpoint,
        'endpoints': HIV_ENDPOINTS,
        'patterns': {
            'treatment': HIV_TREATMENT_PATTERNS,
            'prevention': HIV_PREVENTION_PATTERNS,
            'pmtct': HIV_PMTCT_PATTERNS,
            'coinfection': HIV_COINFECTION_PATTERNS
        }
    },
    'typhoid': {
        'subspecialties': ['treatment', 'vaccine', 'resistance', 'complications'],
        'detection_function': detect_typhoid_subspecialty,
        'normalizer': normalize_typhoid_endpoint,
        'endpoints': TYPHOID_ENDPOINTS,
        'patterns': {
            'treatment': TYPHOID_TREATMENT_PATTERNS,
            'vaccine': TYPHOID_VACCINE_PATTERNS,
            'resistance': TYPHOID_RESISTANCE_PATTERNS,
            'complications': TYPHOID_COMPLICATIONS_PATTERNS
        }
    },
    'infectious_disease': {
        'subspecialties': ['covid', 'hepatitis', 'bacterial'],
        'endpoints': {
            'MORTALITY': {'aliases': ['mortality', 'death', 'all-cause mortality']},
            'HOSPITALIZATION': {'aliases': ['hospitalization', 'hospital admission']},
            'RECOVERY': {'aliases': ['recovery', 'clinical recovery', 'time to recovery']},
            'VIROLOGIC_RESPONSE': {'aliases': ['virologic response', 'viral suppression', 'undetectable']}
        }
    },
    'diabetes': {
        'subspecialties': ['glycemic', 'cardiorenal', 'hypoglycemia', 'complications'],
        'detection_function': detect_diabetes_subspecialty,
        'normalizer': normalize_diabetes_endpoint,
        'endpoints': DIABETES_ENDPOINTS,
        'patterns': {
            'glycemic': DIABETES_GLYCEMIC_PATTERNS,
            'cardiorenal': DIABETES_CARDIORENAL_PATTERNS,
            'hypoglycemia': DIABETES_HYPOGLYCEMIA_PATTERNS,
            'complications': DIABETES_COMPLICATIONS_PATTERNS
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
        'malaria': [
            r'malaria', r'plasmodium', r'falciparum', r'vivax',
            r'antimalarial', r'artemisinin', r'\bacpr\b', r'parasit(?:ae|e)mia',
            r'parasite\s+clearance', r'recrudescen', r'gametocyt',
            r'artemether[- ]?lumefantrine', r'dihydroartemisinin',
            r'sulfadoxine[- ]?pyrimethamine', r'rts,?\s?s', r'\bsmc\b',
            r'chemoprevention'
        ],
        'hiv': [
            r'\bhiv\b', r'\baids\b', r'antiretroviral', r'\bart\b', r'\bhaart\b',
            r'viral\s+(?:load\s+)?suppression', r'virologic', r'\bcd4\b',
            r'pre[- ]?exposure\s+prophylaxis', r'\bprep\b', r'dolutegravir',
            r'tenofovir|emtricitabine', r'mother[- ]to[- ]child\s+transmission',
            r'efavirenz', r'undetectable'
        ],
        'typhoid': [
            r'typhoid', r'enteric\s+fever', r'paratyphoid', r'paratyphi',
            r'salmonella\s+typhi', r'\bs\.?\s*typhi\b', r'typhoid\s+conjugate\s+vaccine',
            r'\btcv\b', r'\bty21a\b', r'vi\s+polysaccharide', r'anti[- ]vi',
            r'fever\s+clearance\s+time', r'widal'
        ],
        'infectious_disease': [
            r'covid', r'sars[- ]?cov', r'hepatitis',
            r'viral', r'bacterial', r'antiviral', r'antibiotic', r'infection'
        ],
        'diabetes': [
            r'diabetes', r'diabetic', r'type\s+2\s+diabetes|\bt2dm\b',
            r'hba1c', r'glycated\s+ha?emoglobin', r'fasting\s+plasma\s+glucose',
            r'glucose', r'insulin', r'glyca?emic', r'hypoglyca?emia',
            r'sglt[- ]?2', r'\w*gliflozin', r'glp[- ]?1', r'\w*glutide', r'tirzepatide',
            r'\w*gliptin', r'dpp[- ]?4', r'metformin', r'sulfonylurea|sulphonylurea',
            r'pioglitazone|rosiglitazone', r'obesity', r'weight\s+loss'
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
    elif best_specialty == 'malaria':
        subspecialty, conf = detect_malaria_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'hiv':
        subspecialty, conf = detect_hiv_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'typhoid':
        subspecialty, conf = detect_typhoid_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'diabetes':
        subspecialty, conf = detect_diabetes_subspecialty(text)
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
