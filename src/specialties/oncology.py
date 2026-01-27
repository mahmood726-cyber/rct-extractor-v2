"""
Oncology Subspecialty Patterns and Endpoints

Subspecialties:
- Breast Cancer (HER2+, HR+, Triple Negative)
- Lung Cancer (NSCLC, SCLC, EGFR+, ALK+, PD-L1+)
- GI Oncology (CRC, Pancreatic, Gastric, HCC)
- GU Oncology (Prostate, RCC, Bladder)
- Hematologic Malignancies
"""

from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# ONCOLOGY ENDPOINTS
# ============================================================

ONCOLOGY_ENDPOINTS = {
    # Survival Endpoints
    'OS': {
        'aliases': ['overall survival', 'os', 'death from any cause',
                    'time to death', 'survival'],
        'measure_types': ['HR', 'median', 'rate']
    },
    'PFS': {
        'aliases': ['progression-free survival', 'pfs',
                    'disease progression or death',
                    'time to progression or death'],
        'measure_types': ['HR', 'median', 'rate']
    },
    'DFS': {
        'aliases': ['disease-free survival', 'dfs',
                    'recurrence-free survival', 'rfs'],
        'measure_types': ['HR', 'median', 'rate']
    },
    'EFS': {
        'aliases': ['event-free survival', 'efs'],
        'measure_types': ['HR', 'median', 'rate']
    },
    'TTP': {
        'aliases': ['time to progression', 'ttp'],
        'measure_types': ['HR', 'median']
    },

    # Response Endpoints
    'ORR': {
        'aliases': ['objective response rate', 'orr', 'overall response rate',
                    'response rate', 'tumor response'],
        'measure_types': ['OR', 'RR', 'RD', 'rate']
    },
    'CR': {
        'aliases': ['complete response', 'cr', 'complete remission'],
        'measure_types': ['OR', 'RR', 'rate']
    },
    'PR': {
        'aliases': ['partial response', 'pr'],
        'measure_types': ['OR', 'RR', 'rate']
    },
    'DCR': {
        'aliases': ['disease control rate', 'dcr', 'clinical benefit rate'],
        'measure_types': ['OR', 'RR', 'rate']
    },
    'DOR': {
        'aliases': ['duration of response', 'dor'],
        'measure_types': ['HR', 'median']
    },

    # Prostate-specific
    'rPFS': {
        'aliases': ['radiographic progression-free survival', 'rpfs',
                    'imaging-based progression'],
        'measure_types': ['HR', 'median']
    },
    'PSA_RESPONSE': {
        'aliases': ['psa response', 'psa decline', 'psa50'],
        'measure_types': ['OR', 'RR', 'rate']
    },

    # Quality of Life
    'TTSD': {
        'aliases': ['time to symptomatic deterioration', 'ttsd',
                    'time to deterioration'],
        'measure_types': ['HR', 'median']
    },
    'QOL': {
        'aliases': ['quality of life', 'qol', 'hrqol',
                    'health-related quality of life'],
        'measure_types': ['MD']
    }
}


# ============================================================
# BREAST CANCER PATTERNS
# ============================================================

BREAST_CANCER_PATTERNS = {
    'detection_keywords': [
        r'breast\s+cancer',
        r'her2[- ]?(?:positive|negative|\+|\-)',
        r'hormone\s+receptor[- ]?(?:positive|negative)',
        r'hr[- ]?(?:positive|negative|\+|\-)',
        r'triple[- ]?negative',
        r'tnbc',
        r'er[- ]?(?:positive|negative|\+|\-)',
        r'pr[- ]?(?:positive|negative|\+|\-)',
        r'trastuzumab|herceptin',
        r'pertuzumab|perjeta',
        r't-?dm1|kadcyla',
        r'trastuzumab\s+deruxtecan|enhertu',
        r'cdk4/6\s+inhibitor',
        r'palbociclib|ribociclib|abemaciclib',
        r'aromatase\s+inhibitor',
        r'letrozole|anastrozole|exemestane',
        r'tamoxifen|fulvestrant'
    ],

    'endpoint_patterns': [
        (r'(?:investigator[- ]?assessed\s+)?progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'(?:pathologic\s+)?complete\s+response', 'pCR'),
        (r'invasive\s+disease[- ]?free\s+survival', 'iDFS'),
        (r'distant\s+(?:recurrence|metastasis)[- ]?free', 'DRFS'),
        (r'objective\s+response\s+rate', 'ORR'),
        (r'clinical\s+benefit\s+rate', 'CBR'),
        (r'duration\s+of\s+response', 'DOR')
    ],

    'subtypes': {
        'her2_positive': [r'her2[- ]?(?:positive|\+)', r'her2\s+amplified'],
        'hr_positive': [r'hormone\s+receptor[- ]?(?:positive|\+)', r'hr[- ]?\+',
                       r'er[- ]?\+', r'luminal'],
        'triple_negative': [r'triple[- ]?negative', r'tnbc', r'basal[- ]?like']
    }
}


# ============================================================
# LUNG CANCER PATTERNS
# ============================================================

LUNG_CANCER_PATTERNS = {
    'detection_keywords': [
        r'non[- ]?small[- ]?cell\s+lung\s+cancer',
        r'nsclc',
        r'small[- ]?cell\s+lung\s+cancer',
        r'sclc',
        r'lung\s+(?:cancer|adenocarcinoma|squamous)',
        r'egfr[- ]?(?:mutation|positive|\+)',
        r'alk[- ]?(?:positive|rearrangement|\+)',
        r'ros1[- ]?(?:positive|rearrangement)',
        r'kras\s+g12c',
        r'pd[- ]?l1',
        r'pembrolizumab|keytruda',
        r'nivolumab|opdivo',
        r'atezolizumab|tecentriq',
        r'durvalumab|imfinzi',
        r'osimertinib|tagrisso',
        r'alectinib|lorlatinib|crizotinib',
        r'sotorasib|adagrasib'
    ],

    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'objective\s+response\s+rate', 'ORR'),
        (r'duration\s+of\s+response', 'DOR'),
        (r'disease[- ]?free\s+survival', 'DFS'),
        (r'intracranial\s+(?:pfs|progression)', 'CNS_PFS'),
        (r'time\s+to\s+cns\s+progression', 'CNS_TTP')
    ],

    'subtypes': {
        'egfr_mutant': [r'egfr[- ]?(?:mutation|mutant|\+)', r'exon\s+(?:19|21)',
                       r'del19|l858r'],
        'alk_positive': [r'alk[- ]?(?:positive|rearrangement|\+)'],
        'pd_l1_high': [r'pd[- ]?l1\s*(?:≥|>|expression\s*≥)\s*50',
                      r'high\s+pd[- ]?l1']
    }
}


