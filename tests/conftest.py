#!/usr/bin/env python3
"""
Pytest Configuration and Shared Fixtures
=========================================

Provides shared fixtures for all test modules:
- Extractor instances
- Sample data
- PDF loading utilities
- Gold standard access
- Temporary file management
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# PATH FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def project_root():
    """Project root directory"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def src_dir(project_root):
    """Source code directory"""
    return project_root / "src"


@pytest.fixture(scope="session")
def data_dir(project_root):
    """Data directory"""
    return project_root / "data"


@pytest.fixture(scope="session")
def test_pdfs_dir(project_root):
    """Test PDFs directory"""
    return project_root / "test_pdfs"


@pytest.fixture(scope="session")
def gold_dir(data_dir):
    """Gold standard data directory"""
    return data_dir / "gold"


# =============================================================================
# EXTRACTOR FIXTURES
# =============================================================================

@pytest.fixture
def enhanced_extractor():
    """Enhanced extractor v3 instance"""
    from src.core.enhanced_extractor_v3 import EnhancedExtractor
    return EnhancedExtractor()


@pytest.fixture
def pdf_parser():
    """PDF parser instance"""
    from src.pdf.pdf_parser import PDFParser
    return PDFParser()


@pytest.fixture
def ocr_preprocessor():
    """OCR preprocessor instance"""
    from src.core.ocr_preprocessor import OCRPreprocessor
    return OCRPreprocessor()


# =============================================================================
# DATA FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def validation_trials():
    """Load external validation trials"""
    from data.external_validation_dataset import ALL_EXTERNAL_VALIDATION_TRIALS
    return ALL_EXTERNAL_VALIDATION_TRIALS


@pytest.fixture(scope="session")
def held_out_cases():
    """Load held-out test cases"""
    from data.held_out_test_set import HELD_OUT_TEST_SET
    return HELD_OUT_TEST_SET


@pytest.fixture(scope="session")
def false_positive_cases():
    """Load false positive test cases"""
    from data.false_positive_test_cases import FALSE_POSITIVE_TEST_CASES
    return FALSE_POSITIVE_TEST_CASES


@pytest.fixture(scope="session")
def gold_standard_trials(gold_dir):
    """Load gold standard JSONL files"""
    trials = []
    for jsonl_file in gold_dir.glob("*.jsonl"):
        with open(jsonl_file) as f:
            for line in f:
                if line.strip():
                    trials.append(json.loads(line))
    return trials


@pytest.fixture(scope="session")
def pdf_manifest(test_pdfs_dir):
    """Load PDF manifest if available"""
    manifest_path = test_pdfs_dir / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f)
    return None


# =============================================================================
# SAMPLE DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_hr_text():
    """Sample text with hazard ratio"""
    return """
    The primary endpoint occurred in 16.3% of patients in the treatment group
    and 21.2% of patients in the placebo group (hazard ratio, 0.74; 95% CI,
    0.65 to 0.85; P<0.001).
    """


@pytest.fixture
def sample_or_text():
    """Sample text with odds ratio"""
    return """
    The odds ratio for the primary outcome was 1.45 (95% CI, 1.12 to 1.88;
    P=0.004) favoring the treatment group.
    """


@pytest.fixture
def sample_rr_text():
    """Sample text with relative risk"""
    return """
    The relative risk of death was 0.83 (95% CI, 0.71-0.97) in the intervention
    arm compared with standard care.
    """


@pytest.fixture
def sample_md_text():
    """Sample text with mean difference"""
    return """
    The mean difference in blood pressure reduction was -5.2 mmHg (95% CI,
    -7.1 to -3.3; P<0.001) between groups.
    """


@pytest.fixture
def sample_multi_effect_text():
    """Sample text with multiple effects"""
    return """
    RESULTS

    Primary Endpoint: The hazard ratio for cardiovascular death or heart
    failure hospitalization was 0.74 (95% CI, 0.65 to 0.85; P<0.001).

    Secondary Endpoints:
    - Cardiovascular death: HR 0.82 (95% CI, 0.69-0.98)
    - Heart failure hospitalization: HR 0.70 (95% CI, 0.59-0.83), P<0.001
    - All-cause mortality: HR 0.83 (95% CI, 0.71-0.97)

    Continuous Outcome: Mean difference in ejection fraction was 3.2%
    (95% CI, 1.8-4.6; P<0.001).
    """


