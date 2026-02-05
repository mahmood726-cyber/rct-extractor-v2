# PDF Extraction Gap Closure Plan

## Goal
Close the gap between snippet validation (93% CI completion) and full PDF extraction (63.7% CI completion).

**Target:** Achieve >80% CI completion on full PDF extraction within a curated RCT corpus.

---

## Current State Analysis

| Metric | Snippet | Full PDF | Gap |
|--------|---------|----------|-----|
| CI Completion | 93.0% | 63.7% | 29.3 pts |
| Extraction Rate | 100%* | 74.1% | 25.9 pts |

*Snippets are pre-selected, so 100% by definition

### Gap Sources (Hypothesis)
1. **PDF Layout Issues** (~40% of gap): Multi-column layouts fragment text
2. **Table Formatting** (~30% of gap): Effect values and CIs in separate cells
3. **Corpus Quality** (~20% of gap): Non-RCT papers included
4. **Pattern Gaps** (~10% of gap): Unusual formats not covered

---

## Phase 1: Corpus Curation (Day 1)

### 1.1 Manual PDF Classification
Review all 58 PDFs and classify:
- **A: Primary RCT Results** - Reports primary endpoint with HR/OR/RR/MD
- **B: Secondary Analysis** - Post-hoc, subgroup analyses
- **C: Non-RCT** - Methods, reviews, educational studies

### 1.2 Create Ground Truth
For each Class A PDF:
- Extract primary endpoint effect manually
- Record: effect type, value, CI, page number, exact source text
- Flag: in_table, in_figure, multi_column

### 1.3 Deliverables
- `data/pdf_ground_truth.json` - Manual annotations
- `data/pdf_classification.json` - A/B/C classification
- Curated corpus of 30+ verified RCT PDFs

---

## Phase 2: Failure Categorization (Day 2)

### 2.1 Categorize Every Missing CI
For each extraction without CI:
- **NOT_REPORTED**: Source paper doesn't report CI
- **IN_TABLE**: CI exists but in table format
- **PATTERN_GAP**: CI in text but pattern missed
- **TEXT_FRAGMENTED**: CI split across columns/pages
- **OCR_ERROR**: Text extraction corrupted

### 2.2 Categorize Zero-Extraction PDFs
For each PDF with 0 extractions:
- **NON_RCT**: Not an RCT results paper
- **TABLE_ONLY**: All effects in tables
- **UNUSUAL_FORMAT**: Effects in non-standard format
- **PARSE_FAILURE**: PDF text extraction failed

### 2.3 Deliverables
- `output/failure_categorization.json`
- Quantified breakdown of gap sources

---

## Phase 3: PDF Parser Enhancement (Days 3-4)

### 3.1 Multi-Column Reordering
Current issue: Two-column PDFs extract as interleaved text.

**Solution:** Implement column detection and reordering:
```python
def reorder_columns(page_text, page_width):
    # Detect column boundaries
    # Group text blocks by column
    # Return left column + right column sequentially
```

### 3.2 Table Extraction Pipeline
Current issue: Table cells extracted separately, breaking patterns.

**Solution:** Dedicated table extraction:
```python
def extract_effects_from_tables(pdf_path):
    # Use pdfplumber table extraction
    # Identify header rows (HR, CI, p-value columns)
    # Parse cell values as structured data
    # Return list of TableExtraction objects
```

### 3.3 CI Proximity Search
Current issue: Value found but CI not adjacent in extracted text.

**Solution:** When value-only extraction found, search wider context:
```python
def find_nearby_ci(text, value_position, effect_type, window=500):
    # Search ±500 chars for CI pattern
    # Match CI to value if plausible range
    # Return enhanced extraction with CI
```

### 3.4 Deliverables
- Enhanced `PDFParser` with column reordering
- `TableExtractor` class for structured table parsing
- `CIProximitySearch` post-processor

---

## Phase 4: Pattern Enhancement (Day 5)

### 4.1 Table-Specific Patterns
Add patterns for common table formats:
- Header: `HR (95% CI)` → Cell: `0.74 (0.65-0.85)`
- Header: `HR` | `95% CI` → Cell: `0.74` | `0.65-0.85`

### 4.2 Cross-Line Patterns
Enable multiline matching for split effects:
```
hazard ratio 0.74
(95% CI, 0.65 to 0.85)
```

### 4.3 Figure Caption Patterns
Extract from forest plot captions:
```
Figure 2. HR 0.74 (95% CI 0.65-0.85) favoring treatment
```

### 4.4 Deliverables
- 20+ new table/figure patterns
- Multiline pattern support
- Updated pattern tests

---

## Phase 5: Validation Pipeline (Day 6)

### 5.1 Ground Truth Matching
```python
def validate_against_ground_truth(extractions, ground_truth):
    # Match extractions to GT by value proximity
    # Calculate: TP, FP, FN for each PDF
    # Report: precision, recall, CI_completion
```

### 5.2 Failure Analysis Report
For each FN (missed extraction):
- Show GT value and source text
- Show extracted text around GT location
- Categorize failure reason

### 5.3 Regression Testing
- Hold out 10 PDFs for final validation
- Track metrics across versions
- Alert on regression >5%

### 5.4 Deliverables
- `scripts/validate_pdf_ground_truth.py`
- `output/pdf_validation_report.html`
- CI/regression test suite

---

## Phase 6: Iteration and Refinement (Days 7-10)

### 6.1 Fix Top Failure Modes
Prioritize fixes by impact:
1. Highest frequency failure category
2. Easiest to fix
3. Repeat until >80% CI completion

### 6.2 Expand Corpus
- Add 20 more verified RCT PDFs
- Ensure effect type diversity
- Re-validate on expanded corpus

### 6.3 Final Validation
- Run on held-out test set
- Compare to snippet baseline
- Document remaining limitations

---

## Success Criteria

| Metric | Current | Target | Stretch |
|--------|---------|--------|---------|
| CI Completion (full PDF) | 63.7% | >80% | >85% |
| Extraction Rate | 74.1% | >85% | >90% |
| Gap to Snippet | 29.3 pts | <15 pts | <10 pts |

---

## Implementation Priority

### Must Have (P0)
- [ ] Manual PDF classification and ground truth
- [ ] Failure categorization
- [ ] CI proximity search
- [ ] Ground truth validation script

### Should Have (P1)
- [ ] Table extraction pipeline
- [ ] Multi-column reordering
- [ ] Cross-line pattern support

### Nice to Have (P2)
- [ ] Figure caption extraction
- [ ] Automated corpus expansion
- [ ] Real-time validation dashboard

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Ground truth creation too slow | Focus on 30 high-quality PDFs first |
| Table extraction unreliable | Fall back to pattern-based extraction |
| Column reordering breaks good PDFs | Make it optional, test thoroughly |
| Overfitting to test corpus | Maintain held-out validation set |

---

## Timeline

| Day | Focus | Deliverable |
|-----|-------|-------------|
| 1 | Corpus curation | 30+ verified RCT PDFs with ground truth |
| 2 | Failure analysis | Quantified gap breakdown |
| 3-4 | Parser enhancement | Column reorder, table extract, CI search |
| 5 | Pattern enhancement | Table/figure patterns |
| 6 | Validation pipeline | Ground truth validation |
| 7-10 | Iteration | >80% CI completion |
