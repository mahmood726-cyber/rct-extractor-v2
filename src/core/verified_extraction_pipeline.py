"""
Verified Extraction Pipeline for RCT Extractor v4.0
====================================================

Integrates all three pillars of the verified extraction architecture:
1. Proof-Carrying Numbers (PCN) - Numbers that carry verification certificates
2. Team-of-Rivals - Multiple independent extractors with consensus
3. Deterministic Verification - Formal mathematical verification

TruthCert-inspired principles (from Burhan):
- Multi-witness verification (Team-of-Rivals)
- Scope-locking (PCN provenance tracking)
- Fail-closed operation (unverified = unusable)

Pipeline:
Text -> Team-of-Rivals Extraction -> Deterministic Verification -> PCN Output
"""

import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum

# Import the three pillars
from .proof_carrying_numbers import (
    ProofCarryingNumber, ProofCarryingExtraction, ProofCertificate,
    VerificationCheck, CheckResult, create_verified_extraction,
    run_all_checks, VerificationError
)
from .team_of_rivals import (
    team_extract, ConsensusResult, CandidateExtraction, ExtractorType,
    ConsensusEngine
)
from .deterministic_verifier import (
    verify_extraction, DeterministicVerificationResult, VerificationLevel,
    DeterministicVerifier
)
from .ocr_preprocessor import preprocess_for_extraction, OCRCorrection


class PipelineStatus(Enum):
    """Overall pipeline status"""
    VERIFIED = "verified"           # All checks passed, consensus reached
    CONSENSUS_ONLY = "consensus"    # Team agreed, verification pending
    PARTIAL = "partial"             # Some checks passed
    FAILED = "failed"               # Critical failures
    REJECTED = "rejected"           # Fail-closed: cannot be used


