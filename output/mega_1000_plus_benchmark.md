# Mega 1000+ Benchmark

- Generated UTC: 2026-02-19T10:16:02.652036+00:00
- Mega corpus PDFs: 1290
- Strict criterion: relative error <= 0.05

## Mega Corpus (1290 studies)

| Version | Coverage | Strict Match | Assisted Match | No Extraction |
|---|---:|---:|---:|---:|
| v10_merged | 82.5% | 59.3% | 71.1% | 17.5% |
| v10_1_merged | 90.1% | 71.1% | 83.5% | 9.9% |
| v10_2_merged | 90.4% | 71.7% | 86.0% | 9.6% |

## Real-RCT Production (37-study frozen gold)

| Metric | Baseline | Current | Delta |
|---|---:|---:|---:|
| Extraction coverage | 56.8% | 100.0% | 43.2% |
| Strict match rate | 56.8% | 100.0% | 43.2% |
| CI completeness | 61.9% | 91.9% | 30.0% |
| MA-ready yield | 8.1% | 100.0% | 91.9% |

## Notes

- Mega strict match uses rel_distance <= 5% from merged match records.
- Mega assisted match uses status == match from merged evaluations.
- Mega and Real-RCT cohorts are different and should be compared by trend, not absolute parity.
