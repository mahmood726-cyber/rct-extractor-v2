"""
Regulatory Validation Suite for RCT Extractor
==============================================

Comprehensive IQ/OQ/PQ test suite meeting FDA/EMA requirements.
Generates formal validation evidence suitable for regulatory submissions.

Compliance: 21 CFR Part 11, GAMP 5 Category 5
"""

import sys
import os
import json
import hashlib
import time
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.verified_extraction_pipeline import VerifiedExtractionPipeline
from src.core.ocr_preprocessor import OCRPreprocessor


@dataclass
class TestCase:
    """A single regulatory test case"""
    test_id: str
    category: str  # IQ, OQ, PQ
    subcategory: str
    description: str
    input_text: str
    expected_type: Optional[str] = None
    expected_value: Optional[float] = None
    expected_ci_lower: Optional[float] = None
    expected_ci_upper: Optional[float] = None
    should_extract: bool = True  # False for negative tests
    tolerance: float = 0.01


@dataclass
class TestResult:
    """Result of a single test execution"""
    test_id: str
    passed: bool
    expected: str
    actual: str
    execution_time_ms: float
    timestamp: str
    notes: str = ""


@dataclass
class ValidationReport:
    """Complete validation report"""
    system_name: str
    system_version: str
    validation_date: str
    validator: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float
    iq_results: Dict
    oq_results: Dict
    pq_results: Dict
    test_results: List[TestResult]
    execution_time_seconds: float
    conclusion: str


# =============================================================================
# INSTALLATION QUALIFICATION (IQ) TESTS
# =============================================================================

IQ_TESTS = [
    TestCase(
        test_id="IQ-001-01",
        category="IQ",
        subcategory="Component Verification",
        description="Verify enhanced_extractor_v3.py exists",
        input_text="",
        should_extract=False
    ),
    TestCase(
        test_id="IQ-001-02",
        category="IQ",
        subcategory="Component Verification",
        description="Verify ocr_preprocessor.py exists",
        input_text="",
        should_extract=False
    ),
    TestCase(
        test_id="IQ-001-03",
        category="IQ",
        subcategory="Component Verification",
        description="Verify team_of_rivals.py exists",
        input_text="",
        should_extract=False
    ),
    TestCase(
        test_id="IQ-001-04",
        category="IQ",
        subcategory="Component Verification",
        description="Verify verified_extraction_pipeline.py exists",
        input_text="",
        should_extract=False
    ),
    TestCase(
        test_id="IQ-002-01",
        category="IQ",
        subcategory="Import Verification",
        description="Verify pipeline can be imported",
        input_text="",
        should_extract=False
    ),
    TestCase(
        test_id="IQ-002-02",
        category="IQ",
        subcategory="Import Verification",
        description="Verify OCR preprocessor can be imported",
        input_text="",
        should_extract=False
    ),
]


# =============================================================================
# OPERATIONAL QUALIFICATION (OQ) TESTS
# =============================================================================

OQ_HR_TESTS = [
    # Standard HR formats
    TestCase("OQ-HR-001", "OQ", "HR Extraction", "Standard HR with dash CI",
             "HR 0.75 (95% CI 0.64-0.89)", "HR", 0.75, 0.64, 0.89),
    TestCase("OQ-HR-002", "OQ", "HR Extraction", "HR with 'to' CI format",
             "hazard ratio 0.82 (0.71 to 0.95)", "HR", 0.82, 0.71, 0.95),
    TestCase("OQ-HR-003", "OQ", "HR Extraction", "HR with semicolon and comma CI",
             "HR=0.68; 95% CI: 0.55, 0.84", "HR", 0.68, 0.55, 0.84),
    TestCase("OQ-HR-004", "OQ", "HR Extraction", "Adjusted HR",
             "adjusted HR 0.91 (95% CI 0.83-0.99)", "HR", 0.91, 0.83, 0.99),
    TestCase("OQ-HR-005", "OQ", "HR Extraction", "HR with context",
             "The hazard ratio for mortality was 0.77 (CI 0.65-0.91)", "HR", 0.77, 0.65, 0.91),
    TestCase("OQ-HR-006", "OQ", "HR Extraction", "Parenthetical HR",
             "(HR, 0.72; 95% CI, 0.61 to 0.85)", "HR", 0.72, 0.61, 0.85),
    TestCase("OQ-HR-007", "OQ", "HR Extraction", "HR with square brackets",
             "HR 1.23 [95% CI 1.05-1.44]", "HR", 1.23, 1.05, 1.44),
    TestCase("OQ-HR-008", "OQ", "HR Extraction", "HR for specific outcome",
             "hazard ratio for death: 0.69 (0.58-0.82)", "HR", 0.69, 0.58, 0.82),
    TestCase("OQ-HR-009", "OQ", "HR Extraction", "HR with comma separator",
             "HR 0.78, 95% CI 0.67 to 0.91", "HR", 0.78, 0.67, 0.91),
    TestCase("OQ-HR-010", "OQ", "HR Extraction", "Unadjusted HR",
             "unadjusted hazard ratio was 1.15 (95% CI 0.98-1.35)", "HR", 1.15, 0.98, 1.35),
]

