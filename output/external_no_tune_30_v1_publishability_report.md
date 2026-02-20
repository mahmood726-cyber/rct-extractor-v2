# External Validation Publishability Report

- Generated UTC: 2026-02-20T12:19:05.676334+00:00
- Cohort: `external_no_tune_30_v1`

## Cohort Integrity

- Selected candidates: 41
- Adjudicated full-text trials: 30
- Parent frozen trials: 40
- Excluded during adjudication: 10
- Included statuses: ['close_match', 'exact_match', 'exact_match_with_ci']
- Excluded status counts: {'approximate_match': 2, 'close_match': 4, 'distant_match': 4}
- PMCID resolution stats: {}
- Download stats: {'already_present': 39, 'failed': 1, 'downloaded': 1}
- Validation stats: {}
- Identity validation applied: False

## Ablation (Adjudicated Cohort)

| Metric | PDF Only | PDF + PubMed | Delta |
| --- | ---: | ---: | ---: |
| extraction_coverage | 93.3% | 100.0% | 6.7% |
| strict_match_rate | 93.3% | 100.0% | 6.7% |
| lenient_match_rate | 93.3% | 100.0% | 6.7% |
| effect_type_accuracy | 100.0% | 100.0% | 0.0% |
| ci_completeness | 100.0% | 100.0% | 0.0% |
| ma_ready_yield | 93.3% | 93.3% | 0.0% |
| computed_effect_share | 90.0% | 90.0% | 0.0% |

- PDF-only status counts: {'close_match': 9, 'exact_match': 17, 'exact_match_with_ci': 2, 'no_match': 2}
- PDF+PubMed status counts: {'close_match': 9, 'exact_match': 17, 'exact_match_with_ci': 4}

## Bootstrap 95% CI (Adjudicated Cohort, PDF Only)

- extraction_coverage: 93.3% (83.3% to 100.0%)
- strict_match_rate: 93.3% (83.3% to 100.0%)
- lenient_match_rate: 93.3% (83.3% to 100.0%)
- effect_type_accuracy: 100.0% (100.0% to 100.0%)
- ci_completeness: 100.0% (100.0% to 100.0%)
- ma_ready_yield: 93.3% (83.3% to 100.0%)
- computed_effect_share: 90.0% (80.0% to 100.0%)

## Residual Manual Adjudication (Adjudicated Cohort)

| Study | Status | Distance | Gold | Extracted | Judgement | Likely Cause | Recommended Fix |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| courage_2007 | no_match | n/a | 1.05 [0.87, 1.27] | None None [None, None] | Needs manual review | Unclassified residual mismatch. | Manual extraction and pattern triage. |
| pacific_2017 | no_match | n/a | 0.52 [0.42, 0.65] | None None [None, None] | Needs manual review | Unclassified residual mismatch. | Manual extraction and pattern triage. |

## Full-Cohort Sensitivity (40-trial v6 with PubMed fallback)

- extraction_coverage: 100.0% (100.0% to 100.0%)
- strict_match_rate: 85.0% (72.5% to 95.0%)
- lenient_match_rate: 90.0% (80.0% to 97.5%)
- effect_type_accuracy: 100.0% (100.0% to 100.0%)
- ci_completeness: 97.5% (92.5% to 100.0%)
- ma_ready_yield: 92.5% (82.5% to 100.0%)
- computed_effect_share: 85.0% (72.5% to 95.0%)

## Publication Readiness

- Not publication-ready for identity-validated external-claim framing: this cohort is adjudicated but not identity-validated.
- Suitable for internal benchmarking and ablation reporting with explicit limitations.
- Suitable for a methods/technical note with transparent scope and limitations.

## Frozen Artifacts

- Artifact hash index: `output/external_no_tune_30_v1_artifact_hashes.json`
- PDF hash manifest: `data/external_no_tune_30_v1/pdf_hash_manifest.jsonl`
