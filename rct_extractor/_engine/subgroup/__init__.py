"""
Subgroup Analysis Extraction Module
====================================

Extracts subgroup analysis results, interaction tests, and heterogeneity
measures from clinical trial publications.

Components:
- SubgroupExtractor: Main extraction class
- InteractionTest: P-for-interaction results
- HeterogeneityMeasure: I², tau², Q statistics
- SubgroupDefinition: Detected subgroup categories
"""

from .subgroup_extractor import (
    SubgroupExtractor,
    SubgroupResult,
    InteractionTest,
    HeterogeneityMeasure,
    SubgroupCategory,
    SubgroupDefinition,
)

__all__ = [
    "SubgroupExtractor",
    "SubgroupResult",
    "InteractionTest",
    "HeterogeneityMeasure",
    "SubgroupCategory",
    "SubgroupDefinition",
]
