# RCT Extractor v4.2 - Real PDF Improvement Plan
## Evidence-Based Enhancement Roadmap

**Created:** 2026-02-03
**Based On:** 105 Real PDF Validation Results
**Current Version:** 4.1.0
**Target Version:** 4.2.0

---

## Executive Summary

This improvement plan is based on **actual validation results** from 105 real PMC Open Access PDFs, not synthetic test cases. Key findings:

| Current Metric | Value | Issue | Target |
|----------------|-------|-------|--------|
| PDFs with Effects | 35% (37/105) | Many non-RCT papers | >60% (RCTs only) |
| CI Completion | 48% (276/575) | MD/SMD patterns weak | >85% |
| Full-Auto Rate | 47% (270/575) | Low confidence extractions | >80% |
| Respiratory Yield | 1 effect / 10 PDFs | Category failing | >5 effects/PDF |
| Diabetes Yield | 7 effects / 15 PDFs | Category weak | >10 effects/PDF |
| CTG-Linked PDFs | 18 | Limited validation | >50 |

---

## Previous Work Summary

### Completed (from V7 Plan)
- [x] Phase 1: CTG Integration - scraper and validator exist
- [x] Phase 2: Table Extraction - table_effect_extractor.py created
- [x] Phase 3: MD/SMD Patterns - 25+ patterns added
- [x] Phase 4: Multi-Language - German, French, Spanish support
- [x] Phase 7: API - FastAPI REST endpoints

### Still Pending
- [ ] Phase 5: Subgroup/NMA detection
- [ ] Phase 6: Advanced validation (Cochrane integration)

### New Issues Discovered
1. **PDF Corpus Quality**: ~35% of PDFs are not RCT results (letters, protocols, reviews)
2. **MD Pattern CI Gap**: 89 MD extractions, only ~10% have CIs
3. **Category Imbalance**: Respiratory (1 effect) vs Rheumatology (334 effects)
4. **Ground Truth Gap**: Only 18 PDFs have NCT IDs for CTG validation

---

## Phase 1: PDF Corpus Curation (Priority: CRITICAL)

### Problem
65% of PDFs (68/105) yield no extractions. Investigation shows many are:
- Letters/correspondence (PMC10695716, PMC10695721)
- Trial protocols without results (PMC12619345)
- Systematic reviews (PMC10034355)
- Non-RCT observational studies

### Solution: Filter corpus to RCT results only

**1.1 RCT Detection Classifier**
```python
# File: src/utils/rct_classifier.py

def is_rct_results_paper(text: str) -> dict:
    """
    Classify if paper is an RCT results publication.

    Returns:
        {
            'is_rct': bool,
            'is_results': bool,  # Has actual results, not protocol
            'confidence': float,
            'study_type': str,   # 'RCT', 'protocol', 'meta-analysis', 'observational', 'letter'
            'signals': list
        }
    """
    signals = {
        'rct_positive': [
            r'randomi[sz]ed',
            r'randomly\s+assigned',
            r'double[- ]blind',
            r'placebo[- ]controlled',
            r'intention[- ]to[- ]treat',
        ],
        'results_positive': [
            r'primary\s+(?:end\s*point|outcome).*(?:was|were)',
            r'hazard\s+ratio\s+(?:was|of|for)',
            r'odds\s+ratio\s+(?:was|of|for)',
            r'mean\s+difference',
            r'we\s+found\s+that',
        ],
        'protocol_signals': [
            r'study\s+protocol',
            r'trial\s+design',
            r'will\s+be\s+randomi[sz]ed',
            r'planned\s+enrollment',
        ],
        'letter_signals': [
            r'^letter\b',
            r'^correspondence\b',
            r'^response\b',
            r'^comment\b',
        ],
        'review_signals': [
            r'systematic\s+review',
            r'meta[- ]analysis',
            r'pooled\s+analysis',
            r'we\s+searched',
        ]
    }
```

**1.2 Corpus Tagging**
```bash
# Tag all 105 PDFs with study type
python scripts/classify_pdf_corpus.py test_pdfs/real_pdfs/ --output output/pdf_classifications.json
```

**Expected Outcome:**
- Identify ~40-50 true RCT results papers
- Filter out ~55-65 non-RCT papers
- Increase extraction yield to >60% on filtered corpus

---

## Phase 2: MD/SMD CI Pattern Enhancement (Priority: HIGH)

### Problem
From validation:
- Cardiology: 80 MD effects, only 1 with CI (1.25%)
- Neurology: 9 SMD effects, 0 with CI (0%)
- Overall MD/SMD CI rate: ~10%

