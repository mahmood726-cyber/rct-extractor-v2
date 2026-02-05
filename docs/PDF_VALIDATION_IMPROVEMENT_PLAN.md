# Real PDF Extraction Improvement Plan

## Current State Assessment

### Assets Available
- **105 real RCT PDFs** in `test_pdfs/real_pdfs/`
- **PDF parser** with PyMuPDF + pdfplumber + OCR fallback
- **Effect extractor** with 90.3% recall on snippets
- **Comprehensive test infrastructure**

### Critical Gap
- **0 PDFs have ground truth annotations**
- Current validation uses pre-selected text snippets, not full PDF extraction
- No measurement of end-to-end PDF→effect accuracy

---

## Phase 1: Ground Truth Creation (Week 1-2)

### 1.1 Rapid Annotation Protocol

Create ground truth for 50 PDFs using semi-automated approach:

```
1. Run extractor on full PDF text
2. Present extractions to human reviewer
3. Reviewer marks: CORRECT / INCORRECT / MISSED
4. Reviewer adds any missed effects
5. Calculate per-PDF precision/recall
```

**Annotation Schema** (`test_pdfs/gold_standard/annotations/`):
```json
{
  "pdf_id": "PMC11419598",
  "annotator": "reviewer_1",
  "annotation_date": "2026-02-03",
  "effects": [
    {
      "type": "HR",
      "value": 0.74,
      "ci_lower": 0.65,
      "ci_upper": 0.85,
      "outcome": "CV death or HF hospitalization",
      "location": "abstract",
      "page": 1,
      "source_text": "hazard ratio, 0.74; 95% CI, 0.65 to 0.85"
    }
  ],
  "extraction_results": {
    "true_positives": 3,
    "false_positives": 1,
    "false_negatives": 0
  }
}
```

### 1.2 Priority PDF Selection

Select 50 PDFs for initial annotation:

| Category | Count | Criteria |
|----------|-------|----------|
| Cardiology | 15 | HR-heavy, NEJM-style |
| Oncology | 10 | HR/OS/PFS endpoints |
| Diabetes | 8 | MD endpoints (HbA1c) |
| Infectious | 7 | RR/vaccine efficacy |
| Neurology | 5 | MD (cognitive scores) |
| Rheumatology | 5 | OR/response rates |

### 1.3 Annotation Tool

Create `scripts/annotate_pdf_extractions.py`:

```python
def annotate_pdf(pdf_path: Path) -> Annotation:
    """
    1. Extract text from PDF
    2. Run effect extractor
    3. Display extractions with context
    4. Prompt for validation
    5. Save annotation
    """
```

---

## Phase 2: End-to-End Validation Pipeline (Week 2-3)

### 2.1 Full PDF Extraction Validation

Create `scripts/validate_pdf_extraction.py`:

```python
def validate_pdf_corpus(
    pdf_dir: Path,
    annotations_dir: Path
) -> ValidationReport:
    """
    For each annotated PDF:
    1. Parse PDF → full text
    2. Run effect extraction
    3. Match against ground truth
    4. Calculate metrics
    """
```

### 2.2 Metrics to Track

| Metric | Description | Target |
|--------|-------------|--------|
| **PDF Parse Success** | PDFs that parse without error | >95% |
| **Text Extraction Quality** | Character accuracy vs original | >98% |
| **Effect Recall (full PDF)** | Effects found / effects in GT | >80% |
| **Effect Precision (full PDF)** | Correct / total extracted | >60% |
| **CI Completion (full PDF)** | With CI / matched | >85% |
| **Location Accuracy** | Correct page/section | >90% |

### 2.3 Error Classification

Track failure modes:

| Failure Type | Description | Example |
|--------------|-------------|---------|
| `PARSE_ERROR` | PDF cannot be parsed | Corrupted file |
| `OCR_ERROR` | Text extraction failed | Scanned PDF |
| `PATTERN_MISS` | Effect present, pattern missed | Novel format |
| `TABLE_MISS` | Effect in table, not extracted | Complex table |
| `MULTI_PAGE` | Effect spans pages | Split sentence |
| `CONTEXT_FP` | Extracted from wrong context | Methods section |

---

## Phase 3: Failure Analysis and Pattern Improvement (Week 3-4)

### 3.1 Systematic Failure Analysis

For each false negative:
1. Extract 500-char context around ground truth effect
2. Identify why pattern failed
3. Categorize failure type
4. Design pattern fix

### 3.2 Pattern Categories Needing Work

Based on PDF analysis, likely gaps:

| Pattern Type | Current Coverage | Gap |
|--------------|------------------|-----|
| Table cell effects | ~30% | Need table-specific patterns |
| Figure captions | ~20% | Forest plot legends |
| Supplement refs | ~10% | "see Table S1" |
| Multi-line effects | ~50% | CI split across lines |
| Footnote effects | ~20% | Table footnotes |

### 3.3 Pattern Development Workflow

```
1. Identify failure cluster (e.g., table effects)
2. Collect 10+ examples from PDFs
3. Design regex pattern
4. Test on examples
5. Validate doesn't break existing tests
6. Add to pattern library
```

---

## Phase 4: Table Extraction Enhancement (Week 4-5)

### 4.1 Table Detection

Current `pdfplumber` extracts tables but patterns don't handle well.

**Improvement**: Pre-process table cells for effect extraction:

```python
def extract_effects_from_tables(pdf_content: PDFContent) -> List[Extraction]:
    for page in pdf_content.pages:
        tables = pdfplumber.extract_tables(page)
        for table in tables:
            # Identify header row (HR, CI, p-value columns)
            # Extract cell values
            # Create structured effects
```

