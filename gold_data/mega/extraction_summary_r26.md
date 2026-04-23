<!-- sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files. -->

# Extraction Summary: clean_batch_r26.json

**Date**: 2026-02-14
**Batch**: r26 (15 studies)
**Extractor**: Manual extraction (Claude Sonnet 4.5)

## Overview

- **Total studies**: 15
- **Data found**: 1 (6.7%)
- **No extractable data**: 14 (93.3%)

## Extraction Results

### Studies with Extractable Data (1)

#### Freedland 2009_2009
- **Outcome**: Depression (continuous)
- **Effect type**: MD (Mean Difference)
- **Data extracted**:
  - Intervention (CBT): mean = 5.5, SD = 1.0
  - Control (usual care): mean = 10.7, SD = 1.0
- **Source quote**: "Covariate-adjusted Hamilton scores were lower in the cognitive behavior therapy (mean [standard error], 5.5 [1.0]) and the supportive stress-management (7.8 [1.0]) arms than in the usual care arm (10.7 [1.0]) at 3 months."
- **Note**: Values reported are standard errors (SE), not standard deviations (SD)

### Studies with No Extractable Data (14)

| Study ID | Outcome | Reason |
|----------|---------|--------|
| Sikkema 2018_2018 | PTSD symptoms, post-treatment | No explicit numerical values (means, SDs) reported |
| Covers 2021_2021 | PTSD symptoms, post-treatment | Only effect sizes reported, not raw means/SDs |
| Mohammadi 2018_2018 | Change in burn-related pruritus | Significance stated but no numerical values |
| Thibaut 2019_2019 | Change in burn-related pruritus | VAS mentioned but no explicit mean ± SD values |
| Agren 2012_2012 | Depression | "No group differences" stated, no numerical data |
| Byrd 2018_2018 | Overall survival | Results_text contains only references section |
| Kumar 2020_2020 | Caregiver burden | Methods description only, no outcome data |
| Nijjar 2019_2019 | Depression | Change score mentioned (-2.3) but incomplete data |
| Song 2006_2006 | Participant-reported cure/improvement | Percentages reported (53.9%, 63.0%, 71.0%) but event counts not explicit |
| Sharif 2012_2012 | Caregiver burden | Significance stated but no numerical values |
| Eleuterio 2019_2019 | Frequency of crisis | "Reduction in pain frequency" mentioned, no values |
| Scoffone 2013_2013 | Haemoglobin status | Hemoglobin S mentioned but no explicit Hb levels |
| Nur 2012_2012 | Haemoglobin status | Hemoglobin values not in provided results_text |
| Nakata 2022_2022 | Physical activity (MVPA) | Results focus on weight/biochemistry, not MVPA |

## Extraction Methodology

**Strict adherence to rules**:
1. Only extracted data EXPLICITLY stated in results_text
2. No calculations or inferences
3. No derived values (e.g., calculating event counts from percentages)
4. Required both point estimates AND measures of variance for continuous outcomes
5. Required raw event counts for binary outcomes

**Borderline cases**:
- **Song 2006**: Improvement percentages (53.9%, 63.0%, 71.0%) and sample sizes (n=26, 32, 31) were explicitly stated, but raw event counts were not. Could potentially be marked as "found" with calculated events, but kept as "not found" per strict interpretation of rules.
- **Nijjar 2019**: Mean change in PHQ-9 for MBSR group mentioned (-2.3 points) but SD not reported and control group change value not explicit. Marked as incomplete/not found.

## Quality Notes

- **Freedland 2009**: Reported values are standard errors (SE), not standard deviations. This is an important distinction for meta-analysis calculations.
- Most studies in this batch had qualitative results statements ("significantly reduced", "greater improvements") without accompanying numerical data in the results_text provided.
- Several studies had truncated or incomplete results_text sections (e.g., Byrd 2018 had only references).

## Output File

**Location**: `C:\Users\user\rct-extractor-v2\gold_data\mega\clean_results_r26.json`

**Format**: JSON array with 15 objects, each containing:
- study_id
- found (boolean)
- effect_type
- point_estimate, ci_lower, ci_upper
- intervention_events, intervention_n, control_events, control_n
- intervention_mean, intervention_sd, control_mean, control_sd
- source_quote
- reasoning
