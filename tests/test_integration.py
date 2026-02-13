"""
End-to-end integration tests for the RCT extraction pipeline.

P1-19: Tests the complete flow: text -> extraction -> PCN certification -> output.
Uses synthetic fixtures (no network, no PDFs) to verify the pipeline wiring.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.enhanced_extractor_v3 import EnhancedExtractor, EffectType, correct_ocr_errors
from src.core.proof_carrying_numbers import (
    ProofCarryingNumber,
    ProofCertificate,
    ProofCarryingExtraction,
    create_verified_extraction,
    run_all_checks,
    CheckResult,
)
from src.core.team_of_rivals import (
    PatternExtractor,
    GrammarExtractor,
    StateMachineExtractor,
    ChunkExtractor,
    ConsensusEngine,
)


# =============================================================================
# Synthetic test fixtures
# =============================================================================

CLEAN_RCT_TEXT = """
Results: The primary composite endpoint of cardiovascular death or
hospitalization for heart failure occurred in 386 of 2373 patients (16.3%)
in the dapagliflozin group and in 502 of 2371 patients (21.2%) in the
placebo group (hazard ratio, 0.74; 95% CI, 0.65 to 0.85; P<0.001).
"""

MULTI_EFFECT_TEXT = """
Primary endpoint: HR 0.74 (95% CI 0.65-0.85), P<0.001.
Key secondary: OR 0.68 (95% CI 0.55-0.84), P=0.0004.
Mean difference in eGFR: MD -1.2 (95% CI -2.1 to -0.3), P=0.009.
"""

OCR_DEGRADED_TEXT = """
Primary endpoint: HR O.74 (95% Cl O.65-O.85), P<O.OOl.
"""

PROTOCOL_TEXT = """
PROTOCOL: We hypothesize that the hazard ratio for the primary composite
will be 0.75, powered at 90% with two-sided alpha of 0.05.
Results will be reported separately.
"""

NEGATIVE_CONTROL_OBSERVATIONAL = """
Retrospective cohort study using Medicare claims data.
Propensity score matching: HR 0.68 (95% CI, 0.62-0.74).
This observational evidence complements randomized trials.
"""


class TestEndToEndExtraction:
    """Integration: text -> EnhancedExtractor -> extractions"""

    def setup_method(self):
        self.extractor = EnhancedExtractor()

    def test_clean_rct_extraction(self):
        """Extract HR from clean RCT results text"""
        results = self.extractor.extract(CLEAN_RCT_TEXT)
        assert len(results) >= 1, "Should extract at least 1 effect"
        hr = results[0]
        assert hr.effect_type == EffectType.HR
        assert abs(hr.point_estimate - 0.74) < 0.01
        assert hr.ci is not None
        assert abs(hr.ci.lower - 0.65) < 0.01
        assert abs(hr.ci.upper - 0.85) < 0.01

    def test_multi_effect_extraction(self):
        """Extract multiple effect types from one text"""
        results = self.extractor.extract(MULTI_EFFECT_TEXT)
        assert len(results) >= 2, f"Expected >=2 effects, got {len(results)}"
        types = {r.effect_type for r in results}
        assert EffectType.HR in types, "Should extract HR"

    def test_ocr_correction_integration(self):
        """OCR-degraded text should be corrected before extraction"""
        results = self.extractor.extract(OCR_DEGRADED_TEXT)
        assert len(results) >= 1, "OCR correction should enable extraction"
        hr = results[0]
        assert abs(hr.point_estimate - 0.74) < 0.01

    def test_protocol_rejection(self):
        """Protocol text should be rejected by negative context filter"""
        results = self.extractor.extract(PROTOCOL_TEXT)
        assert len(results) == 0, (
            f"Protocol text should produce 0 extractions, got {len(results)}: "
            f"{[(r.effect_type.value, r.point_estimate) for r in results]}"
        )

    def test_observational_rejection(self):
        """Observational study text should be rejected"""
        results = self.extractor.extract(NEGATIVE_CONTROL_OBSERVATIONAL)
        assert len(results) == 0, (
            f"Observational text should produce 0 extractions, got {len(results)}"
        )


class TestEndToEndPCN:
    """Integration: extraction -> PCN certification -> verification"""

    def setup_method(self):
        self.extractor = EnhancedExtractor()

    def test_pcn_roundtrip(self):
        """Full roundtrip: extract -> certify -> verify checks"""
        results = self.extractor.extract(CLEAN_RCT_TEXT)
        assert len(results) >= 1
        extraction = results[0]

        # Create verified extraction via PCN pipeline
        pce = create_verified_extraction(
            effect_type=extraction.effect_type.value,
            value=extraction.point_estimate,
            ci_lower=extraction.ci.lower,
            ci_upper=extraction.ci.upper,
            source_text=extraction.source_text,
            char_start=extraction.char_start,
            char_end=extraction.char_end,
            extraction_method="pattern",
        )
        assert pce is not None
        assert isinstance(pce, ProofCarryingExtraction)
        assert abs(pce.point_estimate.value - 0.74) < 0.01
        assert pce.master_certificate is not None
        assert pce.master_certificate.is_verified, (
            f"PCN should be verified, failed: {pce.master_certificate.checks_failed}"
        )

    def test_pcn_checks_all_pass(self):
        """All verification checks should pass for valid extraction"""
        checks = run_all_checks("HR", 0.74, 0.65, 0.85, p_value=0.001)
        failed = [c for c in checks if c.result == CheckResult.FAILED]
        assert len(failed) == 0, f"Checks failed: {[(c.name, c.message) for c in failed]}"

    def test_pcn_catches_invalid_ci(self):
        """PCN checks should fail when CI doesn't bracket estimate"""
        checks = run_all_checks("HR", 0.50, 0.65, 0.85)
        failed_names = [c.name for c in checks if c.result == CheckResult.FAILED]
        assert "CI_CONTAINS_POINT" in failed_names

    def test_pcn_catches_implausible(self):
        """PCN checks should flag implausible values"""
        checks = run_all_checks("HR", 500.0, 400.0, 600.0)
        failed_names = [c.name for c in checks if c.result == CheckResult.FAILED]
        assert "RANGE_PLAUSIBLE" in failed_names

    def test_pcn_integrity_hash(self):
        """Integrity hash should change when value is tampered"""
        cert = ProofCertificate(
            source_text="HR 0.74 (0.65-0.85)",
            char_start=0,
            char_end=20,
            extraction_method="pattern",
        )
        pcn = ProofCarryingNumber(value=0.74, certificate=cert)
        original_hash = pcn.certificate.integrity_hash

        # Create new PCN with different value — should get different hash
        cert2 = ProofCertificate(
            source_text="HR 0.74 (0.65-0.85)",
            char_start=0,
            char_end=20,
            extraction_method="pattern",
        )
        pcn2 = ProofCarryingNumber(value=0.99, certificate=cert2)
        assert pcn2.certificate.integrity_hash != original_hash


