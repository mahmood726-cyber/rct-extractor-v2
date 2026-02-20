# External Validation Publishability Report

- Generated UTC: 2026-02-20T13:04:31.795101+00:00
- Cohort: `external_no_tune_41_validated_probe`

## Cohort Integrity

- Selected candidates: 41
- Identity-validated adjudicated full-text trials: 9
- PMCID resolution stats: {'kept_source_pmc_unverified': 35, 'source_pmc_replaced_by_pmid': 8, 'source_pmc_verified_by_pmid': 4}
- Download stats: {'already_present': 32, 'downloaded': 7, 'failed': 2}
- Validation stats: {'failed': 30, 'passed': 9}
- Identity validation applied: True

## Ablation (Adjudicated Cohort)

| Metric | PDF Only | PDF + PubMed | Delta |
| --- | ---: | ---: | ---: |
| extraction_coverage | 100.0% | 100.0% | 0.0% |
| strict_match_rate | 88.9% | 88.9% | 0.0% |
| lenient_match_rate | 100.0% | 100.0% | 0.0% |
| effect_type_accuracy | 100.0% | 100.0% | 0.0% |
| ci_completeness | 88.9% | 88.9% | 0.0% |
| ma_ready_yield | 88.9% | 88.9% | 0.0% |
| computed_effect_share | 22.2% | 22.2% | 0.0% |

- PDF-only status counts: {'approximate_match': 1, 'close_match': 2, 'exact_match': 2, 'exact_match_with_ci': 4}
- PDF+PubMed status counts: {'approximate_match': 1, 'close_match': 2, 'exact_match': 2, 'exact_match_with_ci': 4}

## Bootstrap 95% CI (Adjudicated Cohort, PDF Only)

- extraction_coverage: 100.0% (100.0% to 100.0%)
- strict_match_rate: 88.9% (66.7% to 100.0%)
- lenient_match_rate: 100.0% (100.0% to 100.0%)
- effect_type_accuracy: 100.0% (100.0% to 100.0%)
- ci_completeness: 88.9% (66.7% to 100.0%)
- ma_ready_yield: 88.9% (66.7% to 100.0%)
- computed_effect_share: 22.2% (0.0% to 55.6%)

## Residual Manual Adjudication (Adjudicated Cohort)

| Study | Status | Distance | Gold | Extracted | Judgement | Likely Cause | Recommended Fix |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| cleopatra_2012 | approximate_match | 0.176931 | 0.62 [0.51, 0.75] | HR 0.74 [None, None] | Needs manual endpoint alignment | Extracted HR value is present but CI missing and appears to reflect a non-gold endpoint/timepoint. | Add outcome-anchored selection for trial primary endpoint before ranking numeric candidates. |

## Full-Cohort Sensitivity (40-trial v6 with PubMed fallback)

- extraction_coverage: 100.0% (100.0% to 100.0%)
- strict_match_rate: 85.0% (72.5% to 95.0%)
- lenient_match_rate: 90.0% (80.0% to 97.5%)
- effect_type_accuracy: 100.0% (100.0% to 100.0%)
- ci_completeness: 97.5% (92.5% to 100.0%)
- ma_ready_yield: 92.5% (82.5% to 100.0%)
- computed_effect_share: 85.0% (72.5% to 95.0%)

## Publication Readiness

- Not publication-ready for broad external full-text claims: identity-validated full-text sample remains small.
- Suitable for a methods/technical note with transparent scope and limitations.

## Frozen Artifacts

- Artifact hash index: `output/external_no_tune_41_validated_probe_artifact_hashes.json`
- PDF hash manifest: `data/external_no_tune_41_validated_probe/pdf_hash_manifest.jsonl`
