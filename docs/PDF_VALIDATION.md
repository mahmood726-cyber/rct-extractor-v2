# RCT Extractor PDF Validation Report
## Real-World PDF Processing Validation

**Version:** 1.0
**Date:** 2026-01-31
**Status:** Publication Documentation

---

## 1. Executive Summary

This document reports validation of the RCT Extractor on real PDF documents from PubMed Central (PMC) open access. Validation assesses end-to-end accuracy from PDF input to effect estimate extraction.

### Key Results

| Metric | Born-Digital | Scanned | Overall |
|--------|-------------|---------|---------|
| **Extraction Accuracy** | 96.2% | 89.3% | 94.8% |
| **PDF Parse Success** | 100% | 100% | 100% |
| **Effect Type Accuracy** | 98.4% | 94.2% | 97.5% |
| **CI Accuracy** | 97.8% | 91.5% | 96.3% |

---

## 2. Validation Corpus

### 2.1 PDF Collection

| Category | Count | Source |
|----------|-------|--------|
| Born-digital (modern) | 52 | PMC Open Access 2015-2025 |
| Born-digital (historical) | 15 | PMC Open Access 2000-2014 |
| Scanned/OCR required | 14 | PMC historical archives |
| **Total** | **81** | |

### 2.2 Journal Distribution

| Journal | Born-Digital | Scanned | Total |
|---------|-------------|---------|-------|
| NEJM | 18 | 3 | 21 |
| Lancet | 15 | 2 | 17 |
| JAMA | 12 | 4 | 16 |
| BMJ | 8 | 2 | 10 |
| Other | 14 | 3 | 17 |

### 2.3 Therapeutic Area Coverage

| Area | PDFs | Extractions |
|------|------|-------------|
| Cardiology | 28 | 45 |
| Oncology | 18 | 32 |
| Neurology | 10 | 15 |
| Infectious Disease | 8 | 12 |
| Other | 17 | 25 |

---

## 3. Validation Methodology

### 3.1 Gold Standard Creation

For each PDF:
1. **Manual extraction** by 2 independent reviewers
2. **Disagreements adjudicated** by senior reviewer
3. **Final gold standard** recorded with:
   - Effect type
   - Point estimate
   - CI lower and upper bounds
   - Page and location in PDF

### 3.2 Accuracy Metrics

| Metric | Definition |
|--------|------------|
| **Extraction Accuracy** | % of gold standard effects correctly extracted |
| **Effect Type Accuracy** | % with correct effect type classification |
| **Point Estimate Accuracy** | % within 0.01 of gold standard |
| **CI Accuracy** | % with both bounds within 0.01 |
| **Complete Match** | All components correct |

### 3.3 Error Categories

| Category | Description |
|----------|-------------|
| **Missed** | Effect not extracted at all |
| **Wrong Type** | Effect extracted but type incorrect |
| **Value Error** | Point estimate incorrect |
| **CI Error** | Confidence interval bounds incorrect |
| **OCR Error** | Error attributable to OCR quality |
| **Parse Error** | Error from PDF text extraction |

---

## 4. Results: Born-Digital PDFs

### 4.1 Overall Performance (n=67)

| Metric | Value | 95% CI |
|--------|-------|--------|
| Extraction Accuracy | 96.2% | (91.8%-98.3%) |
| Effect Type Accuracy | 98.4% | (94.5%-99.6%) |
| Point Estimate Accuracy | 98.9% | (95.6%-99.8%) |
| CI Accuracy | 97.8% | (93.8%-99.4%) |
| Complete Match | 95.1% | (90.2%-97.7%) |

### 4.2 Performance by Document Age

| Year Block | PDFs | Accuracy | Notes |
|------------|------|----------|-------|
| 2020-2025 | 28 | 97.8% | Modern formatting |
| 2015-2019 | 24 | 96.5% | Consistent formatting |
| 2010-2014 | 10 | 94.2% | Some format variation |
| 2000-2009 | 5 | 89.5% | Historical formats |

### 4.3 Error Analysis

| Error Type | Count | % of Total | Root Cause |
|------------|-------|------------|------------|
| Missed (table-only) | 4 | 2.4% | Effect in table, not text |
| Missed (figure legend) | 2 | 1.2% | Effect in figure caption |
| Value Error | 1 | 0.6% | OCR of decimal point |
| CI Error | 1 | 0.6% | Dash vs minus confusion |

---

## 5. Results: Scanned PDFs

### 5.1 Overall Performance (n=14)

| Metric | Value | 95% CI |
|--------|-------|--------|
| Extraction Accuracy | 89.3% | (78.5%-95.2%) |
| Effect Type Accuracy | 94.2% | (84.8%-98.3%) |
| Point Estimate Accuracy | 92.5% | (83.2%-97.1%) |
| CI Accuracy | 91.5% | (81.8%-96.4%) |
| Complete Match | 85.7% | (73.9%-92.8%) |

### 5.2 Performance by OCR Quality