### Root Cause Analysis
The current MD patterns extract values but miss CI formats common in real PDFs:

```
# Patterns that are being MISSED:
"mean difference 22.0 ml (95% CI, 3.5 to 40.5)"       # "ml" before CI
"MD -0.49 (−0.82, −0.16)"                              # Unicode minus, comma separator
"difference: -2.60 (95% CI: -2.97 to -2.23)"          # Colon formats
"effect size d = 0.55 [0.32, 0.78]"                   # Square bracket CI
"SMD −0.61 (95% CI −0.89 to −0.33)"                   # Unicode minus
```

### Solution: Add 20 New MD/SMD Patterns

**File: `src/core/enhanced_extractor_v3.py`**

```python
MD_PATTERNS_V42 = [
    # Format: "mean difference X ml (95% CI, Y to Z)" - units before CI
    r'mean\s+difference\s+([+-−]?\d+[.,]?\d*)\s*(?:ml|mL|kg|g|%|mmHg|points?)?\s*\(\s*(?:95%?\s*)?CI[,:\s]+([+-−]?\d+[.,]?\d*)\s+to\s+([+-−]?\d+[.,]?\d*)',

    # Format: "MD X (Y, Z)" - comma in CI, no "to"
    r'\bMD\b\s+([+-−]?\d+[.,]?\d*)\s*\(\s*([+-−]?\d+[.,]?\d*)\s*,\s*([+-−]?\d+[.,]?\d*)\s*\)',

    # Format: "difference: X (95% CI: Y to Z)" - colon before value
    r'difference[:\s]+([+-−]?\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+([+-−]?\d+[.,]?\d*)\s+to\s+([+-−]?\d+[.,]?\d*)',

    # Format: "MD −X (95% CI −Y to −Z)" - Unicode minus throughout
    r'\bMD\b\s+([+-−]?\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?CI\s+([+-−]?\d+[.,]?\d*)\s+to\s+([+-−]?\d+[.,]?\d*)',

    # Format: "mean difference, X; 95% CI, Y to Z" - semicolon separator
    r'mean\s+difference[,;]\s*([+-−]?\d+[.,]?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+([+-−]?\d+[.,]?\d*)\s+to\s+([+-−]?\d+[.,]?\d*)',

    # Format: "difference of X points (Y-Z)" - "of" and dash CI
    r'difference\s+of\s+([+-−]?\d+[.,]?\d*)\s*(?:points?|%|ml)?\s*\(\s*([+-−]?\d+[.,]?\d*)\s*[-–—]\s*([+-−]?\d+[.,]?\d*)\s*\)',

    # Format: "estimated difference X (95% CI Y, Z)" - comma CI
    r'estimated\s+(?:treatment\s+)?difference\s+([+-−]?\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?CI\s+([+-−]?\d+[.,]?\d*)\s*,\s*([+-−]?\d+[.,]?\d*)',

    # Format: "change from baseline: X (95% CI X to Y)"
    r'change\s+from\s+baseline[:\s]+([+-−]?\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+([+-−]?\d+[.,]?\d*)\s+to\s+([+-−]?\d+[.,]?\d*)',
]

SMD_PATTERNS_V42 = [
    # Format: "SMD X [Y, Z]" - square brackets
    r'\bSMD\b\s+([+-−]?\d+[.,]?\d*)\s*\[\s*([+-−]?\d+[.,]?\d*)\s*,\s*([+-−]?\d+[.,]?\d*)\s*\]',

    # Format: "effect size d = X (Y to Z)"
    r'effect\s+size\s+d\s*=\s*([+-−]?\d+[.,]?\d*)\s*\(\s*([+-−]?\d+[.,]?\d*)\s+to\s+([+-−]?\d+[.,]?\d*)',

    # Format: "Cohen's d X (95% CI Y-Z)"
    r"Cohen's\s+d\s+([+-−]?\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+([+-−]?\d+[.,]?\d*)\s*[-–—]\s*([+-−]?\d+[.,]?\d*)",

    # Format: "Hedges' g = X; 95% CI: Y to Z"
    r"Hedges'\s+g\s*=\s*([+-−]?\d+[.,]?\d*)\s*[;,]\s*(?:95%?\s*)?CI[:\s]+([+-−]?\d+[.,]?\d*)\s+to\s+([+-−]?\d+[.,]?\d*)",

    # Format: "standardised mean difference X (Y, Z)" - British spelling
    r'standardised\s+mean\s+difference\s+([+-−]?\d+[.,]?\d*)\s*\(\s*([+-−]?\d+[.,]?\d*)\s*,\s*([+-−]?\d+[.,]?\d*)',

    # Format: "pooled SMD = X (95% CI: Y to Z)"
    r'pooled\s+SMD\s*=\s*([+-−]?\d+[.,]?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+([+-−]?\d+[.,]?\d*)\s+to\s+([+-−]?\d+[.,]?\d*)',
]
```

