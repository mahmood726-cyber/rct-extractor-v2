# RCT Extractor v4.3.3 - PDF Validation Improvements

**Date:** 2026-02-03
**Final Update:** Extended validation with 58 PDFs

## Summary

This update focused on improving extraction from real RCT result PDFs, expanding the validation corpus, and fixing pattern gaps discovered during full PDF validation.

---

## Validation Corpus Expansion

| Metric | Initial | Final |
|--------|---------|-------|
| PDF corpus size | 17 | **58** |
| Total extractions | 63 | **182** |
| Effect type coverage | HR-dominated | HR/OR/RR/MD/RRR/SMD/IRR/ARD |

### Effect Type Distribution (58 PDFs, 182 extractions)
| Type | Count | Percentage |
|------|-------|------------|
| HR | 73 | 40.1% |
| OR | 32 | 17.6% |
| RR | 30 | 16.5% |
| MD | 27 | 14.8% |
| RRR | 10 | 5.5% |
| SMD | 7 | 3.8% |
| IRR | 2 | 1.1% |
| ARD | 1 | 0.5% |

---

## Pattern Improvements

### 1. NEJM [CI] Bracket Format
Added patterns for NEJM-style reporting used in LEADER trial and similar:
```
hazard ratio, 0.87; 95% confidence interval [CI], 0.78 to 0.97
```

### 2. Equals Sign with CI Formats
Added patterns for:
```
HR=0.97; 0.80, 1.17    (semicolon then CI without label)
HR=0.89 [0.80-0.99]    (equals + square brackets)
HR = 0.8 (0.7-0.9)     (spaced equals)
HR=0.78, 95% CI 0.47-1.28  (comma before CI)
```

Same patterns added for OR and RR.

### 3. Line Break Normalization
Added text normalization to handle PDF line breaks:
- `HR\n= 0.8` → `HR = 0.8`
- `mean difference\n3.1` → `mean difference 3.1`
- `,\n95% CI` → `, 95% CI`

---

## Metrics

### Snippet-Based Validation (49 trials)
| Metric | v4.3.2 | v4.3.3 | Change |
|--------|--------|--------|--------|
| Recall | 90.3% | **91.9%** | +1.6% |
| CI Completion | 92.9% | **93.0%** | +0.1% |
| Tests Passing | 33/33 | 33/33 | - |

### Full PDF Validation (58 PDFs)
| Metric | Initial | Final | Target | Status |
|--------|---------|-------|--------|--------|
| Parse success | 100% | 100% | >95% | ✅ |
| Extraction rate | 82.4% | **74.1%** | >70% | ✅ |
| CI completion | 71.4% | **63.7%** | >80% | ⚠️ |
| Total extractions | 63 | **182** | - | +189% |

Note: Extraction rate decreased as corpus expanded to include more diverse papers (some non-RCT). CI completion is lower on full PDFs due to table/multi-column layout issues.

---

## Known Limitations

### Full PDF CI Completion (60.2% vs 93% snippet)
The gap is due to:
1. **Multi-column layouts**: CIs appear in different text columns than effect values
2. **Table formatting**: Effect values and CIs in separate table cells
3. **Figure captions**: Forest plot CIs not in main text flow
4. **Value-only reporting**: Some PDFs report effects without CIs

### Zero-Extraction PDFs (10/38)
- Methods/review papers incorrectly included in search
- Papers reporting effects without standard patterns
- Papers using only p-values without CIs

---

## Files Modified

### Pattern Improvements
- `src/core/enhanced_extractor_v3.py`:
  - Added NEJM [CI] bracket patterns
  - Added HR/OR/RR=X; CI format patterns
  - Added line break normalization

### Validation Scripts
- `scripts/download_more_rcts.py`: Download additional OA RCTs
- `scripts/analyze_pdf_failures.py`: Investigate extraction failures
- `scripts/find_open_access_rcts.py`: Search for OA papers

### Output
- `output/expanded_rct_validation_v4.json`: Full validation results
- `test_pdfs/open_access_rcts/`: 38 validated RCT PDFs

---

## Recommendations for Further Improvement

1. **Table-specific extraction**: Add special handling for effect values in tables
2. **Multi-column reordering**: Improve PDF parser to handle column layouts
3. **CI proximity search**: When value found without CI, search wider context
4. **Corpus quality**: Manual review to filter non-RCT papers

---

## Verification

All 33 extraction accuracy tests pass:
```
============================= 33 passed in 33.67s =============================
```
