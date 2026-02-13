# RCT Extractor v4.1 - Improvement Plan
## Next-Generation Validation & Feature Roadmap

**Created:** 2026-01-31
**Current Version:** 4.0.8
**Target Version:** 4.1.0

---

## Executive Summary

Based on the v4.0.8 validation results, this plan outlines priorities for further improvement:

| Current Metric | Value | Target |
|----------------|-------|--------|
| PDF Parse Rate | 100% | 100% |
| CI Completeness | 100% | 100% |
| Full-Auto Rate | 97.2% | >98% |
| Effect Types | HR, OR, RR | +MD, SMD, IRR |
| Table Extraction | Not validated | >90% accuracy |
| Multi-language | English only | +German, French, Spanish |

---

## Phase 1: ClinicalTrials.gov Integration

### 1.1 CTG Result Scraper
**Priority: HIGH**

Download and parse effect estimates from CTG results pages for validation.

**File:** `scripts/ctg_scraper.py`

```python
# Features:
# - Search by NCT ID
# - Extract primary/secondary outcomes
# - Get effect estimates with CIs
# - Cross-validate with PDF extractions
```

**Data Fields to Extract:**
- NCT ID
- Primary outcome measures
- Effect estimates (HR, OR, RR, MD)
- Confidence intervals
- P-values
- Sample sizes per arm

### 1.2 CTG Validation Dataset
**Target:** 500+ trials with CTG results

| Therapeutic Area | Target Count |
|------------------|--------------|
| Cardiology | 100 |
| Oncology | 100 |
| Neurology | 50 |
| Infectious Disease | 50 |
| Diabetes | 50 |
| Rheumatology | 50 |
| Other | 100 |

### 1.3 Cross-Validation Pipeline

```
CTG Results → Expected Values
      ↓
PDF Extraction → Extracted Values
      ↓
Comparison → Accuracy Metrics
```

**Metrics:**
- Value match rate (±0.01)
- CI match rate (±0.02)
- Effect type accuracy
- Sensitivity by outcome type

---

## Phase 2: Table Extraction Enhancement

### 2.1 Table-to-Effect Pipeline
**Priority: HIGH**

Currently ~25% of effects are in tables only. Need table extraction.

**File:** `src/tables/table_effect_extractor.py`

**Features:**
1. Detect outcome tables (vs baseline/safety)
2. Identify HR/OR/RR columns
3. Extract values with CIs
4. Link to outcome names

### 2.2 Table Detection Improvements

| Method | Current | Target |
|--------|---------|--------|
| pdfplumber | Basic | Enhanced cell detection |
| Heuristics | Row alignment | Column type inference |
| ML (optional) | Table Transformer | Fine-tuned on RCT tables |

### 2.3 Table Test Cases
**Target:** 50 tables from real PDFs

| Table Type | Cases |
|------------|-------|
| Primary outcomes | 20 |
| Subgroup analyses | 10 |
| Forest plot data | 10 |
| Safety summaries | 5 |
| Sensitivity analyses | 5 |

---

## Phase 3: Mean Difference & Continuous Outcomes

### 3.1 MD/SMD Pattern Expansion
**Priority: MEDIUM**

Current MD/SMD extraction is minimal. Need comprehensive patterns.

**New Patterns to Add:**