OQ_OR_TESTS = [
    TestCase("OQ-OR-001", "OQ", "OR Extraction", "Standard OR",
             "OR 1.45 (95% CI 1.12-1.88)", "OR", 1.45, 1.12, 1.88),
    TestCase("OQ-OR-002", "OQ", "OR Extraction", "OR with 'to' format",
             "odds ratio 0.72 (0.58 to 0.89)", "OR", 0.72, 0.58, 0.89),
    TestCase("OQ-OR-003", "OQ", "OR Extraction", "Adjusted OR with colon CI",
             "adjusted OR=2.15 (95% CI: 1.62, 2.85)", "OR", 2.15, 1.62, 2.85),
    TestCase("OQ-OR-004", "OQ", "OR Extraction", "Parenthetical OR",
             "(OR 0.89, 95% CI 0.84 to 0.95)", "OR", 0.89, 0.84, 0.95),
    TestCase("OQ-OR-005", "OQ", "OR Extraction", "OR with semicolon",
             "OR: 1.56; 95% CI: 1.21-2.01", "OR", 1.56, 1.21, 2.01),
    TestCase("OQ-OR-006", "OQ", "OR Extraction", "aOR abbreviation",
             "aOR 1.82 (95% CI 1.35-2.46)", "OR", 1.82, 1.35, 2.46),
    TestCase("OQ-OR-007", "OQ", "OR Extraction", "OR with confidence interval spelled out",
             "odds ratio 0.81 (confidence interval 0.67 to 0.98)", "OR", 0.81, 0.67, 0.98),
    TestCase("OQ-OR-008", "OQ", "OR Extraction", "Diagnostic OR",
             "Diagnostic odds ratio: DOR 15.3 (95% CI 9.8-23.9)", "OR", 15.3, 9.8, 23.9),
]

OQ_RR_TESTS = [
    TestCase("OQ-RR-001", "OQ", "RR Extraction", "Standard RR",
             "RR 0.81 (95% CI 0.70-0.94)", "RR", 0.81, 0.70, 0.94),
    TestCase("OQ-RR-002", "OQ", "RR Extraction", "Relative risk spelled out",
             "relative risk 0.65 (0.52 to 0.81)", "RR", 0.65, 0.52, 0.81),
    TestCase("OQ-RR-003", "OQ", "RR Extraction", "RR with semicolon",
             "risk ratio 0.77; 95% CI, 0.69 to 0.85", "RR", 0.77, 0.69, 0.85),
    TestCase("OQ-RR-004", "OQ", "RR Extraction", "Parenthetical RR",
             "(RR 0.85, 95% CI 0.79-0.92)", "RR", 0.85, 0.79, 0.92),
    TestCase("OQ-RR-005", "OQ", "RR Extraction", "Pooled RR",
             "Pooled relative risk: 0.84 (0.74, 0.95)", "RR", 0.84, 0.74, 0.95),
    TestCase("OQ-RR-006", "OQ", "RR Extraction", "Adjusted RR",
             "adjusted RR was 1.28 (95% CI 1.08-1.51)", "RR", 1.28, 1.08, 1.51),
]