### 4.2 Table Pattern Library

Add patterns for common table formats:

| Format | Example | Pattern |
|--------|---------|---------|
| Header row | `HR (95% CI)` then `0.74 (0.65-0.85)` | Column matching |
| Inline cell | `HR=0.74; CI 0.65-0.85` | Cell-specific |
| Footnote ref | `0.74*` with `* p<0.001` | Footnote linking |

---

## Phase 5: Section-Aware Extraction (Week 5-6)

### 5.1 Section Detection

Identify document sections to improve precision:

| Section | Effect Validity | Action |
|---------|-----------------|--------|
| Abstract | HIGH | Extract, high confidence |
| Results | HIGH | Extract, high confidence |
| Tables | HIGH | Extract with table parser |
| Methods | LOW | Flag as "assumed/planned" |
| Discussion | MEDIUM | Extract but flag |
| References | NONE | Skip entirely |

### 5.2 Section Detection Heuristics

```python
SECTION_PATTERNS = {
    'abstract': r'^(?:ABSTRACT|Summary)\s*$',
    'methods': r'^(?:METHODS|Materials and Methods)\s*$',
    'results': r'^(?:RESULTS|Findings)\s*$',
    'discussion': r'^(?:DISCUSSION|Interpretation)\s*$',
}

def detect_section(text_block: TextBlock) -> str:
    """Detect section from heading text"""
```

### 5.3 Section-Specific Confidence

Adjust extraction confidence based on section:

| Section | Confidence Multiplier |
|---------|----------------------|
| Abstract | 1.0 |
| Results | 1.0 |
| Tables | 0.95 (needs structure validation) |
| Discussion | 0.7 |
| Methods | 0.3 (likely hypothetical) |

---

## Phase 6: OCR Quality Handling (Week 6)

### 6.1 OCR Detection and Preprocessing

Enhance OCR handling for scanned PDFs:

```python
def preprocess_ocr_text(text: str, confidence: float) -> str:
    """
    Fix common OCR errors:
    - 0.74 → O.74 (letter O)
    - CI → Cl (lowercase L)
    - 95% → 9S% (S for 5)
    """
```

### 6.2 OCR Quality Thresholds

| Confidence | Action |
|------------|--------|
| >90% | Extract normally |
| 70-90% | Extract with warning |
| 50-70% | Manual review required |
| <50% | Reject, flag for reprocessing |

---

## Phase 7: Continuous Validation Pipeline (Week 7-8)

### 7.1 Automated Validation Script

Create `scripts/run_pdf_validation.py`:

```bash
# Run weekly
python scripts/run_pdf_validation.py \
  --pdf-dir test_pdfs/real_pdfs/ \
  --annotations test_pdfs/gold_standard/annotations/ \
  --output output/pdf_validation_$(date +%Y%m%d).json
```

### 7.2 Regression Detection

Alert if metrics drop:

```python
def check_regression(current: Metrics, baseline: Metrics) -> List[Alert]:
    alerts = []
    if current.recall < baseline.recall - 0.05:
        alerts.append(Alert("Recall dropped by >5%"))
    if current.precision < baseline.precision - 0.05:
        alerts.append(Alert("Precision dropped by >5%"))
    return alerts
```

### 7.3 Validation Dashboard

Track over time:
- Per-PDF extraction success rate
- Pattern hit rates
- Failure type distribution
- OCR quality trends

---

## Implementation Checklist

### Week 1-2: Ground Truth
- [ ] Create annotation schema
- [ ] Build annotation tool
- [ ] Annotate 25 PDFs (batch 1)
- [ ] Annotate 25 PDFs (batch 2)
- [ ] Calculate initial metrics

### Week 3-4: Validation Pipeline
- [ ] Create end-to-end validation script
- [ ] Run on annotated corpus
- [ ] Generate failure report
- [ ] Categorize failure modes

### Week 4-5: Pattern Fixes
- [ ] Fix top 5 pattern gaps
- [ ] Add table extraction patterns
- [ ] Add multi-line patterns
- [ ] Regression test

### Week 5-6: Section Awareness
- [ ] Implement section detection
- [ ] Add section-based confidence
- [ ] Validate on corpus

### Week 6-7: OCR Enhancement
- [ ] Enhance OCR preprocessing
- [ ] Add quality thresholds
- [ ] Test on scanned PDFs

### Week 7-8: Continuous Pipeline
- [ ] Create automated validation script
- [ ] Set up regression detection
- [ ] Deploy monitoring

---

## Success Criteria

### Minimum Viable (v5.0)
- [ ] 50 PDFs with ground truth
- [ ] Full PDF recall >75%
- [ ] Full PDF precision >55%
- [ ] Parse success >95%

### Production Ready (v6.0)
- [ ] 100 PDFs with ground truth
- [ ] Full PDF recall >85%
- [ ] Full PDF precision >65%
- [ ] Section-aware extraction
- [ ] Table extraction working
- [ ] Continuous validation deployed

---

## Resource Estimates

| Task | Hours | Notes |
|------|-------|-------|
| Annotation tool | 8 | Semi-automated |
| Annotate 50 PDFs | 25 | ~30 min/PDF |
| Validation pipeline | 16 | End-to-end |
| Pattern fixes | 20 | Iterative |
| Section detection | 12 | Heuristics |
| OCR enhancement | 8 | Preprocessing |
| Continuous pipeline | 8 | Automation |
| **Total** | **~100 hours** | ~2.5 weeks FTE |
