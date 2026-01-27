"""
Tests for evaluation framework
"""

import pytest
import sys
import tempfile
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.evaluation import (
    Evaluator, EvaluationReport, EvaluationMetrics,
    GoldRecord, GoldDataset, load_gold_dataset,
    compare_numeric, compare_ci, compare_events,
    MatchLevel
)
from src.core.models import (
    ExtractionOutput, ExtractionRecord, HazardRatioCI, BinaryOutcome,
    Arm, PaperMetadata, Provenance, Timepoint, EndpointType, ExtractionConfidence
)


class TestNumericComparison:
    """Tests for numeric comparison functions"""

    def test_exact_match(self):
        """Exact values match exactly"""
        level, error = compare_numeric(0.75, 0.75)
        assert level == MatchLevel.EXACT
        assert error == 0.0

    def test_close_match(self):
        """Values within tolerance match closely"""
        level, error = compare_numeric(0.750, 0.752, rel_tol=0.01)
        assert level == MatchLevel.CLOSE

    def test_mismatch(self):
        """Values outside tolerance don't match"""
        level, error = compare_numeric(0.75, 0.85, rel_tol=0.01)
        assert level == MatchLevel.MISMATCH

    def test_none_values(self):
        """None values return missing"""
        level, error = compare_numeric(0.75, None)
        assert level == MatchLevel.MISSING


class TestCIComparison:
    """Tests for CI comparison"""

    def test_exact_ci_match(self):
        """Exact CI bounds match"""
        level, error = compare_ci(0.65, 0.85, 0.65, 0.85)
        assert level == MatchLevel.EXACT

    def test_close_ci_match(self):
        """CI bounds within tolerance match closely"""
        level, error = compare_ci(0.65, 0.85, 0.66, 0.84)
        assert level == MatchLevel.CLOSE


class TestEventsComparison:
    """Tests for events comparison"""

    def test_exact_events_match(self):
        """Exact events/n match"""
        gold = {"events": 100, "n": 500}
        ext = {"events": 100, "n": 500}
        level, error = compare_events(gold, ext)
        assert level == MatchLevel.EXACT


class TestGoldDatasetLoading:
    """Tests for gold dataset loading"""

    def test_load_jsonl(self):
        """Load JSONL format gold dataset"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"_type": "metadata", "pdf_file": "test.pdf"}\n')
            f.write('{"endpoint_canonical": "CV_DEATH", "hr": 0.75, "hr_ci_low": 0.65, "hr_ci_high": 0.87}\n')
            temp_path = f.name

        try:
            gold = load_gold_dataset(temp_path)
            assert gold.pdf_file == "test.pdf"
            assert len(gold.records) == 1
            assert gold.records[0].hr == 0.75
        finally:
            Path(temp_path).unlink()


class TestEvaluator:
    """Tests for main Evaluator class"""

    def create_test_extraction(self):
        """Create test extraction output"""
        provenance = Provenance(
            pdf_file="test.pdf",
            page_number=5,
            raw_text="HR 0.80 (95% CI 0.67-0.95)",
            extraction_method="test"
        )

        return ExtractionOutput(
            source_pdf="test.pdf",
            paper=PaperMetadata(title="Test Trial"),
            arms=[
                Arm(arm_id="treatment", arm_name="Drug A"),
                Arm(arm_id="control", arm_name="Placebo")
            ],
            extractions=[
                ExtractionRecord(
                    endpoint_canonical="CV_DEATH_OR_HF_HOSP",
                    endpoint_raw="cardiovascular death or HF hospitalization",
                    endpoint_type=EndpointType.TIME_TO_EVENT,
                    timepoint=Timepoint(raw_text="median 2.4y"),
                    effect_estimate=HazardRatioCI(
                        hr=0.80,
                        ci_low=0.67,
                        ci_high=0.95,
                        provenance=provenance
                    )
                )
            ],
            overall_confidence=ExtractionConfidence.MEDIUM,
            review_queue=[],
            pages_processed=10,
            tables_found=2,
            extraction_time_seconds=5.0
        )

    def create_test_gold(self):
        """Create test gold dataset"""
        return GoldDataset(
            pdf_file="test.pdf",
            records=[
                GoldRecord(
                    endpoint_canonical="CV_DEATH_OR_HF_HOSP",
                    hr=0.80,
                    hr_ci_low=0.67,
                    hr_ci_high=0.95
                )
            ]
        )

    def test_perfect_match(self):
        """Extraction exactly matches gold"""
        evaluator = Evaluator()
        extraction = self.create_test_extraction()
        gold = self.create_test_gold()

        report = evaluator.evaluate(extraction, gold)

        assert report.metrics.total_gold_records == 1
        assert report.metrics.matched_records == 1
        assert report.metrics.exact_match_rate == 1.0

    def test_missing_record(self):
        """Gold record not in extraction"""
        evaluator = Evaluator()

        extraction = ExtractionOutput(
            source_pdf="test.pdf",
            paper=PaperMetadata(),
            arms=[],
            extractions=[],  # Empty!
            overall_confidence=ExtractionConfidence.REVIEW_REQUIRED,
            review_queue=[],
            pages_processed=10,
            tables_found=0,
            extraction_time_seconds=1.0
        )

        gold = self.create_test_gold()
        report = evaluator.evaluate(extraction, gold)

        assert report.metrics.missing_records == 1
        assert report.metrics.matched_records == 0


class TestReportSerialization:
    """Tests for report serialization"""

    def test_to_dict(self):
        """Report converts to dict correctly"""
        report = EvaluationReport(
            pdf_file="test.pdf",
            gold_file="test_gold.jsonl",
            timestamp="2024-01-01T00:00:00",
            metrics=EvaluationMetrics(
                total_gold_records=5,
                total_extracted_records=4,
                matched_records=3,
                overall_accuracy=0.6
            )
        )

        d = report.to_dict()
        assert d["pdf_file"] == "test.pdf"
        assert d["metrics"]["total_gold_records"] == 5
        assert d["metrics"]["overall_accuracy"] == 0.6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