@pytest.fixture
def sample_table_text():
    """Sample table-like text"""
    return """
    Table 2. Primary and Secondary Outcomes

    Outcome                     Treatment    Placebo     HR (95% CI)         P
    -------------------------------------------------------------------------
    Primary composite           16.3%        21.2%       0.74 (0.65-0.85)    <0.001
    CV death                    9.6%         11.5%       0.82 (0.69-0.98)    0.03
    HF hospitalization          10.0%        13.7%       0.70 (0.59-0.83)    <0.001
    All-cause mortality         11.6%        13.9%       0.83 (0.71-0.97)    0.02
    """


@pytest.fixture
def sample_negative_text():
    """Sample text that should NOT produce extractions"""
    return """
    Financial Report Q4 2023

    Revenue increased by 15% with a growth rate of 0.85 compared to Q3.
    The confidence interval for projections is 0.75 to 0.95 based on
    historical data. The hazard of market volatility remains a concern
    with P&L ratios showing improvement.
    """


# =============================================================================
# PDF FIXTURES
# =============================================================================

@pytest.fixture
def available_pdfs(test_pdfs_dir):
    """Get list of available PDFs for testing"""
    pdfs = []
    for category in ["born_digital", "scanned"]:
        for subdir in (test_pdfs_dir / "pmc_open_access" / category).glob("*"):
            if subdir.is_dir():
                pdfs.extend(subdir.glob("*.pdf"))
            elif subdir.suffix == ".pdf":
                pdfs.append(subdir)
    return pdfs


@pytest.fixture
def sample_pdf(available_pdfs):
    """Get a sample PDF for testing"""
    if not available_pdfs:
        pytest.skip("No PDF files available for testing")
    return available_pdfs[0]


# =============================================================================
# GOLD STANDARD FIXTURES
# =============================================================================

@pytest.fixture
def gold_annotations(test_pdfs_dir):
    """Load gold standard annotations"""
    annotations_dir = test_pdfs_dir / "gold_standard" / "annotations"
    annotations = {}

    for f in annotations_dir.glob("*.gold.jsonl"):
        with open(f) as file:
            try:
                data = json.loads(file.read())
                annotations[data.get("trial_name", f.stem)] = data
            except json.JSONDecodeError:
                continue

    return annotations


# =============================================================================
# TEMPORARY FILE FIXTURES
# =============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for test outputs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_pdf(temp_dir):
    """Create a temporary PDF path"""
    return temp_dir / "test.pdf"


# =============================================================================
# MARKER CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "pdf: PDF-specific tests"
    )
    config.addinivalue_line(
        "markers", "slow: Long-running tests"
    )
    config.addinivalue_line(
        "markers", "ocr: OCR-related tests"
    )
    config.addinivalue_line(
        "markers", "gold: Gold standard validation tests"
    )


# =============================================================================
# SKIP CONDITIONS
# =============================================================================

def pytest_collection_modifyitems(config, items):
    """Modify test collection based on available resources"""
    # Check if PDFs are available
    test_pdfs = Path(__file__).parent.parent / "test_pdfs"
    has_pdfs = any(test_pdfs.glob("**/*.pdf"))

    if not has_pdfs:
        skip_pdf = pytest.mark.skip(reason="No PDF files available")
        for item in items:
            if "pdf" in item.keywords:
                item.add_marker(skip_pdf)

    # Skip slow tests unless explicitly requested
    if not config.getoption("--runslow", default=False):
        skip_slow = pytest.mark.skip(reason="Use --runslow to run slow tests")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="Run slow tests"
    )
    parser.addoption(
        "--runpdf",
        action="store_true",
        default=False,
        help="Run PDF tests even if no PDFs available"
    )


# =============================================================================
# REPORTING
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def report_test_environment(request):
    """Report test environment information"""
    print("\n" + "=" * 60)
    print("TEST ENVIRONMENT")
    print("=" * 60)

    project_root = Path(__file__).parent.parent
    test_pdfs = project_root / "test_pdfs"

    # Count PDFs
    pdf_count = len(list(test_pdfs.glob("**/*.pdf")))
    print(f"PDF files available: {pdf_count}")

    # Count gold standard annotations
    annotations_dir = test_pdfs / "gold_standard" / "annotations"
    annotation_count = len(list(annotations_dir.glob("*.gold.jsonl")))
    print(f"Gold standard annotations: {annotation_count}")

    # Check dependencies
    try:
        import pdfplumber
        print(f"pdfplumber: {pdfplumber.__version__ if hasattr(pdfplumber, '__version__') else 'installed'}")
    except ImportError:
        print("pdfplumber: NOT INSTALLED")

    try:
        import fitz
        print(f"PyMuPDF: {fitz.version[0]}")
    except ImportError:
        print("PyMuPDF: NOT INSTALLED")

    try:
        import pytesseract
        print(f"pytesseract: installed")
    except ImportError:
        print("pytesseract: NOT INSTALLED")

    print("=" * 60 + "\n")
