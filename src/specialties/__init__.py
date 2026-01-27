"""
Specialty-specific extraction patterns and endpoints.

Organized by therapeutic area and subspecialty for improved accuracy.
"""

from .cardiology import (
    CARDIOLOGY_ENDPOINTS,
    HEART_FAILURE_PATTERNS,
    ACS_PATTERNS,
    AF_PATTERNS,
    VALVE_PATTERNS,
    detect_cardiology_subspecialty
)

from .oncology import (
    ONCOLOGY_ENDPOINTS,
    BREAST_CANCER_PATTERNS,
    LUNG_CANCER_PATTERNS,
    GI_ONCOLOGY_PATTERNS,
    detect_oncology_subspecialty
)

from .registry import (
    SPECIALTY_REGISTRY,
    get_specialty_patterns,
    get_endpoint_normalizer
)

__all__ = [
    # Cardiology
    'CARDIOLOGY_ENDPOINTS',
    'HEART_FAILURE_PATTERNS',
    'ACS_PATTERNS',
    'AF_PATTERNS',
    'VALVE_PATTERNS',
    'detect_cardiology_subspecialty',

    # Oncology
    'ONCOLOGY_ENDPOINTS',
    'BREAST_CANCER_PATTERNS',
    'LUNG_CANCER_PATTERNS',
    'GI_ONCOLOGY_PATTERNS',
    'detect_oncology_subspecialty',

    # Registry
    'SPECIALTY_REGISTRY',
    'get_specialty_patterns',
    'get_endpoint_normalizer'
]
