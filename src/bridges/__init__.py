"""
Bridges to external extractors

E1: TruthCert CTGov verification (truthcert_bridge.py)

JS and Wasserstein bridges archived in v5.0 (not needed for core extraction).
All imports are lazy to avoid crashing when optional dependencies are not installed.
"""


def __getattr__(name):
    """Lazy import to avoid crashing when optional bridge deps are missing."""
    _truthcert_exports = {
        'TruthCertBridge', 'CTGovClient', 'CTGovTrial', 'CTGovOutcome',
        'VerificationResult', 'verify_against_ctgov', 'fetch_ctgov_results',
    }

    if name in _truthcert_exports:
        from .truthcert_bridge import (
            TruthCertBridge, CTGovClient, CTGovTrial, CTGovOutcome,
            VerificationResult, verify_against_ctgov, fetch_ctgov_results,
        )
        return locals()[name]
    raise AttributeError(f"module 'src.bridges' has no attribute {name!r}")


__all__ = [
    'TruthCertBridge', 'CTGovClient', 'CTGovTrial', 'CTGovOutcome',
    'VerificationResult', 'verify_against_ctgov', 'fetch_ctgov_results',
]