OQ_MD_TESTS = [
    TestCase("OQ-MD-001", "OQ", "MD Extraction", "Standard MD",
             "MD -3.2 (95% CI -4.1 to -2.3)", "MD", -3.2, -4.1, -2.3),
    TestCase("OQ-MD-002", "OQ", "MD Extraction", "Mean difference spelled out",
             "mean difference 8.2 points (5.1 to 11.3)", "MD", 8.2, 5.1, 11.3),
    TestCase("OQ-MD-003", "OQ", "MD Extraction", "MD with units",
             "MD -5.2 mmHg (95% CI -7.1 to -3.3)", "MD", -5.2, -7.1, -3.3),
    TestCase("OQ-MD-004", "OQ", "MD Extraction", "WMD format",
             "weighted mean difference -1.12 (95% CI -1.28 to -0.96)", "MD", -1.12, -1.28, -0.96),
    TestCase("OQ-MD-005", "OQ", "MD Extraction", "MD with kg units",
             "MD -2.5 kg, 95% CI -3.1 to -1.9", "MD", -2.5, -3.1, -1.9),
    TestCase("OQ-MD-006", "OQ", "MD Extraction", "MD with days units",
             "MD -1.8 days (95% CI -2.4 to -1.2)", "MD", -1.8, -2.4, -1.2),
]

OQ_SMD_TESTS = [
    TestCase("OQ-SMD-001", "OQ", "SMD Extraction", "Standard SMD",
             "SMD -0.62 (95% CI -0.81 to -0.42)", "SMD", -0.62, -0.81, -0.42),
    TestCase("OQ-SMD-002", "OQ", "SMD Extraction", "Cohen's d",
             "Cohen's d 0.45 (0.28-0.62)", "SMD", 0.45, 0.28, 0.62),
    TestCase("OQ-SMD-003", "OQ", "SMD Extraction", "Hedges' g",
             "Hedges' g -0.35 (-0.52 to -0.18)", "SMD", -0.35, -0.52, -0.18),
    TestCase("OQ-SMD-004", "OQ", "SMD Extraction", "Standardized mean difference spelled out",
             "standardized mean difference -0.88; 95% CI -1.03 to -0.74", "SMD", -0.88, -1.03, -0.74),
    TestCase("OQ-SMD-005", "OQ", "SMD Extraction", "Effect size",
             "effect size: SMD 0.30 (95% CI 0.26-0.34)", "SMD", 0.30, 0.26, 0.34),
]

OQ_OTHER_TESTS = [
    TestCase("OQ-IRR-001", "OQ", "IRR Extraction", "Incidence rate ratio",
             "incidence rate ratio 1.45 (95% CI 1.22-1.72)", "IRR", 1.45, 1.22, 1.72),
    TestCase("OQ-ARD-001", "OQ", "ARD Extraction", "Absolute risk difference",
             "absolute risk difference -2.3% (95% CI -3.8% to -0.8%)", "ARD", -2.3, -3.8, -0.8),
    TestCase("OQ-NNT-001", "OQ", "NNT Extraction", "Number needed to treat",
             "NNT 12 (95% CI 8-24)", "NNT", 12, 8, 24),
    TestCase("OQ-RRR-001", "OQ", "RRR Extraction", "Vaccine efficacy as RRR",
             "Vaccine efficacy was 95.0% (95% CI, 90.3%-97.6%)", "RRR", 95.0, 90.3, 97.6),
]

OQ_OCR_TESTS = [
    TestCase("OQ-OCR-001", "OQ", "OCR Correction", "O to 0 correction",
             "HR O.74 (95% CI O.61-O.89)", "HR", 0.74, 0.61, 0.89),
    TestCase("OQ-OCR-002", "OQ", "OCR Correction", "l to 1 correction",
             "OR l.56 (95% CI l.21-2.0l)", "OR", 1.56, 1.21, 2.01),
    TestCase("OQ-OCR-003", "OQ", "OCR Correction", "Cl to CI correction",
             "RR 0.81 (95% Cl 0.70-0.94)", "RR", 0.81, 0.70, 0.94),
    TestCase("OQ-OCR-004", "OQ", "OCR Correction", "Compound OCR errors",
             "HR O.74 (95% Cl O.6l-O.89)", "HR", 0.74, 0.61, 0.89),
    TestCase("OQ-OCR-005", "OQ", "OCR Correction", "Severe degradation",
             "SMD -O.5l (95% Cl -O.7l to -O.3l)", "SMD", -0.51, -0.71, -0.31),
]