### Test Cases from Real PDFs

| PDF | Current | Expected | Pattern Needed |
|-----|---------|----------|----------------|
| PMC12101153 | MD 22.00 (no CI) | MD 22.0 (3.5-40.5) | units before CI |
| PMC12788081 | MD -2.60 ✓ | ✓ | Already works |
| PMC12676894 | SMD -0.61 (no CI) | SMD -0.61 (-0.89,-0.33) | Unicode minus |

---

## Phase 3: Category-Specific Pattern Analysis (Priority: HIGH)

### Problem
Huge variance in extraction yield:
- Rheumatology: 334 effects (33.4/PDF) - inflated by large review
- Infectious: 33 effects (2.2/PDF) - reasonable
- Respiratory: 1 effect (0.1/PDF) - failing
- Diabetes: 7 effects (0.5/PDF) - weak

### Solution: Category-specific pattern investigation

**3.1 Respiratory Deep Dive**
```python
# Investigate why respiratory PDFs yield so few extractions
# File: scripts/investigate_category.py

def investigate_respiratory():
    """
    For each respiratory PDF:
    1. Extract full text
    2. Search for any effect-related terms
    3. Identify what patterns would match
    4. Report gaps
    """
    respiratory_pdfs = [
        'PMC10026740.pdf',  # 0 effects - why?
        'PMC10034355.pdf',  # 0 effects - systematic review
        'PMC10045420.pdf',  # 0 effects - why?
        ...
    ]
```

**3.2 Expected Respiratory Patterns**
Based on pulmonology literature:
```python
RESPIRATORY_PATTERNS = [
    # FEV1 changes
    r'FEV1\s+(?:change|difference)[:\s]+([+-−]?\d+[.,]?\d*)\s*(?:ml|mL|L)?\s*\(\s*(?:95%?\s*)?CI',

    # Rate ratios for exacerbations
    r'(?:exacerbation|AECOPD)\s+rate\s+ratio[:\s]+(\d+[.,]?\d*)\s*\(\s*(\d+[.,]?\d*)\s*[-–—]\s*(\d+[.,]?\d*)',

    # Symptom scores (SGRQ, CAT)
    r'(?:SGRQ|CAT)\s+(?:score\s+)?(?:change|difference)[:\s]+([+-−]?\d+[.,]?\d*)',
]
```

**3.3 Diabetes Patterns**
Based on endocrinology literature:
```python
DIABETES_PATTERNS = [
    # HbA1c changes - most common
    r'(?:HbA1c|A1C|glycated\s+h[ae]moglobin)\s+(?:change|reduction|difference)[:\s]+([+-−]?\d+[.,]?\d*)\s*%?\s*\(\s*(?:95%?\s*)?CI',

    # Weight changes (GLP-1 trials)
    r'(?:weight|body\s+weight)\s+(?:change|loss|reduction)[:\s]+([+-−]?\d+[.,]?\d*)\s*(?:kg|%)?\s*\(\s*(?:95%?\s*)?CI',

    # MACE HR (CV outcome trials)
    r'(?:MACE|major\s+adverse\s+cardiovascular)\s+(?:HR|hazard\s+ratio)[:\s]+(\d+[.,]?\d*)\s*\(\s*(\d+[.,]?\d*)',
]
```

---

## Phase 4: CTG Ground Truth Expansion (Priority: MEDIUM)

### Current State
- 18 PDFs have NCT IDs (17% of corpus)
- 15 are single-trial papers
- Limited ability to validate extractions

### Solution: Expand CTG linkage

**4.1 NCT ID Extraction Enhancement**
```python
# Current: Only scans first 5 pages
# New: Scan entire document + structured fields

def extract_nct_ids(pdf_content):
    """
    Extract NCT IDs from:
    1. Full text (all pages)
    2. References section
    3. Trial registration statements
    4. Footnotes
    """
    patterns = [
        r'NCT\d{8}',
        r'ClinicalTrials\.gov[:\s]+(\w+\d+)',
        r'trial\s+registration[:\s]+.*(NCT\d{8})',
        r'registered\s+(?:at|with).*?(NCT\d{8})',
    ]
```

**4.2 CTG Validation Pipeline**
```python
# File: scripts/run_ctg_validation.py

def validate_against_ctg():
    """
    For each PDF with NCT ID:
    1. Fetch CTG results
    2. Extract effects from PDF
    3. Compare values
    4. Report matches/mismatches
    """
```

