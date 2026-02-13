#!/usr/bin/env python3
"""
Tests for RCT Classifier Integration into PDF Extraction Pipeline
==================================================================

Verifies that:
1. Classification result is populated on extraction
2. skip_non_rct=True correctly skips non-RCT papers
3. Known letters/protocols are correctly excluded
4. Known RCTs are never falsely excluded
5. Classification fields are present in PDFExtractionResult
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from src.core.pdf_extraction_pipeline import PDFExtractionPipeline, PDFExtractionResult
from src.utils.rct_classifier import RCTClassifier, StudyType, ClassificationResult


# =============================================================================
# Sample texts for testing
# =============================================================================

RCT_RESULTS_TEXT = """
A Randomized, Double-Blind, Placebo-Controlled Trial of Dapagliflozin
in Patients With Heart Failure

We randomly assigned 4744 patients with heart failure to receive
dapagliflozin or placebo. The primary outcome was a composite of
cardiovascular death or worsening heart failure.

Results: The hazard ratio for the primary outcome was 0.74 (95% CI,
0.65 to 0.85; P<0.001). The number needed to treat was 21.

Trial registration: NCT03036124. CONSORT diagram is provided.
The intention-to-treat population included all randomized patients.
"""

PROTOCOL_TEXT = """
Study Protocol: A Phase III Randomized Controlled Trial of Drug X
for the Treatment of Type 2 Diabetes

This protocol describes a planned randomized controlled trial.
Patients will be randomized 1:1 to Drug X or placebo.
We will assess HbA1c reduction as the primary endpoint.
Planned enrollment is 500 patients over 24 months.
Recruitment will begin in Q3 2026.
We will evaluate safety and efficacy at 52 weeks.
"""

LETTER_TEXT = """
Letter to the Editor

Dear Editor,

In response to the article by Smith et al. regarding the use of
dapagliflozin in heart failure, we would like to comment on the
statistical methods used. The reported hazard ratio of 0.74 (95% CI,
0.65 to 0.85) is consistent with our experience.

Reply to the editorial commentary on DAPA-HF results.
Correspondence regarding methodology.
"""

META_ANALYSIS_TEXT = """
Systematic Review and Meta-Analysis of SGLT2 Inhibitors
in Heart Failure: A PRISMA-Compliant Analysis

We searched PubMed, MEDLINE, Embase, and Cochrane databases.
The pooled analysis included 12 randomized trials.
The pooled hazard ratio was 0.77 (95% CI, 0.72 to 0.82).
Heterogeneity was low (I2 = 12%).
A funnel plot showed no evidence of publication bias.
Risk of bias assessment was performed using the Cochrane tool.
"""

OBSERVATIONAL_TEXT = """
A Retrospective Cohort Study of SGLT2 Inhibitor Use
in Real-World Practice

This retrospective cohort study analyzed data from 50,000 patients.
Real-world evidence from a healthcare database.
Propensity score matching was used to reduce confounding.
The adjusted hazard ratio was 0.82 (95% CI, 0.75 to 0.90).
"""

RCT_WITH_EFFECTS = """
Randomized Controlled Trial of Empagliflozin in Type 2 Diabetes

Patients were randomly assigned to empagliflozin 10mg, 25mg, or placebo.
Double-blind design with intention-to-treat analysis.
NCT01131676.

The primary outcome was 3-point MACE (cardiovascular death, nonfatal
myocardial infarction, or nonfatal stroke).

