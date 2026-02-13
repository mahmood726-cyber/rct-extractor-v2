# RCT Extractor v4.1.0 - Improvement Plan
## Real PDF Validation & Production Readiness

**Date:** 2026-01-31
**Target Version:** 4.1.0
**Status:** Planning

---

## Executive Summary

This plan addresses the critical gap between **documented capabilities** and **actual validated functionality** in RCT Extractor. While the codebase has mature architecture for PDF processing, table extraction, and forest plot analysis, these features have **zero real-world validation**.

### Current State vs Target

| Component | Current | Target |
|-----------|---------|--------|
| Real PDFs tested | 0 | 100+ |
| Table extraction validated | No | Yes |
| Forest plot extraction validated | No | Yes |
| OCR pathway tested | No | Yes |
| External R datasets | 0 | 50+ |
| CI/CD with real PDFs | No | Yes |

---

## Gap Analysis Summary

### Critical Gaps (Block Production)

| Gap | Impact | Priority |
|-----|--------|----------|
| **Zero real PDFs downloaded** | Cannot validate PDF pathway | P0 |
| **Table extraction untested** | 2-5% of effects missed | P0 |
| **OCR pathway untested** | Unknown scanned PDF accuracy | P0 |
| **No gold standard PDFs** | Cannot measure PDF accuracy | P0 |

### High Priority Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| Forest plot extraction untested | Missing figure-based effects | P1 |
| No external R package data | Limited independent validation | P1 |
| CI/CD uses no real data | Tests pass without validation | P1 |
| No degraded PDF testing | Unknown OCR robustness | P1 |

### Medium Priority Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| No ClinicalTrials.gov integration | Missing registry validation | P2 |
| No multi-language support | Limited to English | P2 |
| No performance regression tests | Speed regressions undetected | P2 |

---

## Phase 1: Real PDF Collection (Week 1-2)

### 1.1 Download PMC Open Access PDFs

**Script:** `scripts/download_pmc_pdfs.py` (exists, needs execution)

**Target Collection:**

| Category | Count | Source | PMC IDs From |
|----------|-------|--------|--------------|
| Cardiovascular | 25 | PMC OA | external_validation_dataset.py |
| Oncology | 25 | PMC OA | external_validation_dataset.py |
| Neurology | 10 | PMC OA | stratified_validation_dataset.py |
| Other specialties | 20 | PMC OA | stratified_validation_dataset.py |
| Scanned/historical | 10 | PMC Archive | Manual selection |
| Multi-column layouts | 5 | Various | Manual selection |
| Table-heavy papers | 10 | Various | Manual selection |
| Forest plot papers | 10 | Cochrane OA | Manual selection |
| **Total** | **115** | | |

**Commands:**
```bash
# Download born-digital PDFs
python scripts/download_pmc_pdfs.py --category cardiovascular --max 25
python scripts/download_pmc_pdfs.py --category oncology --max 25
python scripts/download_pmc_pdfs.py --category neurology --max 10
python scripts/download_pmc_pdfs.py --category other --max 20

# Download scanned/historical
python scripts/download_pmc_pdfs.py --years 1990-2005 --max 10
```

### 1.2 Create Gold Standard Annotations

**Process:**
1. For each PDF, manually extract all effect estimates
2. Dual annotation (2 reviewers)
3. Adjudication for disagreements
4. Store in `test_pdfs/gold_standard/annotations/`

**Annotation Schema:**
```json
{
  "pdf_file": "dapa_hf_nejm_2019.pdf",
  "pmc_id": "PMC6893803",
  "annotator": "reviewer_a",
  "effects": [
    {
      "effect_type": "HR",
      "value": 0.74,
      "ci_lower": 0.65,
      "ci_upper": 0.85,
      "page": 5,
      "location": "text",
      "verbatim": "HR 0.74 (95% CI 0.65-0.85)"
    }
  ]
}
```

### 1.3 Directory Structure