OQ_MULTILANG_TESTS = [
    TestCase("OQ-LANG-001", "OQ", "Multi-language", "German KI format",
             "Hazard Ratio 0,78 (95%-KI 0,65-0,94)", "HR", 0.78, 0.65, 0.94),
    TestCase("OQ-LANG-002", "OQ", "Multi-language", "French IC format",
             "Rapport de cotes 1,45 (IC 95% 1,12-1,88)", "OR", 1.45, 1.12, 1.88),
    TestCase("OQ-LANG-003", "OQ", "Multi-language", "Spanish IC format",
             "Razón de riesgo 0,81 (IC 95%: 0,69-0,95)", "HR", 0.81, 0.69, 0.95),
    TestCase("OQ-LANG-004", "OQ", "Multi-language", "Chinese format",
             "风险比 0.72 (95% CI 0.58-0.89)", "HR", 0.72, 0.58, 0.89),
    TestCase("OQ-LANG-005", "OQ", "Multi-language", "Japanese format",
             "ハザード比 0.68 (95% CI 0.55-0.84)", "HR", 0.68, 0.55, 0.84),
    TestCase("OQ-LANG-006", "OQ", "Multi-language", "Korean format",
             "위험비 0.71 (95% CI 0.59-0.86)", "HR", 0.71, 0.59, 0.86),
    TestCase("OQ-LANG-007", "OQ", "Multi-language", "European decimal (comma)",
             "HR 0,82 (95% CI 0,71-0,95)", "HR", 0.82, 0.71, 0.95),
    TestCase("OQ-LANG-008", "OQ", "Multi-language", "Dutch BI format",
             "Hazard ratio 0,75 (95%-BI 0,62-0,91)", "HR", 0.75, 0.62, 0.91),
]

OQ_NEGATIVE_TESTS = [
    TestCase("OQ-NEG-001", "OQ", "Negative Testing", "Power calculation",
             "assuming HR of 0.75 with 80% power", should_extract=False),
    TestCase("OQ-NEG-002", "OQ", "Negative Testing", "Sample size context",
             "sample size to detect OR 1.5 with alpha 0.05", should_extract=False),
    TestCase("OQ-NEG-003", "OQ", "Negative Testing", "Expected effect",
             "expected RR of 0.80 based on pilot data", should_extract=False),
    TestCase("OQ-NEG-004", "OQ", "Negative Testing", "Historical reference",
             "previous meta-analysis reported HR 0.82", should_extract=False),
    TestCase("OQ-NEG-005", "OQ", "Negative Testing", "Hypothetical",
             "if the HR is greater than 1.0, treatment is harmful", should_extract=False),
    TestCase("OQ-NEG-006", "OQ", "Negative Testing", "Interpretation",
             "this would be interpreted as HR of approximately 0.75", should_extract=False),
]


# =============================================================================
# PERFORMANCE QUALIFICATION (PQ) TESTS
# =============================================================================

PQ_EDGE_TESTS = [
    TestCase("PQ-EDGE-001", "PQ", "Edge Cases", "HR exactly 1.00",
             "HR 1.00 (95% CI 0.85-1.18)", "HR", 1.00, 0.85, 1.18),
    TestCase("PQ-EDGE-002", "PQ", "Edge Cases", "Very small effect",
             "HR 0.99 (95% CI 0.97-1.01)", "HR", 0.99, 0.97, 1.01),
    TestCase("PQ-EDGE-003", "PQ", "Edge Cases", "Very large OR",
             "OR 15.0 (95% CI 8.5-26.5)", "OR", 15.0, 8.5, 26.5),
    TestCase("PQ-EDGE-004", "PQ", "Edge Cases", "Strong protective effect",
             "OR 0.08 (95% CI 0.02-0.32)", "OR", 0.08, 0.02, 0.32),
    TestCase("PQ-EDGE-005", "PQ", "Edge Cases", "Large harmful RR",
             "RR 4.25 (95% CI 2.18-8.29)", "RR", 4.25, 2.18, 8.29),
    TestCase("PQ-EDGE-006", "PQ", "Edge Cases", "Large SMD",
             "SMD 1.25 (95% CI 0.98-1.52)", "SMD", 1.25, 0.98, 1.52),
    TestCase("PQ-EDGE-007", "PQ", "Edge Cases", "Negative SMD",
             "SMD -2.15 (95% CI -2.58 to -1.72)", "SMD", -2.15, -2.58, -1.72),
    TestCase("PQ-EDGE-008", "PQ", "Edge Cases", "Wide CI",
             "RR 0.50 (95% CI 0.10-2.50)", "RR", 0.50, 0.10, 2.50),
    TestCase("PQ-EDGE-009", "PQ", "Edge Cases", "Narrow CI",
             "OR 0.85 (95% CI 0.84-0.86)", "OR", 0.85, 0.84, 0.86),
    TestCase("PQ-EDGE-010", "PQ", "Edge Cases", "Three decimal places",
             "HR 0.723 (95% CI 0.618-0.846)", "HR", 0.723, 0.618, 0.846),
    TestCase("PQ-EDGE-011", "PQ", "Edge Cases", "CI crosses null",
             "RR 1.05 (95% CI 0.82-1.35)", "RR", 1.05, 0.82, 1.35),
    TestCase("PQ-EDGE-012", "PQ", "Edge Cases", "SMD crosses zero",
             "SMD -0.12 (95% CI -0.35 to 0.11)", "SMD", -0.12, -0.35, 0.11),
]

