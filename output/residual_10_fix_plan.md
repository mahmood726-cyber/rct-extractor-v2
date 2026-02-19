# Residual Extracted-No-Match Diagnostic

- Residual studies analyzed: 10

## Category Counts

- unknown_type_and_no_raw_data: 6
- far_miss_gt_20pct: 2
- missing_expected_effect_family: 2

## Prioritized Fix Plan

- P1 | unknown_type_and_no_raw_data (6): Add fallback type inference from outcome text (e.g., death/dropout/adverse event => binary) and confidence penalties when only incompatible effect families are present.
- P3 | far_miss_gt_20pct (2): Manual triage with PDF-level evidence snippets; these are likely outcome-linking or reporting-ambiguity cases needing targeted heuristics.
- P1 | missing_expected_effect_family (2): Strengthen outcome-type gating and extraction ranking so binary outcomes prefer OR/RR/RD candidates over MD/SMD noise; add binary table-row parsers for rare event endpoints.

## Residual Study Details

| Study | Category | Data Type | Cochrane | Best Candidate | Rel Gap | Transform |
|---|---|---|---:|---:|---:|---|
| Cooke 2011_2011 | unknown_type_and_no_raw_data | unknown | 0.0477 | 14.261274691780867 | 297.9785 | sign_flip |
| El-Kafy 2021_2021 | far_miss_gt_20pct | continuous | 0.386851 | 827.3727846183966 | 2137.7376 | sign_flip |
| Guo 2022_2022 | missing_expected_effect_family | binary | 0.750241 | 1.0 | 0.3329 | direct |
| Haire-Joshu 2008_2008 | unknown_type_and_no_raw_data | unknown | 0.0267 | 0.18081534908050018 | 5.7721 | smd_d_to_hedges_df8 |
| Hajji 2021_2021 | missing_expected_effect_family | binary | 0.395349 | -4.928666644805762 | 13.4666 | direct |
| Kitamura 2020_2020 | unknown_type_and_no_raw_data | unknown | 0.45 | 0.1262063286696591 | 0.7195 | smd_hedges_to_d_df8 |
| Linder 2015_2015 | far_miss_gt_20pct | continuous | 0.006257 | 2010.0 | 321239.211 | direct |
| Morgenstern 2012_2012 | unknown_type_and_no_raw_data | unknown | -0.083 | -0.53 | 5.3855 | sign_flip |
| Walters 2009_2009 | unknown_type_and_no_raw_data | unknown | 0.266 | 0.7577839875736236 | 1.8488 | smd_signflip_d_to_hedges_df8 |
| Wintzen 2007_2007 | unknown_type_and_no_raw_data | unknown | -3.9 | -3.181874438342219 | 0.1841 | direct |
