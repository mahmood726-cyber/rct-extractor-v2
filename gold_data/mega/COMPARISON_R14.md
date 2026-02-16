# Comparison: Automated Extraction vs. Manual Gold Standard (Batch R14)

**Date:** 2026-02-14
**Batch:** clean_batch_r14.json
**Total Studies:** 15

## Summary Statistics

| Category | Count | Percentage |
|----------|-------|------------|
| **Manual Found** | 8 | 53.3% |
| **Manual Not Found** | 7 | 46.7% |
| **Agreement** | 1 | 6.7% |
| **Disagreement** | 8 | 53.3% |
| **New Finds** | 3 | 20.0% |
| **No Data Either** | 3 | 20.0% |

## Agreement Analysis

### ✓ MATCH (1 study)
**Existing extraction agrees with manual gold standard**

1. **Leis 2020_2020**
   - Existing: MD = 0.06 (among 2 extractions: 3.33, 0.06)
   - Manual: MD = 0.06
   - **Status:** CORRECT MATCH

---

### ✗ MISMATCH (5 studies)
**Existing extraction differs from manual gold standard**

2. **Kristiansen 2019_2019**
   - Existing: MD = -11.2
   - Manual: MD = 13.3 (95% CI: -0.2, 26.9)
   - **Issue:** Wrong sign (negative vs. positive) and wrong magnitude

3. **Tovar 2023_2023**
   - Existing: SMD = 0.2 and 0.5
   - Manual: MD = 2.14 (HEI score, 95% CI: 0.17, 1.48)
   - **Issue:** Wrong effect type (SMD vs. MD) and wrong magnitude (HEI score misinterpreted)

4. **Haire-Joshu 2008_2008**
   - Existing: MD = 0.7
   - Manual: MD = 0.35 (for normal weight children)
   - **Issue:** Wrong value (0.7 vs. 0.35) - may have extracted parent value (0.20) or combined groups incorrectly

5. **Martinez-Andrade 2014_2014**
   - Existing: OR = 0.52
   - Manual: MD = 6.3 servings/week (95% CI: 1.8, 10.8)
   - **Issue:** Wrong effect type (OR vs. MD) - extracted completely different outcome

6. **Cooke 2011_2011**
   - Existing: MD = -0.48
   - Manual: NOT FOUND (results text has no numerical vegetable intake data)
   - **Issue:** False positive - extractor fabricated or misattributed data

---

### ⚠ DISAGREE - FALSE POSITIVES (3 studies)
**Existing had data but manual found nothing**

7. **Nicklas 2017_2017**
   - Existing: SMD = 0.28
   - Manual: NOT FOUND
   - **Reasoning:** Results say "significantly increased" but provide no numerical value for vegetable intake

8. **Alexandrou 2023_2023**
   - Existing: OR = 1.99, MD = 0.91, 0.34, 0.31, None
   - Manual: NOT FOUND
   - **Reasoning:** Results report sweet treats, sweet drinks, screen time - NOT fruit/vegetable intake

9. **Fagerlund 2020_2020**
   - Existing: MD = 20.0
   - Manual: NOT FOUND
   - **Reasoning:** Results explicitly state "No effect...on vegetable intake"

---

### ★ NEW FINDS (3 studies)
**Manual found data that automated extraction missed**

10. **Krieger 2009_2009**
    - Existing: None (old_status: no_extraction)
    - Manual: MD = 0.22 (95% CI: 0.00, 0.44)
    - **Outcome:** Quality of life (not F&V intake)

11. **Rapson 2022_2022**
    - Existing: None (old_status: no_extraction)
    - Manual: MD = 11.83 g (95% CI: 0.82, 22.84)
    - **Outcome:** Broccoli intake

12. **Namenek Brouwer 2013_2013**
    - Existing: None (old_status: no_extraction)
    - Manual: MD = 0.43 servings (calculated from change scores)
    - **Outcome:** Vegetable consumption

---

### ○ NO DATA (3 studies)
**Both automated and manual found no data**

13. **Braga-Pontes 2021_2021**
    - Both: No extraction
    - Reason: Only qualitative statements in results