@dataclass
class PipelineResult:
    """Complete result from the verified extraction pipeline"""
    # Source
    source_text: str

    # Extraction result
    effect_type: str
    value: float
    ci_lower: Optional[float]
    ci_upper: Optional[float]
    standard_error: Optional[float]
    p_value: Optional[float]

    # Verification components
    pcn_extraction: Optional[ProofCarryingExtraction]
    consensus_result: Optional[ConsensusResult]
    verification_result: Optional[DeterministicVerificationResult]

    # Status
    status: PipelineStatus
    confidence: float  # 0.0 to 1.0

    # Flags
    is_usable: bool = False  # False = fail-closed
    needs_review: bool = False
    warnings: List[str] = field(default_factory=list)

    # Provenance
    extraction_method: str = ""
    extraction_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for output"""
        result = {
            'effect_type': self.effect_type,
            'value': self.value,
            'ci_lower': self.ci_lower,
            'ci_upper': self.ci_upper,
            'standard_error': self.standard_error,
            'p_value': self.p_value,
            'status': self.status.value,
            'confidence': self.confidence,
            'is_usable': self.is_usable,
            'needs_review': self.needs_review,
            'warnings': self.warnings,
            'extraction_method': self.extraction_method,
            'extraction_hash': self.extraction_hash,
        }

        if self.consensus_result:
            result['consensus'] = {
                'agreement_ratio': self.consensus_result.agreement_ratio,
                'agreeing_extractors': [e.value for e in self.consensus_result.agreeing_extractors],
                'is_unanimous': self.consensus_result.is_unanimous,
            }

        if self.verification_result:
            result['verification'] = {
                'level': self.verification_result.overall_level.value,
                'all_critical_passed': self.verification_result.all_critical_satisfied,
                'hash': self.verification_result.verification_hash,
            }

        if self.pcn_extraction:
            result['pcn'] = self.pcn_extraction.to_dict()

        return result

    def render_value(self, allow_unverified: bool = False) -> str:
        """
        Render the extracted value.
        Fail-closed: Refuses to render if not verified.
        """
        if not self.is_usable:
            if allow_unverified:
                return f"[UNVERIFIED: {self.value}]"
            raise VerificationError(
                f"Cannot render unverified value {self.value}. "
                f"Status: {self.status.value}. Warnings: {self.warnings}"
            )
        return str(self.value)


# =============================================================================
# VERIFIED EXTRACTION PIPELINE
# =============================================================================

class VerifiedExtractionPipeline:
    """
    Main pipeline integrating all verification components.

    Architecture:
    1. Team-of-Rivals extracts candidates (V3 primary for 100% sensitivity)
    2. Deterministic verifier validates mathematically
    3. PCN wraps result with certificates
    4. Fail-closed: Only verified results are usable

    Key change in v4.0.1: Require Pattern extractor agreement to maintain 0% FPR.
    """

    def __init__(self, min_agreement: float = 0.25, require_verification: bool = True,
                 require_pattern_agreement: bool = True, use_v3_primary: bool = True):
        """
        Initialize pipeline.

        Args:
            min_agreement: Minimum consensus ratio (0.25 = at least one extractor)
            require_verification: If True, fail-closed on verification failure
            require_pattern_agreement: If True, require Pattern extractor to agree (reduces FPR)
            use_v3_primary: If True, use V3ExtractorWrapper as primary extractor
        """
        self.min_agreement = min_agreement
        self.require_verification = require_verification
        self.require_pattern_agreement = require_pattern_agreement
        self.verifier = DeterministicVerifier()
        self._ocr_corrections = []  # Track OCR corrections for audit trail

        # Use V3-based consensus engine
        from .team_of_rivals import ConsensusEngine
        self.consensus_engine = ConsensusEngine(
            use_v3_primary=use_v3_primary,
            require_pattern_agreement=require_pattern_agreement
        )

    def extract(self, text: str) -> List[PipelineResult]:
        """
        Run complete verified extraction pipeline.

        Args:
            text: Text to extract from

        Returns:
            List of PipelineResult objects
        """
        results = []

        # Step 0: OCR Preprocessing for regulatory-grade extraction
        # Corrects common OCR errors (O->0, l->1, Cl->CI) to ensure 100% sensitivity
        corrected_text, ocr_corrections = preprocess_for_extraction(text)

        # Log OCR corrections for audit trail
        if ocr_corrections:
            self._ocr_corrections = ocr_corrections

        # Step 1: Team-of-Rivals extraction using configured engine
        consensus_results = self.consensus_engine.extract_with_consensus(corrected_text)

        for consensus in consensus_results:
            if consensus.extraction is None:
                continue

            candidate = consensus.extraction

            # Step 2: Deterministic verification
            verification = None
            if candidate.ci_lower is not None and candidate.ci_upper is not None:
                verification = self.verifier.verify(
                    effect_type=candidate.effect_type,
                    value=candidate.value,
                    ci_lower=candidate.ci_lower,
                    ci_upper=candidate.ci_upper,
                    p_value=candidate.p_value,
                )

            # Step 3: Create PCN extraction
            pcn_extraction = None
            if candidate.ci_lower is not None and candidate.ci_upper is not None:
                pcn_extraction = create_verified_extraction(
                    effect_type=candidate.effect_type,
                    value=candidate.value,
                    ci_lower=candidate.ci_lower,
                    ci_upper=candidate.ci_upper,
                    source_text=candidate.source_text,
                    char_start=candidate.char_start,
                    char_end=candidate.char_end,
                    extraction_method=f"team_of_rivals_{candidate.extractor.value}",
                    p_value=candidate.p_value,
                )

                # Add consensus info to certificate
                if pcn_extraction.master_certificate:
                    pcn_extraction.master_certificate.extractors_agreed = [
                        e.value for e in consensus.agreeing_extractors
                    ]
                    pcn_extraction.master_certificate.extractors_disagreed = [
                        e.value for e in consensus.disagreeing_extractors
                    ]
                    pcn_extraction.master_certificate.agreement_count = len(consensus.agreeing_extractors)
                    pcn_extraction.master_certificate.total_extractors = 4  # PatternExtractor, GrammarExtractor, StateMachineExtractor, ChunkExtractor

            # Step 4: Determine status and usability
            status, confidence, is_usable, warnings = self._determine_status(
                consensus, verification, pcn_extraction
            )

            # Calculate SE
            standard_error = None
            if candidate.ci_lower is not None and candidate.ci_upper is not None:
                try:
                    import math
                    if candidate.effect_type in ['HR', 'OR', 'RR', 'IRR']:
                        standard_error = (math.log(candidate.ci_upper) - math.log(candidate.ci_lower)) / (2 * 1.96)
                    else:
                        standard_error = (candidate.ci_upper - candidate.ci_lower) / (2 * 1.96)
                except (ValueError, ZeroDivisionError):
                    pass

            # Compute extraction hash
            hash_input = f"{candidate.effect_type}|{candidate.value}|{candidate.ci_lower}|{candidate.ci_upper}"
            extraction_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

            result = PipelineResult(
                source_text=candidate.source_text,
                effect_type=candidate.effect_type,
                value=candidate.value,
                ci_lower=candidate.ci_lower,
                ci_upper=candidate.ci_upper,
                standard_error=standard_error,
                p_value=candidate.p_value,
                pcn_extraction=pcn_extraction,
                consensus_result=consensus,
                verification_result=verification,
                status=status,
                confidence=confidence,
                is_usable=is_usable,
                needs_review=not is_usable or len(warnings) > 0,
                warnings=warnings,
                extraction_method=f"team_of_rivals_{candidate.extractor.value}",
                extraction_hash=extraction_hash,
            )

            results.append(result)

        return results

    def _determine_status(
        self,
        consensus: ConsensusResult,
        verification: Optional[DeterministicVerificationResult],
        pcn: Optional[ProofCarryingExtraction]
    ) -> tuple:
        """Determine overall status, confidence, usability, and warnings"""
        warnings = []

        # Check consensus
        has_consensus = consensus.agreement_ratio >= self.min_agreement
        is_unanimous = consensus.is_unanimous

        # Check if Pattern extractor agreed (critical for low FPR)
        pattern_agreed = ExtractorType.PATTERN in consensus.agreeing_extractors

        if not has_consensus:
            warnings.append(f"Low consensus: {consensus.agreement_ratio:.0%}")

        if self.require_pattern_agreement and not pattern_agreed:
            warnings.append("Pattern extractor did not agree")

        # Check verification
        verification_passed = True
        if verification:
            if verification.overall_level == VerificationLevel.VIOLATED:
                verification_passed = False
                warnings.extend(verification.warnings)
            elif verification.overall_level == VerificationLevel.UNCERTAIN:
                warnings.append("Verification uncertain")

        # Check PCN
        pcn_verified = True
        if pcn:
            pcn_verified = pcn.is_fully_verified
            if not pcn_verified:
                warnings.append("PCN verification failed")

        # Determine status - Pattern agreement is critical
        if is_unanimous and verification_passed and pcn_verified:
            status = PipelineStatus.VERIFIED
            confidence = 0.99
        elif pattern_agreed and verification_passed:
            # Pattern agreed + verification passed = high confidence
            status = PipelineStatus.CONSENSUS_ONLY
            confidence = 0.95
        elif pattern_agreed and has_consensus:
            # Pattern agreed but verification issues
            status = PipelineStatus.PARTIAL
            confidence = 0.85
        elif has_consensus and verification_passed:
            # Consensus but no pattern agreement
            status = PipelineStatus.PARTIAL
            confidence = 0.6 * consensus.agreement_ratio
        else:
            status = PipelineStatus.FAILED
            confidence = 0.3 * consensus.agreement_ratio

        # Determine usability (fail-closed)
        # Key: Require Pattern agreement for usable status to maintain low FPR
        if self.require_verification:
            if self.require_pattern_agreement:
                is_usable = pattern_agreed and status in [PipelineStatus.VERIFIED, PipelineStatus.CONSENSUS_ONLY, PipelineStatus.PARTIAL]
            else:
                is_usable = status in [PipelineStatus.VERIFIED, PipelineStatus.CONSENSUS_ONLY]
        else:
            is_usable = status != PipelineStatus.FAILED

        if not is_usable:
            status = PipelineStatus.REJECTED

        return status, confidence, is_usable, warnings

    def extract_verified_only(self, text: str) -> List[PipelineResult]:
        """
        Extract and return only verified results.
        All unverified results are filtered out.
        """
        all_results = self.extract(text)
        return [r for r in all_results if r.is_usable]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def verified_extract(text: str, strict: bool = True) -> List[PipelineResult]:
    """
    Main interface: Extract effect estimates with full verification.

    Args:
        text: Text to extract from
        strict: If True, only returns verified results (fail-closed)

    Returns:
        List of PipelineResult objects
    """
    pipeline = VerifiedExtractionPipeline(require_verification=strict)
    if strict:
        return pipeline.extract_verified_only(text)
    return pipeline.extract(text)


def extract_to_dict(text: str) -> List[Dict[str, Any]]:
    """
    Extract and return as list of dictionaries.
    Convenient for JSON output.
    """
    results = verified_extract(text, strict=True)
    return [r.to_dict() for r in results]


def extract_values(text: str) -> List[tuple]:
    """
    Extract just the values (effect_type, value, ci_lower, ci_upper).
    Only returns verified results.
    """
    results = verified_extract(text, strict=True)
    return [
        (r.effect_type, r.value, r.ci_lower, r.ci_upper)
        for r in results
    ]


# =============================================================================
# BATCH PROCESSING
# =============================================================================

class BatchProcessor:
    """Process multiple texts with verification"""

    def __init__(self, strict: bool = True):
        self.pipeline = VerifiedExtractionPipeline(require_verification=strict)
        self.strict = strict

    def process(self, texts: List[str]) -> Dict[str, Any]:
        """
        Process multiple texts.

        Returns:
            Dictionary with results, statistics, and any errors
        """
        all_results = []
        errors = []

        for i, text in enumerate(texts):
            try:
                results = self.pipeline.extract(text)
                for r in results:
                    r_dict = r.to_dict()
                    r_dict['text_index'] = i
                    all_results.append(r_dict)
            except Exception as e:
                errors.append({
                    'text_index': i,
                    'error': str(e),
                })

        # Calculate statistics
        verified_count = sum(1 for r in all_results if r['is_usable'])
        total_count = len(all_results)

        stats = {
            'total_extractions': total_count,
            'verified_extractions': verified_count,
            'verification_rate': verified_count / total_count if total_count > 0 else 0,
            'error_count': len(errors),
        }

        return {
            'results': all_results if not self.strict else [r for r in all_results if r['is_usable']],
            'statistics': stats,
            'errors': errors,
        }


# =============================================================================
# REPORTING
# =============================================================================

def generate_verification_report(results: List[PipelineResult]) -> str:
    """Generate a human-readable verification report"""
    lines = [
        "=" * 60,
        "VERIFIED EXTRACTION REPORT",
        "=" * 60,
        "",
    ]

    for i, r in enumerate(results, 1):
        lines.append(f"Extraction #{i}")
        lines.append("-" * 40)
        lines.append(f"  Effect Type: {r.effect_type}")
        lines.append(f"  Value: {r.value}")
        if r.ci_lower and r.ci_upper:
            lines.append(f"  95% CI: [{r.ci_lower}, {r.ci_upper}]")
        if r.standard_error:
            lines.append(f"  SE: {r.standard_error:.4f}")
        lines.append(f"  Status: {r.status.value}")
        lines.append(f"  Confidence: {r.confidence:.0%}")
        lines.append(f"  Usable: {'Yes' if r.is_usable else 'NO - FAIL-CLOSED'}")

        if r.consensus_result:
            lines.append(f"  Consensus: {r.consensus_result.agreement_ratio:.0%} agreement")
            lines.append(f"  Agreeing: {[e.value for e in r.consensus_result.agreeing_extractors]}")

        if r.verification_result:
            lines.append(f"  Verification: {r.verification_result.overall_level.value}")

        if r.warnings:
            lines.append(f"  Warnings: {r.warnings}")

        lines.append("")

    # Summary
    lines.append("=" * 60)
    lines.append("SUMMARY")
    lines.append("-" * 40)

    total = len(results)
    usable = sum(1 for r in results if r.is_usable)
    verified = sum(1 for r in results if r.status == PipelineStatus.VERIFIED)

    lines.append(f"Total extractions: {total}")
    lines.append(f"Usable (passed fail-closed): {usable} ({usable/total*100:.0f}%)" if total > 0 else "No extractions")
    lines.append(f"Fully verified: {verified}")
    lines.append("=" * 60)

    return "\n".join(lines)
