<!-- sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files. -->

# Extraction Notes for Batch R40

## Overview
Manual extraction of numerical outcome data from `clean_batch_r40.json` completed on 2026-02-14.

**Input:** `clean_batch_r40.json` (15 study entries)
**Output:** `clean_results_r40.json` (15 extraction results)
**Extraction Script:** `extract_r40.py`

## Summary Statistics
- **Total entries:** 15
- **Found (extracted data):** 5 (33.3%)
- **Not found (no data):** 10 (66.7%)

## Entries with Extracted Data

### 1. Gato-Moreno 2021_2021
- **Outcome:** zBMI (Medium Term)
- **Effect type:** MD (continuous)
- **Data extracted:**
  - Intervention: mean=0.14, sd=1.05, n=115
  - Control: mean=0.17, sd=1.03, n=132
- **Source:** Table 2, 2nd year follow-up (medium term)
- **Notes:** Final zBMI values at 2-year follow-up

### 2. Stookey 2017_2017
- **Outcome:** zBMI (Medium Term)
- **Effect type:** MD (mean difference)
- **Data extracted:** MD = -0.08 (SE=0.03)
- **Source:** Results text reporting group comparison
- **Notes:** This is the DIFFERENCE between groups, not raw group values

### 3. Cunha 2013_2013
- **Outcome:** BMI medium-term
- **Effect type:** MD (regression coefficient)
- **Data extracted:** b = 0.003 (p=0.75)
- **Source:** ITT analysis regression result
- **Notes:** Essentially zero difference (null result)

### 4. Stettler 2015_2015
- **Outcome:** BMI medium-term
- **Effect type:** MD (BMIz change difference)
- **Data extracted:**
  - MD = -0.089
  - 95% CI: [-0.170, -0.008]
  - n=139 (combined intervention), n=33 (control)
- **Source:** Results comparing combined intervention vs control
- **Notes:** Outcome labeled "BMI medium-term" but data is BMIz. Using as reported.

### 5. Ickovics 2019_2019
- **Outcome:** Percentile long-term
- **Effect type:** MD (regression coefficient)
- **Data extracted:** β = -2.40 (p=0.04)
- **Source:** 3-year follow-up nutrition intervention results
- **Notes:** BMI percentile difference at 3 years

## Entries with No Data (found=false)

### Reasons for No Data:

**Study protocols (no results yet):**
- Hammersley 2021_2021 - protocol/registration only

**Different outcomes reported:**
- Ostbye 2012_2012 - only maternal feeding practices, no child zBMI
- Coleman 2012_2012 - obesity prevalence % only, no zBMI means/SDs
- Tomayko 2016_2016 - BMI percentile only, not absolute BMI

**Null results without numerical data:**
- Morshed 2018_2018 - states "no effect" but no numerical values
- Morgan 2022_2022 - states "no effects" (text appears cut off)
- Tomayko 2019_2019 - states "no changes" without values
- Hawkins 2019_2019 - directional statement only, no values
- Nicholl 2021_2021 - states "no differential changes" without values
- Davis 2021_2021 - states "no effects" without values

## Extraction Principles Applied

1. **Only explicitly stated data** - No calculations or inferences
2. **Outcome-specific** - Matched extraction to stated outcome field
3. **Source quotes** - Every extraction includes verbatim quote
4. **Clear reasoning** - All decisions documented
5. **Null handling** - Proper use of `null` for missing fields, not zero

## Data Types Observed

- **Continuous outcomes:** Raw means/SDs (1 entry)
- **Mean differences:** Direct MD or regression coefficients (4 entries)
- **Confidence intervals:** Only 1 entry had full CI

## Notes on Effect Type Coding

All extracted effects coded as "MD" (mean difference) since all outcomes were continuous (BMI, zBMI, BMI percentile). This includes:
- Raw group means (can compute MD)
- Direct mean difference reported
- Regression coefficients (β or b)

## File Locations

- Input: `C:\Users\user\rct-extractor-v2\gold_data\mega\clean_batch_r40.json`
- Output: `C:\Users\user\rct-extractor-v2\gold_data\mega\clean_results_r40.json`
- Script: `C:\Users\user\rct-extractor-v2\gold_data\mega\extract_r40.py`
- Notes: `C:\Users\user\rct-extractor-v2\gold_data\mega\EXTRACTION_NOTES_r40.md`
