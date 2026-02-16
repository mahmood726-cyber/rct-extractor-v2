# Batch R14 - Manual Gold Standard Extraction

**Date:** 2026-02-14
**Extractor:** Human expert (manual extraction)
**Batch Size:** 15 studies
**Status:** COMPLETE

## Files Created

### Input
- `clean_batch_r14.json` (103 KB) - Input batch with 15 studies from "no_extraction" and "extracted_no_match" categories

### Output
- `clean_results_r14.json` (11 KB) - **Manual gold standard extractions** for all 15 studies
- `extract_r14.py` (17 KB) - Python script with extraction logic (for documentation/reproducibility)

### Documentation
- `EXTRACTION_SUMMARY_R14.md` (6.4 KB) - Detailed summary of findings, data quality notes, extraction challenges
- `COMPARISON_R14.md` (6.8 KB) - Comparison of automated extractions vs. manual gold standard
- `README_r14.md` (this file)

## Extraction Results

### Summary Statistics
- **Total studies:** 15
- **Found data:** 8 (53.3%)
- **No data found:** 7 (46.7%)
- **Effect type:** All MD (Mean Difference) when found

### Studies with Complete Data (Point Estimate + 95% CI)
1. Krieger 2009 - Quality of life: MD=0.22 (0.00, 0.44)
2. Rapson 2022 - Vegetable intake: MD=11.83 g (0.82, 22.84)
3. Kristiansen 2019 - Vegetable intake: MD=13.3 g/day (-0.2, 26.9)
4. Tovar 2023 - HEI fruit score: MD=2.14 (0.17, 1.48) *CI may be questionable*
5. Martinez-Andrade 2014 - Vegetable intake: MD=6.3 servings/week (1.8, 10.8)

### Studies with Point Estimate Only
6. Namenek Brouwer 2013 - Vegetable intake: MD=0.43 servings (with raw means+SDs)
7. Leis 2020 - F&V servings: β=0.06 portions
8. Haire-Joshu 2008 - F&V servings: MD=0.35 servings (normal weight children only)

### Studies with No Data
9. Cooke 2011 - Qualitative results only
10. Braga-Pontes 2021 - "Effective" but no numbers
11. Gans 2022 - Results text incomplete
12. Nicklas 2017 - "Significant increase" but no values
13. Alexandrou 2023 - Wrong outcomes reported (treats, drinks, screen time)
14. Fagerlund 2020 - Explicitly "no effect"
15. Sherwood 2015 - Results text about BMI, not F&V

## Comparison with Automated Extraction

### Performance Metrics
- **Precision:** 11.1% (1 correct / 9 automated extractions)
- **Recall:** 12.5% (1 found / 8 true positives)
- **False Positive Rate:** 44.4% (4 false positives / 9 extractions)

### Agreement Categories
- ✓ **Match:** 1 study (Leis 2020: both found MD=0.06)
- ✗ **Mismatch:** 5 studies (wrong values or effect types)
- ⚠ **False Positives:** 4 studies (automated extracted, manual found nothing)
- ★ **False Negatives:** 3 studies (automated missed, manual found data)
- ○ **Both Empty:** 3 studies (neither found data)

### Major Issues Identified
1. **False positives:** Cooke, Nicklas, Alexandrou, Fagerlund (extracted data that doesn't exist)
2. **Sign errors:** Kristiansen (-11.2 vs. +13.3)
3. **Magnitude errors:** Haire-Joshu (0.7 vs. 0.35)
4. **Effect type errors:** Martinez-Andrade (OR vs. MD), Tovar (SMD vs. MD)
5. **Missed patterns:** Change scores, HEI scores, beta coefficients

## Extraction Methodology

All extractions followed strict rules:
1. Only explicitly stated numerical data extracted
2. No calculations or inferences made
3. Exact source quotes recorded for verification
4. Reasoning documented for every decision
5. When outcome data not found in results text, marked `found=false`

## Data Quality Notes

### High Confidence (5 studies)
Studies with complete reporting (point estimate + 95% CI + clear outcome match):
- Krieger 2009, Rapson 2022, Kristiansen 2019, Martinez-Andrade 2014

### Medium Confidence (3 studies)
Studies with point estimate only but reliable source:
- Namenek Brouwer 2013 (change scores with SDs)
- Leis 2020 (beta coefficient)
- Haire-Joshu 2008 (subgroup-specific)

### Caution Required (1 study)
- **Tovar 2023:** CI bounds (0.17, 1.48) seem inconsistent with PE=2.14 - needs verification

### Not Found (7 studies)
Reasons vary: qualitative only, incomplete results text, wrong outcomes, null results

## Use Cases

This gold standard dataset can be used to:

1. **Evaluate extraction algorithms** - Compare automated output against human expert baseline
2. **Train ML models** - Supervised learning with verified labels
3. **Identify pattern gaps** - Find reporting formats not covered by current patterns
4. **Test validation rules** - Check if negative context detection prevents false positives
5. **Benchmark improvements** - Track precision/recall gains across versions

## Recommendations for Extractor Improvement

### Critical Fixes
1. Implement negative context detection ("no effect", "no significant difference")
2. Add outcome field validation (reject extractions from wrong outcomes)
3. Improve sign/direction validation (intervention should increase healthy behaviors)

### Pattern Additions
1. Change score format: "+X (SD) vs. -Y (SD)"
2. HEI score format: "PE = X, 95% CI (...)"
3. Beta coefficient format: "β = X, p = ..."
4. Subgroup format: "MN=X, p=... in [subgroup]"

### Validation Rules
1. Plausibility bounds by outcome type
2. Cross-check extracted outcome matches specified outcome field
3. Reject extractions from qualitative-only results
4. Flag when CI doesn't contain point estimate

## Next Steps

1. Apply lessons learned to improve extraction patterns
2. Re-run automated extraction on this batch with updated code
3. Measure improvement in precision, recall, false positive rate
4. Process additional batches to expand gold standard

---

**Contact:** For questions about this extraction batch, refer to EXTRACTION_SUMMARY_R14.md and COMPARISON_R14.md for detailed analysis.
