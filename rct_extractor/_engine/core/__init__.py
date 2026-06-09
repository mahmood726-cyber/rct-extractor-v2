"""
Core extraction modules — lazy imports to avoid crashing on missing optional deps.
"""

# Mapping: attribute name -> (module_path, attribute_name)
_LAZY_IMPORTS = {
    # Models
    'ExtractionOutput': ('.models', 'ExtractionOutput'),
    'ExtractionRecord': ('.models', 'ExtractionRecord'),
    'HazardRatioCI': ('.models', 'HazardRatioCI'),
    'OddsRatioCI': ('.models', 'OddsRatioCI'),
    'RiskRatioCI': ('.models', 'RiskRatioCI'),
    'MeanDifference': ('.models', 'MeanDifference'),
    'BinaryOutcome': ('.models', 'BinaryOutcome'),
    'Arm': ('.models', 'Arm'),
    'Provenance': ('.models', 'Provenance'),
    'ExtractionConfidence': ('.models', 'ExtractionConfidence'),
    # Main extractor
    'RCTExtractor': ('.extractor', 'RCTExtractor'),
    # Evaluation
    'Evaluator': ('.evaluation', 'Evaluator'),
    'EvaluationReport': ('.evaluation', 'EvaluationReport'),
    'load_gold_dataset': ('.evaluation', 'load_gold_dataset'),
    'evaluate_batch': ('.evaluation', 'evaluate_batch'),
    # Meta-analysis support
    'MetaAnalysisFields': ('.meta_analysis', 'MetaAnalysisFields'),
    'calculate_se_from_ci': ('.meta_analysis', 'calculate_se_from_ci'),
    'detect_outcome_priority': ('.meta_analysis', 'detect_outcome_priority'),
    'classify_effect_direction': ('.meta_analysis', 'classify_effect_direction'),
    'detect_subgroup_analyses': ('.meta_analysis', 'detect_subgroup_analyses'),
    'extract_continuous_outcomes': ('.meta_analysis', 'extract_continuous_outcomes'),
    'calculate_nnt_from_rd': ('.meta_analysis', 'calculate_nnt_from_rd'),
    'enhance_extraction': ('.meta_analysis', 'enhance_extraction'),
    # Ensemble merger
    'EnsembleMerger': ('.ensemble', 'EnsembleMerger'),
    'MergedResult': ('.ensemble', 'MergedResult'),
    'ExtractorResult': ('.ensemble', 'ExtractorResult'),
    'ConfidenceGrade': ('.ensemble', 'ConfidenceGrade'),
    'generate_ensemble_report': ('.ensemble', 'generate_ensemble_report'),
    # Unified PDF extractor
    'UnifiedExtractor': ('.unified_extractor', 'UnifiedExtractor'),
    'EffectEstimate': ('.unified_extractor', 'EffectEstimate'),
    'PDFExtractionResult': ('.unified_extractor', 'PDFExtractionResult'),
    'extract_from_pdf': ('.unified_extractor', 'extract_from_pdf'),
    # Proof-Carrying Numbers
    'ProofCarryingNumber': ('.proof_carrying_numbers', 'ProofCarryingNumber'),
    'ProofCarryingExtraction': ('.proof_carrying_numbers', 'ProofCarryingExtraction'),
    'ProofCertificate': ('.proof_carrying_numbers', 'ProofCertificate'),
    'VerificationCheck': ('.proof_carrying_numbers', 'VerificationCheck'),
    'CheckResult': ('.proof_carrying_numbers', 'CheckResult'),
    'VerificationError': ('.proof_carrying_numbers', 'VerificationError'),
    'create_verified_extraction': ('.proof_carrying_numbers', 'create_verified_extraction'),
    'run_all_checks': ('.proof_carrying_numbers', 'run_all_checks'),
    # Team-of-Rivals
    'team_extract': ('.team_of_rivals', 'team_extract'),
    'get_verified_extractions': ('.team_of_rivals', 'get_verified_extractions'),
    'ConsensusResult': ('.team_of_rivals', 'ConsensusResult'),
    'CandidateExtraction': ('.team_of_rivals', 'CandidateExtraction'),
    'ExtractorType': ('.team_of_rivals', 'ExtractorType'),
    'ConsensusEngine': ('.team_of_rivals', 'ConsensusEngine'),
    'PatternExtractor': ('.team_of_rivals', 'PatternExtractor'),
    'GrammarExtractor': ('.team_of_rivals', 'GrammarExtractor'),
    'StateMachineExtractor': ('.team_of_rivals', 'StateMachineExtractor'),
    'ChunkExtractor': ('.team_of_rivals', 'ChunkExtractor'),
    'Critic': ('.team_of_rivals', 'Critic'),
    # V3 wrapper
    'V3ExtractorWrapper': ('.v3_extractor_wrapper', 'V3ExtractorWrapper'),
    # Deterministic Verifier
    'verify_extraction': ('.deterministic_verifier', 'verify_extraction'),
    'is_verified': ('.deterministic_verifier', 'is_verified'),
    'DeterministicVerificationResult': ('.deterministic_verifier', 'DeterministicVerificationResult'),
    'VerificationLevel': ('.deterministic_verifier', 'VerificationLevel'),
    'DeterministicVerifier': ('.deterministic_verifier', 'DeterministicVerifier'),
    'SymbolicVerifier': ('.deterministic_verifier', 'SymbolicVerifier'),
    'PlausibilityVerifier': ('.deterministic_verifier', 'PlausibilityVerifier'),
    'CrossValueVerifier': ('.deterministic_verifier', 'CrossValueVerifier'),
    # Verified Extraction Pipeline
    'verified_extract': ('.verified_extraction_pipeline', 'verified_extract'),
    'extract_to_dict': ('.verified_extraction_pipeline', 'extract_to_dict'),
    'extract_values': ('.verified_extraction_pipeline', 'extract_values'),
    'VerifiedExtractionPipeline': ('.verified_extraction_pipeline', 'VerifiedExtractionPipeline'),
    'PipelineResult': ('.verified_extraction_pipeline', 'PipelineResult'),
    'PipelineStatus': ('.verified_extraction_pipeline', 'PipelineStatus'),
    'BatchProcessor': ('.verified_extraction_pipeline', 'BatchProcessor'),
    'generate_verification_report': ('.verified_extraction_pipeline', 'generate_verification_report'),
    # Meta-analysis output contract
    'MAProvenance': ('.ma_contract', 'MAProvenance'),
    'MAExtractionRecord': ('.ma_contract', 'MAExtractionRecord'),
    'validate_ma_records': ('.ma_contract', 'validate_ma_records'),
    'is_meta_analysis_ready': ('.ma_contract', 'is_meta_analysis_ready'),
}

__all__ = list(_LAZY_IMPORTS.keys())


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        import importlib
        mod = importlib.import_module(module_path, package=__name__)
        val = getattr(mod, attr_name)
        globals()[name] = val  # Cache for subsequent access
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