### Target
- Expand to 50+ CTG-linked PDFs
- 90%+ match rate for effects with CTG results

---

## Phase 5: Table Extraction Integration (Priority: MEDIUM)

### Problem
From previous analysis: 2.4% of effects are in tables only, not running text.

### Current State
- `src/tables/table_effect_extractor.py` exists
- Not integrated into main validation pipeline

### Solution: Integrate table extraction

**5.1 Pipeline Integration**
```python
# In extraction pipeline:
def extract_from_pdf(pdf_path):
    # 1. Extract text
    text_effects = extract_from_text(pdf_content.full_text)

    # 2. Extract tables
    tables = extract_tables(pdf_content)
    table_effects = extract_from_tables(tables)

    # 3. Deduplicate (same effect in text and table)
    all_effects = deduplicate(text_effects + table_effects)

    return all_effects
```

**5.2 Table Test Set**
Create 20 annotated tables from real PDFs:
- 10 primary outcome tables
- 5 subgroup analysis tables
- 5 forest plot data tables

---

## Phase 6: Quality Metrics Dashboard (Priority: LOW)

### Problem
Hard to track progress without real-time metrics.

### Solution: Validation dashboard

```python
# File: scripts/validation_dashboard.py

def generate_dashboard():
    """
    Generate HTML dashboard with:
    - Overall extraction metrics
    - Per-category breakdown
    - Pattern hit rates
    - CI completion rates
    - Trend over versions
    """
```

---

## Implementation Order

| Phase | Focus | Effort | Impact | Priority |
|-------|-------|--------|--------|----------|
| 1 | PDF Corpus Curation | 1 day | HIGH | CRITICAL |
| 2 | MD/SMD CI Patterns | 2 days | HIGH | HIGH |
| 3 | Category Patterns | 3 days | MEDIUM | HIGH |
| 4 | CTG Expansion | 2 days | MEDIUM | MEDIUM |
| 5 | Table Integration | 2 days | MEDIUM | MEDIUM |
| 6 | Dashboard | 1 day | LOW | LOW |

---

## Success Criteria for v4.2.0

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| PDFs with Effects (RCTs only) | 35% | >60% | ❌ |
| CI Completion Rate | 48% | >85% | ❌ |
| Full-Auto Rate | 47% | >80% | ❌ |
| MD CI Rate | ~10% | >70% | ❌ |
| SMD CI Rate | 0% | >50% | ❌ |
| CTG-Linked PDFs | 18 | >50 | ❌ |
| CTG Match Rate | N/A | >90% | ❌ |

---

## Files to Create/Modify

### New Files
1. `src/utils/rct_classifier.py` - RCT detection
2. `scripts/classify_pdf_corpus.py` - Corpus tagging
3. `scripts/investigate_category.py` - Category analysis
4. `scripts/run_ctg_validation.py` - CTG validation
5. `scripts/validation_dashboard.py` - Metrics dashboard

### Files to Modify
1. `src/core/enhanced_extractor_v3.py` - Add 20+ new patterns
2. `run_enhanced_pdf_validation.py` - Integrate table extraction
3. `test_pdfs/manifest.json` - Add study type tags

---

## Quick Wins (Can Do Today)

1. **Tag 10 PDFs** with study type manually (1 hour)
2. **Add 5 MD CI patterns** for most common formats (2 hours)
3. **Investigate PMC10026740** (respiratory) manually (30 min)
4. **Run CTG validation** on 15 single-trial PDFs (1 hour)

---

## Appendix: Real PDF Evidence

### Zero-Extraction PDFs Investigated

| PDF | Category | Reason | Action |
|-----|----------|--------|--------|
| PMC10695716 | diabetes | Letter (2 pages) | Exclude |
| PMC10695721 | diabetes | Response (2 pages) | Exclude |
| PMC12619345 | diabetes | Trial protocol | Exclude |
| PMC10034355 | respiratory | Systematic review | Keep (different patterns) |
| PMC10026740 | respiratory | RCT but no effects found | Investigate |

### High-Yield PDFs

| PDF | Category | Effects | CI Rate | Notes |
|-----|----------|---------|---------|-------|
| PMC10000335 | rheumatology | 290 | 53% | Large review |
| PMC12101153 | cardiology | 80 | 1% | MD patterns failing |
| PMC10021491 | infectious | 12 | 100% | Good extraction |

---

*Plan created: 2026-02-03*
*Based on: 105 real PDF validation*
*Next review: After Phase 2 completion*