PQ_REALWORLD_TESTS = [
    # Real-world patterns from major journals
    TestCase("PQ-RW-001", "PQ", "Real-world", "NEJM SPRINT pattern",
             "The hazard ratio for the primary outcome was 0.75 (95% CI, 0.64 to 0.89; P<0.001)",
             "HR", 0.75, 0.64, 0.89),
    TestCase("PQ-RW-002", "PQ", "Real-world", "Lancet CTT pattern",
             "LDL cholesterol reduction with statins reduced major vascular events (RR 0.79, 95% CI 0.77-0.81)",
             "RR", 0.79, 0.77, 0.81),
    TestCase("PQ-RW-003", "PQ", "Real-world", "JAMA pattern",
             "Treatment was associated with reduced mortality (OR 0.72; 95% CI, 0.58-0.89; P=.002)",
             "OR", 0.72, 0.58, 0.89),
    TestCase("PQ-RW-004", "PQ", "Real-world", "BMJ pattern",
             "The pooled standardized mean difference was -0.62 (95% CI -0.81 to -0.42), favoring treatment",
             "SMD", -0.62, -0.81, -0.42),
    TestCase("PQ-RW-005", "PQ", "Real-world", "Cochrane pattern",
             "Random effects meta-analysis: RR 0.68 (95% CI 0.58 to 0.80), I² = 32%",
             "RR", 0.68, 0.58, 0.80),
]


# =============================================================================
# TEST RUNNER
# =============================================================================

