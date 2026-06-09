"""
Evaluation Framework for RCT Extractor
Compares extracted data against gold standard datasets.
Provides detailed metrics for each field type.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json
import logging
from datetime import datetime
from enum import Enum

from .models import (
    ExtractionOutput, ExtractionRecord, HazardRatioCI, OddsRatioCI,
    RiskRatioCI, MeanDifference, BinaryOutcome, ExtractionConfidence
)

logger = logging.getLogger(__name__)


class MatchLevel(Enum):
    """How closely an extraction matches gold standard"""
    EXACT = "exact"           # Values match perfectly
    CLOSE = "close"           # Within tolerance
    PARTIAL = "partial"       # Some fields match
    MISMATCH = "mismatch"     # Values don't match
    MISSING = "missing"       # Not extracted
    EXTRA = "extra"           # Extracted but not in gold


@dataclass
class FieldComparison:
    """Comparison result for a single field"""
    field_name: str
    gold_value: Any
    extracted_value: Any
    match_level: MatchLevel
    error_magnitude: Optional[float] = None  # For numeric fields


@dataclass
class RecordComparison:
    """Comparison result for a single extraction record"""
    endpoint: str
    gold_record_id: Optional[str] = None
    extracted_record_id: Optional[str] = None
    match_level: MatchLevel = MatchLevel.MISSING
    field_comparisons: List[FieldComparison] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class EvaluationMetrics:
    """Overall evaluation metrics"""
    # Counts
    total_gold_records: int = 0
    total_extracted_records: int = 0
    matched_records: int = 0
    missing_records: int = 0
    extra_records: int = 0

    # Field-level metrics
    hr_metrics: Dict[str, float] = field(default_factory=dict)
    ci_metrics: Dict[str, float] = field(default_factory=dict)
    events_metrics: Dict[str, float] = field(default_factory=dict)
    endpoint_metrics: Dict[str, float] = field(default_factory=dict)

    # Overall accuracy
    overall_accuracy: float = 0.0
    exact_match_rate: float = 0.0
    close_match_rate: float = 0.0

    # Error analysis
    mean_hr_error: float = 0.0
    mean_ci_error: float = 0.0
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0


@dataclass
class EvaluationReport:
    """Complete evaluation report"""
    pdf_file: str
    gold_file: str
    timestamp: str
    metrics: EvaluationMetrics
    record_comparisons: List[RecordComparison] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "pdf_file": self.pdf_file,
            "gold_file": self.gold_file,
            "timestamp": self.timestamp,
            "metrics": {
                "total_gold_records": self.metrics.total_gold_records,
                "total_extracted_records": self.metrics.total_extracted_records,
                "matched_records": self.metrics.matched_records,
                "missing_records": self.metrics.missing_records,
                "extra_records": self.metrics.extra_records,
                "overall_accuracy": self.metrics.overall_accuracy,
                "exact_match_rate": self.metrics.exact_match_rate,
                "close_match_rate": self.metrics.close_match_rate,
                "hr_metrics": self.metrics.hr_metrics,
                "ci_metrics": self.metrics.ci_metrics,
                "mean_hr_error": self.metrics.mean_hr_error,
                "mean_ci_error": self.metrics.mean_ci_error,
            },
            "record_comparisons": [
                {
                    "endpoint": rc.endpoint,
                    "match_level": rc.match_level.value,
                    "fields": [
                        {
                            "field": fc.field_name,
                            "gold": fc.gold_value,
                            "extracted": fc.extracted_value,
                            "match": fc.match_level.value,
                            "error": fc.error_magnitude
                        }
                        for fc in rc.field_comparisons
                    ],
                    "notes": rc.notes
                }
                for rc in self.record_comparisons
            ],
            "summary": self.summary
        }


# ============================================================
# TOLERANCE SETTINGS
# ============================================================

class EvaluationTolerance:
    """Tolerance settings for numeric comparisons"""

    # Relative tolerance for ratio measures (HR, OR, RR)
    RATIO_REL_TOL = 0.01  # 1% relative tolerance

    # Absolute tolerance for CI bounds
    CI_ABS_TOL = 0.02

    # Event count tolerance (allow rounding)
    EVENTS_TOL = 1

    # Percentage tolerance
    PERCENTAGE_TOL = 0.5

    # Endpoint matching threshold (fuzzy match score)
    ENDPOINT_THRESHOLD = 80


# ============================================================
# GOLD STANDARD LOADER
# ============================================================

@dataclass
class GoldRecord:
    """Single gold standard record"""
    endpoint_canonical: str
    endpoint_raw: Optional[str] = None
    timepoint: Optional[str] = None

    # Effect estimate (one of these)
    hr: Optional[float] = None
    hr_ci_low: Optional[float] = None
    hr_ci_high: Optional[float] = None

    or_value: Optional[float] = None
    or_ci_low: Optional[float] = None
    or_ci_high: Optional[float] = None

    rr: Optional[float] = None
    rr_ci_low: Optional[float] = None
    rr_ci_high: Optional[float] = None

    # Binary outcomes
    arm_events: Optional[Dict[str, Dict[str, int]]] = None  # {arm_id: {events, n}}

    # P-value
    p_value: Optional[float] = None

    # Source info
    page_number: Optional[int] = None
    source_type: Optional[str] = None  # table, text, figure


@dataclass
class GoldDataset:
    """Complete gold standard dataset for a PDF"""
    pdf_file: str
    paper_title: Optional[str] = None
    nct_id: Optional[str] = None
    arms: List[Dict[str, Any]] = field(default_factory=list)
    records: List[GoldRecord] = field(default_factory=list)
    annotator: Optional[str] = None
    annotation_date: Optional[str] = None


def load_gold_dataset(gold_path: str) -> GoldDataset:
    """Load gold standard from JSONL file"""
    path = Path(gold_path)

    if path.suffix == '.jsonl':
        return _load_jsonl(path)
    elif path.suffix == '.json':
        return _load_json(path)
    else:
        raise ValueError(f"Unsupported gold format: {path.suffix}")


def _load_jsonl(path: Path) -> GoldDataset:
    """Load JSONL format (one record per line)"""
    records = []
    metadata = {}

    with open(path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON on line {line_num}: {e}")
                continue

            if data.get('_type') == 'metadata':
                metadata = data
            else:
                record = GoldRecord(
                    endpoint_canonical=data.get('endpoint_canonical', ''),
                    endpoint_raw=data.get('endpoint_raw'),
                    timepoint=data.get('timepoint'),
                    hr=data.get('hr'),
                    hr_ci_low=data.get('hr_ci_low'),
                    hr_ci_high=data.get('hr_ci_high'),
                    or_value=data.get('or'),
                    or_ci_low=data.get('or_ci_low'),
                    or_ci_high=data.get('or_ci_high'),
                    rr=data.get('rr'),
                    rr_ci_low=data.get('rr_ci_low'),
                    rr_ci_high=data.get('rr_ci_high'),
                    arm_events=data.get('arm_events'),
                    p_value=data.get('p_value'),
                    page_number=data.get('page_number'),
                    source_type=data.get('source_type')
                )
                records.append(record)

    return GoldDataset(
        pdf_file=metadata.get('pdf_file', str(path)),
        paper_title=metadata.get('paper_title'),
        nct_id=metadata.get('nct_id'),
        arms=metadata.get('arms', []),
        records=records,
        annotator=metadata.get('annotator'),
        annotation_date=metadata.get('annotation_date')
    )


def _load_json(path: Path) -> GoldDataset:
    """Load JSON format (single object)"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = []
    for rec_data in data.get('records', []):
        record = GoldRecord(
            endpoint_canonical=rec_data.get('endpoint_canonical', ''),
            endpoint_raw=rec_data.get('endpoint_raw'),
            timepoint=rec_data.get('timepoint'),
            hr=rec_data.get('hr'),
            hr_ci_low=rec_data.get('hr_ci_low'),
            hr_ci_high=rec_data.get('hr_ci_high'),
            or_value=rec_data.get('or'),
            or_ci_low=rec_data.get('or_ci_low'),
            or_ci_high=rec_data.get('or_ci_high'),
            rr=rec_data.get('rr'),
            rr_ci_low=rec_data.get('rr_ci_low'),
            rr_ci_high=rec_data.get('rr_ci_high'),
            arm_events=rec_data.get('arm_events'),
            p_value=rec_data.get('p_value'),
            page_number=rec_data.get('page_number'),
            source_type=rec_data.get('source_type')
        )
        records.append(record)

    return GoldDataset(
        pdf_file=data.get('pdf_file', str(path)),
        paper_title=data.get('paper_title'),
        nct_id=data.get('nct_id'),
        arms=data.get('arms', []),
        records=records,
        annotator=data.get('annotator'),
        annotation_date=data.get('annotation_date')
    )