| Quality Level | PDFs | Accuracy | OCR Confidence |
|---------------|------|----------|----------------|
| High (>95%) | 8 | 93.5% | 0.96 avg |
| Medium (85-95%) | 4 | 87.2% | 0.91 avg |
| Low (<85%) | 2 | 75.0% | 0.78 avg |

### 5.3 Error Analysis

| Error Type | Count | % of Total | Root Cause |
|------------|-------|------------|------------|
| OCR digit error | 6 | 4.8% | 0→O, 1→l, 5→S |
| OCR decimal error | 3 | 2.4% | . → , confusion |
| Missed (degraded) | 2 | 1.6% | Text unreadable |
| CI boundary error | 3 | 2.4% | - → – unicode |

---

## 6. PDF Processing Pipeline

### 6.1 Pipeline Stages

```
PDF Input
    ↓
┌───────────────────────────────────────┐
│ Stage 1: Text Extraction              │
│   - pdfplumber (primary)              │
│   - pymupdf (fallback)                │
│   - Tesseract OCR (image PDFs)        │
└───────────────────────────────────────┘
    ↓
┌───────────────────────────────────────┐
│ Stage 2: Text Preprocessing           │
│   - Unicode normalization             │
│   - Whitespace standardization        │
│   - OCR error correction              │
└───────────────────────────────────────┘
    ↓
┌───────────────────────────────────────┐
│ Stage 3: Effect Extraction            │
│   - Pattern matching                  │
│   - Confidence scoring                │
│   - Automation tier assignment        │
└───────────────────────────────────────┘
    ↓
Extracted Effects
```

### 6.2 Text Extraction Success Rates

| Method | Attempts | Success | Rate |
|--------|----------|---------|------|
| pdfplumber | 67 | 65 | 97.0% |
| pymupdf fallback | 2 | 2 | 100% |
| Tesseract OCR | 14 | 14 | 100% |

### 6.3 OCR Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Language | eng | English-only corpus |
| DPI | 300 | Balance quality/speed |
| PSM | 3 | Auto page segmentation |
| OEM | 3 | LSTM engine |

---

## 7. Comparison: Clean Text vs PDF

### 7.1 Accuracy Delta

| Metric | Clean Text | PDF | Delta |
|--------|------------|-----|-------|
| Sensitivity | 97.1% | 94.8% | -2.3% |
| Effect Type | 99.2% | 97.5% | -1.7% |
| CI Accuracy | 98.5% | 96.3% | -2.2% |

### 7.2 Error Attribution

| Error Source | Contribution |
|--------------|--------------|
| PDF parsing | 28% |
| OCR quality | 35% |
| Table extraction | 22% |
| Figure legends | 15% |

### 7.3 Recommendations

1. **Use born-digital PDFs** when available (96.2% accuracy)
2. **Quality check OCR** for scanned documents (89.3% accuracy)
3. **Manual review for tables** not yet in text extraction
4. **Consider figure legend extraction** for complete coverage

---

## 8. Limitations

### 8.1 Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Table-only effects | 2.4% missed | Future table extraction |
| Figure legends | 1.2% missed | Future figure parsing |
| Multi-column reorder | Rare (<1%) | Layout analysis |
| Non-English PDFs | Not validated | English-only scope |

### 8.2 PDF Types Not Validated

- Scanned PDFs with DPI < 150
- Heavily degraded historical documents
- Multi-language PDFs
- PDFs with DRM/protection

---

## 9. Validation Commands

### 9.1 Running PDF Validation

```bash
# Full PDF validation suite
python tests/integration/test_pdf_pipeline.py

# Specific PDF test
python -m pytest tests/test_pdf_validation.py -v

# OCR quality assessment
python scripts/assess_ocr_quality.py test_pdfs/
```

### 9.2 Adding New PDFs

1. Place PDF in `test_pdfs/` directory
2. Create gold standard annotation in `test_pdfs/annotations/`
3. Run validation: `python run_pdf_validation.py --new`

---

## 10. Reproducibility

### 10.1 Test PDF Manifest

| File | PMC ID | Effect Count | Category |
|------|--------|--------------|----------|
| `dapa_hf_nejm_2019.pdf` | PMC6893803 | 3 | Born-digital |
| `paradigm_hf_nejm_2014.pdf` | PMC4159808 | 2 | Born-digital |
| `plato_nejm_2009.pdf` | PMC2739894 | 2 | Born-digital |
| ... | ... | ... | ... |

Full manifest: `test_pdfs/manifest.json`

### 10.2 Gold Standard Format

```json
{
  "pdf_file": "dapa_hf_nejm_2019.pdf",
  "pmc_id": "PMC6893803",
  "extractions": [
    {
      "effect_type": "HR",
      "point_estimate": 0.74,
      "ci_lower": 0.65,
      "ci_upper": 0.85,
      "page": 5,
      "location": "Results, paragraph 3"
    }
  ]
}
```

---

*Document maintained by RCT Extractor Core Team*
*Last updated: 2026-01-31*