# ============================================================
# GI ONCOLOGY PATTERNS
# ============================================================

GI_ONCOLOGY_PATTERNS = {
    'detection_keywords': [
        r'colorectal\s+cancer',
        r'\bcrc\b',
        r'colon\s+cancer',
        r'rectal\s+cancer',
        r'pancreatic\s+(?:cancer|adenocarcinoma)',
        r'pdac',
        r'gastric\s+cancer',
        r'gastroesophageal',
        r'hepatocellular\s+carcinoma',
        r'\bhcc\b',
        r'esophageal\s+(?:cancer|adenocarcinoma)',
        r'cholangiocarcinoma',
        r'biliary\s+tract',
        r'kras|nras|braf',
        r'msi[- ]?(?:high|h)',
        r'mmr[- ]?(?:deficient|d)',
        r'her2',
        r'folfox|folfiri|folfoxiri',
        r'bevacizumab|avastin',
        r'cetuximab|panitumumab',
        r'regorafenib|trifluridine'
    ],

    'endpoint_patterns': [
        (r'progression[- ]?free\s+survival', 'PFS'),
        (r'overall\s+survival', 'OS'),
        (r'objective\s+response\s+rate', 'ORR'),
        (r'disease\s+control\s+rate', 'DCR'),
        (r'duration\s+of\s+response', 'DOR'),
        (r'time\s+to\s+progression', 'TTP'),
        (r'pathologic\s+complete\s+response', 'pCR')
    ],

    'subtypes': {
        'msi_high': [r'msi[- ]?(?:high|h)', r'mmr[- ]?(?:deficient|d)',
                    r'microsatellite\s+instability'],
        'ras_wildtype': [r'(?:k|n)?ras\s+wild[- ]?type', r'all[- ]?ras\s+wt'],
        'braf_mutant': [r'braf\s+(?:v600e|mutant|mutation)']
    }
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_oncology_subspecialty(text: str) -> Tuple[str, str, float]:
    """
    Detect oncology subspecialty and subtype from text.

    Returns:
        Tuple of (subspecialty, subtype, confidence)
        Subspecialties: 'breast', 'lung', 'gi', 'gu', 'heme', 'other'
    """
    text_lower = text.lower()

    scores = {
        'breast': 0,
        'lung': 0,
        'gi': 0
    }

    # Score each subspecialty
    for keyword in BREAST_CANCER_PATTERNS['detection_keywords']:
        if re.search(keyword, text_lower):
            scores['breast'] += 1

    for keyword in LUNG_CANCER_PATTERNS['detection_keywords']:
        if re.search(keyword, text_lower):
            scores['lung'] += 1

    for keyword in GI_ONCOLOGY_PATTERNS['detection_keywords']:
        if re.search(keyword, text_lower):
            scores['gi'] += 1

    # Find best match
    best_subspecialty = max(scores, key=scores.get)
    best_score = scores[best_subspecialty]
    total = sum(scores.values())

    if best_score == 0:
        return ('other_oncology', None, 0.5)

    confidence = best_score / total if total > 0 else 0.5

    # Detect subtype
    subtype = detect_oncology_subtype(text_lower, best_subspecialty)

    return (best_subspecialty, subtype, confidence)


def detect_oncology_subtype(text: str, subspecialty: str) -> Optional[str]:
    """Detect specific tumor subtype."""
    subtypes_map = {
        'breast': BREAST_CANCER_PATTERNS.get('subtypes', {}),
        'lung': LUNG_CANCER_PATTERNS.get('subtypes', {}),
        'gi': GI_ONCOLOGY_PATTERNS.get('subtypes', {})
    }

    subtypes = subtypes_map.get(subspecialty, {})

    for subtype_name, patterns in subtypes.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return subtype_name

    return None


def get_oncology_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    """Get endpoint patterns for a specific oncology subspecialty."""
    patterns_map = {
        'breast': BREAST_CANCER_PATTERNS['endpoint_patterns'],
        'lung': LUNG_CANCER_PATTERNS['endpoint_patterns'],
        'gi': GI_ONCOLOGY_PATTERNS['endpoint_patterns']
    }
    return patterns_map.get(subspecialty, [])


def normalize_oncology_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize endpoint name to canonical form."""
    endpoint_lower = endpoint.lower()

    for canonical, info in ONCOLOGY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower:
                return canonical

    return endpoint.upper()
