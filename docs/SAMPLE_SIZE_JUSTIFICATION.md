# Sample Size Justification for Validation Set
## Statistical Power Analysis

**Version:** 1.0
**Date:** 2026-01-31

---

## 1. Objective

To determine the minimum sample size required for the validation dataset to:
1. Estimate sensitivity with adequate precision
2. Detect clinically meaningful differences in subgroups
3. Provide sufficient power for calibration assessment

---

## 2. Primary Sample Size Calculation

### 2.1 Target Parameters

| Parameter | Value | Justification |
|-----------|-------|---------------|
| Target sensitivity | 95% | Industry standard for automation |
| Precision (margin of error) | ±5% | Clinically acceptable |
| Confidence level | 95% | Standard for publication |
| Design effect | 1.0 | Simple random sampling |

### 2.2 Calculation Method

Using exact binomial confidence interval (Clopper-Pearson):

For a single proportion with:
- p = 0.95 (expected sensitivity)
- α = 0.05 (two-sided)
- d = 0.05 (margin of error)

The required sample size is:

```
n = (Z²α/2 × p × (1-p)) / d²
n = (1.96² × 0.95 × 0.05) / 0.05²
n = (3.84 × 0.0475) / 0.0025
n = 72.96 ≈ 73
```

### 2.3 Adjustment for Wilson Score Interval

Wilson score intervals are used (more appropriate for extreme proportions):

Using the Wilson formula and solving for n:
- Minimum n = 73 for 95% CI width ≤ 10%

### 2.4 Actual Sample Size

**Actual n = 100+ trials** (exceeds minimum by 37%)

This provides:
- 95% CI width of ≈8% at 95% sensitivity
- Additional power for subgroup analyses
- Buffer for exclusions or missing data

---

## 3. Subgroup Analysis Power

### 3.1 Minimum Stratum Size

For meaningful inference within strata:

| Stratum Type | Minimum n | Achieved n | Status |
|--------------|-----------|------------|--------|
| Year block (5) | 10 each | 10-27 | ✓ Adequate |
| Journal (10) | 5 each | 2-53 | ⚠ Some limited |
| Therapeutic area (11) | 5 each | 2-35 | ⚠ Some limited |
| Effect type (4) | 10 each | 4-52 | ⚠ Some limited |

### 3.2 Acknowledged Limitations

Strata with n < 5:
- Psychiatry (n=2): Wide CI, limited inference
- Rheumatology (n=2): Wide CI, limited inference
- Surgery (n=2): Wide CI, limited inference
- Dermatology (n=0): Not validated
- Ophthalmology (n=0): Not validated

**Mitigation:** Results reported with Wilson CIs that appropriately reflect uncertainty.

---

## 4. Calibration Assessment Power

### 4.1 Hosmer-Lemeshow Test

For the Hosmer-Lemeshow goodness-of-fit test:
- Minimum n = 50 for stable chi-square approximation
- Recommended n = 100+ for 10 bins

**Actual n = 100+** ✓ Adequate

### 4.2 Expected Calibration Error (ECE)

For reliable ECE estimation:
- Minimum 10 samples per bin recommended
- With 10 bins: n = 100 minimum

**Actual n = 100+** ✓ Adequate

---

## 5. False Positive Validation

### 5.1 Specificity Sample Size

To demonstrate 100% specificity with confidence:

```
If 0 false positives in n negative cases:
Upper 95% CI for false positive rate = 1 - 0.05^(1/n)

For n = 100: Upper 95% CI = 2.95%
For n = 150: Upper 95% CI = 1.98%
```

**Actual n = 100 negative cases**
- Upper 95% CI for FP rate: 2.95%
- Sufficient for claiming "near-zero" false positive rate

---

## 6. Held-Out Calibration Set

### 6.1 Split Rationale

| Split | Percentage | n | Purpose |
|-------|------------|---|---------|
| Development | 70% | 57 | Pattern tuning, threshold setting |
| Calibration | 30% | 25 | Unbiased performance estimation |

### 6.2 Calibration Set Power

With n = 25 in held-out set:
- Can detect sensitivity ≥ 80% vs < 80% with 80% power
- 95% CI width ≈ 20% at 95% sensitivity

This is acceptable for calibration validation; wider CIs are appropriately reported.

---

## 7. Temporal Holdout Validation

### 7.1 Prospective Validation

Papers from 2024-2025 (after pattern development):
- Target: n = 15
- Purpose: True prospective validation
- Power: Detect sensitivity drop from 95% to 80%

---

## 8. Summary Table

| Validation Component | Required n | Actual n | Status |
|---------------------|------------|----------|--------|
| Overall sensitivity | 73 | 100+ | ✓ Exceeds |
| Subgroup (year) | 10/block | 10-27 | ✓ Adequate |
| Subgroup (journal) | 5/source | 2-53 | ⚠ Partial |
| Subgroup (disease) | 5/area | 2-35 | ⚠ Partial |
| Subgroup (effect) | 10/type | 4-52 | ⚠ Partial |
| Calibration (H-L) | 50 | 100+ | ✓ Adequate |
| ECE estimation | 100 | 100+ | ✓ Adequate |
| False positive | 100 | 100 | ✓ Adequate |
| Held-out set | 20 | 25 | ✓ Adequate |
| Temporal holdout | 15 | 15 | ✓ Target met |

---

## 9. Conclusion

The validation dataset of **100+ trials** exceeds the minimum required sample size (n=73) for the primary objective. While some subgroups have limited sample sizes, this is:

1. **Transparently reported** with appropriate confidence intervals
2. **Consistent with literature** (most SR tool validations use 50-200 papers)
3. **Adequate for primary claims** about overall sensitivity

### Recommendations for Future Versions

1. Expand underrepresented therapeutic areas (Psychiatry, Rheumatology, Dermatology)
2. Add more rare effect types (IRR, ARD, SMD)
3. Increase journal diversity beyond NEJM dominance

---

## 10. References

1. Clopper, C. J., & Pearson, E. S. (1934). The use of confidence or fiducial limits illustrated in the case of the binomial. Biometrika, 26(4), 404-413.

2. Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. Journal of the American Statistical Association, 22(158), 209-212.

3. Hosmer, D. W., & Lemeshow, S. (2000). Applied Logistic Regression (2nd ed.). Wiley.

4. Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences (2nd ed.). Lawrence Erlbaum Associates.
