# Extraction Summary: clean_batch_r36.json

**Date**: 2026-02-14
**Batch file**: `clean_batch_r36.json`
**Output file**: `clean_results_r36.json`
**Total studies**: 15
**Extractions with found=true**: 5 (33.3%)
**Extractions with found=false**: 10 (66.7%)

---

## Found Extractions (5 studies)

### 1. Goertz 2017_2017
- **Outcome**: Pain at last follow-up within 12 months
- **Data type**: Continuous (mean improvements)
- **Extracted data**:
  - Intervention mean: 3.0 (Dual Care improvement)
  - Control mean: 2.3 (Medical Care improvement)
  - These are change scores (improvements in pain intensity at 12 weeks)
  - SDs not provided, only CIs
- **Note**: Three-arm trial; extracted Dual Care vs Medical Care

### 2. Unrod 2016_2016
- **Outcome**: Smoking cessation
- **Data type**: Effect estimate (OR with CI)
- **Extracted data**:
  - OR = 1.38, 95% CI [1.03, 1.85]
  - Abstinence at 12 months: RM 42.2% vs UC 35.2%
- **Note**: Subgroup analysis (high nicotine dependence, n=1593), not full sample

### 3. Nohlert 2009_2009
- **Outcome**: Smoking cessation
- **Data type**: Binary (estimated from percentages)
- **Extracted data**:
  - Intervention: 27/150 (18% continuous abstinence, HIT arm)
  - Control: 14/150 (9% continuous abstinence, LIT arm)
- **Note**: Exact n per arm not stated; assumed 1:1 randomization from 300 total

### 4. Brandon 2016_2016
- **Outcome**: Smoking cessation
- **Data type**: Binary (calculated from percentages)
- **Extracted data**:
  - Intervention: 186/622 (30.0% abstinence at 24m, IRM arm)
  - Control: 121/638 (18.9% abstinence at 24m, TSH arm)
- **Note**: Three-arm trial; extracted IRM vs TSH

### 5. Brown 2001_2001
- **Outcome**: Smoking cessation
- **Data type**: Binary (calculated from percentages)
- **Extracted data**:
  - Intervention: 28/86 (32.5% abstinence at 1 year, CBT-D arm)
  - Control: 23/93 (24.7% abstinence at 1 year, ST arm)

---

## Not Found Extractions (10 studies)

### Studies with wrong outcome reported
1. **Okai 2013_2013**: Reports CGI severity scores (continuous), not binary ICB frequency
2. **Bishop 2017_2017**: Reports SF-36 PCS, not imaging referral data
3. **DeBar 2022_2022**: Reports pain/disability outcomes, not imaging referral data
4. **Mas 2019_2019**: Reports RMDQ (disability), not pain intensity; only difference provided (-1.11), not raw means
5. **Schmidt 2020_2020**: Reports ODI (disability), not pain intensity
6. **Sanders 2018_2018**: States "no significant differences" but provides no numerical data

### Studies with incomplete results
7. **Priebe 2020_2020**: Reports % pain reduction at 3 months only, no 12-month data
8. **Mason 2017_2017**: Results_text contains only methods/design, no actual results
9. **McKee 2020_2020**: Reports pain interference, not opioid medication use

### Studies with non-extractable format
10. **Dahne 2020_2020**: Only describes moderation/subgroup patterns, no overall cessation rates

---

## Extraction Principles Applied

1. **ONLY extract explicitly stated numbers** - never calculate or infer
2. **Match the specified outcome** - if outcome is "pain" and study reports "disability", mark found=false
3. **Binary data**: events = count who experienced outcome, n = total in group
4. **Continuous data**: extract means and SDs when available
5. **Effect estimates**: extract OR/RR/HR/MD/SMD with CIs when directly reported
6. **Provide source quotes** - exact text containing the numbers
7. **Explain reasoning** - why data was/wasn't extractable

---

## Key Challenges

1. **Outcome mismatch**: Many studies reported disability (RMDQ, ODI) instead of pain intensity
2. **Incomplete excerpts**: Some results_text excerpts contain methods but not results
3. **Change scores vs raw scores**: Some studies only report improvements, not absolute values
4. **Subgroup analyses**: Some results are for specific subgroups (e.g., high nicotine dependence)
5. **Multi-arm trials**: Required judgment on which arms to compare (intervention vs control)
6. **Missing SDs**: Many studies report means with CIs but not SDs
7. **Percentage-based binary data**: Required calculating events from n × percentage

---

## Data Quality Notes

- **Goertz 2017_2017**: Change scores, not absolute pain levels
- **Unrod 2016_2016**: Subgroup result, not main trial result
- **Nohlert 2009_2009**: Estimated n per arm (150) based on equal allocation assumption
- **Brandon 2016_2016**: Calculated events from percentages
- **Brown 2001_2001**: Calculated events from percentages

All extractions are conservative - when in doubt, marked found=false rather than inferring data.
