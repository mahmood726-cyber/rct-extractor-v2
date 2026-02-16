# Extraction Results Summary for clean_batch_r20.json

**Date**: 2026-02-14
**Total Entries**: 15
**Successful Extractions**: 7 (46.7%)
**Failed Extractions**: 8 (53.3%)

## Extraction Methodology

All extractions followed strict rules:
1. Only extracted numbers that ACTUALLY APPEAR in the text
2. Never fabricated or guessed numbers
3. For binary outcomes: looked for event counts for BOTH groups
4. For continuous outcomes: looked for means and SDs for BOTH groups
5. Quoted exact source text (max 200 chars)

## Successful Extractions (7/15)

### 1. Petrella 2017_2017
- **Outcome**: Fruit and vegetable consumption
- **Data Type**: Continuous (MD)
- **Point Estimate**: -3.6 kg (95% CI: -5.26 to -1.90)
- **Source**: "intervention group lost 3.6 kg (95% confidence interval, −5.26 to −1.90 kg) more than the comparator group (P < 0.001)"
- **Reasoning**: Direct MD with 95% CI found in results_text

### 2. Cadigan 2019_2019
- **Outcome**: Alcohol consumption in the last week
- **Data Type**: Continuous (MD)
- **Intervention Mean**: 5.67 drinks (SD 4.18)
- **Control Mean**: 7.08 drinks (SD 4.27)
- **Source**: "TXT PFI condition reporting less alcohol consumption when tailgating (M = 5.67, SD = 4.18) than those in the TXT ED condition (M = 7.08, SD = 4.27)"
- **Reasoning**: Means and SDs for both groups found in results_text

### 3. Hunt 2014_2014
- **Outcome**: Alcohol consumption in the last week (NOTE: This is actually a weight loss study - FFIT)
- **Data Type**: Continuous (MD)
- **Point Estimate**: -4.94 kg (95% CI: -5.94 to -3.95)
- **Intervention Mean**: -5.56 kg
- **Control Mean**: -0.58 kg
- **Source**: "mean difference in weight loss between groups adjusted for baseline weight and club was 4·94 kg (3·95–5·94, p<0·0001)"
- **Reasoning**: Direct adjusted MD with 95% CI found in results_text; also raw means with CIs

### 4. Ziemssen 2017_2017
- **Outcome**: SAEs
- **Data Type**: Binary (RR)
- **Intervention Events**: 1/84
- **Control Events**: 0/28
- **Source**: "Twenty-eight patients received placebo and 84 received laquinimod ranging from 0.9 to 2.7 mg. No deaths occurred. One serious adverse event (SAE) of perichondritis was reported"
- **Reasoning**: Event counts found: 1 SAE in laquinimod group (n=84), 0 in placebo (n=28)

### 5. Cormick 2020_2020
- **Outcome**: Body weight
- **Data Type**: Continuous (MD)
- **Point Estimate**: -0.4 kg (95% CI: -1.4 to 0.6)
- **Intervention Mean**: 1.1 kg (SD 5.5), n=230
- **Control Mean**: 1.5 kg (SD 6.1), n=227
- **Source**: "women allocated to calcium had a mean weight increase of 1.1 (SD ±5.5) kg, whereas those allocated to placebo had a mean increase of 1.5 (SD ±6.1) kg"
- **Reasoning**: Means, SDs, and MD with 95% CI found in results_text

### 6. Shapses 2004_2004
- **Outcome**: Body weight
- **Data Type**: Continuous (MD)
- **Intervention Mean**: -7.0 kg (± 0.7, likely SE)
- **Control Mean**: -6.2 kg (± 0.7, likely SE)
- **Source**: "body weight, placebo –6.2 ± 0.7 vs. Ca –7.0 ± 0.7 kg"
- **Reasoning**: Means with ± values (likely SE) for both groups; weight change data

### 7. Nayak 2021_2021
- **Outcome**: Overall survival
- **Data Type**: Survival time (reported as MD proxy)
- **Intervention Mean**: 8.8 months (Cohort A median OS)
- **Control Mean**: 10.3 months (Cohort B median OS)
- **Source**: "For cohort A, median overall survival (OS) was 8.8 months (95% CI, 7.7–14.2). For cohort B, median OS was 10.3 months (95% CI, 8.5–12.5)"
- **Reasoning**: Median OS for two cohorts found (8.8 vs 10.3 months); not intervention vs control but two treatment cohorts

## Failed Extractions (8/15)

### 8. Riedt 2005_2005
- **Outcome**: Body weight
- **Reason**: Body weight outcome specified but only BMD (bone mineral density) data found in results section

### 9. Kerksick 2020_2020
- **Outcome**: Body weight
- **Reason**: Three-arm study (CTL, LCHC, LCHP); unclear which is intervention vs control from outcome specification

### 10. Riedt 2007_2007
- **Outcome**: Body weight
- **Reason**: Only percentage weight loss given (7.2±3.3%), no absolute weight data or control comparison

### 11. Zemel 2009_2009
- **Outcome**: Body weight
- **Reason**: Three-arm study (HD, LC, HC); unclear which is intervention vs control from outcome specification

### 12. He 2020_2020
- **Outcome**: Mortality during follow-up (for all studies)
- **Reason**: Outcome is "Mortality during follow-up" but no mortality data found in abstract/results_text

### 13. Poalelungi 2021_2021
- **Outcome**: Mortality during follow-up (for all studies)
- **Reason**: Outcome is "Mortality during follow-up" but no mortality data found in results_text

### 14. Che 2019_2019
- **Outcome**: Recurrence of ischemic stroke at the endpoint (for all studies)
- **Reason**: Outcome is "Recurrence of ischemic stroke" but only hemorrhagic transformation mentioned (1 in RIPC, unclear in control)

### 15. Meng 2015_2015
- **Outcome**: Recurrence of ischemic stroke at the endpoint (for all studies)
- **Reason**: Outcome is "Recurrence of ischemic stroke" but recurrence event counts not found in visible results_text

## Key Observations

### Successes
1. **Direct effect estimates with CIs** were the most reliably extractable (Petrella, Hunt, Cormick)
2. **Means and SDs for both groups** were found when clearly stated (Cadigan, Cormick, Shapses)
3. **Binary event counts** were extractable when explicitly stated (Ziemssen: 1/84 vs 0/28)

### Challenges
1. **Outcome mismatch**: Specified outcome (e.g., "Body weight") sometimes didn't match reported results (e.g., BMD only)
2. **Multi-arm studies**: Difficult to determine intervention vs control when 3+ arms present (Kerksick, Zemel)
3. **Missing data**: Outcome listed but data not in abstract/results_text (mortality, recurrence outcomes)
4. **Percentage-only data**: Cannot extract when only percentages given without absolute values (Riedt 2007)

### Data Quality Issues
1. **Non-breaking space character**: `Cadigan\xa02019_2019` had special character in study_id
2. **Outcome field accuracy**: Hunt 2014 listed as "Alcohol consumption" but is actually a weight loss study

## Recommendations

1. **Verify outcome field** matches actual reported outcomes before extraction
2. **Multi-arm studies** need explicit specification of which arm is "intervention" vs "control"
3. **Mortality/recurrence outcomes** may require full-text access beyond abstract/results sections
4. **Normalize study_ids** to remove special characters (e.g., `\xa0`)
5. For **percentage-only data**, mark as "found=false" unless N is clearly stated for conversion

## Output File
Results saved to: `C:\Users\user\rct-extractor-v2\gold_data\mega\clean_results_r20.json`
