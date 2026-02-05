# Real PDF Extraction Validation - Practical Plan

## Critical Finding

The current "real PDFs" corpus (`test_pdfs/real_pdfs/`) contains:
- **Systematic reviews** (citing effects from other studies)
- **Protocols** (planned studies without results)
- **Observational studies** (non-RCT designs)
- **Editorials and comments**

**0% of sampled PDFs are primary RCT results papers.**

This explains why:
- Full PDF extraction rate: 35%
- CI completion: 10.7%
- High "MD" extractions (from review statistics)

---

## Phase 1: Acquire Actual RCT Results PDFs

### Option A: Manual Curation (Recommended)

Download specific RCT results papers manually from:

| Trial | PMC ID | Journal | How to Get |
|-------|--------|---------|------------|
| DAPA-HF | PMC6832437 | NEJM | Search PMC, click PDF link |
| PARADIGM-HF | PMC4212585 | NEJM | Search PMC, click PDF link |
| EMPEROR-Reduced | PMC7592000 | NEJM | Search PMC, click PDF link |
| KEYNOTE-024 | PMC5101118 | NEJM | Search PMC, click PDF link |

**Process**:
1. Go to https://www.ncbi.nlm.nih.gov/pmc/
2. Search for PMC ID
3. Click "PDF" link
4. Save to `test_pdfs/validated_rcts/{PMC_ID}.pdf`

**Target**: 30 primary RCT results papers

### Option B: PMC FTP (Bulk Access)

PMC provides bulk downloads via FTP:
```
ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/
```

However, this requires:
- Filtering for specific PMC IDs
- Large download (TB+ total)
- Not practical for targeted validation

### Option C: Europe PMC API

Europe PMC has more permissive API access:
```python
import requests

def download_from_europepmc(pmc_id):
    url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmc_id}&blobtype=pdf"
    response = requests.get(url, allow_redirects=True)
    if response.headers.get('content-type') == 'application/pdf':
        return response.content
```

---

## Phase 2: Create Minimal Validated Corpus

### Target Composition

| Category | Count | Source |
|----------|-------|--------|
| Cardiovascular HF | 6 | DAPA-HF, EMPEROR, PARADIGM-HF, etc. |
| Cardiology other | 4 | FOURIER, COMPASS, etc. |
| Oncology | 6 | KEYNOTE-024, CLEOPATRA, etc. |
| Diabetes | 4 | LEADER, SUSTAIN-6, etc. |
| Infectious | 3 | Vaccine trials |
| Other | 7 | Mixed therapeutic areas |
| **Total** | **30** | |

### Validation Schema

For each downloaded PDF, create annotation:

```json
{
  "pdf_id": "PMC6832437",
  "trial_name": "DAPA-HF",
  "is_primary_rct_result": true,
  "ground_truth": [
    {
      "effect_type": "HR",
      "value": 0.74,
      "ci_lower": 0.65,
      "ci_upper": 0.85,
      "outcome": "CV death or worsening HF",
      "page": 1,
      "section": "abstract"
    }
  ],
  "extraction_validation": {
    "run_date": "2026-02-03",
    "effects_found": 4,
    "true_positives": 2,
    "false_positives": 2,
    "false_negatives": 0
  }
}
```

---

## Phase 3: End-to-End Validation Pipeline

### 3.1 Validation Script

```python
def validate_rct_pdf(pdf_path: Path, annotation: dict) -> ValidationResult:
    """
    1. Parse PDF to text
    2. Run effect extraction
    3. Match against ground truth
    4. Calculate precision/recall
    """
    # Parse
    parser = PDFParser()
    content = parser.parse(str(pdf_path))
    full_text = "\n".join(p.full_text for p in content.pages)

    # Extract
    extractor = EnhancedExtractor()
    extractions = extractor.extract(full_text)

    # Match
    ground_truth = annotation["ground_truth"]
    matches = match_effects(ground_truth, extractions)

    return ValidationResult(
        pdf_id=annotation["pdf_id"],
        recall=matches.recall,
        precision=matches.precision,
        ci_completion=matches.ci_rate,
    )
```

### 3.2 Expected Baseline Metrics

Based on snippet validation (90% recall) and PDF parsing challenges:

| Metric | Snippet-Based | Expected Full PDF | Target |
|--------|---------------|-------------------|--------|
| Recall | 90.3% | ~70-80% | >80% |
| Precision | 36.8%* | ~60-70% | >60% |
| CI Completion | 92.9% | ~80-85% | >85% |

*Precision is low due to ground truth incompleteness

---

## Phase 4: Failure Mode Analysis

### Anticipated Failure Modes

| Failure Type | Description | Mitigation |
|--------------|-------------|------------|
| **Table extraction** | Effects in tables not parsed | Add table-specific patterns |
| **Multi-column** | Text split across columns | Improve text reordering |
| **Figure captions** | Effects in forest plot legends | Caption extraction |
| **Cross-page** | Effect spans page break | Page boundary handling |
| **Header/footer** | Page numbers misinterpreted | Filter page furniture |

### Failure Analysis Protocol

For each false negative:
1. Locate effect in PDF (page, section)
2. Extract raw text around effect
3. Identify why pattern failed
4. Categorize failure type
5. Design pattern fix

---

## Phase 5: Incremental Improvement Cycle

```
Week 1: Download/curate 30 RCT PDFs
        ↓
Week 2: Run baseline extraction, calculate metrics
        ↓
Week 3: Analyze failures, identify top 5 gaps
        ↓
Week 4: Fix patterns, validate improvement
        ↓
Week 5: Expand corpus to 50 PDFs
        ↓
Week 6: Final validation, document limitations
```

---

## Immediate Action Items

### This Week

1. **Manual PDF Download (4 hours)**
   - Download 10 high-priority RCT PDFs manually
   - DAPA-HF, PARADIGM-HF, EMPEROR-Reduced
   - KEYNOTE-024, KEYNOTE-189, CLEOPATRA
   - FOURIER, LEADER, SUSTAIN-6
   - RALES

2. **Create Annotations (2 hours)**
   - Use existing ground truth from external_validation_dataset.py
   - Create annotation JSON for each PDF

3. **Run Validation (1 hour)**
   - Execute full PDF extraction
   - Calculate baseline metrics
   - Identify failure modes

### Success Criteria

| Metric | Baseline | Week 2 Target | Week 6 Target |
|--------|----------|---------------|---------------|
| PDFs in corpus | 0 | 10 | 30 |
| Recall | Unknown | >70% | >80% |
| CI Completion | Unknown | >75% | >85% |

---

## Alternative: Use Existing Snippet Validation

If PDF acquisition is blocked, continue with snippet-based validation but:

1. **Acknowledge limitation** in all documentation
2. **Report as "pattern accuracy"** not "full extraction accuracy"
3. **Add caveat**: "Full PDF extraction may have lower performance due to parsing challenges"

This is methodologically honest and still valuable for pattern development.