# ============================================================
# COMPARISON FUNCTIONS
# ============================================================

def compare_numeric(gold: float, extracted: float, rel_tol: float = 0.01, abs_tol: float = 0.02) -> Tuple[MatchLevel, float]:
    """Compare numeric values with tolerance"""
    if gold is None or extracted is None:
        return (MatchLevel.MISSING, None)

    error = abs(gold - extracted)
    rel_error = error / abs(gold) if gold != 0 else error

    if error == 0:
        return (MatchLevel.EXACT, 0.0)
    elif rel_error <= rel_tol or error <= abs_tol:
        return (MatchLevel.CLOSE, error)
    else:
        return (MatchLevel.MISMATCH, error)


def compare_ci(gold_low: float, gold_high: float, ext_low: float, ext_high: float) -> Tuple[MatchLevel, float]:
    """Compare confidence interval bounds"""
    if None in [gold_low, gold_high, ext_low, ext_high]:
        return (MatchLevel.MISSING, None)

    low_match, low_err = compare_numeric(gold_low, ext_low, abs_tol=EvaluationTolerance.CI_ABS_TOL)
    high_match, high_err = compare_numeric(gold_high, ext_high, abs_tol=EvaluationTolerance.CI_ABS_TOL)

    if low_match == MatchLevel.EXACT and high_match == MatchLevel.EXACT:
        return (MatchLevel.EXACT, 0.0)
    elif low_match in [MatchLevel.EXACT, MatchLevel.CLOSE] and high_match in [MatchLevel.EXACT, MatchLevel.CLOSE]:
        return (MatchLevel.CLOSE, (low_err or 0) + (high_err or 0))
    elif low_match != MatchLevel.MISMATCH or high_match != MatchLevel.MISMATCH:
        return (MatchLevel.PARTIAL, max(low_err or 0, high_err or 0))
    else:
        return (MatchLevel.MISMATCH, max(low_err or 0, high_err or 0))


