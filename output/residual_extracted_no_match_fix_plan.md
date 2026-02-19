# Residual Extracted-No-Match Diagnostic

- Residual studies analyzed: 19

## Category Counts

- unknown_type_and_no_raw_data: 9
- near_miss_5_to_10pct: 4
- near_miss_10_to_20pct: 3
- missing_expected_effect_family: 2
- tiny_effect_abs_tolerance_candidate: 1

## Prioritized Fix Plan

- P1 | unknown_type_and_no_raw_data (9): Add fallback type inference from outcome text (e.g., death/dropout/adverse event => binary) and confidence penalties when only incompatible effect families are present.
- P2 | near_miss_5_to_10pct (4): Investigate scale/rounding harmonization for outcome families where raw data is absent, including decimal-place normalization and reciprocal/sign disambiguation.
- P2 | near_miss_10_to_20pct (3): Investigate scale/rounding harmonization for outcome families where raw data is absent, including decimal-place normalization and reciprocal/sign disambiguation.
- P1 | missing_expected_effect_family (2): Strengthen outcome-type gating and extraction ranking so binary outcomes prefer OR/RR/RD candidates over MD/SMD noise; add binary table-row parsers for rare event endpoints.
- P2 | tiny_effect_abs_tolerance_candidate (1): Add absolute-tolerance matching guard for very small effects (|effect| <= 0.1) to reduce false misses caused by rounding noise.

## Residual Study Details

| Study | Category | Data Type | Cochrane | Best Candidate | Rel Gap | Transform |
|---|---|---|---:|---:|---:|---|
| Cannell 2018_2018 | near_miss_5_to_10pct | continuous | -0.30198 | -0.320992592267081 | 0.063 | direct |
| Cooke 2011_2011 | unknown_type_and_no_raw_data | unknown | 0.0477 | 0.004897617822218954 | 0.8973 | direct |
| El-Kafy 2021_2021 | near_miss_10_to_20pct | continuous | 0.386851 | 0.4399999999999977 | 0.1374 | sign_flip |
| Guillaumier 2018_2018 | near_miss_5_to_10pct | binary | 1.5 | 1.6085090553312655 | 0.0723 | direct |
| Guo 2022_2022 | missing_expected_effect_family | binary | 0.750241 | 1.0 | 0.3329 | direct |
| Haire-Joshu 2008_2008 | unknown_type_and_no_raw_data | unknown | 0.0267 | 0.036882373648440075 | 0.3814 | sign_flip |
| Hajji 2021_2021 | near_miss_5_to_10pct | binary | 0.395349 | 0.375521103718563 | 0.0502 | direct |
| Kitamura 2020_2020 | unknown_type_and_no_raw_data | unknown | 0.45 | 0.4181187170323605 | 0.0708 | direct |
| Ladapo 2020_2020 | near_miss_5_to_10pct | binary | 1.84 | 1.9333333333333333 | 0.0507 | raw_metric_variant_rr_to_or |
| Linder 2015_2015 | tiny_effect_abs_tolerance_candidate | continuous | 0.006257 | -0.009615384615384609 | 2.5367 | direct |
| Lookzadeh 2019_2019 | missing_expected_effect_family | binary | 1.2 | 1.0 | 0.1667 | direct |
| Morgenstern 2012_2012 | unknown_type_and_no_raw_data | unknown | -0.083 | -0.07009009009009008 | 0.1555 | risk_difference_sign_flip |
| Roset-Salla 2016_2016 | unknown_type_and_no_raw_data | unknown | 0.051918 | 0.0568369260994159 | 0.0947 | direct |
| Santamaria 2015_2015 | near_miss_10_to_20pct | binary | 1.416149 | 1.2230064916985595 | 0.1364 | direct |
| Sherwood 2015_2015 | unknown_type_and_no_raw_data | unknown | 0.2594 | 0.24530471444998087 | 0.0543 | reciprocal |
| Walters 2009_2009 | unknown_type_and_no_raw_data | unknown | 0.266 | 0.251 | 0.0564 | direct |
| Wintzen 2007_2007 | unknown_type_and_no_raw_data | unknown | -3.9 | -3.181874438342219 | 0.1841 | direct |
| Wolf 2000_2000 | near_miss_10_to_20pct | binary | 1.3125 | 1.1292064575806844 | 0.1397 | direct |
| Wyse 2012_2012 | unknown_type_and_no_raw_data | unknown | 0.2485 | 0.27662191632469074 | 0.1132 | sign_flip |