class RegulatoryTestRunner:
    """Executes regulatory validation tests and generates reports"""

    def __init__(self):
        self.pipeline = VerifiedExtractionPipeline()
        self.results: List[TestResult] = []
        self.start_time = None

    def run_iq_tests(self) -> Dict:
        """Run Installation Qualification tests"""
        print("\n" + "=" * 70)
        print("  INSTALLATION QUALIFICATION (IQ)")
        print("=" * 70)

        iq_results = {"passed": 0, "failed": 0, "tests": []}

        # Check file existence
        base_path = Path(__file__).parent / "src" / "core"
        files_to_check = [
            ("IQ-001-01", "enhanced_extractor_v3.py"),
            ("IQ-001-02", "ocr_preprocessor.py"),
            ("IQ-001-03", "team_of_rivals.py"),
            ("IQ-001-04", "verified_extraction_pipeline.py"),
        ]

        for test_id, filename in files_to_check:
            filepath = base_path / filename
            passed = filepath.exists() and filepath.stat().st_size > 0
            result = TestResult(
                test_id=test_id,
                passed=passed,
                expected=f"{filename} exists",
                actual="Found" if passed else "Not found",
                execution_time_ms=0,
                timestamp=datetime.now().isoformat()
            )
            self.results.append(result)
            iq_results["tests"].append(result)
            if passed:
                iq_results["passed"] += 1
            else:
                iq_results["failed"] += 1

        # Check imports
        try:
            from src.core.verified_extraction_pipeline import VerifiedExtractionPipeline
            passed = True
        except ImportError:
            passed = False

        result = TestResult(
            test_id="IQ-002-01",
            passed=passed,
            expected="Pipeline imports successfully",
            actual="Success" if passed else "Import failed",
            execution_time_ms=0,
            timestamp=datetime.now().isoformat()
        )
        self.results.append(result)
        iq_results["tests"].append(result)
        if passed:
            iq_results["passed"] += 1
        else:
            iq_results["failed"] += 1

        try:
            from src.core.ocr_preprocessor import OCRPreprocessor
            passed = True
        except ImportError:
            passed = False

        result = TestResult(
            test_id="IQ-002-02",
            passed=passed,
            expected="OCR Preprocessor imports successfully",
            actual="Success" if passed else "Import failed",
            execution_time_ms=0,
            timestamp=datetime.now().isoformat()
        )
        self.results.append(result)
        iq_results["tests"].append(result)
        if passed:
            iq_results["passed"] += 1
        else:
            iq_results["failed"] += 1

        print(f"\n  IQ Result: {iq_results['passed']}/{iq_results['passed'] + iq_results['failed']} PASSED")
        return iq_results

    def run_extraction_test(self, test: TestCase) -> TestResult:
        """Run a single extraction test"""
        start = time.time()

        try:
            extractions = self.pipeline.extract(test.input_text)
            usable = [e for e in extractions if e.is_usable]

            if not test.should_extract:
                # Negative test - should NOT extract
                passed = len(usable) == 0
                actual = f"No extraction" if passed else f"Incorrectly extracted {len(usable)}"
            else:
                # Positive test - should extract matching values
                passed = False
                actual = "No extraction"

                for ext in usable:
                    if ext.effect_type == test.expected_type:
                        value_match = abs(ext.value - test.expected_value) < test.tolerance
                        ci_lower_match = ext.ci_lower is not None and abs(ext.ci_lower - test.expected_ci_lower) < test.tolerance
                        ci_upper_match = ext.ci_upper is not None and abs(ext.ci_upper - test.expected_ci_upper) < test.tolerance

                        if value_match and ci_lower_match and ci_upper_match:
                            passed = True
                            actual = f"{ext.effect_type}={ext.value} ({ext.ci_lower}-{ext.ci_upper})"
                            break
                        else:
                            actual = f"{ext.effect_type}={ext.value} ({ext.ci_lower}-{ext.ci_upper}) [mismatch]"

                if not passed and usable:
                    types = [e.effect_type for e in usable]
                    actual = f"Wrong type: {types}"

        except Exception as e:
            passed = False
            actual = f"Error: {str(e)}"

        elapsed_ms = (time.time() - start) * 1000

        expected = f"{test.expected_type}={test.expected_value} ({test.expected_ci_lower}-{test.expected_ci_upper})" if test.should_extract else "No extraction"

        return TestResult(
            test_id=test.test_id,
            passed=passed,
            expected=expected,
            actual=actual,
            execution_time_ms=elapsed_ms,
            timestamp=datetime.now().isoformat()
        )

    def run_oq_tests(self) -> Dict:
        """Run Operational Qualification tests"""
        print("\n" + "=" * 70)
        print("  OPERATIONAL QUALIFICATION (OQ)")
        print("=" * 70)

        all_oq_tests = (
            OQ_HR_TESTS + OQ_OR_TESTS + OQ_RR_TESTS +
            OQ_MD_TESTS + OQ_SMD_TESTS + OQ_OTHER_TESTS +
            OQ_OCR_TESTS + OQ_MULTILANG_TESTS + OQ_NEGATIVE_TESTS
        )

        oq_results = {"passed": 0, "failed": 0, "tests": [], "by_category": {}}

        for test in all_oq_tests:
            result = self.run_extraction_test(test)
            self.results.append(result)
            oq_results["tests"].append(result)

            if result.passed:
                oq_results["passed"] += 1
            else:
                oq_results["failed"] += 1
                print(f"  FAILED: {test.test_id} - {test.description}")
                print(f"          Expected: {result.expected}")
                print(f"          Actual: {result.actual}")

            # Track by category
            if test.subcategory not in oq_results["by_category"]:
                oq_results["by_category"][test.subcategory] = {"passed": 0, "failed": 0}
            if result.passed:
                oq_results["by_category"][test.subcategory]["passed"] += 1
            else:
                oq_results["by_category"][test.subcategory]["failed"] += 1

        print(f"\n  OQ Results by Category:")
        for cat, counts in oq_results["by_category"].items():
            total = counts["passed"] + counts["failed"]
            print(f"    {cat}: {counts['passed']}/{total}")

        print(f"\n  OQ Total: {oq_results['passed']}/{oq_results['passed'] + oq_results['failed']} PASSED")
        return oq_results

    def run_pq_tests(self) -> Dict:
        """Run Performance Qualification tests"""
        print("\n" + "=" * 70)
        print("  PERFORMANCE QUALIFICATION (PQ)")
        print("=" * 70)

        all_pq_tests = PQ_EDGE_TESTS + PQ_REALWORLD_TESTS

        pq_results = {"passed": 0, "failed": 0, "tests": []}

        for test in all_pq_tests:
            result = self.run_extraction_test(test)
            self.results.append(result)
            pq_results["tests"].append(result)

            if result.passed:
                pq_results["passed"] += 1
            else:
                pq_results["failed"] += 1
                print(f"  FAILED: {test.test_id} - {test.description}")

        # Reproducibility test
        print("\n  Running reproducibility test (100 iterations)...")
        test_text = "HR 0.75 (95% CI 0.64-0.89)"
        results_set = set()
        for _ in range(100):
            extractions = self.pipeline.extract(test_text)
            if extractions:
                e = extractions[0]
                results_set.add((e.effect_type, round(e.value, 3), round(e.ci_lower, 3), round(e.ci_upper, 3)))

        reproducible = len(results_set) == 1
        result = TestResult(
            test_id="PQ-REPRO-001",
            passed=reproducible,
            expected="All 100 iterations identical",
            actual=f"{len(results_set)} unique results",
            execution_time_ms=0,
            timestamp=datetime.now().isoformat()
        )
        self.results.append(result)
        pq_results["tests"].append(result)
        if reproducible:
            pq_results["passed"] += 1
        else:
            pq_results["failed"] += 1

        print(f"\n  PQ Total: {pq_results['passed']}/{pq_results['passed'] + pq_results['failed']} PASSED")
        return pq_results

    def generate_report(self, iq_results, oq_results, pq_results) -> ValidationReport:
        """Generate final validation report"""
        total_passed = iq_results["passed"] + oq_results["passed"] + pq_results["passed"]
        total_failed = iq_results["failed"] + oq_results["failed"] + pq_results["failed"]
        total = total_passed + total_failed

        elapsed = time.time() - self.start_time

        conclusion = "VALIDATION PASSED" if total_failed == 0 else "VALIDATION FAILED"

        report = ValidationReport(
            system_name="RCT Effect Estimate Extractor",
            system_version="4.0.3",
            validation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            validator="Automated Validation Suite",
            total_tests=total,
            passed_tests=total_passed,
            failed_tests=total_failed,
            pass_rate=total_passed / total * 100 if total > 0 else 0,
            iq_results=iq_results,
            oq_results=oq_results,
            pq_results=pq_results,
            test_results=[asdict(r) for r in self.results],
            execution_time_seconds=elapsed,
            conclusion=conclusion
        )

        return report

    def run_full_validation(self):
        """Run complete IQ/OQ/PQ validation"""
        self.start_time = time.time()

        print("=" * 70)
        print("  FDA REGULATORY VALIDATION SUITE")
        print("  RCT Effect Estimate Extractor v4.0.3")
        print("  Compliance: 21 CFR Part 11, GAMP 5")
        print("=" * 70)
        print(f"  Validation Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        iq_results = self.run_iq_tests()
        oq_results = self.run_oq_tests()
        pq_results = self.run_pq_tests()

        report = self.generate_report(iq_results, oq_results, pq_results)

        # Print summary
        print("\n" + "=" * 70)
        print("  VALIDATION SUMMARY")
        print("=" * 70)
        print(f"""
  System:           {report.system_name}
  Version:          {report.system_version}
  Date:             {report.validation_date}

  TEST RESULTS:
  -------------
  Installation Qualification (IQ):  {iq_results['passed']}/{iq_results['passed'] + iq_results['failed']}
  Operational Qualification (OQ):   {oq_results['passed']}/{oq_results['passed'] + oq_results['failed']}
  Performance Qualification (PQ):   {pq_results['passed']}/{pq_results['passed'] + pq_results['failed']}
  --------------------------------------
  TOTAL:                            {report.passed_tests}/{report.total_tests} ({report.pass_rate:.1f}%)

  Execution Time: {report.execution_time_seconds:.2f} seconds

  CONCLUSION: {report.conclusion}
        """)

        # Save report
        report_path = Path(__file__).parent / "regulatory" / "validation_report.json"
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(asdict(report), f, indent=2)
        print(f"  Report saved to: {report_path}")

        return report


if __name__ == "__main__":
    runner = RegulatoryTestRunner()
    report = runner.run_full_validation()

    # Exit with appropriate code
    sys.exit(0 if report.failed_tests == 0 else 1)
