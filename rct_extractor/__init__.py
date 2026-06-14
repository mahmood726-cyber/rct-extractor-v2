"""
rct_extractor -- meta-analysis-grade RCT data extraction from clinical-trial text.

Public, stable API for installers. Example::

    import rct_extractor as rx

    result = rx.extract(abstract_text, specialty="diabetes")
    # or auto-detect:
    result = rx.extract(abstract_text)            # specialty="auto"

    print(result["specialty"], result["subspecialty"])
    print(result["effects"])      # [{type, effect_size, ci_lower, ci_upper, ...}]
    print(result["arm_level"])    # {poolable_2x2, tables_2x2, continuous}

The 17 supported disease specialties are in :data:`rct_extractor.SPECIALTIES`.
"""
from __future__ import annotations

try:
    from rct_extractor._engine import __version__ as __version__  # single source of truth
except Exception:  # pragma: no cover - fallback if src metadata unavailable
    __version__ = "0.0.0"

from .api import (
    SPECIALTIES,
    detect_specialty,
    extract,
    extract_batch,
    extract_dose_response,
    list_specialties,
    to_metakit_config,
)

__all__ = [
    "__version__",
    "SPECIALTIES",
    "detect_specialty",
    "extract",
    "extract_batch",
    "extract_dose_response",
    "list_specialties",
    "to_metakit_config",
]
