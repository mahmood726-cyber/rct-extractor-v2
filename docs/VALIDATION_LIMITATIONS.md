# RCT Extractor v4.3.1 - Validation Limitations and Caveats

## Corpus Composition Limitations

### Effect Type Imbalance
The current validation corpus is heavily weighted toward hazard ratios:

| Effect Type | Count | Percentage | Interpretation |
|-------------|-------|------------|----------------|
| HR | 50 | 80.6% | Well-validated |
| RR | 8 | 12.9% | Moderately validated |
| MD | 3 | 4.8% | Preliminary only |
| OR | 1 | 1.6% | Insufficient for claims |

**Implication**: Recall and CI completion metrics are primarily reflective of HR extraction performance. Metrics for OR, MD, and RR should be considered preliminary estimates with wide uncertainty bounds.

### Journal Concentration
| Journal | Count | Percentage |
|---------|-------|------------|
| NEJM | 44 | 89.8% |
| Lancet | 3 | 6.1% |
| Other | 2 | 4.1% |

**Implication**: Performance on non-NEJM journals (different formatting conventions, reporting styles) is not well characterized. NEJM's standardized reporting may inflate apparent accuracy.

### Temporal Distribution
- 78% of trials from 2014-2023
- Limited coverage of older reporting formats (pre-2010)
- No trials from 2024-2026

### Therapeutic Area Coverage
Cardiovascular/metabolic trials dominate (>60%). Limited representation of:
- Psychiatry (n=1)
- Infectious disease (n=1)
- Rare diseases (n=0)
- Pediatric trials (n=0)

---

## Inter-Rater Reliability Clarification

### Current Status: Single Extraction with Verification

The reported 100% inter-rater agreement reflects the **data structure** rather than independent dual extraction:

1. `extractor_a` contains the primary manual extraction
2. `extractor_b` contains verification/confirmation extraction
3. `consensus` is derived when both agree

This is methodologically equivalent to **single extraction with verification**, not true dual independent extraction with adjudication.

### Correct Interpretation
- The dataset demonstrates internal consistency
- It does NOT demonstrate inter-rater reliability in the traditional sense
- Cohen's kappa of 1.0 should be interpreted as "verification confirmed primary extraction" not "independent extractors achieved perfect agreement"

### Future Work
True inter-rater reliability requires:
- Blinded independent extraction by 2+ extractors
- Disagreement resolution protocol
- Reporting of pre-adjudication agreement rates

---

## Precision Measurement Caveats

### "Extra" Extractions Analysis

The 96 "extra" extractions on positive controls include:

| Category | Estimated % | Description |
|----------|-------------|-------------|
| Secondary endpoints | ~60% | Valid effects not in ground truth |
| Subgroup analyses | ~20% | Reported but not primary |
| Sensitivity analyses | ~10% | Alternative analysis methods |
| True false positives | ~10% | Actual extraction errors |

**Implication**: Combined precision of 35.9% substantially underestimates true precision because ground truth is incomplete.

### Recommended Interpretation
- **Negative control FP rate (13.3%)** is the better precision proxy
- Combined precision reflects "primary endpoint capture rate" not error rate
- For systematic review use: expect 2-3x extractions vs expected primary effects

---

## Validation Scope Limitations

### Currently Validated
- Pre-selected text snippets (100-500 characters)
- Clean, well-formatted text
- English language only
- Standard effect reporting formats

### NOT Validated
- Full PDF text extraction pipeline
- OCR-degraded text
- Table-embedded effects
- Non-English trials
- Supplementary materials
- Multi-arm trial reporting
- Network meta-analysis inputs

---

## Recommended Use Cases

### Appropriate Uses
1. Initial screening of English-language RCT abstracts
2. Extraction from NEJM/Lancet/JAMA publications
3. HR-focused cardiovascular/oncology reviews
4. Rapid evidence mapping

### Use with Caution
1. OR-heavy datasets (psychiatry, case-control)
2. MD-focused outcomes (continuous endpoints)
3. Non-English publications
4. Older trials (pre-2010)

### Not Recommended Without Additional Validation
1. Regulatory submissions
2. Health technology assessments
3. Cochrane reviews (require manual verification)
4. Legal/forensic applications