```
test_pdfs/
├── pmc_open_access/
│   ├── born_digital/
│   │   ├── cardiovascular/     # 25 PDFs
│   │   ├── oncology/          # 25 PDFs
│   │   ├── neurology/         # 10 PDFs
│   │   └── other/             # 20 PDFs
│   ├── scanned/               # 10 PDFs
│   └── edge_cases/
│       ├── multi_column/      # 5 PDFs
│       ├── table_heavy/       # 10 PDFs
│       └── forest_plots/      # 10 PDFs
├── gold_standard/
│   ├── pdfs/                  # 50 annotated PDFs
│   └── annotations/           # JSONL annotations
├── degraded/                  # Artificially degraded PDFs
│   ├── blur/
│   ├── noise/
│   └── low_contrast/
└── manifest.json              # Index with metadata
```

---

## Phase 2: PDF Extraction Validation (Week 2-3)

### 2.1 Text Extraction Accuracy

**Metrics:**
- Character Error Rate (CER): Target < 2%
- Word Error Rate (WER): Target < 5%
- Effect estimate extraction accuracy: Target > 95%

**Test Cases (50 tests):**
```python
class TestPDFTextExtraction:
    def test_born_digital_text_accuracy(self):
        """CER < 1% for born-digital PDFs"""

    def test_scanned_text_accuracy(self):
        """CER < 5% for scanned PDFs with OCR confidence > 90%"""

    def test_multi_column_reordering(self):
        """Text extracted in correct reading order"""

    def test_table_text_extraction(self):
        """Table cells extracted with correct structure"""
```

### 2.2 Effect Extraction from PDFs

**Test Matrix:**

| PDF Type | Count | Target Accuracy |
|----------|-------|-----------------|
| Born-digital, text effects | 60 | > 97% |
| Born-digital, table effects | 20 | > 90% |
| Scanned, text effects | 15 | > 90% |
| Scanned, table effects | 5 | > 85% |
| Forest plot effects | 10 | > 80% |

**Comparison Methodology:**
1. Extract text from PDF
2. Run pattern extraction
3. Compare to gold standard annotations
4. Calculate precision, recall, F1

### 2.3 PDF vs Text Baseline

Compare PDF extraction to clean text extraction:
```python
def test_pdf_vs_text_delta():
    """PDF extraction should be within 3% of text baseline"""
    text_accuracy = run_text_validation()  # 97.4%
    pdf_accuracy = run_pdf_validation()
    assert text_accuracy - pdf_accuracy < 0.03
```

---

## Phase 3: Table Extraction Validation (Week 3-4)

### 3.1 Table Detection

**Test Cases (25 tests):**

| Test | Description | Target |
|------|-------------|--------|
| Table detection | Identify tables in PDFs | > 95% recall |
| Table boundaries | Correct row/column count | > 90% |
| Header identification | Identify header rows | > 85% |
| Cell extraction | Extract cell content | > 90% |
| Effect extraction | Extract effects from cells | > 85% |

### 3.2 Table Test PDFs

Curate 10 PDFs with effects **only** in tables:
- Results tables with HR, OR, RR
- Subgroup analysis tables
- Multi-arm trial tables
- Forest plot data tables

### 3.3 Implementation Tasks

```python
# tests/test_table_extraction.py

class TestTableExtraction:
    @pytest.fixture
    def table_pdfs(self):
        """Load PDFs with table-only effects"""
        return load_pdfs("test_pdfs/edge_cases/table_heavy/")

    def test_table_detection_recall(self, table_pdfs):
        """Detect at least 95% of tables"""

    def test_table_effect_extraction(self, table_pdfs):
        """Extract effects from tables with >85% accuracy"""

    def test_complex_table_layouts(self, table_pdfs):
        """Handle merged cells, spanning headers"""
```

---

## Phase 4: Forest Plot Extraction (Week 4-5)

### 4.1 Forest Plot Detection

**Test Cases (15 tests):**

| Test | Description | Target |
|------|-------------|--------|
| Figure detection | Identify forest plots | > 90% recall |
| Study identification | Extract study names | > 85% |
| Effect extraction | Extract point estimates | > 80% |
| CI extraction | Extract CI bounds | > 75% |
| Diamond extraction | Extract pooled estimate | > 85% |

### 4.2 Forest Plot Test PDFs

