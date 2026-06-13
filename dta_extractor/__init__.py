"""
dta_extractor -- diagnostic test accuracy (DTA) data extraction from study text.

A new extraction MODE alongside the RCT pairwise-effect extractor in
`rct_extractor`. Where `rct_extractor.extract` pulls treatment-effect estimates
from RCT text, `dta_extractor.extract` pulls the DTA primitives:

    * the 2x2 contingency table (TP, FP, FN, TN)
    * sensitivity, specificity, PPV, NPV
    * positive/negative likelihood ratios, diagnostic odds ratio
    * AUC / AUROC / c-statistic, overall accuracy
    * the index test, reference standard, and target condition

Example::

    import dta_extractor as dta

    result = dta.extract(abstract_text)            # domain auto-detected
    print(result["entities"])                      # index_test / reference_standard / target_condition
    print(result["two_by_two"])                    # explicit TP/FP/FN/TN tables
    print(result["measures"])                      # sensitivity/specificity/... measures
    print(result["records"])                       # poolable DTAStudyRecords

Supported DTA domains are in :data:`dta_extractor.DOMAINS`.
"""
from __future__ import annotations

from ._engine import __version__ as __version__
from ._engine.extractor import DTAExtractor, extract
from ._engine.models import DTAMeasure, DTAStudyRecord, TwoByTwo
from ._engine.registry import DTA_REGISTRY, detect_domain, list_domains

DOMAINS = list_domains()


def list_domains_public():
    return list_domains()


__all__ = [
    "__version__",
    "extract",
    "DTAExtractor",
    "TwoByTwo",
    "DTAMeasure",
    "DTAStudyRecord",
    "DTA_REGISTRY",
    "DOMAINS",
    "detect_domain",
    "list_domains",
]
