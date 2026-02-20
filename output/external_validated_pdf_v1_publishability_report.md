# External Validation Publishability Report

- Generated UTC: 2026-02-20T11:30:52.759072+00:00
- Cohort: `external_validated_pdf_v1`

## Cohort Integrity

- Selected candidates: 47
- Frozen identity-validated full-text trials: 11
- PMCID resolution stats: {'kept_source_pmc_unverified': 35, 'source_pmc_replaced_by_pmid': 8, 'source_pmc_verified_by_pmid': 4}
- Download stats: {'downloaded': 42, 'failed': 4, 'already_present': 1}
- Validation stats: {'failed': 32, 'passed': 11}

## Ablation (Validated Cohort)

| Metric | PDF Only | PDF + PubMed | Delta |
| --- | ---: | ---: | ---: |
| extraction_coverage | 100.0% | 100.0% | 0.0% |
| strict_match_rate | 90.9% | 90.9% | 0.0% |
| lenient_match_rate | 100.0% | 100.0% | 0.0% |
| effect_type_accuracy | 100.0% | 100.0% | 0.0% |
| ci_completeness | 90.9% | 90.9% | 0.0% |
| ma_ready_yield | 90.9% | 90.9% | 0.0% |
| computed_effect_share | 18.2% | 18.2% | 0.0% |

- PDF-only status counts: {'approximate_match': 1, 'close_match': 2, 'exact_match': 2, 'exact_match_with_ci': 6}
- PDF+PubMed status counts: {'approximate_match': 1, 'close_match': 2, 'exact_match': 2, 'exact_match_with_ci': 6}

## Bootstrap 95% CI (Validated Cohort, PDF Only)

- extraction_coverage: 100.0% (100.0% to 100.0%)
- strict_match_rate: 90.9% (72.7% to 100.0%)
- lenient_match_rate: 100.0% (100.0% to 100.0%)
- effect_type_accuracy: 100.0% (100.0% to 100.0%)
- ci_completeness: 90.9% (72.7% to 100.0%)
- ma_ready_yield: 90.9% (72.7% to 100.0%)
- computed_effect_share: 18.2% (0.0% to 45.5%)

## Residual Manual Adjudication (Validated Cohort)

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

- Artifact hash index: `output/external_validated_pdf_v1_artifact_hashes.json`
- PDF hash manifest: `data/external_validated_pdf_v1/pdf_hash_manifest.jsonl`
