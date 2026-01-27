"""
Core extraction modules
"""

from .models import (
    ExtractionOutput,
    ExtractionRecord,
    HazardRatioCI,
    OddsRatioCI,
    RiskRatioCI,
    MeanDifference,
    BinaryOutcome,
    Arm,
    Provenance,
    ExtractionConfidence
)

from .extractor import RCTExtractor

from .evaluation import (
    Evaluator,
    EvaluationReport,
    load_gold_dataset,
    evaluate_batch
)

from .meta_analysis import (
    MetaAnalysisFields,
    calculate_se_from_ci,
    detect_outcome_priority,
    classify_effect_direction,
    detect_subgroup_analyses,
    extract_continuous_outcomes,
    calculate_nnt_from_rd,
    enhance_extraction
)

from .ensemble import (
    EnsembleMerger,
    MergedResult,
    ExtractorResult,
    ConfidenceGrade,
    generate_ensemble_report
)

__all__ = [
    # Main extractor
    'RCTExtractor',

    # Models
    'ExtractionOutput',
    'ExtractionRecord',
    'HazardRatioCI',
    'OddsRatioCI',
    'RiskRatioCI',
    'MeanDifference',
    'BinaryOutcome',
    'Arm',
    'Provenance',
    'ExtractionConfidence',

    # Evaluation
    'Evaluator',
    'EvaluationReport',
    'load_gold_dataset',
    'evaluate_batch',

    # Meta-analysis support (from v4.8)
    'MetaAnalysisFields',
    'calculate_se_from_ci',
    'detect_outcome_priority',
    'classify_effect_direction',
    'detect_subgroup_analyses',
    'extract_continuous_outcomes',
    'calculate_nnt_from_rd',
    'enhance_extraction',

    # Ensemble merger
    'EnsembleMerger',
    'MergedResult',
    'ExtractorResult',
    'ConfidenceGrade',
    'generate_ensemble_report'
]
