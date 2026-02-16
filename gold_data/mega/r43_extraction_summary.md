# RCT Batch r43 Extraction Summary

**Date**: 2026-02-14
**Batch File**: clean_batch_r43.json
**Results File**: clean_results_r43.json

## Overview

- **Total Studies**: 15
- **Data Found**: 4 (26.7%)
- **Data Not Found**: 11 (73.3%)

## Studies with Extracted Data

### 1. Ramirez-Rivera 2021_2021
- **Outcome**: zBMI short-term
- **Effect Type**: MD (Mean Difference)
- **Point Estimate**: -0.11
- **95% CI**: [-0.23, 0.01]
- **Source**: "At 9 weeks, no signiﬁcant differences were found between the intervention and control groups in the change in BMI z-score (−0.11, 95% CI −0.23, 0.01)."

### 2. Topham 2021_2021
- **Outcome**: zBMI long-term
- **Effect Type**: MD (Regression coefficient)
- **Point Estimate**: -2.36
- **95% CI**: Not provided
- **Source**: "FL + FD + PG vs. Control... Obese: Raw BMI (B = −0.05, p = 0.04), BMI-M% (B = −2.36, p = 0.00)"
- **Note**: This is BMI-M% (percent distance from median), not raw zBMI. Represents slope difference over 3 years for obese subgroup.

### 3. Robinson 2010_2010
- **Outcome**: BMI long-term (NOT zBMI)
- **Effect Type**: MD
- **Point Estimate**: 0.04
- **95% CI**: [-0.18, 0.27]
- **Source**: "Changes in BMI did not differ between groups (adjusted mean difference [95% confidence interval] = 0.04 [−.18, .27] kg/m2 per year)."
- **Note**: This is raw BMI in kg/m², not z-score. Units are per year.

### 4. Kuroko 2020_2020
- **Outcome**: zBMI medium term
- **Effect Type**: MD
- **Point Estimate**: 0.08
- **95% CI**: [0.02, 0.14]
- **Source**: "Change at 7 weeks... BMI z-score: 0.08 (0.02, 0.14), p = 0.006"
- **Note**: Positive value indicates intervention group had HIGHER BMI z-score gain (adverse effect).

## Studies with No Extractable Data (11 studies)

### Feasibility Studies (2)
- **O'Connor 2020_2020**: Feasibility study, only reported recruitment/retention rates
- **Sahota 2019_2019**: Feasibility study, only reported knowledge scores and dietary behaviors

### No Specific Values Reported (6)
- **Nyberg 2015_2015**: Only stated "did not affect prevalence of overweight or obesity"
- **Nyberg 2016_2016**: Mentioned p=0.03 for obese subgroup but no mean difference or CI
- **Fulkerson 2022_2022**: Stated "no significant effects" but no specific values
- **Sherwood 2019_2019**: Stated "no overall significant treatment effect" with subgroup p-values only
- **Crespo 2012_2012**: Explicitly stated "no intervention effects" without values
- **HEALTHY Study Group 2010_2010**: Mentioned p=0.04 but no mean difference or CI
- **Williamson 2012_2012**: Stated "found no differences" without specific values

### Wrong Outcome Type (1)
- **Levy 2012_2012**: Results reported OR for obesity, not zBMI means/SD

### Within-Group Values Only (1)
- **Habib-Mourad 2020_2020**: Reported mean changes within each group separately (0.07±0.05 vs 0.145±0.05, p=0.27) but no between-group difference explicitly calculated

## Extraction Methodology

All extractions followed strict rules:
1. **Only explicitly stated data** was extracted
2. **No calculations or inferences** were performed
3. Each entry includes:
   - `source_quote`: Direct text from results
   - `reasoning`: Why data was found or not found
4. Binary and continuous outcome fields left null (all outcomes were direct effects)

## Notes

- Most studies (73%) did not provide extractable numerical outcome data in the results text
- Common issue: p-values reported without effect sizes or confidence intervals
- Some studies reported "no significant difference" without providing the actual values
- One study (Kuroko) showed an adverse intervention effect (increased BMI z-score)
- Outcome measures varied: zBMI, BMI-M%, raw BMI in kg/m²