Curate 10 PDFs with forest plots:
- Cochrane systematic reviews
- Meta-analysis papers
- Individual patient data meta-analyses

### 4.3 Implementation Tasks

```python
# tests/test_forest_plot_extraction.py

class TestForestPlotExtraction:
    @pytest.fixture
    def forest_plot_pdfs(self):
        """Load PDFs with forest plots"""
        return load_pdfs("test_pdfs/edge_cases/forest_plots/")

    def test_forest_plot_detection(self, forest_plot_pdfs):
        """Detect forest plots with >90% recall"""

    def test_effect_coordinate_extraction(self, forest_plot_pdfs):
        """Extract effect values from plot coordinates"""

    def test_pooled_estimate_extraction(self, forest_plot_pdfs):
        """Extract diamond/pooled estimates"""
```

---

## Phase 5: OCR Stress Testing (Week 5-6)

### 5.1 Degraded PDF Generation

Use `scripts/degrade_pdf.py` to create test cases:

| Degradation | Parameters | Expected Accuracy |
|-------------|------------|-------------------|
| High quality | None | > 95% |
| Medium blur | Gaussian σ=1 | > 90% |
| High blur | Gaussian σ=2 | > 80% |
| Noise | Salt-pepper 5% | > 85% |
| Low contrast | 50% reduction | > 85% |
| Rotation | 2° skew | > 90% |
| Combined | Blur + noise | > 75% |

**Command:**
```bash
python scripts/degrade_pdf.py \
    --input test_pdfs/pmc_open_access/born_digital/ \
    --output test_pdfs/degraded/ \
    --quality low medium high
```

### 5.2 OCR Confidence Calibration

Validate that OCR confidence scores predict actual accuracy:

```python
def test_ocr_confidence_calibration():
    """OCR confidence should correlate with actual accuracy"""
    results = []
    for pdf in degraded_pdfs:
        confidence = extract_with_confidence(pdf)
        actual_accuracy = compare_to_gold(pdf)
        results.append((confidence, actual_accuracy))

    correlation = spearman_correlation(results)
    assert correlation > 0.8
```

### 5.3 OCR Threshold Optimization

Find optimal thresholds for automation tiers:

| OCR Confidence | Recommended Action |
|----------------|-------------------|
| > 95% | FULL_AUTO |
| 85-95% | SPOT_CHECK |
| 70-85% | VERIFY |
| < 70% | MANUAL or reject |

---

## Phase 6: External Dataset Integration (Week 6-7)

### 6.1 R Package Datasets

| Package | Datasets | Effects | Status |
|---------|----------|---------|--------|
| mada | 8 | ~50 | Not integrated |
| metafor | 12 | ~100 | Not integrated |
| rmeta | 5 | ~30 | Not integrated |
| meta | 6 | ~40 | Not integrated |
| netmeta | 4 | ~25 | Not integrated |
| **Total** | **35** | **~245** | |

**Script:** `scripts/download_r_datasets.py`

```python
# Download datasets from R packages
def download_mada_datasets():
    """Download diagnostic accuracy datasets from mada package"""
    datasets = [
        "Dementia", "Dipperman", "Catheter",
        "Rutter", "Sinusitis", "Woodhead"
    ]
    for ds in datasets:
        download_r_dataset("mada", ds)
```

### 6.2 Zenodo Datasets

Search for systematic review datasets on Zenodo:
- DOI: 10.5281/zenodo.* with keywords "systematic review", "meta-analysis"
- Download PRISMA-compliant datasets

### 6.3 ClinicalTrials.gov Integration

**Script:** `scripts/download_ctgov_results.py` (partially exists)

```python
# Download results from ClinicalTrials.gov
def download_ctgov_results(nct_ids: List[str]):
    """Download XML results for completed trials"""
    for nct_id in nct_ids:
        url = f"https://clinicaltrials.gov/ct2/show/results/{nct_id}?resultsxml=true"
        download_xml(url, f"data/ctgov/{nct_id}.xml")
```

---

## Phase 7: CI/CD Enhancement (Week 7-8)

### 7.1 Add Real PDF Tests to CI