def compare_events(gold: Dict[str, int], extracted: Dict[str, int]) -> Tuple[MatchLevel, float]:
    """Compare events/n values"""
    if not gold or not extracted:
        return (MatchLevel.MISSING, None)

    gold_events = gold.get('events')
    gold_n = gold.get('n')
    ext_events = extracted.get('events')
    ext_n = extracted.get('n')

    events_match, events_err = compare_numeric(gold_events, ext_events, abs_tol=EvaluationTolerance.EVENTS_TOL)
    n_match, n_err = compare_numeric(gold_n, ext_n, abs_tol=EvaluationTolerance.EVENTS_TOL)

    if events_match == MatchLevel.EXACT and n_match == MatchLevel.EXACT:
        return (MatchLevel.EXACT, 0.0)
    elif events_match in [MatchLevel.EXACT, MatchLevel.CLOSE] and n_match in [MatchLevel.EXACT, MatchLevel.CLOSE]:
        return (MatchLevel.CLOSE, (events_err or 0) + (n_err or 0))
    else:
        return (MatchLevel.MISMATCH, max(events_err or 0, n_err or 0))


# ============================================================
# MAIN EVALUATOR
# ============================================================

class Evaluator:
    """Main evaluation class"""

    def __init__(self, tolerance: EvaluationTolerance = None):
        self.tolerance = tolerance or EvaluationTolerance()

    def evaluate(self, extraction: ExtractionOutput, gold: GoldDataset) -> EvaluationReport:
        """Evaluate extraction against gold standard"""
        report = EvaluationReport(
            pdf_file=extraction.source_pdf,
            gold_file=gold.pdf_file,
            timestamp=datetime.now().isoformat(),
            metrics=EvaluationMetrics()
        )

        # Match records
        gold_matched = set()
        ext_matched = set()

        for ext_idx, ext_rec in enumerate(extraction.extractions):
            best_match = None
            best_score = 0

            for gold_idx, gold_rec in enumerate(gold.records):
                if gold_idx in gold_matched:
                    continue

                score = self._match_score(ext_rec, gold_rec)
                if score > best_score:
                    best_score = score
                    best_match = (gold_idx, gold_rec)

            if best_match and best_score >= EvaluationTolerance.ENDPOINT_THRESHOLD:
                gold_idx, gold_rec = best_match
                gold_matched.add(gold_idx)
                ext_matched.add(ext_idx)

                comparison = self._compare_records(gold_rec, ext_rec)
                report.record_comparisons.append(comparison)

        # Handle unmatched gold records (missing)
        for gold_idx, gold_rec in enumerate(gold.records):
            if gold_idx not in gold_matched:
                comparison = RecordComparison(
                    endpoint=gold_rec.endpoint_canonical,
                    gold_record_id=str(gold_idx),
                    match_level=MatchLevel.MISSING,
                    notes=["Gold record not found in extraction"]
                )
                report.record_comparisons.append(comparison)

        # Handle unmatched extractions (extra)
        for ext_idx, ext_rec in enumerate(extraction.extractions):
            if ext_idx not in ext_matched:
                comparison = RecordComparison(
                    endpoint=ext_rec.endpoint_canonical,
                    extracted_record_id=str(ext_idx),
                    match_level=MatchLevel.EXTRA,
                    notes=["Extracted record not in gold standard"]
                )
                report.record_comparisons.append(comparison)

        # Calculate metrics
        report.metrics = self._calculate_metrics(report, gold, extraction)
        report.summary = self._generate_summary(report)

        return report

    def _match_score(self, ext_rec: ExtractionRecord, gold_rec: GoldRecord) -> float:
        """Calculate match score between extracted and gold record"""
        # Simple endpoint matching for now
        if ext_rec.endpoint_canonical == gold_rec.endpoint_canonical:
            return 100.0
        elif ext_rec.endpoint_canonical.lower() in gold_rec.endpoint_canonical.lower():
            return 80.0
        elif gold_rec.endpoint_canonical.lower() in ext_rec.endpoint_canonical.lower():
            return 80.0
        return 0.0

    def _compare_records(self, gold: GoldRecord, extracted: ExtractionRecord) -> RecordComparison:
        """Compare a matched pair of records"""
        comparison = RecordComparison(
            endpoint=gold.endpoint_canonical,
            gold_record_id=gold.endpoint_canonical,
            extracted_record_id=extracted.endpoint_canonical
        )

        field_matches = []

        # Compare HR if present
        if gold.hr is not None:
            if isinstance(extracted.effect_estimate, HazardRatioCI):
                match, err = compare_numeric(gold.hr, extracted.effect_estimate.hr)
                comparison.field_comparisons.append(FieldComparison(
                    field_name="hr",
                    gold_value=gold.hr,
                    extracted_value=extracted.effect_estimate.hr,
                    match_level=match,
                    error_magnitude=err
                ))
                field_matches.append(match)

                # Compare CI
                ci_match, ci_err = compare_ci(
                    gold.hr_ci_low, gold.hr_ci_high,
                    extracted.effect_estimate.ci_low, extracted.effect_estimate.ci_high
                )
                comparison.field_comparisons.append(FieldComparison(
                    field_name="hr_ci",
                    gold_value=f"[{gold.hr_ci_low}, {gold.hr_ci_high}]",
                    extracted_value=f"[{extracted.effect_estimate.ci_low}, {extracted.effect_estimate.ci_high}]",
                    match_level=ci_match,
                    error_magnitude=ci_err
                ))
                field_matches.append(ci_match)
            else:
                comparison.field_comparisons.append(FieldComparison(
                    field_name="hr",
                    gold_value=gold.hr,
                    extracted_value=None,
                    match_level=MatchLevel.MISSING
                ))
                field_matches.append(MatchLevel.MISSING)

        # Compare OR if present
        if gold.or_value is not None:
            if isinstance(extracted.effect_estimate, OddsRatioCI):
                match, err = compare_numeric(gold.or_value, extracted.effect_estimate.or_value)
                comparison.field_comparisons.append(FieldComparison(
                    field_name="or",
                    gold_value=gold.or_value,
                    extracted_value=extracted.effect_estimate.or_value,
                    match_level=match,
                    error_magnitude=err
                ))
                field_matches.append(match)
            else:
                comparison.field_comparisons.append(FieldComparison(
                    field_name="or",
                    gold_value=gold.or_value,
                    extracted_value=None,
                    match_level=MatchLevel.MISSING
                ))
                field_matches.append(MatchLevel.MISSING)

        # Compare binary outcomes
        if gold.arm_events:
            for arm_id, gold_arm_data in gold.arm_events.items():
                ext_arm_data = None
                if extracted.binary_outcomes:
                    for bo in extracted.binary_outcomes:
                        if bo.arm_id == arm_id:
                            ext_arm_data = {'events': bo.events, 'n': bo.n}
                            break

                if ext_arm_data:
                    match, err = compare_events(gold_arm_data, ext_arm_data)
                    comparison.field_comparisons.append(FieldComparison(
                        field_name=f"events_{arm_id}",
                        gold_value=gold_arm_data,
                        extracted_value=ext_arm_data,
                        match_level=match,
                        error_magnitude=err
                    ))
                    field_matches.append(match)
                else:
                    comparison.field_comparisons.append(FieldComparison(
                        field_name=f"events_{arm_id}",
                        gold_value=gold_arm_data,
                        extracted_value=None,
                        match_level=MatchLevel.MISSING
                    ))
                    field_matches.append(MatchLevel.MISSING)

        # Determine overall match level
        if not field_matches:
            comparison.match_level = MatchLevel.MISSING
        elif all(m == MatchLevel.EXACT for m in field_matches):
            comparison.match_level = MatchLevel.EXACT
        elif all(m in [MatchLevel.EXACT, MatchLevel.CLOSE] for m in field_matches):
            comparison.match_level = MatchLevel.CLOSE
        elif any(m in [MatchLevel.EXACT, MatchLevel.CLOSE] for m in field_matches):
            comparison.match_level = MatchLevel.PARTIAL
        else:
            comparison.match_level = MatchLevel.MISMATCH

        return comparison

    def _calculate_metrics(
        self,
        report: EvaluationReport,
        gold: GoldDataset,
        extraction: ExtractionOutput
    ) -> EvaluationMetrics:
        """Calculate evaluation metrics"""
        metrics = EvaluationMetrics()

        metrics.total_gold_records = len(gold.records)
        metrics.total_extracted_records = len(extraction.extractions)

        # Count match types
        exact_matches = 0
        close_matches = 0
        missing = 0
        extra = 0
        hr_errors = []
        ci_errors = []

        for comp in report.record_comparisons:
            if comp.match_level == MatchLevel.EXACT:
                exact_matches += 1
            elif comp.match_level == MatchLevel.CLOSE:
                close_matches += 1
            elif comp.match_level == MatchLevel.MISSING:
                missing += 1
            elif comp.match_level == MatchLevel.EXTRA:
                extra += 1

            # Collect errors
            for fc in comp.field_comparisons:
                if fc.field_name == 'hr' and fc.error_magnitude is not None:
                    hr_errors.append(fc.error_magnitude)
                if fc.field_name == 'hr_ci' and fc.error_magnitude is not None:
                    ci_errors.append(fc.error_magnitude)

        metrics.matched_records = exact_matches + close_matches
        metrics.missing_records = missing
        metrics.extra_records = extra

        # Calculate rates
        if metrics.total_gold_records > 0:
            metrics.exact_match_rate = exact_matches / metrics.total_gold_records
            metrics.close_match_rate = (exact_matches + close_matches) / metrics.total_gold_records
            metrics.overall_accuracy = metrics.close_match_rate
            metrics.false_negative_rate = missing / metrics.total_gold_records

        if metrics.total_extracted_records > 0:
            metrics.false_positive_rate = extra / metrics.total_extracted_records

        # Calculate mean errors
        if hr_errors:
            metrics.mean_hr_error = sum(hr_errors) / len(hr_errors)
        if ci_errors:
            metrics.mean_ci_error = sum(ci_errors) / len(ci_errors)

        # Field-level metrics
        metrics.hr_metrics = {
            "precision": metrics.close_match_rate,
            "recall": metrics.close_match_rate,
            "mean_error": metrics.mean_hr_error
        }

        return metrics

    def _generate_summary(self, report: EvaluationReport) -> str:
        """Generate human-readable summary"""
        m = report.metrics
        lines = [
            "=" * 60,
            "EVALUATION SUMMARY",
            "=" * 60,
            f"Gold records: {m.total_gold_records}",
            f"Extracted records: {m.total_extracted_records}",
            "",
            "MATCH RATES:",
            f"  Exact matches: {m.matched_records - int(m.close_match_rate * m.total_gold_records - m.exact_match_rate * m.total_gold_records)}",
            f"  Close matches: {m.matched_records}",
            f"  Missing: {m.missing_records}",
            f"  Extra: {m.extra_records}",
            "",
            f"ACCURACY: {m.overall_accuracy:.1%}",
            f"  Exact match rate: {m.exact_match_rate:.1%}",
            f"  Close match rate: {m.close_match_rate:.1%}",
            "",
            "ERRORS:",
            f"  Mean HR error: {m.mean_hr_error:.4f}",
            f"  Mean CI error: {m.mean_ci_error:.4f}",
            f"  False positive rate: {m.false_positive_rate:.1%}",
            f"  False negative rate: {m.false_negative_rate:.1%}",
            "=" * 60,
        ]
        return "\n".join(lines)


