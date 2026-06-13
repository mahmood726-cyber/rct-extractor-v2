"""Internal DTA extraction engine (not the stable public API).

Public callers should use the top-level :mod:`dta_extractor` package.
"""
from .extractor import DTAExtractor, extract  # noqa: F401
from .models import DTAMeasure, DTAStudyRecord, TwoByTwo  # noqa: F401

__version__ = "0.1.0"
