# Batch R51 - Manual Gold Standard Extraction

## Overview
- **Input**: `clean_batch_r51.json` (15 studies)
- **Output**: `clean_results_r51.json` (15 extraction results)
- **Date**: 2026-02-14
- **Extractor**: Claude Code (manual review)

## Extraction Rules
1. **Only extract EXPLICITLY stated data** - Never calculate or infer
2. The "outcome" field indicates which specific outcome to extract
3. If data not found, set `found=false`
4. Provide `source_quote` and `reasoning` for all decisions

## Results Summary
- **Total studies**: 15
- **Found**: 7 (46.7%)
- **Not found**: 8 (53.3%)

### Found Breakdown
- **Binary outcomes**: 1 study (Sahr 2021 - vaping cessation)
- **Continuous data** (mean ± SD provided): 3 studies
  - Acheampong 2018 - systolic BP
  - Faggiani 2022 - HHS functional status
  - Johansson 2020 - BMI z-score change
- **Mean difference only**: 3 studies
  - Jarbandhan 2022 - DASH disability score (MD = -9.8)
  - Vidmar 2023 - BMI change with CI (MD = -1.29 [−1.82, −0.76])
  - Ball 2024 - OHS quality of life with CI (MD = -1.23 [−3.96, 1.49])

### Not Found - Reasons
1. **Norman 2016**: Only p-value, no numerical BMI values
2. **Abraham 2015**: Only qualitative statement ("no significant differences")
3. **Likhitweerawong 2021**: Only qualitative comparison
4. **Dean 2018**: No numerical disability values in excerpt
5. **Rizvi 2023**: No numerical BP values in excerpt
6. **Vahlberg 2021**: 6-minute walk test reported, but no walking speed (m/s) values
7. **Saxer 2018**: Qualitative statement on mortality, no event counts
8. **Klein 2024**: Results excerpt only shows baseline data, no cessation outcomes

## Output Schema
Each entry contains:
```json
{
  "study_id": "string",
  "found": boolean,
  "effect_type": "MD|RR|OR|HR|etc or null",
  "point_estimate": number or null,
  "ci_lower": number or null,
  "ci_upper": number or null,
  "intervention_events": number or null,
  "intervention_n": number or null,
  "control_events": number or null,
  "control_n": number or null,
  "intervention_mean": number or null,
  "intervention_sd": number or null,
  "control_mean": number or null,
  "control_sd": number or null,
  "source_quote": "string",
  "reasoning": "string"
}
```

## Files
- `clean_batch_r51.json` - Input batch with study metadata and results_text
- `clean_results_r51.json` - Output extraction results (15 entries)
- `extract_r51_complete.py` - Extraction script with study-specific logic
- `r51_extraction_summary.txt` - Detailed human-readable summary
- `README_r51.md` - This file

## Validation
All schema checks pass:
- ✓ Valid JSON format
- ✓ All 15 entries present
- ✓ All required fields present in each entry
- ✓ No missing study_id, found, or reasoning fields

## Notable Cases

### Johansson 2020
- Provides mean change for both groups but **no SDs**
- Intervention: -0.23, Control: 0.01, Difference: -0.24
- Source explicitly states the values

### Vidmar 2023
- Reports **overall effect** across all groups combined
- "All adolescents... lost weight over 24-weeks (−1.29%, [−1.82, −0.76])"
- BUT "no significant weight loss difference between groups (p = 0.3)"
- Extracted overall MD with CI, but note this is not intervention vs control

### Acheampong 2018
- Table format with pre/post values
- Extracted **POST-treatment** values for both groups
- Combined exercise (intervention): 126.20 ± 7.82 mmHg
- Conventional (control): 142.13 ± 8.00 mmHg

### Sahr 2021
- Three-arm trial (NRT+behavioral, vape-taper+behavioral, self-guided)
- Extracted vape-taper+behavioral (6/8) vs self-guided (4/9)
- Could also extract NRT+behavioral (3/7) vs self-guided as alternative comparison

### Ball 2024
- Large RCT (244 participants)
- **Adjusted** mean difference provided with CI
- Primary outcome: Oxford Hip Score at 120 days
- MD = -1.23 [95% CI −3.96 to 1.49], p=0.37 (not significant)

## Limitations
1. Many studies provide only p-values without effect estimates
2. Some excerpts may be truncated (full tables not available)
3. "Explicit only" rule is conservative - real papers likely have more data in tables/appendices
4. Multi-arm trials require choosing which comparison to extract
5. Some studies report overall effects but not between-group differences