```python
MD_PATTERNS_NEW = [
    # "mean difference -2.5 (95% CI: -4.0 to -1.0)"
    r'mean\s+difference[:\s]+([+-]?\d+\.?\d*)\s*\(.*?([+-]?\d+\.?\d*)\s*to\s*([+-]?\d+\.?\d*)',

    # "MD = -3.2 mmHg (95% CI -5.1, -1.3)"
    r'\bMD\b\s*=?\s*([+-]?\d+\.?\d*)\s*\w*\s*\(.*?([+-]?\d+\.?\d*)[,\s]+([+-]?\d+\.?\d*)',

    # "difference between groups: 2.5 kg (1.2-3.8)"
    r'difference\s+between\s+groups[:\s]+([+-]?\d+\.?\d*)\s*\w*\s*\(([+-]?\d+\.?\d*)\s*[-–]\s*([+-]?\d+\.?\d*)',

    # "change from baseline: -5.2 ± 2.1"
    r'change\s+from\s+baseline[:\s]+([+-]?\d+\.?\d*)\s*[±\+\-]\s*(\d+\.?\d*)',
]

SMD_PATTERNS_NEW = [
    # "standardized mean difference 0.45 (0.22-0.68)"
    r'standardized\s+mean\s+difference[:\s]+([+-]?\d+\.?\d*)\s*\(([+-]?\d+\.?\d*)\s*[-–]\s*([+-]?\d+\.?\d*)',

    # "SMD = 0.32 (95% CI: 0.15 to 0.49)"
    r'\bSMD\b\s*=?\s*([+-]?\d+\.?\d*)\s*\(.*?([+-]?\d+\.?\d*)\s*to\s*([+-]?\d+\.?\d*)',

    # "Cohen's d = 0.55"
    r"Cohen's\s+d\s*=\s*([+-]?\d+\.?\d*)",

    # "Hedges' g = 0.42 (0.18, 0.66)"
    r"Hedges'\s+g\s*=\s*([+-]?\d+\.?\d*)\s*\(([+-]?\d+\.?\d*)[,\s]+([+-]?\d+\.?\d*)",
]
```

### 3.2 Continuous Outcome Test Set
**Target:** 50 trials with continuous outcomes

| Outcome Type | Cases |
|--------------|-------|
| Blood pressure | 15 |
| HbA1c | 10 |
| Weight/BMI | 10 |
| Quality of life scores | 10 |
| Biomarkers | 5 |

---

## Phase 4: Multi-Language Support

### 4.1 European Language Patterns
**Priority: MEDIUM**

Expand beyond English-only.

**Languages:**
- German (deu)
- French (fra)
- Spanish (spa)
- Italian (ita)

### 4.2 Language-Specific Patterns

```python
# German patterns
DE_PATTERNS = {
    'HR': r'Hazard[-\s]?Ratio[:\s]+(\d+[,.]?\d*)\s*\((\d+[,.]?\d*)\s*[-–]\s*(\d+[,.]?\d*)',
    'OR': r'Odds[-\s]?Ratio[:\s]+(\d+[,.]?\d*)\s*\((\d+[,.]?\d*)\s*[-–]\s*(\d+[,.]?\d*)',
    'CI': r'(?:95%?\s*)?(?:KI|Konfidenzintervall)[:\s]+(\d+[,.]?\d*)\s*[-–]\s*(\d+[,.]?\d*)',
}

# French patterns
FR_PATTERNS = {
    'HR': r'rapport\s+de\s+risque[:\s]+(\d+[,.]?\d*)\s*\((\d+[,.]?\d*)\s*[-–]\s*(\d+[,.]?\d*)',
    'OR': r'rapport\s+de\s+cotes[:\s]+(\d+[,.]?\d*)\s*\((\d+[,.]?\d*)\s*[-–]\s*(\d+[,.]?\d*)',
    'CI': r'(?:IC\s*95%?|intervalle\s+de\s+confiance)[:\s]+(\d+[,.]?\d*)\s*[-–]\s*(\d+[,.]?\d*)',
}
```

### 4.3 OCR Language Configuration

```python
OCR_LANG_CONFIG = {
    'en': 'eng',
    'de': 'deu+eng',
    'fr': 'fra+eng',
    'es': 'spa+eng',
    'multi': 'eng+deu+fra+spa',
}
```

### 4.4 Multi-Language Test Set
**Target:** 30 non-English PDFs

| Language | PDFs |
|----------|------|
| German | 10 |
| French | 10 |
| Spanish | 5 |
| Italian | 5 |

---

## Phase 5: Subgroup & Network Meta-Analysis

### 5.1 Subgroup Detection
**Priority: LOW**

Detect and extract subgroup analyses.

**Features:**
- Identify subgroup headers
- Extract interaction p-values
- Link effects to subgroup definitions
- Forest plot subgroup parsing

### 5.2 Network Meta-Analysis Support
**Priority: LOW**

Support indirect comparisons.

**Features:**
- Detect NMA studies
- Extract pairwise comparisons
- Handle SUCRA/P-scores
- Network geometry extraction

---

## Phase 6: Advanced Validation

### 6.1 Living Review Integration

Automated pipeline for living systematic reviews:

