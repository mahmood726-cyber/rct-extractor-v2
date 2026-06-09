"""
Benchmark Suite for RCT Extractor v2

Compares ensemble extraction accuracy vs individual extractors.
Tests against gold standard datasets and CTGov ground truth.
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkCase:
    """A single benchmark test case"""
    case_id: str
    source: str  # 'gold', 'ctgov', 'synthetic'
    text: str
    nct_id: Optional[str] = None

    # Expected values (ground truth)
    expected_hr: Optional[float] = None
    expected_hr_ci: Optional[Tuple[float, float]] = None
    expected_or: Optional[float] = None
    expected_or_ci: Optional[Tuple[float, float]] = None
    expected_rr: Optional[float] = None
    expected_rr_ci: Optional[Tuple[float, float]] = None

    # Expected endpoint
    expected_endpoint: Optional[str] = None
    expected_measure_type: str = "HR"

    # Metadata
    trial_name: str = ""
    journal: str = ""
    notes: str = ""


@dataclass
class ExtractorMetrics:
    """Metrics for a single extractor"""
    extractor_id: str
    name: str

    # Accuracy metrics
    total_cases: int = 0
    correct_values: int = 0
    correct_cis: int = 0
    correct_endpoints: int = 0

    # Error metrics
    mean_absolute_error: float = 0.0
    mean_relative_error: float = 0.0
    max_error: float = 0.0

    # Timing
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0

    # Grade distribution
    grade_a_count: int = 0
    grade_b_count: int = 0
    grade_c_count: int = 0
    grade_d_count: int = 0
    grade_f_count: int = 0

    @property
    def accuracy(self) -> float:
        if self.total_cases == 0:
            return 0.0
        return self.correct_values / self.total_cases

    @property
    def ci_accuracy(self) -> float:
        if self.total_cases == 0:
            return 0.0
        return self.correct_cis / self.total_cases


@dataclass
class BenchmarkResult:
    """Complete benchmark results"""
    timestamp: str
    total_cases: int
    total_time_seconds: float

    # Per-extractor metrics
    e1_metrics: ExtractorMetrics  # Python extractor
    e2_metrics: ExtractorMetrics  # JS extractor
    e3_metrics: ExtractorMetrics  # Wasserstein
    e4_metrics: ExtractorMetrics  # TruthCert
    ensemble_metrics: ExtractorMetrics  # Merged ensemble

    # Comparison
    ensemble_improvement: float = 0.0  # vs best individual
    agreement_rate: float = 0.0  # How often extractors agree

    # Detailed results
    case_results: List[Dict[str, Any]] = field(default_factory=list)


class BenchmarkSuite:
    """
    Benchmark suite for comparing extractors.

    Runs all 4 extractors plus ensemble merger on test cases
    and compares accuracy, timing, and agreement.
    """

    def __init__(
        self,
        tolerance: float = 0.05,
        ci_tolerance: float = 0.10
    ):
        self.tolerance = tolerance
        self.ci_tolerance = ci_tolerance

        # Initialize extractors (lazy loading)
        self._e1_extractor = None
        self._e2_bridge = None
        self._e3_bridge = None
        self._e4_bridge = None
        self._ensemble_merger = None

    @property
    def e1_extractor(self):
        """Python extractor (E1)"""
        if self._e1_extractor is None:
            from ..core.extractor import RCTExtractor
            self._e1_extractor = RCTExtractor()
        return self._e1_extractor

    @property
    def e2_bridge(self):
        """JS extractor bridge (E2) — archived in v5.0"""
        raise NotImplementedError("JS bridge archived in v5.0. Use core extractors.")

    @property
    def e3_bridge(self):
        """Wasserstein bridge (E3) — archived in v5.0"""
        raise NotImplementedError("Wasserstein bridge archived in v5.0. Use core extractors.")

    @property
    def e4_bridge(self):
        """TruthCert bridge (E4)"""
        if self._e4_bridge is None:
            from ..bridges.truthcert_bridge import TruthCertBridge
            self._e4_bridge = TruthCertBridge()
        return self._e4_bridge

    @property
    def ensemble_merger(self):
        """Ensemble merger"""
        if self._ensemble_merger is None:
            from ..core.ensemble import EnsembleMerger
            self._ensemble_merger = EnsembleMerger()
        return self._ensemble_merger

    def run_benchmark(
        self,
        cases: List[BenchmarkCase],
        skip_e2: bool = False,
        skip_e3: bool = True,  # Wasserstein needs KM curves, skip by default
        skip_e4: bool = False
    ) -> BenchmarkResult:
        """
        Run benchmark on test cases.

        Args:
            cases: List of benchmark cases
            skip_e2: Skip JS extractor (requires Node.js)
            skip_e3: Skip Wasserstein (requires KM curve data)
            skip_e4: Skip TruthCert (requires network)

        Returns:
            BenchmarkResult with all metrics
        """
        start_time = time.time()

        # Initialize metrics
        e1_metrics = ExtractorMetrics(extractor_id='E1', name='Python Extractor')
        e2_metrics = ExtractorMetrics(extractor_id='E2', name='JS Extractor')
        e3_metrics = ExtractorMetrics(extractor_id='E3', name='Wasserstein')
        e4_metrics = ExtractorMetrics(extractor_id='E4', name='TruthCert')
        ensemble_metrics = ExtractorMetrics(extractor_id='ENS', name='Ensemble')

        case_results = []
        agreement_count = 0

        for case in cases:
            case_result = self._run_single_case(
                case, skip_e2, skip_e3, skip_e4
            )

            # Update metrics
            self._update_metrics(e1_metrics, case_result, 'e1')
            if not skip_e2:
                self._update_metrics(e2_metrics, case_result, 'e2')
            if not skip_e3:
                self._update_metrics(e3_metrics, case_result, 'e3')
            if not skip_e4:
                self._update_metrics(e4_metrics, case_result, 'e4')
            self._update_metrics(ensemble_metrics, case_result, 'ensemble')

            # Check agreement
            if case_result.get('all_agree', False):
                agreement_count += 1

            case_results.append(case_result)

        # Finalize metrics
        for metrics in [e1_metrics, e2_metrics, e3_metrics, e4_metrics, ensemble_metrics]:
            if metrics.total_cases > 0:
                metrics.avg_time_ms = metrics.total_time_ms / metrics.total_cases
                if metrics.correct_values > 0:
                    metrics.mean_absolute_error /= metrics.correct_values
                    metrics.mean_relative_error /= metrics.correct_values

        # Calculate ensemble improvement
        best_individual = max(
            e1_metrics.accuracy,
            e2_metrics.accuracy if not skip_e2 else 0,
            e4_metrics.accuracy if not skip_e4 else 0
        )
        if best_individual > 0:
            ensemble_improvement = (ensemble_metrics.accuracy - best_individual) / best_individual
        else:
            ensemble_improvement = 0.0

        total_time = time.time() - start_time

        return BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            total_cases=len(cases),
            total_time_seconds=total_time,
            e1_metrics=e1_metrics,
            e2_metrics=e2_metrics,
            e3_metrics=e3_metrics,
            e4_metrics=e4_metrics,
            ensemble_metrics=ensemble_metrics,
            ensemble_improvement=ensemble_improvement,
            agreement_rate=agreement_count / len(cases) if cases else 0,
            case_results=case_results
        )

    def _run_single_case(
        self,
        case: BenchmarkCase,
        skip_e2: bool,
        skip_e3: bool,
        skip_e4: bool
    ) -> Dict[str, Any]:
        """Run all extractors on a single case"""
        result = {
            'case_id': case.case_id,
            'expected_value': case.expected_hr or case.expected_or or case.expected_rr,
            'expected_ci': case.expected_hr_ci or case.expected_or_ci or case.expected_rr_ci,
            'measure_type': case.expected_measure_type
        }

        # E1: Python extractor
        t1_start = time.time()
        try:
            e1_results = self._extract_e1(case.text)
            result['e1_results'] = e1_results
            result['e1_time_ms'] = (time.time() - t1_start) * 1000
            result['e1_value'] = self._get_primary_value(e1_results, case.expected_measure_type)
            result['e1_correct'] = self._check_correct(result['e1_value'], result['expected_value'])
        except Exception as e:
            logger.error(f"E1 error on {case.case_id}: {e}")
            result['e1_error'] = str(e)

        # E2: JS extractor
        if not skip_e2:
            t2_start = time.time()
            try:
                e2_results = self.e2_bridge.extract_to_ensemble_format(case.text)
                result['e2_results'] = e2_results
                result['e2_time_ms'] = (time.time() - t2_start) * 1000
                result['e2_value'] = self._get_primary_value(e2_results, case.expected_measure_type)
                result['e2_correct'] = self._check_correct(result['e2_value'], result['expected_value'])
            except Exception as e:
                logger.error(f"E2 error on {case.case_id}: {e}")
                result['e2_error'] = str(e)

        # E3: Wasserstein (skip by default, needs KM data)
        if not skip_e3:
            result['e3_results'] = []
            result['e3_value'] = None

        # E4: TruthCert
        if not skip_e4 and case.nct_id:
            t4_start = time.time()
            try:
                e4_results = self.e4_bridge.extract_to_ensemble_format(case.nct_id)
                # Filter to only primary outcomes or matching values
                e4_filtered = [
                    r for r in e4_results
                    if r.get('ctgov_outcome_type') == 'PRIMARY'
                    or (result.get('e1_value') and self._values_close(r.get('value'), result.get('e1_value')))
                ]
                result['e4_results'] = e4_filtered if e4_filtered else e4_results[:1]
                result['e4_time_ms'] = (time.time() - t4_start) * 1000
                result['e4_value'] = self._get_primary_value(result['e4_results'], case.expected_measure_type)
                result['e4_correct'] = self._check_correct(result['e4_value'], result['expected_value'])
            except Exception as e:
                logger.error(f"E4 error on {case.case_id}: {e}")
                result['e4_error'] = str(e)

        # Ensemble merge - convert dicts to ExtractorResult dataclasses
        try:
            from ..core.ensemble import ExtractorResult
            merged = self.ensemble_merger.merge(
                self._to_extractor_results(result.get('e1_results', []), 'E1'),
                self._to_extractor_results(result.get('e2_results', []), 'E2'),
                self._to_extractor_results(result.get('e3_results', []), 'E3'),
                self._to_extractor_results(result.get('e4_results', []), 'E4')
            )
            if merged:
                result['ensemble_results'] = [m.__dict__ for m in merged]
                result['ensemble_value'] = merged[0].value if merged else None
                result['ensemble_grade'] = merged[0].confidence_grade.value if merged else 'F'
                result['ensemble_correct'] = self._check_correct(
                    result['ensemble_value'], result['expected_value']
                )
        except Exception as e:
            logger.error(f"Ensemble error on {case.case_id}: {e}")
            result['ensemble_error'] = str(e)

        # Check agreement
        values = [
            result.get('e1_value'),
            result.get('e2_value'),
            result.get('e4_value')
        ]
        values = [v for v in values if v is not None]
        if len(values) >= 2:
            result['all_agree'] = all(
                self._values_close(v, values[0]) for v in values
            )
        else:
            result['all_agree'] = False

        return result

    def _extract_e1(self, text: str) -> List[Dict[str, Any]]:
        """Extract using Python extractor and convert to ensemble format"""
        from ..core.extractor import NumericParser

        results = []

        # Extract HRs - parse_hazard_ratio returns dict or None
        hr = NumericParser.parse_hazard_ratio(text)
        if hr:
            results.append({
                'extractor_id': 'E1',
                'endpoint': 'PRIMARY_OUTCOME',
                'value': hr.get('hr'),
                'ci_low': hr.get('ci_low'),
                'ci_high': hr.get('ci_high'),
                'measure_type': 'HR',
                'has_provenance': bool(hr.get('raw_match')),
                'provenance_text': hr.get('raw_match'),
                'confidence_score': 0.85
            })

        # Extract ORs - parse_odds_ratio returns dict or None
        or_val = NumericParser.parse_odds_ratio(text)
        if or_val:
            results.append({
                'extractor_id': 'E1',
                'endpoint': 'PRIMARY_OUTCOME',
                'value': or_val.get('or'),
                'ci_low': or_val.get('ci_low'),
                'ci_high': or_val.get('ci_high'),
                'measure_type': 'OR',
                'has_provenance': bool(or_val.get('raw_match')),
                'provenance_text': or_val.get('raw_match'),
                'confidence_score': 0.85
            })

        # Extract RRs
        rr = NumericParser.parse_relative_risk(text)
        if rr:
            results.append({
                'extractor_id': 'E1',
                'endpoint': 'PRIMARY_OUTCOME',
                'value': rr.get('rr'),
                'ci_low': rr.get('ci_low'),
                'ci_high': rr.get('ci_high'),
                'measure_type': 'RR',
                'has_provenance': bool(rr.get('raw_match')),
                'provenance_text': rr.get('raw_match'),
                'confidence_score': 0.85
            })

        # Extract RDs (Risk Differences)
        rd = NumericParser.parse_risk_difference(text)
        if rd:
            results.append({
                'extractor_id': 'E1',
                'endpoint': 'PRIMARY_OUTCOME',
                'value': rd.get('rd'),
                'ci_low': rd.get('ci_low'),
                'ci_high': rd.get('ci_high'),
                'measure_type': 'RD',
                'has_provenance': bool(rd.get('raw_match')),
                'provenance_text': rd.get('raw_match'),
                'confidence_score': 0.85
            })

        # Extract MDs (Mean Differences)
        md = NumericParser.parse_mean_difference(text)
        if md:
            results.append({
                'extractor_id': 'E1',
                'endpoint': 'PRIMARY_OUTCOME',
                'value': md.get('md'),
                'ci_low': md.get('ci_low'),
                'ci_high': md.get('ci_high'),
                'measure_type': 'MD',
                'has_provenance': bool(md.get('raw_match')),
                'provenance_text': md.get('raw_match'),
                'confidence_score': 0.85
            })

        return results

    def _to_extractor_results(
        self,
        dicts: List[Dict[str, Any]],
        extractor_id: str
    ) -> List:
        """Convert list of dicts to ExtractorResult dataclasses"""
        from ..core.ensemble import ExtractorResult

        results = []
        for d in dicts:
            if d is None:
                continue
            results.append(ExtractorResult(
                extractor_id=d.get('extractor_id', extractor_id),
                endpoint=d.get('endpoint', 'UNKNOWN'),
                value=d.get('value'),
                ci_low=d.get('ci_low'),
                ci_high=d.get('ci_high'),
                measure_type=d.get('measure_type', 'HR'),
                has_provenance=d.get('has_provenance', False),
                provenance_text=d.get('provenance_text'),
                is_verified=d.get('is_verified', False),
                wasserstein_grade=d.get('wasserstein_grade'),
                raw_match=d.get('raw_match'),
                confidence_score=d.get('confidence_score', 0.5)
            ))
        return results

    def _get_primary_value(
        self,
        results: List[Dict[str, Any]],
        measure_type: str
    ) -> Optional[float]:
        """Get primary value from results matching measure type"""
        for r in results:
            if r.get('measure_type') == measure_type:
                return r.get('value')

        # Fall back to first result
        if results:
            return results[0].get('value')

        return None

    def _check_correct(
        self,
        extracted: Optional[float],
        expected: Optional[float]
    ) -> bool:
        """Check if extracted value is correct within tolerance"""
        if extracted is None or expected is None:
            return False

        return self._values_close(extracted, expected)

    def _values_close(self, val1: float, val2: float) -> bool:
        """Check if two values are close within tolerance"""
        if val1 is None or val2 is None:
            return False

        if val2 == 0:
            return abs(val1) < self.tolerance

        return abs(val1 - val2) / abs(val2) <= self.tolerance

    def _update_metrics(
        self,
        metrics: ExtractorMetrics,
        case_result: Dict[str, Any],
        extractor_key: str
    ):
        """Update metrics from case result"""
        metrics.total_cases += 1

        value_key = f'{extractor_key}_value'
        correct_key = f'{extractor_key}_correct'
        time_key = f'{extractor_key}_time_ms'

        if case_result.get(correct_key, False):
            metrics.correct_values += 1

        if time_key in case_result:
            metrics.total_time_ms += case_result[time_key]

        # Calculate errors
        extracted = case_result.get(value_key)
        expected = case_result.get('expected_value')

        if extracted is not None and expected is not None:
            abs_error = abs(extracted - expected)
            rel_error = abs_error / abs(expected) if expected != 0 else abs_error

            metrics.mean_absolute_error += abs_error
            metrics.mean_relative_error += rel_error
            metrics.max_error = max(metrics.max_error, abs_error)

        # Track grades for ensemble
        if extractor_key == 'ensemble':
            grade = case_result.get('ensemble_grade', 'F')
            if grade == 'A':
                metrics.grade_a_count += 1
            elif grade == 'B':
                metrics.grade_b_count += 1
            elif grade == 'C':
                metrics.grade_c_count += 1
            elif grade == 'D':
                metrics.grade_d_count += 1
            else:
                metrics.grade_f_count += 1


# ============================================================
# BENCHMARK DATA LOADERS
# ============================================================

def load_gold_cases(gold_dir: Path) -> List[BenchmarkCase]:
    """Load benchmark cases from gold standard JSONL files"""
    cases = []

    for jsonl_file in gold_dir.glob("*.jsonl"):
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    expected = data.get('expected', {})
                    measure_type = expected.get('measure_type', 'HR')

                    # Get expected value and CI based on measure type
                    expected_value = None
                    expected_ci = None

                    if measure_type == 'HR':
                        expected_value = expected.get('hr')
                        if expected.get('hr_ci_low'):
                            expected_ci = (expected.get('hr_ci_low'), expected.get('hr_ci_high'))
                    elif measure_type == 'OR':
                        expected_value = expected.get('or')
                        if expected.get('or_ci_low'):
                            expected_ci = (expected.get('or_ci_low'), expected.get('or_ci_high'))
                    elif measure_type == 'RR':
                        expected_value = expected.get('rr')
                        if expected.get('rr_ci_low'):
                            expected_ci = (expected.get('rr_ci_low'), expected.get('rr_ci_high'))
                    elif measure_type == 'RD':
                        expected_value = expected.get('rd')
                        if expected.get('rd_ci_low'):
                            expected_ci = (expected.get('rd_ci_low'), expected.get('rd_ci_high'))
                    elif measure_type == 'MD':
                        expected_value = expected.get('md')
                        if expected.get('md_ci_low'):
                            expected_ci = (expected.get('md_ci_low'), expected.get('md_ci_high'))

                    case = BenchmarkCase(
                        case_id=f"{jsonl_file.stem}_{line_num}",
                        source='gold',
                        text=data.get('text', ''),
                        nct_id=data.get('nct_id'),
                        expected_hr=expected_value if measure_type == 'HR' else None,
                        expected_hr_ci=expected_ci if measure_type == 'HR' else None,
                        expected_or=expected_value if measure_type == 'OR' else None,
                        expected_or_ci=expected_ci if measure_type == 'OR' else None,
                        expected_rr=expected_value if measure_type == 'RR' else None,
                        expected_rr_ci=expected_ci if measure_type == 'RR' else None,
                        expected_endpoint=expected.get('endpoint'),
                        expected_measure_type=measure_type,
                        trial_name=data.get('trial_name', ''),
                        journal=data.get('journal', '')
                    )
                    cases.append(case)
                except json.JSONDecodeError as e:
                    logger.warning(f"Error parsing {jsonl_file}:{line_num}: {e}")

    return cases


def create_synthetic_cases() -> List[BenchmarkCase]:
    """Create synthetic benchmark cases for testing"""
    return [
        BenchmarkCase(
            case_id='synth_001',
            source='synthetic',
            text='The hazard ratio for the primary outcome was 0.80 (95% CI, 0.73 to 0.87).',
            expected_hr=0.80,
            expected_hr_ci=(0.73, 0.87),
            expected_measure_type='HR'
        ),
        BenchmarkCase(
            case_id='synth_002',
            source='synthetic',
            text='Treatment reduced mortality with HR 0.65 (95% confidence interval 0.55-0.77, P<0.001).',
            expected_hr=0.65,
            expected_hr_ci=(0.55, 0.77),
            expected_measure_type='HR'
        ),
        BenchmarkCase(
            case_id='synth_003',
            source='synthetic',
            text='The odds ratio for adverse events was 1.23 (95% CI: 1.05-1.44).',
            expected_or=1.23,
            expected_or_ci=(1.05, 1.44),
            expected_measure_type='OR'
        ),
        BenchmarkCase(
            case_id='synth_004',
            source='synthetic',
            text='Cardiovascular death or hospitalization for heart failure occurred with a hazard ratio of 0.75 (95% CI, 0.65 to 0.86; P<0.001).',
            expected_hr=0.75,
            expected_hr_ci=(0.65, 0.86),
            expected_measure_type='HR',
            expected_endpoint='HF_HOSPITALIZATION'
        ),
        BenchmarkCase(
            case_id='synth_005',
            source='synthetic',
            text='The hazard ratio in the empagliflozin group was 0.68 (95% confidence interval [CI], 0.57 to 0.82).',
            expected_hr=0.68,
            expected_hr_ci=(0.57, 0.82),
            expected_measure_type='HR'
        ),
    ]


# ============================================================
# REPORT GENERATION
# ============================================================

def generate_benchmark_report(result: BenchmarkResult) -> str:
    """Generate human-readable benchmark report"""
    lines = [
        "=" * 60,
        "RCT EXTRACTOR v2 BENCHMARK REPORT",
        "=" * 60,
        f"Timestamp: {result.timestamp}",
        f"Total Cases: {result.total_cases}",
        f"Total Time: {result.total_time_seconds:.2f}s",
        "",
        "ACCURACY COMPARISON",
        "-" * 40,
    ]

    # Metrics table
    metrics_list = [
        result.e1_metrics,
        result.e2_metrics,
        result.e4_metrics,
        result.ensemble_metrics
    ]

    for m in metrics_list:
        if m.total_cases > 0:
            lines.append(
                f"{m.name:20s}: {m.accuracy*100:5.1f}% accuracy "
                f"({m.correct_values}/{m.total_cases}), "
                f"MAE={m.mean_absolute_error:.4f}, "
                f"Avg {m.avg_time_ms:.0f}ms"
            )

    lines.extend([
        "",
        "ENSEMBLE PERFORMANCE",
        "-" * 40,
        f"Improvement vs Best Individual: {result.ensemble_improvement*100:+.1f}%",
        f"Agreement Rate: {result.agreement_rate*100:.1f}%",
        "",
        "GRADE DISTRIBUTION (Ensemble)",
        "-" * 40,
        f"Grade A (auto-accept):  {result.ensemble_metrics.grade_a_count}",
        f"Grade B (accept+note):  {result.ensemble_metrics.grade_b_count}",
        f"Grade C (review):       {result.ensemble_metrics.grade_c_count}",
        f"Grade D (low-conf):     {result.ensemble_metrics.grade_d_count}",
        f"Grade F (reject):       {result.ensemble_metrics.grade_f_count}",
        "",
        "=" * 60
    ])

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Run benchmark with synthetic cases
    print("Running benchmark with synthetic cases...\n")

    suite = BenchmarkSuite()
    cases = create_synthetic_cases()

    # Run without E2 (needs Node.js) and E4 (needs network)
    result = suite.run_benchmark(cases, skip_e2=True, skip_e3=True, skip_e4=True)

    report = generate_benchmark_report(result)
    print(report)

    # Show individual case results
    print("\nDETAILED RESULTS:")
    print("-" * 40)
    for case_result in result.case_results:
        case_id = case_result['case_id']
        expected = case_result.get('expected_value')
        e1_val = case_result.get('e1_value')
        ens_val = case_result.get('ensemble_value')
        e1_ok = "✓" if case_result.get('e1_correct') else "✗"
        ens_ok = "✓" if case_result.get('ensemble_correct') else "✗"

        print(f"{case_id}: expected={expected}, E1={e1_val} {e1_ok}, ENS={ens_val} {ens_ok}")
