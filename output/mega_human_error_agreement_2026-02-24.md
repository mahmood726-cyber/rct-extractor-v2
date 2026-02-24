# Mega Real-Data Human-Error Agreement Report

- Generated UTC: 2026-02-24T13:03:09.485924+00:00
- Input: `gold_data/mega/mega_eval.jsonl`
- Human-error envelope target: `10%` relative point-estimate error

## Summary

- Total rows: 560
- Rows with PMCID: 560
- Rows with Cochrane reference: 546
- Strict match rate (5% criterion from eval status): 98.7%
- 10% envelope agreement (status-based, conservative): 98.7%
- 10% envelope bootstrap 95% CI (status-based): 98.7% (97.6% to 99.6%)
- Residual non-match rows: 7

## Residual Rows

| Study ID | Status | PMCID | n_extracted | n_cochrane | Best Direct Rel Error |
| --- | --- | --- | ---: | ---: | ---: |
| Wintzen 2007_2007 | extracted_no_match | PMC1915648 | 34 | 2 | 0.184135 |
| Guo 2022_2022 | extracted_no_match | PMC8941540 | 22 | 3 | 0.332905 |
| Kitamura 2020_2020 | extracted_no_match | PMC7686635 | 395 | 1 | 0.746683 |
| Hajji 2021_2021 | extracted_no_match | PMC7982281 | 256 | 2 | 13.466622 |
| Cooke 2011_2011 | extracted_no_match | PMC3272376 | 31 | 3 | 299.978505 |
| Linder 2015_2015 | extracted_no_match | PMC4480056 | 228 | 1 | 321239.210964 |
| El-Kafy 2021_2021 | no_extraction | PMC8594757 | 0 | 1 | n/a |

## Interpretation

- This artifact provides broad-N real-data agreement evidence for point estimates; CI-field reliability should be evaluated separately.
