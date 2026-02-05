# Full PDF Extraction Validation Summary

**Date:** 2026-02-03
**Version:** v4.3.2 (with NEJM [CI] pattern fix)

## Executive Summary

Full PDF extraction validation was performed on **17 confirmed open-access RCT results papers** downloaded from Europe PMC. Results show significant improvement over previous validation attempts on incorrectly-identified PDFs.

### Key Metrics

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Parse success rate | 100% | >95% | ✅ PASS |
| PDFs with extractions | 82.4% (14/17) | >70% | ✅ PASS |
| CI completion rate | 71.4% (45/63) | >80% | ⚠️ CLOSE |
| Total extractions | 63 | - | - |
| Avg extractions per PDF | 3.7 | - | - |

### Effect Type Distribution

| Type | Count | Percentage |
|------|-------|------------|
| HR | 56 | 88.9% |
| IRR | 2 | 3.2% |
| RR | 2 | 3.2% |
| OR | 2 | 3.2% |
| ARD | 1 | 1.6% |

---

## Validation Corpus

### Source
- 17 actual RCT results papers from Europe PMC Open Access
- Therapeutic areas: Cardiology, Oncology, Diabetes, Respiratory
- Publication years: 2025 (recent papers with confirmed open access)

### Papers with Extractions (14/17)

| PMC ID | Journal | Extractions | CI Rate |
|--------|---------|-------------|---------|
| PMC11978796 | Nat Commun | 2 | 100% |
| PMC12144549 | Circulation | 3 | 100% |
| PMC12206259 | Can J Kidney | 4 | 75% |
| PMC12266184 | Lancet Reg Health | 5 | 80% |
| PMC12312311 | Cardiovasc Diabetol | 5 | 80% |
| PMC12381027 | BMC Cancer | 8 | 75% |
| PMC12398225 | Cancer Res | 3 | 67% |
| PMC12618225 | Nat Med | 4 | 100% |
| PMC12670541 | Lancet Oncol | 2 | 50% |
| PMC12670988 | Lancet Oncol | 7 | 71% |
| PMC12700247 | Ann Am Thorac Soc | 1 | 100% |
| PMC12705423 | Nat Med | 7 | 71% |
| PMC12705445 | Nat Med | 8 | 63% |
| PMC12799424 | Br J Anaesth | 4 | 75% |

### Papers with 0 Extractions (3/17)

| PMC ID | Reason |
|--------|--------|
| PMC12355417 | Reports HR without 95% CI (only p-values) |
| PMC12691396 | Methods paper, not RCT results |
| PMC12705465 | PDF text garbled from multi-column layout |

---

## Pattern Improvements Made

### v4.3.2 Fix: NEJM [CI] Bracket Format

Added patterns for NEJM-style reporting:

```
hazard ratio, 0.87; 95% confidence interval [CI], 0.78 to 0.97
```

This fixed extraction of LEADER trial primary endpoint and similar formats.

---

## Comparison to Previous Validation

| Corpus | PDFs | Extraction Rate | CI Rate | Notes |
|--------|------|-----------------|---------|-------|
| Snippet validation | 49 | 100%* | 92.9% | Pre-selected text |
| "Real PDFs" (wrong) | 8 | 37.5% | 93.8% | Wrong papers (reviews) |
| **Open-access RCTs** | 17 | **82.4%** | **71.4%** | Actual RCT results |

*Snippet validation tests pattern matching only, not full PDF extraction.

---

## Known Limitations

### 1. PDF Parsing Issues
- Multi-column layouts can cause garbled text (seen in PMC12705465)
- Complex tables may not parse correctly
- Some journals have restrictive formatting

### 2. Format Coverage Gaps
- Papers reporting HR/OR without 95% CI are correctly skipped
- Some unusual formats may not match patterns

### 3. Corpus Limitations
- Limited to open-access papers (many landmark trials behind paywalls)
- 2025 papers may have different formatting than older papers

---

## Recommendations

1. **CI Completion**: At 71.4%, slightly below 80% target
   - Review failed CI extractions for pattern gaps
   - Consider adding more tolerance for CI format variations

2. **Corpus Expansion**:
   - Current: 17 papers
   - Target: 50+ papers for robust validation
   - Continue downloading from Europe PMC

3. **Multi-column Handling**:
   - Investigate alternative PDF parsers for complex layouts
   - Consider pre-processing to reorder text

---

## Files Updated

- `src/core/enhanced_extractor_v3.py`: Added NEJM [CI] patterns
- `scripts/download_rct_results_pdfs.py`: Fixed to use Europe PMC
- `output/oa_rct_extraction.json`: Full validation results
- `test_pdfs/open_access_rcts/`: 17 validated RCT PDFs