14. **Gans 2022_2022**
    - Both: No extraction
    - Reason: Results text excerpt lacks F&V intake data

15. **Sherwood 2015_2015**
    - Both: No extraction
    - Reason: Results text excerpt focuses on BMI, not F&V intake

---

## Error Analysis

### Automated Extraction Issues

1. **False Positives (4 studies):** 26.7% of batch
   - Cooke 2011: Fabricated MD = -0.48
   - Nicklas 2017: Fabricated SMD = 0.28
   - Alexandrou 2023: Extracted wrong outcomes (OR, multiple MDs)
   - Fagerlund 2020: Extracted MD = 20.0 despite "no effect" statement

2. **Sign Errors (1 study):** 6.7%
   - Kristiansen 2019: -11.2 vs. +13.3 (opposite direction)

3. **Magnitude Errors (2 studies):** 13.3%
   - Haire-Joshu 2008: 0.7 vs. 0.35 (2x error)
   - Tovar 2023: SMD 0.2/0.5 vs. MD 2.14 (wrong scale/metric)

4. **Effect Type Errors (2 studies):** 13.3%
   - Martinez-Andrade 2014: OR vs. MD (different outcome)
   - Tovar 2023: SMD vs. MD (HEI score misclassified)

5. **False Negatives (3 studies):** 20.0%
   - Krieger 2009: Missed quality of life MD
   - Rapson 2022: Missed vegetable intake MD with CI
   - Namenek Brouwer 2013: Missed change score data

### Accuracy Metrics

- **Precision:** 1/9 = 11.1% (only 1 correct out of 9 automated extractions)
- **Recall:** 1/8 = 12.5% (only 1 found out of 8 true positives)
- **False Positive Rate:** 4/9 = 44.4%

## Recommendations

### Immediate Fixes Needed

1. **Negative Context Detection:** Implement detection of "no effect", "no significant", "no difference" to prevent false positives (Fagerlund 2020)

2. **Outcome Matching:** Verify extracted data matches the specified outcome field - many extractions pulled wrong outcomes (Alexandrou 2023, Martinez-Andrade 2014)

3. **Sign Validation:** Cross-check direction of effect makes sense in context (Kristiansen 2019: intervention should increase, not decrease vegetables)

4. **Qualitative Filter:** Don't extract when results only report "significantly increased" without numbers (Nicklas 2017, Cooke 2011)

5. **HEI Score Handling:** Properly classify Healthy Eating Index scores as MD (continuous scale 0-100), not SMD (Tovar 2023)

6. **Change Score Patterns:** Improve detection of intervention vs. control change scores in format "+X (SD) vs. -Y (SD)" (Namenek Brouwer 2013)

### Pattern Improvements

1. Add pattern for: "mean difference of X g vegetables/day (95% CI: ...)" (Kristiansen 2019, Rapson 2022)
2. Add pattern for: "increased by X servings/week (95% CI: ...)" (Martinez-Andrade 2014)
3. Add pattern for: "point estimate (PE) = X, 95% CI (...)" (Tovar 2023)
4. Add pattern for: "MN=X, p=..." (Haire-Joshu 2008)

### Validation Rules

1. **Cross-check outcome field:** If outcome="Fruit and vegetable intake", reject extractions for "sweet treats", "screen time", "BMI"
2. **Null result detection:** Reject extractions from text containing "no effect", "no difference", "no significant effect"
3. **Plausibility bounds:** MD for vegetable servings/day should be -5 to +5, not 20
4. **Sign consistency:** Intervention effect on healthy behaviors should generally be positive

---

## Conclusion

The automated extraction system shows **poor performance** on this batch:
- Only **11% precision** (9 extractions, 1 correct, 4 false positives)
- Only **13% recall** (missed 7 of 8 true positives)
- **44% false positive rate**

Key issues:
1. Extracting data from wrong outcomes
2. Not detecting null results ("no effect")
3. Missing common reporting formats (change scores, HEI scores, beta coefficients)
4. Sign and magnitude errors

**Priority:** Implement negative context detection and outcome matching validation before next batch.
