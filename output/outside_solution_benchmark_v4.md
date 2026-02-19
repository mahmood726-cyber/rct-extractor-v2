# Outside-Solution Benchmark

- Generated UTC: 2026-02-18T13:21:50.138637+00:00
- Gold file: `data\frozen_eval_v1\frozen_gold.jsonl`
- Total trials in full set: 37

## Full Set

| System | Coverage | Strict | Lenient | Effect Type | CI Complete | MA Ready |
|---|---:|---:|---:|---:|---:|---:|
| real_rct_results_upgraded_v3 | 100.0% | 100.0% | 100.0% | 100.0% | 91.9% | 100.0% |
| baseline_results | 56.8% | 56.8% | 56.8% | 100.0% | 61.9% | 8.1% |
| external_mega_v10_merged | 45.9% | 10.8% | 10.8% | 82.4% | 5.9% | 0.0% |
| external_v10_pdf_results | 8.1% | 0.0% | 0.0% | 0.0% | 33.3% | 0.0% |

### mega_overlap_set (21 trials)

## mega_overlap_set Metrics

| System | Coverage | Strict | Lenient | Effect Type | CI Complete | MA Ready |
|---|---:|---:|---:|---:|---:|---:|
| real_rct_results_upgraded_v3 | 100.0% | 100.0% | 100.0% | 100.0% | 95.2% | 100.0% |
| baseline_results | 52.4% | 52.4% | 52.4% | 100.0% | 63.6% | 9.5% |
| external_mega_v10_merged | 81.0% | 19.0% | 19.0% | 82.4% | 5.9% | 0.0% |
| external_v10_pdf_results | 14.3% | 0.0% | 0.0% | 0.0% | 33.3% | 0.0% |

Trial IDs:

Berry_2013, Beulen_2016, Bomyea_2015, Chung_2022, Coentrao_2012, Fagerlin_2011, Feltner_2009, Habib_2017, Hirono_2019, Hutchins_2019, Jin_2016, McDonald_2015, Moschonis_2019, Oyo-Ita_2021, Palve_2020, Papay_2014, Rajanbabu_2019, Shi_2012, Siddiqi_2020, Toker_2019, Yan_2021

### v10_pdf_overlap_set (6 trials)

## v10_pdf_overlap_set Metrics

| System | Coverage | Strict | Lenient | Effect Type | CI Complete | MA Ready |
|---|---:|---:|---:|---:|---:|---:|
| real_rct_results_upgraded_v3 | 100.0% | 100.0% | 100.0% | 100.0% | 83.3% | 100.0% |
| baseline_results | 16.7% | 16.7% | 16.7% | 100.0% | 0.0% | 0.0% |
| external_mega_v10_merged | 33.3% | 16.7% | 16.7% | 100.0% | 0.0% | 0.0% |
| external_v10_pdf_results | 50.0% | 0.0% | 0.0% | 0.0% | 33.3% | 0.0% |

Trial IDs:

Berry_2013, Fagerlin_2011, Feltner_2009, Habib_2017, Rajanbabu_2019, Toker_2019

### all_external_overlap_set (6 trials)

## all_external_overlap_set Metrics

| System | Coverage | Strict | Lenient | Effect Type | CI Complete | MA Ready |
|---|---:|---:|---:|---:|---:|---:|
| real_rct_results_upgraded_v3 | 100.0% | 100.0% | 100.0% | 100.0% | 83.3% | 100.0% |
| baseline_results | 16.7% | 16.7% | 16.7% | 100.0% | 0.0% | 0.0% |
| external_mega_v10_merged | 33.3% | 16.7% | 16.7% | 100.0% | 0.0% | 0.0% |
| external_v10_pdf_results | 50.0% | 0.0% | 0.0% | 0.0% | 33.3% | 0.0% |

Trial IDs:

Berry_2013, Fagerlin_2011, Feltner_2009, Habib_2017, Rajanbabu_2019, Toker_2019

## Notes

- External benchmark uses two outside artifacts adapted to the real-RCT schema.
- Study mapping is author-year key based and excludes ambiguous key collisions.
- Full-set metrics answer end-to-end readiness on the target 37-study cohort.