Update `.github/workflows/test.yml`:

```yaml
pdf-validation:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Download test PDFs (cached)
      uses: actions/cache@v3
      with:
        path: test_pdfs/
        key: test-pdfs-v1-${{ hashFiles('data/pmc_ids.txt') }}

    - name: Download missing PDFs
      run: python scripts/download_pmc_pdfs.py --max 20

    - name: Run PDF validation
      run: pytest tests/test_pdf_validation.py -v --tb=short

    - name: Upload PDF test results
      uses: actions/upload-artifact@v3
      with:
        name: pdf-validation-results
        path: reports/pdf_validation.json
```

### 7.2 Performance Regression Tests

```yaml
performance-tests:
  runs-on: ubuntu-latest
  steps:
    - name: Run benchmarks
      run: python benchmark/run_benchmarks.py --quick

    - name: Check for regressions
      run: python benchmark/check_regression.py --threshold 20%
```

### 7.3 Multi-Platform Testing

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python: [3.8, 3.9, 3.10, 3.11]
```

---

## Phase 8: Documentation & Reporting (Week 8)

### 8.1 Update Validation Report

Add sections for:
- Real PDF validation results
- Table extraction metrics
- Forest plot extraction metrics
- OCR stress test results
- External dataset validation

### 8.2 Create PDF Validation Report

**File:** `docs/PDF_VALIDATION_RESULTS.md`

| Metric | Born-Digital | Scanned | Overall |
|--------|-------------|---------|---------|
| PDFs tested | 80 | 15 | 95 |
| Text extraction CER | 0.5% | 3.2% | 1.1% |
| Effect extraction accuracy | 96.5% | 89.2% | 94.8% |
| Table extraction accuracy | 88.3% | 82.1% | 86.5% |
| Forest plot accuracy | 81.2% | N/A | 81.2% |

### 8.3 Update Tool Comparison

Re-run LLM benchmarks on PDF extraction:
- RCT Extractor on PDFs vs clean text
- GPT-4 Vision on PDFs
- Claude 3.5 on PDFs

---

## Implementation Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1 | PDF Collection | 50 PDFs downloaded |
| 2 | PDF Collection + Annotation | 100 PDFs, 30 annotated |
| 3 | Text Extraction Validation | 50 tests, CER metrics |
| 4 | Table Extraction | 25 tests, table accuracy |
| 5 | Forest Plot Extraction | 15 tests, plot accuracy |
| 6 | OCR Stress Testing | Degraded PDFs, thresholds |
| 7 | External Datasets | R packages, Zenodo |
| 8 | CI/CD + Documentation | Pipeline, final report |

---

## Success Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Real PDFs tested | 0 | 100+ | - |
| Born-digital accuracy | Unknown | > 95% | - |
| Scanned PDF accuracy | Unknown | > 88% | - |
| Table extraction accuracy | Unknown | > 85% | - |
| Forest plot accuracy | Unknown | > 80% | - |
| External datasets | 0 | 50+ | - |
| CI/CD PDF tests | No | Yes | - |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| PMC download rate limits | Cache PDFs, use off-peak hours |
| Tesseract accuracy issues | Try multiple PSM modes, pre-processing |
| Table extraction complexity | Start with simple tables, iterate |
| Forest plot variety | Focus on standard Cochrane format first |
| Annotation time | Prioritize most common trial types |

---

## Resource Requirements

| Resource | Quantity | Purpose |
|----------|----------|---------|
| Developer time | 8 weeks | Implementation |
| Annotator time | 40 hours | Gold standard creation |
| Storage | 5 GB | PDF collection |
| Compute | Standard CI | Automated testing |

---

## Version 4.1.0 Release Criteria

Before release, must achieve:
- [ ] 100+ real PDFs validated
- [ ] Born-digital accuracy > 95%
- [ ] Scanned PDF accuracy > 88%
- [ ] Table extraction accuracy > 85%
- [ ] All CI tests passing with real PDFs
- [ ] Updated validation report with PDF metrics
- [ ] External dataset validation complete

---

*Plan created: 2026-01-31*
*Target release: v4.1.0*