class TestEndToEndTeamOfRivals:
    """Integration: text -> 4 extractors -> consensus"""

    def test_consensus_on_clean_text(self):
        """All 4 extractors should find the same HR in clean text"""
        text = "HR 0.74 (95% CI 0.65-0.85)"
        extractors = [
            PatternExtractor(),
            GrammarExtractor(),
            StateMachineExtractor(),
            ChunkExtractor(),
        ]
        all_results = []
        for ext in extractors:
            results = ext.extract(text)
            all_results.extend(results)

        # At least some extractors should find the value
        assert len(all_results) >= 2, (
            f"Expected >=2 extractors to find HR, got {len(all_results)}"
        )

        # All found values should agree
        values = [r.value for r in all_results]
        for v in values:
            assert abs(v - 0.74) < 0.01, f"Expected ~0.74, got {v}"

    def test_consensus_engine(self):
        """ConsensusEngine should produce consensus from individual extractions"""
        text = "HR 0.74 (95% CI 0.65-0.85)"
        engine = ConsensusEngine()
        consensus = engine.extract_with_consensus(text)
        assert isinstance(consensus, list)
        if consensus:
            # ConsensusResult has .extraction.value
            assert consensus[0].extraction is not None
            assert abs(consensus[0].extraction.value - 0.74) < 0.01


class TestEndToEndOCRCorrection:
    """Integration: OCR correction function"""

    def test_ocr_cl_to_ci(self):
        """Cl -> CI correction"""
        text = "95% Cl 0.65-0.85"
        corrected = correct_ocr_errors(text)
        assert "CI" in corrected
        assert "Cl" not in corrected

    def test_ocr_O_to_zero(self):
        """O -> 0 in numeric context"""
        text = "O.74"
        corrected = correct_ocr_errors(text)
        assert "0.74" in corrected

    def test_ocr_preserves_words(self):
        """OCR correction should not corrupt normal words"""
        text = "Overall HR 0.74 Clinical outcome"
        corrected = correct_ocr_errors(text)
        assert "Overall" in corrected
        assert "Clinical" in corrected


class TestEndToEndNegativeControls:
    """Integration: negative control texts should produce zero extractions"""

    def setup_method(self):
        self.extractor = EnhancedExtractor()

    def test_negative_controls_batch(self):
        """Run all negative controls through the extractor.

        Note: REVIEW and SECONDARY_ANALYSIS types are excluded because
        v5.0.1 intentionally removed meta-analysis/pooled negative context
        patterns — pooled estimates from these sources are valid extractions.
        """
        from data.negative_controls import NEGATIVE_CONTROLS, NegativeControlType

        # Types where extraction is intentionally allowed (v5.0.1 design decision)
        ALLOWED_TYPES = {NegativeControlType.REVIEW, NegativeControlType.SECONDARY_ANALYSIS}

        false_positives = []
        for nc in NEGATIVE_CONTROLS:
            if nc.control_type in ALLOWED_TYPES:
                continue
            results = self.extractor.extract(nc.source_text)
            if results:
                false_positives.append((nc.id, nc.control_type.value,
                                        [(r.effect_type.value, r.point_estimate) for r in results]))

        if false_positives:
            fp_summary = "\n".join(
                f"  {fp_id} ({fp_type}): {fp_vals}"
                for fp_id, fp_type, fp_vals in false_positives
            )
            pytest.fail(
                f"False positives on {len(false_positives)}/{len(NEGATIVE_CONTROLS)} "
                f"negative controls:\n{fp_summary}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
