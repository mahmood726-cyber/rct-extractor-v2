# Residual Extracted-No-Match Diagnostic

- Residual studies analyzed: 18

## Category Counts

- unknown_type_and_no_raw_data: 8
- far_miss_gt_20pct: 4
- missing_expected_effect_family: 4
- near_miss_10_to_20pct: 1
- near_miss_5_to_10pct: 1

## Prioritized Fix Plan

- P1 | unknown_type_and_no_raw_data (8): Add fallback type inference from outcome text (e.g., death/dropout/adverse event => binary) and confidence penalties when only incompatible effect families are present.
- P3 | far_miss_gt_20pct (4): Manual triage with PDF-level evidence snippets; these are likely outcome-linking or reporting-ambiguity cases needing targeted heuristics.
- P1 | missing_expected_effect_family (4): Strengthen outcome-type gating and extraction ranking so binary outcomes prefer OR/RR/RD candidates over MD/SMD noise; add binary table-row parsers for rare event endpoints.
- P2 | near_miss_10_to_20pct (1): Investigate scale/rounding harmonization for outcome families where raw data is absent, including decimal-place normalization and reciprocal/sign disambiguation.
- P2 | near_miss_5_to_10pct (1): Investigate scale/rounding harmonization for outcome families where raw data is absent, including decimal-place normalization and reciprocal/sign disambiguation.

## Residual Study Details

| Study | Category | Data Type | Cochrane | Best Candidate | Rel Gap | Transform |
|---|---|---|---:|---:|---:|---|
| Cannell 2018_2018 | far_miss_gt_20pct | continuous | -0.30198 | -82.8404208746717 | 273.3242 | direct |
| Cooke 2011_2011 | unknown_type_and_no_raw_data | unknown | 0.0477 | 14.261274691780867 | 297.9785 | sign_flip |
| El-Kafy 2021_2021 | far_miss_gt_20pct | continuous | 0.386851 | 827.3727846183966 | 2137.7376 | sign_flip |
| Guillaumier 2018_2018 | near_miss_5_to_10pct | binary | 1.5 | 1.37 | 0.0867 | direct |
| Guo 2022_2022 | missing_expected_effect_family | binary | 0.750241 | 1.0 | 0.3329 | direct |
| Haire-Joshu 2008_2008 | unknown_type_and_no_raw_data | unknown | 0.0267 | 0.20018842219626806 | 6.4977 | direct |
| Hajji 2021_2021 | missing_expected_effect_family | binary | 0.395349 | -4.928666644805762 | 13.4666 | direct |
| Kitamura 2020_2020 | unknown_type_and_no_raw_data | unknown | 0.45 | 0.11399281299195016 | 0.7467 | direct |
| Ladapo 2020_2020 | far_miss_gt_20pct | binary | 1.84 | 2.56 | 0.3913 | direct |
| Linder 2015_2015 | far_miss_gt_20pct | continuous | 0.006257 | 2010.0 | 321239.211 | direct |
| Lookzadeh 2019_2019 | missing_expected_effect_family | binary | 1.2 | 1.0 | 0.1667 | direct |
| Morgenstern 2012_2012 | unknown_type_and_no_raw_data | unknown | -0.083 | -0.53 | 5.3855 | sign_flip |
| Santamaria 2015_2015 | near_miss_10_to_20pct | binary | 0.164191 | 0.19 | 0.1572 | direct |
| Sherwood 2015_2015 | unknown_type_and_no_raw_data | unknown | 0.2594 | 0.22213798538054388 | 0.1436 | direct |
| Walters 2009_2009 | unknown_type_and_no_raw_data | unknown | 0.266 | 0.838975129099369 | 2.154 | sign_flip |
| Wintzen 2007_2007 | unknown_type_and_no_raw_data | unknown | -3.9 | -3.181874438342219 | 0.1841 | direct |
| Wolf 2000_2000 | missing_expected_effect_family | binary | 1.3125 | 63.78305084745763 | 47.5966 | direct |
| Wyse 2012_2012 | unknown_type_and_no_raw_data | unknown | 0.2485 | 1.3763636146495029 | 4.5387 | sign_flip |