# ============================================================
# BATCH EVALUATION
# ============================================================

def evaluate_batch(
    pdf_dir: str,
    gold_dir: str,
    extractor,
    output_file: str = None
) -> Dict[str, EvaluationReport]:
    """Evaluate all PDFs in a directory against gold standards"""
    results = {}
    evaluator = Evaluator()

    pdf_path = Path(pdf_dir)
    gold_path = Path(gold_dir)

    for pdf_file in pdf_path.glob("*.pdf"):
        # Find matching gold file
        gold_file = gold_path / f"{pdf_file.stem}.jsonl"
        if not gold_file.exists():
            gold_file = gold_path / f"{pdf_file.stem}.json"

        if not gold_file.exists():
            logger.warning(f"No gold standard for {pdf_file.name}")
            continue

        logger.info(f"Evaluating {pdf_file.name}")

        try:
            # Extract
            extraction = extractor.extract(str(pdf_file))

            # Load gold
            gold = load_gold_dataset(str(gold_file))

            # Evaluate
            report = evaluator.evaluate(extraction, gold)
            results[pdf_file.name] = report

            print(report.summary)
        except Exception as e:
            logger.error(f"Failed to evaluate {pdf_file.name}: {e}")

    # Save aggregate results
    if output_file:
        aggregate = {
            "timestamp": datetime.now().isoformat(),
            "total_pdfs": len(results),
            "results": {
                name: report.to_dict()
                for name, report in results.items()
            }
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(aggregate, f, indent=2)

    return results


# ============================================================
# GOLD DATASET TEMPLATE GENERATOR
# ============================================================

def generate_gold_template(pdf_file: str, output_file: str):
    """Generate empty gold standard template for manual annotation"""
    template = {
        "_type": "metadata",
        "pdf_file": pdf_file,
        "paper_title": "",
        "nct_id": "",
        "arms": [
            {"arm_id": "treatment", "arm_name": "", "n_randomized": None},
            {"arm_id": "control", "arm_name": "", "n_randomized": None}
        ],
        "annotator": "",
        "annotation_date": datetime.now().strftime("%Y-%m-%d")
    }

    example_record = {
        "endpoint_canonical": "CV_DEATH_OR_HF_HOSP",
        "endpoint_raw": "cardiovascular death or hospitalization for heart failure",
        "timepoint": "median_2.4y",
        "hr": None,
        "hr_ci_low": None,
        "hr_ci_high": None,
        "or": None,
        "or_ci_low": None,
        "or_ci_high": None,
        "arm_events": {
            "treatment": {"events": None, "n": None},
            "control": {"events": None, "n": None}
        },
        "p_value": None,
        "page_number": None,
        "source_type": "table"
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(json.dumps(template) + "\n")
        f.write(json.dumps(example_record) + "\n")
        f.write("# Add more records below, one JSON object per line\n")

    logger.info(f"Generated gold template: {output_file}")