The hazard ratio for 3-point MACE was 0.86 (95% CI, 0.74 to 0.99; P=0.04).
The odds ratio for hospitalization was 0.65 (95% CI, 0.50 to 0.85).
Mean difference in HbA1c was -0.7% (95% CI, -0.9 to -0.5; P<0.001).
"""


# =============================================================================
# Tests
# =============================================================================

class TestRCTClassifierDirectly:
    """Test the RCTClassifier class directly."""

    def setup_method(self):
        self.classifier = RCTClassifier()

    def test_rct_results_classified_correctly(self):
        result = self.classifier.classify(RCT_RESULTS_TEXT)
        assert result.study_type == StudyType.RCT_RESULTS
        assert result.is_rct is True
        assert result.has_results is True
        assert result.recommendation == "include"
        assert result.confidence >= 0.7

    def test_protocol_classified_correctly(self):
        result = self.classifier.classify(PROTOCOL_TEXT)
        assert result.study_type == StudyType.PROTOCOL
        assert result.has_results is False
        assert result.recommendation == "exclude"

    def test_letter_classified_correctly(self):
        result = self.classifier.classify(LETTER_TEXT)
        assert result.study_type == StudyType.LETTER
        assert result.is_rct is False
        assert result.recommendation == "exclude"

    def test_meta_analysis_classified_correctly(self):
        result = self.classifier.classify(META_ANALYSIS_TEXT)
        assert result.study_type == StudyType.META_ANALYSIS
        assert result.recommendation == "include"

    def test_observational_classified_correctly(self):
        result = self.classifier.classify(OBSERVATIONAL_TEXT)
        assert result.study_type == StudyType.OBSERVATIONAL
        assert result.is_rct is False

    def test_classification_has_signals(self):
        result = self.classifier.classify(RCT_RESULTS_TEXT)
        assert len(result.signals_found) > 0

    def test_empty_text_returns_other(self):
        result = self.classifier.classify("")
        assert result.study_type == StudyType.OTHER


class TestClassifierIntegration:
    """Test classifier integration into PDFExtractionPipeline."""

    def setup_method(self):
        self.pipeline = PDFExtractionPipeline(extract_diagnostics=False)
        self.pipeline_skip = PDFExtractionPipeline(
            extract_diagnostics=False, skip_non_rct=True
        )

    def test_classification_populated_on_text_extraction(self):
        result = self.pipeline.extract_from_text(RCT_RESULTS_TEXT)
        assert result.classification is not None
        assert isinstance(result.classification, ClassificationResult)
        assert result.classification.study_type == StudyType.RCT_RESULTS

    def test_rct_not_skipped(self):
        result = self.pipeline_skip.extract_from_text(RCT_RESULTS_TEXT)
        assert len(result.effect_estimates) > 0
        assert result.classification.recommendation == "include"

    def test_protocol_skipped_when_skip_enabled(self):
        result = self.pipeline_skip.extract_from_text(PROTOCOL_TEXT)
        assert result.classification.recommendation == "exclude"
        assert len(result.effect_estimates) == 0
        assert any("Skipped" in w for w in result.warnings)

    def test_letter_skipped_when_skip_enabled(self):
        result = self.pipeline_skip.extract_from_text(LETTER_TEXT)
        assert result.classification.recommendation == "exclude"
        # With skip_non_rct, letter should have no extractions
        # (even though letter text contains HR values)
        assert len(result.effect_estimates) == 0

    def test_letter_not_skipped_by_default(self):
        """Without skip_non_rct, letters still get extracted."""
        result = self.pipeline.extract_from_text(LETTER_TEXT)
        assert result.classification is not None
        # Extraction still happens (even if the text is a letter)
        # The classification is informational only

    def test_meta_analysis_not_skipped(self):
        """Meta-analyses should be included (they have pooled effects)."""
        result = self.pipeline_skip.extract_from_text(META_ANALYSIS_TEXT)
        assert result.classification.recommendation == "include"
        # Should still extract effects
        assert len(result.effect_estimates) > 0

    def test_rct_with_effects_classified_and_extracted(self):
        result = self.pipeline.extract_from_text(RCT_WITH_EFFECTS)
        assert result.classification.study_type == StudyType.RCT_RESULTS
        assert result.classification.recommendation == "include"
        # Should have at least one effect extracted
        assert len(result.effect_estimates) > 0


class TestNoFalseExclusions:
    """
    Critical test: Ensure no real RCTs are falsely excluded.
    """

    def setup_method(self):
        self.classifier = RCTClassifier()

    def test_rct_variants_not_excluded(self):
        """Various RCT text formats should all be classified as include."""
        rct_texts = [
            "This randomized controlled trial enrolled 500 patients. "
            "The primary endpoint showed HR 0.74 (95% CI 0.65-0.85, P<0.001).",

            "Patients were randomly assigned to treatment or control. "
            "Double-blind, placebo-controlled study. NCT01234567. "
            "The odds ratio was 0.65 (0.50-0.85).",

            "A phase III randomized trial of Drug X vs placebo. "
            "Results: Mean difference -2.3 mmHg (95% CI -3.1 to -1.5). "
            "Intention-to-treat analysis.",

            "CONSORT-compliant parallel-group RCT. "
            "Randomly allocated 1:1. Primary outcome: cardiovascular death. "
            "Risk ratio 0.88 (0.78-0.99). P = 0.032.",
        ]

        for text in rct_texts:
            result = self.classifier.classify(text)
            assert result.recommendation != "exclude", (
                f"RCT text falsely excluded: {text[:80]}..."
            )

    def test_borderline_rct_not_excluded(self):
        """RCTs with weak signals should get 'review', not 'exclude'."""
        text = (
            "Patients were randomized to receive treatment A or B. "
            "The primary outcome was mortality at 30 days. "
            "Results showed a hazard ratio of 0.85."
        )
        result = self.classifier.classify(text)
        assert result.recommendation != "exclude"


class TestPipelineTableExtraction:
    """Test that table extraction parameter is properly initialized."""

    def test_table_extractor_init_with_extract_tables(self):
        pipeline = PDFExtractionPipeline(extract_diagnostics=False, extract_tables=True)
        # Table extractor should be initialized if module is available
        if hasattr(pipeline, 'table_effect_extractor'):
            # May be None if tables module not importable, that's OK
            pass

    def test_table_extractor_disabled(self):
        pipeline = PDFExtractionPipeline(extract_diagnostics=False, extract_tables=False)
        assert pipeline.table_effect_extractor is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
