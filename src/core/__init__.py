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

from .unified_extractor import (
    UnifiedExtractor,
    EffectEstimate,
    PDFExtractionResult,
    extract_from_pdf
)

# v4.0 Verified Extraction Architecture
from .proof_carrying_numbers import (
    ProofCarryingNumber,
    ProofCarryingExtraction,
    ProofCertificate,
    VerificationCheck,
    CheckResult,
    VerificationError,
    create_verified_extraction,
    run_all_checks
)

from .team_of_rivals import (
    team_extract,
    get_verified_extractions,
    ConsensusResult,
    CandidateExtraction,
    ExtractorType,
    ConsensusEngine,
    PatternExtractor,
    GrammarExtractor,
    StateMachineExtractor,
    ChunkExtractor,
    Critic
)

from .v3_extractor_wrapper import V3ExtractorWrapper

from .deterministic_verifier import (
    verify_extraction,
    is_verified,
    DeterministicVerificationResult,
    VerificationLevel,
    DeterministicVerifier,
    SymbolicVerifier,
    PlausibilityVerifier,
    CrossValueVerifier
)

from .verified_extraction_pipeline import (
    verified_extract,
    extract_to_dict,
    extract_values,
    VerifiedExtractionPipeline,
    PipelineResult,
    PipelineStatus,
    BatchProcessor,
    generate_verification_report
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
    'generate_ensemble_report',

    # Unified PDF extractor (v2.3)
    'UnifiedExtractor',
    'EffectEstimate',
    'PDFExtractionResult',
    'extract_from_pdf',

    # v4.0 Verified Extraction Architecture
    # Proof-Carrying Numbers
    'ProofCarryingNumber',
    'ProofCarryingExtraction',
    'ProofCertificate',
    'VerificationCheck',
    'CheckResult',
    'VerificationError',
    'create_verified_extraction',
    'run_all_checks',

    # Team-of-Rivals
    'team_extract',
    'get_verified_extractions',
    'ConsensusResult',
    'CandidateExtraction',
    'ExtractorType',
    'ConsensusEngine',
    'PatternExtractor',
    'GrammarExtractor',
    'StateMachineExtractor',
    'ChunkExtractor',
    'Critic',
    'V3ExtractorWrapper',

    # Deterministic Verifier
    'verify_extraction',
    'is_verified',
    'DeterministicVerificationResult',
    'VerificationLevel',
    'DeterministicVerifier',
    'SymbolicVerifier',
    'PlausibilityVerifier',
    'CrossValueVerifier',

    # Verified Extraction Pipeline
    'verified_extract',
    'extract_to_dict',
    'extract_values',
    'VerifiedExtractionPipeline',
    'PipelineResult',
    'PipelineStatus',
    'BatchProcessor',
    'generate_verification_report',
]
