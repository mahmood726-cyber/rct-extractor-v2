"""
Bridges to external extractors

E1: Python extractor (core/extractor.py)
E2: JavaScript extractor (js_extractor_bridge.py)
E3: Wasserstein survival analysis (wasserstein_bridge.py)
E4: TruthCert CTGov verification (truthcert_bridge.py)
"""

from .js_extractor_bridge import JSExtractorBridge, extract_with_js
from .wasserstein_bridge import (
    WassersteinBridge,
    KaplanMeierCurve,
    SurvivalPoint,
    SurvivalAnalysisResult,
    create_km_curve_from_data,
    wasserstein_survival_1,
    wasserstein_survival_2,
    reconstruct_ipd_guyot
)
from .truthcert_bridge import (
    TruthCertBridge,
    CTGovClient,
    CTGovTrial,
    CTGovOutcome,
    VerificationResult,
    verify_against_ctgov,
    fetch_ctgov_results
)

__all__ = [
    # JS Extractor (E2)
    'JSExtractorBridge',
    'extract_with_js',

    # Wasserstein Bridge (E3)
    'WassersteinBridge',
    'KaplanMeierCurve',
    'SurvivalPoint',
    'SurvivalAnalysisResult',
    'create_km_curve_from_data',
    'wasserstein_survival_1',
    'wasserstein_survival_2',
    'reconstruct_ipd_guyot',

    # TruthCert Bridge (E4)
    'TruthCertBridge',
    'CTGovClient',
    'CTGovTrial',
    'CTGovOutcome',
    'VerificationResult',
    'verify_against_ctgov',
    'fetch_ctgov_results'
]