```
New Publication Alert
        ↓
PDF Download (PMC/CrossRef)
        ↓
Effect Extraction
        ↓
Quality Check (automation tier)
        ↓
Human Review (if needed)
        ↓
Update Meta-Analysis
```

### 6.2 Cochrane Integration

Validate against Cochrane systematic reviews:

| Resource | Usage |
|----------|-------|
| CDSR RevMan files | Gold standard effects |
| Risk of Bias data | Quality context |
| Forest plot data | Visual validation |

### 6.3 Performance Benchmarks

| Benchmark | Current | Target |
|-----------|---------|--------|
| Extraction speed | 50 docs/s | 100 docs/s |
| Memory usage | ~500MB | <300MB |
| API latency | N/A | <100ms |

---

## Phase 7: API & Integration

### 7.1 REST API
**File:** `src/api/main.py`

```python
# Endpoints:
POST /extract          # Extract from text
POST /extract/pdf      # Extract from PDF
GET  /validate/{id}    # Validate extraction
GET  /health           # Health check
```

### 7.2 Python Package

```bash
pip install rct-extractor
```

```python
from rct_extractor import extract, extract_pdf

effects = extract("HR 0.74 (95% CI: 0.65-0.85)")
pdf_effects = extract_pdf("study.pdf")
```

### 7.3 Integration Options

| Platform | Integration |
|----------|-------------|
| Covidence | Export plugin |
| RevMan | Data import |
| R meta/metafor | Data exchange |
| GRADE | Quality linking |

---

## Implementation Timeline

| Phase | Focus | Duration | Priority |
|-------|-------|----------|----------|
| 1 | CTG Integration | 2 weeks | HIGH |
| 2 | Table Extraction | 2 weeks | HIGH |
| 3 | MD/SMD Patterns | 1 week | MEDIUM |
| 4 | Multi-Language | 2 weeks | MEDIUM |
| 5 | Subgroup/NMA | 2 weeks | LOW |
| 6 | Advanced Validation | 2 weeks | MEDIUM |
| 7 | API & Integration | 2 weeks | LOW |

---

## Success Metrics

### v4.1.0 Release Criteria

| Metric | Requirement |
|--------|-------------|
| Overall Sensitivity | >98% |
| CI Completeness | >99% |
| Full-Auto Rate | >98% |
| Table Extraction | >90% |
| MD/SMD Coverage | >80% |
| Multi-Language | >85% (de, fr) |
| CTG Validation | 500+ trials |
| Regulatory Tests | 100% pass |

---

## Files to Create/Modify

### New Files
1. `scripts/ctg_scraper.py` - CTG results scraper
2. `scripts/ctg_validator.py` - Cross-validation with CTG
3. `src/tables/table_effect_extractor.py` - Table-to-effect pipeline
4. `src/lang/multi_lang_extractor.py` - Multi-language support
5. `src/subgroup/subgroup_detector.py` - Subgroup analysis
6. `src/api/main.py` - REST API
7. `tests/test_ctg_validation.py` - CTG tests
8. `tests/test_multi_language.py` - Language tests

### Files to Update
1. `src/core/enhanced_extractor_v3.py` - New MD/SMD patterns
2. `src/tables/table_extractor.py` - Enhanced detection
3. `src/pdf/pdf_parser.py` - Multi-language OCR
4. `requirements.txt` - New dependencies
5. `.github/workflows/test.yml` - New test jobs

---

## Quick Wins (Can Do Now)

1. **Add 5 more OR patterns** for common PDF formats
2. **CTG scraper prototype** using requests + BeautifulSoup
3. **MD pattern expansion** (10 new patterns)
4. **German HR/OR patterns** (basic support)
5. **Table outcome detection** (keyword-based)

---

## Data Sources for Validation

| Source | Type | Access |
|--------|------|--------|
| PubMed Central | Open PDFs | Free API |
| ClinicalTrials.gov | Results | Free API |
| Cochrane CDSR | RevMan | Subscription |
| Zenodo | Datasets | Free |
| R Packages | Test data | Free |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| OCR quality variation | Multi-engine fallback |
| Table format diversity | Hybrid detection methods |
| Language edge cases | Community contributions |
| API rate limits | Caching, batch processing |

---

*Plan created: 2026-01-31*
*Next review: After Phase 1 completion*
