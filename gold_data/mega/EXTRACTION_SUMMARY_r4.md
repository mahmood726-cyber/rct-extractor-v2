# Manual Extraction Summary: clean_batch_r4.json

**Date:** 2026-02-14
**Batch:** clean_batch_r4.json (15 studies)
**Output:** clean_results_r4.json

## Overview

| Metric | Count | Percentage |
|--------|-------|------------|
| Total studies | 15 | 100% |
| Data found | 1 | 6.7% |
| Data not found | 14 | 93.3% |

## Breakdown by Outcome Type

| Outcome Type | Total | Found | Not Found |
|--------------|-------|-------|-----------|
| Binary | 4 | 0 | 4 |
| Continuous | 10 | 1 | 9 |
| None/unspecified | 1 | 0 | 1 |

## Successfully Extracted Studies

### 1. Kooncumchoo 2021_2021
- **Outcome:** Walking velocity (metres per second) at end of intervention phase
- **Data type:** Continuous
- **Found:** Baseline walking velocity (10-meter walk test)
- **Intervention (I-Walk):** 0.48 ± 0.19 m/s, n=15
- **Control (Conventional PT):** 0.41 ± 0.17 m/s, n=15
- **Source:** Table 1 (baseline characteristics)
- **Note:** Baseline data extracted, not end-of-intervention as specified in outcome

## Common Reasons for No Extraction

### 1. Qualitative descriptions only (n=6)
Studies reported improvements qualitatively without numerical mean±SD or event counts:
- Buesing 2015: "significant improvements in gait parameters...including an increase in velocity"
- Han 2016: "Both groups exhibited significant functional recovery"
- Forrester 2014, Talaty 2023, Westlake 2009, Choi 2022: Similar pattern

### 2. Wrong outcome reported (n=3)
Results_text contained data for different outcomes:
- Locatelli 2014: Death outcome requested, but text reports phosphorus/cholesterol only
- Kim 2020: Walking velocity requested, but text reports cortical activity (mM·cm)
- Schroeder 2024: Independent walking requested, data_type=None

### 3. Background mentions only (n=2)
Outcome mentioned only in introduction/background, not as trial result:
- Locatelli 2014: Death mentioned in rationale only
- Molteni 2021: Independent walking cited from other studies [18,19]

### 4. Change scores instead of baseline/endpoint (n=1)
- Kang 2021: Reported Δmean±SD (1.1±1.6, 5.5±7.6) for step length changes, not walking velocity values

### 5. P-values without raw data (n=2)
- Louie 2021: "regained independent walking earlier (p = 0.03)" but no event counts
- Gandolfi 2019, Calabrò 2018: Similar pattern

## Data Limitations

The results_text field appears to contain:
1. **Abstract-length excerpts** (5000 chars truncated)
2. **Introduction/background sections** more often than results tables
3. **General conclusions** without detailed numerical data

This suggests the results_text may not be the full results section from the papers, limiting extractability.

## Recommendations

1. **Expand results_text:** Include full results sections with tables, not just abstracts
2. **Prioritize studies with tables:** Look for "Table X" mentions in text
3. **Check for supplementary materials:** Numerical data may be in appendices
4. **Verify outcome alignment:** Ensure results_text discusses the specified outcome
5. **Consider OCR quality:** Some texts may have extraction artifacts

## Study-by-Study Details

| # | Study ID | Outcome | Data Type | Found | Reason if Not Found |
|---|----------|---------|-----------|-------|---------------------|
| 1 | Locatelli 2014 | Death (all causes) | binary | No | Wrong outcome (phosphorus/cholesterol) |
| 2 | Buesing 2015 | Walking velocity | continuous | No | Qualitative only |
| 3 | Han 2016 | Independent walking | binary | No | Qualitative only |
| 4 | Forrester 2014 | Walking velocity | continuous | No | No quantitative data |
| 5 | Louie 2021 | Independent walking | binary | No | P-value only, no event counts |
| 6 | Schroeder 2024 | Independent walking | None | No | Data type None |
| 7 | Molteni 2021 | Independent walking | binary | No | Background mention only |
| 8 | Talaty 2023 | Walking velocity | continuous | No | No quantitative data |
| 9 | Westlake 2009 | Walking velocity | continuous | No | No quantitative data |
| 10 | Choi 2022 | Walking velocity | continuous | No | No quantitative data |
| 11 | Gandolfi 2019 | Walking velocity | continuous | No | No quantitative data |
| 12 | Calabrò 2018 | Walking velocity | continuous | No | No quantitative data |
| 13 | Kang 2021 | Walking velocity | continuous | No | Change scores (Δ) not endpoint |
| 14 | Kim 2020 | Walking velocity | continuous | No | Wrong outcome (cortical activity) |
| 15 | Kooncumchoo 2021 | Walking velocity | continuous | **Yes** | ✓ Baseline table data |

## Extraction Quality Notes

- All extractions follow strict "explicitly stated only" rule
- No calculations or inferences made
- Source quotes provided for all found data
- Reasoning documented for all not-found cases
- One study (Kooncumchoo 2021) has caveat: baseline not endpoint data

---

**Extractor:** Manual human review
**Files created:** clean_results_r4.json, study_r4_*.txt (15 individual study files)
